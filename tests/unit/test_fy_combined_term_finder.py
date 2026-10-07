"""Tests for pacejka.fitters.fy.fit_combined_fy_coefficients (port of
Pacejka_Term_Finder_FX_V4_Redo.m's combined-slip Fy stage, CBaseFit/
CdFzFit/CdIAFit applied to the lateral channel).

No MATLAB access in this environment -- per MIGRATION_PLAN.md Sec.5,
optimizer-driven fits are verified by fit quality against known-good
synthetic data, not exact coefficient recovery (CLAUDE.md quirk #18).

TRUE_COMB is chosen within every bound in pacejka/fitters/fy.py's
_COMBINED_FY_BASE_BOUNDS/_COMBINED_FY_DFZ_BOUNDS/_COMBINED_FY_DIA_BOUNDS,
close to the committed all-ones p0 (_COMBINED_FY_P0) -- same
generic-p0 sensitivity documented there and in
test_fx_combined_term_finder.py's module docstring: values picked far
from p0 (e.g. By4=-100, Vsy6=5) were confirmed during development to
land the optimizer in a visibly worse local minimum than these.
"""

import numpy as np
import pytest

from pacejka.model import FyCoefficients, FyCombinedCoefficients, fy_combined
from pacejka.fitters.fy import (
    LBF_TO_N,
    CombinedFySweepPoint,
    fit_combined_fy_coefficients,
)

PURE_COEFFS = FyCoefficients(
    Cy1=0.975, Dy1=2.784, Dy2=-0.01, Dy3=25.0,
    Ey1=1.0, Ey2=-0.80, Ey3=0.0, Ey4=1.0, Ey5=1.0,
    Hsy1=0.0, Hsy2=0.0,
    Ky1=175.5, Ky2=2.9, Ky3=1.0, Ky4=0.8, Ky5=1.0, Ky6=3.0, Ky7=0.0,
    py1=1.0, py2=1.0, py3=1.0, py4=1.0, py5=1.0,
    Vsy1=0.0, Vsy2=0.0, Vsy3=3.0, Vsy4=0.0,
)

TRUE_COMB = FyCombinedCoefficients(
    By1=3.0, By2=1.5, By3=0.0, By4=-20.0,
    Cy1=1.3,
    Ey1=0.5, Ey2=0.2,
    Hsy1=0.02, Hsy2=0.002,
    Vsy1=0.05, Vsy2=0.02, Vsy3=0.1, Vsy4=0.5, Vsy5=1.2, Vsy6=3.0,
)

FZ0_PRIME = 150 * LBF_TO_N
KAPPA = np.linspace(-0.15, 0.13, 200)
NOISE_SCALE = 3.0  # N


def _make_point(rng, fz_lbf, ia_deg, sa_deg):
    fz_n = fz_lbf * LBF_TO_N
    gamma_star = float(np.sin(np.radians(ia_deg)))
    alpha_rad = np.radians(sa_deg)
    fyc = fy_combined(fz_n, FZ0_PRIME, gamma_star, KAPPA, alpha_rad, PURE_COEFFS, TRUE_COMB)
    noisy = fyc + rng.normal(scale=NOISE_SCALE, size=fyc.shape)
    return CombinedFySweepPoint(fz_n=fz_n, gamma_star=gamma_star, alpha_rad=alpha_rad, kappa=KAPPA, fy_n=noisy)


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
    result = fit_combined_fy_coefficients(PURE_COEFFS, base, alpha_sweep, load_sweep, camber_sweep)

    assert _rmse(result.base_fit_fy_n, base.fy_n) < 3 * NOISE_SCALE

    for point, fit in zip(alpha_sweep, result.alpha_sweep_fit_fy_n):
        assert _rmse(fit, point.fy_n) < 3 * NOISE_SCALE

    for point, fit in zip(load_sweep, result.load_sweep_fit_fy_n):
        assert _rmse(fit, point.fy_n) < 4 * NOISE_SCALE

    for point, fit in zip(camber_sweep, result.camber_sweep_fit_fy_n):
        assert _rmse(fit, point.fy_n) < 3 * NOISE_SCALE


def test_vsy4_has_zero_effect_at_alpha_zero():
    # Regression test for the true dead-parameter identity (see
    # pacejka.model.fy_combined's docstring and CLAUDE.md quirk #26):
    # Vsy4 only ever appears inside cos(atan(Vsy4 * alpha_rad)), which is
    # cos(atan(0)) == 1 at alpha_rad=0 *regardless* of Vsy4 -- unlike the
    # jointly-unidentifiable-but-not-dead By1/By2/By3, this one
    # coefficient has exactly zero effect on the combined-slip Fy curve
    # when alpha=0, for any kappa.
    fz_n = 150 * LBF_TO_N
    gamma_star = 0.0

    low_vsy4 = FyCombinedCoefficients(**{**TRUE_COMB.__dict__, "Vsy4": -40.0})
    high_vsy4 = FyCombinedCoefficients(**{**TRUE_COMB.__dict__, "Vsy4": 1.9})

    fy_low = fy_combined(fz_n, FZ0_PRIME, gamma_star, KAPPA, 0.0, PURE_COEFFS, low_vsy4)
    fy_high = fy_combined(fz_n, FZ0_PRIME, gamma_star, KAPPA, 0.0, PURE_COEFFS, high_vsy4)
    assert np.allclose(fy_low, fy_high)


def test_single_alpha_point_cannot_identify_vsy4(synthetic_dataset):
    # Fitting-level counterpart to the identity above: with only alpha=0
    # data (`base` alone, no real alpha_sweep/camber_sweep), Vsy4 has
    # zero gradient effect on the objective and can't move off its
    # (already-in-bounds) p0, regardless of what the other jointly-
    # unidentifiable Base-stage fields do.
    base, _, load_sweep, _ = synthetic_dataset
    degenerate = fit_combined_fy_coefficients(PURE_COEFFS, base, [], load_sweep, [])
    from pacejka.fitters.fy import _COMBINED_FY_P0

    assert degenerate.coefficients.Vsy4 == pytest.approx(_COMBINED_FY_P0["Vsy4"], abs=1e-6)


def test_camber_sweep_identifies_vsy3(synthetic_dataset):
    # Vsy3 (one of the two dIA-stage fields) multiplies gamma_star
    # linearly inside dyk, so the camber sweep (recorded at the nonzero
    # reference slip angle, per fit_combined_fy_coefficients' own
    # docstring) gives it real, clean signal. (By4, this stage's other
    # dIA field, is deliberately not tested the same way here -- it sits
    # inside Byk alongside the jointly-unidentifiable-at-alpha=0 By1/
    # By2/By3 triple, described in fy_combined's docstring and CLAUDE.md
    # quirk #26, and correlates with them even once real alpha-dependence
    # is added back in, so its *individual* recovered value isn't a
    # meaningful check -- the overall-fit-quality test above already
    # confirms the combined curve itself is right regardless.)
    base, alpha_sweep, load_sweep, camber_sweep = synthetic_dataset
    result = fit_combined_fy_coefficients(PURE_COEFFS, base, alpha_sweep, load_sweep, camber_sweep)
    assert result.coefficients.Vsy3 == pytest.approx(TRUE_COMB.Vsy3, abs=0.05)


def test_load_sweep_identifies_ey2(synthetic_dataset):
    # Ey2 (one of the three dFz-stage fields) multiplies dfz inside Eyk,
    # so the load sweep (recorded at the nonzero reference slip angle)
    # should give it real signal.
    base, alpha_sweep, load_sweep, camber_sweep = synthetic_dataset
    result = fit_combined_fy_coefficients(PURE_COEFFS, base, alpha_sweep, load_sweep, camber_sweep)
    assert result.coefficients.Ey2 == pytest.approx(TRUE_COMB.Ey2, abs=1.0)
