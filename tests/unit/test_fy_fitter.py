"""Tests for pacejka.fitters.fy.fit_alpha_sweep (port of
Raw_Data_Fitter_Fy_V3.m / internally Raw_Data_Fitter_Fy_V2 -- see
CLAUDE.md quirk #1).

No MATLAB access in this environment, and the real Round-9 file the user
provided turned out not to help here: every FZ/IA/P condition in it covers
only a few tenths of a degree of SA (a load/camber step-calibration
segment, not the +/-12 deg slip-angle sweep this function is meant to
smooth) -- see the session notes. So this is verified against a synthetic,
fabricated slip-angle sweep with a known underlying shape instead: the
smoothed output should recover that shape within the injected noise, and
different channels (which use different MATLAB SmoothingParam values)
should visibly diverge given identical noisy input.
"""

import numpy as np
import pandas as pd
import pytest

from pacejka.fitters.fy import SA_GRID_DEG, fit_alpha_sweep


@pytest.fixture
def synthetic_alpha_sweep():
    rng = np.random.RandomState(3)
    sa = np.linspace(-12, 12, 250)
    true_fy = -150 * np.tanh(sa / 6)  # smooth S-shaped lateral-force curve
    noisy_fy = true_fy + rng.normal(scale=3.0, size=sa.size)
    mz = 5 * np.sin(sa * np.pi / 12) + rng.normal(scale=0.2, size=sa.size)
    vc = np.full(sa.size, 25.0) + rng.normal(scale=0.05, size=sa.size)

    condition = pd.DataFrame(
        {"SA": sa, "FX": noisy_fy, "FY": noisy_fy, "MZ": mz, "Vc": vc}
    )
    return condition, true_fy


def test_evaluation_grid_matches_matlabs_fixed_grid(synthetic_alpha_sweep):
    condition, _ = synthetic_alpha_sweep
    result = fit_alpha_sweep(condition)

    assert result.sa_grid_deg.shape == (491,)
    assert result.sa_grid_deg[0] == pytest.approx(-12.25)
    assert result.sa_grid_deg[-1] == pytest.approx(12.25)
    assert np.array_equal(result.sa_grid_deg, SA_GRID_DEG)


def test_smoothed_fy_recovers_the_underlying_shape(synthetic_alpha_sweep):
    condition, _ = synthetic_alpha_sweep
    result = fit_alpha_sweep(condition)

    # Compare against the true function at grid points well inside the
    # data's domain (avoid the extrapolated tails near +/-12.25).
    inside_domain = (result.sa_grid_deg > -11) & (result.sa_grid_deg < 11)
    true_at_grid = -150 * np.tanh(result.sa_grid_deg[inside_domain] / 6)

    assert result.fy[inside_domain] == pytest.approx(true_at_grid, abs=5.0)


def test_channels_are_smoothed_independently_with_their_own_param(synthetic_alpha_sweep):
    # FX and FY are fed the *identical* noisy series in the fixture, but
    # use different SmoothingParam values (0.99999 vs 0.90) -- so their
    # smoothed outputs must diverge, and FX (closer to interpolation)
    # should track the raw noisy data more tightly than FY does.
    condition, _ = synthetic_alpha_sweep
    result = fit_alpha_sweep(condition)

    assert not np.allclose(result.fx, result.fy)

    raw_sa = condition["SA"].to_numpy()
    raw_fy = condition["FY"].to_numpy()
    fx_on_raw_grid = np.interp(raw_sa, result.sa_grid_deg, result.fx)
    fy_on_raw_grid = np.interp(raw_sa, result.sa_grid_deg, result.fy)

    fx_residual = np.sum((fx_on_raw_grid - raw_fy) ** 2)
    fy_residual = np.sum((fy_on_raw_grid - raw_fy) ** 2)
    assert fx_residual < fy_residual
