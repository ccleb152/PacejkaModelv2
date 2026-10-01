"""Experiment: does fitting all Mz coefficients jointly (one simultaneous
least-squares optimization across every tested condition) beat the
production staged approach (Base -> dFz -> dIA, each stage freezing the
previous stage's coefficients)?

Motivation: the staged approach commits early. The Base stage fits 10
coefficients against *one* reference condition with full freedom, then
the dFz and dIA stages are stuck explaining the rest of the dataset with
only 7 coefficients each, unable to revisit anything the Base stage got
slightly wrong. A joint fit lets every coefficient trade off against
every condition at once, which should in principle do better whenever
the staged split is costing real fit quality (see MODEL_CHANGES.md's
2026-10-01 entry for a case -- the dIA stage -- where more freedom
turned out to make things *worse*, because that stage is genuinely
under-determined; this script is how you'd check whether that's also
true elsewhere, or whether the dFz stage specifically has room to
improve from joint fitting).

This does NOT modify pacejka/fitters/mz.py or anything the deployed app
uses -- it imports that module's field/bound tables for a fair
side-by-side comparison, and pacejka.model's public mz_pure/
MzCoefficients to run its own independent optimization.

Usage:
    python research/mz_joint_vs_staged_fit.py [compound] [diameter_in] [width_in]

Defaults to the bundled R20 16x7.5 (the tire this was first investigated
on). Writes comparison plots to research/output/.
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


def fit_mz_jointly(base, load_sweep, camber_sweep, fy_coefficients, ro) -> MzFitResult:
    """All non-deferred Mz coefficients, fit in one simultaneous
    least_squares call against every tested condition at once -- no
    staging, no frozen-from-a-previous-stage coefficients.

    Uses the exact same field/bound tables as the production staged fit
    (imported from pacejka.fitters.mz) so the comparison is apples to
    apples: same coefficients free, same bounds, same deferred cross
    terms fixed at 0.0, same initial guess per field. The only thing
    that differs is *when* each coefficient is allowed to move.
    """
    fz0_prime = base.fz_n
    all_points = [base] + list(load_sweep) + list(camber_sweep)
    fy_derived = _fy_derived(all_points, fz0_prime, fy_coefficients)

    all_fields = _BASE_FIELDS + _DFZ_FIELDS + _DIA_FIELDS
    all_bounds = _BASE_BOUNDS + _DFZ_BOUNDS + _DIA_BOUNDS
    # Bz4's bounds are a deliberate zero-width (20.0, 20.0) fix (see
    # pacejka/fitters/mz.py) -- scipy.optimize.least_squares requires a
    # strictly increasing bound per parameter, so it has to be pulled out
    # as a fixed value the same way the staged fit does via
    # split_fixed_fields, not left in the free-parameter list.
    free_fields, free_bounds, fixed_from_bounds = split_fixed_fields(all_fields, all_bounds, dict(_MZ_P0))
    fixed_values = {"Hz4": 0.0, "Dz9": 0.0, "Dz11": 0.0, **fixed_from_bounds}

    alpha_rad = np.concatenate([p.alpha_rad for p in all_points])
    fz_n = np.concatenate([np.full_like(p.alpha_rad, p.fz_n) for p in all_points])
    gamma_star = np.concatenate([np.full_like(p.alpha_rad, p.gamma_star) for p in all_points])
    cos_alpha_p = np.concatenate([p.cos_alpha_p for p in all_points])
    target_mz_nm = np.concatenate([p.mz_nm for p in all_points])
    fy_cy = np.concatenate([np.full_like(p.alpha_rad, d[0]) for p, d in zip(all_points, fy_derived)])
    fy_by = np.concatenate([np.full_like(p.alpha_rad, d[1]) for p, d in zip(all_points, fy_derived)])
    s_hf = np.concatenate([np.full_like(p.alpha_rad, d[2]) for p, d in zip(all_points, fy_derived)])
    fy_og0 = np.concatenate([d[3] for d in fy_derived])

    def residuals(x):
        values = dict(fixed_values)
        values.update(zip(free_fields, x))
        mz = mz_pure(fz_n, fz0_prime, ro, gamma_star, alpha_rad, cos_alpha_p, fy_cy, fy_by, s_hf, fy_og0, MzCoefficients(**values))
        return mz - target_mz_nm

    x0 = [_MZ_P0[name] for name in free_fields]
    lb, ub = zip(*free_bounds)
    x0_clipped = np.clip(x0, lb, ub)
    result = least_squares(residuals, x0_clipped, bounds=(lb, ub))

    final_values = dict(fixed_values)
    final_values.update(zip(free_fields, result.x))
    coeffs = MzCoefficients(**final_values)

    load_fy_derived = _fy_derived(load_sweep, fz0_prime, fy_coefficients)
    camber_fy_derived = _fy_derived(camber_sweep, fz0_prime, fy_coefficients)
    base_fy_derived = _fy_derived([base], fz0_prime, fy_coefficients)

    return MzFitResult(
        coefficients=coeffs,
        base_fit_mz_nm=_eval_mz([base], base_fy_derived, fz0_prime, ro, coeffs)[0],
        load_sweep_fit_mz_nm=_eval_mz(load_sweep, load_fy_derived, fz0_prime, ro, coeffs),
        camber_sweep_fit_mz_nm=_eval_mz(camber_sweep, camber_fy_derived, fz0_prime, ro, coeffs),
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

    joint_mz = fit_mz_jointly(base, load_sweep, camber_sweep, staged.fy.coefficients, ro)
    joint_result = replace(staged, mz=joint_mz)

    staged_table = fit_quality_table(staged)
    joint_table = fit_quality_table(joint_result)
    staged_mz = staged_table[staged_table["quantity"] == "Mz"].set_index("condition")
    joint_mz_table = joint_table[joint_table["quantity"] == "Mz"].set_index("condition")

    print(f"\nMz fit quality: staged (production) vs. joint, {compound} {diameter_in}x{width_in}")
    print(f"{'condition':<14}{'staged R2':>12}{'joint R2':>12}{'staged RMSE':>14}{'joint RMSE':>12}")
    for condition in staged_mz.index:
        s, j = staged_mz.loc[condition], joint_mz_table.loc[condition]
        print(f"{condition:<14}{s.r_squared:>12.4f}{j.r_squared:>12.4f}{s.rmse:>14.3f}{j.rmse:>12.3f}")

    OUTPUT_DIR.mkdir(exist_ok=True)
    _plot_comparison(staged, joint_result, compound, diameter_in, width_in)


_PALETTE = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf"]


def _plot_comparison(staged, joint_result, compound, diameter_in, width_in):
    ftlb = 1 / (0.3048 * 4.448)
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Load sweep", "Camber sweep"))

    for col, conditions, staged_fits, joint_fits, label_fn in [
        (1, staged.load_conditions, staged.mz.load_sweep_fit_mz_nm, joint_result.mz.load_sweep_fit_mz_nm,
         lambda c: f"Fz={c.fz_nom:g} lbf"),
        (2, staged.camber_conditions, staged.mz.camber_sweep_fit_mz_nm, joint_result.mz.camber_sweep_fit_mz_nm,
         lambda c: f"IA={c.ia_nom:g} deg"),
    ]:
        for i, (condition, staged_fit, joint_fit) in enumerate(zip(conditions, staged_fits, joint_fits)):
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
                go.Scatter(x=sa_deg, y=joint_fit * ftlb, mode="lines", name=f"{label} joint",
                           line=dict(color=color, width=2), legendgroup=label),
                row=1, col=col,
            )
        fig.update_xaxes(title_text="Slip angle (deg)", row=1, col=col)
        fig.update_yaxes(title_text="Mz (ft-lb)", row=1, col=col)

    fig.update_layout(
        title=f"{compound} {diameter_in:g}x{width_in:g}: staged (dashed) vs. joint (solid) Mz fit; dotted = smoothed data",
        width=1400, height=600,
    )
    out_path = OUTPUT_DIR / f"mz_joint_vs_staged_{compound}_{diameter_in:g}x{width_in:g}.png"
    fig.write_image(out_path, scale=2)
    print(f"\nSaved plot to {out_path}")


if __name__ == "__main__":
    main()
