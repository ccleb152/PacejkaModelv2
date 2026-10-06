"""Orchestration for the longitudinal (Fx, pure-slip + combined-slip)
fitting pipeline.

Mirrors `pacejka.pipeline`'s cornering orchestration (MIGRATION_PLAN.md
step 9's role, extended to Phase 2): given one loaded raw TTC
BrakeDrive/Braking round and a handful of top-level settings, runs the
full segment -> smooth -> fit pipeline across every tested load and
camber angle automatically, the same multi-load-sweep principle as
`run_cornering_fit` (see CLAUDE.md's roadmap), rather than the original's
per-file hardcoded sweeps.

Scope note: pure-slip Fx, plus the combined-slip Fx/Fy stages (see
`pacejka.fitters.fx`/`pacejka.fitters.fy`'s module docstrings for the
`SA_vals=0` degeneracy those fix). Combined-slip Fy needs an
already-fit pure-slip `FyCoefficients` (from a Cornering round for the
*same tire* -- `pacejka.pipeline.run_cornering_fit`'s result) passed in
as `fy_pure_coeffs`; without it, combined-slip Fy is skipped (`combined.
fy is None`) since there's no pure-slip curve for `fy_combined` to
weight. Combined-slip fitting as a whole is skipped (`combined is None`)
when the round has no real multi-slip-angle data (`detect_sa_levels`
finds nothing beyond SA=0) -- a round recorded before the team started
sweeping multiple slip angles is still a valid pure-slip-only Fx fit.

Deliberately has no Streamlit/plotting dependency -- the app layer calls
this and renders `LongitudinalFitResult`, this module just computes it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pandas as pd

from pacejka.detection import detect_camber_levels, detect_fz_levels, detect_sa_levels
from pacejka.fitters.fx import (
    CombinedFxFitResult,
    FxFitResult,
    KappaSweepSplines,
    combined_sweep_point_from_kappa_sweep as combined_fx_sweep_point_from_kappa_sweep,
    fit_combined_fx_coefficients,
    fit_fx_coefficients,
    fit_kappa_sweep,
    sweep_point_from_kappa_sweep,
    trim_to_raw_domain,
)
from pacejka.fitters.fy import (
    CombinedFyFitResult,
    combined_sweep_point_from_kappa_sweep as combined_fy_sweep_point_from_kappa_sweep,
    fit_combined_fy_coefficients,
)
from pacejka.model import FyCoefficients
from pacejka.quality import QualityIssue, check_condition_quality, check_round_quality
from pacejka.segmenting import segment_condition


@dataclass(frozen=True)
class LongitudinalConditionResult:
    """Everything computed for one nominal (Fz, IA, SA) condition -- the
    raw segmented samples and the smoothed kappa-sweep curves -- for
    diagnostic plotting (raw scatter + smoothed spline; the Pacejka fit
    curve itself lives in the `FxFitResult`/`CombinedFxFitResult`/
    `CombinedFyFitResult`, evaluated at each of these same conditions in
    the same order).

    `sa_nom` is 0.0 for every pure-slip condition (`load_conditions`/
    `camber_conditions`) -- it only varies for the combined-slip
    conditions (`CombinedSlipFitResult.alpha_conditions`/`load_conditions`/
    `camber_conditions`), which are recorded at a nonzero slip angle.
    """

    fz_nom: float
    ia_nom: float
    samples: pd.DataFrame
    fx_splines: KappaSweepSplines
    quality_issues: list[QualityIssue]
    sa_nom: float = 0.0


@dataclass(frozen=True)
class CombinedSlipFitResult:
    """The combined-slip portion of one longitudinal pipeline run.

    `reference_sa_nom` is the nonzero slip angle `load_conditions`/
    `camber_conditions` were recorded at -- a single nonzero value is
    deliberately reused across both the dFz and dIA stages of each fitter
    (rather than, say, picking the largest-magnitude tested angle for one
    stage and the smallest for another), matching the data shape
    `fit_combined_fx_coefficients`/`fit_combined_fy_coefficients` expect.
    It's chosen as the tested nonzero slip angle closest to zero (e.g.
    -3 deg over -6 deg, when both are tested) since that's the condition
    least likely to have its own data quality issues from being a more
    extreme test condition. `alpha_conditions` instead spans *every*
    tested nonzero slip angle (not just the reference one), at the
    reference load and zero camber -- that's what lets the Base-stage fit
    actually see alpha vary.

    `fy` is `None` when no pure-slip `FyCoefficients` was supplied to
    `run_longitudinal_fit` (see its docstring).
    """

    reference_sa_nom: float
    alpha_conditions: list[LongitudinalConditionResult]
    load_conditions: list[LongitudinalConditionResult]
    camber_conditions: list[LongitudinalConditionResult]
    fx: CombinedFxFitResult
    fy: CombinedFyFitResult | None


@dataclass(frozen=True)
class LongitudinalFitResult:
    """The complete result of one longitudinal (Fx, pure + combined-slip,
    plus combined-slip Fy) pipeline run.

    `combined` is `None` when the round has no real multi-slip-angle data
    to fit combined-slip coefficients from -- see this module's
    docstring.
    """

    reference_fz_nom: float
    load_conditions: list[LongitudinalConditionResult]
    camber_conditions: list[LongitudinalConditionResult]
    fx: FxFitResult
    quality_issues: list[QualityIssue]
    combined: CombinedSlipFitResult | None = None


def _process_condition(samples, fz_nom, ia_nom, p_nom, v_nom, sa_nom=0.0) -> LongitudinalConditionResult:
    segment = segment_condition(
        samples, fz_nom=fz_nom, p_nom=p_nom, ia_nom=ia_nom, sa_nom=sa_nom, v_nom=v_nom, test_type="Braking"
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
        sa_nom=sa_nom,
    )


def run_longitudinal_fit(
    samples: pd.DataFrame,
    p_nom: float = 12.0,
    v_nom: float = 25.0,
    reference_fz_nom: float | None = None,
    fz_noms: Sequence[float] | None = None,
    ia_degs: Sequence[float] | None = None,
    sa_noms: Sequence[float] | None = None,
    fy_pure_coeffs: FyCoefficients | None = None,
) -> LongitudinalFitResult:
    """Run the Fx (pure-slip + combined-slip) fitting pipeline on one raw
    Braking round, plus combined-slip Fy when `fy_pure_coeffs` is given.

    `fz_noms`/`ia_degs` default to auto-detection (`pacejka.detection`,
    `test_type="Braking"`) when not given. `reference_fz_nom` (the
    Base-stage anchor, Fz0') defaults to the middle detected/given load;
    it must be one of `fz_noms`. Zero camber must be among `ia_degs` --
    it's the anchor the load sweep is done at.

    `sa_noms` defaults to auto-detection (`pacejka.detection.
    detect_sa_levels`, at the reference load and zero camber) when not
    given, and controls the combined-slip fit: when fewer than 2 distinct
    slip angles are found (i.e. no real nonzero-SA data), combined-slip
    fitting is skipped entirely and `LongitudinalFitResult.combined` is
    `None` -- a round with no multi-slip-angle test matrix still gets a
    valid pure-slip-only Fx fit. `fy_pure_coeffs` is the already-fit
    pure-slip `FyCoefficients` for this same tire (from a Cornering round
    via `pacejka.pipeline.run_cornering_fit`) -- `fy_combined` weights
    that pure-slip curve, it can't be fit independently (see
    `pacejka.model.fy_combined`). Without it, combined-slip Fy is skipped
    (`combined.fy is None`) even when combined-slip Fx was fit.

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

    combined = _run_combined_slip_fit(
        samples,
        p_nom,
        v_nom,
        reference_fz_nom,
        fz_noms,
        ia_degs,
        sa_noms,
        reference_fz_splines=next(c.fx_splines for c in load_conditions if c.fz_nom == reference_fz_nom),
        fx_pure_coeffs=fx_result.coefficients,
        fy_pure_coeffs=fy_pure_coeffs,
    )

    return LongitudinalFitResult(
        reference_fz_nom=reference_fz_nom,
        load_conditions=load_conditions,
        camber_conditions=camber_conditions,
        fx=fx_result,
        quality_issues=round_issues,
        combined=combined,
    )


def _run_combined_slip_fit(
    samples,
    p_nom,
    v_nom,
    reference_fz_nom,
    fz_noms,
    ia_degs,
    sa_noms,
    reference_fz_splines,
    fx_pure_coeffs,
    fy_pure_coeffs,
) -> CombinedSlipFitResult | None:
    """Build the combined-slip (Fx + optionally Fy) fit, or return `None`
    when there's no real multi-slip-angle data to fit it from.

    See `run_longitudinal_fit`'s docstring and `CombinedSlipFitResult`'s
    for the data shape this builds: `alpha_conditions` sweeps every
    nonzero tested slip angle at the reference load and zero camber;
    `load_conditions`/`camber_conditions` (here, distinct from the
    pure-slip ones of the same name in `run_longitudinal_fit`) sweep load
    and camber respectively at a single nonzero reference slip angle --
    required because the combined-slip weighting is identically 1
    (`pacejka.model.fx_combined`'s `G_xa` degeneracy) or only partially
    identifiable (`fy_combined`'s `G_yk` Base-stage degeneracy) at
    alpha=0, so the dFz/dIA stages can't reuse the pure-slip (alpha=0)
    load/camber sweeps the way the pure-slip fit itself does.
    """
    if sa_noms is None:
        sa_noms = detect_sa_levels(samples, fz_nom=reference_fz_nom, ia_nom=0.0, p_nom=p_nom, v_nom=v_nom)
    sa_noms = sorted(sa_noms)
    nonzero_sa_noms = sorted((sa for sa in sa_noms if sa != 0.0), key=abs)
    if not nonzero_sa_noms:
        return None
    reference_sa_nom = nonzero_sa_noms[0]

    alpha_conditions = [
        _process_condition(samples, reference_fz_nom, 0.0, p_nom, v_nom, sa_nom=sa) for sa in nonzero_sa_noms
    ]
    combined_load_conditions = [
        _process_condition(samples, fz, 0.0, p_nom, v_nom, sa_nom=reference_sa_nom) for fz in fz_noms
    ]
    combined_camber_conditions = [
        _process_condition(samples, reference_fz_nom, ia, p_nom, v_nom, sa_nom=reference_sa_nom) for ia in ia_degs
    ]

    fx_base = combined_fx_sweep_point_from_kappa_sweep(reference_fz_splines, reference_fz_nom, 0.0, 0.0)
    fx_alpha_sweep = [
        combined_fx_sweep_point_from_kappa_sweep(c.fx_splines, reference_fz_nom, 0.0, c.sa_nom)
        for c in alpha_conditions
    ]
    fx_load_sweep = [
        combined_fx_sweep_point_from_kappa_sweep(c.fx_splines, c.fz_nom, 0.0, reference_sa_nom)
        for c in combined_load_conditions
    ]
    fx_camber_sweep = [
        combined_fx_sweep_point_from_kappa_sweep(c.fx_splines, reference_fz_nom, c.ia_nom, reference_sa_nom)
        for c in combined_camber_conditions
    ]
    fx_combined_result = fit_combined_fx_coefficients(fx_pure_coeffs, fx_base, fx_alpha_sweep, fx_load_sweep, fx_camber_sweep)

    fy_combined_result = None
    if fy_pure_coeffs is not None:
        fy_base = combined_fy_sweep_point_from_kappa_sweep(reference_fz_splines, reference_fz_nom, 0.0, 0.0)
        fy_alpha_sweep = [
            combined_fy_sweep_point_from_kappa_sweep(c.fx_splines, reference_fz_nom, 0.0, c.sa_nom)
            for c in alpha_conditions
        ]
        fy_load_sweep = [
            combined_fy_sweep_point_from_kappa_sweep(c.fx_splines, c.fz_nom, 0.0, reference_sa_nom)
            for c in combined_load_conditions
        ]
        fy_camber_sweep = [
            combined_fy_sweep_point_from_kappa_sweep(c.fx_splines, reference_fz_nom, c.ia_nom, reference_sa_nom)
            for c in combined_camber_conditions
        ]
        fy_combined_result = fit_combined_fy_coefficients(
            fy_pure_coeffs, fy_base, fy_alpha_sweep, fy_load_sweep, fy_camber_sweep
        )

    return CombinedSlipFitResult(
        reference_sa_nom=reference_sa_nom,
        alpha_conditions=alpha_conditions,
        load_conditions=combined_load_conditions,
        camber_conditions=combined_camber_conditions,
        fx=fx_combined_result,
        fy=fy_combined_result,
    )
