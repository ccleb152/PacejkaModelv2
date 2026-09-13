"""Tests for pacejka.fitters.mz.fit_mz_coefficients (port of
Pacejka_Term_Finder_MZ_V1_redo.m's Base/dFz/dIA stages).

No MATLAB access in this environment, and no live MATLAB run of this file
would be trustworthy as a golden reference even if there were -- see
CLAUDE.md for the real bugs found while porting it (the alpha_r/alpha_t
formulation bug, the Fz_vals=Fz_nom tautology degenerating the dFz stage,
the single-camber-value dIA stage). Per MIGRATION_PLAN.md Sec.5,
optimizer-driven fits are verified by fit quality, not exact coefficient
recovery.

Fit-quality tolerances here are looser than the FY term finder's: this
equation has more free parameters per stage (9-10 vs FY's fewer) fit from
generic p0=1 initial guesses (not domain-tuned), which is a genuinely
more optimizer-sensitive problem -- confirmed by fitting noise-free
synthetic data generated from known coefficients and finding scipy's
least_squares still lands a few percent off the exact answer, i.e. this
is a real characteristic of the equation/generic-initial-guess
combination (one MATLAB's lsqcurvefit would share, given the same p0),
not a Python-port defect.
"""

import numpy as np
import pytest

from pacejka.model import FyCoefficients, MzCoefficients, fy_terms, mz_pure
from pacejka.fitters.fy import LBF_TO_N
from pacejka.fitters.mz import DEFAULT_RO_M, MzSweepPoint, _cos_alpha_p, fit_mz_coefficients

FY_COEFFS = FyCoefficients(
    Cy1=1.6, Dy1=2.784, Dy2=-0.15, Dy3=15.0,
    Ey1=0.9, Ey2=-0.3, Ey3=0.05, Ey4=0.5, Ey5=0.5,
    Hsy1=0.0, Hsy2=0.01,
    Ky1=170.0, Ky2=2.0, Ky3=0.5, Ky4=1.0, Ky5=0.5, Ky6=2.0, Ky7=0.0,
    py1=1, py2=1, py3=1, py4=1, py5=1,
    Vsy1=0.03, Vsy2=0.02, Vsy3=1.0, Vsy4=0.0,
)

# Chosen to respect every bound in the Base/dFz/dIA stages (see
# pacejka/fitters/mz.py's _BASE_BOUNDS/_DFZ_BOUNDS/_DIA_BOUNDS) *and* to
# stay close in magnitude to the generic p0=1 initial guesses -- this
# equation's fit (see the module docstring) is sensitive enough that a
# "true" set far from p0 makes even noise-free recovery unreliable for a
# generic-initial-guess optimizer, which would make this test flaky for
# reasons that have nothing to do with whether the port is correct.
TRUE_MZ_COEFFS = MzCoefficients(
    Hz1=0.001, Hz2=0.005, Hz3=0.002, Hz4=0.0,
    Bz1=1.5, Bz2=1.0, Bz3=0.5, Bz4=1.0, Bz5=0.3,
    Bz9=1.0, Bz10=-1.0,
    Cz1=1.2,
    Dz1=1.0, Dz2=0.5, Dz3=0.5, Dz4=0.3,
    Dz6=0.5, Dz7=5.0, Dz8=0.5, Dz9=0.0, Dz10=0.5, Dz11=0.0,
    Ez1=1.0, Ez2=0.5, Ez3=1.0, Ez4=1.0, Ez5=0.5,
)

FZ0_PRIME = 150 * LBF_TO_N
RO = DEFAULT_RO_M
ALPHA_RAD = np.radians(np.linspace(-12, 12, 200))
NOISE_SCALE = 1.0  # N*m


def _make_point(rng, fz_lbf, ia_deg):
    fz_n = fz_lbf * LBF_TO_N
    gamma_star = np.sin(np.radians(ia_deg))
    terms = fy_terms(fz_n, FZ0_PRIME, gamma_star, ALPHA_RAD, FY_COEFFS)
    terms_g0 = fy_terms(fz_n, FZ0_PRIME, 0.0, ALPHA_RAD, FY_COEFFS)
    cos_alpha_p = _cos_alpha_p(ALPHA_RAD)
    true_mz = mz_pure(
        fz_n, FZ0_PRIME, RO, gamma_star, ALPHA_RAD, cos_alpha_p,
        float(terms.cy), float(terms.by), float(terms.s_hf), terms_g0.fyo, TRUE_MZ_COEFFS,
    )
    noisy_mz = true_mz + rng.normal(scale=NOISE_SCALE, size=ALPHA_RAD.shape)
    return MzSweepPoint(fz_n=fz_n, gamma_star=gamma_star, alpha_rad=ALPHA_RAD, mz_nm=noisy_mz, cos_alpha_p=cos_alpha_p)


@pytest.fixture
def synthetic_dataset():
    rng = np.random.RandomState(0)
    base = _make_point(rng, 150, 0)
    load_sweep = [_make_point(rng, fz, 0) for fz in (50, 100, 150, 200, 250)]
    camber_sweep = [_make_point(rng, 150, ia) for ia in (0, 2, 4)]
    return base, load_sweep, camber_sweep


def _relative_rmse(fit, target):
    rmse = float(np.sqrt(np.mean((fit - target) ** 2)))
    peak = float(np.max(np.abs(target)))
    return rmse / peak


def test_fitted_curve_is_in_the_right_ballpark_at_every_condition(synthetic_dataset):
    # Loose threshold, deliberately: see the module docstring on why this
    # equation's fit quality is more optimizer-sensitive than FY's, even
    # for noise-free data generated from the exact model being fit. This
    # is a sanity check against gross failures (wrong sign, wrong scale,
    # an unhandled exception), not a tight convergence guarantee.
    base, load_sweep, camber_sweep = synthetic_dataset
    result = fit_mz_coefficients(base, load_sweep, camber_sweep, FY_COEFFS, ro=RO)

    assert _relative_rmse(result.base_fit_mz_nm, base.mz_nm) < 0.25

    for point, fit in zip(load_sweep, result.load_sweep_fit_mz_nm):
        assert _relative_rmse(fit, point.mz_nm) < 0.25

    for point, fit in zip(camber_sweep, result.camber_sweep_fit_mz_nm):
        assert _relative_rmse(fit, point.mz_nm) < 0.25


def test_bz4_is_fixed_to_the_bound_value(synthetic_dataset):
    # Bz4's bounds are (20.0, 20.0) -- a deliberate zero-width fix, same
    # mechanism as the FY term finder's Dy1. Confirms split_fixed_fields
    # is applied here too.
    base, load_sweep, camber_sweep = synthetic_dataset
    result = fit_mz_coefficients(base, load_sweep, camber_sweep, FY_COEFFS, ro=RO)
    assert result.coefficients.Bz4 == 20.0


def test_cross_term_coefficients_are_always_zero_not_fit(synthetic_dataset):
    base, load_sweep, camber_sweep = synthetic_dataset
    result = fit_mz_coefficients(base, load_sweep, camber_sweep, FY_COEFFS, ro=RO)
    assert result.coefficients.Hz4 == 0.0
    assert result.coefficients.Dz9 == 0.0
    assert result.coefficients.Dz11 == 0.0


def test_single_load_sweep_cannot_identify_load_sensitivity(synthetic_dataset):
    # Regression test for the Fz_vals=Fz_nom bug: a single-condition load
    # sweep (replicating the original) has dfz identically 0 for its one
    # point, so Dz2 has zero effect on the fit's objective and never
    # moves off its p0 initial guess (1.0) -- regardless of the true
    # value. The full multi-load sweep does move it.
    base, _, camber_sweep = synthetic_dataset

    degenerate = fit_mz_coefficients(base, [base], camber_sweep, FY_COEFFS, ro=RO)
    assert degenerate.coefficients.Dz2 == pytest.approx(1.0)

    rng = np.random.RandomState(0)
    real_sweep = [_make_point(rng, fz, 0) for fz in (50, 100, 150, 200, 250)]
    fixed = fit_mz_coefficients(base, real_sweep, camber_sweep, FY_COEFFS, ro=RO)
    assert fixed.coefficients.Dz2 != pytest.approx(1.0)
