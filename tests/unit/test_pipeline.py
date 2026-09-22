"""Integration tests for pacejka.pipeline.run_cornering_fit.

Verifies the wiring end-to-end (raw round -> auto-detected conditions ->
segmented -> smoothed -> fit) on a synthetic, fabricated round generated
from known Magic Formula coefficients (not real telemetry, per CLAUDE.md's
no-data-in-repo rule). Fit-quality itself is already covered at the unit
level in test_fy_term_finder.py/test_mz_term_finder.py; this checks the
pipeline assembles conditions/results correctly, not fit precision.
"""

import numpy as np
import pandas as pd
import pytest

from pacejka.fitters.fy import LBF_TO_N
from pacejka.fitters.mz import FTLB_TO_NM, DEFAULT_RO_M, _cos_alpha_p
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

    fy_lbf = terms.fyo / LBF_TO_N + rng.normal(scale=1.0, size=n)
    mz_ftlb = mz_nm / FTLB_TO_NM + rng.normal(scale=0.3, size=n)

    return pd.DataFrame(
        {
            "FZ": -fz_nom + rng.normal(scale=1.0, size=n),
            "P": 12.0 + rng.normal(scale=0.1, size=n),
            "IA": ia_nom + rng.normal(scale=0.02, size=n),
            "SA": sa_deg,
            "V": 25.0 + rng.normal(scale=0.1, size=n),
            "FX": rng.normal(scale=2, size=n),
            "FY": fy_lbf,
            "MZ": mz_ftlb,
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
    blocks = [_condition_rows(rng, fz, 0.0) for fz in (50.0, 100.0, 150.0, 200.0, 250.0)]
    blocks += [_condition_rows(rng, REFERENCE_FZ_NOM, ia) for ia in (2.0, 4.0)]
    return pd.concat(blocks, ignore_index=True)


def test_auto_detects_conditions_and_picks_the_middle_load_as_reference(synthetic_round):
    result = run_cornering_fit(synthetic_round, p_nom=12.0, v_nom=25.0)

    assert result.reference_fz_nom == REFERENCE_FZ_NOM
    assert [c.fz_nom for c in result.load_conditions] == [50.0, 100.0, 150.0, 200.0, 250.0]
    assert [c.ia_nom for c in result.camber_conditions] == [0.0, 2.0, 4.0]


def test_fitted_coefficients_are_physically_sane(synthetic_round):
    # Regression check for CLAUDE.md quirk #9 (Ky1's sign bug) surviving
    # the full pipeline, not just the isolated term-finder unit tests.
    result = run_cornering_fit(synthetic_round, p_nom=12.0, v_nom=25.0)
    assert result.fy.coefficients.Ky1 > 0
    assert result.fy.coefficients.Ky7 == 0.0
    assert result.mz.coefficients.Hz4 == 0.0


def test_explicit_fz_noms_and_ia_degs_override_detection(synthetic_round):
    result = run_cornering_fit(
        synthetic_round, p_nom=12.0, v_nom=25.0, fz_noms=[100.0, 150.0, 200.0], ia_degs=[0.0, 2.0]
    )
    assert [c.fz_nom for c in result.load_conditions] == [100.0, 150.0, 200.0]
    assert [c.ia_nom for c in result.camber_conditions] == [0.0, 2.0]


def test_reference_fz_nom_must_be_among_the_tested_loads(synthetic_round):
    with pytest.raises(ValueError, match="reference_fz_nom"):
        run_cornering_fit(synthetic_round, p_nom=12.0, v_nom=25.0, reference_fz_nom=999.0)


def test_zero_camber_must_be_present(synthetic_round):
    with pytest.raises(ValueError, match="[Zz]ero camber"):
        run_cornering_fit(synthetic_round, p_nom=12.0, v_nom=25.0, ia_degs=[2.0, 4.0])


def test_explicitly_requesting_an_untested_condition_raises_a_clear_error(synthetic_round):
    # Requesting a load with essentially no real data (rather than one
    # that's simply undetected) used to reach the spline fitter with a
    # near-empty segment and fail with a confusing error deep inside
    # csaps; pacejka.quality.check_condition_quality now catches this at
    # the pipeline level with a clear, actionable message instead.
    with pytest.raises(ValueError, match="Fz=350.*too few"):
        run_cornering_fit(synthetic_round, p_nom=12.0, v_nom=25.0, fz_noms=[100.0, 150.0, 350.0])


def test_a_condition_with_a_truncated_sweep_surfaces_a_warning_not_a_crash():
    # A condition with enough samples to be usable but a slip-angle sweep
    # that never completes (e.g. the test was cut short) should still fit
    # -- just with a warning attached to that condition's result, per
    # pacejka.quality.check_condition_quality. Built from scratch (rather
    # than reusing synthetic_round) so the truncated Fz=200 block is the
    # *only* data at that load -- adding it alongside a full-sweep block
    # at the same load would just widen the combined segment back out.
    rng = np.random.RandomState(0)
    blocks = [_condition_rows(rng, fz, 0.0) for fz in (50.0, 100.0, 150.0, 250.0)]
    blocks += [_condition_rows(rng, REFERENCE_FZ_NOM, ia) for ia in (2.0, 4.0)]
    truncated = _condition_rows(rng, fz_nom=200.0, ia_nom=0.0, n=60)
    truncated["SA"] = np.linspace(-3.0, 3.0, len(truncated))
    blocks.append(truncated)
    augmented = pd.concat(blocks, ignore_index=True)

    result = run_cornering_fit(
        augmented, p_nom=12.0, v_nom=25.0, fz_noms=[50.0, 100.0, 150.0, 200.0, 250.0]
    )

    condition = next(c for c in result.load_conditions if c.fz_nom == 200.0)
    assert any(issue.severity == "warning" and "Fz=200" in issue.message for issue in condition.quality_issues)


def test_raises_a_clear_error_when_nothing_is_detected():
    # An empty round now fails the pacejka.quality whole-round gate before
    # detection even runs -- a more specific, more actionable message
    # ("0 samples", "entirely missing") than the old generic "no load
    # levels detected" (which is still what a *non-empty* round with no
    # matching conditions gets -- see the reference_fz_nom/zero-camber
    # tests above, which use a real synthetic round).
    empty = pd.DataFrame(
        columns=["FZ", "P", "IA", "SA", "V", "FX", "FY", "MZ", "RE", "RL", "N", "TSTC", "TSTI", "TSTO"]
    )
    with pytest.raises(ValueError, match="0 samples"):
        run_cornering_fit(empty, p_nom=12.0, v_nom=25.0)
