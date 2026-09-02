"""Port of ParaRange.m.

Given nominal test-condition values, returns acceptance bands used to
filter raw TTC samples down to the ones actually taken at (approximately)
that nominal condition. Pure function: no I/O, no dependency on any other
ported module.
"""

from __future__ import annotations

import math
from typing import NamedTuple


class ParaRangeBounds(NamedTuple):
    fz_high: float
    fz_low: float
    p_high: float
    p_low: float
    ia_high: float
    ia_low: float
    sa_high: float
    sa_low: float
    v_high: float
    v_low: float


# FZ (lbf) acceptance bands are identical for both test types in the
# original; P (psi) bands are shared too. SA (deg) bands differ: Cornering
# uses one fixed +/-15 deg band regardless of SA_Nom, Braking looks SA_Nom
# up in its own table.
_FZ_BANDS = {
    350: (375, 315),
    250: (275, 226),
    200: (225, 175),
    150: (170, 136),
    100: (115, 80),
    50: (65, 35),
}

_P_BANDS = {
    8: (8.99, 7),
    10: (10.5, 9.00),
    11: (11.5, 10.51),
    12: (12.99, 11.51),
    14: (15, 13),
}

_BRAKING_SA_BANDS = {
    0: (0.1, -0.1),
    -3: (-2.9, -3.1),
    -6: (-5.9, -6.1),
}


def _lookup(bands: dict, nominal: float, label: str) -> tuple[float, float]:
    for key, bounds in bands.items():
        if nominal == key:
            return bounds
    raise ValueError(
        f"No acceptance band defined for {label}={nominal!r}. "
        f"Known nominal values: {sorted(bands)}."
    )


def para_range(
    fz_nom: float,
    p_nom: float,
    ia_nom: float,
    sa_nom: float,
    v_nom: float,
    test_type: str,
) -> ParaRangeBounds:
    """Acceptance bands for each channel around a nominal test condition.

    Port of ParaRange.m. Raw TTC samples rarely land exactly on the nominal
    condition a sweep was aiming for (e.g. FZ_Nom=150 lbf might actually
    read 148.3 lbf), so callers use these bounds to select the samples that
    count as "at" that nominal condition.

    Differences from the MATLAB original (see CLAUDE.md "Known MATLAB
    quirks"):
    - An unmapped FZ_Nom/P_Nom/SA_Nom nominal value raises ValueError
      instead of silently leaving the corresponding bound undefined (which
      in MATLAB either errors downstream or carries a stale value over from
      a previous loop iteration).
    - `test_type` matching is case-insensitive outright, rather than
      MATLAB's explicit `'Cornering'`/`'cornering'` (and `'Brake'`/
      `'brake'`/`'Braking'`/`'braking'`) enumeration.
    - The dead `if 1==1` around SA_High/SA_Low in the Cornering branch is
      just an unconditional assignment here.

    NOTE ON A REAL MATLAB BUG THIS PRESERVES: in the original, the IA and V
    bands are guarded by `isreal(...)`, evidently intended to special-case
    NaN via a trailing `isnan(...)` branch. But `isreal(nan)` is `True` in
    MATLAB (NaN has no imaginary part), so that NaN branch is unreachable
    dead code -- a NaN `ia_nom`/`v_nom` actually produces NaN +/- a constant
    here (not +/-inf, despite appearances). `Data_Finder_v3.m` compensates
    for this by re-checking `isnan(IA_Nom)`/`isnan(V_Nom)` itself right
    after calling `ParaRange` and overwriting the bounds with +/-inf when
    needed -- so this quirk is preserved here for golden-test fidelity, and
    the Python port of `Data_Finder_v3` (`segmenting.py`) must replicate
    that same compensating override rather than assume `para_range` already
    handles NaN.
    """
    normalized_type = test_type.strip().lower()

    if normalized_type == "cornering":
        if math.isnan(fz_nom):
            fz_high, fz_low = math.inf, -math.inf
        else:
            fz_high, fz_low = _lookup(_FZ_BANDS, fz_nom, "FZ_Nom")

        p_high, p_low = _lookup(_P_BANDS, p_nom, "P_Nom")
        sa_high, sa_low = 15.0, -15.0

        ia_high, ia_low = ia_nom + 0.075, ia_nom - 0.075
        v_high, v_low = v_nom + 2.5, v_nom - 2.5

    elif normalized_type in ("brake", "braking"):
        fz_high, fz_low = _lookup(_FZ_BANDS, fz_nom, "FZ_Nom")
        p_high, p_low = _lookup(_P_BANDS, p_nom, "P_Nom")
        sa_high, sa_low = _lookup(_BRAKING_SA_BANDS, sa_nom, "SA_Nom")

        ia_high, ia_low = ia_nom + 0.075, ia_nom - 0.075
        v_high, v_low = v_nom + 0.2, v_nom - 0.2

    else:
        raise ValueError(
            f"Unknown test_type {test_type!r}; expected 'Cornering' or 'Braking'."
        )

    return ParaRangeBounds(
        fz_high=fz_high,
        fz_low=fz_low,
        p_high=p_high,
        p_low=p_low,
        ia_high=ia_high,
        ia_low=ia_low,
        sa_high=sa_high,
        sa_low=sa_low,
        v_high=v_high,
        v_low=v_low,
    )
