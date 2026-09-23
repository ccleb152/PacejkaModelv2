"""Tests for pacejka.io.tire_catalog. Not a MATLAB port -- the original
tool has no equivalent -- so plain unit tests, per CLAUDE.md's conventions
for non-port utility modules.

The `tireid` strings used here are the exact formats found in the team's
real Round 6/8/9 raw files (see the module docstring) -- they're pure
metadata text (a tire size description), not measurement data, so using
the real strings verbatim doesn't run afoul of CLAUDE.md's "no real TTC
telemetry in the repo" rule. The .mat files built for scan_raw_data_folder
tests are synthetic (tiny fabricated channel arrays), matching every other
test's pattern.
"""

import numpy as np
import pytest
from scipy.io import savemat

from pacejka.io.tire_catalog import (
    UnrecognizedTireDescription,
    find_entries,
    list_compounds,
    list_diameters,
    list_widths,
    load_combined_round,
    parse_tire_description,
    scan_raw_data_folder,
)


def test_parses_item_first_format():
    spec = parse_tire_description("Hoosier 43075 16x7.5-10 R25B, 7 inch rim")
    assert spec.manufacturer == "Hoosier"
    assert spec.compound == "R25B"
    assert spec.diameter_in == 16.0
    assert spec.width_in == 7.5
    assert spec.wheel_diameter_in == 10.0
    assert spec.item_code == "43075"


def test_parses_item_trailing_format():
    spec = parse_tire_description("Hoosier 18.0 x 6.0 10 R25B (Item 43101), 7 inch rim")
    assert spec.compound == "R25B"
    assert spec.diameter_in == 18.0
    assert spec.width_in == 6.0
    assert spec.item_code == "43101"


def test_handles_width_before_diameter_ordering():
    # Hoosier's own size notation for some families writes width/diameter
    # instead of diameter x width (like a road tire's "205/50R16") -- the
    # larger number should still be picked as the diameter regardless of
    # which side of the separator it's on.
    spec = parse_tire_description("Hoosier 6.0 / 18.0 10 LCO C2000 (Item 41100), 7 inch rim")
    assert spec.diameter_in == 18.0
    assert spec.width_in == 6.0
    # "LCO C2000" (Round 6) and "LCO" (Round 8) are the same physical
    # compound -- confirmed by the team, see _COMPOUND_ALIASES.
    assert spec.compound == "LCO"


def test_normalizes_known_compound_aliases_to_one_canonical_label():
    round6 = parse_tire_description("Hoosier 6.0 / 18.0 10 LCO C2000 (Item 41100), 7 inch rim")
    round8 = parse_tire_description("Hoosier 43075 16x7.5-10 LCO, 7 inch rim")
    assert round6.compound == round8.compound == "LCO"


def test_unrecognized_format_raises_a_clear_error():
    with pytest.raises(UnrecognizedTireDescription, match="Continental 205"):
        parse_tire_description("Continental 205/510R13")


def _write_round(path, tireid, run, source="FSAE TTC Round 9", testid="Cornering", n=20):
    sa = np.linspace(-12, 12, n)
    savemat(
        path,
        {
            "source": source,
            "testid": testid,
            "tireid": tireid,
            "RUN": np.full((n, 1), float(run)),
            "SA": sa.reshape(-1, 1),
            "FZ": np.full((n, 1), -150.0),
            "FY": np.zeros((n, 1)),
            "MZ": np.zeros((n, 1)),
            "IA": np.zeros((n, 1)),
            "P": np.full((n, 1), 12.0),
            "V": np.full((n, 1), 25.0),
        },
    )


@pytest.fixture
def catalog_root(tmp_path):
    cornering = tmp_path / "Cornering"
    brake = tmp_path / "BrakeDrive"
    cornering.mkdir()
    brake.mkdir()

    _write_round(cornering / "run1.mat", "Hoosier 43075 16x7.5-10 R25B, 7 inch rim", run=1)
    _write_round(cornering / "run2.mat", "Hoosier 43075 16x7.5-10 R25B, 7 inch rim", run=2)
    _write_round(cornering / "run3.mat", "Hoosier 43070 16x6-10 R25B, 7 inch rim", run=3)
    _write_round(cornering / "run4.mat", "Hoosier 43075 16x7.5-10 LCO, 7 inch rim", run=4)
    _write_round(brake / "run5.mat", "Hoosier 43075 16x7.5-10 R25B, 7 inch rim", run=5, testid="Braking")

    # A corrupted/truncated upload -- should be reported as an error, not
    # crash the whole scan (this is a real, observed failure mode: a few
    # of the team's own uploaded files came through as 2-byte stubs).
    (cornering / "bad.mat").write_bytes(b"\x00\x01")

    return tmp_path


def test_scans_every_test_type_subfolder(catalog_root):
    result = scan_raw_data_folder(catalog_root)
    assert len(result.entries) == 5
    assert {e.test_type for e in result.entries} == {"Cornering", "BrakeDrive"}


def test_reports_unreadable_files_without_crashing_the_scan(catalog_root):
    result = scan_raw_data_folder(catalog_root)
    assert len(result.errors) == 1
    bad_path, message = result.errors[0]
    assert bad_path.name == "bad.mat"
    assert message


def test_list_compounds_filters_by_test_type(catalog_root):
    result = scan_raw_data_folder(catalog_root)
    assert list_compounds(result.entries, test_type="Cornering") == ["LCO", "R25B"]
    assert list_compounds(result.entries, test_type="BrakeDrive") == ["R25B"]
    assert list_compounds(result.entries) == ["LCO", "R25B"]


def test_list_diameters_and_widths_cascade(catalog_root):
    result = scan_raw_data_folder(catalog_root)
    diameters = list_diameters(result.entries, "R25B", test_type="Cornering")
    assert diameters == [16.0]
    widths = list_widths(result.entries, "R25B", 16.0, test_type="Cornering")
    assert widths == [6.0, 7.5]


def test_find_entries_returns_matching_runs_sorted(catalog_root):
    result = scan_raw_data_folder(catalog_root)
    matches = find_entries(result.entries, "R25B", 16.0, 7.5, test_type="Cornering")
    assert [e.run for e in matches] == [1, 2]


def test_load_combined_round_concatenates_all_matching_runs(catalog_root):
    result = scan_raw_data_folder(catalog_root)
    matches = find_entries(result.entries, "R25B", 16.0, 7.5, test_type="Cornering")
    combined = load_combined_round(matches)
    assert len(combined.samples) == 40  # 2 runs x 20 samples each
    assert "1" in combined.source and "2" in combined.source


def test_load_combined_round_rejects_empty_selection():
    with pytest.raises(ValueError, match="No matching runs"):
        load_combined_round([])
