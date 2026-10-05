"""Orchestration for the longitudinal (Fx, pure-slip only) fitting pipeline.

Mirrors `pacejka.pipeline`'s cornering orchestration (MIGRATION_PLAN.md
step 9's role, extended to Phase 2): given one loaded raw TTC
BrakeDrive/Braking round and a handful of top-level settings, runs the
full segment -> smooth -> fit pipeline across every tested load and
camber angle automatically, the same multi-load-sweep principle as
`run_cornering_fit` (see CLAUDE.md's roadmap), rather than the original's
per-file hardcoded sweeps.

Scope note: pure-slip Fx only -- see pacejka.fitters.fx's module
docstring for why the combined-slip stages are deferred.

Deliberately has no Streamlit/plotting dependency -- the app layer calls
this and renders `LongitudinalFitResult`, this module just computes it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pandas as pd

from pacejka.detection import detect_camber_levels, detect_fz_levels
from pacejka.fitters.fx import (
    FxFitResult,
    KappaSweepSplines,
    fit_fx_coefficients,
    fit_kappa_sweep,
    sweep_point_from_kappa_sweep,
    trim_to_raw_domain,
)
from pacejka.quality import QualityIssue, check_condition_quality, check_round_quality
from pacejka.segmenting import segment_condition


@dataclass(frozen=True)
class LongitudinalConditionResult:
    """Everything computed for one nominal (Fz, IA) condition -- the raw
    segmented samples and the smoothed kappa-sweep curves -- for
    diagnostic plotting (raw scatter + smoothed spline; the Pacejka fit
    curve itself lives in the `FxFitResult`, evaluated at each of these
    same conditions in the same order).
    """

    fz_nom: float
    ia_nom: float
    samples: pd.DataFrame
    fx_splines: KappaSweepSplines
    quality_issues: list[QualityIssue]


@dataclass(frozen=True)
class LongitudinalFitResult:
    """The complete result of one longitudinal (pure-slip Fx) pipeline run."""

    reference_fz_nom: float
    load_conditions: list[LongitudinalConditionResult]
    camber_conditions: list[LongitudinalConditionResult]
    fx: FxFitResult
    quality_issues: list[QualityIssue]


def _process_condition(samples, fz_nom, ia_nom, p_nom, v_nom) -> LongitudinalConditionResult:
    segment = segment_condition(
        samples, fz_nom=fz_nom, p_nom=p_nom, ia_nom=ia_nom, sa_nom=0.0, v_nom=v_nom, test_type="Braking"
    )
    # Check quality *before* spline-fitting -- see pacejka.pipeline's
    # equivalent for why (a too-sparse segment can crash deep inside
    # csaps rather than fail cleanly).
    issues = check_condition_quality(segment, fz_nom, ia_nom, test_type="Braking")
    errors = [issue for issue in issues if issue.severity == "error"]
    if errors:
        raise ValueError(" ".join(issue.message for issue in errors))

    # Trim the spline evaluation to this condition's own real SL domain
    # before anything downstream (fitting or quality scoring) sees it --
    # see pacejka.fitters.fx.trim_to_raw_domain's docstring for why: the
    # fixed SL_GRID can extend past what a specific condition's raw data
    # actually covers, and csaps extrapolates unreliably past a spline's
    # fitted domain.
    sl = segment["SL"]
    splines = trim_to_raw_domain(fit_kappa_sweep(segment), float(sl.min()), float(sl.max()))

    return LongitudinalConditionResult(
        fz_nom=fz_nom,
        ia_nom=ia_nom,
        samples=segment,
        fx_splines=splines,
        quality_issues=issues,
    )


def run_longitudinal_fit(
    samples: pd.DataFrame,
    p_nom: float = 12.0,
    v_nom: float = 25.0,
    reference_fz_nom: float | None = None,
    fz_noms: Sequence[float] | None = None,
    ia_degs: Sequence[float] | None = None,
) -> LongitudinalFitResult:
    """Run the pure-slip Fx fitting pipeline on one raw Braking round.

    `fz_noms`/`ia_degs` default to auto-detection (`pacejka.detection`,
    `test_type="Braking"`) when not given. `reference_fz_nom` (the
    Base-stage anchor, Fz0') defaults to the middle detected/given load;
    it must be one of `fz_noms`. Zero camber must be among `ia_degs` --
    it's the anchor the load sweep is done at.

    Raises `ValueError` under the same conditions as
    `pacejka.pipeline.run_cornering_fit` -- see its docstring.
    """
    round_issues = check_round_quality(samples, test_type="Braking")
    round_errors = [issue for issue in round_issues if issue.severity == "error"]
    if round_errors:
        raise ValueError(" ".join(issue.message for issue in round_errors))

    if fz_noms is None:
        fz_noms = detect_fz_levels(samples, p_nom=p_nom, v_nom=v_nom, test_type="Braking")
    fz_noms = sorted(fz_noms)
    if not fz_noms:
        raise ValueError("No tested load levels were detected (or given) -- nothing to fit.")

    if reference_fz_nom is None:
        reference_fz_nom = fz_noms[len(fz_noms) // 2]
    elif reference_fz_nom not in fz_noms:
        raise ValueError(f"reference_fz_nom={reference_fz_nom} is not among the tested loads {fz_noms}.")

    if ia_degs is None:
        ia_degs = detect_camber_levels(samples, fz_nom=reference_fz_nom, p_nom=p_nom, v_nom=v_nom, test_type="Braking")
    ia_degs = sorted(ia_degs)
    if not ia_degs:
        raise ValueError(f"No tested camber levels were detected (or given) at Fz_nom={reference_fz_nom}.")
    if 0.0 not in ia_degs:
        raise ValueError("Zero camber (0 deg) must be among the tested camber levels -- it anchors the load sweep.")

    load_conditions = [_process_condition(samples, fz, 0.0, p_nom, v_nom) for fz in fz_noms]
    camber_conditions = [_process_condition(samples, reference_fz_nom, ia, p_nom, v_nom) for ia in ia_degs]

    fx_base = sweep_point_from_kappa_sweep(
        next(c.fx_splines for c in load_conditions if c.fz_nom == reference_fz_nom), reference_fz_nom, 0.0
    )
    fx_load_sweep = [sweep_point_from_kappa_sweep(c.fx_splines, c.fz_nom, 0.0) for c in load_conditions]
    fx_camber_sweep = [
        sweep_point_from_kappa_sweep(c.fx_splines, reference_fz_nom, c.ia_nom) for c in camber_conditions
    ]
    fx_result = fit_fx_coefficients(fx_base, fx_load_sweep, fx_camber_sweep)

    return LongitudinalFitResult(
        reference_fz_nom=reference_fz_nom,
        load_conditions=load_conditions,
        camber_conditions=camber_conditions,
        fx=fx_result,
        quality_issues=round_issues,
    )
