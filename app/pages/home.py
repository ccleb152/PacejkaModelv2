"""Home page -- Provides directions and clickable links to other pages in
the app.

Shows a one-time welcome dialog (`st.dialog`) explaining what this tool is
for and how to leave feedback, aimed at first-time users during the
initial feedback-focused rollout. It pops up automatically only the first
time the app is opened in a given browser session (tracked via
`st.session_state`, which persists across page navigation for that
session but resets on a fresh app launch) and can be reopened any time
from the "How to use this app" button below. Dismissing it any way --
the "Got it" button, the dialog's own X, or Esc -- marks it seen, so it
doesn't keep reappearing on every visit to this page.
"""

from __future__ import annotations

import streamlit as st


def _mark_welcome_dialog_seen() -> None:
    st.session_state["welcome_dialog_seen"] = True


@st.dialog(
    "Welcome to Alabama FSAE's Tire Model",
    width="large",
    on_dismiss=_mark_welcome_dialog_seen,
)
def _welcome_dialog() -> None:
    st.markdown(
        """
<div style="font-size: 1.15rem; line-height: 1.6;">

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

</div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Got it, let's go", type="primary"):
        _mark_welcome_dialog_seen()
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