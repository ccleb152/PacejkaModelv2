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

from pacejka.detection import detect_camber_levels, detect_fz_levels, detect_sa_levels

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


def _braking_block(rng, fz_nom, sl_min=-0.15, sl_max=0.13, n=150, sa_nom=0.0):
    sl = np.linspace(sl_min, sl_max, n)
    return pd.DataFrame(
        {
            "FZ": -fz_nom + rng.normal(scale=1.5, size=n),
            "P": 12.0 + rng.normal(scale=0.1, size=n),
            "IA": rng.normal(scale=0.02, size=n),
            "SA": sa_nom + rng.normal(scale=0.02, size=n),  # see para_range's _BRAKING_SA_BANDS
            "SL": sl,
            "V": 25.0 + rng.normal(scale=0.1, size=n),
            "FX": fz_nom * np.tanh(sl * 15) + rng.normal(scale=5, size=n),
            "FY": rng.normal(scale=5, size=n),
            "MZ": rng.normal(scale=2, size=n),
            "RE": np.full(n, 9.0),
            "RL": np.full(n, 8.8),
            "N": np.full(n, 300.0),
            "TSTC": np.full(n, 100.0),
            "TSTI": np.full(n, 110.0),
            "TSTO": np.full(n, 120.0),
        }
    )


def test_braking_excludes_a_detected_level_whose_sl_sweep_is_too_narrow():
    # Regression test: a transient/settling segment can have >= min_samples
    # and >= 2 distinct SL values (clearing the generic checks) while still
    # being nowhere near a real ~0.3-wide braking/drive sweep -- confirmed
    # against real R20 18x6-10 BrakeDrive data, where an auto-detected
    # Fz=100 lbf "load level" had a 0.015-wide SL range. See
    # pacejka/quality.py's MIN_SL_SWEEP_RANGE and MODEL_CHANGES.md.
    rng = np.random.RandomState(4)
    real_sweep = _braking_block(rng, 150.0)
    transient = _braking_block(rng, 100.0, sl_min=-0.01, sl_max=0.0, n=50)
    samples = pd.concat([real_sweep, transient], ignore_index=True)

    detected = detect_fz_levels(samples, p_nom=12, v_nom=25, test_type="Braking")
    assert detected == [150.0]


def test_detects_every_tested_sa_level_at_one_load_and_camber():
    rng = np.random.RandomState(5)
    blocks = [_braking_block(rng, 150.0, sa_nom=sa) for sa in (0.0, -3.0, -6.0)]
    samples = pd.concat(blocks, ignore_index=True)
    detected = detect_sa_levels(samples, fz_nom=150.0, ia_nom=0.0, p_nom=12, v_nom=25)
    assert detected == [-6.0, -3.0, 0.0]


def test_sa_levels_excludes_a_too_narrow_sl_sweep():
    # Same class of regression as detect_fz_levels's narrow-sweep test --
    # a transient segment at a real nominal SA band shouldn't count as a
    # detected combined-slip condition if its SL range is too narrow to
    # fit against.
    rng = np.random.RandomState(6)
    real_sweep = _braking_block(rng, 150.0, sa_nom=-3.0)
    transient = _braking_block(rng, 150.0, sl_min=-0.01, sl_max=0.0, n=50, sa_nom=-6.0)
    samples = pd.concat([real_sweep, transient], ignore_index=True)

    detected = detect_sa_levels(samples, fz_nom=150.0, ia_nom=0.0, p_nom=12, v_nom=25)
    assert detected == [-3.0]


def test_detects_no_sa_levels_that_were_never_tested():
    rng = np.random.RandomState(7)
    samples = _braking_block(rng, 150.0, sa_nom=0.0)
    detected = detect_sa_levels(samples, fz_nom=150.0, ia_nom=0.0, p_nom=12, v_nom=25)
    assert detected == [0.0]
