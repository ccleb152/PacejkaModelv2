"""Tests for pacejka.io.ttc_raw.load_ttc_round.

Builds a synthetic .mat on the fly matching the real Calspan TTC round
layout (confirmed against a real Round-9 Hoosier 16x7.5-10 cornering file
during development -- not committed here, see CLAUDE.md's "no data in the
repo" rule) rather than shipping any real telemetry as a fixture.
"""

import numpy as np
import pytest
from scipy.io import savemat

from pacejka.io.ttc_raw import load_ttc_round


@pytest.fixture
def synthetic_round_path(tmp_path):
    n = 5
    data = {
        "FZ": np.array([-150.0, -136.0, -170.0, -100.0, -50.0]).reshape(n, 1),
        "FX": np.linspace(1, 5, n).reshape(n, 1),
        "FY": np.linspace(-200, -100, n).reshape(n, 1),
        "P": np.full((n, 1), 12.0),
        "IA": np.zeros((n, 1)),
        "SA": np.linspace(-1, 1, n).reshape(n, 1),
        "V": np.full((n, 1), 25.0),
        "N": np.full((n, 1), 300.0),
        "RE": np.full((n, 1), 9.0),
        "RL": np.full((n, 1), 8.8),
        "TSTC": np.full((n, 1), 100.0),
        "TSTI": np.full((n, 1), 110.0),
        "TSTO": np.full((n, 1), 120.0),
        "source": np.array(["Synthetic test fixture"], dtype=object),
        "testid": np.array(["Cornering"], dtype=object),
        "tireid": np.array(["Synthetic 16x7.5-10 test tire"], dtype=object),
    }
    path = tmp_path / "synthetic_round.mat"
    savemat(path, data)
    return path


def test_loads_channels_into_a_dataframe(synthetic_round_path):
    result = load_ttc_round(synthetic_round_path)
    assert list(result.samples["FZ"]) == pytest.approx([-150.0, -136.0, -170.0, -100.0, -50.0])
    assert len(result.samples) == 5


def test_loads_metadata_strings(synthetic_round_path):
    result = load_ttc_round(synthetic_round_path)
    assert result.source == "Synthetic test fixture"
    assert result.testid == "Cornering"
    assert result.tireid == "Synthetic 16x7.5-10 test tire"


def test_raises_on_a_file_with_no_recognized_channels(tmp_path):
    path = tmp_path / "empty.mat"
    savemat(path, {"unrelated_variable": np.array([[1.0]])})
    with pytest.raises(ValueError, match="channel"):
        load_ttc_round(path)
