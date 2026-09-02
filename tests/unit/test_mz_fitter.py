"""Tests for pacejka.fitters.mz.fit_aligning_moment (port of
Raw_Data_Fitter_Mz_V2.m).

No MATLAB access in this environment, so verified against a synthetic,
fabricated slip-angle sweep with a known aligning-moment-like shape (rises
then decays back toward zero, roughly odd-symmetric -- a stand-in for a
real pneumatic-trail curve) rather than captured MATLAB output, following
the same approach used for pacejka.fitters.fy.
"""

import numpy as np
import pandas as pd
import pytest

from pacejka.fitters.mz import SA_GRID_DEG, fit_aligning_moment


@pytest.fixture
def synthetic_mz_sweep():
    rng = np.random.RandomState(4)
    sa = np.linspace(-12, 12, 300)
    true_mz = 10 * sa * np.exp(-((sa / 4) ** 2))
    noisy_mz = true_mz + rng.normal(scale=0.5, size=sa.size)
    condition = pd.DataFrame({"SA": sa, "MZ": noisy_mz})
    return condition


def test_evaluation_grid_matches_matlabs_nonuniform_grid(synthetic_mz_sweep):
    result = fit_aligning_moment(synthetic_mz_sweep)

    assert result.sa_grid_deg.shape == (681,)
    assert np.array_equal(result.sa_grid_deg, SA_GRID_DEG)
    # Boundaries of the three concatenated ranges.
    assert result.sa_grid_deg[0] == pytest.approx(-12.3)
    assert result.sa_grid_deg[152] == pytest.approx(-4.7)
    assert result.sa_grid_deg[153] == pytest.approx(-4.675)
    assert result.sa_grid_deg[152 + 375 - 1] == pytest.approx(4.65, abs=0.01)
    assert result.sa_grid_deg[152 + 375] == pytest.approx(4.675)
    assert result.sa_grid_deg[-1] == pytest.approx(12.3)


def test_grid_is_denser_near_zero_than_at_the_extremes(synthetic_mz_sweep):
    result = fit_aligning_moment(synthetic_mz_sweep)
    steps = np.diff(result.sa_grid_deg)
    near_zero_step = steps[len(steps) // 2]
    outer_step = steps[5]
    assert near_zero_step == pytest.approx(0.025, abs=1e-6)
    assert outer_step == pytest.approx(0.05, abs=1e-6)


def test_smoothed_mz_recovers_the_underlying_shape(synthetic_mz_sweep):
    result = fit_aligning_moment(synthetic_mz_sweep)

    inside_domain = (result.sa_grid_deg > -11) & (result.sa_grid_deg < 11)
    grid = result.sa_grid_deg[inside_domain]
    true_at_grid = 10 * grid * np.exp(-((grid / 4) ** 2))

    assert result.mz[inside_domain] == pytest.approx(true_at_grid, abs=1.0)


def test_only_mz_is_fit_no_other_channels_required(synthetic_mz_sweep):
    # Raw_Data_Fitter_Mz_V2.m's RawDataVars is just ['MZ', 'SA'] -- unlike
    # the Fy fitter, this should work with a DataFrame that has nothing
    # but SA and MZ.
    minimal = synthetic_mz_sweep[["SA", "MZ"]]
    result = fit_aligning_moment(minimal)
    assert result.mz.shape == (681,)
