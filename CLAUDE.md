# CLAUDE.md — PacejkaModelv2 (MATLAB → Python migration)

This file persists constraints and conventions for the MATLAB → Python
migration of Alabama FSAE's tire modeling codebase. Read this before doing
any work in this repo. See `MIGRATION_PLAN.md` for the inventory, call
graph, translation order, and testing strategy.

## What this project is

A Formula SAE team's Pacejka Magic Formula tire-fitting toolchain, currently
11 MATLAB `.m` files. It ingests raw TTC (Tire Testing Consortium) round
data, segments it by test condition, spline-smooths it, and fits Magic
Formula coefficients (lateral force, aligning moment, longitudinal force,
overturning moment) via nonlinear least squares. Must outlive the current
maintainer's MATLAB license and remain usable by future, less MATLAB-fluent
teammates.

## Roadmap beyond Phase 1

Two things the user has confirmed about where this is going, which change
how the term-finder ports (`Pacejka_Term_Finder_FY_V3`/`MZ_V1_redo`, not
yet ported) should be scoped when we get there:

- **Multi-load sweeps are core, not optional.** A real test session
  typically covers ~5 nominal loads (50-250 lbf). This is exactly what
  quirk #7's `SweepVars.Fz = [50]` was meant to be hand-edited into (e.g.
  `[50 100 150 200 250]`) each session in MATLAB — the pipeline was always
  supposed to sweep every tested load, not fit one hardcoded value forever.
  The Python orchestration layer should take the list of nominal loads
  actually tested in a session — ideally auto-detected from the loaded
  round's FZ channel rather than hand-typed, consistent with the
  no-per-session-code-edits principle above — and run the segment/smooth/
  fit pipeline once per load automatically, producing the per-load overlay
  plots `tiremodelV2.m`'s plotting loop already does.
- **The eventual goal is a real interpolating/predictive tire model for
  lapsim integration (explicitly future work, not now). Decided: fit the
  `dFz` terms properly; no fallback interpolation utility.** The
  mechanism for this is *not* a separate interpolation layer bolted on
  top — it's fitting the Magic Formula's own load-dependence terms
  (`D_y`/`E_y`/etc. as functions of `dFz`, e.g. `mu_y = Dy1 + Dy2*dfz`)
  correctly, using data that spans the *full* set of tested loads at once.
  Done right, the resulting closed-form equation in `model.py` already
  interpolates (and extrapolates a bit) continuously across load — that's
  what the `dFz` terms are *for*. `tiremodelV2.m`'s tail-end
  `interp1`-between-independently-fit-per-load-curves section is a
  workaround for the `dFz` stage never having been fit properly (itself
  another symptom of the same hardcoding pattern —
  `Pacejka_Term_Finder_FY_V3.m`'s own `dFz` stage also uses a hardcoded
  single `Fz_vals = [50]` rather than the full spread) — the Python port
  should fix the `dFz` fit itself rather than reproduce that workaround.
  Practical implication for `model.py`: keep it stateless pure functions
  of `(Fz, IA, alpha, coefficients) -> force`, importable independently of
  Streamlit/pandas, since that's the interface a future lapsim integration
  would actually call.

## Hard constraints

- **Target**: Python 3, with a Streamlit UI for loading raw data, running
  fits, and saving/exporting results.
- **Fitting stack**: numpy/pandas + `scipy.optimize` (`least_squares` /
  `curve_fit` in place of `lsqcurvefit`/`nlinfit`). Spline smoothing
  (`fit(...,'smoothingspline',...)`) uses `csaps`, not
  `scipy.interpolate.UnivariateSpline`/`splrep` — MATLAB's smoothing spline
  minimizes `p*sum((y-f(x))^2) + (1-p)*integral(f''(x)^2)` with `p` a 0-1
  fidelity/curvature trade-off and every data point as a knot (the Reinsch
  formulation); scipy's FITPACK-based splines instead choose a *reduced*
  knot set to keep the residual sum under an absolute threshold `s`, in the
  data's own units — the two parameters aren't interconvertible, and each
  `Raw_Data_Fitter_*` file uses a different hand-tuned `SmoothingParam`
  (0.99999999, 0.90, 0.1, 0.75, 0.9 across the four files), which matters
  because the smoothed curve is what gets fit as Magic Formula `ydata`, so
  under/over-smoothing shows up as a real shift in fitted `D_y`/`E_y`, not
  just cosmetically. `csaps` implements the same Reinsch `p`-in-`[0,1]`
  formulation MATLAB uses, so the existing `SmoothingParam` values transfer
  directly instead of needing re-derivation per condition.
- **No hardcoded absolute paths, anywhere.** The MATLAB code currently
  hardcodes `C:\OneDrive - The University of Alabama\...` and
  `"CC's tire model folder\Fitted Parameters\"` (see MIGRATION_PLAN.md for
  every instance). The Python data root must be configured once (env var,
  `.env`, or a local config file such as `~/.pacejka/config.toml`) pointing
  at the user's locally-synced OneDrive/SharePoint folder, and every module
  reads that root instead of embedding a path. Configuring it should be a
  one-time step exposed in the Streamlit UI, not a code edit.
- **`requirements.txt`** must be kept current as dependencies are added.
- **Correctness discipline — golden tests.** Every ported function must be
  checked against the original MATLAB output on the same input, within a
  tolerance, before it's considered done. See "Golden testing" below and
  MIGRATION_PLAN.md §5 for the fixture format and capture workflow.
- **Longitudinal (Fx / braking) support is a future extension.** The
  existing MATLAB code already contains an Fx/braking pipeline
  (`Raw_Data_Fitter_Fx_V2`, `Pacejka_Term_Finder_Data_Compiler_V1`,
  `Pacejka_Term_Finder_FX_V4_Redo`, `Pacejka_Term_Finder_MX_V1`) but it is
  less mature than the cornering (Fy/Mz) pipeline — `Mx` isn't even wired
  into `tiremodelV2.m` (its call is commented out). **Working assumption:**
  Phase 1 of the port covers the cornering pipeline only (segmentation →
  `ParaRange` → `Raw_Data_Fitter_Fy`/`Fy` term finder →
  `Raw_Data_Fitter_Mz`/`Mz` term finder). The package layout reserves a
  `fitters/fx.py` and `fitters/mx.py` module and a `Longitudinal` config
  section so the Fx/Mx pipeline slots in later without restructuring, but
  their fitting logic is *not* ported in Phase 1. **Confirm this reading
  with the user before starting** — "longitudinal" could also just mean
  "don't reach for new capability beyond what MATLAB already does," in
  which case Fx/Mx get ported too, just after Fy/Mz.

## Known MATLAB quirks — preserve intent, fix the bug, keep golden tests honest

These are real oddities in the source. Don't silently "clean them up" in a
way that changes numerics without noting it, and don't assume they're
correct just because they're the original:

1. **Filename/function-name mismatches.** `Raw_Data_Fitter_Fy_V3.m`
   contains a function named `Raw_Data_Fitter_Fy_V2`. `Raw_Data_Fitter_Mx_V2.m`
   contains a function named `Raw_Data_Fitter_MX_V2` (case differs). MATLAB
   resolves by filename on-disk, so callers reference the V3/V2-by-filename
   version; the internal name is dead cosmetic mismatch. When capturing
   golden fixtures from MATLAB, invoke by file, not by the function's
   internal name.
2. **Fragile string comparison in `tiremodelV2.m`**: `if Type == 'FY'` is
   an elementwise char comparison, not `strcmp`. It happens to work today
   because `'FX'` and `'FY'` are both length 2, but it's a latent bug. Fix
   this for real in the Python port (plain `==` on Python `str` is safe).
3. **Inconsistent parameter-file naming** across term finders:
   `FY_Parameters_{Tire}_{Round}_{Run}_{Fz}FZ.mat` vs.
   `FX_Parameters_{Tire}_{Round}_{Fz}FZ_{Run}.mat` (Run and Fz swapped) vs.
   `MX_Parameters_{Tire}_{Round}_{Run}.mat` (no Fz) vs.
   `MZ_Parameters_{Tire}_{Round}_{Run}_{Fz}FZ.mat`. The Python port should
   adopt one consistent naming/storage convention (e.g. a single
   `parameters.py` read/write module keyed by `(quantity, tire, round, run,
   fz)`), not replicate four inconsistent schemes.
4. **`ParaRange.m`** has a stray `if 1==1` (dead conditional, always true)
   for `SA_High`/`SA_Low` in the Cornering branch, and leaves `FZ_High`/
   `FZ_Low`/others undefined for out-of-table nominal values (e.g.
   `P_Nom` values other than {8,10,11,12,14}) — MATLAB would error or carry
   stale values from a previous loop iteration. Port the explicit branches;
   raise a clear error on an unmapped nominal value instead of silently
   reusing stale state.
5. **`ParaRange.m`'s `isreal(IA_Nom)`/`isreal(V_Nom)` guards are dead-branch
   bugs.** Each is written as `if isreal(X) ... else isnan(X); ... end`,
   apparently intended to special-case NaN. But `isreal(nan)` is `True` in
   MATLAB (NaN has no imaginary part), so the `isnan` branch is unreachable
   — a NaN `IA_Nom`/`V_Nom` silently produces `NaN ± constant`, not
   `±inf`. `Data_Finder_v3.m` already compensates for this itself,
   re-checking `isnan(IA_Nom)`/`isnan(V_Nom)` right after calling
   `ParaRange` and overwriting the bounds with `±inf`. The Python port
   (`pacejka/ranges.py`) preserves the original NaN-in-NaN-out behavior for
   golden-test fidelity — the *caller* (the future `segmenting.py` port of
   `Data_Finder_v3.m`) must replicate the same compensating override, not
   assume `para_range` already handles NaN.
6. **`Data_Finder_v3.m`'s own `isnan(IA_Nom)`/`isnan(V_Nom)` override checks
   the whole sweep *vector*, not the current loop element.** It's written
   as `if isnan(IA_Nom) ... end` where `IA_Nom` is the full sweep array
   (e.g. `[0,1,2,3,4]`), not `IA_Nom(r)`. MATLAB's `if` on a non-scalar
   array is only true when *every* element is nonzero, so this only fires
   if the entire sweep is NaN — never for one NaN entry mixed with real
   values. Combined with quirk #5 above, a NaN entry in a mixed sweep would
   silently produce NaN (not `±inf`) bounds, which makes every `>=`/`<=`
   comparison false and drops all data for that condition — the opposite
   of the "NaN nominal means don't filter on this channel" behavior that's
   clearly intended (and that `FZ_Nom` already gets, directly in
   `ParaRange`). No sweep configuration used anywhere else in this repo
   actually mixes a NaN entry into an otherwise-real IA_Nom/V_Nom sweep, so
   this never changes behavior for real usage — but it's a real bug, not a
   deliberate design. `pacejka/segmenting.py`'s `segment_condition` checks
   the scalar value actually passed in for that call, which is what was
   clearly intended, rather than replicating the vector-wide check.
7. **`Raw_Data_Fitter_Fy_V3.m` hardcodes `SweepVars.Fz = [50]`** (and
   `IA=[0]`, `SA=[0]`, `P=[12]`, `V=[25]`) inside its own body, not as
   parameters. Its caller, `Pacejka_Term_Finder_FY_V3.m`, takes an `Fz_nom`
   argument and uses it to build a field name to look up in the result
   (e.g. `SplineData.P12.SA0.IA0.FY_..._150FZ_12P_0IA`) — but
   `Raw_Data_Fitter_Fy_V3` only ever *produces* the `_50FZ_` field, no
   matter what `Fz_nom` was passed to the term finder. **In the current
   MATLAB tool, the whole FY/MZ term-finder pipeline silently only ever
   fits FZ=50 lbf**, regardless of what `Fz_nom` a user requests — any
   other value would hit a "field not found" error, or (if some other
   value happened to exist from a stale run) silently reuse the wrong
   condition's data. This isn't a deliberate single-condition design; it's
   a real limitation nobody appears to have hit yet, presumably because
   nobody has tried fitting anything other than 50 lbf with this code. The
   Python port (`pacejka/fitters/fy.py`'s `fit_alpha_sweep`) has no
   equivalent to preserve: it fits whatever `DataFrame` it's handed (from
   `pacejka.segmenting.segment_condition`), so which condition gets fit is
   controlled entirely by what the caller segments beforehand, not by a
   hardcoded sweep inside the fitting function. **Practical implication
   for the team**: if any previously-fitted parameter set from this MATLAB
   tool claims to be for a load other than 50 lbf, that claim should be
   treated with suspicion until re-verified.
8. **Optimizer nondeterminism**: `lsqcurvefit`/`nlinfit` in MATLAB and
   `scipy.optimize.least_squares`/`curve_fit` in Python use different
   underlying algorithms (trust-region-reflective variants differ in
   implementation detail, Levenberg-Marquardt line search, etc.). Fitted
   coefficients will not match bit-for-bit even with identical inputs,
   bounds, and initial guess. **Golden tests for fit-producing functions
   compare fit quality (residuals/R² against the same input data), not
   coefficient equality.** Pure/deterministic functions (spline evaluation
   at fixed points, Magic Formula evaluation given fixed coefficients,
   `ParaRange`) get exact-value golden tests instead.

## Migration workflow

- Translate one function at a time, leaf functions first (see
  MIGRATION_PLAN.md §2 for the full order).
- Each function gets: a Python port + a golden test comparing to captured
  MATLAB output + (if applicable) a unit test for edge cases MATLAB doesn't
  cover well. Commit at that granularity — don't batch multiple ported
  functions into one commit.
- Shared Magic Formula math (the core `Fyo`/`Fxo`/`Mzo`/`Mxo` equations,
  duplicated inline across the term-finder scripts and once more as a
  nested `Pacejka_FY` function inside `Pacejka_Term_Finder_FX_V4_Redo.m`)
  should become one shared, tested module (`model.py`) rather than four
  copies — this is a case where the Python port should *not* mirror
  MATLAB's structure, since the duplication there is a maintenance hazard,
  not a deliberate design choice.
- **No per-condition file round-tripping.** `Data_Finder_v3.m` writes one
  `.mat` file per nominal test condition to disk, and every
  `Raw_Data_Fitter_*`/`Pacejka_Term_Finder_Data_Compiler_V1` function
  re-loads those files by reconstructing the same filename from the same
  nominal values via string concatenation. That's a side effect of MATLAB
  scripts not being able to hand a struct back to a caller as easily as a
  function can — it isn't part of the physics or the math. The Python port
  (`pacejka/segmenting.py`'s `segment_condition`) returns an in-memory
  `pandas.DataFrame` for one condition directly; downstream fitters should
  consume that DataFrame directly rather than re-implementing MATLAB's
  save/reload dance. Same deliberate-divergence principle as `model.py`
  above — don't mirror accidental plumbing.
- Golden tests need a genuine MATLAB run to compare against. Where that
  isn't available in the working environment (no MATLAB access), a
  function's tests are unit tests with independently hand-computed expected
  values instead, clearly labeled as such (not silently presented as
  "golden") — see `tests/unit/test_segmenting.py` for the pattern. Real TTC
  data used to spot-check a port during development is never committed to
  the repo (per the data-root constraint above) — synthetic fixtures only.
