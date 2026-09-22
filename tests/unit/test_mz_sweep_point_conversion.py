"""Unit conversion checks for
pacejka.fitters.mz.sweep_point_from_aligning_moment.

Pure/deterministic (no fitting involved), so exact-value comparison per
MIGRATION_PLAN.md Sec.5.
"""

import numpy as np
import pytest

from pacejka.fitters.mz import (
    AligningMomentSpline,
    FTLB_TO_NM,
    LBF_TO_N,
    sweep_point_from_aligning_moment,
)


def test_converts_ftlb_to_nm_lbf_to_n_and_degrees_to_radians():
    splines = AligningMomentSpline(
        sa_grid_deg=np.array([-10.0, 0.0, 10.0]),
        mz=np.array([-5.0, 0.0, 5.0]),
    )

    point = sweep_point_from_aligning_moment(splines, fz_lbf=150.0, ia_deg=2.0)

    assert point.fz_n == pytest.approx(150.0 * LBF_TO_N)
    assert point.gamma_star == pytest.approx(np.sin(np.radians(2.0)))
    assert point.alpha_rad == pytest.approx(np.radians([-10.0, 0.0, 10.0]))
    assert point.mz_nm == pytest.approx([-5.0 * FTLB_TO_NM, 0.0, 5.0 * FTLB_TO_NM])


def test_cos_alpha_p_is_close_to_but_not_exactly_cosine():
    splines = AligningMomentSpline(sa_grid_deg=np.array([0.0, 5.0]), mz=np.zeros(2))
    point = sweep_point_from_aligning_moment(splines, fz_lbf=150.0, ia_deg=0.0)

    expected_cos = np.cos(point.alpha_rad)
    assert point.cos_alpha_p == pytest.approx(expected_cos, abs=0.02)
    assert not np.array_equal(point.cos_alpha_p, expected_cos)
