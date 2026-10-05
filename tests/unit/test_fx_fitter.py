"""Tests for pacejka.fitters.fx.fit_kappa_sweep (port of
Raw_Data_Fitter_Fx_V2.m).

No MATLAB access in this environment -- verified against a synthetic,
fabricated slip-ratio sweep with a known underlying shape, same approach
as test_fy_fitter.py.
"""

import numpy as np
import pandas as pd
import pytest

from pacejka.fitters.fx import SL_GRID, fit_kappa_sweep


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
