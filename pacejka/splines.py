"""Shared smoothing-spline helper, built on `csaps`.

See CLAUDE.md's "Fitting stack" note for why `csaps` and not scipy's
`UnivariateSpline`/`splrep`: `csaps` implements the same Reinsch
`p`-in-`[0,1]` formulation as MATLAB's
`fit(x, y, 'smoothingspline', 'SmoothingParam', p)`, so the SmoothingParam
values already hand-tuned in the original `Raw_Data_Fitter_*` files
transfer directly to `smooth` here instead of needing re-derivation.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
from csaps import csaps


def fit_smoothing_spline(x, y, smooth: float) -> Callable[[np.ndarray], np.ndarray]:
    """Fit a cubic smoothing spline and return it as a callable.

    Mirrors MATLAB's `fit(x, y, 'smoothingspline', 'SmoothingParam', smooth)`:
    `x` need not be sorted, and repeated x values are collapsed by
    averaging their corresponding y values before fitting. That's MATLAB's
    own documented behavior for `fit` given non-distinct x -- not a
    Python-side workaround -- and it's a real requirement here, not an
    edge case: raw TTC channels routinely report the same rounded value
    for several consecutive samples, and `csaps` itself requires strictly
    increasing x and raises otherwise.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    order = np.argsort(x, kind="stable")
    x_sorted, y_sorted = x[order], y[order]

    x_unique, inverse = np.unique(x_sorted, return_inverse=True)
    sums = np.zeros(x_unique.shape)
    counts = np.zeros(x_unique.shape)
    np.add.at(sums, inverse, y_sorted)
    np.add.at(counts, inverse, 1)
    y_averaged = sums / counts

    return csaps(x_unique, y_averaged, smooth=smooth)
