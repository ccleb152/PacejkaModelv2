# MATLAB → Python Migration Plan

Status: **exploration only — no Python written yet.** Review this, then
we'll start translating leaf functions first.

---

## 1. Inventory — every `.m` file

| File | Kind | What it does |
|---|---|---|
| `ParaRange.m` | function | Given nominal `FZ, P, IA, SA, V` and a test `type` (`Cornering`/`Braking`), returns high/low acceptance bands for each channel, used to filter noisy raw samples around a nominal test condition. Pure, no I/O, no deps. |
| `Data_Finder_v3.m` | script | Loads one raw TTC round `.mat` file (e.g. `A1320run33.mat`), and for every combination of nominal `FZ × P × IA × SA`, calls `ParaRange` to get acceptance bands, filters the round's sample arrays down to points inside those bands, strips NaNs, computes derived channels (`NFX`, `NFY`, `Vc`, `Vs`), and saves one segmented `.mat` file per condition into `FX Data/<P>psi/<SA>SA/<IA>IA/` or `FY Data/...` depending on `type`. |
| `Pacejka_Term_Finder_Data_Compiler_V1.m` | function | Sweeps `Fz × SA × IA × P`, loads the segmented per-condition `.mat` files `Data_Finder_v3` produced, and pulls out `FX`, `FY`, `SL` raw vectors into one nested `RawData` struct keyed by `.P<P>.SA<SA>.IA<IA>.<Var>_...`. No fitting — just aggregation. |
| `Raw_Data_Fitter_Fx_V2.m` | function | Same sweep-and-load pattern as the compiler, but per condition it fits smoothing splines of `SL→FX`, `SL→FY`, `SL→MZ`, `SL→Vc`, evaluates them on a fixed slip-ratio grid, and returns a `SplineData` struct plus a `RawData.<FZ...>.{SL,FX}` passthrough of the raw (unsplined) points for plotting. |
| `Raw_Data_Fitter_Fy_V3.m` (**function inside is named `Raw_Data_Fitter_Fy_V2`** — filename/function-name mismatch, see CLAUDE.md) | function | Same pattern, fits `SA→FX`, `SA→FY`, `SA→MZ`, `SA→Vc` splines, evaluated on a fixed slip-angle grid. |
| `Raw_Data_Fitter_Mx_V2.m` (**function inside is `Raw_Data_Fitter_MX_V2`**, case mismatch) | function | Sweeps `Fz × IA`, loads segmented files, trims the wrap-around/return-sweep portion of the SA trace (via an index computed from where SA hits its max/min), fits one `SA→MX` smoothing spline per condition, evaluates on a fixed asymmetric-density SA grid, keeps raw trimmed points too. |
| `Raw_Data_Fitter_Mz_V2.m` | function | Same shape as the Mx fitter, for `SA→MZ` (the wrap-around trim is present but currently commented out, unlike Mx). |
| `Pacejka_Term_Finder_FY_V3.m` | function | The core lateral pure-slip fit. Calls `Raw_Data_Fitter_Fy_V3` for smoothed `Alpha/FY` data, defines the Magic Formula pure-lateral equations (`B_y, C_y, D_y, E_y, S_Hy, S_Vy → F_yo`) as closures, and runs four sequential `lsqcurvefit` stages: **Base** (nominal Fz, zero camber) → **dFz** (load sensitivity, via `nlinfit` with bisquare robust weighting) → **dPi** (pressure — currently a no-op stub, coefficients hardcoded to 0) → **dIA** (camber sensitivity) → **dIA×dFz** (cross term). Each stage's fitted coefficients seed the next. Also contains a `Pacejka_FY` nested-function *duplicate* of the final Fy equation (used only by other files, not by this one — see §2). Saves `FY_Parameters_<Tire>_<Round>_<Run>_<Fz>FZ.mat`, a table of `{Structure, Variable, Initial, Final, Lower, Upper}`. |
| `Pacejka_Term_Finder_FX_V4_Redo.m` | function | The core longitudinal fit, and the most complex file. Calls `Raw_Data_Fitter_Fx_V2` and `Pacejka_Term_Finder_Data_Compiler_V1`. Fits, in order: pure-slip `Base` → `dFz` → (`dPi` stub) → `dIA`; then **combined-slip longitudinal** `Base` → `dFz` → `dIA` (weighting pure-slip `Fx` by a cosine-based `G_xa` factor); then **combined-slip lateral** `Base` → `dFz` → `dIA` (weighting a pure `Fy0`, computed by an internal nested function `Pacejka_FY`, by a `G_yk` factor). The nested `Pacejka_FY` here **loads the `FY_Parameters` `.mat` file on disk** — i.e. this function has a *file-based* dependency on `Pacejka_Term_Finder_FY_V3` having already been run and saved, not a call-graph dependency. Saves `FX_Parameters_<Tire>_<Round>_<Fz>FZ_<Run>.mat`. |
| `Pacejka_Term_Finder_MX_V1.m` | function | Overturning-moment fit. Calls `Raw_Data_Fitter_Mx_V2`. Its `ParameterLoad` local function loads **both** `FY_Parameters` and `FX_Parameters` `.mat` files to get a combined-slip `Fy_cn` value used inside the Mx equation, then fits `Base` and `dIA` stages. **Not currently called from `tiremodelV2.m`** (the call is commented out) — this pipeline is present but disconnected/unfinished. Saves `MX_Parameters_<Tire>_<Round>_<Run>.mat`. |
| `Pacejka_Term_Finder_MZ_V1_redo.m` | function | Aligning-moment (pneumatic trail) fit, MF-Tire 6.1-based. Calls `Raw_Data_Fitter_Mz_V2`. Its `ParameterLoad` local function loads the `FY_Parameters` `.mat` file to get `K_yalpha, Cy, mu_y, By, Fy_o` at both the actual camber and camber=0. Fits `Base` → `dFz` → `dIA` → `dIA×dFz`. Saves `MZ_Parameters_<Tire>_<Round>_<Run>_<Fz>FZ.mat`. |
| `tiremodelV2.m` | script (top-level orchestrator) | Interactive entry point. Opens a file-picker (`uigetfile`) rooted at a **hardcoded absolute Windows path**, loads one or more raw TTC round `.mat` files, regex-matches variable names to detect whether the selection is cornering (`FY`) or braking (`FX`) data, then dispatches: for `FY` data it calls `Pacejka_Term_Finder_FY_V3` then `Pacejka_Term_Finder_MZ_V1_redo` and plots both; for `FX` data it calls `Pacejka_Term_Finder_FX_V4_Redo` and plots. Finishes with a cross-`Fz` linear interpolation/extrapolation of the Fy curves at intermediate loads, purely for visualization. Also `cd`s into another hardcoded absolute path mid-script and saves figures to a third hardcoded relative-but-Windows-flavored path (`"CC's tire model folder\Fitted Parameters\..."`). This script *is* essentially "the app" — its logic becomes the Streamlit page flow. |

Total: 11 `.m` files (10 functions/scripts of substance + `ParaRange` as the one pure leaf).

---

## 2. Call graph and translation order

**Edges** (`A → B` = A calls B; `A ⇢ B` = A has a *file-based* dependency
on B's saved output, not a direct call):

```
tiremodelV2
 ├─→ Pacejka_Term_Finder_FY_V3
 │      └─→ Raw_Data_Fitter_Fy_V3        (internal fn name: Raw_Data_Fitter_Fy_V2)
 ├─→ Pacejka_Term_Finder_MZ_V1_redo
 │      ├─→ Raw_Data_Fitter_Mz_V2
 │      └─⇢ Pacejka_Term_Finder_FY_V3      (loads FY_Parameters_*.mat)
 └─→ Pacejka_Term_Finder_FX_V4_Redo
        ├─→ Raw_Data_Fitter_Fx_V2
        ├─→ Pacejka_Term_Finder_Data_Compiler_V1
        └─⇢ Pacejka_Term_Finder_FY_V3      (loads FY_Parameters_*.mat)

Pacejka_Term_Finder_MX_V1              (disconnected — not called by tiremodelV2)
 ├─→ Raw_Data_Fitter_Mx_V2
 ├─⇢ Pacejka_Term_Finder_FY_V3            (loads FY_Parameters_*.mat)
 └─⇢ Pacejka_Term_Finder_FX_V4_Redo       (loads FX_Parameters_*.mat)

Data_Finder_v3 → ParaRange                (upstream of all of the above: produces
                                            the segmented .mat files every
                                            Raw_Data_Fitter_* and the Data_Compiler read)
```

**Leaf functions** (no `.m`-to-`.m` calls at all): `ParaRange`,
`Raw_Data_Fitter_Fx_V2`, `Raw_Data_Fitter_Fy_V3`, `Raw_Data_Fitter_Mx_V2`,
`Raw_Data_Fitter_Mz_V2`, `Pacejka_Term_Finder_Data_Compiler_V1`. All six
only touch `.mat` files on disk, not other functions.

**Proposed translation order** (leaves first, then build up; Fx/Mx deferred
per the longitudinal-is-future-work assumption — see CLAUDE.md):

**Phase 0 — shared foundation** (not a direct port of any one file, but
needed before anything else can be golden-tested meaningfully):
1. `model.py` — the Magic Formula equations that are currently duplicated
   inline in `Pacejka_Term_Finder_FY_V3`, re-duplicated as the nested
   `Pacejka_FY` in `Pacejka_Term_Finder_FX_V4_Redo`, and consumed again via
   file-load in the `MZ`/`MX` term finders. Written once, tested once,
   imported everywhere else. This is the one place we deliberately diverge
   from "mirror MATLAB's file structure."

**Phase 1 — cornering pipeline (Fy, Mz), leaf-first:**
2. `ParaRange` — pure, zero dependencies, trivial to golden-test exactly.
3. `Pacejka_Term_Finder_Data_Compiler_V1` — leaf, file I/O only, no fitting math.
4. `Data_Finder_v3` — depends only on `ParaRange` (already ported in step 2).
5. `Raw_Data_Fitter_Fy_V3` — leaf w.r.t. other `.m` files, but introduces the
   MATLAB-smoothing-spline → scipy translation problem; do this before any
   term finder needs it.
6. `Raw_Data_Fitter_Mz_V2` — same spline-translation shape, for MZ.
7. `Pacejka_Term_Finder_FY_V3` — depends on step 5 + `model.py`. This is the
   highest-value single port: it's the thing every other quantity's fit
   depends on (by file, if not by call). **Scope note (see CLAUDE.md
   "Roadmap beyond Phase 1"):** the original's `dFz`-stage fit uses a
   single hardcoded `Fz_vals = [50]` instead of the full spread of tested
   loads, which is why `tiremodelV2.m` falls back to crudely `interp1`-ing
   between independently-fit per-load curves instead of getting real
   interpolation from the Magic Formula's own load-dependence terms. The
   Python port's `dFz` stage should take data spanning all tested nominal
   loads, not one hardcoded value, so the fitted `D_y`/`E_y`/etc. actually
   interpolate across load the way they're designed to.
8. `Pacejka_Term_Finder_MZ_V1_redo` — depends on step 6 + step 7's saved
   parameters (or, better, an in-memory call once both are Python objects
   instead of round-tripping through `.mat`). Same `dFz`-stage scope note
   as step 7 applies here too.
9. `tiremodelV2` orchestration logic → becomes the Streamlit page flow
   (file selection, FX/FY dispatch, calling into steps 7–8, plotting).

**Phase 2 — longitudinal pipeline (Fx, Mx), future work per CLAUDE.md:**
10. `Raw_Data_Fitter_Fx_V2`
11. `Raw_Data_Fitter_Mx_V2`
12. `Pacejka_Term_Finder_FX_V4_Redo` (depends on 10, step 3, and step 7's
    output)
13. `Pacejka_Term_Finder_MX_V1` (depends on 11, step 7 and step 12's output
    — and note it's currently *disconnected* from the orchestrator, so
    porting it doesn't unblock anything else; lowest priority of all 11
    files)

---

## 3. Raw file formats

Three distinct `.mat` shapes flow through this pipeline, none of them
committed to the repo (they live on the team's synced OneDrive/SharePoint
folder, per the data-root config constraint in CLAUDE.md):

1. **Raw TTC round data** (e.g. `A1320run33.mat`, referenced in
   `Data_Finder_v3.m`; loaded ad hoc via `uigetfile` in `tiremodelV2.m`).
   One `.mat` file per test round, containing parallel 1×N arrays — this is
   the standard Calspan/TTC round-data layout: `FY, FX, MZ, MX, SA, SL, FZ,
   IA, P, V, N` (channels), plus `TSTC, TSTI, TSTO` (tire surface temps,
   center/inner/outer), `RE, RL` (effective/loaded radius), `SR` (slip
   ratio, if distinct from `SL`), `ET` (elapsed time), `AMBTMP`, `RST`,
   `RUN`, `channel`, `source`, `testid`, `tireid` (metadata). Units are the
   TTC convention — force in lbf, angles in degrees, speed in mph — later
   converted to SI (N, rad, m/s) inside the term-finder functions (`*4.448`
   lbf→N, `*pi/180` deg→rad, `*1.609/3.6` mph→m/s).

2. **Segmented per-condition data**, produced by `Data_Finder_v3.m`,
   consumed by every `Raw_Data_Fitter_*` and the `Data_Compiler`. One file
   per `(P, SA, FZ, IA)` combination. Filename pattern (as written by
   `Data_Finder_v3`, and as expected on load by the fitters —
   **note these two patterns don't quite agree**, see the flag below):
   `<test>_<tire>_<P>psi_<SA>SA_<FZ>FZ_<IA>IA_<V>.mat`, stored under
   `FX Data/<P>psi/<SA>SA/<IA>IA/` or `FY Data/<P>psi/<SA>SA/<IA>IA/`
   depending on test type. Each file holds channel vectors renamed with a
   `<Var>_<TestID>_<FZ>FZ_<P>P_<IA>IA` suffix convention, e.g.
   `FY_R9_Rn32_150FZ_12P_0IA`, `SA_R9_Rn32_150FZ_12P_0IA`,
   `Vc_R9_Rn32_150FZ_12P_0IA` — the fitters reconstruct these variable
   names by string concatenation and `eval`/dynamic field access, which is
   the main reason this whole layer needs care in translation (Python will
   use explicit dict/DataFrame keys instead of `eval`).
   ⚠️ **Flag for verification during Phase 1**: `Data_Finder_v3.m`'s
   `SaveFilename` construction and the `File = strcat(FilePrefix, ...)`
   construction in `Raw_Data_Fitter_Fy_V3`/`Fx_V2` are not obviously
   byte-identical (different token order/prefix). This needs to be checked
   against real files on the OneDrive folder before porting step 3–6, since
   if they don't actually match, the MATLAB pipeline is already relying on
   some manual renaming step that isn't captured in any `.m` file.

3. **Fitted-parameter output**, written by each `Pacejka_Term_Finder_*` and
   read back by the ones downstream of it (by file, not by call — see §2).
   Each holds one MATLAB table variable (`FY_ParameterList`,
   `FX_ParameterList`, `MX_ParameterList`, `MZ_ParameterList`) with columns
   `Structure` (which coefficient family, e.g. `'p.'`, `'ry.'`, `'r.'`),
   `Variable` (name, e.g. `Ky1`, `Dy2`), `Initial`, `Final`, `Lower`,
   `Upper`. Filename convention differs per quantity (flagged in CLAUDE.md
   §"Known MATLAB quirks" #3) — the Python port normalizes this to one
   scheme.

---

## 4. Proposed Python project structure

```
pacejka/                        # installable package — the ported model + I/O
  __init__.py
  config.py                     # data-root resolution: env var → local config
                                 # file (~/.pacejka/config.toml) → Streamlit
                                 # first-run prompt. No path ever hardcoded
                                 # in source.
  model.py                      # shared Magic Formula equations (Fyo, Fxo,
                                 # Mzo, Mxo) as pure numpy functions — the one
                                 # place we deliberately de-duplicate vs. MATLAB
  ranges.py                     # ParaRange port
  segmenting.py                 # Data_Finder_v3 port
  io/
    __init__.py
    ttc_raw.py                  # load raw round .mat files (scipy.io.loadmat)
    segmented.py                # read/write per-condition segmented files
    parameters.py                # read/write fitted-parameter tables
                                 # (pandas DataFrame in, DataFrame/CSV out —
                                 # one consistent naming scheme, see CLAUDE.md)
  splines.py                    # shared smoothing-spline helpers, built on
                                 # `csaps` (not scipy's UnivariateSpline/
                                 # splrep) since csaps uses the same Reinsch
                                 # p-in-[0,1] formulation as MATLAB's
                                 # `fit(..., 'smoothingspline',
                                 # 'SmoothingParam', p)` -- see CLAUDE.md
  fitters/
    __init__.py
    fy.py                       # Raw_Data_Fitter_Fy + Pacejka_Term_Finder_FY
    mz.py                       # Raw_Data_Fitter_Mz + Pacejka_Term_Finder_MZ
    fx.py                       # (Phase 2 placeholder) longitudinal fit
    mx.py                       # (Phase 2 placeholder) overturning-moment fit
  pipeline.py                   # tiremodelV2 orchestration logic, minus the
                                 # UI bits (those live in app/)

app/
  streamlit_app.py              # entry point / landing page
  pages/
    1_configure_data_folder.py  # one-time data-root setup
    2_load_data.py              # pick raw round file(s), segment if needed
    3_run_fit.py                # dispatch Fy/Mz (and later Fx/Mx) fitting,
                                 # show fit-vs-raw plots (Plotly, for
                                 # interactivity, replacing MATLAB's uitabgroup)
    4_results_export.py         # inspect/export parameter tables
  state.py                      # st.session_state helpers shared across pages

tests/
  conftest.py
  golden/
    fixtures/                   # captured MATLAB inputs+outputs, one dir per
                                 # ported function (see §5)
    test_para_range.py
    test_raw_data_fitter_fy.py
    test_pacejka_term_finder_fy.py
    ...
  unit/                         # Python-only edge-case tests not covered by
                                 # golden fixtures (e.g. error handling on
                                 # unmapped ParaRange inputs)

scripts/
  matlab/
    generate_golden_fixtures.m  # single driver: calls each ported .m
                                 # function with canned inputs, dumps
                                 # inputs+outputs to tests/golden/fixtures/

requirements.txt
CLAUDE.md
MIGRATION_PLAN.md
README.md
```

Notes:
- `data/` is intentionally *not* part of this tree — raw and segmented
  `.mat` files stay on the synced OneDrive/SharePoint folder pointed to by
  `pacejka/config.py`, never committed.
- Plotting moves from MATLAB `uitabgroup`/`uitab` figures to Plotly-in-
  Streamlit tabs (`st.tabs`), which is the natural equivalent and keeps
  interactivity (MATLAB's datatips) via Plotly hover.
- `pipeline.py` intentionally separates orchestration (what `tiremodelV2.m`
  does) from presentation (what the Streamlit pages do), so the fitting
  pipeline stays testable/scriptable outside the UI.

---

## 5. Capturing golden values from MATLAB

Goal: for every ported function, a small set of fixed inputs with MATLAB's
actual output captured, so the Python port can be checked against it on
demand (`pytest`), without needing MATLAB installed in CI or by future devs.

**Mechanism:**
1. A single MATLAB driver script, `scripts/matlab/generate_golden_fixtures.m`,
   calls each function-under-test with 2-3 representative canned inputs
   (small enough to hand-pick and reason about — a handful of `Fz`/`IA`/`SA`
   values, not full sweeps) and writes each case to
   `tests/golden/fixtures/<function_name>/<case_name>.json`:
   ```json
   {
     "inputs": { "FZ_Nom": 150, "P_Nom": 12, "IA_Nom": 2, "SA_Nom": -3, "V_Nom": 25, "type": "Cornering" },
     "outputs": { "FZ_High": 170, "FZ_Low": 136, "P_High": 12.99, "...": "..." }
   }
   ```
   JSON (via `jsonencode`) rather than `.mat` for the fixture files
   themselves — human-readable, diffable in PRs, no `scipy.io.loadmat`
   version-compatibility surface for something this small. For
   inputs/outputs that are naturally arrays (spline-evaluated vectors,
   parameter tables), JSON still works (nested arrays / list-of-records for
   the `Structure/Variable/Initial/Final/Lower/Upper` table).
2. **Two tolerance regimes**, matching the two kinds of ported function:
   - **Deterministic functions** (`ParaRange`, spline evaluation at fixed
     points given fixed input vectors, the Magic Formula equations in
     `model.py` given fixed coefficients): exact-ish comparison,
     `np.testing.assert_allclose(actual, expected, rtol=1e-6, atol=1e-9)`.
     These should match MATLAB almost to floating-point precision.
   - **Optimizer-driven functions** (anything calling `lsqcurvefit`/
     `nlinfit` — the bulk of the `Pacejka_Term_Finder_*` files): scipy's
     optimizer will not reproduce MATLAB's fitted coefficients bit-for-bit
     (see CLAUDE.md quirk #5). The golden fixture instead captures MATLAB's
     **fitted curve evaluated on the input grid** (i.e. `yfit.Base`, not
     `Xb`), and the Python test asserts the *Python* fit reproduces that
     curve within a looser tolerance (e.g. `rtol=1e-2` or an R²/RMSE
     threshold against the same `ydata`) — checking "does this fit the
     data about as well as MATLAB's fit did," not "are the coefficients
     identical."
3. **Re-running fixtures**: whenever a `.m` file changes (or a golden test
   fails and the cause is traced to the MATLAB reference being stale, not a
   Python bug), re-run `generate_golden_fixtures.m` and commit the updated
   JSON. This keeps the fixture-generation step explicit and versioned
   rather than something that happens invisibly.
4. **Fixture inputs come from real segmented data where relevant** — for
   the `Raw_Data_Fitter_*` and `Pacejka_Term_Finder_*` functions, the
   "input" in the fixture is realistically a path to a small, checked-in
   *sample* segmented `.mat`/CSV (a few hundred points, not a full test
   round) rather than inline scalars, since these functions consume whole
   channel vectors. `ParaRange` and `model.py`'s equations are the
   exception — those take scalars/small arrays and can be inlined directly
   in the JSON fixture.

**Open item to resolve before Phase 1 coding starts**: confirm the
filename-construction mismatch flagged in §3 doesn't mean the
`Raw_Data_Fitter_*` functions are already effectively broken/unused with
real data — if `Data_Finder_v3`'s output filenames don't match what the
fitters try to load, either there's a manual renaming step nobody wrote
down, or these functions haven't actually been exercised end-to-end
recently. Worth a quick check against the real OneDrive folder contents
before trusting them as a golden-test source of truth.
