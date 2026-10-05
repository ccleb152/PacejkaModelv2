"""Read/write fitted Magic Formula coefficients.

Replaces the four inconsistent MATLAB parameter-file naming schemes (see
CLAUDE.md quirk #3 -- `FY_Parameters_{Tire}_{Round}_{Run}_{Fz}FZ.mat` vs.
`FX_Parameters_{Tire}_{Round}_{Fz}FZ_{Run}.mat` vs.
`MX_Parameters_{Tire}_{Round}_{Run}.mat` vs.
`MZ_Parameters_{Tire}_{Round}_{Run}_{Fz}FZ.mat`) with one consistent JSON
schema. The identifying fields (tire/round/run/reference load) live
*inside* the file as data, not encoded into the filename -- callers are
free to name the file however they like (the Streamlit app suggests a
sensible default).
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pandas as pd

from pacejka.longitudinal_pipeline import LongitudinalFitResult
from pacejka.model import FxCoefficients, FyCoefficients, MzCoefficients
from pacejka.pipeline import CorneringFitResult

_SCHEMA_VERSION = 1


def cornering_fit_to_dict(
    result: CorneringFitResult, tire: str, round_: int, run: int
) -> dict:
    """Build the JSON-serializable payload for one cornering fit."""
    return {
        "schema_version": _SCHEMA_VERSION,
        "tire": tire,
        "round": round_,
        "run": run,
        "reference_fz_nom": result.reference_fz_nom,
        "tested_fz_noms": [c.fz_nom for c in result.load_conditions],
        "tested_ia_degs": [c.ia_nom for c in result.camber_conditions],
        "fy_coefficients": dataclasses.asdict(result.fy.coefficients),
        "mz_coefficients": dataclasses.asdict(result.mz.coefficients),
    }


def save_cornering_fit(result: CorneringFitResult, path, tire: str, round_: int, run: int) -> None:
    """Write one cornering fit's coefficients to `path` as JSON."""
    payload = cornering_fit_to_dict(result, tire, round_, run)
    Path(path).write_text(json.dumps(payload, indent=2))


def load_fy_coefficients(payload: dict) -> FyCoefficients:
    """Reconstruct FyCoefficients from a payload's `fy_coefficients` block
    (or an equivalent standalone dict with the same field names)."""
    fields = payload.get("fy_coefficients", payload)
    return FyCoefficients(**fields)


def load_mz_coefficients(payload: dict) -> MzCoefficients:
    """Reconstruct MzCoefficients from a payload's `mz_coefficients` block
    (or an equivalent standalone dict with the same field names)."""
    fields = payload.get("mz_coefficients", payload)
    return MzCoefficients(**fields)


def load_cornering_fit_file(path) -> dict:
    """Read back a JSON file written by `save_cornering_fit`."""
    return json.loads(Path(path).read_text())


def cornering_fit_to_dataframe(result: CorneringFitResult, tire: str, round_: int, run: int) -> pd.DataFrame:
    """One tidy (long-format) row per fitted coefficient -- the app's CSV
    export. Easier to load straight into Excel/pandas/a lapsim's own
    tooling than the nested JSON schema above, which stays as the
    round-trip format `load_fy_coefficients`/`load_mz_coefficients` read
    back (this function doesn't replace that; it's a second, flatter view
    of the same fit for a different consumer)."""
    rows = []
    for quantity, coefficients in (("Fy", result.fy.coefficients), ("Mz", result.mz.coefficients)):
        for name, value in dataclasses.asdict(coefficients).items():
            rows.append(
                {
                    "tire": tire,
                    "round": round_,
                    "run": run,
                    "reference_fz_nom": result.reference_fz_nom,
                    "quantity": quantity,
                    "coefficient": name,
                    "value": value,
                }
            )
    return pd.DataFrame(rows)


def longitudinal_fit_to_dict(
    result: LongitudinalFitResult, tire: str, round_: int, run: int
) -> dict:
    """Build the JSON-serializable payload for one pure-slip Fx fit --
    mirrors `cornering_fit_to_dict`'s shape for the Braking pipeline."""
    return {
        "schema_version": _SCHEMA_VERSION,
        "tire": tire,
        "round": round_,
        "run": run,
        "reference_fz_nom": result.reference_fz_nom,
        "tested_fz_noms": [c.fz_nom for c in result.load_conditions],
        "tested_ia_degs": [c.ia_nom for c in result.camber_conditions],
        "fx_coefficients": dataclasses.asdict(result.fx.coefficients),
    }


def save_longitudinal_fit(result: LongitudinalFitResult, path, tire: str, round_: int, run: int) -> None:
    """Write one pure-slip Fx fit's coefficients to `path` as JSON."""
    payload = longitudinal_fit_to_dict(result, tire, round_, run)
    Path(path).write_text(json.dumps(payload, indent=2))


def load_fx_coefficients(payload: dict) -> FxCoefficients:
    """Reconstruct FxCoefficients from a payload's `fx_coefficients` block
    (or an equivalent standalone dict with the same field names)."""
    fields = payload.get("fx_coefficients", payload)
    return FxCoefficients(**fields)


def load_longitudinal_fit_file(path) -> dict:
    """Read back a JSON file written by `save_longitudinal_fit`."""
    return json.loads(Path(path).read_text())


def longitudinal_fit_to_dataframe(result: LongitudinalFitResult, tire: str, round_: int, run: int) -> pd.DataFrame:
    """One tidy (long-format) row per fitted Fx coefficient -- the app's
    CSV export for the Braking pipeline, mirroring
    `cornering_fit_to_dataframe`."""
    rows = []
    for name, value in dataclasses.asdict(result.fx.coefficients).items():
        rows.append(
            {
                "tire": tire,
                "round": round_,
                "run": run,
                "reference_fz_nom": result.reference_fz_nom,
                "quantity": "Fx",
                "coefficient": name,
                "value": value,
            }
        )
    return pd.DataFrame(rows)
