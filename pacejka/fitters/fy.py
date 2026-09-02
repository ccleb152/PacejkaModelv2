"""Port of Raw_Data_Fitter_Fy_V3.m.

(The function defined inside that file is actually named
`Raw_Data_Fitter_Fy_V2` -- a filename/function-name mismatch; MATLAB
resolves calls by filename, so this is dead cosmetic drift, not a
versioning clue. See CLAUDE.md quirk #1.)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from pacejka.splines import fit_smoothing_spline

# The original's fixed slip-angle evaluation grid: -12.25 to 12.25 degrees
# in 0.05-degree steps, 491 points. linspace (not arange) so float rounding
# can't drop or duplicate the endpoint: (12.25 - -12.25) / 0.05 == 490
# steps exactly, i.e. 491 points.
SA_GRID_DEG = np.linspace(-12.25, 12.25, 491)

# The original's per-channel MATLAB SmoothingParam values -- see
# CLAUDE.md's "Fitting stack" note on why these transfer directly to
# csaps's `smooth` and why they differ per channel in the first place.
_SMOOTHING_PARAMS = {
    "FX": 0.99999,
    "FY": 0.90,
    "MZ": 0.1,
    "Vc": 0.99999,
}


@dataclass(frozen=True)
class AlphaSweepSplines:
    """Smoothed slip-angle-sweep curves for one segmented test condition.

    `sa_grid_deg` is the fixed evaluation grid (SA_GRID_DEG); `fx`, `fy`,
    `mz`, `vc` are the corresponding smoothing-spline fits evaluated on
    that grid, in the source data's original units (lb, lb, ft-lb, mph --
    unconverted, matching Raw_Data_Fitter_Fy_V3.m's own output; unit
    conversion to SI happens in the term-finder that consumes this, same
    as the original).
    """

    sa_grid_deg: np.ndarray
    fx: np.ndarray
    fy: np.ndarray
    mz: np.ndarray
    vc: np.ndarray


def fit_alpha_sweep(condition: pd.DataFrame) -> AlphaSweepSplines:
    """Smooth one segmented condition's SA -> FX/FY/MZ/Vc curves.

    `condition` is one nominal test condition's samples -- typically the
    output of `pacejka.segmenting.segment_condition` -- with at least SA,
    FX, FY, MZ, Vc columns. SA is the independent variable (the slip-angle
    sweep); each of the other four is fit against it with its own
    MATLAB-matching SmoothingParam and evaluated on the fixed SA_GRID_DEG
    grid, exactly as Raw_Data_Fitter_Fy_V3.m does.

    ARCHITECTURE NOTE, and a real bug this sidesteps: Raw_Data_Fitter_Fy_V3.m
    decides which condition to load via its own internal `SweepVars.Fz =
    [50]` (also IA=[0], SA=[0], P=[12], V=[25]) -- all hardcoded, not
    parameters. Its caller, Pacejka_Term_Finder_FY_V3.m, takes an `Fz_nom`
    argument and uses it to look up a field name inside the result (e.g.
    `SplineData.P12.SA0.IA0.FY_..._150FZ_12P_0IA`), but Raw_Data_Fitter_Fy_V3
    itself only ever *produces* the `_50FZ_` field, regardless of what
    Fz_nom was requested -- so the original pipeline silently fits FZ=50 lbf
    no matter what a caller asks for, and would error looking up a field
    that doesn't exist for any other Fz_nom. This is a real, previously
    undocumented limitation of the MATLAB tool (see CLAUDE.md), not a
    deliberate single-condition design. It has no equivalent to preserve
    here: this function fits whatever DataFrame it's handed, so which
    condition gets fit is determined entirely by what the caller passed to
    `segment_condition` beforehand.
    """
    sa = condition["SA"].to_numpy(dtype=float)

    def _smoothed(channel: str) -> np.ndarray:
        y = condition[channel].to_numpy(dtype=float)
        spline = fit_smoothing_spline(sa, y, _SMOOTHING_PARAMS[channel])
        return spline(SA_GRID_DEG)

    return AlphaSweepSplines(
        sa_grid_deg=SA_GRID_DEG,
        fx=_smoothed("FX"),
        fy=_smoothed("FY"),
        mz=_smoothed("MZ"),
        vc=_smoothed("Vc"),
    )
