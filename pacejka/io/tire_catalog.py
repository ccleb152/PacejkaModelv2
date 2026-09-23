"""A browsable catalog of raw TTC round files, built from their own
embedded `tireid` metadata -- the "tire database" behind the Streamlit
app's compound -> diameter -> width selector.

Not a MATLAB port -- the original tool has no equivalent; a user always
pointed `Raw_Data_Fitter_*` at one hand-picked file. This scans a folder
tree of raw round files (e.g. the team's `RawDataFiles/` folder, one
subfolder per test type -- `Cornering`, `BrakeDrive`, matching Calspan's
own round organization) and, for each file, parses which physical tire it
is straight out of the file's own `tireid` string -- no cross-referencing
Calspan's separate Tire ID Schedule spreadsheet needed, since the raw
round file already carries this.

Two `tireid` formats show up across the team's actual rounds (Round 6 vs.
Rounds 8/9), because Calspan's own free-text convention isn't consistent
round to round:

    "Hoosier 18.0 x 6.0 10 R25B (Item 43101), 7 inch rim"       (Round 6)
    "Hoosier 6.0 / 18.0 10 LCO C2000 (Item 41100), 7 inch rim"  (Round 6,
                                                                  width/diameter
                                                                  swapped --
                                                                  see below)
    "Hoosier 43075 16x7.5-10 R25B, 7 inch rim"                  (Rounds 8/9)

`parse_tire_description` handles both. The width/diameter order in the
first form isn't a typo -- Hoosier's own size notation writes some tire
families as "width/diameter" instead of "diameter x width" (the same
pattern as a road tire's "205/50R16"), so which number comes first in the
string isn't a reliable signal. A real FSAE tire's diameter (10-20+ in) is
always larger than its width (6-9 in), so `parse_tire_description` picks
the larger of the two numbers as the diameter regardless of which side of
the separator it's on -- robust to both orderings without needing to
special-case which round used which convention.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import loadmat

from pacejka.io.ttc_raw import TtcRound, load_ttc_round

_METADATA_VARS = ("source", "testid", "tireid", "RUN")

# "<mfr> <item> <d1>x<d2>-<wheel> <compound>, <rim>" -- Rounds 8/9's
# consistent format: item code before the size, hyphen before the wheel
# diameter.
_FORMAT_ITEM_FIRST = re.compile(
    r"^(?P<mfr>\S+)\s+(?P<item>\d+)\s+(?P<d1>\d+(?:\.\d+)?)\s*[x/]\s*(?P<d2>\d+(?:\.\d+)?)"
    r"-(?P<wheel>\d+(?:\.\d+)?)\s+(?P<compound>[^,]+?)\s*,\s*(?P<rest>.+)$"
)

# "<mfr> <d1> x <d2> <wheel> <compound> (Item <item>), <rim>" -- Round 6's
# format: item code trails in parentheses, no hyphen before the wheel
# diameter.
_FORMAT_ITEM_TRAILING = re.compile(
    r"^(?P<mfr>\S+)\s+(?P<d1>\d+(?:\.\d+)?)\s*[x/]\s*(?P<d2>\d+(?:\.\d+)?)\s+(?P<wheel>\d+(?:\.\d+)?)"
    r"\s+(?P<compound>[^,(]+?)\s*(?:\(Item\s*(?P<item>\d+)\))?\s*,\s*(?P<rest>.+)$"
)


@dataclass(frozen=True)
class TireSpec:
    """One physical tire specification, parsed from a raw round's own
    `tireid` metadata string."""

    manufacturer: str
    compound: str
    diameter_in: float
    width_in: float
    wheel_diameter_in: float
    item_code: str | None
    raw_tireid: str


class UnrecognizedTireDescription(ValueError):
    """Raised when a `tireid` string doesn't match any known Calspan
    format. Deliberately not swallowed/skipped silently -- a new round
    using a third format should surface as an actionable error (add a
    pattern here), not quietly vanish from the catalog."""

    def __init__(self, tireid: str):
        super().__init__(
            f"Don't recognize the tire description format: {tireid!r}. "
            f"This round may use a new Calspan tireid format not yet "
            f"handled by pacejka.io.tire_catalog.parse_tire_description."
        )


def parse_tire_description(tireid: str) -> TireSpec:
    """Parse a raw round's `tireid` string into a `TireSpec`."""
    match = _FORMAT_ITEM_FIRST.match(tireid) or _FORMAT_ITEM_TRAILING.match(tireid)
    if match is None:
        raise UnrecognizedTireDescription(tireid)

    fields = match.groupdict()
    d1, d2 = float(fields["d1"]), float(fields["d2"])
    return TireSpec(
        manufacturer=fields["mfr"],
        compound=fields["compound"].strip(),
        diameter_in=max(d1, d2),
        width_in=min(d1, d2),
        wheel_diameter_in=float(fields["wheel"]),
        item_code=fields.get("item"),
        raw_tireid=tireid,
    )


@dataclass(frozen=True)
class CatalogEntry:
    """One cataloged raw round file."""

    path: Path
    test_type: str
    run: int | None
    tire: TireSpec
    source: str
    testid: str


@dataclass(frozen=True)
class CatalogScanResult:
    """The result of scanning a folder tree for raw round files.

    `errors` holds (path, message) for any `.mat` file that couldn't be
    read or whose `tireid` couldn't be parsed -- surfaced to the user
    rather than silently dropped, since a truncated upload or a new
    tireid format both mean the catalog is missing data it should have.
    """

    entries: list[CatalogEntry]
    errors: list[tuple[Path, str]]


def _unwrap_scalar_str(value) -> str:
    while isinstance(value, np.ndarray):
        value = value.ravel()[0]
    return str(value)


def _load_one(path: Path, test_type: str) -> CatalogEntry:
    raw = loadmat(path, variable_names=_METADATA_VARS)
    missing = [var for var in ("source", "testid", "tireid") if var not in raw]
    if missing:
        raise ValueError(f"missing expected metadata field(s): {', '.join(missing)}")

    tireid = _unwrap_scalar_str(raw["tireid"])
    tire = parse_tire_description(tireid)

    run = None
    if "RUN" in raw:
        run_values = np.unique(raw["RUN"])
        if run_values.size:
            run = int(run_values[0])

    return CatalogEntry(
        path=path,
        test_type=test_type,
        run=run,
        tire=tire,
        source=_unwrap_scalar_str(raw["source"]),
        testid=_unwrap_scalar_str(raw["testid"]),
    )


def scan_raw_data_folder(root: Path | str) -> CatalogScanResult:
    """Scan `root` for raw round `.mat` files, one subfolder per test type
    (e.g. `root/Cornering/*.mat`, `root/BrakeDrive/*.mat`) -- matching how
    the team's own `RawDataFiles/` folder is organized. Files directly in
    `root` (not in a test-type subfolder) are skipped, since there'd be no
    way to know their test type.
    """
    root = Path(root)
    entries: list[CatalogEntry] = []
    errors: list[tuple[Path, str]] = []

    for test_type_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for path in sorted(test_type_dir.glob("*.mat")):
            try:
                entries.append(_load_one(path, test_type_dir.name))
            except Exception as exc:  # noqa: BLE001 -- report, don't crash the scan
                errors.append((path, str(exc)))

    return CatalogScanResult(entries=entries, errors=errors)


def list_compounds(entries: list[CatalogEntry], test_type: str | None = None) -> list[str]:
    """Distinct compounds present, sorted alphabetically."""
    return sorted({e.tire.compound for e in entries if test_type is None or e.test_type == test_type})


def list_diameters(entries: list[CatalogEntry], compound: str, test_type: str | None = None) -> list[float]:
    """Distinct diameters (in) tested for `compound`, ascending."""
    return sorted(
        {
            e.tire.diameter_in
            for e in entries
            if e.tire.compound == compound and (test_type is None or e.test_type == test_type)
        }
    )


def list_widths(
    entries: list[CatalogEntry], compound: str, diameter_in: float, test_type: str | None = None
) -> list[float]:
    """Distinct widths (in) tested for `compound` at `diameter_in`, ascending."""
    return sorted(
        {
            e.tire.width_in
            for e in entries
            if e.tire.compound == compound
            and e.tire.diameter_in == diameter_in
            and (test_type is None or e.test_type == test_type)
        }
    )


def load_combined_round(entries: list[CatalogEntry]) -> TtcRound:
    """Load every cataloged file in `entries` and concatenate their
    samples into one `TtcRound` -- e.g. every Cornering run recorded for
    one (compound, diameter, width) tire spec, so the fitting pipeline
    sees the full tested load/camber sweep across all of that tire's
    runs, not just one file's worth (matching the multi-run reality of
    real test sessions -- see CLAUDE.md's multi-load-sweep roadmap).

    Raises `ValueError` if `entries` is empty. The combined round's
    `source`/`testid`/`tireid` describe the whole group rather than any
    one file.
    """
    if not entries:
        raise ValueError("No matching runs to load.")

    rounds = [load_ttc_round(entry.path) for entry in entries]
    combined_samples = pd.concat([r.samples for r in rounds], ignore_index=True)

    tire = entries[0].tire
    run_numbers = ", ".join(str(e.run) for e in entries if e.run is not None)
    return TtcRound(
        samples=combined_samples,
        source=f"Tire database: {len(entries)} run(s) (#{run_numbers})",
        testid=entries[0].testid,
        tireid=tire.raw_tireid,
    )


def find_entries(
    entries: list[CatalogEntry],
    compound: str,
    diameter_in: float,
    width_in: float,
    test_type: str | None = None,
) -> list[CatalogEntry]:
    """Every cataloged run matching one (compound, diameter, width) tire
    spec, sorted by run number."""
    matches = [
        e
        for e in entries
        if e.tire.compound == compound
        and e.tire.diameter_in == diameter_in
        and e.tire.width_in == width_in
        and (test_type is None or e.test_type == test_type)
    ]
    return sorted(matches, key=lambda e: (e.run is None, e.run))
