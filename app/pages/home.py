"""Home page -- Provides directions and clickable links to other pages in
the app.

Shows a one-time welcome dialog (`st.dialog`) explaining what this tool is
for and how to leave feedback, aimed at first-time users during the
initial feedback-focused rollout. It pops up automatically the first time
a user reaches this page in a given browser session (tracked via
`st.session_state`, so it won't re-appear on every page navigation within
the same session) and can be reopened any time from the "How to use this
app" button below.
"""

from __future__ import annotations

import streamlit as st


@st.dialog("Welcome to Alabama FSAE's Tire Model", width="large")
def _welcome_dialog() -> None:
    st.markdown(
        """
This app is a Python replacement for the team's MATLAB Pacejka tire-fitting
toolchain - it takes raw Calspan TTC tire test data, fits Magic Formula
tire model coefficients (lateral force and aligning moment for now), and
lets you export those coefficients and plots for lap sim or reports.

**We're sharing it early to collect feedback** before it becomes the
team's default tool, so please try it out and tell us what's confusing,
broken, or missing - there's a Feedback box at the bottom of the Tire
Fitting page for exactly that.

**How to use it:**
1. **Tire Fitting** page -- load a round of test data, either from the
   built-in tire database (pick compound, diameter, and width) or by
   uploading your own raw `.mat` file.
2. Review the load/camber conditions found in that data and run a fit.
3. Check the **Fit Diagnostics** page for goodness-of-fit (R², RMSE, etc.)
   on the fit you just ran.
4. Back on the Tire Fitting page, export the coefficients (CSV) and plots
   to a folder of your choice.
5. **Leave feedback** at the bottom of the Tire Fitting page any time --
   even if you didn't get through a full fit. Anything helps: confusing
   labels, missing features, or just "this crashed."
        """
    )
    if st.button("Got it, let's go", type="primary"):
        st.session_state["welcome_dialog_seen"] = True
        st.rerun()


if "welcome_dialog_seen" not in st.session_state:
    st.session_state["welcome_dialog_seen"] = False

st.title("Home Page")
st.caption(
    "Home page description"
)

if st.button("How to use this app"):
    st.session_state["welcome_dialog_seen"] = False

if not st.session_state["welcome_dialog_seen"]:
    _welcome_dialog()

with st.container(border=True, width="stretch"):
    st.page_link("pages/tire_fitting.py", label="Tire Fitting", icon="")
    st.page_link("pages/fit_diagnostics.py", label="Fit Diagnostics", icon="")