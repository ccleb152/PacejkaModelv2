"""Port of Raw_Data_Fitter_Mz_V2.m."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from pacejka.splines import fit_smoothing_spline

# The original's fixed, non-uniform slip-angle evaluation grid: coarser
# 0.05-degree spacing away from zero SA, finer 0.025-degree spacing near it
# (where the aligning-moment curve's peak/pneumatic-trail behavior is most
# sensitive to slip angle) -- concatenation of
# [-12.3,-4.7]@0.05, [-4.675,4.675]@0.025, [4.7,12.3]@0.05, 681 points total.
# linspace per segment (not arange) so float rounding can't drop or
# duplicate an endpoint.
_OUTER_NEG_SA = np.linspace(-12.3, -4.7, 153)
_INNER_SA = np.linspace(-4.675, 4.675, 375)
_OUTER_POS_SA = np.linspace(4.7, 12.3, 153)
SA_GRID_DEG = np.concatenate([_OUTER_NEG_SA, _INNER_SA, _OUTER_POS_SA])

# The original's MATLAB SmoothingParam for SA->MZ.
_MZ_SMOOTHING_PARAM = 0.75


@dataclass(frozen=True)
class AligningMomentSpline:
    """Smoothed slip-angle -> aligning-moment curve for one condition.

    `sa_grid_deg` is the fixed evaluation grid (SA_GRID_DEG); `mz` is the
    smoothing-spline fit evaluated on it, in the source data's original
    units (ft-lb, unconverted -- unit conversion to SI happens in the term
    finder that consumes this, same as the original).
    """

    sa_grid_deg: np.ndarray
    mz: np.ndarray


def fit_aligning_moment(condition: pd.DataFrame) -> AligningMomentSpline:
    """Smooth one segmented condition's SA -> MZ curve.

    `condition` is one nominal test condition's samples -- typically the
    output of `pacejka.segmenting.segment_condition` -- with at least SA
    and MZ columns.

    Unlike `Raw_Data_Fitter_Mx_V2.m` (see `pacejka.fitters.mx`, not yet
    ported), this does *not* trim the "return sweep" portion of a
    triangle-wave SA trace before fitting -- Raw_Data_Fitter_Mz_V2.m
    computes the trim indices (`Index`/`Max1`/`Min2`) but the actual
    trim lines are commented out, so they're dead code, omitted here.
    Whether that's deliberate (MZ's fit is meant to include both sweep
    directions, e.g. to capture hysteresis) or an oversight when this file
    was copied from its MX sibling is not knowable from the source alone
    -- see CLAUDE.md quirk #8. This port preserves the original's actual
    (untrimmed) behavior; flagged for the team to confirm.

    Also unlike `pacejka.fitters.fy.fit_alpha_sweep`, only MZ is fit here
    (the original's `RawDataVars` is just `['MZ', 'SA']`) -- no FX/FY/Vc,
    matching Raw_Data_Fitter_Mz_V2.m's own narrower scope.
    """
    sa = condition["SA"].to_numpy(dtype=float)
    mz = condition["MZ"].to_numpy(dtype=float)

    spline = fit_smoothing_spline(sa, mz, _MZ_SMOOTHING_PARAM)
    return AligningMomentSpline(sa_grid_deg=SA_GRID_DEG, mz=spline(SA_GRID_DEG))
