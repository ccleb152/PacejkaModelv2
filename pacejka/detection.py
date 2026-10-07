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

from pacejka.quality import MIN_SL_SWEEP_RANGE
from pacejka.segmenting import segment_condition

# The nominal loads (lbf) ParaRange.m's Cornering branch has acceptance
# bands for -- see pacejka/ranges.py's _FZ_BANDS. Candidates outside this
# set can't be detected this way since there's no band to test against;
# a genuinely different tested load would need a new ParaRange band added
# first (see CLAUDE.md quirk #4).
CANDIDATE_FZ_NOMS = (50.0, 100.0, 150.0, 200.0, 250.0, 350.0)

# The nominal slip angles (deg) ParaRange.m's Braking branch has
# acceptance bands for -- see pacejka/ranges.py's _BRAKING_SA_BANDS.
# Unlike Cornering (one fixed +/-15 deg band regardless of SA_Nom), a
# Braking round holds slip angle at one of a small fixed set of nominal
# values while sweeping slip ratio -- this is how the original tool's
# combined-slip stages are meant to get real alpha != 0 data, though its
# own hardcoded SweepVars.SA=[0] (CLAUDE.md quirk #24) never read any
# value but the first. Confirmed present, full-width, at every tested
# load/camber in the team's real 18x6-10 BrakeDrive rounds.
CANDIDATE_SA_NOMS = (0.0, -3.0, -6.0)

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

    A candidate also needs at least 2 distinct values of the swept
    channel (SL for Braking, SA for Cornering) to count as detected, not
    just enough raw samples -- confirmed against real R20 18x6-10
    BrakeDrive data, where Fz=100/350 lbf each matched >= min_samples
    worth of a brief transient/calibration segment at 1-2 distinct SL
    values, not an actual tested load level (the real sweep there is
    exactly the four loads Raw_Data_Fitter_Fx_V2.m's own hardcoded
    SweepVars.Fz=[50 150 200 250] tested). Without this, such a
    candidate would be "detected" here only to crash downstream in
    `pacejka.quality.check_condition_quality`/the spline fitter -- same
    reasoning, applied one step earlier so a bogus load never gets this
    far into the pipeline at all.

    For Braking, a candidate additionally needs an SL range of at least
    `pacejka.quality.MIN_SL_SWEEP_RANGE` -- the same threshold
    `check_condition_quality` enforces as a hard error there. Found on
    the same real R20 data: Fz=100 lbf's segment had 2+ distinct SL
    values (so the check above alone wasn't enough to exclude it) but
    only a 0.015-wide range, nowhere near the ~0.3-wide range a real
    sweep covers -- without this check it would be "detected", then
    raise downstream once `check_condition_quality` ran on it, aborting
    the whole fit instead of just excluding one bogus load.

    Returns the detected loads in ascending order.
    """
    swept_channel = "SL" if test_type == "Braking" else "SA"
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
        swept = segment[swept_channel]
        if len(segment) < min_samples or swept.nunique() < 2:
            continue
        if test_type == "Braking" and float(swept.max() - swept.min()) < MIN_SL_SWEEP_RANGE:
            continue
        detected.append(fz_nom)
    return sorted(detected)


def detect_sa_levels(
    samples: pd.DataFrame,
    fz_nom: float,
    ia_nom: float,
    p_nom: float,
    v_nom: float,
    candidates=CANDIDATE_SA_NOMS,
    min_samples: int = DEFAULT_MIN_SAMPLES,
) -> list[float]:
    """Which of the standard nominal slip angles have real combined-slip
    (SL-swept) data in this Braking round, at the given load/camber.

    Braking-only (no `test_type` parameter): Cornering has no equivalent
    concept -- its SA band is one fixed +/-15 deg range covering the
    whole slip-angle sweep itself, not a small set of discrete nominal
    angles to detect among. This is the combined-slip counterpart to
    `detect_fz_levels`: the swept channel it checks is always SL (a
    Braking round's SL is swept within each fixed-SA condition, the
    mirror image of `detect_fz_levels`'s own SA/SL check), and the same
    two robustness requirements apply for the same reason -- a candidate
    must have at least 2 distinct SL values and an SL range of at least
    `pacejka.quality.MIN_SL_SWEEP_RANGE`, so a transient/calibration
    segment is never reported as a detected slip-angle level only to
    crash or get fit downstream. Real data check: all three of these
    candidates have substantial, full-width SL sweeps at every tested
    load and camber in the team's real 18x6-10 BrakeDrive rounds.

    Returns the detected slip angles in ascending order.
    """
    detected = []
    for sa_nom in candidates:
        try:
            segment = segment_condition(
                samples, fz_nom=fz_nom, p_nom=p_nom, ia_nom=ia_nom, sa_nom=sa_nom, v_nom=v_nom, test_type="Braking"
            )
        except ValueError:
            continue
        sl = segment["SL"]
        if len(segment) < min_samples or sl.nunique() < 2:
            continue
        if float(sl.max() - sl.min()) < MIN_SL_SWEEP_RANGE:
            continue
        detected.append(sa_nom)
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

    A rounded cluster passing `min_samples` here is necessary but not
    sufficient: the rounding bucket is `round_to_deg` wide (0.5 deg on
    either side by default), much wider than `para_range`'s real
    Cornering/Braking IA acceptance band (`ia_nom +/- 0.075` deg), so a
    transient reading while the rig settles between two real camber
    levels can collect enough points in the coarse bucket to clear
    `min_samples` while having almost none inside the tight band
    `segment_condition` will actually use downstream -- confirmed
    against real LCO 18x6-10 BrakeDrive data, where a spurious "IA=1 deg"
    cluster (33 points in the +/-0.5 deg bucket, transitional data
    between the real 0 and 2 deg sweeps) had only 5 points inside the
    real +/-0.075 deg band, too few to fit. Each candidate is re-checked
    with the same `ia_nom`/`min_samples` semantics `pacejka.pipeline`/
    `pacejka.longitudinal_pipeline` will actually use, so a level that
    wouldn't survive that downstream check is never reported as detected
    in the first place.
    """
    segment = segment_condition(
        samples, fz_nom=fz_nom, p_nom=p_nom, ia_nom=math.nan, sa_nom=0.0, v_nom=v_nom, test_type=test_type
    )
    if segment.empty:
        return []

    rounded = np.round(segment["IA"].to_numpy(dtype=float) / round_to_deg) * round_to_deg
    values, counts = np.unique(rounded, return_counts=True)
    candidates = [float(v) for v, c in zip(values, counts) if c >= min_samples]

    detected = []
    for ia_nom in candidates:
        real_segment = segment_condition(
            samples, fz_nom=fz_nom, p_nom=p_nom, ia_nom=ia_nom, sa_nom=0.0, v_nom=v_nom, test_type=test_type
        )
        if len(real_segment) >= min_samples:
            detected.append(ia_nom)
    return sorted(detected)
