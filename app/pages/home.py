"""Home page -- Provides directions and clickable links to other pages in
the app.
"""

from __future__ import annotations

import streamlit as st


st.title("Home Page")
st.caption(
    "Home page description"
)

with st.container(border=True, width="stretch)


st.page_link("pages/tire_fitting.py", label="Tire Fitting", icon="")
st.page_link("pages/fit_diagnostics.py", label="Fit Diagnostics", icon="")