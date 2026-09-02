"""Port of Raw_Data_Fitter_Fy_V3.m and Pacejka_Term_Finder_FY_V3.m.

(Raw_Data_Fitter_Fy_V3.m's function is actually named
`Raw_Data_Fitter_Fy_V2` -- a filename/function-name mismatch; MATLAB
resolves calls by filename, so this is dead cosmetic drift, not a
versioning clue. See CLAUDE.md quirk #1.)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from pacejka.model import FyCoefficients, fy_pure
from pacejka.splines import fit_smoothing_spline

# MATLAB's literal lbf->N conversion factor, used throughout the term
# finder (Fz, and the smoothed Fy ydata, both get multiplied by this).
LBF_TO_N = 4.448

# The original's fixed slip-angle evaluation grid: -12.25 to 12.25 degrees
# in 0.05-degree steps, 491 points. linspace (not arange) so float rounding
# can't drop or duplicate the endpoint: (12.25 - -12.25) / 0.05 == 490
# steps exactly, i.e. 491 points.
SA_GRID_DEG = np.linspace(-12.25, 12.25, 491)

# The original's per-channel MATLAB SmoothingParam values -- see
# CLAUDE.md's "Fitting stack" note on why these transfer directly to
# csaps's `smooth` and why they differ per channel in the first place.
_SMOOTHING_PARAMS = {
    "FX": 0.99999,
    "FY": 0.90,
    "MZ": 0.1,
    "Vc": 0.99999,
}


@dataclass(frozen=True)
class AlphaSweepSplines:
    """Smoothed slip-angle-sweep curves for one segmented test condition.

    `sa_grid_deg` is the fixed evaluation grid (SA_GRID_DEG); `fx`, `fy`,
    `mz`, `vc` are the corresponding smoothing-spline fits evaluated on
    that grid, in the source data's original units (lb, lb, ft-lb, mph --
    unconverted, matching Raw_Data_Fitter_Fy_V3.m's own output; unit
    conversion to SI happens in the term-finder that consumes this, same
    as the original).
    """

    sa_grid_deg: np.ndarray
    fx: np.ndarray
    fy: np.ndarray
    mz: np.ndarray
    vc: np.ndarray


def fit_alpha_sweep(condition: pd.DataFrame) -> AlphaSweepSplines:
    """Smooth one segmented condition's SA -> FX/FY/MZ/Vc curves.

    `condition` is one nominal test condition's samples -- typically the
    output of `pacejka.segmenting.segment_condition` -- with at least SA,
    FX, FY, MZ, Vc columns. SA is the independent variable (the slip-angle
    sweep); each of the other four is fit against it with its own
    MATLAB-matching SmoothingParam and evaluated on the fixed SA_GRID_DEG
    grid, exactly as Raw_Data_Fitter_Fy_V3.m does.

    ARCHITECTURE NOTE, and a real bug this sidesteps: Raw_Data_Fitter_Fy_V3.m
    decides which condition to load via its own internal `SweepVars.Fz =
    [50]` (also IA=[0], SA=[0], P=[12], V=[25]) -- all hardcoded, not
    parameters. Its caller, Pacejka_Term_Finder_FY_V3.m, takes an `Fz_nom`
    argument and uses it to look up a field name inside the result (e.g.
    `SplineData.P12.SA0.IA0.FY_..._150FZ_12P_0IA`), but Raw_Data_Fitter_Fy_V3
    itself only ever *produces* the `_50FZ_` field, regardless of what
    Fz_nom was requested -- so the original pipeline silently fits FZ=50 lbf
    no matter what a caller asks for, and would error looking up a field
    that doesn't exist for any other Fz_nom. This is a real, previously
    undocumented limitation of the MATLAB tool (see CLAUDE.md), not a
    deliberate single-condition design. It has no equivalent to preserve
    here: this function fits whatever DataFrame it's handed, so which
    condition gets fit is determined entirely by what the caller passed to
    `segment_condition` beforehand.
    """
    sa = condition["SA"].to_numpy(dtype=float)

    def _smoothed(channel: str) -> np.ndarray:
        y = condition[channel].to_numpy(dtype=float)
        spline = fit_smoothing_spline(sa, y, _SMOOTHING_PARAMS[channel])
        return spline(SA_GRID_DEG)

    return AlphaSweepSplines(
        sa_grid_deg=SA_GRID_DEG,
        fx=_smoothed("FX"),
        fy=_smoothed("FY"),
        mz=_smoothed("MZ"),
        vc=_smoothed("Vc"),
    )


# ---------------------------------------------------------------------------
# Pacejka_Term_Finder_FY_V3.m
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FySweepPoint:
    """One nominal condition's smoothed alpha -> Fy curve, in SI units,
    tagged with the physical load/camber it was recorded at. Build with
    `sweep_point_from_alpha_sweep`.
    """

    fz_n: float
    gamma_star: float
    alpha_rad: np.ndarray
    fy_n: np.ndarray


def sweep_point_from_alpha_sweep(splines: AlphaSweepSplines, fz_lbf: float, ia_deg: float) -> FySweepPoint:
    """Build an FySweepPoint from `fit_alpha_sweep`'s output plus the
    segmented condition's nominal load (lbf) and camber (deg)."""
    return FySweepPoint(
        fz_n=fz_lbf * LBF_TO_N,
        gamma_star=float(np.sin(np.radians(ia_deg))),
        alpha_rad=np.radians(splines.sa_grid_deg),
        fy_n=splines.fy * LBF_TO_N,
    )


# p0 in the MATLAB source. Ky7/Vsy4 (the load-camber cross term) are never
# actually fit here -- see FyFitResult's docstring -- so their p0 value
# never matters; kept for completeness against the source.
_P0 = dict(
    Cy1=0.975, Dy1=2.625, Dy2=-0.01, Dy3=25.0,
    Ey1=1.0, Ey2=-0.80, Ey3=0.0, Ey4=1.0, Ey5=1.0,
    Hsy1=0.0, Hsy2=0.0,
    Ky1=175.5, Ky2=2.9, Ky3=1.0, Ky4=0.8, Ky5=1.0, Ky6=3.0, Ky7=2.0,
    py1=1.0, py2=1.0, py3=1.0, py4=1.0, py5=1.0,
    Vsy1=0.0, Vsy2=0.0, Vsy3=3.0, Vsy4=0.0,
)

# Base stage: fit at the nominal load, zero camber. Field order and (lb, ub)
# match Pacejka_Term_Finder_FY_V3.m's Xb(1..9)/lbb/ubb exactly, with one
# deliberate fix -- see CLAUDE.md quirk #9: the original bounds Ky1 to
# [-70, -50], which excludes its own initial guess (175.5) and has the
# wrong sign for a coefficient that needs to be positive (it scales the
# cornering-stiffness term Ky_a); MATLAB would have silently clipped the
# initial guess to -50 and fit a physically-backwards (negative-stiffness)
# curve. Widened here to a permissive, uncommitted [0, 1000] bracket that
# contains the initial guess with the correct sign -- flagged as needing
# real domain-informed re-tuning, not a validated final choice. Dy1's
# bounds (2.784, 2.784) are a zero-width, evidently intentional fix of
# mu_y to a known value; its mismatched p0 (2.625) is inert since the
# fixed bound overrides it regardless.
_BASE_FIELDS = ("Cy1", "Dy1", "Ey1", "Ey3", "Hsy1", "Ky1", "Ky2", "Ky4", "Vsy1")
_BASE_BOUNDS = (
    (1.5, 1.7),
    (2.784, 2.784),
    (-15.0, 15.0),
    (-10.0, 25.0),
    (-0.01, 0.001),
    (0.0, 1000.0),
    (-10.0, 25.0),
    (-10.0, 25.0),
    (-10.0, 25.0),
)

# dFz stage: fit across every tested load at zero camber (per the
# multi-load-sweep decision in CLAUDE.md's roadmap -- the original hardcodes
# a single Fz_vals = [50], quirk #7). The original fits this stage with
# `nlinfit` + bisquare robust weighting and *never actually applies* the
# lbfz/ubfz bounds it computes (nlinfit doesn't support bounds at all;
# they're only ever written into the output table as metadata) -- so this
# stays genuinely unconstrained here too, matching real behavior rather
# than the recorded-but-inert bounds. Also fixes a real unit bug: the
# original's ydata for this stage is never converted from lbf to N (unlike
# every other stage), while its model still computes force in N -- a
# ~4.448x mismatch that would have badly distorted the fitted
# load-sensitivity coefficients (quirk #10). Fixed by converting
# consistently (see `sweep_point_from_alpha_sweep`, which always converts).
_DFZ_FIELDS = ("Dy2", "Ey2", "Hsy2", "Vsy2")

# dIA stage: fit across every tested camber angle at the nominal load. The
# original hardcodes gamma_vals = [0] (quirk #11), meaning it fits
# camber-sensitivity coefficients using data recorded *at zero camber*,
# with its own model also evaluated at zero camber throughout -- every
# term this stage is supposed to fit multiplies gamma_star or
# gamma_star**2, so it has zero effect on the fit's objective function and
# the "fitted" values are pure optimizer noise. Fixed the same way as dFz:
# real data spanning multiple tested camber angles, not one hardcoded
# value. Field order and bounds
# match Xb(...)/lbIA/ubIA exactly; one mild initial-guess overshoot exists
# (Dy3's p0=25 is just outside its own ub=20) and is handled generically by
# clipping into bounds before fitting, replicating MATLAB's own documented
# behavior for lsqcurvefit given an infeasible x0 (it silently moves
# out-of-bounds components to the nearest bound) rather than scipy's
# `least_squares`, which raises instead.
_DIA_FIELDS = ("Dy3", "Ey4", "Ey5", "Ky3", "Ky5", "Ky6", "Vsy3")
_DIA_BOUNDS = (
    (-20.0, 20.0),
    (-50.0, 50.0),
    (0.0, 80.0),
    (-20.0, 20.0),
    (-20.0, 20.0),
    (-4.0, 4.0),
    (-20.0, 20.0),
)


@dataclass(frozen=True)
class FyFitResult:
    """Fitted Magic Formula pure-lateral-slip coefficients plus the fitted
    curve at each input condition, for diagnostic plotting.

    `coefficients.Ky7` and `.Vsy4` (the load-camber cross term, MATLAB's
    5th "dIA x dFz" stage) are always 0.0 here -- not fit at all, rather
    than fit from data that can't actually identify them. The original's
    cross-term stage reuses the same single-load/single-camber data as
    every other stage, which can never constrain a term that's supposed to
    capture how camber-sensitivity itself changes with load: that needs
    data at combinations of nonzero camber *and* non-nominal load
    simultaneously (e.g. IA=2 deg at Fz=100 lbf), which nothing in this
    pipeline collects yet (`fit_alpha_sweep` only ever handles one
    load/camber combination per call). Deferred as a follow-up rather than
    fit from data that can't support it, or carried forward from the
    original's arbitrary, never-validated p0 guess (Ky7=2.0). See
    CLAUDE.md quirk #12.
    """

    coefficients: FyCoefficients
    base_fit_fy_n: np.ndarray
    load_sweep_fit_fy_n: list[np.ndarray]
    camber_sweep_fit_fy_n: list[np.ndarray]


def _residuals(x, field_names, fixed_values, fz0_prime, alpha_rad, fz_n, gamma_star, target_fy_n):
    values = dict(fixed_values)
    values.update(zip(field_names, x))
    fyo, _ = fy_pure(fz_n, fz0_prime, gamma_star, alpha_rad, FyCoefficients(**values))
    return fyo - target_fy_n


def _split_fixed_fields(field_names, bounds, current_values):
    """Split (field, bound) pairs into ones scipy can actually optimize and
    ones MATLAB's lb==ub effectively fixes as a constant.

    `scipy.optimize.least_squares` requires a *strictly* increasing
    `[lb, ub]` per parameter and raises otherwise; MATLAB's `lsqcurvefit`
    happily accepts `lb == ub` and treats that parameter as pinned to that
    value for the whole fit (e.g. Base's `Dy1`, fixed to a known mu_y of
    2.784 regardless of its stale p0 initial guess). Returns
    `(free_fields, free_bounds, fixed_updates)`.
    """
    free_fields, free_bounds = [], []
    fixed_updates = {}
    for name, (lb, ub) in zip(field_names, bounds):
        if lb == ub:
            fixed_updates[name] = lb
        else:
            free_fields.append(name)
            free_bounds.append((lb, ub))
    return free_fields, free_bounds, fixed_updates


def _fit_stage(field_names, x0, points, fz0_prime, fixed_values, bounds=None, robust=False):
    alpha_rad = np.concatenate([p.alpha_rad for p in points])
    fz_n = np.concatenate([np.full_like(p.alpha_rad, p.fz_n) for p in points])
    gamma_star = np.concatenate([np.full_like(p.alpha_rad, p.gamma_star) for p in points])
    target_fy_n = np.concatenate([p.fy_n for p in points])

    x0 = np.asarray(x0, dtype=float)
    args = (field_names, fixed_values, fz0_prime, alpha_rad, fz_n, gamma_star, target_fy_n)

    if bounds is None:
        lb, ub = -np.inf, np.inf
    else:
        lb = np.asarray([b[0] for b in bounds], dtype=float)
        ub = np.asarray([b[1] for b in bounds], dtype=float)
        # Replicates MATLAB's lsqcurvefit silently clipping an infeasible
        # x0 into [lb, ub] rather than scipy's least_squares, which raises.
        x0 = np.clip(x0, lb, ub)

    kwargs = {}
    if robust:
        # scipy's robust losses need an f_scale (the residual magnitude at
        # which a point starts being down-weighted); there's no fixed
        # value that makes sense across every stage/dataset since Fy
        # residuals could be single digits or thousands of Newtons
        # depending on the fit, so it's derived from the data itself (the
        # initial residual spread) rather than a hardcoded magic number --
        # approximating MATLAB's nlinfit+bisquare, which auto-scales its
        # robust weights from the residuals' own MAD. Not an exact match
        # (bisquare fully rejects far outliers; scipy's 'soft_l1' just
        # down-weights them), but closer than an arbitrary fixed scale.
        initial_residuals = _residuals(x0, *args)
        kwargs["loss"] = "soft_l1"
        kwargs["f_scale"] = max(float(np.std(initial_residuals)), 1e-6)

    result = least_squares(_residuals, x0, bounds=(lb, ub), args=args, **kwargs)
    return dict(zip(field_names, result.x))


def fit_fy_coefficients(
    base: FySweepPoint,
    load_sweep: Sequence[FySweepPoint],
    camber_sweep: Sequence[FySweepPoint],
) -> FyFitResult:
    """Fit the Magic Formula pure-lateral-slip coefficients.

    `base` anchors the reference load Fz0' (dfz=0) and zero camber, and is
    used alone for the Base stage. `load_sweep` should span every nominal
    load tested in the session at zero camber (including `base`'s own
    condition) and is used for the dFz stage. `camber_sweep` should span
    every nominal camber angle tested at the reference load (including
    zero camber, i.e. `base`'s own condition) and is used for the dIA
    stage. See `FyFitResult` for why the load-camber cross term is always
    zero rather than fit.

    Port of Pacejka_Term_Finder_FY_V3.m's Base/dFz/dIA stages -- see
    CLAUDE.md quirks #7 and #11 (hardcoded single-condition dFz/dIA data),
    #9 and #10 (Ky1 bounds, dFz unit bug), and #12 (deferred cross term),
    plus the module-level docstrings on `_BASE_BOUNDS`/`_DIA_FIELDS`/
    `FyFitResult` for what changed and why.
    """
    fz0_prime = base.fz_n
    coeffs_values = dict(_P0)

    free_fields, free_bounds, fixed_from_bounds = _split_fixed_fields(_BASE_FIELDS, _BASE_BOUNDS, coeffs_values)
    coeffs_values.update(fixed_from_bounds)
    x0 = [coeffs_values[name] for name in free_fields]
    fixed = {k: v for k, v in coeffs_values.items() if k not in free_fields}
    coeffs_values.update(_fit_stage(free_fields, x0, [base], fz0_prime, fixed, bounds=free_bounds))
    base_fit_fy_n, _ = fy_pure(
        base.fz_n, fz0_prime, base.gamma_star, base.alpha_rad, FyCoefficients(**coeffs_values)
    )

    x0 = [coeffs_values[name] for name in _DFZ_FIELDS]
    fixed = {k: v for k, v in coeffs_values.items() if k not in _DFZ_FIELDS}
    coeffs_values.update(_fit_stage(_DFZ_FIELDS, x0, load_sweep, fz0_prime, fixed, bounds=None, robust=True))
    dfz_coeffs = FyCoefficients(**coeffs_values)
    load_sweep_fit_fy_n = [fy_pure(p.fz_n, fz0_prime, p.gamma_star, p.alpha_rad, dfz_coeffs)[0] for p in load_sweep]

    x0 = [coeffs_values[name] for name in _DIA_FIELDS]
    fixed = {k: v for k, v in coeffs_values.items() if k not in _DIA_FIELDS}
    coeffs_values.update(_fit_stage(_DIA_FIELDS, x0, camber_sweep, fz0_prime, fixed, bounds=_DIA_BOUNDS))

    # Load-camber cross term: deferred, not fit -- see FyFitResult.
    coeffs_values["Ky7"] = 0.0
    coeffs_values["Vsy4"] = 0.0

    final_coeffs = FyCoefficients(**coeffs_values)
    camber_sweep_fit_fy_n = [
        fy_pure(p.fz_n, fz0_prime, p.gamma_star, p.alpha_rad, final_coeffs)[0] for p in camber_sweep
    ]

    return FyFitResult(
        coefficients=final_coeffs,
        base_fit_fy_n=base_fit_fy_n,
        load_sweep_fit_fy_n=load_sweep_fit_fy_n,
        camber_sweep_fit_fy_n=camber_sweep_fit_fy_n,
    )
