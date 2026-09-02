"""Golden tests for pacejka.model.fy_pure.

fy_pure is a pure, deterministic function of fixed coefficients and state
(no optimizer involved), so per MIGRATION_PLAN.md Sec.5's "deterministic
functions" tolerance regime it gets exact-value comparison. There's no
live MATLAB to run for this one (it's not itself a MATLAB function --
it's the equation extracted from three duplicated call sites), so the
expected values are hand-derived: computed with an independent,
freshly-written transcription of the same equation (see the session's
derivation), not by importing pacejka.model itself, and cross-checked
algebraically against Pacejka_Term_Finder_FY_V3.m's own Base/dFz staged
closures at their special cases (gamma_star=0, fz==fz0_prime or not).
"""

import math

import pytest

from pacejka.model import FyCoefficients, fy_pure

COEFFS = FyCoefficients(
    Cy1=1.6, Dy1=2.7, Dy2=-0.2, Dy3=0.05,
    Ey1=0.9, Ey2=-0.1, Ey3=0.02, Ey4=0.01, Ey5=0.03,
    Hsy1=0.01, Hsy2=0.005,
    Ky1=170.0, Ky2=1.5, Ky3=0.02, Ky4=1.9, Ky5=0.1, Ky6=2.0, Ky7=0.3,
    py1=1, py2=1, py3=1, py4=1, py5=1,
    Vsy1=0.02, Vsy2=0.01, Vsy3=0.5, Vsy4=0.1,
)

FZ0_PRIME = 150 * 4.448


@pytest.mark.parametrize(
    "fz,gamma_star,alpha_star,expected_fyo,expected_mu_y",
    [
        # Nominal load, zero camber, positive slip angle.
        (FZ0_PRIME, 0.0, 0.05, 1797.4905056271832, 2.7),
        # Different load (exercises dFz), nonzero camber (exercises dIA),
        # negative slip angle.
        (100 * 4.448, math.sin(2 * math.pi / 180), -0.1, -1215.1022276075275, 2.766498180142971),
        # Nominal load, zero camber, negative slip angle (exercises sign()).
        (FZ0_PRIME, 0.0, -0.08, -1777.0054242270303, 2.7),
    ],
)
def test_fy_pure_matches_hand_derived_reference(
    fz, gamma_star, alpha_star, expected_fyo, expected_mu_y
):
    fyo, mu_y = fy_pure(fz, FZ0_PRIME, gamma_star, alpha_star, COEFFS)
    assert fyo == pytest.approx(expected_fyo, rel=1e-9)
    assert mu_y == pytest.approx(expected_mu_y, rel=1e-9)


def test_fy_pure_at_nominal_load_and_zero_camber_matches_base_stage_form():
    # At fz == fz0_prime (dfz=0) and gamma_star=0, fy_pure collapses to
    # exactly Pacejka_Term_Finder_FY_V3.m's "Base" stage equation, with
    # its free parameters Xb(1..9) mapping onto Cy1, mu_y(=Dy1), Ey1, Ey3,
    # Hsy1, Ky1, Ky2, Ky4, Vsy1 respectively -- transcribed independently
    # here (not calling fy_pure) as the cross-check.
    Cy1, Dy1, Ey1, Ey3, Hsy1, Ky1, Ky2, Ky4, Vsy1 = (
        COEFFS.Cy1, COEFFS.Dy1, COEFFS.Ey1, COEFFS.Ey3, COEFFS.Hsy1,
        COEFFS.Ky1, COEFFS.Ky2, COEFFS.Ky4, COEFFS.Vsy1,
    )
    alpha_star = 0.06
    fz = FZ0_PRIME

    s_hy = Hsy1
    alpha_y = alpha_star + s_hy
    c_y = Cy1
    d_y = Dy1 * fz
    e_y = Ey1 * (1 - Ey3 * math.copysign(1.0, alpha_star))
    k_y_a = Ky1 * FZ0_PRIME * math.sin(Ky4 * math.atan((fz / FZ0_PRIME) / Ky2))
    b_y = k_y_a / (c_y * d_y + 0.1)
    s_vy = fz * Vsy1
    expected_base_form = (
        d_y * math.sin(c_y * math.atan(b_y * alpha_y - e_y * (b_y * alpha_y - math.atan(b_y * alpha_y))))
        + s_vy
    )

    fyo, _ = fy_pure(fz, FZ0_PRIME, 0.0, alpha_star, COEFFS)
    assert fyo == pytest.approx(expected_base_form, rel=1e-9)
