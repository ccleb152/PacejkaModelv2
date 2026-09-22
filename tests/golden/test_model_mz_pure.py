"""Golden tests for pacejka.model.mz_pure.

Like fy_pure, mz_pure is a pure, deterministic function of fixed
coefficients and state, so it gets exact-value comparison per
MIGRATION_PLAN.md Sec.5's "deterministic functions" tolerance regime.
Expected values are hand-derived: computed with an independent,
freshly-written transcription of the same equation (see the session's
derivation), not by importing pacejka.model itself.
"""

import numpy as np
import pytest

from pacejka.model import MzCoefficients, mz_pure

COEFFS = MzCoefficients(
    Hz1=0.001, Hz2=0.002, Hz3=0.003, Hz4=0.0,
    Bz1=10.0, Bz2=2.0, Bz3=0.5, Bz4=0.2, Bz5=0.1,
    Bz9=1.0, Bz10=-0.5,
    Cz1=1.1,
    Dz1=0.05, Dz2=0.01, Dz3=0.02, Dz4=0.01,
    Dz6=0.03, Dz7=0.005, Dz8=0.01, Dz9=0.0, Dz10=0.02, Dz11=0.0,
    Ez1=0.5, Ez2=0.1, Ez3=0.05, Ez4=0.3, Ez5=0.02,
)

FZ0_PRIME = 150 * 4.448
RO = 9 * 0.0254


def _cos_alpha_p(alpha_rad):
    vcx = 25 * 0.447
    v = vcx / np.cos(alpha_rad)
    return vcx / (v + 0.1)


def test_mz_pure_matches_hand_derived_reference():
    fz = 200 * 4.448
    gamma_star = np.sin(np.radians(2.0))
    alpha = np.array([0.05])
    cos_alpha_p = _cos_alpha_p(alpha)

    result = mz_pure(
        fz, FZ0_PRIME, RO, gamma_star, alpha, cos_alpha_p,
        fy_cy=1.6, fy_by=30.0, s_hf=0.02, fy_og0=500.0, coeffs=COEFFS,
    )
    assert result == pytest.approx([0.315231], rel=1e-5)


def test_alpha_r_fix_produces_a_materially_different_result_than_the_original_bug():
    # Regression test for the alpha_r/alpha_t bug documented in mz_pure's
    # docstring and CLAUDE.md: the residual-moment term must use alpha_r
    # (shifted by s_hf, from the FY fit), not alpha_t (shifted by the
    # locally-fit S_Ht) -- the original MATLAB uses alpha_t everywhere,
    # a copy-paste bug. Using a deliberately different s_hf here (0.5,
    # far from S_Ht's ~0.002) makes the two diverge sharply, proving the
    # implementation actually threads alpha_r through, not alpha_t twice.
    fz = 200 * 4.448
    gamma_star = np.sin(np.radians(2.0))
    alpha = np.array([0.05])
    cos_alpha_p = _cos_alpha_p(alpha)

    result_with_far_s_hf = mz_pure(
        fz, FZ0_PRIME, RO, gamma_star, alpha, cos_alpha_p,
        fy_cy=1.6, fy_by=30.0, s_hf=0.5, fy_og0=500.0, coeffs=COEFFS,
    )
    result_with_near_zero_s_hf = mz_pure(
        fz, FZ0_PRIME, RO, gamma_star, alpha, cos_alpha_p,
        fy_cy=1.6, fy_by=30.0, s_hf=0.0, fy_og0=500.0, coeffs=COEFFS,
    )
    # If alpha_t were used instead of alpha_r, s_hf would have zero effect
    # on the result at all -- these two calls would be identical.
    assert not np.allclose(result_with_far_s_hf, result_with_near_zero_s_hf)


def test_fy_og0_scales_the_trail_term_but_not_the_residual_term():
    # A sanity check on which piece uses which Fy: fy_og0 (the zero-camber
    # lateral force) only multiplies the trail term (mzo_p = -trail*fy_og0),
    # so doubling it should not simply double the whole Mz (the residual
    # term is unaffected).
    fz = 200 * 4.448
    gamma_star = np.sin(np.radians(2.0))
    alpha = np.array([0.05])
    cos_alpha_p = _cos_alpha_p(alpha)

    base = mz_pure(
        fz, FZ0_PRIME, RO, gamma_star, alpha, cos_alpha_p,
        fy_cy=1.6, fy_by=30.0, s_hf=0.02, fy_og0=500.0, coeffs=COEFFS,
    )
    doubled_og0 = mz_pure(
        fz, FZ0_PRIME, RO, gamma_star, alpha, cos_alpha_p,
        fy_cy=1.6, fy_by=30.0, s_hf=0.02, fy_og0=1000.0, coeffs=COEFFS,
    )
    assert not np.allclose(np.asarray(doubled_og0), 2 * np.asarray(base))
