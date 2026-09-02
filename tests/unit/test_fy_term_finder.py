"""Tests for pacejka.fitters.fy.fit_fy_coefficients (port of
Pacejka_Term_Finder_FY_V3.m's Base/dFz/dIA stages).

No MATLAB access in this environment, and no live MATLAB run of this
specific file would be trustworthy as a golden reference even if there
were -- see CLAUDE.md quirks #7 and #9 for the real bugs found while
porting it (a sign/magnitude error in the Base stage's Ky1 bounds, a unit
conversion missing from the dFz stage, and the dFz/dIA stages both being
fed single-condition data that can't actually identify what they're
fitting). Per MIGRATION_PLAN.md Sec.5, optimizer-driven fits are verified
by fit quality against known-good synthetic data, not exact coefficient
recovery -- scipy's optimizer won't match MATLAB's anyway, and several
Magic Formula coefficients are genuinely correlated/weakly identifiable
from a single smooth curve regardless of which optimizer is used.
"""

import numpy as np
import pytest

from pacejka.model import FyCoefficients, fy_pure
from pacejka.fitters.fy import LBF_TO_N, FySweepPoint, fit_fy_coefficients

# Chosen to respect every bound in the Base/dIA stages (see
# pacejka/fitters/fy.py's _BASE_BOUNDS/_DIA_BOUNDS) so the fit can actually
# reach the ground truth -- a coefficient outside its own stage's bounds
# would make the fit fail by construction, which is a test-setup mistake,
# not something the implementation could ever satisfy.
TRUE_COEFFS = FyCoefficients(
    Cy1=1.6, Dy1=2.784, Dy2=-0.15, Dy3=15.0,
    Ey1=0.9, Ey2=-0.3, Ey3=0.05, Ey4=0.5, Ey5=0.5,
    Hsy1=0.0, Hsy2=0.01,
    Ky1=170.0, Ky2=2.0, Ky3=0.5, Ky4=1.0, Ky5=0.5, Ky6=2.0, Ky7=0.0,
    py1=1, py2=1, py3=1, py4=1, py5=1,
    Vsy1=0.03, Vsy2=0.02, Vsy3=1.0, Vsy4=0.0,
)

FZ0_PRIME = 150 * LBF_TO_N
ALPHA_RAD = np.radians(np.linspace(-12, 12, 200))
NOISE_SCALE = 5.0  # N


def _make_point(rng, fz_lbf, ia_deg):
    fz_n = fz_lbf * LBF_TO_N
    gamma_star = np.sin(np.radians(ia_deg))
    fyo, _ = fy_pure(fz_n, FZ0_PRIME, gamma_star, ALPHA_RAD, TRUE_COEFFS)
    noisy = fyo + rng.normal(scale=NOISE_SCALE, size=fyo.shape)
    return FySweepPoint(fz_n=fz_n, gamma_star=gamma_star, alpha_rad=ALPHA_RAD, fy_n=noisy)


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
    result = fit_fy_coefficients(base, load_sweep, camber_sweep)

    assert _rmse(result.base_fit_fy_n, base.fy_n) < 3 * NOISE_SCALE

    for point, fit in zip(load_sweep, result.load_sweep_fit_fy_n):
        # A little slack at the highest loads: peak force scales with Fz,
        # so the same absolute noise is a smaller fraction of the signal,
        # but correlated-parameter effects can still show up as a few
        # times the injected noise in absolute terms.
        assert _rmse(fit, point.fy_n) < 5 * NOISE_SCALE

    for point, fit in zip(camber_sweep, result.camber_sweep_fit_fy_n):
        assert _rmse(fit, point.fy_n) < 3 * NOISE_SCALE


def test_ky1_comes_out_positive_not_the_original_wrong_sign_bound(synthetic_dataset):
    # Regression test for CLAUDE.md quirk #9: the original bounds Ky1 to
    # [-70, -50], which would force a physically-backwards (negative
    # cornering-stiffness) fit. The corrected bounds are [0, 1000].
    base, load_sweep, camber_sweep = synthetic_dataset
    result = fit_fy_coefficients(base, load_sweep, camber_sweep)
    assert result.coefficients.Ky1 > 0


def test_dy1_is_fixed_to_the_bound_value_not_the_stale_p0_guess(synthetic_dataset):
    # Dy1's bounds are (2.784, 2.784) -- a deliberate zero-width fix,
    # distinct from p0.Dy1=2.625 (see pacejka/fitters/fy.py's _BASE_BOUNDS
    # comment). Confirms _split_fixed_fields handles it correctly.
    base, load_sweep, camber_sweep = synthetic_dataset
    result = fit_fy_coefficients(base, load_sweep, camber_sweep)
    assert result.coefficients.Dy1 == 2.784


def test_cross_term_coefficients_are_always_zero_not_fit(synthetic_dataset):
    base, load_sweep, camber_sweep = synthetic_dataset
    result = fit_fy_coefficients(base, load_sweep, camber_sweep)
    assert result.coefficients.Ky7 == 0.0
    assert result.coefficients.Vsy4 == 0.0


def test_single_load_sweep_cannot_identify_load_sensitivity(synthetic_dataset):
    # Regression test for CLAUDE.md quirk #7: a single-condition load
    # sweep (replicating the original's hardcoded Fz_vals=[50]) has dfz
    # identically 0 for its one point, so Dy2 has zero effect on the fit's
    # objective and never moves off its p0 initial guess (-0.01) --
    # regardless of the true value. The full multi-load sweep does
    # identify it.
    base, _, camber_sweep = synthetic_dataset

    degenerate = fit_fy_coefficients(base, [base], camber_sweep)
    assert degenerate.coefficients.Dy2 == pytest.approx(-0.01)

    rng = np.random.RandomState(0)
    real_sweep = [_make_point(rng, fz, 0) for fz in (50, 100, 150, 200, 250)]
    fixed = fit_fy_coefficients(base, real_sweep, camber_sweep)
    assert fixed.coefficients.Dy2 == pytest.approx(TRUE_COEFFS.Dy2, abs=0.05)
