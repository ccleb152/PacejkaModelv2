"""Tests for pacejka.fitters.fx.fit_combined_fx_coefficients (port of
Pacejka_Term_Finder_FX_V4_Redo.m's combined-slip Fx stage, CBaseFit/
CdFzFit/CdIAFit).

No MATLAB access in this environment -- per MIGRATION_PLAN.md Sec.5,
optimizer-driven fits are verified by fit quality against known-good
synthetic data, not exact coefficient recovery (CLAUDE.md quirk #18).

TRUE_COMB chooses values within every bound in pacejka/fitters/fx.py's
_COMBINED_BASE_BOUNDS/_COMBINED_DFZ_BOUNDS/_COMBINED_DIA_BOUNDS, close
enough to the committed all-defaults-ish p0 (_COMBINED_P0) that the
optimizer converges to the noise level rather than a worse local
minimum -- same generic-p0 sensitivity as test_fx_term_finder.py's
TRUE_COEFFS, and documented in pacejka/fitters/fy.py's
_COMBINED_FY_BASE_FIELDS comment for the Fy side of this same stage.
"""

import numpy as np
import pytest

from pacejka.model import FxCoefficients, FxCombinedCoefficients, fx_combined, fx_pure
from pacejka.fitters.fx import (
    LBF_TO_N,
    CombinedFxSweepPoint,
    fit_combined_fx_coefficients,
)

PURE_COEFFS = FxCoefficients(
    Cx1=1.6, Dx1=2.8, Dx2=-3.0, Dx3=10.0,
    Ex1=-0.1, Ex2=0.05, Ex3=0.0, Ex4=0.02,
    Hsx1=0.001, Hsx2=0.0002,
    Kx1=80.0, Kx2=-8.0, Kx3=0.02,
    Vsx1=2.0, Vsx2=-0.05,
)

TRUE_COMB = FxCombinedCoefficients(
    Bx1=11.0, Bx2=13.0, Bx3=250.0, Cx1=0.5, Ex1=-0.4, Ex2=3.0, Hsx1=0.0002,
)

FZ0_PRIME = 150 * LBF_TO_N
KAPPA = np.linspace(-0.15, 0.13, 200)
NOISE_SCALE = 5.0  # N


def _make_point(rng, fz_lbf, ia_deg, sa_deg):
    fz_n = fz_lbf * LBF_TO_N
    gamma_rad = np.radians(ia_deg)
    alpha_rad = np.radians(sa_deg)
    fxc = fx_combined(fz_n, FZ0_PRIME, gamma_rad, KAPPA, alpha_rad, PURE_COEFFS, TRUE_COMB)
    noisy = fxc + rng.normal(scale=NOISE_SCALE, size=fxc.shape)
    return CombinedFxSweepPoint(fz_n=fz_n, gamma_rad=gamma_rad, alpha_rad=alpha_rad, kappa=KAPPA, fx_n=noisy)


@pytest.fixture
def synthetic_dataset():
    rng = np.random.RandomState(0)
    base = _make_point(rng, 150, 0, 0)
    alpha_sweep = [_make_point(rng, 150, 0, sa) for sa in (-3, -6)]
    load_sweep = [_make_point(rng, fz, 0, -3) for fz in (50, 100, 150, 200, 250)]
    camber_sweep = [_make_point(rng, 150, ia, -3) for ia in (0, 2, 4)]
    return base, alpha_sweep, load_sweep, camber_sweep


def _rmse(a, b):
    return float(np.sqrt(np.mean((a - b) ** 2)))


def test_fitted_curve_matches_noise_level_at_every_condition(synthetic_dataset):
    base, alpha_sweep, load_sweep, camber_sweep = synthetic_dataset
    result = fit_combined_fx_coefficients(PURE_COEFFS, base, alpha_sweep, load_sweep, camber_sweep)

    assert _rmse(result.base_fit_fx_n, base.fx_n) < 3 * NOISE_SCALE

    for point, fit in zip(alpha_sweep, result.alpha_sweep_fit_fx_n):
        assert _rmse(fit, point.fx_n) < 3 * NOISE_SCALE

    for point, fit in zip(load_sweep, result.load_sweep_fit_fx_n):
        assert _rmse(fit, point.fx_n) < 5 * NOISE_SCALE

    for point, fit in zip(camber_sweep, result.camber_sweep_fit_fx_n):
        assert _rmse(fit, point.fx_n) < 3 * NOISE_SCALE


def test_alpha_zero_degenerates_to_identity_weighting():
    # Regression test for the exact G_xa==1 identity (see
    # pacejka.model.fx_combined's docstring and CLAUDE.md quirk #24/#25):
    # at alpha=0, combined-slip Fx must equal the pure-slip curve
    # *regardless* of the combined-slip coefficients -- this is the real
    # bug the original's hardcoded SA_vals=0 caused, not merely a weakly
    # identified fit.
    fz_n = 150 * LBF_TO_N
    fx0 = fx_pure(fz_n, FZ0_PRIME, 0.0, KAPPA, PURE_COEFFS)
    fxc = fx_combined(fz_n, FZ0_PRIME, 0.0, KAPPA, 0.0, PURE_COEFFS, TRUE_COMB)
    assert np.allclose(fxc, fx0)

    other_comb = FxCombinedCoefficients(Bx1=9.0, Bx2=10.0, Bx3=400.0, Cx1=0.9, Ex1=-0.8, Ex2=-5.0, Hsx1=-0.0005)
    fxc_other = fx_combined(fz_n, FZ0_PRIME, 0.0, KAPPA, 0.0, PURE_COEFFS, other_comb)
    assert np.allclose(fxc_other, fx0)


def test_single_alpha_point_cannot_identify_base_coefficients(synthetic_dataset):
    # A degenerate regression test mirroring test_fx_term_finder.py's
    # test_single_load_sweep_cannot_identify_load_sensitivity: fitting
    # against `base` alone (alpha=0 only, no real alpha_sweep/
    # camber_sweep data) can't move the Base-stage coefficients off
    # their p0 in any way that reflects the true alpha-dependence --
    # confirming the alpha_sweep data is actually doing the identifying
    # work in the main test above, not just along for the ride.
    base, _, load_sweep, _ = synthetic_dataset
    degenerate = fit_combined_fx_coefficients(PURE_COEFFS, base, [], load_sweep, [])
    # Every Base/dIA-stage field has zero effect on the alpha=0-only
    # training data's objective (same G_xa==1 identity as above), so the
    # optimizer can't move them at all: they stay exactly at their p0
    # initial guess, clipped into bounds where p0 itself is infeasible
    # (see pacejka.fitting.fit_stage's docstring on replicating MATLAB's
    # silent infeasible-x0 clipping; _COMBINED_P0's Bx1/Bx2/Ex1/Bx3 all
    # overshoot their own bounds -- see _COMBINED_BASE_BOUNDS/
    # _COMBINED_DIA_BOUNDS's comment).
    expected_clipped = dict(Bx1=8.0, Bx2=10.0, Bx3=200.0, Cx1=1.0, Ex1=0.0, Hsx1=0.0)
    for field, expected in expected_clipped.items():
        assert getattr(degenerate.coefficients, field) == pytest.approx(expected, abs=1e-6)


def test_camber_sweep_identifies_bx3(synthetic_dataset):
    # Bx3 (the sole dIA-stage coefficient) multiplies gamma_rad**2 inside
    # Bxa, so the camber sweep (recorded at the nonzero reference slip
    # angle, per fit_combined_fx_coefficients' own docstring) should give
    # it real signal.
    base, alpha_sweep, load_sweep, camber_sweep = synthetic_dataset
    result = fit_combined_fx_coefficients(PURE_COEFFS, base, alpha_sweep, load_sweep, camber_sweep)
    assert result.coefficients.Bx3 == pytest.approx(TRUE_COMB.Bx3, abs=30.0)


def test_load_sweep_identifies_ex2(synthetic_dataset):
    # Ex2 (the sole dFz-stage coefficient) multiplies dfz inside Exa, so
    # the load sweep (recorded at the nonzero reference slip angle)
    # should give it real signal, unlike a degenerate single-load dFz
    # stage would.
    base, alpha_sweep, load_sweep, camber_sweep = synthetic_dataset
    result = fit_combined_fx_coefficients(PURE_COEFFS, base, alpha_sweep, load_sweep, camber_sweep)
    assert result.coefficients.Ex2 == pytest.approx(TRUE_COMB.Ex2, abs=3.0)
