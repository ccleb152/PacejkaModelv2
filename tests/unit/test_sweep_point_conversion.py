"""Unit conversion checks for pacejka.fitters.fy.sweep_point_from_alpha_sweep.

Pure/deterministic (no fitting involved), so exact-value comparison per
MIGRATION_PLAN.md Sec.5.
"""

import numpy as np
import pytest

from pacejka.fitters.fy import AlphaSweepSplines, sweep_point_from_alpha_sweep


def test_converts_lbf_to_n_and_degrees_to_radians():
    splines = AlphaSweepSplines(
        sa_grid_deg=np.array([-10.0, 0.0, 10.0]),
        fx=np.zeros(3),
        fy=np.array([-100.0, 0.0, 100.0]),
        mz=np.zeros(3),
        vc=np.zeros(3),
    )

    point = sweep_point_from_alpha_sweep(splines, fz_lbf=150.0, ia_deg=2.0)

    assert point.fz_n == pytest.approx(150.0 * 4.448)
    assert point.gamma_star == pytest.approx(np.sin(np.radians(2.0)))
    assert point.alpha_rad == pytest.approx(np.radians([-10.0, 0.0, 10.0]))
    assert point.fy_n == pytest.approx([-100.0 * 4.448, 0.0, 100.0 * 4.448])


def test_zero_camber_gives_zero_gamma_star():
    splines = AlphaSweepSplines(
        sa_grid_deg=np.array([0.0]), fx=np.zeros(1), fy=np.zeros(1), mz=np.zeros(1), vc=np.zeros(1)
    )
    point = sweep_point_from_alpha_sweep(splines, fz_lbf=50.0, ia_deg=0.0)
    assert point.gamma_star == 0.0
