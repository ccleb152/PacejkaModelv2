"""Orchestration for the cornering (Fy/Mz) fitting pipeline.

Replaces `tiremodelV2.m`'s role (MIGRATION_PLAN.md step 9): given one
loaded raw TTC round and a handful of top-level settings (pressure, test
speed), runs the full segment -> smooth -> fit pipeline across every
tested load and camber angle automatically, rather than requiring the
per-file hardcoded sweeps (`Fz_nom = [50]`, `gamma_vals = 2`, ...) that
quirks #7/#11/#14/#15 are all instances of. This is the piece that
actually makes the multi-load-sweep decision in CLAUDE.md's roadmap real.

Deliberately has no Streamlit/plotting dependency -- the app layer calls
this and renders `CorneringFitResult`, this module just computes it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pandas as pd

from pacejka.detection import detect_camber_levels, detect_fz_levels
from pacejka.fitters.fy import (
    AlphaSweepSplines,
    FyFitResult,
    fit_alpha_sweep,
    fit_fy_coefficients,
    sweep_point_from_alpha_sweep,
)
from pacejka.fitters.mz import (
    AligningMomentSpline,
    MzFitResult,
    fit_aligning_moment,
    fit_mz_coefficients,
    sweep_point_from_aligning_moment,
)
from pacejka.segmenting import segment_condition


@dataclass(frozen=True)
class ConditionResult:
    """Everything computed for one nominal (Fz, IA) condition -- the raw
    segmented samples and the smoothed alpha-sweep curves -- for
    diagnostic plotting (raw scatter + smoothed spline; the Pacejka fit
    curve itself lives in the `FyFitResult`/`MzFitResult`, evaluated at
    each of these same conditions in the same order).
    """

    fz_nom: float
    ia_nom: float
    samples: pd.DataFrame
    fy_splines: AlphaSweepSplines
    mz_splines: AligningMomentSpline


@dataclass(frozen=True)
class CorneringFitResult:
    """The complete result of one cornering-pipeline run."""

    reference_fz_nom: float
    load_conditions: list[ConditionResult]
    camber_conditions: list[ConditionResult]
    fy: FyFitResult
    mz: MzFitResult


def _process_condition(samples, fz_nom, ia_nom, p_nom, v_nom, test_type) -> ConditionResult:
    segment = segment_condition(
        samples, fz_nom=fz_nom, p_nom=p_nom, ia_nom=ia_nom, sa_nom=0.0, v_nom=v_nom, test_type=test_type
    )
    return ConditionResult(
        fz_nom=fz_nom,
        ia_nom=ia_nom,
        samples=segment,
        fy_splines=fit_alpha_sweep(segment),
        mz_splines=fit_aligning_moment(segment),
    )


def run_cornering_fit(
    samples: pd.DataFrame,
    p_nom: float = 12.0,
    v_nom: float = 25.0,
    reference_fz_nom: float | None = None,
    fz_noms: Sequence[float] | None = None,
    ia_degs: Sequence[float] | None = None,
    test_type: str = "Cornering",
) -> CorneringFitResult:
    """Run the full cornering (Fy + Mz) fitting pipeline on one raw round.

    `fz_noms`/`ia_degs` default to auto-detection (`pacejka.detection`)
    when not given -- pass them explicitly to override detection (e.g. a
    level was wrongly excluded/included) without re-running it.
    `reference_fz_nom` (the Base-stage anchor, Fz0') defaults to the
    middle detected/given load; it must be one of `fz_noms`. Zero camber
    must be among `ia_degs` -- it's the anchor the load sweep is done at.

    Raises `ValueError` if no loads or cambers can be found/used -- this
    is meant to surface as an actionable message in the Streamlit UI, not
    to be silently worked around.
    """
    if fz_noms is None:
        fz_noms = detect_fz_levels(samples, p_nom=p_nom, v_nom=v_nom, test_type=test_type)
    fz_noms = sorted(fz_noms)
    if not fz_noms:
        raise ValueError("No tested load levels were detected (or given) -- nothing to fit.")

    if reference_fz_nom is None:
        reference_fz_nom = fz_noms[len(fz_noms) // 2]
    elif reference_fz_nom not in fz_noms:
        raise ValueError(f"reference_fz_nom={reference_fz_nom} is not among the tested loads {fz_noms}.")

    if ia_degs is None:
        ia_degs = detect_camber_levels(samples, fz_nom=reference_fz_nom, p_nom=p_nom, v_nom=v_nom, test_type=test_type)
    ia_degs = sorted(ia_degs)
    if not ia_degs:
        raise ValueError(f"No tested camber levels were detected (or given) at Fz_nom={reference_fz_nom}.")
    if 0.0 not in ia_degs:
        raise ValueError("Zero camber (0 deg) must be among the tested camber levels -- it anchors the load sweep.")

    load_conditions = [_process_condition(samples, fz, 0.0, p_nom, v_nom, test_type) for fz in fz_noms]
    camber_conditions = [_process_condition(samples, reference_fz_nom, ia, p_nom, v_nom, test_type) for ia in ia_degs]

    fy_base = sweep_point_from_alpha_sweep(
        next(c.fy_splines for c in load_conditions if c.fz_nom == reference_fz_nom), reference_fz_nom, 0.0
    )
    fy_load_sweep = [sweep_point_from_alpha_sweep(c.fy_splines, c.fz_nom, 0.0) for c in load_conditions]
    fy_camber_sweep = [
        sweep_point_from_alpha_sweep(c.fy_splines, reference_fz_nom, c.ia_nom) for c in camber_conditions
    ]
    fy_result = fit_fy_coefficients(fy_base, fy_load_sweep, fy_camber_sweep)

    mz_base = sweep_point_from_aligning_moment(
        next(c.mz_splines for c in load_conditions if c.fz_nom == reference_fz_nom), reference_fz_nom, 0.0
    )
    mz_load_sweep = [sweep_point_from_aligning_moment(c.mz_splines, c.fz_nom, 0.0) for c in load_conditions]
    mz_camber_sweep = [
        sweep_point_from_aligning_moment(c.mz_splines, reference_fz_nom, c.ia_nom) for c in camber_conditions
    ]
    mz_result = fit_mz_coefficients(mz_base, mz_load_sweep, mz_camber_sweep, fy_result.coefficients)

    return CorneringFitResult(
        reference_fz_nom=reference_fz_nom,
        load_conditions=load_conditions,
        camber_conditions=camber_conditions,
        fy=fy_result,
        mz=mz_result,
    )
