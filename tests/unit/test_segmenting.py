"""Tests for pacejka.segmenting.segment_condition.

Not a golden test against captured MATLAB output -- Data_Finder_v3.m
produces files, not a return value, and we don't have MATLAB available in
this environment to run it. Instead: synthetic, fully fabricated rows
(no real TTC telemetry, per the "no data committed to the repo" rule --
see CLAUDE.md) crafted to sit on both sides of every mask boundary, with
expected outputs computed independently (by hand, with math.*, not by
importing pacejka.segmenting's own constants) so the test can't just be
checking the implementation against itself.

The mask logic and derived-channel formulas were spot-checked separately
against a real Round-9 Hoosier 16x7.5-10 cornering file the user provided
(not committed here) -- see the session notes. A true MATLAB-vs-Python
golden comparison for this function is still open; it needs someone to run
Data_Finder_v3.m in MATLAB on a real round and share the segmented output.
"""

import math

import pandas as pd
import pytest

from pacejka.segmenting import segment_condition

# Bounds for FZ_Nom=150, P_Nom=12, IA_Nom=0, V_Nom=25, Cornering (computed
# from pacejka.ranges.para_range, transcribed from ParaRange.m's constants):
# FZ in [136, 170], P in [11.51, 12.99], IA in [-0.075, 0.075] (all
# inclusive), SA in (-15, 15), V in (22.5, 27.5) (both exclusive).

_COMMON = dict(FX=10, FY=-200, RE=9.0, RL=8.8, N=300, TSTC=100, TSTI=110, TSTO=120)


def _row(**overrides):
    row = dict(FZ=-150, P=12.0, IA=0.0, SA=5.0, V=25.0, **_COMMON)
    row.update(overrides)
    return row


@pytest.fixture
def samples():
    rows = {
        "A_included": _row(),
        "B_fz_out_of_band": _row(FZ=-100),
        "C_p_below_band": _row(P=11.0),
        "D_ia_above_band": _row(IA=0.2),
        "E_sa_at_high_boundary_excluded": _row(SA=15.0),
        "F_sa_at_low_boundary_excluded": _row(SA=-15.0),
        "G_v_at_high_boundary_excluded": _row(V=27.5),
        "H_fz_at_low_boundary_included": _row(FZ=-136),
        "I_fz_at_high_boundary_included": _row(FZ=-170),
        "J_fz_just_above_high_boundary_excluded": _row(FZ=-171),
    }
    return pd.DataFrame(rows.values(), index=rows.keys())


def test_mask_boundaries(samples):
    result = segment_condition(
        samples, fz_nom=150, p_nom=12, ia_nom=0, sa_nom=0, v_nom=25, test_type="Cornering"
    )
    # Row order is preserved (no sorting), so recover which original rows
    # survived by their fabricated FX/FY combination not being ambiguous --
    # simplest is to just check the count and spot-check via the known
    # unique FZ per surviving row.
    assert sorted(result["FZ"]) == sorted([-150, -136, -170])


@pytest.mark.parametrize(
    "fz,expected",
    [
        (-150, (110.0, -0.06666666666666667, 1.3333333333333333, 9.292036732051033, 8.935037566870378)),
        (-136, (110.0, -0.07352941176470588, 1.4705882352941178, 9.292036732051033, 8.935037566870378)),
        (-170, (110.0, -0.058823529411764705, 1.1764705882352942, 9.292036732051033, 8.935037566870378)),
    ],
)
def test_derived_channels_match_independent_hand_computation(samples, fz, expected):
    result = segment_condition(
        samples, fz_nom=150, p_nom=12, ia_nom=0, sa_nom=0, v_nom=25, test_type="Cornering"
    )
    row = result.loc[result["FZ"] == fz].iloc[0]
    t_avg, nfx, nfy, vc, vs = expected
    assert row["T_Avg"] == pytest.approx(t_avg)
    assert row["NFX"] == pytest.approx(nfx)
    assert row["NFY"] == pytest.approx(nfy)
    assert row["Vc"] == pytest.approx(vc)
    assert row["Vs"] == pytest.approx(vs)


def test_nan_ia_nom_accepts_any_inclination_angle(samples):
    # ia_nom=NaN is meant to mean "don't filter on IA at all" (matching
    # FZ_Nom's existing NaN-means-unbounded behavior in para_range) -- see
    # the fixed whole-vector isnan bug documented in segment_condition's
    # docstring and CLAUDE.md quirk #6.
    wide_ia_row = pd.DataFrame([_row(FZ=-150, IA=3.9)], index=["wide_ia"])
    combined = pd.concat([samples, wide_ia_row])

    result = segment_condition(
        combined, fz_nom=150, p_nom=12, ia_nom=math.nan, sa_nom=0, v_nom=25, test_type="Cornering"
    )
    assert 3.9 in result["IA"].values


def test_empty_result_when_nothing_matches(samples):
    result = segment_condition(
        samples, fz_nom=50, p_nom=12, ia_nom=0, sa_nom=0, v_nom=25, test_type="Cornering"
    )
    assert result.empty
