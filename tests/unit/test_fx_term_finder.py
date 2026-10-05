"""Tests for pacejka.fitters.fx.fit_fx_coefficients (port of
Pacejka_Term_Finder_FX_V4_Redo.m's pure-slip Base/dFz/dIA stages).

No MATLAB access in this environment -- see pacejka/fitters/fx.py's
module and field-group docstrings for the real bugs found while porting
this file (the dFz stage's hardcoded single-load gate, which would crash
for any Fz_nom other than 50 in the original; the dIA stage's
single-camber-value and mismatched-reference-load bugs). Per
MIGRATION_PLAN.md Sec.5, optimizer-driven fits are verified by fit
quality against known-good synthetic data, not exact coefficient
recovery.
"""

import numpy as np
import pytest

from pacejka.model import FxCoefficients, fx_pure
from pacejka.fitters.fx import LBF_TO_N, FxSweepPoint, fit_fx_coefficients

# Chosen to respect every bound in the Base/dFz/dIA stages (see
# pacejka/fitters/fx.py's _BASE_BOUNDS/_DFZ_BOUNDS/_DIA_BOUNDS), with
# Ex3 fixed at exactly 0.0 (its bound is a zero-width pin), and the dFz
# fields (Dx2/Ex2/Kx2/Kx3/Hsx2/Vsx2) kept close in sign/magnitude to
# their own p0 (after p0's own out-of-bounds entries are clipped into
# range) rather than picked independently -- same rationale as
# test_fy_term_finder.py's TRUE_COEFFS comment: Kx2 and Kx3 both shape
# how K_x scales with dfz (one additive, one exponential) and are
# genuinely correlated from a generic/far-from-truth initial guess, so a
# "true" Kx3 of the opposite sign from p0 (which this file's p0.Kx3=-0.1
# would clip to 0 anyway, since its bound is (0, 0.5)) sent the optimizer
# to a different, badly-fitting local minimum in this equation's
# generic-initial-guess regime -- not a port defect, the same
# equation/generic-p0 sensitivity CLAUDE.md quirk #18 and the Mz term
# finder's test module docstring describe.
TRUE_COEFFS = FxCoefficients(
    Cx1=1.6, Dx1=2.8, Dx2=-3.0, Dx3=10.0,
    Ex1=-0.1, Ex2=0.05, Ex3=0.0, Ex4=0.02,
    Hsx1=0.001, Hsx2=0.0002,
    Kx1=80.0, Kx2=-8.0, Kx3=0.02,
    Vsx1=2.0, Vsx2=-0.05,
)

FZ0_PRIME = 150 * LBF_TO_N
KAPPA = np.linspace(-0.15, 0.13, 200)
NOISE_SCALE = 5.0  # N


def _make_point(rng, fz_lbf, ia_deg):
    fz_n = fz_lbf * LBF_TO_N
    gamma_rad = np.radians(ia_deg)
    fxo = fx_pure(fz_n, FZ0_PRIME, gamma_rad, KAPPA, TRUE_COEFFS)
    noisy = fxo + rng.normal(scale=NOISE_SCALE, size=fxo.shape)
    return FxSweepPoint(fz_n=fz_n, gamma_rad=gamma_rad, kappa=KAPPA, fx_n=noisy)


@pytest.fixture
def synthetic_dataset():
    rng = np.random.RandomState(0)
    base = _make_point(rng, 150, 0)
    load_sweep = [_make_point(rng, fz, 0) for fz in (50, 100, 150, 200, 250)]
    camber_sweep = [_make_point(rng, 150, ia) for ia in (0, 2, 4)]
    return base, load_sweep, camber_sweep


def _rmse(a, b):
    return float(np.sqrt(np.mean((a - b) ** 2)))


def test_fitted_curve_matches_noise_level_at_every_condition(synthetic_dataset):
    base, load_sweep, camber_sweep = synthetic_dataset
    result = fit_fx_coefficients(base, load_sweep, camber_sweep)

    assert _rmse(result.base_fit_fx_n, base.fx_n) < 3 * NOISE_SCALE

    for point, fit in zip(load_sweep, result.load_sweep_fit_fx_n):
        assert _rmse(fit, point.fx_n) < 5 * NOISE_SCALE

    for point, fit in zip(camber_sweep, result.camber_sweep_fit_fx_n):
        assert _rmse(fit, point.fx_n) < 3 * NOISE_SCALE


def test_ex3_is_fixed_to_zero_not_the_stale_p0_guess(synthetic_dataset):
    # Ex3's bounds are (0.0, 0.0) -- a deliberate zero-width fix,
    # distinct from p0.Ex3=-0.4 (see pacejka/fitters/fx.py's
    # _DFZ_BOUNDS comment). Confirms split_fixed_fields handles it here
    # too.
    base, load_sweep, camber_sweep = synthetic_dataset
    result = fit_fx_coefficients(base, load_sweep, camber_sweep)
    assert result.coefficients.Ex3 == 0.0


def test_single_load_sweep_cannot_identify_load_sensitivity(synthetic_dataset):
    # Regression test for the dFz stage's hardcoded Fz_vals=[50] gate
    # (see pacejka/fitters/fx.py's _DFZ_FIELDS comment): a single-
    # condition load sweep has dfz identically 0 for its one point, so
    # Dx2 has zero effect on the fit's objective and never moves off its
    # p0 initial guess (-1.75) -- regardless of the true value. The full
    # multi-load sweep does identify it.
    base, _, camber_sweep = synthetic_dataset

    degenerate = fit_fx_coefficients(base, [base], camber_sweep)
    assert degenerate.coefficients.Dx2 == pytest.approx(-1.75)

    rng = np.random.RandomState(0)
    real_sweep = [_make_point(rng, fz, 0) for fz in (50, 100, 150, 200, 250)]
    fixed = fit_fx_coefficients(base, real_sweep, camber_sweep)
    assert fixed.coefficients.Dx2 == pytest.approx(TRUE_COEFFS.Dx2, abs=0.5)


def test_camber_sweep_identifies_dx3(synthetic_dataset):
    # Dx3 (the sole dIA-stage coefficient) multiplies gamma**2, so even
    # the original's single hardcoded gamma_vals=[2] gives it some
    # signal (milder than FY's exactly-zero-effect dIA bug) -- confirm
    # the real multi-camber sweep this port uses instead recovers it.
    base, load_sweep, camber_sweep = synthetic_dataset
    result = fit_fx_coefficients(base, load_sweep, camber_sweep)
    assert result.coefficients.Dx3 == pytest.approx(TRUE_COEFFS.Dx3, abs=3.0)
