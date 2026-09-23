"""Fit diagnostics -- a separate page (Streamlit's native multipage
support: any .py file under app/pages/ becomes its own page, with an
auto-generated sidebar switcher) so the main page stays uncluttered for
casual viewers while the full goodness-of-fit breakdown is one click away
for anyone who wants it.

Reads the same `st.session_state["fit_result"]` the main page
(app/streamlit_app.py) already writes -- session state is shared across
pages in a Streamlit multipage app, so no extra plumbing is needed to get
the fit here.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Same bootstrap as app/streamlit_app.py -- pages run as their own script
# too, so `pacejka` needs to be importable regardless of the invoking cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from pacejka.regression import fit_quality_table


def _r_squared_color(value: float) -> str:
    """Background color for one R^2 cell: red (0.0) -> green (1.0),
    clamped. Hand-rolled rather than pandas Styler's background_gradient
    specifically to avoid pulling in matplotlib as a dependency just for
    a color scale."""
    v = max(0.0, min(1.0, value))
    red = int(220 - v * 140)
    green = int(80 + v * 140)
    return f"background-color: rgb({red}, {green}, 90)"


st.set_page_config(page_title="Fit Diagnostics", layout="wide")
st.title("Fit Diagnostics")
st.caption(
    "Goodness-of-fit for every condition in the current fit -- how closely each "
    "Pacejka curve matches the smoothed data it was fit to. Run a fit on the main "
    "page first; this page just reads that result."
)

if "fit_result" not in st.session_state:
    st.info("No fit yet -- go to the main page, load a round, and run a fit first.")
    st.stop()

result = st.session_state["fit_result"]
st.caption(
    f"Reference load Fz0' = {result.reference_fz_nom} lbf | "
    f"tested loads: {[c.fz_nom for c in result.load_conditions]} | "
    f"tested cambers: {[c.ia_nom for c in result.camber_conditions]} deg"
)

table = fit_quality_table(result)

st.subheader("Goodness of fit by condition")
st.caption(
    "R² = 1.0 is a perfect match to the smoothed curve; 0.0 is no better than a "
    "flat line at that curve's own mean; negative is worse than that. RMSE/MAE/max "
    "error are in the quantity's native unit (lbf for Fy, ft-lb for Mz). Rows are "
    "sorted worst-first so the conditions most worth a second look show up top."
)

table = table.sort_values("r_squared", ascending=True).reset_index(drop=True)
styled = table.style.map(_r_squared_color, subset=["r_squared"]).format(
    {
        "r_squared": "{:.4f}",
        "rmse": "{:.2f}",
        "mae": "{:.2f}",
        "max_abs_error": "{:.2f}",
    }
)
st.dataframe(styled, use_container_width=True)

low_quality = table[table["r_squared"] < 0.85]
if not low_quality.empty:
    st.warning(
        f"{len(low_quality)} of {len(table)} conditions have R² below 0.85 -- "
        f"worth a closer look before trusting this fit for those loads/cambers: "
        + ", ".join(f"{row.quantity} {row.condition}" for row in low_quality.itertuples())
    )
