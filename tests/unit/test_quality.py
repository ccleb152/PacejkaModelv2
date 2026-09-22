"""Tests for pacejka.quality -- not a MATLAB port (the original had no
equivalent check), so plain unit tests against fabricated good/bad data,
per CLAUDE.md's testing conventions for non-port utility modules (see
test_detection.py for the same pattern)."""

import numpy as np
import pandas as pd
import pytest

from pacejka.quality import (
    MIN_CONDITION_SAMPLES,
    MIN_SA_SWEEP_RANGE_DEG,
    MIN_TOTAL_SAMPLES,
    check_condition_quality,
    check_round_quality,
)

REQUIRED_COLUMNS = ["FZ", "SA", "IA", "P", "V", "FY", "MZ"]


def _good_round(n=2000):
    rng = np.random.RandomState(0)
    sa = np.tile(np.linspace(-12, 12, 200), n // 200 + 1)[:n]
    return pd.DataFrame(
        {
            "FZ": -150.0 + rng.normal(scale=1.0, size=n),
            "SA": sa,
            "IA": rng.normal(scale=0.02, size=n),
            "P": 12.0 + rng.normal(scale=0.05, size=n),
            "V": 25.0 + rng.normal(scale=0.1, size=n),
            "FY": -150.0 * np.tanh(sa / 6) + rng.normal(scale=2, size=n),
            "MZ": rng.normal(scale=2, size=n),
        }
    )


def test_a_full_round_has_no_issues():
    assert check_round_quality(_good_round()) == []


def test_flags_too_few_total_samples():
    tiny = _good_round(n=50)
    issues = check_round_quality(tiny)
    assert any(i.severity == "error" and "50 samples" in i.message for i in issues)


def test_exactly_at_the_threshold_is_fine():
    at_threshold = _good_round(n=MIN_TOTAL_SAMPLES)
    issues = check_round_quality(at_threshold)
    assert not any("samples total" in i.message for i in issues)


def test_flags_missing_channel():
    round_ = _good_round().drop(columns=["MZ"])
    issues = check_round_quality(round_)
    assert any(i.severity == "error" and "MZ" in i.message and "Missing" in i.message for i in issues)


def test_flags_all_nan_channel():
    round_ = _good_round()
    round_["FY"] = np.nan
    issues = check_round_quality(round_)
    assert any(i.severity == "error" and "FY" in i.message and "NaN" in i.message for i in issues)


def test_flags_a_stuck_dead_sensor():
    round_ = _good_round()
    round_["IA"] = 0.0  # never changes -- looks like a dead sensor
    issues = check_round_quality(round_)
    assert any(i.severity == "error" and "IA" in i.message and "never changes" in i.message for i in issues)


def test_multiple_problems_are_all_reported():
    round_ = _good_round(n=50).drop(columns=["FZ"])
    issues = check_round_quality(round_)
    messages = [i.message for i in issues]
    assert any("50 samples" in m for m in messages)
    assert any("FZ" in m and "Missing" in m for m in messages)


def _good_condition(n=300):
    rng = np.random.RandomState(1)
    sa = np.linspace(-12, 12, n)
    return pd.DataFrame({"SA": sa, "FY": -150.0 * np.tanh(sa / 6) + rng.normal(scale=1, size=n)})


def test_condition_with_enough_samples_and_full_sweep_has_no_issues():
    issues = check_condition_quality(_good_condition(), fz_nom=150.0, ia_nom=0.0)
    assert issues == []


def test_condition_with_too_few_samples_is_an_error():
    sparse = _good_condition(n=MIN_CONDITION_SAMPLES - 1)
    issues = check_condition_quality(sparse, fz_nom=150.0, ia_nom=0.0)
    assert len(issues) == 1
    assert issues[0].severity == "error"
    assert "Fz=150" in issues[0].message


def test_condition_with_narrow_sweep_is_a_warning_not_an_error():
    n = 300
    sa = np.linspace(-2, 2, n)  # well under MIN_SA_SWEEP_RANGE_DEG
    narrow = pd.DataFrame({"SA": sa, "FY": np.zeros(n)})
    issues = check_condition_quality(narrow, fz_nom=100.0, ia_nom=0.0)
    assert len(issues) == 1
    assert issues[0].severity == "warning"
    assert "Fz=100" in issues[0].message


def test_sweep_right_at_the_threshold_is_fine():
    n = 300
    sa = np.linspace(-MIN_SA_SWEEP_RANGE_DEG / 2, MIN_SA_SWEEP_RANGE_DEG / 2, n)
    exact = pd.DataFrame({"SA": sa, "FY": np.zeros(n)})
    issues = check_condition_quality(exact, fz_nom=100.0, ia_nom=0.0)
    assert issues == []


def test_too_few_samples_short_circuits_the_sweep_check():
    # A too-sparse segment might also have a technically-narrow sweep --
    # only the (more actionable) sample-count error should be reported,
    # not both.
    n = MIN_CONDITION_SAMPLES - 1
    sa = np.linspace(-1, 1, n)
    sparse_and_narrow = pd.DataFrame({"SA": sa, "FY": np.zeros(n)})
    issues = check_condition_quality(sparse_and_narrow, fz_nom=100.0, ia_nom=2.0)
    assert len(issues) == 1
    assert issues[0].severity == "error"
