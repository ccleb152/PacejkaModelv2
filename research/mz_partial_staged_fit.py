"""Experiment: a "partial staged" hybrid Mz fit -- keep the production
dFz (load-sweep) stage exactly as it is, but fit the Base and dIA stages
*jointly* instead of staged, using both the reference condition and the
full camber sweep together.

Motivation: the two previous experiments here (see
OPTIMIZATION_NOTES.md, 2026-10-02 entries) showed the production staged
fit's actual weak point is the Base stage, not the dIA stage directly --
the Base stage fits 10 coefficients using *only* the single zero-camber
reference condition, with no camber information at all, before the dIA
stage ever runs. By the time the dIA stage gets its turn, it's stuck
making the best of whatever the Base stage chose, using coefficients
that were never asked to accommodate anything off-camber in the first
place. Fully joint fitting (all coefficients, all conditions at once)
fixed that but broke the load sweep, because the dFz stage's conditions
got diluted into the same unweighted objective as everything else --
even though the dFz stage alone, in production, does a good job.

This hybrid targets the actual mechanism: refit Base+dIA together against
{base, camber_sweep} (so the camber-sensitive coefficients can draw on
real camber data *and* the Base-stage coefficients get to adjust to
accommodate it, instead of being frozen before the dIA stage ever sees
the data) -- then run the dFz stage exactly as production does, using
the load sweep, with the new Base-stage coefficients as its starting
point. The load sweep's fitting conditions are untouched from production;
only how the Base/dIA split works changes.

This does NOT modify pacejka/fitters/mz.py or anything the deployed app
uses -- it imports that module's field/bound tables for a fair
side-by-side comparison, and pacejka.model's public mz_pure/
MzCoefficients to run its own independent optimization.

Usage:
    python research/mz_partial_staged_fit.py [compound] [diameter_in] [width_in]

Defaults to the bundled R20 16x7.5 (same tire as the other Mz
experiments). Writes a comparison plot to research/output/.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.optimize import least_squares

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pacejka.fitting import split_fixed_fields
from pacejka.fitters.mz import (
    _BASE_BOUNDS,
    _BASE_FIELDS,
    _DFZ_BOUNDS,
    _DFZ_FIELDS,
    _DIA_BOUNDS,
    _DIA_FIELDS,
    _MZ_P0,
    MzFitResult,
    sweep_point_from_aligning_moment,
)
from pacejka.io.tire_catalog import load_combined_round, scan_raw_data_folder
from pacejka.model import fy_terms, mz_pure, MzCoefficients
from pacejka.pipeline import run_cornering_fit
from pacejka.regression import fit_quality_table

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def _load_tire_samples(compound: str, diameter_in: float, width_in: float):
    catalog = scan_raw_data_folder("RawDataFiles")
    entries = [
        e for e in catalog.entries
        if e.tire.compound == compound and e.tire.diameter_in == diameter_in and e.tire.width_in == width_in
    ]
    if not entries:
        raise SystemExit(f"No bundled RawDataFiles entries for {compound} {diameter_in}x{width_in}.")
    return load_combined_round(entries).samples


def _fy_derived(points, fz0_prime, fy_coefficients):
    derived = []
    for p in points:
        terms = fy_terms(p.fz_n, fz0_prime, p.gamma_star, p.alpha_rad, fy_coefficients)
        terms_g0 = fy_terms(p.fz_n, fz0_prime, 0.0, p.alpha_rad, fy_coefficients)
        derived.append((float(terms.cy), float(terms.by), float(terms.s_hf), terms_g0.fyo))
    return derived


def _eval_mz(points, fy_derived, fz0_prime, ro, coeffs: MzCoefficients):
    return [
        mz_pure(p.fz_n, fz0_prime, ro, p.gamma_star, p.alpha_rad, p.cos_alpha_p, cy, by, s_hf, fy_og0, coeffs)
        for p, (cy, by, s_hf, fy_og0) in zip(points, fy_derived)
    ]


def _fit_stage(field_names, bounds, x0_source, points, fy_derived, fz0_prime, ro, fixed_values):
    """Shared stage-fitting helper: fit `field_names` jointly against
    `points`, holding `fixed_values` constant. Mirrors
    pacejka.fitters.mz's own `_fit_mz_stage`/`fit_stage` mechanics
    (clip x0 into bounds, bounded least_squares) without reaching into
    that module's private helper directly.
    """
    alpha_rad = np.concatenate([p.alpha_rad for p in points])
    fz_n = np.concatenate([np.full_like(p.alpha_rad, p.fz_n) for p in points])
    gamma_star = np.concatenate([np.full_like(p.alpha_rad, p.gamma_star) for p in points])
    cos_alpha_p = np.concatenate([p.cos_alpha_p for p in points])
    target_mz_nm = np.concatenate([p.mz_nm for p in points])
    fy_cy = np.concatenate([np.full_like(p.alpha_rad, d[0]) for p, d in zip(points, fy_derived)])
    fy_by = np.concatenate([np.full_like(p.alpha_rad, d[1]) for p, d in zip(points, fy_derived)])
    s_hf = np.concatenate([np.full_like(p.alpha_rad, d[2]) for p, d in zip(points, fy_derived)])
    fy_og0 = np.concatenate([d[3] for d in fy_derived])

    def residuals(x):
        values = dict(fixed_values)
        values.update(zip(field_names, x))
        mz = mz_pure(fz_n, fz0_prime, ro, gamma_star, alpha_rad, cos_alpha_p, fy_cy, fy_by, s_hf, fy_og0, MzCoefficients(**values))
        return mz - target_mz_nm

    x0 = [x0_source[name] for name in field_names]
    lb, ub = zip(*bounds)
    x0_clipped = np.clip(x0, lb, ub)
    result = least_squares(residuals, x0_clipped, bounds=(lb, ub))
    return dict(zip(field_names, result.x))


def fit_mz_partial_staged(base, load_sweep, camber_sweep, fy_coefficients, ro) -> MzFitResult:
    """Base+dIA fit jointly against {base, camber_sweep}; dFz fit
    afterward against load_sweep exactly as production does, frozen from
    the new Base-stage values. See module docstring for the motivation.
    """
    fz0_prime = base.fz_n
    coeffs_values = dict(_MZ_P0)
    coeffs_values["Hz4"] = 0.0
    coeffs_values["Dz9"] = 0.0
    coeffs_values["Dz11"] = 0.0

    # Stage 1: Base + dIA jointly, against the reference-load conditions
    # (zero camber + every tested camber) -- the camber dimension, fit as
    # one problem instead of Base-then-dIA.
    base_dia_fields = _BASE_FIELDS + _DIA_FIELDS
    base_dia_bounds = _BASE_BOUNDS + _DIA_BOUNDS
    free_fields, free_bounds, fixed_from_bounds = split_fixed_fields(base_dia_fields, base_dia_bounds, coeffs_values)
    coeffs_values.update(fixed_from_bounds)
    camber_points = [base] + list(camber_sweep)
    camber_fy_derived = _fy_derived(camber_points, fz0_prime, fy_coefficients)
    fixed = {k: v for k, v in coeffs_values.items() if k not in free_fields}
    coeffs_values.update(
        _fit_stage(free_fields, free_bounds, coeffs_values, camber_points, camber_fy_derived, fz0_prime, ro, fixed)
    )
    base_fy_derived = _fy_derived([base], fz0_prime, fy_coefficients)
    base_fit_mz_nm = _eval_mz([base], base_fy_derived, fz0_prime, ro, MzCoefficients(**coeffs_values))[0]
    camber_sweep_fy_derived = _fy_derived(camber_sweep, fz0_prime, fy_coefficients)
    camber_sweep_fit_mz_nm = _eval_mz(camber_sweep, camber_sweep_fy_derived, fz0_prime, ro, MzCoefficients(**coeffs_values))

    # Stage 2: dFz against the load sweep, exactly as production -- same
    # fields, same bounds, just starting from the Stage 1 Base values
    # instead of production's Base-stage-alone values.
    load_fy_derived = _fy_derived(load_sweep, fz0_prime, fy_coefficients)
    fixed = {k: v for k, v in coeffs_values.items() if k not in _DFZ_FIELDS}
    coeffs_values.update(
        _fit_stage(_DFZ_FIELDS, _DFZ_BOUNDS, coeffs_values, load_sweep, load_fy_derived, fz0_prime, ro, fixed)
    )
    final_coeffs = MzCoefficients(**coeffs_values)
    load_sweep_fit_mz_nm = _eval_mz(load_sweep, load_fy_derived, fz0_prime, ro, final_coeffs)

    return MzFitResult(
        coefficients=final_coeffs,
        base_fit_mz_nm=base_fit_mz_nm,
        load_sweep_fit_mz_nm=load_sweep_fit_mz_nm,
        camber_sweep_fit_mz_nm=camber_sweep_fit_mz_nm,
    )


def main():
    compound = sys.argv[1] if len(sys.argv) > 1 else "R20"
    diameter_in = float(sys.argv[2]) if len(sys.argv) > 2 else 16.0
    width_in = float(sys.argv[3]) if len(sys.argv) > 3 else 7.5

    samples = _load_tire_samples(compound, diameter_in, width_in)
    staged = run_cornering_fit(samples)

    base = sweep_point_from_aligning_moment(
        next(c.mz_splines for c in staged.load_conditions if c.fz_nom == staged.reference_fz_nom),
        staged.reference_fz_nom, 0.0,
    )
    load_sweep = [sweep_point_from_aligning_moment(c.mz_splines, c.fz_nom, c.ia_nom) for c in staged.load_conditions]
    camber_sweep = [
        sweep_point_from_aligning_moment(c.mz_splines, staged.reference_fz_nom, c.ia_nom)
        for c in staged.camber_conditions
    ]
    ro = 9 * 0.0254

    partial_mz = fit_mz_partial_staged(base, load_sweep, camber_sweep, staged.fy.coefficients, ro)
    partial_result = replace(staged, mz=partial_mz)

    staged_table = fit_quality_table(staged)
    partial_table = fit_quality_table(partial_result)
    staged_mz = staged_table[staged_table["quantity"] == "Mz"].set_index("condition")
    partial_mz_table = partial_table[partial_table["quantity"] == "Mz"].set_index("condition")

    print(f"\nMz fit quality: staged (production) vs. partial-staged (Base+dIA joint), {compound} {diameter_in}x{width_in}")
    print(f"{'condition':<14}{'staged R2':>14}{'partial R2':>14}{'staged RMSE':>14}{'partial RMSE':>14}")
    for condition in staged_mz.index:
        s, p = staged_mz.loc[condition], partial_mz_table.loc[condition]
        print(f"{condition:<14}{s.r_squared:>14.4f}{p.r_squared:>14.4f}{s.rmse:>14.3f}{p.rmse:>14.3f}")

    OUTPUT_DIR.mkdir(exist_ok=True)
    _plot_comparison(staged, partial_result, compound, diameter_in, width_in)
    _plot_with_raw_data(staged, partial_result, compound, diameter_in, width_in)


_PALETTE = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf"]


def _plot_comparison(staged, partial_result, compound, diameter_in, width_in):
    ftlb = 1 / (0.3048 * 4.448)
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Load sweep", "Camber sweep"))

    for col, conditions, staged_fits, partial_fits, label_fn in [
        (1, staged.load_conditions, staged.mz.load_sweep_fit_mz_nm, partial_result.mz.load_sweep_fit_mz_nm,
         lambda c: f"Fz={c.fz_nom:g} lbf"),
        (2, staged.camber_conditions, staged.mz.camber_sweep_fit_mz_nm, partial_result.mz.camber_sweep_fit_mz_nm,
         lambda c: f"IA={c.ia_nom:g} deg"),
    ]:
        for i, (condition, staged_fit, partial_fit) in enumerate(zip(conditions, staged_fits, partial_fits)):
            color = _PALETTE[i % len(_PALETTE)]
            label = label_fn(condition)
            sa_deg = condition.mz_splines.sa_grid_deg
            fig.add_trace(
                go.Scatter(x=sa_deg, y=condition.mz_splines.mz, mode="lines", name=f"{label} smoothed",
                           line=dict(color=color, width=1, dash="dot"), opacity=0.4, legendgroup=label),
                row=1, col=col,
            )
            fig.add_trace(
                go.Scatter(x=sa_deg, y=staged_fit * ftlb, mode="lines", name=f"{label} staged",
                           line=dict(color=color, width=1.5, dash="dash"), legendgroup=label),
                row=1, col=col,
            )
            fig.add_trace(
                go.Scatter(x=sa_deg, y=partial_fit * ftlb, mode="lines", name=f"{label} partial-staged",
                           line=dict(color=color, width=2), legendgroup=label),
                row=1, col=col,
            )
        fig.update_xaxes(title_text="Slip angle (deg)", row=1, col=col)
        fig.update_yaxes(title_text="Mz (ft-lb)", row=1, col=col)

    fig.update_layout(
        title=(
            f"{compound} {diameter_in:g}x{width_in:g}: staged (dashed) vs. partial-staged "
            "(solid, Base+dIA fit jointly) Mz fit; dotted = smoothed data"
        ),
        width=1400, height=600,
    )
    out_path = OUTPUT_DIR / f"mz_partial_staged_vs_staged_{compound}_{diameter_in:g}x{width_in:g}.png"
    fig.write_image(out_path, scale=2)
    print(f"\nSaved plot to {out_path}")


def _plot_with_raw_data(staged, partial_result, compound, diameter_in, width_in):
    """Partial-staged fit curve overlaid directly on the raw (pre-
    smoothing) measured samples -- the sanity check of whether the fit
    tracks the actual data, not just the smoothed curve it was fit to.
    """
    ftlb = 1 / (0.3048 * 4.448)
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Load sweep", "Camber sweep"))

    for col, conditions, partial_fits, label_fn in [
        (1, staged.load_conditions, partial_result.mz.load_sweep_fit_mz_nm, lambda c: f"Fz={c.fz_nom:g} lbf"),
        (2, staged.camber_conditions, partial_result.mz.camber_sweep_fit_mz_nm, lambda c: f"IA={c.ia_nom:g} deg"),
    ]:
        for i, (condition, partial_fit) in enumerate(zip(conditions, partial_fits)):
            color = _PALETTE[i % len(_PALETTE)]
            label = label_fn(condition)
            fig.add_trace(
                go.Scatter(
                    x=condition.samples["SA"], y=condition.samples["MZ"], mode="markers",
                    name=f"{label} raw", marker=dict(size=3, opacity=0.35, color=color), legendgroup=label,
                ),
                row=1, col=col,
            )
            fig.add_trace(
                go.Scatter(x=condition.mz_splines.sa_grid_deg, y=partial_fit * ftlb, mode="lines",
                           name=f"{label} partial-staged", line=dict(color=color, width=2.5), legendgroup=label),
                row=1, col=col,
            )
        fig.update_xaxes(title_text="Slip angle (deg)", row=1, col=col)
        fig.update_yaxes(title_text="Mz (ft-lb)", row=1, col=col)

    fig.update_layout(
        title=f"{compound} {diameter_in:g}x{width_in:g}: partial-staged Mz fit over raw measured data",
        width=1400, height=600,
    )
    out_path = OUTPUT_DIR / f"mz_partial_staged_with_raw_{compound}_{diameter_in:g}x{width_in:g}.png"
    fig.write_image(out_path, scale=2)
    print(f"Saved plot to {out_path}")


if __name__ == "__main__":
    main()
