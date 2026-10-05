"""Tests for pacejka.fitters.fx.fit_kappa_sweep (port of
Raw_Data_Fitter_Fx_V2.m).

No MATLAB access in this environment -- verified against a synthetic,
fabricated slip-ratio sweep with a known underlying shape, same approach
as test_fy_fitter.py.
"""

import numpy as np
import pandas as pd
import pytest

from pacejka.fitters.fx import SL_GRID, fit_kappa_sweep, trim_to_raw_domain


@pytest.fixture
def synthetic_kappa_sweep():
    rng = np.random.RandomState(4)
    sl = np.linspace(-0.15, 0.13, 250)
    true_fx = 400 * np.tanh(sl * 15)  # smooth S-shaped longitudinal-force curve
    noisy_fx = true_fx + rng.normal(scale=5.0, size=sl.size)
    fy = rng.normal(scale=3.0, size=sl.size)
    mz = 2 * np.sin(sl * 20) + rng.normal(scale=0.2, size=sl.size)
    vc = np.full(sl.size, 25.0) + rng.normal(scale=0.05, size=sl.size)

    condition = pd.DataFrame({"SL": sl, "FX": noisy_fx, "FY": fy, "MZ": mz, "Vc": vc})
    return condition, true_fx


def test_evaluation_grid_matches_matlabs_fixed_grid(synthetic_kappa_sweep):
    condition, _ = synthetic_kappa_sweep
    result = fit_kappa_sweep(condition)

    assert result.sl_grid.shape == (303,)
    assert result.sl_grid[0] == pytest.approx(-0.161)
    assert result.sl_grid[-1] == pytest.approx(0.141)
    assert np.array_equal(result.sl_grid, SL_GRID)


def test_smoothed_fx_recovers_the_underlying_shape(synthetic_kappa_sweep):
    condition, _ = synthetic_kappa_sweep
    result = fit_kappa_sweep(condition)

    # Compare against the true function at grid points well inside the
    # data's domain (avoid the extrapolated tails near +/-0.161/0.141).
    inside_domain = (result.sl_grid > -0.14) & (result.sl_grid < 0.12)
    true_at_grid = 400 * np.tanh(result.sl_grid[inside_domain] * 15)

    assert result.fx[inside_domain] == pytest.approx(true_at_grid, abs=10.0)


def test_channels_are_smoothed_independently_with_their_own_param(synthetic_kappa_sweep):
    # FX and MZ are smoothed with very different SmoothingParam values
    # (0.99999999 vs 0.99999), so even though they're unrelated series
    # here, confirm both come back as real, finite, distinct curves.
    condition, _ = synthetic_kappa_sweep
    result = fit_kappa_sweep(condition)

    assert np.all(np.isfinite(result.fx))
    assert np.all(np.isfinite(result.mz))
    assert not np.allclose(result.fx, result.mz)


def test_trim_to_raw_domain_drops_points_outside_the_given_range(synthetic_kappa_sweep):
    # Regression test: a condition whose real raw SL doesn't reach the
    # fixed grid's edges should have its extrapolated tail(s) dropped --
    # confirmed necessary on real R20 18x6-10 data (Fz=50 lbf's raw SL
    # only reached 0.115, and csaps extrapolated to +2487 N at the
    # grid's 0.141 edge for a 50 lbf load). See MODEL_CHANGES.md.
    condition, _ = synthetic_kappa_sweep
    splines = fit_kappa_sweep(condition)

    trimmed = trim_to_raw_domain(splines, sl_min=-0.1, sl_max=0.1)

    assert trimmed.sl_grid.min() >= -0.1
    assert trimmed.sl_grid.max() <= 0.1
    assert len(trimmed.sl_grid) < len(splines.sl_grid)
    # Every array stays aligned to the same (shorter) grid.
    assert len(trimmed.fx) == len(trimmed.sl_grid)
    assert len(trimmed.fy) == len(trimmed.sl_grid)
    assert len(trimmed.mz) == len(trimmed.sl_grid)
    assert len(trimmed.vc) == len(trimmed.sl_grid)
    # Untouched outside the trim -- same values, just fewer of them.
    inside = (splines.sl_grid >= -0.1) & (splines.sl_grid <= 0.1)
    assert np.array_equal(trimmed.fx, splines.fx[inside])


def test_trim_to_raw_domain_is_a_no_op_when_domain_covers_the_whole_grid(synthetic_kappa_sweep):
    condition, _ = synthetic_kappa_sweep
    splines = fit_kappa_sweep(condition)
    trimmed = trim_to_raw_domain(splines, sl_min=SL_GRID[0], sl_max=SL_GRID[-1])
    assert np.array_equal(trimmed.sl_grid, splines.sl_grid)
    assert np.array_equal(trimmed.fx, splines.fx)
