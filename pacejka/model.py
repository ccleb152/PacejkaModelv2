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


@dataclass(frozen=True)
class FyTerms:
    """Every intermediate quantity from the pure-lateral-slip equation, not
    just the final force -- `Pacejka_Term_Finder_MZ_V1_redo.m`'s aligning-
    moment equation reuses `k_yalpha`/`cy`/`by`/`s_hy`/`s_vy` directly
    (via its own `ParameterLoad`, a fourth near-duplicate of this same
    equation in the MATLAB source), not just `fyo`. See `fy_terms`.
    """

    k_yalpha: np.ndarray
    k_ygo: np.ndarray
    s_hy: np.ndarray
    alpha_y: np.ndarray
    cy: float
    mu_y: np.ndarray
    dy: np.ndarray
    ey: np.ndarray
    by: np.ndarray
    s_vy: np.ndarray
    fyo: np.ndarray

    @property
    def s_hf(self):
        """`S_Hf = S_Hy + S_Vy / (K_yalpha + epsilon_k)` -- the combined
        horizontal shift `Pacejka_Term_Finder_MZ_V1_redo.m`'s `alpha_r`
        uses (see `mz_pure`), distinct from the trail term's own `S_Ht`.
        """
        return self.s_hy + self.s_vy / (self.k_yalpha + _EPSILON_K)


def fy_terms(fz, fz0_prime, gamma_star, alpha_star, coeffs: FyCoefficients, dpi=0.0) -> FyTerms:
    """Pure-lateral-slip Magic Formula equation, returning every
    intermediate quantity (see `FyTerms`) rather than just the final
    force. `fy_pure` is a thin wrapper around this for the common case of
    only wanting `(fyo, mu_y)`.

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

    return FyTerms(
        k_yalpha=k_yalpha, k_ygo=k_ygo, s_hy=s_hy, alpha_y=alpha_y, cy=cy, mu_y=mu_y,
        dy=dy, ey=ey, by=by, s_vy=s_vy, fyo=fyo,
    )


def fy_pure(fz, fz0_prime, gamma_star, alpha_star, coeffs: FyCoefficients, dpi=0.0):
    """Pure-lateral-slip Magic Formula lateral force Fy0.

    Returns `(fyo, mu_y)`, matching the original `Pacejka_FY`'s two-output
    signature -- `mu_y` is returned separately because
    `Pacejka_Term_Finder_MZ_V1_redo.m`'s aligning-moment equation needs it
    directly, not just the final force. See `fy_terms` for every other
    intermediate quantity that equation also needs.
    """
    terms = fy_terms(fz, fz0_prime, gamma_star, alpha_star, coeffs, dpi)
    return terms.fyo, terms.mu_y


@dataclass(frozen=True)
class MzCoefficients:
    """Fitted Magic Formula aligning-moment coefficients.

    Field names match the MATLAB `q0`/`ParameterList` `Variable` strings,
    with one deliberate exception: MATLAB names the 10th `Bz` coefficient
    `Bz1o` (letter O, not the digit 0) -- a typo, not a versioning
    convention. Named `Bz10` here, matching the standard MF-Tire naming it
    was clearly supposed to follow; nothing else changes.

    `Ez2` is used inside the *residual-moment magnitude* term (`Dr`), not
    anywhere in the trail-curvature term (`Et`) its name would suggest --
    a real oddity in the source's naming, not a Python-port choice, kept
    as-is for fidelity to the original parameter table. See CLAUDE.md.

    `Hz4`, `Dz9`, `Dz11` (the load-camber cross term) are never fit --
    same rationale as `FyCoefficients`' unfit `Ky7`/`Vsy4`, see
    `MzFitResult` in `pacejka.fitters.mz`.
    """

    Hz1: float
    Hz2: float
    Hz3: float
    Hz4: float
    Bz1: float
    Bz2: float
    Bz3: float
    Bz4: float
    Bz5: float
    Bz9: float
    Bz10: float
    Cz1: float
    Dz1: float
    Dz2: float
    Dz3: float
    Dz4: float
    Dz6: float
    Dz7: float
    Dz8: float
    Dz9: float
    Dz10: float
    Dz11: float
    Ez1: float
    Ez2: float
    Ez3: float
    Ez4: float
    Ez5: float


def mz_pure(fz, fz0_prime, ro, gamma_star, alpha_star, cos_alpha_p, fy_cy, fy_by, s_hf, fy_og0, coeffs: MzCoefficients):
    """Magic Formula aligning moment Mz0 (MF-Tire 6.1).

    `fz`/`fz0_prime`/`gamma_star`/`alpha_star` mean the same as in
    `fy_pure`. `ro` is the tire's (loaded) radius (m). `cos_alpha_p` is a
    numerically-regularized `cos(alpha)` (matches the original's
    `Vcx/(Vcx/cos(Alpha) + 0.1)` exactly, not simplified to `cos(alpha)`,
    since the two aren't quite equal). `fy_cy`, `fy_by`, `s_hf`, `fy_og0`
    come from the already-fit FY coefficients via `fy_terms` -- `fy_cy`,
    `fy_by`, and `s_hf` (that call's own `.s_hf` property) at this call's
    actual `gamma_star`, and `fy_og0` as the *separate* `fyo` from
    `fy_terms` called with `gamma_star=0`
    (the standard MF-Tire aligning-moment equation always uses the
    zero-camber lateral force for the trail term, regardless of the
    actual camber -- this is standard theory, not a bug).

    Fixes a real bug relative to the standard MF-Tire 6.1 formulation
    (which this file's MATLAB header cites): the residual-moment term
    should use `alpha_r = alpha_star + s_hf`, a *different* shifted slip
    angle than the trail term's `alpha_t = alpha_star + S_Ht`. The
    original computes `alpha_r` in every one of its four fitting stages
    and then never uses it -- every stage's residual-moment formula uses
    `alpha_t` instead, identically. There's no plausible intentional
    reading of "compute a variable, use it nowhere, ever" -- this reads
    as a copy-paste error, most likely from duplicating the trail term's
    line and forgetting to swap the shifted angle. Fixed here: the
    residual-moment term below uses `alpha_r`. See CLAUDE.md.
    """
    p = coeffs
    dfz = (fz - fz0_prime) / fz0_prime

    s_ht = p.Hz1 + p.Hz2 * dfz + (p.Hz3 + p.Hz4 * dfz) * gamma_star
    alpha_t = alpha_star + s_ht
    alpha_r = alpha_star + s_hf

    bt = (p.Bz1 + p.Bz2 * dfz + p.Bz3 * dfz**2) * (1 + p.Bz4 + p.Bz5 * np.abs(gamma_star))
    ct = p.Cz1
    dto = fz * (ro / fz0_prime) * (p.Dz1 + p.Dz7 * dfz)
    dt = dto * (1 + p.Dz3 * np.abs(gamma_star) + p.Dz4 * gamma_star**2)
    et = (p.Ez1 + p.Ez3 * dfz) * (
        1 + (p.Ez4 + p.Ez5 * gamma_star) * (2 / np.pi) * np.arctan(bt * ct * alpha_t)
    )
    br = p.Bz9 + p.Bz10 * fy_cy * fy_by
    cr = 1
    dr = (
        fz * ro
        * (
            p.Dz6 + p.Ez2 * dfz
            + ((p.Dz8 + p.Dz9 * dfz) + (p.Dz10 + p.Dz11 * dfz) * np.abs(gamma_star)) * gamma_star
        )
        * cos_alpha_p
    )

    trail = dt * np.cos(ct * np.arctan(bt * alpha_t - et * (bt * alpha_t - np.arctan(bt * alpha_t)))) * cos_alpha_p
    mzo_p = -trail * fy_og0
    mzro = dr * np.cos(cr * np.arctan(br * alpha_r)) * cos_alpha_p
    return mzo_p + mzro
