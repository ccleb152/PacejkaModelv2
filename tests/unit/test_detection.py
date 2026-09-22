"""Tests for pacejka.detection.detect_fz_levels/detect_camber_levels.

Synthetic, fabricated round data (not real telemetry, per CLAUDE.md's
no-data-in-repo rule) shaped like a real TTC round: a continuous SA sweep
recorded separately at each nominal (FZ, IA) combination, with realistic
noise around each nominal value -- the same shape segment_condition's own
tests use.
"""

import numpy as np
import pandas as pd
import pytest

from pacejka.detection import detect_camber_levels, detect_fz_levels

REQUIRED_COLUMNS = ["FZ", "P", "IA", "SA", "V", "FX", "FY", "MZ", "RE", "RL", "N", "TSTC", "TSTI", "TSTO"]


def _condition_block(rng, fz_nom, ia_nom, n=150):
    sa = np.linspace(-12, 12, n)
    return pd.DataFrame(
        {
            "FZ": -fz_nom + rng.normal(scale=1.5, size=n),  # Calspan negative-load convention
            "P": 12.0 + rng.normal(scale=0.1, size=n),
            "IA": ia_nom + rng.normal(scale=0.02, size=n),
            "SA": sa,
            "V": 25.0 + rng.normal(scale=0.1, size=n),
            "FX": rng.normal(scale=5, size=n),
            "FY": -fz_nom * np.tanh(sa / 6) + rng.normal(scale=5, size=n),
            "MZ": rng.normal(scale=2, size=n),
            "RE": np.full(n, 9.0),
            "RL": np.full(n, 8.8),
            "N": np.full(n, 300.0),
            "TSTC": np.full(n, 100.0),
            "TSTI": np.full(n, 110.0),
            "TSTO": np.full(n, 120.0),
        }
    )


@pytest.fixture
def synthetic_round():
    rng = np.random.RandomState(0)
    blocks = [
        _condition_block(rng, fz_nom, 0.0) for fz_nom in (50.0, 100.0, 150.0, 200.0, 250.0)
    ] + [_condition_block(rng, 150.0, ia_nom) for ia_nom in (2.0, 4.0)]
    samples = pd.concat(blocks, ignore_index=True)
    assert set(REQUIRED_COLUMNS).issubset(samples.columns)
    return samples


def test_detects_every_tested_fz_level_at_zero_camber(synthetic_round):
    detected = detect_fz_levels(synthetic_round, p_nom=12, v_nom=25)
    assert detected == [50.0, 100.0, 150.0, 200.0, 250.0]


def test_detects_no_fz_levels_that_were_never_tested():
    rng = np.random.RandomState(1)
    samples = _condition_block(rng, 150.0, 0.0)
    detected = detect_fz_levels(samples, p_nom=12, v_nom=25)
    assert detected == [150.0]


def test_detects_every_tested_camber_level_at_the_given_load(synthetic_round):
    detected = detect_camber_levels(synthetic_round, fz_nom=150.0, p_nom=12, v_nom=25)
    assert detected == [0.0, 2.0, 4.0]


def test_detects_no_camber_levels_when_load_condition_has_no_data():
    rng = np.random.RandomState(2)
    samples = _condition_block(rng, 150.0, 0.0)
    detected = detect_camber_levels(samples, fz_nom=50.0, p_nom=12, v_nom=25)
    assert detected == []


def test_min_samples_filters_out_transient_noise(synthetic_round):
    # A handful of stray IA readings near a value that was never really
    # tested (e.g. mid-sweep transition points) shouldn't count as a
    # detected level.
    rng = np.random.RandomState(3)
    noise_rows = _condition_block(rng, 150.0, 1.0, n=3)
    augmented = pd.concat([synthetic_round, noise_rows], ignore_index=True)
    detected = detect_camber_levels(augmented, fz_nom=150.0, p_nom=12, v_nom=25)
    assert 1.0 not in detected
    assert detected == [0.0, 2.0, 4.0]
