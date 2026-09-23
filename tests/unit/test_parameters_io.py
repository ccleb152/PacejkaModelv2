"""Tests for pacejka.io.parameters -- the single consistent parameter-file
schema replacing MATLAB's four inconsistent naming conventions (CLAUDE.md
quirk #3). Not a MATLAB port, so plain round-trip unit tests."""

import json

import numpy as np
import pandas as pd
import pytest

from pacejka.fitters.fy import LBF_TO_N
from pacejka.fitters.mz import FTLB_TO_NM, DEFAULT_RO_M, _cos_alpha_p
from pacejka.io.parameters import (
    cornering_fit_to_dataframe,
    cornering_fit_to_dict,
    load_cornering_fit_file,
    load_fy_coefficients,
    load_mz_coefficients,
    save_cornering_fit,
)
from pacejka.model import FyCoefficients, MzCoefficients, fy_terms, mz_pure
from pacejka.pipeline import run_cornering_fit

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


def _condition_rows(rng, fz_nom, ia_nom, n=300):
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
            "FY": terms.fyo / LBF_TO_N + rng.normal(scale=1.0, size=n),
            "MZ": mz_nm / FTLB_TO_NM + rng.normal(scale=0.3, size=n),
            "RE": np.full(n, 9.0),
            "RL": np.full(n, 8.8),
            "N": np.full(n, 300.0),
            "TSTC": np.full(n, 100.0),
            "TSTI": np.full(n, 110.0),
            "TSTO": np.full(n, 120.0),
        }
    )


@pytest.fixture
def fit_result():
    rng = np.random.RandomState(0)
    blocks = [_condition_rows(rng, fz, 0.0) for fz in (50.0, 100.0, 150.0, 200.0, 250.0)]
    blocks += [_condition_rows(rng, REFERENCE_FZ_NOM, ia) for ia in (2.0, 4.0)]
    samples = pd.concat(blocks, ignore_index=True)
    return run_cornering_fit(samples, p_nom=12.0, v_nom=25.0)


def test_round_trips_through_a_file(fit_result, tmp_path):
    path = tmp_path / "fit.json"
    save_cornering_fit(fit_result, path, tire="TestTire", round_=9, run=32)

    payload = load_cornering_fit_file(path)
    assert payload["tire"] == "TestTire"
    assert payload["round"] == 9
    assert payload["run"] == 32
    assert payload["reference_fz_nom"] == fit_result.reference_fz_nom
    assert payload["tested_fz_noms"] == [50.0, 100.0, 150.0, 200.0, 250.0]
    assert payload["tested_ia_degs"] == [0.0, 2.0, 4.0]

    fy_back = load_fy_coefficients(payload)
    mz_back = load_mz_coefficients(payload)
    assert fy_back == fit_result.fy.coefficients
    assert mz_back == fit_result.mz.coefficients


def test_payload_is_plain_json_serializable(fit_result):
    payload = cornering_fit_to_dict(fit_result, tire="TestTire", round_=9, run=32)
    # Should not raise -- every value must be a plain JSON-compatible type,
    # not e.g. a numpy float that json can't handle without a custom encoder.
    json.dumps(payload)


def test_load_fy_coefficients_also_accepts_a_bare_coefficients_dict():
    # For a standalone coefficients export, not just the full payload.
    bare = {
        "Cy1": 1.0, "Dy1": 2.0, "Dy2": 0.0, "Dy3": 0.0,
        "Ey1": 0.0, "Ey2": 0.0, "Ey3": 0.0, "Ey4": 0.0, "Ey5": 0.0,
        "Hsy1": 0.0, "Hsy2": 0.0,
        "Ky1": 1.0, "Ky2": 1.0, "Ky3": 0.0, "Ky4": 1.0, "Ky5": 0.0, "Ky6": 0.0, "Ky7": 0.0,
        "py1": 1.0, "py2": 1.0, "py3": 1.0, "py4": 1.0, "py5": 1.0,
        "Vsy1": 0.0, "Vsy2": 0.0, "Vsy3": 0.0, "Vsy4": 0.0,
    }
    coeffs = load_fy_coefficients(bare)
    assert coeffs.Cy1 == 1.0


def test_cornering_fit_to_dataframe_is_tidy_one_row_per_coefficient(fit_result):
    df = cornering_fit_to_dataframe(fit_result, tire="TestTire", round_=9, run=32)
    assert list(df.columns) == ["tire", "round", "run", "reference_fz_nom", "quantity", "coefficient", "value"]
    # 27 Fy fields + 27 Mz fields (see FyCoefficients/MzCoefficients)
    assert len(df) == 27 + 27
    assert set(df["quantity"]) == {"Fy", "Mz"}
    assert (df["tire"] == "TestTire").all()
    assert (df["round"] == 9).all()
    assert (df["run"] == 32).all()

    cy1_row = df[(df["quantity"] == "Fy") & (df["coefficient"] == "Cy1")].iloc[0]
    assert cy1_row["value"] == fit_result.fy.coefficients.Cy1


def test_cornering_fit_to_dataframe_round_trips_through_csv(fit_result, tmp_path):
    df = cornering_fit_to_dataframe(fit_result, tire="TestTire", round_=9, run=32)
    csv_path = tmp_path / "coefficients.csv"
    df.to_csv(csv_path, index=False)

    reloaded = pd.read_csv(csv_path)
    assert len(reloaded) == len(df)
    assert list(reloaded.columns) == list(df.columns)
