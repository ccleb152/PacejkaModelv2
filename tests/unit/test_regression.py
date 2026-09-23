"""Tests for pacejka.regression. Not a MATLAB port -- the original tool
never checked fit quality at all -- so plain unit tests against a
synthetic, fabricated round (not real telemetry, per CLAUDE.md's
no-data-in-repo rule), matching test_pipeline.py's pattern.
"""

import numpy as np
import pandas as pd
import pytest

from pacejka.fitters.fy import LBF_TO_N
from pacejka.fitters.mz import FTLB_TO_NM, DEFAULT_RO_M, _cos_alpha_p
from pacejka.model import FyCoefficients, MzCoefficients, fy_terms, mz_pure
from pacejka.pipeline import run_cornering_fit
from pacejka.regression import fit_quality_rows, fit_quality_table

FY_COEFFS = FyCoefficients(
    Cy1=1.6, Dy1=2.784, Dy2=-0.15, Dy3=15.0,
    Ey1=0.9, Ey2=-0.3, Ey3=0.05, Ey4=0.5, Ey5=0.5,
    Hsy1=0.0, Hsy2=0.01,
    Ky1=170.0, Ky2=2.0, Ky3=0.5, Ky4=1.0, Ky5=0.5, Ky6=2.0, Ky7=0.0,
    py1=1, py2=1, py3=1, py4=1, py5=1,
    Vsy1=0.03, Vsy2=0.02, Vsy3=1.0, Vsy4=0.0,
)
MZ_COEFFS = MzCoefficients(
    Hz1=0.001, Hz2=0.005, Hz3=0.002, Hz4=0.0,
    Bz1=1.5, Bz2=1.0, Bz3=0.5, Bz4=1.0, Bz5=0.3,
    Bz9=1.0, Bz10=-1.0,
    Cz1=1.2,
    Dz1=1.0, Dz2=0.5, Dz3=0.5, Dz4=0.3,
    Dz6=0.5, Dz7=5.0, Dz8=0.5, Dz9=0.0, Dz10=0.5, Dz11=0.0,
    Ez1=1.0, Ez2=0.5, Ez3=1.0, Ez4=1.0, Ez5=0.5,
)
REFERENCE_FZ_NOM = 150.0
FZ0_PRIME = REFERENCE_FZ_NOM * LBF_TO_N
RO = DEFAULT_RO_M


def _condition_rows(rng, fz_nom, ia_nom, n=300, noise_scale=1.0):
    sa_deg = np.linspace(-12, 12, n)
    alpha_rad = np.radians(sa_deg)
    fz_n = fz_nom * LBF_TO_N
    gamma_star = np.sin(np.radians(ia_nom))

    terms = fy_terms(fz_n, FZ0_PRIME, gamma_star, alpha_rad, FY_COEFFS)
    terms_g0 = fy_terms(fz_n, FZ0_PRIME, 0.0, alpha_rad, FY_COEFFS)
    cos_alpha_p = _cos_alpha_p(alpha_rad)
    mz_nm = mz_pure(
        fz_n, FZ0_PRIME, RO, gamma_star, alpha_rad, cos_alpha_p,
        float(terms.cy), float(terms.by), float(terms.s_hf), terms_g0.fyo, MZ_COEFFS,
    )

    return pd.DataFrame(
        {
            "FZ": -fz_nom + rng.normal(scale=1.0, size=n),
            "P": 12.0 + rng.normal(scale=0.1, size=n),
            "IA": ia_nom + rng.normal(scale=0.02, size=n),
            "SA": sa_deg,
            "V": 25.0 + rng.normal(scale=0.1, size=n),
            "FX": rng.normal(scale=2, size=n),
            "FY": terms.fyo / LBF_TO_N + rng.normal(scale=noise_scale, size=n),
            "MZ": mz_nm / FTLB_TO_NM + rng.normal(scale=noise_scale * 0.3, size=n),
            "RE": np.full(n, 9.0),
            "RL": np.full(n, 8.8),
            "N": np.full(n, 300.0),
            "TSTC": np.full(n, 100.0),
            "TSTI": np.full(n, 110.0),
            "TSTO": np.full(n, 120.0),
        }
    )


@pytest.fixture
def good_fit_result():
    rng = np.random.RandomState(0)
    blocks = [_condition_rows(rng, fz, 0.0) for fz in (50.0, 100.0, 150.0, 200.0, 250.0)]
    blocks += [_condition_rows(rng, REFERENCE_FZ_NOM, ia) for ia in (2.0, 4.0)]
    samples = pd.concat(blocks, ignore_index=True)
    return run_cornering_fit(samples, p_nom=12.0, v_nom=25.0)


def test_returns_one_row_per_condition_per_quantity(good_fit_result):
    rows = fit_quality_rows(good_fit_result)
    # 5 loads + 3 cambers, x2 quantities (Fy, Mz) = 16 rows
    assert len(rows) == 16
    assert {r.quantity for r in rows} == {"Fy", "Mz"}
    assert {r.sweep for r in rows} == {"load", "camber"}


def test_a_good_fit_has_high_r_squared(good_fit_result):
    # The synthetic data is generated from the exact FY_COEFFS/MZ_COEFFS
    # the pipeline then re-fits, with only light noise -- the resulting
    # fit should track the smoothed curve closely.
    rows = fit_quality_rows(good_fit_result)
    for row in rows:
        assert row.r_squared > 0.9, f"{row.quantity} {row.condition}: R^2={row.r_squared}"


def test_condition_labels_match_the_app_plots(good_fit_result):
    rows = fit_quality_rows(good_fit_result)
    load_labels = {r.condition for r in rows if r.sweep == "load"}
    assert load_labels == {"Fz=50 lbf", "Fz=100 lbf", "Fz=150 lbf", "Fz=200 lbf", "Fz=250 lbf"}
    camber_labels = {r.condition for r in rows if r.sweep == "camber"}
    assert camber_labels == {"IA=0 deg", "IA=2 deg", "IA=4 deg"}


def test_fit_quality_table_is_a_dataframe_with_expected_columns(good_fit_result):
    table = fit_quality_table(good_fit_result)
    assert isinstance(table, pd.DataFrame)
    assert list(table.columns) == [
        "quantity", "sweep", "condition", "n_points", "r_squared", "rmse", "mae", "max_abs_error",
    ]
    assert len(table) == 16


def test_a_bad_fit_is_flagged_by_low_r_squared():
    # Deliberately mismatched: fit against data generated from different
    # coefficients than what's actually optimized for, at only one load
    # (so the dFz stage can't correct the mismatch) -- the resulting fit
    # should score poorly, proving the metric actually discriminates.
    rng = np.random.RandomState(1)
    mismatched_coeffs = FyCoefficients(
        Cy1=1.6, Dy1=2.784, Dy2=-0.15, Dy3=15.0,
        Ey1=0.9, Ey2=-0.3, Ey3=0.05, Ey4=0.5, Ey5=0.5,
        Hsy1=0.0, Hsy2=0.01,
        Ky1=5.0, Ky2=2.0, Ky3=0.5, Ky4=1.0, Ky5=0.5, Ky6=2.0, Ky7=0.0,
        py1=1, py2=1, py3=1, py4=1, py5=1,
        Vsy1=0.03, Vsy2=0.02, Vsy3=1.0, Vsy4=0.0,
    )
    n = 600
    sa_deg = np.linspace(-12, 12, n)
    alpha_rad = np.radians(sa_deg)
    fz_n = REFERENCE_FZ_NOM * LBF_TO_N
    terms = fy_terms(fz_n, FZ0_PRIME, 0.0, alpha_rad, mismatched_coeffs)

    blocks = [
        pd.DataFrame(
            {
                "FZ": -REFERENCE_FZ_NOM + rng.normal(scale=1.0, size=n),
                "P": 12.0 + rng.normal(scale=0.1, size=n),
                "IA": rng.normal(scale=0.02, size=n),
                "SA": sa_deg,
                "V": 25.0 + rng.normal(scale=0.1, size=n),
                "FX": rng.normal(scale=2, size=n),
                # Sharp triangle-wave-ish noise the smooth Pacejka fit
                # can't reproduce, unlike the light Gaussian noise used
                # elsewhere -- guarantees a visibly bad R^2.
                "FY": terms.fyo / LBF_TO_N + 200 * np.sign(np.sin(sa_deg * 5)),
                "MZ": rng.normal(scale=2, size=n),
                "RE": np.full(n, 9.0),
                "RL": np.full(n, 8.8),
                "N": np.full(n, 300.0),
                "TSTC": np.full(n, 100.0),
                "TSTI": np.full(n, 110.0),
                "TSTO": np.full(n, 120.0),
            }
        )
    ]
    samples = pd.concat(blocks, ignore_index=True)
    result = run_cornering_fit(
        samples, p_nom=12.0, v_nom=25.0, fz_noms=[REFERENCE_FZ_NOM], ia_degs=[0.0]
    )
    rows = fit_quality_rows(result)
    fy_row = next(r for r in rows if r.quantity == "Fy")
    assert fy_row.r_squared < 0.5
