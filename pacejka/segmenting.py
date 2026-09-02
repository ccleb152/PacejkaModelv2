"""Port of Data_Finder_v3.m.

Filters one raw TTC round down to the samples actually taken "at" a given
nominal test condition (FZ/P/IA/SA/V), using pacejka.ranges.para_range for
the acceptance bands, and computes the same derived channels the original
does (T_Avg, NFX, NFY, Vc, Vs).

ARCHITECTURE DIVERGENCE FROM MATLAB (deliberate, not a numeric change):
Data_Finder_v3.m writes one .mat file per nominal condition to disk, which
the Raw_Data_Fitter_*/Data_Compiler functions then re-load by reconstructing
the filename from the same nominal values. That two-step file handoff is a
side effect of MATLAB scripts not being able to hand a struct back to a
caller as easily as a function can -- it isn't part of the physics or the
math. `segment_condition` below returns an in-memory DataFrame for one
condition directly; the fitters that come next in the migration (Sec.2 of
MIGRATION_PLAN.md) consume that DataFrame directly instead of a filename
built by string concatenation. See CLAUDE.md for the full rationale.
"""

from __future__ import annotations

import math

import pandas as pd

from pacejka.ranges import para_range

_RPM_TO_RAD_PER_SEC = 2 * math.pi / 60
_IN_PER_SEC_TO_MPH = 3600 / (12 * 5280)


def segment_condition(
    samples: pd.DataFrame,
    fz_nom: float,
    p_nom: float,
    ia_nom: float,
    sa_nom: float,
    v_nom: float,
    test_type: str,
) -> pd.DataFrame:
    """Select and enrich the samples matching one nominal test condition.

    `samples` is a raw round's per-sample channels (e.g. from
    `pacejka.io.ttc_raw.load_ttc_round(...).samples`), and must contain at
    least FZ, P, IA, SA, V, FX, FY, RE, RL, N, TSTC, TSTI, TSTO.

    A sample counts as "at" the nominal condition when FZ (compared by
    magnitude -- Calspan's convention records normal load as negative) and
    P and IA fall inside the pacejka.ranges.para_range band for that
    channel (inclusive), and SA and V fall strictly inside theirs
    (exclusive) -- this mirrors Data_Finder_v3.m's mix of `>=`/`<=` for
    FZ/P/IA and `>`/`<` for SA/V exactly; it isn't a typo to "fix".

    Differs from Data_Finder_v3.m in one respect beyond the file-I/O
    architecture change (see module docstring): the original re-checks
    `isnan(IA_Nom)`/`isnan(V_Nom)` on the *entire sweep vector* passed into
    the enclosing loop, not the current element -- because MATLAB's `if` on
    a non-scalar array is only true when every element is nonzero, that
    check only fires when every value in the sweep is NaN, never for one
    NaN entry mixed with real ones. Combined with ParaRange's own
    isreal(NaN)-is-True bug (CLAUDE.md quirk #5), a NaN entry within a
    mixed IA/V sweep would silently produce NaN bounds in the original --
    which makes every `>=`/`<=` comparison false and drops all data for
    that condition, rather than the "NaN nominal means don't filter on
    this channel" behavior that's evidently intended (and that FZ_Nom
    already gets, directly in `para_range`). This function checks the
    scalar `ia_nom`/`v_nom` actually passed in, which is what was clearly
    intended. See CLAUDE.md quirk #7. This never changes behavior for any
    sweep configuration used elsewhere in this codebase, since none of them
    mix a NaN entry into an otherwise-real IA_Nom/SA_Nom/V_Nom sweep.
    """
    bounds = para_range(fz_nom, p_nom, ia_nom, sa_nom, v_nom, test_type)

    ia_high, ia_low = bounds.ia_high, bounds.ia_low
    if math.isnan(ia_nom):
        ia_high, ia_low = math.inf, -math.inf

    v_high, v_low = bounds.v_high, bounds.v_low
    if math.isnan(v_nom):
        v_high, v_low = math.inf, -math.inf

    fz_mag = samples["FZ"].abs()
    mask = (
        (fz_mag >= bounds.fz_low)
        & (fz_mag <= bounds.fz_high)
        & (samples["P"] >= bounds.p_low)
        & (samples["P"] <= bounds.p_high)
        & (samples["IA"] >= ia_low)
        & (samples["IA"] <= ia_high)
        & (samples["SA"] < bounds.sa_high)
        & (samples["SA"] > bounds.sa_low)
        & (samples["V"] < v_high)
        & (samples["V"] > v_low)
    )

    selected = samples.loc[mask].reset_index(drop=True)

    result = selected.copy()
    result["T_Avg"] = selected[["TSTC", "TSTI", "TSTO"]].mean(axis=1)
    result["NFX"] = selected["FX"] / selected["FZ"]
    result["NFY"] = selected["FY"] / selected["FZ"]

    angular_rate = selected["N"] * _RPM_TO_RAD_PER_SEC
    result["Vc"] = selected["V"] - selected["RL"] * angular_rate * _IN_PER_SEC_TO_MPH
    result["Vs"] = selected["V"] - selected["RE"] * angular_rate * _IN_PER_SEC_TO_MPH

    return result
