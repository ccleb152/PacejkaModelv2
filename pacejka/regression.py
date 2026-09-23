"""Goodness-of-fit diagnostics for one cornering fit.

Not a MATLAB port -- the original tool has no equivalent (it plots the
fit and leaves the viewer to eyeball it, nothing more). Per CLAUDE.md
quirk #18's own golden-testing rule -- "compare fit quality (residuals/
R^2) against the same input data" -- these functions compare each fitted
Pacejka curve against the *smoothed spline* curve it was actually fit to
(the same target `pacejka.fitting.fit_stage`'s residual function
minimizes against), not the raw noisy samples: that's the right
comparison for "did the optimizer converge to a curve that matches the
measured shape," independent of how noisy the raw telemetry happened to
be for that run.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

import numpy as np
import pandas as pd

from pacejka.fitters.fy import LBF_TO_N
from pacejka.fitters.mz import FTLB_TO_NM
from pacejka.pipeline import CorneringFitResult


@dataclass(frozen=True)
class FitQualityRow:
    """Goodness-of-fit metrics for one Pacejka fit curve against the
    smoothed measured curve it was fit to, for one nominal condition.

    `r_squared` is the standard coefficient of determination against the
    smoothed curve's own mean (1.0 = exact match; 0.0 = no better than a
    flat line at the mean; negative = worse than that flat line -- a
    clear red flag). `rmse`/`mae`/`max_abs_error` are in the quantity's
    native unit (lbf for Fy, ft-lb for Mz), matching the app's plots.
    """

    quantity: str  # "Fy" or "Mz"
    sweep: str  # "load" or "camber"
    condition: str  # e.g. "Fz=150 lbf" or "IA=2 deg"
    n_points: int
    r_squared: float
    rmse: float
    mae: float
    max_abs_error: float


def _fit_quality_row(quantity: str, sweep: str, condition: str, actual, predicted) -> FitQualityRow:
    residuals = actual - predicted
    sse = float(np.sum(residuals**2))
    sst = float(np.sum((actual - np.mean(actual)) ** 2))
    r_squared = 1.0 - sse / sst if sst > 0 else float("nan")
    return FitQualityRow(
        quantity=quantity,
        sweep=sweep,
        condition=condition,
        n_points=len(actual),
        r_squared=r_squared,
        rmse=float(np.sqrt(np.mean(residuals**2))),
        mae=float(np.mean(np.abs(residuals))),
        max_abs_error=float(np.max(np.abs(residuals))),
    )


def fit_quality_rows(result: CorneringFitResult) -> list[FitQualityRow]:
    """Goodness-of-fit rows for every condition in one cornering fit: Fy
    and Mz, across both the load sweep and the camber sweep -- the same
    condition groupings already shown as overlay plots in the app.
    """
    rows: list[FitQualityRow] = []

    for condition, fit_n in zip(result.load_conditions, result.fy.load_sweep_fit_fy_n):
        rows.append(
            _fit_quality_row(
                "Fy", "load", f"Fz={condition.fz_nom:g} lbf",
                condition.fy_splines.fy, fit_n / LBF_TO_N,
            )
        )
    for condition, fit_n in zip(result.camber_conditions, result.fy.camber_sweep_fit_fy_n):
        rows.append(
            _fit_quality_row(
                "Fy", "camber", f"IA={condition.ia_nom:g} deg",
                condition.fy_splines.fy, fit_n / LBF_TO_N,
            )
        )
    for condition, fit_nm in zip(result.load_conditions, result.mz.load_sweep_fit_mz_nm):
        rows.append(
            _fit_quality_row(
                "Mz", "load", f"Fz={condition.fz_nom:g} lbf",
                condition.mz_splines.mz, fit_nm / FTLB_TO_NM,
            )
        )
    for condition, fit_nm in zip(result.camber_conditions, result.mz.camber_sweep_fit_mz_nm):
        rows.append(
            _fit_quality_row(
                "Mz", "camber", f"IA={condition.ia_nom:g} deg",
                condition.mz_splines.mz, fit_nm / FTLB_TO_NM,
            )
        )
    return rows


def fit_quality_table(result: CorneringFitResult) -> pd.DataFrame:
    """`fit_quality_rows` as a DataFrame, for display or CSV export."""
    return pd.DataFrame([dataclasses.asdict(row) for row in fit_quality_rows(result)])
