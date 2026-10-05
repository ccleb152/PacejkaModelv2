"""Experiment: the same "partial staged" hybrid that worked for Mz
(see mz_partial_staged_fit.py), applied to Fy -- keep the production dFz
(load-sweep) stage exactly as it is, but fit Base and dIA jointly against
the reference condition plus the full camber sweep.

Motivation: fy_joint_vs_staged_fit.py showed that *fully* joint fitting
makes Fy worse across the board, because Fy's staged fit is already
excellent (unlike Mz's, where the camber sweep specifically was broken)
-- full joint fitting had nothing to gain and real room to lose by
putting the load sweep into the same unweighted objective as everything
else. The partial-staged hybrid never does that: the load sweep keeps
its own dedicated, unchanged dFz stage, exactly like production. This
script checks whether that matters here too -- does the partial hybrid
avoid the regression that sank the full joint fit, and does it find any
of the same kind of win it found for Mz (or confirm there's nothing to
fix on this tire's Fy data)?

This does NOT modify pacejka/fitters/fy.py or anything the deployed app
uses -- it imports that module's field/bound tables for a fair
side-by-side comparison, and pacejka.model's public fy_pure/
FyCoefficients to run its own independent optimization.

Usage:
    python research/fy_partial_staged_fit.py [compound] [diameter_in] [width_in]

Defaults to the bundled R20 16x7.5 (same tire as the other experiments).
Writes a comparison plot to research/output/.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pacejka.fitting import fit_stage, split_fixed_fields
from pacejka.fitters.fy import (
    _BASE_BOUNDS,
    _BASE_FIELDS,
    _DFZ_FIELDS,
    _DIA_BOUNDS,
    _DIA_FIELDS,
    _P0,
    FyFitResult,
    LBF_TO_N,
    sweep_point_from_alpha_sweep,
)
from pacejka.io.tire_catalog import load_combined_round, scan_raw_data_folder
from pacejka.model import fy_pure, FyCoefficients
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


def _fit_fy_stage(field_names, x0, points, fz0_prime, fixed_values, bounds=None, robust=False):
    """Fy-specific residual closure over pacejka.fitting.fit_stage --
    same mechanics pacejka.fitters.fy's own (private) _fit_fy_stage uses,
    written locally rather than imported, since it's a few lines and this
    script already avoids importing other modules' private functions
    (only their field/bound tables, for a fair comparison)."""
    alpha_rad = np.concatenate([p.alpha_rad for p in points])
    fz_n = np.concatenate([np.full_like(p.alpha_rad, p.fz_n) for p in points])
    gamma_star = np.concatenate([np.full_like(p.alpha_rad, p.gamma_star) for p in points])
    target_fy_n = np.concatenate([p.fy_n for p in points])

    def residuals(x):
        values = dict(fixed_values)
        values.update(zip(field_names, x))
        fyo, _ = fy_pure(fz_n, fz0_prime, gamma_star, alpha_rad, FyCoefficients(**values))
        return fyo - target_fy_n

    fitted_x = fit_stage(residuals, x0, bounds=bounds, robust=robust)
    return dict(zip(field_names, fitted_x))


def fit_fy_partial_staged(base, load_sweep, camber_sweep) -> FyFitResult:
    """Base+dIA fit jointly against {base, camber_sweep}; dFz fit
    afterward against load_sweep exactly as production does (unbounded,
    robust loss), frozen from the new Base-stage values.
    """
    fz0_prime = base.fz_n
    coeffs_values = dict(_P0)
    coeffs_values["Ky7"] = 0.0
    coeffs_values["Vsy4"] = 0.0

    # Stage 1: Base + dIA jointly, against the reference-load conditions
    # (zero camber + every tested camber).
    base_dia_fields = _BASE_FIELDS + _DIA_FIELDS
    base_dia_bounds = _BASE_BOUNDS + _DIA_BOUNDS
    free_fields, free_bounds, fixed_from_bounds = split_fixed_fields(base_dia_fields, base_dia_bounds, coeffs_values)
    coeffs_values.update(fixed_from_bounds)
    camber_points = [base] + list(camber_sweep)
    x0 = [coeffs_values[name] for name in free_fields]
    fixed = {k: v for k, v in coeffs_values.items() if k not in free_fields}
    coeffs_values.update(_fit_fy_stage(free_fields, x0, camber_points, fz0_prime, fixed, bounds=free_bounds))
    base_fit_fy_n, _ = fy_pure(base.fz_n, fz0_prime, base.gamma_star, base.alpha_rad, FyCoefficients(**coeffs_values))
    camber_sweep_fit_fy_n = [
        fy_pure(p.fz_n, fz0_prime, p.gamma_star, p.alpha_rad, FyCoefficients(**coeffs_values))[0] for p in camber_sweep
    ]

    # Stage 2: dFz against the load sweep, exactly as production --
    # unconstrained (bounds=None) with robust loss, same as
    # pacejka.fitters.fy.fit_fy_coefficients's own dFz stage. Only the
    # starting point (Stage 1's Base values) differs from production.
    x0 = [coeffs_values[name] for name in _DFZ_FIELDS]
    fixed = {k: v for k, v in coeffs_values.items() if k not in _DFZ_FIELDS}
    coeffs_values.update(_fit_fy_stage(_DFZ_FIELDS, x0, load_sweep, fz0_prime, fixed, bounds=None, robust=True))
    final_coeffs = FyCoefficients(**coeffs_values)
    load_sweep_fit_fy_n = [fy_pure(p.fz_n, fz0_prime, p.gamma_star, p.alpha_rad, final_coeffs)[0] for p in load_sweep]

    return FyFitResult(
        coefficients=final_coeffs,
        base_fit_fy_n=base_fit_fy_n,
        load_sweep_fit_fy_n=load_sweep_fit_fy_n,
        camber_sweep_fit_fy_n=camber_sweep_fit_fy_n,
    )


def main():
    compound = sys.argv[1] if len(sys.argv) > 1 else "R20"
    diameter_in = float(sys.argv[2]) if len(sys.argv) > 2 else 16.0
    width_in = float(sys.argv[3]) if len(sys.argv) > 3 else 7.5

    samples = _load_tire_samples(compound, diameter_in, width_in)
    staged = run_cornering_fit(samples)

    base = sweep_point_from_alpha_sweep(
        next(c.fy_splines for c in staged.load_conditions if c.fz_nom == staged.reference_fz_nom),
        staged.reference_fz_nom, 0.0,
    )
    load_sweep = [sweep_point_from_alpha_sweep(c.fy_splines, c.fz_nom, c.ia_nom) for c in staged.load_conditions]
    camber_sweep = [
        sweep_point_from_alpha_sweep(c.fy_splines, staged.reference_fz_nom, c.ia_nom)
        for c in staged.camber_conditions
    ]

    partial_fy = fit_fy_partial_staged(base, load_sweep, camber_sweep)
    partial_result = replace(staged, fy=partial_fy)

    staged_table = fit_quality_table(staged)
    partial_table = fit_quality_table(partial_result)
    staged_fy = staged_table[staged_table["quantity"] == "Fy"].set_index("condition")
    partial_fy_table = partial_table[partial_table["quantity"] == "Fy"].set_index("condition")

    print(f"\nFy fit quality: staged (production) vs. partial-staged (Base+dIA joint), {compound} {diameter_in}x{width_in}")
    print(f"{'condition':<14}{'staged R2':>14}{'partial R2':>14}{'staged RMSE':>14}{'partial RMSE':>14}")
    for condition in staged_fy.index:
        s, p = staged_fy.loc[condition], partial_fy_table.loc[condition]
        print(f"{condition:<14}{s.r_squared:>14.4f}{p.r_squared:>14.4f}{s.rmse:>14.3f}{p.rmse:>14.3f}")

    OUTPUT_DIR.mkdir(exist_ok=True)
    _plot_comparison(staged, partial_result, compound, diameter_in, width_in)
    _plot_with_raw_data(staged, partial_result, compound, diameter_in, width_in)


_PALETTE = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf"]


def _plot_comparison(staged, partial_result, compound, diameter_in, width_in):
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Load sweep", "Camber sweep"))

    for col, conditions, staged_fits, partial_fits, label_fn in [
        (1, staged.load_conditions, staged.fy.load_sweep_fit_fy_n, partial_result.fy.load_sweep_fit_fy_n,
         lambda c: f"Fz={c.fz_nom:g} lbf"),
        (2, staged.camber_conditions, staged.fy.camber_sweep_fit_fy_n, partial_result.fy.camber_sweep_fit_fy_n,
         lambda c: f"IA={c.ia_nom:g} deg"),
    ]:
        for i, (condition, staged_fit, partial_fit) in enumerate(zip(conditions, staged_fits, partial_fits)):
            color = _PALETTE[i % len(_PALETTE)]
            label = label_fn(condition)
            sa_deg = condition.fy_splines.sa_grid_deg
            fig.add_trace(
                go.Scatter(x=sa_deg, y=condition.fy_splines.fy, mode="lines", name=f"{label} smoothed",
                           line=dict(color=color, width=1, dash="dot"), opacity=0.4, legendgroup=label),
                row=1, col=col,
            )
            fig.add_trace(
                go.Scatter(x=sa_deg, y=staged_fit / LBF_TO_N, mode="lines", name=f"{label} staged",
                           line=dict(color=color, width=1.5, dash="dash"), legendgroup=label),
                row=1, col=col,
            )
            fig.add_trace(
                go.Scatter(x=sa_deg, y=partial_fit / LBF_TO_N, mode="lines", name=f"{label} partial-staged",
                           line=dict(color=color, width=2), legendgroup=label),
                row=1, col=col,
            )
        fig.update_xaxes(title_text="Slip angle (deg)", row=1, col=col)
        fig.update_yaxes(title_text="Fy (lbf)", row=1, col=col)

    fig.update_layout(
        title=(
            f"{compound} {diameter_in:g}x{width_in:g}: staged (dashed) vs. partial-staged "
            "(solid, Base+dIA fit jointly) Fy fit; dotted = smoothed data"
        ),
        width=1400, height=600,
    )
    out_path = OUTPUT_DIR / f"fy_partial_staged_vs_staged_{compound}_{diameter_in:g}x{width_in:g}.png"
    fig.write_image(out_path, scale=2)
    print(f"\nSaved plot to {out_path}")


def _plot_with_raw_data(staged, partial_result, compound, diameter_in, width_in):
    """Partial-staged fit curve overlaid directly on the raw (pre-
    smoothing) measured samples -- the sanity check of whether the fit
    tracks the actual data, not just the smoothed curve it was fit to.
    """
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Load sweep", "Camber sweep"))

    for col, conditions, partial_fits, label_fn in [
        (1, staged.load_conditions, partial_result.fy.load_sweep_fit_fy_n, lambda c: f"Fz={c.fz_nom:g} lbf"),
        (2, staged.camber_conditions, partial_result.fy.camber_sweep_fit_fy_n, lambda c: f"IA={c.ia_nom:g} deg"),
    ]:
        for i, (condition, partial_fit) in enumerate(zip(conditions, partial_fits)):
            color = _PALETTE[i % len(_PALETTE)]
            label = label_fn(condition)
            fig.add_trace(
                go.Scatter(
                    x=condition.samples["SA"], y=condition.samples["FY"], mode="markers",
                    name=f"{label} raw", marker=dict(size=3, opacity=0.35, color=color), legendgroup=label,
                ),
                row=1, col=col,
            )
            fig.add_trace(
                go.Scatter(x=condition.fy_splines.sa_grid_deg, y=partial_fit / LBF_TO_N, mode="lines",
                           name=f"{label} partial-staged", line=dict(color=color, width=2.5), legendgroup=label),
                row=1, col=col,
            )
        fig.update_xaxes(title_text="Slip angle (deg)", row=1, col=col)
        fig.update_yaxes(title_text="Fy (lbf)", row=1, col=col)

    fig.update_layout(
        title=f"{compound} {diameter_in:g}x{width_in:g}: partial-staged Fy fit over raw measured data",
        width=1400, height=600,
    )
    out_path = OUTPUT_DIR / f"fy_partial_staged_with_raw_{compound}_{diameter_in:g}x{width_in:g}.png"
    fig.write_image(out_path, scale=2)
    print(f"Saved plot to {out_path}")


if __name__ == "__main__":
    main()
