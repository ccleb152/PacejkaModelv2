"""Experiment: same question as mz_joint_vs_staged_fit.py, but for Fy.

Does fitting all Fy coefficients jointly (one simultaneous least-squares
optimization across every tested condition) trend the same way as it did
for Mz -- worse load-sweep accuracy, better camber-sweep accuracy -- or
is that an Mz-specific artifact? See research/OPTIMIZATION_NOTES.md for
the Mz result this is checking against.

Mirrors mz_joint_vs_staged_fit.py's structure and comparison style so the
two are easy to read side by side. Does NOT modify
pacejka/fitters/fy.py or anything the deployed app uses -- it imports
that module's field/bound tables for a fair side-by-side comparison, and
pacejka.model's public fy_pure/FyCoefficients to run its own independent
optimization.

Usage:
    python research/fy_joint_vs_staged_fit.py [compound] [diameter_in] [width_in]

Defaults to the bundled R20 16x7.5 (same tire as the Mz experiment, for
a direct comparison). Writes comparison plots to research/output/.
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


def fit_fy_jointly(base, load_sweep, camber_sweep) -> FyFitResult:
    """All non-deferred Fy coefficients, fit in one simultaneous
    least_squares call against every tested condition at once -- no
    staging, no frozen-from-a-previous-stage coefficients.

    Uses the exact same field/bound tables as the production staged fit
    (imported from pacejka.fitters.fy), so the comparison is apples to
    apples: same coefficients free, same bounds per field, same deferred
    cross term fixed at 0.0, same initial guess. The dFz-stage fields
    (Dy2/Ey2/Hsy2/Vsy2) are unconstrained in production (matching
    MATLAB's nlinfit, which doesn't support bounds) -- given (-inf, inf)
    bounds here for the same reason, not an arbitrary choice. Unlike
    production, this does NOT use robust loss for those fields (plain
    least squares throughout) -- robust-vs-plain loss is a separate
    question from staged-vs-joint, and conflating the two would make it
    unclear which change caused any difference in the result.
    """
    fz0_prime = base.fz_n
    all_points = [base] + list(load_sweep) + list(camber_sweep)

    all_fields = _BASE_FIELDS + _DFZ_FIELDS + _DIA_FIELDS
    all_bounds = _BASE_BOUNDS + tuple((-np.inf, np.inf) for _ in _DFZ_FIELDS) + _DIA_BOUNDS
    free_fields, free_bounds, fixed_from_bounds = split_fixed_fields(all_fields, all_bounds, dict(_P0))
    # Every _P0 field not in free_fields stays fixed at its p0 value --
    # this is how the staged fit leaves the untouched-by-any-stage
    # pressure-sensitivity fields (py1..py5) and the not-yet-reached
    # fields at their initial guess, same mechanism it uses between
    # stages. Ky7/Vsy4 (the deferred cross term) are the one exception:
    # overridden to 0.0 rather than left at p0's never-validated guess
    # (Ky7=2.0), matching FyFitResult's documented behavior.
    fixed_values = {k: v for k, v in _P0.items() if k not in free_fields}
    fixed_values.update(fixed_from_bounds)
    fixed_values["Ky7"] = 0.0
    fixed_values["Vsy4"] = 0.0

    alpha_rad = np.concatenate([p.alpha_rad for p in all_points])
    fz_n = np.concatenate([np.full_like(p.alpha_rad, p.fz_n) for p in all_points])
    gamma_star = np.concatenate([np.full_like(p.alpha_rad, p.gamma_star) for p in all_points])
    target_fy_n = np.concatenate([p.fy_n for p in all_points])

    def residuals(x):
        values = dict(fixed_values)
        values.update(zip(free_fields, x))
        fyo, _ = fy_pure(fz_n, fz0_prime, gamma_star, alpha_rad, FyCoefficients(**values))
        return fyo - target_fy_n

    x0 = [_P0[name] for name in free_fields]
    lb, ub = zip(*free_bounds)
    x0_clipped = np.clip(x0, lb, ub)
    result = least_squares(residuals, x0_clipped, bounds=(lb, ub))

    final_values = dict(fixed_values)
    final_values.update(zip(free_fields, result.x))
    coeffs = FyCoefficients(**final_values)

    base_fit_fy_n, _ = fy_pure(base.fz_n, fz0_prime, base.gamma_star, base.alpha_rad, coeffs)
    load_sweep_fit_fy_n = [fy_pure(p.fz_n, fz0_prime, p.gamma_star, p.alpha_rad, coeffs)[0] for p in load_sweep]
    camber_sweep_fit_fy_n = [fy_pure(p.fz_n, fz0_prime, p.gamma_star, p.alpha_rad, coeffs)[0] for p in camber_sweep]

    return FyFitResult(
        coefficients=coeffs,
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

    joint_fy = fit_fy_jointly(base, load_sweep, camber_sweep)
    joint_result = replace(staged, fy=joint_fy)

    staged_table = fit_quality_table(staged)
    joint_table = fit_quality_table(joint_result)
    staged_fy = staged_table[staged_table["quantity"] == "Fy"].set_index("condition")
    joint_fy_table = joint_table[joint_table["quantity"] == "Fy"].set_index("condition")

    print(f"\nFy fit quality: staged (production) vs. joint, {compound} {diameter_in}x{width_in}")
    print(f"{'condition':<14}{'staged R2':>12}{'joint R2':>12}{'staged RMSE':>14}{'joint RMSE':>12}")
    for condition in staged_fy.index:
        s, j = staged_fy.loc[condition], joint_fy_table.loc[condition]
        print(f"{condition:<14}{s.r_squared:>12.4f}{j.r_squared:>12.4f}{s.rmse:>14.3f}{j.rmse:>12.3f}")

    OUTPUT_DIR.mkdir(exist_ok=True)
    _plot_comparison(staged, joint_result, compound, diameter_in, width_in)


_PALETTE = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf"]


def _plot_comparison(staged, joint_result, compound, diameter_in, width_in):
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Load sweep", "Camber sweep"))

    for col, conditions, staged_fits, joint_fits, label_fn in [
        (1, staged.load_conditions, staged.fy.load_sweep_fit_fy_n, joint_result.fy.load_sweep_fit_fy_n,
         lambda c: f"Fz={c.fz_nom:g} lbf"),
        (2, staged.camber_conditions, staged.fy.camber_sweep_fit_fy_n, joint_result.fy.camber_sweep_fit_fy_n,
         lambda c: f"IA={c.ia_nom:g} deg"),
    ]:
        for i, (condition, staged_fit, joint_fit) in enumerate(zip(conditions, staged_fits, joint_fits)):
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
                go.Scatter(x=sa_deg, y=joint_fit / LBF_TO_N, mode="lines", name=f"{label} joint",
                           line=dict(color=color, width=2), legendgroup=label),
                row=1, col=col,
            )
        fig.update_xaxes(title_text="Slip angle (deg)", row=1, col=col)
        fig.update_yaxes(title_text="Fy (lbf)", row=1, col=col)

    fig.update_layout(
        title=f"{compound} {diameter_in:g}x{width_in:g}: staged (dashed) vs. joint (solid) Fy fit; dotted = smoothed data",
        width=1400, height=600,
    )
    out_path = OUTPUT_DIR / f"fy_joint_vs_staged_{compound}_{diameter_in:g}x{width_in:g}.png"
    fig.write_image(out_path, scale=2)
    print(f"\nSaved plot to {out_path}")


if __name__ == "__main__":
    main()
