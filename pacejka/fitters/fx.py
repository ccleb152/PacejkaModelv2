"""Port of Raw_Data_Fitter_Fx_V2.m and Pacejka_Term_Finder_FX_V4_Redo.m's
pure-longitudinal-slip stages only.

Scope note (confirmed with the user before starting -- see CLAUDE.md's
"Longitudinal (Fx / braking) support" status note): `Pacejka_Term_Finder_
FX_V4_Redo.m` also fits two combined-slip stages (how a nonzero slip
angle reduces longitudinal force, and how a nonzero slip ratio reduces
lateral force) after the pure-slip stages this module ports. Both
combined-slip stages are fit from data at a single hardcoded `SA_vals =
0` -- the same degenerate single-value-sweep pattern already documented
for Fy's dIA stage (quirk #11) and Mz's dIA stage (quirk #15); see
CLAUDE.md quirk #24. Deferred as explicit future work rather than
ported as a literal (and currently unfixable) translation; see
MODEL_CHANGES.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd

from pacejka.fitters.fy import LBF_TO_N
from pacejka.fitting import fit_stage, split_fixed_fields
from pacejka.model import FxCoefficients, fx_pure
from pacejka.splines import fit_smoothing_spline

# The original's fixed slip-ratio evaluation grid: -0.161 to 0.141 in
# 0.001 steps, 303 points (`SLRange = (-0.161:0.001:0.141)'`). linspace
# (not arange) so float rounding can't drop or duplicate the endpoint:
# (0.141 - -0.161) / 0.001 == 302 steps exactly, i.e. 303 points.
SL_GRID = np.linspace(-0.161, 0.141, 303)

# The original's per-channel MATLAB SmoothingParam values, from
# Raw_Data_Fitter_Fx_V2.m -- see CLAUDE.md's "Fitting stack" note on why
# these transfer directly to csaps's `smooth` and why they differ per
# channel/file in the first place.
_SMOOTHING_PARAMS = {
    "FX": 0.99999999,
    "FY": 0.9999999,
    "MZ": 0.99999,
    "Vc": 0.99999,
}


@dataclass(frozen=True)
class KappaSweepSplines:
    """Smoothed slip-ratio-sweep curves for one segmented test condition.

    `sl_grid` is the fixed evaluation grid (SL_GRID); `fx`, `fy`, `mz`,
    `vc` are the corresponding smoothing-spline fits evaluated on that
    grid, in the source data's original units (lb, lb, ft-lb, mph --
    unconverted, matching Raw_Data_Fitter_Fx_V2.m's own output; unit
    conversion to SI happens in the term-finder that consumes this, same
    as the original).
    """

    sl_grid: np.ndarray
    fx: np.ndarray
    fy: np.ndarray
    mz: np.ndarray
    vc: np.ndarray


def fit_kappa_sweep(condition: pd.DataFrame) -> KappaSweepSplines:
    """Smooth one segmented condition's SL -> FX/FY/MZ/Vc curves.

    `condition` is one nominal test condition's samples -- typically the
    output of `pacejka.segmenting.segment_condition` with
    `test_type="Braking"` -- with at least SL, FX, FY, MZ, Vc columns. SL
    (slip ratio) is the independent variable; each of the other four is
    fit against it with its own MATLAB-matching SmoothingParam and
    evaluated on the fixed SL_GRID grid, exactly as Raw_Data_Fitter_Fx_V2.m
    does.

    Unlike `pacejka.fitters.fy.fit_alpha_sweep`, the original's own
    `SweepVars` here are all hardcoded too (`Fz=[50 150 200 250]`,
    `IA=[0 2]`, `SA=[0]`, `P=[12]`, `V=[25]`) -- same pattern as quirks
    #7/#11, but with no equivalent to preserve: this function fits
    whatever DataFrame it's handed, so which condition gets fit is
    determined entirely by what the caller passed to
    `pacejka.segmenting.segment_condition` beforehand.
    """
    sl = condition["SL"].to_numpy(dtype=float)

    def _smoothed(channel: str) -> np.ndarray:
        y = condition[channel].to_numpy(dtype=float)
        spline = fit_smoothing_spline(sl, y, _SMOOTHING_PARAMS[channel])
        return spline(SL_GRID)

    return KappaSweepSplines(
        sl_grid=SL_GRID,
        fx=_smoothed("FX"),
        fy=_smoothed("FY"),
        mz=_smoothed("MZ"),
        vc=_smoothed("Vc"),
    )


# ---------------------------------------------------------------------------
# Pacejka_Term_Finder_FX_V4_Redo.m -- pure-slip stages only (see module
# docstring for the deferred combined-slip stages)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FxSweepPoint:
    """One nominal condition's smoothed kappa -> Fx curve, in SI units,
    tagged with the physical load/camber it was recorded at. Build with
    `sweep_point_from_kappa_sweep`.
    """

    fz_n: float
    gamma_rad: float
    kappa: np.ndarray
    fx_n: np.ndarray


def sweep_point_from_kappa_sweep(splines: KappaSweepSplines, fz_lbf: float, ia_deg: float) -> FxSweepPoint:
    """Build an FxSweepPoint from `fit_kappa_sweep`'s output plus the
    segmented condition's nominal load (lbf) and camber (deg).

    `gamma_rad` is the raw camber angle in radians, not `sin(camber)`
    (see `pacejka.model.FxCoefficients`' docstring on why this differs
    from Fy/Mz's `gamma_star` convention) -- matching the original's own
    `gamma = gamma_vals*pi/180` literally.

    Also fixes a real unit-conversion bug, the same shape as quirk #10:
    the original's Base and dFz stages both convert their smoothed `FX`
    ydata from lbf to N (`.*4.448`) before fitting, but the dIA stage's
    ydata does not, even though `dIAFit.F_x` still computes force in N --
    a ~4.448x mismatch. Fixed here by always converting, regardless of
    which stage ends up consuming this point.
    """
    return FxSweepPoint(
        fz_n=fz_lbf * LBF_TO_N,
        gamma_rad=float(np.radians(ia_deg)),
        kappa=splines.sl_grid,
        fx_n=splines.fx * LBF_TO_N,
    )


# p0 in the MATLAB source.
_P0 = dict(
    Cx1=1.5, Dx1=3.3, Dx2=-1.75, Dx3=2.0,
    Ex1=0.4, Ex2=-0.04, Ex3=-0.4, Ex4=1.2,
    Hsx1=0.0, Hsx2=0.0,
    Kx1=60.0, Kx2=-10.0, Kx3=-0.1,
    Vsx1=0.0, Vsx2=0.0,
)

# Base coefficients: historically fit alone, at the nominal load and zero
# camber only (Pacejka_Term_Finder_FX_V4_Redo.m's Xb(1..7)/lbb/ubb, field
# order and bounds still match that exactly -- "Increased limits" per the
# source's own comment, i.e. these are already a widened-from-some-earlier
# version bracket, not the original-original values). Three of the seven
# p0 values fall outside their own bound here -- MATLAB's lsqcurvefit
# silently clips an infeasible x0 to the nearest bound (replicated by
# pacejka.fitting.fit_stage) rather than erroring, so this doesn't crash,
# but it's worth flagging by severity:
#   - Dx1=3.3 vs bound (2.5, 3.0): mild, 10% overshoot -- same class as
#     FY's Dy3 p0 overshoot, harmless once clipped.
#   - Ex1=0.4 vs bound (-0.6, 0.2): mild, 2x overshoot.
#   - Ex4=1.2 vs bound (-0.1, 0.1): severe, 12x overshoot -- Ex4 is meant
#     to be a small sign-asymmetry correction (it multiplies
#     `sign(kappa)`), so a p0 this far outside its own tight bound smells
#     like FY's Ky1 wrong-bound bug (quirk #9). Unlike Ky1, there's no
#     clear physical argument here for what the bound/guess *should* be
#     (Ky1's fix was justified by "cornering stiffness must be positive";
#     Ex4 has no equally clear constraint), so this is left as the
#     original MATLAB bound (clipped same as MATLAB would) rather than a
#     unilateral "fix" -- flagged for the team to re-derive Ex4's correct
#     p0/bounds from a real fit, not treated as validated.
#
# As of the partial-staged fit below, fit *jointly* with the dIA field --
# see `fit_fx_coefficients` -- so "Base stage" is no longer a separate
# optimization pass, just the name for this field group.
_BASE_FIELDS = ("Cx1", "Dx1", "Ex1", "Ex4", "Kx1", "Hsx1", "Vsx1")
_BASE_BOUNDS = (
    (1.2, 2.2),
    (2.5, 3.0),
    (-0.6, 0.2),
    (-0.1, 0.1),
    (0.0, 600.0),
    (-0.01, 0.01),
    (-100.0, 100.0),
)

# dFz coefficients: fit across every tested load at zero camber, as its
# own, separate stage -- the one part of the original Base/dFz/dIA split
# this port keeps staged (see `fit_fx_coefficients`). The original
# hardcodes `Fz_vals = [50]` and only runs the dFz `lsqcurvefit` call
# *inside* `if Fz_vals(n) == Fz_nom` -- i.e. for any `Fz_nom` other than
# 50, the loop body (including the assignment to `Xf_out`) never
# executes at all, and the very next section (dIA) unconditionally
# references `Xf_out`, which would error as an undefined variable. This
# is a more severe version of quirk #7 (FY's equivalent silently fits the
# wrong, always-50 condition; here a non-50 `Fz_nom` would simply crash
# the whole function). Fixed the same way as #7: real data spanning
# multiple tested loads, with no hardcoded gate. This stage's original
# `lsqcurvefit` call *does* apply real bounds (unlike FY's `nlinfit`
# dFz stage -- same distinction as Mz's quirk #14), so bounded, no robust
# loss, matching Mz's treatment.
#
# `Ex3`'s bound (0.0, 0.0) is a deliberate zero-width pin (same mechanism
# as FY's Dy1/Mz's Bz4), overriding its mismatched p0=-0.4 -- not fit.
_DFZ_FIELDS = ("Dx2", "Ex2", "Ex3", "Kx2", "Kx3", "Hsx2", "Vsx2")
_DFZ_BOUNDS = (
    (-50.0, 0.0),
    (0.0, 0.5),
    (0.0, 0.0),
    (-30.0, 0.0),
    (0.0, 0.5),
    (-0.001, 0.001),
    (-1.0, 0.0),
)

# dIA coefficient: historically fit alone, with Base and dFz already
# frozen. Two independent hardcoding bugs here, both fixed the same way
# (a real multi-camber sweep at the reference load, via `camber_sweep`):
#   - `gamma_vals = [2]`: a single nonzero camber, not a sweep -- milder
#     than FY's dIA quirk #11 (gamma=0 there made every camber term
#     exactly zero-effect; here Dx3 multiplies gamma**2, which is nonzero
#     at gamma=2 deg, so it does get *some* signal), but still only one
#     data point for one free parameter, which happens to be just enough
#     to identify Dx3 alone (there's only the one dIA-stage coefficient
#     here, unlike Mz's dIA stage with 7), so this is the mildest instance
#     of the pattern across Fy/Mz/Fx.
#   - `Fz_vals = [150]`, hardcoded independently of `Fz_nom` (unlike the
#     Base/dFz stages above, which key off `Fz_nom` directly) -- so the
#     original's dIA stage silently fits at Fz=150 lbf regardless of what
#     load the Base/dFz stages were just fit at, a mismatch with no
#     equivalent in FY/MZ's dIA stages (both of those correctly reuse the
#     same reference load throughout). Fixed by using the same
#     `base.fz_n` reference load as everything else, via `camber_sweep`
#     being recorded at the reference load like FY/MZ's camber sweeps.
_DIA_FIELDS = ("Dx3",)
_DIA_BOUNDS = ((0.0, 300.0),)


@dataclass(frozen=True)
class FxFitResult:
    """Fitted Magic Formula pure-longitudinal-slip coefficients plus the
    fitted curve at each input condition, for diagnostic plotting."""

    coefficients: FxCoefficients
    base_fit_fx_n: np.ndarray
    load_sweep_fit_fx_n: list[np.ndarray]
    camber_sweep_fit_fx_n: list[np.ndarray]


def _fit_fx_stage(field_names, x0, points, fz0_prime, fixed_values, bounds=None):
    """Fx-specific residual closure over `pacejka.fitting.fit_stage`."""
    kappa = np.concatenate([p.kappa for p in points])
    fz_n = np.concatenate([np.full_like(p.kappa, p.fz_n) for p in points])
    gamma_rad = np.concatenate([np.full_like(p.kappa, p.gamma_rad) for p in points])
    target_fx_n = np.concatenate([p.fx_n for p in points])

    def residuals(x):
        values = dict(fixed_values)
        values.update(zip(field_names, x))
        fxo = fx_pure(fz_n, fz0_prime, gamma_rad, kappa, FxCoefficients(**values))
        return fxo - target_fx_n

    fitted_x = fit_stage(residuals, x0, bounds=bounds)
    return dict(zip(field_names, fitted_x))


def fit_fx_coefficients(
    base: FxSweepPoint,
    load_sweep: Sequence[FxSweepPoint],
    camber_sweep: Sequence[FxSweepPoint],
) -> FxFitResult:
    """Fit the Magic Formula pure-longitudinal-slip coefficients.

    `base` anchors the reference load Fz0' (dfz=0) and zero camber, and
    is used (jointly with `camber_sweep`) for the Base stage. `load_sweep`
    should span every nominal load tested in the session at zero camber
    (including `base`'s own condition) and is used for the dFz stage.
    `camber_sweep` should span every nominal camber angle tested at the
    reference load (including zero camber, i.e. `base`'s own condition)
    and is used for the dIA stage.

    Port of Pacejka_Term_Finder_FX_V4_Redo.m's pure-slip Base/dFz/dIA
    stages only -- see the module docstring for the deferred combined-slip
    stages, and this module's `_BASE_BOUNDS`/`_DFZ_FIELDS`/`_DIA_FIELDS`
    for the specific bugs found and fixed (the dFz stage's
    hardcoded-single-load gate that would crash for any Fz_nom != 50, the
    dIA stage's single-camber-value *and* mismatched-reference-load bugs).

    Follows the same partial-staged hybrid already validated and promoted
    for `pacejka.fitters.fy.fit_fy_coefficients`/
    `pacejka.fitters.mz.fit_mz_coefficients` (see MODEL_CHANGES.md's
    2026-10-05 entry): Base and dIA are fit *jointly*, against the
    reference condition plus the full camber sweep together, rather than
    Base alone (blind to camber) frozen before dIA runs. The dFz stage is
    unchanged -- same fields, bounds (bounded, matching the original's
    `lsqcurvefit`), and load sweep data, just starting from the
    jointly-fit Base values.
    """
    fz0_prime = base.fz_n
    coeffs_values = dict(_P0)

    # Stage 1: Base + dIA fit jointly, against the reference condition
    # plus the full camber sweep.
    base_dia_fields = _BASE_FIELDS + _DIA_FIELDS
    base_dia_bounds = _BASE_BOUNDS + _DIA_BOUNDS
    free_fields, free_bounds, fixed_from_bounds = split_fixed_fields(base_dia_fields, base_dia_bounds, coeffs_values)
    coeffs_values.update(fixed_from_bounds)
    camber_points = [base] + list(camber_sweep)
    x0 = [coeffs_values[name] for name in free_fields]
    fixed = {k: v for k, v in coeffs_values.items() if k not in free_fields}
    coeffs_values.update(_fit_fx_stage(free_fields, x0, camber_points, fz0_prime, fixed, bounds=free_bounds))

    # Stage 2: dFz against the load sweep -- bounded, no robust loss,
    # matching the original's bounded lsqcurvefit call (see _DFZ_FIELDS).
    free_fields, free_bounds, fixed_from_bounds = split_fixed_fields(_DFZ_FIELDS, _DFZ_BOUNDS, coeffs_values)
    coeffs_values.update(fixed_from_bounds)
    x0 = [coeffs_values[name] for name in free_fields]
    fixed = {k: v for k, v in coeffs_values.items() if k not in free_fields}
    coeffs_values.update(_fit_fx_stage(free_fields, x0, load_sweep, fz0_prime, fixed, bounds=free_bounds))

    final_coeffs = FxCoefficients(**coeffs_values)
    base_fit_fx_n = fx_pure(base.fz_n, fz0_prime, base.gamma_rad, base.kappa, final_coeffs)
    load_sweep_fit_fx_n = [fx_pure(p.fz_n, fz0_prime, p.gamma_rad, p.kappa, final_coeffs) for p in load_sweep]
    camber_sweep_fit_fx_n = [fx_pure(p.fz_n, fz0_prime, p.gamma_rad, p.kappa, final_coeffs) for p in camber_sweep]

    return FxFitResult(
        coefficients=final_coeffs,
        base_fit_fx_n=base_fit_fx_n,
        load_sweep_fit_fx_n=load_sweep_fit_fx_n,
        camber_sweep_fit_fx_n=camber_sweep_fit_fx_n,
    )
