"""Data-quality checks for raw TTC rounds and segmented conditions.

Not a MATLAB port -- the original tool had no equivalent check at all,
which is exactly the problem: some raw round files turn out to be
incomplete or aborted runs (a test cut short by an unstable load
controller, a bad pressure regulator, etc. -- see real examples in the
team's own Calspan run-comment logs, e.g. "Test aborted, Psi Control was
bad" / "unstable load control"), and feeding one into the fitting
pipeline either crashes deep inside `scipy.optimize` with a confusing
error or, worse, produces a fit that looks plausible but is quietly
garbage. These checks catch the *symptom* (too little data, a sensor
that never moves, a slip-angle sweep that never completes) directly from
the round's own channel data, rather than trying to parse the free-text,
per-run comment codes in Calspan's summary spreadsheets -- those aren't
shipped with the raw round file itself and their format/legend varies
round to round, so they can't be checked programmatically at load time.

Two levels, matching the two places a problem can show up:
- `check_round_quality` -- the whole loaded file, before any condition is
  segmented out of it (missing/dead channels, too few samples overall).
- `check_condition_quality` -- one already-segmented nominal condition
  (too few samples for that condition specifically, or a slip-angle sweep
  that doesn't span a real cornering test's range) -- a whole file can
  look fine in aggregate while one condition inside it was cut short.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

Severity = Literal["error", "warning"]

# Channels every downstream step (segmenting, spline fitting, term
# finding) actually reads. Absence or a dead/constant reading in any of
# these means the round can't be fit meaningfully, not just "some other
# channel is missing" -- see load_ttc_round, which already errors if
# *none* of the broader CHANNEL_VARS are present; this is the narrower,
# per-channel version of that check.
REQUIRED_CHANNELS = ("FZ", "SA", "IA", "P", "V", "FY", "MZ")

# A full cornering round is thousands of samples across every tested
# condition; a run cut short after one or two sweeps is a tiny fraction
# of that. This is deliberately conservative (a real full round is
# usually >>1000) so it only fires on genuinely truncated files.
MIN_TOTAL_SAMPLES = 500

# A real cornering slip-angle sweep spans roughly +-12 deg (the fixed
# evaluation grids in fitters/fy.py and fitters/mz.py both assume this).
# A sweep that never gets past a few degrees peak-to-peak means the test
# was cut off before completing its first pass.
MIN_SA_SWEEP_RANGE_DEG = 15.0

# Below this many samples, a segmented condition is too sparse to spline-
# fit meaningfully -- matches pacejka.detection's own DEFAULT_MIN_SAMPLES,
# the threshold already used to decide whether a condition was "tested"
# at all.
MIN_CONDITION_SAMPLES = 10


@dataclass(frozen=True)
class QualityIssue:
    """One data-quality problem found in a round or a segmented condition.

    `severity="error"` means the affected data can't be fit at all (a
    required channel is missing/dead, or there's essentially no data);
    `severity="warning"` means the data is fittable but suspect (e.g. a
    truncated slip-angle sweep still has enough points to spline-fit, but
    the resulting curve won't represent a full sweep).
    """

    severity: Severity
    message: str


def check_round_quality(
    samples: pd.DataFrame,
    min_total_samples: int = MIN_TOTAL_SAMPLES,
) -> list[QualityIssue]:
    """Whole-file checks, run right after loading a round and before any
    condition is segmented out of it."""
    issues: list[QualityIssue] = []

    if len(samples) < min_total_samples:
        issues.append(
            QualityIssue(
                "error",
                f"This file has only {len(samples)} samples total -- a full test "
                f"round is normally in the thousands. This looks like an "
                f"incomplete or aborted run, not a full round.",
            )
        )

    for channel in REQUIRED_CHANNELS:
        if channel not in samples.columns:
            issues.append(QualityIssue("error", f"Missing expected channel '{channel}'."))
            continue
        column = samples[channel]
        if column.isna().all():
            issues.append(QualityIssue("error", f"Channel '{channel}' is entirely missing/NaN."))
        elif len(column) > 1 and column.nunique(dropna=True) <= 1:
            issues.append(
                QualityIssue(
                    "error",
                    f"Channel '{channel}' never changes value across the whole file -- "
                    f"this usually means a sensor was dead or the test was aborted "
                    f"before it started moving.",
                )
            )

    return issues


def check_condition_quality(
    segment: pd.DataFrame,
    fz_nom: float,
    ia_nom: float,
    min_samples: int = MIN_CONDITION_SAMPLES,
    min_sa_range_deg: float = MIN_SA_SWEEP_RANGE_DEG,
) -> list[QualityIssue]:
    """Checks for one already-segmented nominal (Fz, IA) condition.

    A round can pass `check_round_quality` in aggregate (plenty of total
    samples, every channel present and moving) while one specific
    condition inside it was still cut short -- e.g. the load controller
    went unstable partway through the load sweep, corrupting just that
    one condition's data. `condition_label` in each message identifies
    which (Fz, IA) condition the issue is about, since the pipeline runs
    this once per condition.
    """
    label = f"Fz={fz_nom:g} lbf, IA={ia_nom:g} deg"
    issues: list[QualityIssue] = []

    if len(segment) < min_samples:
        issues.append(
            QualityIssue(
                "error",
                f"{label}: only {len(segment)} samples matched this condition -- "
                f"too few to fit (need at least {min_samples}). This condition's "
                f"sweep may not have been run, or was cut short.",
            )
        )
        return issues

    sa = segment["SA"].dropna()
    if not sa.empty:
        sa_range = float(sa.max() - sa.min())
        if sa_range < min_sa_range_deg:
            issues.append(
                QualityIssue(
                    "warning",
                    f"{label}: the slip-angle sweep only spans {sa_range:.1f} deg "
                    f"peak-to-peak -- a full cornering sweep is normally "
                    f">= {min_sa_range_deg:g} deg. This condition's data may be an "
                    f"incomplete sweep rather than a full one.",
                )
            )

    return issues
