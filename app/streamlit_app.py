"""Streamlit UI for the cornering (Fy/Mz) fitting pipeline.

Replaces `tiremodelV2.m`'s orchestration role (MIGRATION_PLAN.md step 9,
the last piece of Phase 1): load one raw TTC round, run the multi-load/
multi-camber cornering fit (`pacejka.pipeline.run_cornering_fit`), and
show the resulting overlay plots and fitted coefficients.

Single-page app for v1 -- MIGRATION_PLAN.md originally sketched a
multi-page layout (separate "load data"/"fit"/"results" pages); this
collapses that into one page with clear sections to get something working
end-to-end first. Splitting into pages later is a pure refactor, not a
behavior change.
"""

from __future__ import annotations

import dataclasses
import io
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

# `streamlit run app/streamlit_app.py` doesn't add the repo root to
# sys.path the way pytest's root conftest.py does -- do the same thing
# here so `pacejka` is importable regardless of the invoking cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.graph_objects as go
import streamlit as st

from pacejka.colors import condition_hue, raw_smoothed_fit_colors
from pacejka.config import DataRootNotConfigured, get_data_root, set_data_root
from pacejka.fitters.fy import LBF_TO_N
from pacejka.fitters.mz import FTLB_TO_NM
from pacejka.io.parameters import cornering_fit_to_dict
from pacejka.io.ttc_raw import load_ttc_round
from pacejka.pipeline import run_cornering_fit
from pacejka.quality import check_round_quality


def _show_quality_issues(issues) -> bool:
    """Render a list of pacejka.quality.QualityIssue as error/warning
    boxes. Returns True if any "error"-severity issue was shown -- the
    caller stops the page in that case, since the underlying data can't
    be fit at all."""
    has_error = False
    for issue in issues:
        if issue.severity == "error":
            st.error(issue.message)
            has_error = True
        else:
            st.warning(issue.message)
    return has_error


def _slugify(text: str) -> str:
    """Make `text` safe to use in a filename: collapse whitespace to a
    single underscore, drop anything that isn't alphanumeric/./-/_."""
    text = re.sub(r"\s+", "_", text.strip())
    return re.sub(r"[^A-Za-z0-9._-]", "", text) or "unnamed"


def _ensure_graph_export_engine() -> None:
    """Make sure Plotly's static-image export (Kaleido) has a Chrome
    binary to render with. Kaleido v1+ doesn't bundle one -- it fetches
    its own on first use (cached under Kaleido's own data directory after
    that, so this only costs time/network once per computer, not once per
    session). Done lazily here rather than in the launcher scripts so
    teammates who never export a graph never pay for it."""
    if st.session_state.get("_graph_export_engine_ready"):
        return
    import kaleido

    kaleido.get_chrome_sync()
    st.session_state["_graph_export_engine_ready"] = True


st.set_page_config(page_title="Pacejka Tire Fitting", layout="wide")
st.title("Pacejka Magic Formula Tire Fitting")

# ---------------------------------------------------------------------------
# Sidebar: data-folder configuration
# ---------------------------------------------------------------------------

st.sidebar.header("Tire data folder")
try:
    data_root = get_data_root()
    st.sidebar.success(f"Configured: {data_root}")
    change = st.sidebar.checkbox("Change folder")
except DataRootNotConfigured:
    data_root = None
    st.sidebar.warning("No tire-data folder configured yet.")
    change = True

if change:
    new_root = st.sidebar.text_input("Path to your synced OneDrive/SharePoint tire-data folder")
    if st.sidebar.button("Save folder") and new_root:
        try:
            saved = set_data_root(new_root)
            st.sidebar.success(f"Saved: {saved}")
            st.rerun()
        except FileNotFoundError as exc:
            st.sidebar.error(str(exc))

# ---------------------------------------------------------------------------
# 1. Load raw TTC round data
# ---------------------------------------------------------------------------

st.header("1. Load raw TTC round data")
col_browse, col_upload = st.columns(2)

with col_browse:
    st.subheader("From the configured folder")
    if data_root is not None:
        mat_files = sorted(data_root.rglob("*.mat"))
        if mat_files:
            selected = st.selectbox(
                "Round file",
                mat_files,
                format_func=lambda p: str(p.relative_to(data_root)),
            )
            if st.button("Load selected file"):
                round_data = load_ttc_round(selected)
                st.session_state["round_data"] = round_data
                st.session_state["source_label"] = str(selected.relative_to(data_root))
        else:
            st.info("No .mat files found under the configured folder.")
    else:
        st.info("Configure a tire-data folder in the sidebar to browse files.")

with col_upload:
    st.subheader("Or upload a file")
    uploaded = st.file_uploader("Raw TTC round (.mat)", type="mat")
    if uploaded is not None and st.button("Load uploaded file"):
        with tempfile.NamedTemporaryFile(suffix=".mat", delete=False) as tmp:
            tmp.write(uploaded.getbuffer())
            tmp_path = Path(tmp.name)
        round_data = load_ttc_round(tmp_path)
        st.session_state["round_data"] = round_data
        st.session_state["source_label"] = uploaded.name

if "round_data" not in st.session_state:
    st.info("Load a raw TTC round above to continue.")
    st.stop()

round_data = st.session_state["round_data"]
st.success(
    f"Loaded {st.session_state['source_label']} -- "
    f"source={round_data.source!r}, testid={round_data.testid!r}, "
    f"tireid={round_data.tireid!r}, {len(round_data.samples)} samples"
)

round_level_issues = check_round_quality(round_data.samples)
if round_level_issues:
    st.subheader("Data quality")
    if _show_quality_issues(round_level_issues):
        st.error(
            "This file doesn't have enough usable data to fit -- it looks like an "
            "incomplete or aborted run. Load a different file to continue."
        )
        st.stop()

# ---------------------------------------------------------------------------
# 2. Fit settings
# ---------------------------------------------------------------------------

st.header("2. Fit settings")
col_p, col_v = st.columns(2)
p_nom = col_p.number_input("Nominal pressure (psi)", value=12.0, step=1.0)
v_nom = col_v.number_input("Nominal test speed (mph)", value=25.0, step=1.0)

st.caption(
    "Tested loads and camber angles are auto-detected from the round's FZ/IA "
    "channels by default -- override below only if a level was wrongly "
    "included or excluded."
)
override = st.checkbox("Override auto-detected loads/cambers")
fz_noms = None
ia_degs = None
reference_fz_nom = None
if override:
    fz_text = st.text_input("Load levels (lbf, comma-separated)", value="50, 100, 150, 200, 250")
    ia_text = st.text_input("Camber levels (deg, comma-separated)", value="0, 2, 4")
    fz_noms = [float(x) for x in fz_text.split(",") if x.strip()]
    ia_degs = [float(x) for x in ia_text.split(",") if x.strip()]
    ref_text = st.text_input("Reference load (lbf, blank = middle of the list)", value="")
    reference_fz_nom = float(ref_text) if ref_text.strip() else None

if st.button("Run Fit", type="primary"):
    try:
        result = run_cornering_fit(
            round_data.samples,
            p_nom=p_nom,
            v_nom=v_nom,
            reference_fz_nom=reference_fz_nom,
            fz_noms=fz_noms,
            ia_degs=ia_degs,
        )
        st.session_state["fit_result"] = result
    except ValueError as exc:
        st.error(str(exc))

if "fit_result" not in st.session_state:
    st.stop()

result = st.session_state["fit_result"]

# ---------------------------------------------------------------------------
# 3. Results
# ---------------------------------------------------------------------------

st.header("3. Results")
st.caption(
    f"Reference load Fz0' = {result.reference_fz_nom} lbf | "
    f"tested loads: {[c.fz_nom for c in result.load_conditions]} | "
    f"tested cambers: {[c.ia_nom for c in result.camber_conditions]} deg"
)

condition_warnings = [
    issue
    for condition in (*result.load_conditions, *result.camber_conditions)
    for issue in condition.quality_issues
] + list(result.quality_issues)
if condition_warnings:
    with st.expander(f"Data quality warnings ({len(condition_warnings)})", expanded=True):
        _show_quality_issues(condition_warnings)


def _sweep_overlay_figure(
    conditions, raw_column, spline_attr, smoothed_attr, fit_curves, unit_divisor, label_fn, y_title
) -> go.Figure:
    """One Plotly figure overlaying raw scatter + smoothed spline + Pacejka
    fit curve for each condition in a load or camber sweep.

    Each condition gets one hue (pacejka.colors.condition_hue, assigned in
    a fixed order); its raw/smoothed/fit traces are light/medium/dark
    steps of that *same* hue, so the three traces belonging to one
    condition read as a group at a glance instead of only via the legend
    text -- see pacejka/colors.py.
    """
    fig = go.Figure()
    for index, (condition, fit_curve) in enumerate(zip(conditions, fit_curves)):
        label = label_fn(condition)
        splines = getattr(condition, spline_attr)
        raw_color, smoothed_color, fit_color = raw_smoothed_fit_colors(condition_hue(index))
        fig.add_trace(
            go.Scatter(
                x=condition.samples["SA"],
                y=condition.samples[raw_column],
                mode="markers",
                name=f"{label} raw",
                marker=dict(size=4, opacity=0.5, color=raw_color),
                legendgroup=label,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=splines.sa_grid_deg,
                y=getattr(splines, smoothed_attr),
                mode="lines",
                name=f"{label} smoothed",
                visible="legendonly",
                line=dict(color=smoothed_color),
                legendgroup=label,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=splines.sa_grid_deg,
                y=fit_curve / unit_divisor,
                mode="lines",
                name=f"{label} fit",
                line=dict(width=2, color=fit_color),
                legendgroup=label,
            )
        )
    fig.update_layout(xaxis_title="Slip angle (deg)", yaxis_title=y_title, legend_title="Condition")
    return fig


# graph_key -> (display label used in the export multiselect, figure).
# Populated as each figure below is built so the Export section can reuse
# the exact same figures without rebuilding them.
exportable_graphs: dict[str, tuple[str, go.Figure]] = {}

st.subheader("Fy vs. slip angle")
col_fy_load, col_fy_camber = st.columns(2)
with col_fy_load:
    st.caption("Across the load sweep (zero camber)")
    fig = _sweep_overlay_figure(
        result.load_conditions,
        "FY",
        "fy_splines",
        "fy",
        result.fy.load_sweep_fit_fy_n,
        LBF_TO_N,
        lambda c: f"Fz={c.fz_nom:g} lbf",
        "Fy (lbf)",
    )
    exportable_graphs["FY_LoadSweep"] = ("Fy vs. slip angle -- load sweep", fig)
    st.plotly_chart(fig, use_container_width=True)
with col_fy_camber:
    st.caption(f"Across the camber sweep (Fz={result.reference_fz_nom:g} lbf)")
    fig = _sweep_overlay_figure(
        result.camber_conditions,
        "FY",
        "fy_splines",
        "fy",
        result.fy.camber_sweep_fit_fy_n,
        LBF_TO_N,
        lambda c: f"IA={c.ia_nom:g} deg",
        "Fy (lbf)",
    )
    exportable_graphs["FY_CamberSweep"] = ("Fy vs. slip angle -- camber sweep", fig)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Mz vs. slip angle")
col_mz_load, col_mz_camber = st.columns(2)
with col_mz_load:
    st.caption("Across the load sweep (zero camber)")
    fig = _sweep_overlay_figure(
        result.load_conditions,
        "MZ",
        "mz_splines",
        "mz",
        result.mz.load_sweep_fit_mz_nm,
        FTLB_TO_NM,
        lambda c: f"Fz={c.fz_nom:g} lbf",
        "Mz (ft-lb)",
    )
    exportable_graphs["MZ_LoadSweep"] = ("Mz vs. slip angle -- load sweep", fig)
    st.plotly_chart(fig, use_container_width=True)
with col_mz_camber:
    st.caption(f"Across the camber sweep (Fz={result.reference_fz_nom:g} lbf)")
    fig = _sweep_overlay_figure(
        result.camber_conditions,
        "MZ",
        "mz_splines",
        "mz",
        result.mz.camber_sweep_fit_mz_nm,
        FTLB_TO_NM,
        lambda c: f"IA={c.ia_nom:g} deg",
        "Mz (ft-lb)",
    )
    exportable_graphs["MZ_CamberSweep"] = ("Mz vs. slip angle -- camber sweep", fig)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Fitted coefficients")
col_fy_table, col_mz_table = st.columns(2)
col_fy_table.write("**Fy coefficients**")
col_fy_table.dataframe(dataclasses.asdict(result.fy.coefficients), use_container_width=True)
col_mz_table.write("**Mz coefficients**")
col_mz_table.dataframe(dataclasses.asdict(result.mz.coefficients), use_container_width=True)

# ---------------------------------------------------------------------------
# 4. Export
# ---------------------------------------------------------------------------

st.header("4. Export")

st.subheader("Tire identity")
st.caption(
    "Used to name every exported file below, as Compound_DiameterXWidth_<name> "
    "-- look these up from your Tire ID Schedule (compound is the tire's code, "
    "e.g. R25B; size is diameter x width, e.g. 20.5x7.0)."
)
col_compound, col_diameter, col_width = st.columns(3)
compound = col_compound.text_input("Compound", value="")
diameter = col_diameter.text_input("Diameter (in)", value="")
width = col_width.text_input("Width (in)", value="")
name_prefix = f"{_slugify(compound)}_{_slugify(diameter)}X{_slugify(width)}"

st.subheader("Fitted coefficients")
col_tire, col_round, col_run = st.columns(3)
tire = col_tire.text_input("Tire ID", value=round_data.tireid or "Tire")
round_num = col_round.number_input("Round", value=0, step=1)
run_num = col_run.number_input("Run", value=0, step=1)

payload = cornering_fit_to_dict(result, tire=tire, round_=int(round_num), run=int(run_num))
st.download_button(
    "Download fitted coefficients (JSON)",
    data=json.dumps(payload, indent=2),
    file_name=f"{name_prefix}_Coefficients.json",
    mime="application/json",
)

st.subheader("Graphs")
graph_keys = list(exportable_graphs.keys())
selected_graph_keys = st.multiselect(
    "Select graphs to export",
    options=graph_keys,
    default=graph_keys,
    format_func=lambda key: exportable_graphs[key][0],
)

if st.button("Export selected graphs"):
    if not selected_graph_keys:
        st.warning("Select at least one graph to export.")
    else:
        try:
            with st.spinner(
                "Rendering graphs -- the first export on this computer sets up the "
                "image renderer and needs an internet connection, so it may take a "
                "little longer than usual..."
            ):
                _ensure_graph_export_engine()
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for key in selected_graph_keys:
                        _, fig = exportable_graphs[key]
                        # Wide/tall enough that the legend (up to 5 conditions
                        # x 3 traces each, for a load sweep) never gets cut
                        # off the way it can at the interactive view's default
                        # inline size.
                        png_bytes = fig.to_image(format="png", width=1200, height=800, scale=2)
                        zip_file.writestr(f"{name_prefix}_{key}.png", png_bytes)
            st.session_state["graph_export_zip"] = buffer.getvalue()
            st.session_state["graph_export_name"] = f"{name_prefix}_graphs.zip"
        except Exception as exc:
            st.error(f"Couldn't render graphs for export: {exc}")

if "graph_export_zip" in st.session_state:
    st.download_button(
        "Download graphs (ZIP)",
        data=st.session_state["graph_export_zip"],
        file_name=st.session_state["graph_export_name"],
        mime="application/zip",
    )
