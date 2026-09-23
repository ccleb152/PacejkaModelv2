"""Home page -- Provides directions and clickable links to other pages in
the app.
"""

from __future__ import annotations

import streamlit as st


st.title("Home")
st.caption(
    "Goodness-of-fit for every condition in the current fit -- how closely each "
    "Pacejka curve matches the smoothed data it was fit to. Run a fit on the main "
    "page first; this page just reads that result."
)

st.page_link("pages/tire_fitting.py", label="Tire Fitting", icon="")
# st.page_link("fit_diagnostics.py", *, label="Fit Diagnostics", icon="")