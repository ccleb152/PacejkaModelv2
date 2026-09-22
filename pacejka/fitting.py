"""Generic staged nonlinear least-squares fitting helpers.

Shared by `pacejka.fitters.fy` and `pacejka.fitters.mz` (and future term
finders): both port MATLAB Pacejka term finders that fit a handful of
named coefficients at a time, holding the rest fixed, across several
sequential stages (Base/dFz/dIA/...), threading each stage's result
forward as a fixed input to the next. This factors out the parts that
aren't specific to either equation: splitting a zero-width (fixed) MATLAB
bound from ones scipy can actually optimize, replicating MATLAB's silent
infeasible-`x0` clipping, and picking a data-driven robust-loss scale. The
model equation and its residuals stay in each fitter module, since those
genuinely differ (`fy_pure` vs. `mz_pure`).
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import least_squares


def split_fixed_fields(field_names, bounds, current_values):
    """Split (field, bound) pairs into ones scipy can actually optimize and
    ones MATLAB's `lb == ub` effectively fixes as a constant.

    `scipy.optimize.least_squares` requires a *strictly* increasing
    `[lb, ub]` per parameter and raises otherwise; MATLAB's `lsqcurvefit`
    happily accepts `lb == ub` and treats that parameter as pinned to that
    value for the whole fit (e.g. the FY term finder's `Dy1`, fixed to a
    known mu_y regardless of its stale p0 initial guess). Returns
    `(free_fields, free_bounds, fixed_updates)`.
    """
    free_fields, free_bounds = [], []
    fixed_updates = {}
    for name, (lb, ub) in zip(field_names, bounds):
        if lb == ub:
            fixed_updates[name] = lb
        else:
            free_fields.append(name)
            free_bounds.append((lb, ub))
    return free_fields, free_bounds, fixed_updates


def fit_stage(residual_fn, x0, bounds=None, robust=False):
    """Run one staged least-squares fit and return the fitted parameters.

    `residual_fn(x) -> residuals` must be fully closed over everything
    except the free parameter vector `x` (the model function, fixed
    coefficient values, and the data to fit against).

    `bounds`, if given, is a sequence of `(lb, ub)` pairs matching `x0`;
    an infeasible `x0` is clipped into bounds first, replicating MATLAB's
    own documented `lsqcurvefit` behavior (it silently moves out-of-bounds
    components to the nearest bound) rather than scipy's `least_squares`,
    which raises instead. `bounds=None` means genuinely unconstrained,
    matching MATLAB's `nlinfit` (which doesn't support bounds at all).

    `robust=True` uses `soft_l1` loss with an `f_scale` derived from the
    initial residuals' own spread (their standard deviation), rather than
    a fixed magic number -- Fy/Mz residuals could be single digits or
    thousands of N/N*m depending on the fit, so a hardcoded scale would
    only be right by accident. This approximates MATLAB's `nlinfit` +
    bisquare robust weighting (which auto-scales from the residuals' own
    MAD), though not exactly -- bisquare fully rejects far outliers,
    `soft_l1` only down-weights them.
    """
    x0 = np.asarray(x0, dtype=float)

    if bounds is None:
        lb, ub = -np.inf, np.inf
    else:
        lb = np.asarray([b[0] for b in bounds], dtype=float)
        ub = np.asarray([b[1] for b in bounds], dtype=float)
        x0 = np.clip(x0, lb, ub)

    kwargs = {}
    if robust:
        initial_residuals = residual_fn(x0)
        kwargs["loss"] = "soft_l1"
        kwargs["f_scale"] = max(float(np.std(initial_residuals)), 1e-6)

    result = least_squares(residual_fn, x0, bounds=(lb, ub), **kwargs)
    return result.x
