"""Edge cases for pacejka.ranges.para_range that MATLAB doesn't handle
cleanly -- see CLAUDE.md "Known MATLAB quirks" #4 and the NOTE in
pacejka/ranges.py.
"""

import math

import pytest

from pacejka.ranges import para_range


def test_unmapped_fz_nom_raises():
    with pytest.raises(ValueError, match="FZ_Nom"):
        para_range(fz_nom=999, p_nom=12, ia_nom=0, sa_nom=0, v_nom=25, test_type="Cornering")


def test_unmapped_p_nom_raises():
    with pytest.raises(ValueError, match="P_Nom"):
        para_range(fz_nom=150, p_nom=13, ia_nom=0, sa_nom=0, v_nom=25, test_type="Cornering")


def test_unmapped_sa_nom_raises_for_braking():
    with pytest.raises(ValueError, match="SA_Nom"):
        para_range(fz_nom=150, p_nom=12, ia_nom=0, sa_nom=-1, v_nom=25, test_type="Braking")


def test_unmapped_fz_nom_raises_for_braking_even_though_matlab_leaves_it_undefined():
    # MATLAB's Braking branch has no isnan(FZ_Nom) case at all, so an
    # unmapped value (NaN included) would silently carry over a stale
    # FZ_High/FZ_Low from a previous loop iteration instead of erroring.
    # The port raises instead -- see CLAUDE.md quirk #4.
    with pytest.raises(ValueError, match="FZ_Nom"):
        para_range(fz_nom=999, p_nom=12, ia_nom=0, sa_nom=0, v_nom=25, test_type="Braking")


def test_unknown_test_type_raises():
    with pytest.raises(ValueError, match="test_type"):
        para_range(fz_nom=150, p_nom=12, ia_nom=0, sa_nom=0, v_nom=25, test_type="Skidpad")


def test_test_type_matching_is_case_insensitive():
    a = para_range(fz_nom=150, p_nom=12, ia_nom=0, sa_nom=0, v_nom=25, test_type="CORNERING")
    b = para_range(fz_nom=150, p_nom=12, ia_nom=0, sa_nom=0, v_nom=25, test_type="cornering")
    assert a == b


def test_nan_ia_nom_produces_nan_not_inf_matching_matlab_isreal_bug():
    # isreal(NaN) is True in MATLAB, so ParaRange.m's `isreal(IA_Nom)`
    # guard never falls through to its (intended) isnan/inf branch --
    # a NaN IA_Nom actually comes back as NaN, not +/-inf. Preserved here
    # for golden-test fidelity; callers that want +/-inf on NaN (like
    # Data_Finder_v3.m) must override it themselves.
    result = para_range(
        fz_nom=150, p_nom=12, ia_nom=math.nan, sa_nom=0, v_nom=25, test_type="Cornering"
    )
    assert math.isnan(result.ia_high)
    assert math.isnan(result.ia_low)
