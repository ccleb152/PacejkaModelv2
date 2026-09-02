"""Tests for pacejka.splines.fit_smoothing_spline.

Not a golden test against MATLAB (no MATLAB access in this environment,
and fitted splines wouldn't need it anyway -- these properties follow from
the Reinsch smoothing-spline formulation itself, which csaps implements
directly, per CLAUDE.md's fitting-stack note). Verified instead via
properties of that formulation: p=1 means pure interpolation (residual=0),
residual against the input data decreases monotonically as `smooth`
increases toward 1, and duplicate x values are collapsed by averaging
(MATLAB's own documented behavior for `fit` given non-distinct x).
"""

import numpy as np
import pytest

from pacejka.splines import fit_smoothing_spline


def test_duplicate_x_values_are_collapsed_by_averaging():
    # x=1 appears with y=2 and y=4 (avg 3); x=3 appears with y=10, 6, 8 (avg 8).
    x = np.array([3, 1, 1, 2, 3, 3])
    y = np.array([10, 2, 4, 5, 6, 8])

    spline = fit_smoothing_spline(x, y, smooth=1.0)  # smooth=1 -> exact interpolation

    result = spline(np.array([1.0, 2.0, 3.0]))
    assert result == pytest.approx([3.0, 5.0, 8.0])


def test_smooth_equal_one_interpolates_exactly():
    rng = np.random.RandomState(0)
    x = np.linspace(-10, 10, 40)
    y = np.sin(x) + rng.normal(scale=0.05, size=x.size)

    spline = fit_smoothing_spline(x, y, smooth=1.0)

    assert spline(x) == pytest.approx(y, abs=1e-9)


def test_residual_decreases_monotonically_as_smooth_increases():
    rng = np.random.RandomState(1)
    x = np.linspace(-10, 10, 60)
    y = np.sin(x) + rng.normal(scale=0.05, size=x.size)

    def residual(smooth):
        spline = fit_smoothing_spline(x, y, smooth)
        return np.sum((spline(x) - y) ** 2)

    smooth_values = [0.01, 0.3, 0.6, 0.9, 0.999, 1.0]
    residuals = [residual(s) for s in smooth_values]

    assert all(a >= b for a, b in zip(residuals, residuals[1:]))
    assert residuals[-1] == pytest.approx(0.0, abs=1e-9)


def test_unsorted_input_matches_presorted_input():
    rng = np.random.RandomState(2)
    x = rng.uniform(-10, 10, size=30)
    y = np.sin(x) + rng.normal(scale=0.05, size=x.size)

    order = np.argsort(x)
    spline_from_sorted = fit_smoothing_spline(x[order], y[order], smooth=0.8)
    spline_from_unsorted = fit_smoothing_spline(x, y, smooth=0.8)

    probe = np.linspace(-9, 9, 25)
    assert spline_from_unsorted(probe) == pytest.approx(spline_from_sorted(probe))
