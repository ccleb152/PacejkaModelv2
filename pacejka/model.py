"""Shared Magic Formula (Pacejka) equations.

Consolidates the core pure-lateral-slip equation that appears three times
in the MATLAB source: inline as a sequence of anonymous-function stages in
`Pacejka_Term_Finder_FY_V3.m` (Base/dFz/dIA/dIAxdFz, each building only
part of the full equation with the other terms held fixed for that fitting
stage), in full as a nested `Pacejka_FY` function inside
`Pacejka_Term_Finder_FX_V4_Redo.m` (used there to get a pure-slip Fy0 for
its combined-slip lateral terms), and again, near-identically, inside
`Pacejka_Term_Finder_MZ_V1_redo.m`'s own `ParameterLoad` local function
(used there to get the aligning-moment equation's K_yalpha/Cy/mu_y/By/Fy_o
inputs). This is one of the few places the Python port deliberately does
*not* mirror MATLAB's file structure -- see CLAUDE.md's migration
workflow.

Kept as pure numpy functions of (state, coefficients) -> force, with no
pandas/Streamlit dependency, since that's the interface a future lapsim
integration would actually call (see CLAUDE.md's "Roadmap beyond Phase 1").
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_EPSILON_Y = 0.1
_EPSILON_K = 0.1


@dataclass(frozen=True)
class FyCoefficients:
    """Fitted Magic Formula pure-lateral-slip coefficients.

    Field names and casing match the `Variable` strings the MATLAB
    ParameterList tables use verbatim, including the lowercase `py1..py5`
    (inconsistent capitalization next to `Cy1`/`Dy1`/etc., but that's the
    source's own convention, and it's what a future parameters.py
    read/write module will key by).

    `py1..py5` scale a normalized-pressure-deviation term (`dpi` in
    `fy_pure`) that none of the current MATLAB fitting stages ever
    actually fit -- see `fy_pure`'s docstring.
    """

    Cy1: float
    Dy1: float
    Dy2: float
    Dy3: float
    Ey1: float
    Ey2: float
    Ey3: float
    Ey4: float
    Ey5: float
    Hsy1: float
    Hsy2: float
    Ky1: float
    Ky2: float
    Ky3: float
    Ky4: float
    Ky5: float
    Ky6: float
    Ky7: float
    py1: float
    py2: float
    py3: float
    py4: float
    py5: float
    Vsy1: float
    Vsy2: float
    Vsy3: float
    Vsy4: float


def fy_pure(fz, fz0_prime, gamma_star, alpha_star, coeffs: FyCoefficients, dpi=0.0):
    """Pure-lateral-slip Magic Formula lateral force Fy0.

    Arguments mirror the MATLAB `Pacejka_FY` nested function exactly:
    `fz` is the actual normal load (N), `fz0_prime` the reference/nominal
    load used to normalize it (`dfz = (fz - fz0_prime) / fz0_prime`),
    `gamma_star = sin(camber angle)`, `alpha_star` the slip angle (rad,
    already the "raw" slip angle -- the horizontal shift `S_Hy` is added
    internally, same as the original).

    `dpi` (normalized pressure deviation) defaults to 0.0: none of the
    current fitting stages in `Pacejka_Term_Finder_FY_V3.m` ever set it
    away from that (its "dPi Parameters" stage is an unfit no-op -- see
    CLAUDE.md), but the equation itself supports a pressure term via
    `coeffs.py1..py5`, so it's exposed as a real parameter here rather
    than hardcoding the current fitting pipeline's limitation into the
    shared math.

    Returns `(fyo, mu_y)`, matching the original's two-output signature --
    `mu_y` is returned separately because
    `Pacejka_Term_Finder_MZ_V1_redo.m`'s aligning-moment equation needs it
    directly, not just the final force.

    Verified against the term finder's own per-stage closures at their
    respective special cases: gamma_star=0 & fz=fz0_prime collapses to
    the "Base" stage's `BaseFit.F_yo`; gamma_star=0 & fz!=fz0_prime to the
    "dFz" stage's `dFzFit.F_yo`; each stage's free parameters map onto a
    subset of `coeffs`' fields exactly (e.g. Base's `Xb(6),Xb(7),Xb(8)`
    are `Ky1,Ky2,Ky4`) -- see the module's git history for the derivation.
    """
    p = coeffs
    dfz = (fz - fz0_prime) / fz0_prime

    k_yalpha = (
        p.Ky1 * fz0_prime * (1 + p.py1 * dpi) * (1 - p.Ky3 * np.abs(gamma_star))
        * np.sin(
            p.Ky4
            * np.arctan((fz / fz0_prime) / ((p.Ky2 + p.Ky5 * gamma_star**2) * (1 + p.py2 * dpi)))
        )
    )
    s_vy_gamma = fz * (p.Vsy3 + p.Vsy4 * dfz) * gamma_star
    k_ygo = fz * (p.Ky6 + p.Ky7 * dfz)
    s_hy = (p.Hsy1 + p.Hsy2 * dfz) + (k_ygo * gamma_star - s_vy_gamma) / (k_yalpha + _EPSILON_K)
    alpha_y = alpha_star + s_hy

    cy = p.Cy1
    mu_y = (p.Dy1 + p.Dy2 * dfz) * (1 + p.py3 * dpi + p.py4 * dpi**2) * (1 - p.Dy3 * gamma_star**2)
    dy = mu_y * fz
    ey = (p.Ey1 + p.Ey2 * dfz) * (
        1 + p.Ey5 * gamma_star**2 - (p.Ey3 + p.Ey4 * gamma_star) * np.sign(alpha_star)
    )
    by = k_yalpha / (cy * dy + _EPSILON_Y)
    s_vy = fz * (p.Vsy1 + p.Vsy2 * dfz) + s_vy_gamma

    fyo = dy * np.sin(cy * np.arctan(by * alpha_y - ey * (by * alpha_y - np.arctan(by * alpha_y)))) + s_vy
    return fyo, mu_y
