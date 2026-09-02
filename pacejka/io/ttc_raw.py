"""Loading raw TTC round data.

Raw TTC (Tire Testing Consortium) round files are the Calspan-format .mat
files described in MIGRATION_PLAN.md Sec.3.1: one row per sample, with
channel arrays (`FZ`, `FX`, `FY`, `MZ`, `MX`, `SA`, `SL`, `SR`, `IA`, `P`,
`V`, `N`, `NFX`, `NFY`, `RE`, `RL`, `TSTC`/`TSTI`/`TSTO`, `ET`, `AMBTMP`,
`RST`, `RUN`) plus a `channel` name/units table and `source`/`testid`/
`tireid` metadata strings. This module reads one into a plain
pandas.DataFrame -- no MATLAB `eval`/dynamic-fieldname reconstruction, just
direct columns.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import loadmat

# Every channel this pipeline ever reads off a raw round file. A given file
# need not contain all of them (e.g. SL/SR are near-zero placeholders on a
# pure-cornering round) -- whichever are present get loaded as columns.
CHANNEL_VARS = (
    "ET", "V", "N", "SA", "IA", "RL", "RE", "P", "FX", "FY", "FZ", "MX",
    "MZ", "NFX", "NFY", "RST", "TSTI", "TSTC", "TSTO", "AMBTMP", "SR", "SL",
    "RUN",
)

_METADATA_VARS = ("source", "testid", "tireid")


def _unwrap_scalar_str(value) -> str:
    """Peel nested 1-element arrays down to a plain string.

    MATLAB char arrays round-trip through scipy.io as differently-nested
    object arrays depending on how they were saved (a direct char array
    loads flat, a cell-wrapped string loads as an array-of-array-of-...),
    so this keeps unwrapping one level of ndarray at a time until it hits
    an actual string.
    """
    while isinstance(value, np.ndarray):
        value = value.ravel()[0]
    return str(value)


@dataclass(frozen=True)
class TtcRound:
    """One raw TTC test round: per-sample channels plus round metadata."""

    samples: pd.DataFrame
    source: str
    testid: str
    tireid: str


def load_ttc_round(path: str | Path) -> TtcRound:
    """Load a raw TTC round .mat file into a TtcRound."""
    raw = loadmat(path)

    columns = {var: raw[var].ravel() for var in CHANNEL_VARS if var in raw}
    if not columns:
        raise ValueError(
            f"{path}: none of the expected TTC channel variables "
            f"({', '.join(CHANNEL_VARS)}) were found in this file."
        )
    samples = pd.DataFrame(columns)

    metadata = {}
    for key in _METADATA_VARS:
        metadata[key] = _unwrap_scalar_str(raw[key]) if key in raw else ""

    return TtcRound(samples=samples, **metadata)
