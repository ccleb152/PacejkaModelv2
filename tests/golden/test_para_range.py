"""Golden tests for pacejka.ranges.para_range.

ParaRange.m is a pure lookup/arithmetic function with no fitting involved,
so its MATLAB output is fully determined by the constants in the source
file itself -- these fixtures are transcribed directly from ParaRange.m's
hardcoded branches rather than captured by running MATLAB, and comparison
is exact (see MIGRATION_PLAN.md Sec.5, "deterministic functions" tolerance
regime).
"""

import json
import math
from pathlib import Path

import pytest

from pacejka.ranges import para_range

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "para_range"


def _load_fixtures():
    for path in sorted(FIXTURES_DIR.glob("*.json")):
        yield path.stem, json.loads(path.read_text())


FIXTURES = list(_load_fixtures())


@pytest.mark.parametrize("name,fixture", FIXTURES, ids=[f[0] for f in FIXTURES])
def test_para_range_matches_matlab(name, fixture):
    result = para_range(**fixture["inputs"])
    expected = fixture["outputs"]

    for field, expected_value in expected.items():
        actual_value = getattr(result, field)
        if isinstance(expected_value, float) and math.isnan(expected_value):
            assert math.isnan(actual_value), f"{field}: expected NaN, got {actual_value}"
        else:
            assert actual_value == pytest.approx(expected_value, rel=1e-9, abs=1e-12), field
