"""Entrypoint / page router for the Streamlit app.

Uses Streamlit's explicit `st.navigation`/`st.Page` API rather than the
implicit `pages/` folder auto-discovery this app used at first. Under
auto-discovery, a page's sidebar label and order come from its filename
(a leading `1_`/`2_` prefix controls order; underscores become spaces) --
which is why the main page briefly showed up as "streamlit app" in the
nav (its own filename, verbatim) and the diagnostics page needed a
`1_` prefix just to sort correctly. Declaring pages explicitly here scales
better as more get added: titles, icons, and order all live in one place
in code instead of being reverse-engineered from filenames, and pages can
be reordered without renaming files.

The launcher scripts and this file's own name are unchanged --
`streamlit run app/streamlit_app.py` still works exactly the same;
what changed is that this script is now a small router instead of holding
all the page content directly. The actual pages live under app/pages/ as
plain modules (not the special auto-discovered kind) and are listed below.
"""

from __future__ import annotations

import sys
from pathlib import Path

# `streamlit run app/streamlit_app.py` doesn't add the repo root to
# sys.path the way pytest's root conftest.py does -- do it once here.
# Every page module runs in this same process after st.navigation directs
# to it, so they don't need to repeat this bootstrap themselves.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

st.set_page_config(page_title="Alabama FSAE Tire Model v2", layout="wide")

tire_fitting_page = st.Page(
    "pages/tire_fitting.py",
    title="Tire Fitting",
    default=True,
)
fit_diagnostics_page = st.Page(
    "pages/fit_diagnostics.py",
    title="Fit Diagnostics",
)

navigation = st.navigation([tire_fitting_page, fit_diagnostics_page])
navigation.run()
