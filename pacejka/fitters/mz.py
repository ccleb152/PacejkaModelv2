"""Port of Raw_Data_Fitter_Mz_V2.m and Pacejka_Term_Finder_MZ_V1_redo.m."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd

from pacejka.fitting import fit_stage, split_fixed_fields
from pacejka.model import FyCoefficients, MzCoefficients, fy_terms, mz_pure
from pacejka.splines import fit_smoothing_spline

# MATLAB's literal ft-lb -> N*m conversion factor.
FTLB_TO_NM = 0.3048 * 4.448

# MATLAB's literal lbf -> N conversion factor (same constant as fy.py's
# LBF_TO_N; kept local to avoid a fy.py<->mz.py import for one float).
LBF_TO_N = 4.448

# The tire's (loaded) radius the MATLAB source hardcodes -- 9 inches.
# Exposed as a `fit_mz_coefficients` default rather than baked into
# model.py's mz_pure, since it's a per-tire physical property, not part
# of the Magic Formula equation itself.
DEFAULT_RO_M = 9 * 0.0254

# The nominal test speed (25 mph) the MATLAB source assumes when computing
# the numerically-regularized cos(alpha) term. Same reasoning as DEFAULT_RO_M.
DEFAULT_TEST_SPEED_MPH = 25.0

# The original's fixed, non-uniform slip-angle evaluation grid: coarser
# 0.05-degree spacing away from zero SA, finer 0.025-degree spacing near it
# (where the aligning-moment curve's peak/pneumatic-trail behavior is most
# sensitive to slip angle) -- concatenation of
# [-12.3,-4.7]@0.05, [-4.675,4.675]@0.025, [4.7,12.3]@0.05, 681 points total.
# linspace per segment (not arange) so float rounding can't drop or
# duplicate an endpoint.
_OUTER_NEG_SA = np.linspace(-12.3, -4.7, 153)
_INNER_SA = np.linspace(-4.675, 4.675, 375)
_OUTER_POS_SA = np.linspace(4.7, 12.3, 153)
SA_GRID_DEG = np.concatenate([_OUTER_NEG_SA, _INNER_SA, _OUTER_POS_SA])

# The original's MATLAB SmoothingParam for SA->MZ.
_MZ_SMOOTHING_PARAM = 0.75


@dataclass(frozen=True)
class AligningMomentSpline:
    """Smoothed slip-angle -> aligning-moment curve for one condition.

    `sa_grid_deg` is the fixed evaluation grid (SA_GRID_DEG); `mz` is the
    smoothing-spline fit evaluated on it, in the source data's original
    units (ft-lb, unconverted -- unit conversion to SI happens in the term
    finder that consumes this, same as the original).
    """

    sa_grid_deg: np.ndarray
    mz: np.ndarray


def fit_aligning_moment(condition: pd.DataFrame) -> AligningMomentSpline:
    """Smooth one segmented condition's SA -> MZ curve.

    `condition` is one nominal test condition's samples -- typically the
    output of `pacejka.segmenting.segment_condition` -- with at least SA
    and MZ columns.

    Unlike `Raw_Data_Fitter_Mx_V2.m` (see `pacejka.fitters.mx`, not yet
    ported), this does *not* trim the "return sweep" portion of a
    triangle-wave SA trace before fitting -- Raw_Data_Fitter_Mz_V2.m
    computes the trim indices (`Index`/`Max1`/`Min2`) but the actual
    trim lines are commented out, so they're dead code, omitted here.
    Whether that's deliberate (MZ's fit is meant to include both sweep
    directions, e.g. to capture hysteresis) or an oversight when this file
    was copied from its MX sibling is not knowable from the source alone
    -- see CLAUDE.md quirk #8. This port preserves the original's actual
    (untrimmed) behavior; flagged for the team to confirm.

    Also unlike `pacejka.fitters.fy.fit_alpha_sweep`, only MZ is fit here
    (the original's `RawDataVars` is just `['MZ', 'SA']`) -- no FX/FY/Vc,
    matching Raw_Data_Fitter_Mz_V2.m's own narrower scope.
    """
    sa = condition["SA"].to_numpy(dtype=float)
    mz = condition["MZ"].to_numpy(dtype=float)

    spline = fit_smoothing_spline(sa, mz, _MZ_SMOOTHING_PARAM)
    return AligningMomentSpline(sa_grid_deg=SA_GRID_DEG, mz=spline(SA_GRID_DEG))


# ---------------------------------------------------------------------------
# Pacejka_Term_Finder_MZ_V1_redo.m
# ---------------------------------------------------------------------------


def _cos_alpha_p(alpha_rad, test_speed_mph=DEFAULT_TEST_SPEED_MPH):
    """Numerically-regularized cos(alpha).

    Matches the original's `Vcx/(Vcx/cos(Alpha) + 0.1)` exactly rather
    than simplifying to `cos(alpha)` -- the two are close (Vcx is large
    relative to the +0.1 regularizer at realistic speeds) but not
    identical, and the original's exact form is cheap to reproduce.
    """
    vcx = test_speed_mph * 0.447
    v = vcx / np.cos(alpha_rad)
    return vcx / (v + 0.1)


@dataclass(frozen=True)
class MzSweepPoint:
    """One nominal condition's smoothed alpha -> Mz curve, in SI units,
    tagged with the physical load/camber it was recorded at, plus the
    per-point `cos_alpha_p` term `mz_pure` needs. Build with
    `sweep_point_from_aligning_moment`.
    """

    fz_n: float
    gamma_star: float
    alpha_rad: np.ndarray
    mz_nm: np.ndarray
    cos_alpha_p: np.ndarray


def sweep_point_from_aligning_moment(
    splines: AligningMomentSpline,
    fz_lbf: float,
    ia_deg: float,
    test_speed_mph: float = DEFAULT_TEST_SPEED_MPH,
) -> MzSweepPoint:
    """Build an MzSweepPoint from `fit_aligning_moment`'s output plus the
    segmented condition's nominal load (lbf) and camber (deg)."""
    alpha_rad = np.radians(splines.sa_grid_deg)
    return MzSweepPoint(
        fz_n=fz_lbf * LBF_TO_N,
        gamma_star=float(np.sin(np.radians(ia_deg))),
        alpha_rad=alpha_rad,
        mz_nm=splines.mz * FTLB_TO_NM,
        cos_alpha_p=_cos_alpha_p(alpha_rad, test_speed_mph),
    )


# p0 in the MATLAB source (all 1.0, except Dz4/Dz11=3.0 -- a uniform,
# not-domain-tuned placeholder set; MATLAB's own silent x0-into-bounds
# clipping, replicated by pacejka.fitting.fit_stage, handles the many
# resulting infeasible initial guesses sensibly -- e.g. Hz1's bound is
# +/-0.01, so an initial guess of 1.0 just clips to the boundary nearest
# zero, which is actually a reasonable starting point for a shift term).
# Hz4/Dz9/Dz11 (the load-camber cross term) are never fit -- see
# MzFitResult -- so their p0 value never matters; kept for completeness.
_MZ_P0 = dict(
    Hz1=1.0, Hz2=1.0, Hz3=1.0, Hz4=1.0,
    Bz1=1.0, Bz2=1.0, Bz3=1.0, Bz4=1.0, Bz5=1.0,
    Bz9=1.0, Bz10=1.0,
    Cz1=1.0,
    Dz1=1.0, Dz2=1.0, Dz3=1.0, Dz4=3.0,
    Dz6=1.0, Dz7=10.0, Dz8=1.0, Dz9=1.0, Dz10=1.0, Dz11=3.0,
    Ez1=1.0, Ez2=1.0, Ez3=1.0, Ez4=1.0, Ez5=1.0,
)

# Base stage: fit at the nominal load, zero camber. Field order and
# (lb, ub) match Pacejka_Term_Finder_MZ_V1_redo.m's Xb(1..10)/lbb/ubb
# exactly. Bz4's bounds (20.0, 20.0) are a deliberate zero-width fix
# (same mechanism as the FY term finder's Dy1 -- see
# pacejka.fitting.split_fixed_fields), not a typo.
_BASE_FIELDS = ("Hz1", "Bz1", "Bz4", "Bz9", "Bz10", "Cz1", "Dz1", "Dz6", "Ez1", "Ez4")
_BASE_BOUNDS = (
    (-0.01, 0.01),
    (-20.0, 70.0),
    (20.0, 20.0),
    (-5.0, 5.0),
    (-20.0, 0.0),
    (0.0, 20.0),
    (-20.0, 20.0),
    (-20.0, 20.0),
    (-20.0, 15.0),
    (-20.0, 20.0),
)

# dFz stage: fit across every tested load at zero camber. The original
# hardcodes `Fz_vals = Fz_nom` -- i.e. literally the same single load the
# Base stage already uses (the file's own comment, `%[50 100 150 200
# 250]`, shows what this was clearly meant to be before someone replaced
# it with `Fz_nom`) -- making dfz identically 0 throughout and this whole
# stage unable to identify anything, the same failure mode as
# Raw_Data_Fitter_Fy_V3.m's hardcoded SweepVars.Fz=[50] (quirk #7). Fixed
# the same way: real data spanning multiple tested loads. Unlike the FY
# term finder's dFz stage (fit with unconstrained `nlinfit`), this one
# uses bounded `lsqcurvefit` in the original, so real bounds are enforced
# here too (no robust loss).
_DFZ_FIELDS = ("Hz2", "Bz2", "Bz3", "Dz2", "Dz7", "Ez2", "Ez3")
_DFZ_BOUNDS = (
    (-0.015, 0.015),
    (-70.0, 20.0),
    (-70.0, 20.0),
    (-50.0, 20.0),
    (-50.0, 20.0),
    (-50.0, 20.0),
    (-20.0, 270.0),
)

# dIA stage: fit across every tested camber angle at the nominal load. The
# original hardcodes `gamma_vals = 2` -- a single nonzero camber, not a
# sweep. Milder than the dFz bug above (a nonzero camber does give the
# fit *some* sensitivity, unlike FY's dIA stage's exactly-zero-effect
# hardcoding), but still poorly identified: several terms multiply
# different functions of gamma (gamma, gamma**2, abs(gamma)), which can't
# be told apart from data at only one nonzero camber value. Fixed the
# same way: a real multi-camber sweep (e.g. 0/2/4 deg).
_DIA_FIELDS = ("Hz3", "Bz5", "Dz3", "Dz4", "Dz8", "Dz10", "Ez5")
_DIA_BOUNDS = (
    (-0.01, 0.01),
    (-20.0, 20.0),
    (-20.0, 20.0),
    (-20.0, 20.0),
    (-20.0, 20.0),
    (-20.0, 20.0),
    (-50.0, 20.0),
)


def _fy_derived_terms(point: MzSweepPoint, fz0_prime: float, fy_coefficients: FyCoefficients):
    """The FY-fit quantities `mz_pure` needs for one point: `cy`, `by`,
    and `s_hf` at this point's actual camber (scalars -- none of these
    depend on alpha), plus `fy_og0` at zero camber regardless of this
    point's actual camber (an array matching `point.alpha_rad` -- `fyo`
    does depend on alpha), matching `ParameterLoad`'s own two calls.
    """
    terms = fy_terms(point.fz_n, fz0_prime, point.gamma_star, point.alpha_rad, fy_coefficients)
    terms_g0 = fy_terms(point.fz_n, fz0_prime, 0.0, point.alpha_rad, fy_coefficients)
    return float(terms.cy), float(terms.by), float(terms.s_hf), terms_g0.fyo


def _eval_mz(points, fy_derived, fz0_prime, ro, coeffs: MzCoefficients):
    return [
        mz_pure(p.fz_n, fz0_prime, ro, p.gamma_star, p.alpha_rad, p.cos_alpha_p, cy, by, s_hf, fy_og0, coeffs)
        for p, (cy, by, s_hf, fy_og0) in zip(points, fy_derived)
    ]


def _fit_mz_stage(field_names, x0, points, fy_derived, fz0_prime, ro, fixed_values, bounds=None, robust=False):
    """Mz-specific residual closure over `pacejka.fitting.fit_stage`."""
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
        mz = mz_pure(
            fz_n, fz0_prime, ro, gamma_star, alpha_rad, cos_alpha_p, fy_cy, fy_by, s_hf, fy_og0,
            MzCoefficients(**values),
        )
        return mz - target_mz_nm

    fitted_x = fit_stage(residuals, x0, bounds=bounds, robust=robust)
    return dict(zip(field_names, fitted_x))


@dataclass(frozen=True)
class MzFitResult:
    """Fitted Magic Formula aligning-moment coefficients plus the fitted
    curve at each input condition, for diagnostic plotting.

    `coefficients.Hz4`, `.Dz9`, `.Dz11` (the load-camber cross term,
    MATLAB's 4th "dIA x dFz" stage) are always 0.0 here -- not fit at
    all, for the same reason as `FyFitResult`'s unfit `Ky7`/`Vsy4`: the
    original's cross-term stage reuses the same single-load/single-camber
    data as every other stage (`Fz_vals=Fz_nom` again makes `dfz` 0
    throughout, so every term this stage is meant to fit -- which all
    multiply `dfz` -- has zero effect on the objective), so it can't
    actually identify a cross term regardless of what it's hardcoded to.
    Deferred as a follow-up, same as FY's cross term, rather than fit
    from data that can't support it. See CLAUDE.md.
    """

    coefficients: MzCoefficients
    base_fit_mz_nm: np.ndarray
    load_sweep_fit_mz_nm: list[np.ndarray]
    camber_sweep_fit_mz_nm: list[np.ndarray]


def fit_mz_coefficients(
    base: MzSweepPoint,
    load_sweep: Sequence[MzSweepPoint],
    camber_sweep: Sequence[MzSweepPoint],
    fy_coefficients: FyCoefficients,
    ro: float = DEFAULT_RO_M,
) -> MzFitResult:
    """Fit the Magic Formula aligning-moment coefficients.

    `base`/`load_sweep`/`camber_sweep` play the same roles as in
    `pacejka.fitters.fy.fit_fy_coefficients` (anchor condition, full load
    sweep at zero camber, full camber sweep at the reference load).
    `fy_coefficients` must already be fit (via `fit_fy_coefficients`) at
    the same reference load -- this equation is built on top of it, not
    an independent fit (matching the original's dependency on a saved
    `FY_Parameters` file, but taken directly in memory here instead of
    round-tripping through disk -- see CLAUDE.md's migration workflow).

    Port of Pacejka_Term_Finder_MZ_V1_redo.m's Base/dFz/dIA stages. See
    `mz_pure` for the alpha_r/alpha_t bug fix, this module's `_DFZ_FIELDS`/
    `_DIA_FIELDS` for the hardcoded-single-condition fixes, and
    `MzFitResult` for the deferred cross term.
    """
    fz0_prime = base.fz_n
    coeffs_values = dict(_MZ_P0)
    coeffs_values["Hz4"] = 0.0
    coeffs_values["Dz9"] = 0.0
    coeffs_values["Dz11"] = 0.0

    base_fy_derived = [_fy_derived_terms(base, fz0_prime, fy_coefficients)]
    free_fields, free_bounds, fixed_from_bounds = split_fixed_fields(_BASE_FIELDS, _BASE_BOUNDS, coeffs_values)
    coeffs_values.update(fixed_from_bounds)
    x0 = [coeffs_values[name] for name in free_fields]
    fixed = {k: v for k, v in coeffs_values.items() if k not in free_fields}
    coeffs_values.update(
        _fit_mz_stage(free_fields, x0, [base], base_fy_derived, fz0_prime, ro, fixed, bounds=free_bounds)
    )
    base_fit_mz_nm = _eval_mz([base], base_fy_derived, fz0_prime, ro, MzCoefficients(**coeffs_values))[0]

    load_fy_derived = [_fy_derived_terms(p, fz0_prime, fy_coefficients) for p in load_sweep]
    x0 = [coeffs_values[name] for name in _DFZ_FIELDS]
    fixed = {k: v for k, v in coeffs_values.items() if k not in _DFZ_FIELDS}
    coeffs_values.update(
        _fit_mz_stage(_DFZ_FIELDS, x0, load_sweep, load_fy_derived, fz0_prime, ro, fixed, bounds=_DFZ_BOUNDS)
    )
    load_sweep_fit_mz_nm = _eval_mz(load_sweep, load_fy_derived, fz0_prime, ro, MzCoefficients(**coeffs_values))

    camber_fy_derived = [_fy_derived_terms(p, fz0_prime, fy_coefficients) for p in camber_sweep]
    x0 = [coeffs_values[name] for name in _DIA_FIELDS]
    fixed = {k: v for k, v in coeffs_values.items() if k not in _DIA_FIELDS}
    coeffs_values.update(
        _fit_mz_stage(_DIA_FIELDS, x0, camber_sweep, camber_fy_derived, fz0_prime, ro, fixed, bounds=_DIA_BOUNDS)
    )

    final_coeffs = MzCoefficients(**coeffs_values)
    camber_sweep_fit_mz_nm = _eval_mz(camber_sweep, camber_fy_derived, fz0_prime, ro, final_coeffs)

    return MzFitResult(
        coefficients=final_coeffs,
        base_fit_mz_nm=base_fit_mz_nm,
        load_sweep_fit_mz_nm=load_sweep_fit_mz_nm,
        camber_sweep_fit_mz_nm=camber_sweep_fit_mz_nm,
    )
