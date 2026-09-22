"""Auto-detecting which nominal test conditions a raw TTC round covers.

Part of `tiremodelV2.m`'s replacement (see MIGRATION_PLAN.md step 9): the
original hardcodes which loads/cambers to fit (`Fz_nom = [50]`, and every
`Raw_Data_Fitter_*`/`Pacejka_Term_Finder_*` file hardcodes its own sweep
independently -- the whole reason quirks #7/#11/#14/#15 exist). Per
CLAUDE.md's roadmap, the Python pipeline detects the tested conditions
from the data itself rather than requiring another hand-typed list.

Deliberately reuses `pacejka.ranges.para_range`/`pacejka.segmenting.
segment_condition` rather than inventing a separate clustering heuristic:
a nominal load is "tested" exactly when real samples fall inside the
acceptance band `ParaRange.m` already defines for it, which is the same
definition the rest of the pipeline uses to select that condition's data.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from pacejka.segmenting import segment_condition

# The nominal loads (lbf) ParaRange.m's Cornering branch has acceptance
# bands for -- see pacejka/ranges.py's _FZ_BANDS. Candidates outside this
# set can't be detected this way since there's no band to test against;
# a genuinely different tested load would need a new ParaRange band added
# first (see CLAUDE.md quirk #4).
CANDIDATE_FZ_NOMS = (50.0, 100.0, 150.0, 200.0, 250.0, 350.0)

DEFAULT_MIN_SAMPLES = 10


def detect_fz_levels(
    samples: pd.DataFrame,
    p_nom: float,
    v_nom: float,
    test_type: str = "Cornering",
    ia_nom: float = 0.0,
    candidates=CANDIDATE_FZ_NOMS,
    min_samples: int = DEFAULT_MIN_SAMPLES,
) -> list[float]:
    """Which of the standard nominal loads actually have data in this
    round, at the given pressure/camber/speed condition (by default, the
    zero-camber load sweep every other detection/fit step is built on).

    Returns the detected loads in ascending order.
    """
    detected = []
    for fz_nom in candidates:
        try:
            segment = segment_condition(
                samples, fz_nom=fz_nom, p_nom=p_nom, ia_nom=ia_nom, sa_nom=0.0, v_nom=v_nom, test_type=test_type
            )
        except ValueError:
            # fz_nom or p_nom isn't one ParaRange has a band for at all --
            # not "no data for this candidate", just "not checkable this way".
            continue
        if len(segment) >= min_samples:
            detected.append(fz_nom)
    return sorted(detected)


def detect_camber_levels(
    samples: pd.DataFrame,
    fz_nom: float,
    p_nom: float,
    v_nom: float,
    test_type: str = "Cornering",
    round_to_deg: float = 1.0,
    min_samples: int = DEFAULT_MIN_SAMPLES,
) -> list[float]:
    """Which nominal camber angles (deg) were tested at one nominal load.

    Unlike FZ, ParaRange has no fixed table of "standard" camber levels to
    check against (its Cornering IA band is `IA_Nom +/- 0.075` for any
    IA_Nom) -- so this clusters the raw IA channel directly instead:
    segments with `ia_nom=NaN` (which `para_range` treats as "accept any
    camber", the same mechanism `Data_Finder_v3.m`'s NaN handling was
    meant to provide -- see CLAUDE.md quirk #5/#6), rounds the resulting
    IA samples to the nearest `round_to_deg`, and keeps whichever rounded
    values have enough samples to be a real tested level rather than a
    transient between sweep segments.

    Returns the detected camber angles in ascending order.
    """
    segment = segment_condition(
        samples, fz_nom=fz_nom, p_nom=p_nom, ia_nom=math.nan, sa_nom=0.0, v_nom=v_nom, test_type=test_type
    )
    if segment.empty:
        return []

    rounded = np.round(segment["IA"].to_numpy(dtype=float) / round_to_deg) * round_to_deg
    values, counts = np.unique(rounded, return_counts=True)
    return sorted(float(v) for v, c in zip(values, counts) if c >= min_samples)
