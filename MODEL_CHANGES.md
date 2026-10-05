# Model change log

A dated, chronological record of changes to the tire model's physics and
math -- as opposed to `CLAUDE.md`, which documents the *current* state of
known MATLAB quirks and conventions. This file exists so a future
viewer looking at a piece of code that looks odd, or a coefficient that
behaves differently than they expect, can find out *when* it got that
way and *why*, without having to reconstruct the reasoning from git
blame or guesswork.

Add an entry here whenever a change affects the fitted coefficients, the
Magic Formula equations themselves, or how fitting data is prepared
(smoothing, sweep selection, bounds) -- not for UI/app changes, export
formats, or anything else that doesn't change the physics or the math.
Cross-reference the relevant `CLAUDE.md` quirk number where one exists,
rather than restating it -- `CLAUDE.md` is the single source of truth for
what the quirk *is*; this file is the record of what was *done* about it
and when.

---

## 2026-10-06 -- Fix the R20 Fz=50/100 fit-quality gap flagged in the Fx entry below

**What:** Follow-up to the open item in the entry below (R20 18x6-10's
Fz=50/100 lbf conditions fitting poorly, R^2 0.65-0.77). Two independent,
real causes, both fixed:
- `pacejka.quality.check_condition_quality`'s Braking slip-ratio-range
  check is now an **error**, not a warning. R20's auto-detected Fz=100
  lbf "load level" had 2+ distinct SL values (enough to pass the
  nunique check added earlier) but only a 0.015-wide SL range -- a
  transient/settling segment, not a real ~0.3-wide sweep. Fitting it
  anyway produced a Pacejka curve with R^2=0.65 against the smoothed
  spline for that condition alone, and (via the shared dFz stage)
  degraded the fit everywhere else too.
  `pacejka.detection.detect_fz_levels` gained the matching check (same
  `MIN_SL_SWEEP_RANGE` threshold, imported from `pacejka.quality` rather
  than duplicated) so this class of candidate is never reported as
  detected in the first place, rather than being detected and then
  raising downstream and aborting the whole fit.
- New `pacejka.fitters.fx.trim_to_raw_domain`, applied in
  `pacejka.longitudinal_pipeline._process_condition` right after
  `fit_kappa_sweep`: restricts each condition's spline evaluation to the
  portion of the fixed `SL_GRID` actually covered by that condition's
  raw SL samples, before either fitting or quality-scoring sees it.
  R20's Fz=50 lbf condition's raw SL only reached 0.115, short of the
  grid's 0.141 edge; `csaps` extrapolates unreliably past a spline's
  fitted domain, and that extrapolated tail (confirmed: +2487 N at
  SL=0.141 for a *50 lbf* load -- physically impossible, mu > 11) was
  feeding straight into both the dFz-stage fit target and the R^2 metric.

**Why:** `Raw_Data_Fitter_Fx_V2.m`'s own design evaluates every
condition's smoothing spline on one fixed `SLRange`, implicitly assuming
every tested load gets swept across the same full range. That holds for
LCO/R25B (every condition's raw SL range tracks the grid's edges within
~0.02) but not for R20's Fz=50 specifically -- not a MATLAB bug to
preserve, just an assumption that happens to fail on one real tire's
data, confirmed by direct inspection (see the diagnostic numbers above)
rather than guessed at.

**Verified with:** Full suite still **124 passed** (no test changes
needed -- the fix lives in the orchestration layer, not the ported
fitting functions themselves). Real-data re-check: R20 now auto-detects
the same clean 4-point load sweep (50/150/200/250 lbf) as LCO/R25B
(Fz=100 excluded entirely), with R^2 0.939 at Fz=50 (was 0.774) and
>= 0.996 at every other load/camber condition -- on par with LCO/R25B.

**Not changed:** `fit_fx_coefficients`'s fitting method (still the
partial-staged hybrid, unchanged by this entry) or any Fy/Mz behavior.

---

## 2026-10-06 -- Add pure-slip Fx (longitudinal) fitting pipeline

**What:** Ported the pure-longitudinal-slip portion of
`Pacejka_Term_Finder_FX_V4_Redo.m` and `Raw_Data_Fitter_Fx_V2.m`:
`pacejka.model.fx_pure`/`FxCoefficients` (the shared equation, unifying
the original's Base/dFz/dIA closures the same way `fy_terms` already
unifies FY's), `pacejka.fitters.fx.fit_kappa_sweep` (SL -> FX/FY/MZ/Vc
smoothing splines) and `fit_fx_coefficients` (the Base/dFz/dIA term
finder), and `pacejka.longitudinal_pipeline.run_longitudinal_fit`
(orchestration, mirroring `pacejka.pipeline.run_cornering_fit`).
`pacejka.quality` gained a `test_type` parameter so `check_round_quality`
/`check_condition_quality` can validate a Braking round (requiring
FX/SL instead of FY/MZ, checking the SL sweep range instead of SA)
without changing default (Cornering) behavior.

Scoped to pure-slip Fx only, confirmed with the user before starting:
the original file's combined-slip Fx and combined-slip Fy stages are
deferred, not ported even as a literal translation -- see CLAUDE.md
quirk #24.

Applied the same fixes already made for Fy/Mz, found independently in
this file:
- The dFz stage's hardcoded `Fz_vals = [50]`, gated by `if Fz_vals(n) ==
  Fz_nom` -- more severe than FY's quirk #7, since a non-50 `Fz_nom`
  would hit an undefined-variable error in the original, not just a
  silent wrong-condition fit. Fixed with a real multi-load `load_sweep`,
  same as FY/MZ. See CLAUDE.md quirk #20.
- The dIA stage's hardcoded `gamma_vals = [2]` (single camber, milder
  than FY's exactly-zero-effect quirk #11 since Fx's camber term is
  `gamma**2`-weighted and 2 deg isn't zero) *and* its independently
  hardcoded `Fz_vals = [150]` that doesn't match whatever `Fz_nom` the
  Base/dFz stages just used. Fixed with a real multi-camber
  `camber_sweep` recorded at the same reference load as everything
  else. See CLAUDE.md quirk #21.
- The dIA stage's missing lbf->N conversion on its `ydata` (same bug
  shape as FY's quirk #10, independently present here). Fixed by always
  converting in `sweep_point_from_kappa_sweep`. See CLAUDE.md quirk #22.
- `px1..px4` (pressure-deviation coefficients) are declared in the
  original's `p0` but never referenced by any of this file's fitting
  formulas at all -- more thoroughly dead than FY's `py1..py5` (which
  are at least used, just never fit). Omitted entirely from
  `FxCoefficients` rather than carried as inert fields. See CLAUDE.md
  quirk #23.

Applied the partial-staged hybrid (Base+dIA fit jointly, dFz kept as its
own separate stage) from the start, rather than porting the fully-staged
original first and promoting later -- the same investigation that
justified this for Fy/Mz (see the entry below) applies here for the same
structural reason (Base's own coefficients need to see real camber data
to generalize to it), and there was no reason to re-derive that
conclusion from scratch for a third equation.

**Why:** The user asked to extend the port into longitudinal (braking/
drive) data fitting, confirming (after reviewing the combined-slip
stages' SA=0 degeneracy) that pure-slip Fx should be scoped first, with
combined-slip Fx/Fy explicitly deferred rather than attempted against
data that can't support it.

**Verified with:** `tests/unit/test_fx_fitter.py` (synthetic slip-ratio
sweep, smoothing-spline recovery) and `tests/unit/test_fx_term_finder.py`
(synthetic Base/dFz/dIA fit, regression tests for the Fz_vals=[50] gate
and the Ex3 zero-width pin). One test-authoring note: the dFz stage's
`Kx2`/`Kx3` coefficients (both shape how `K_x` scales with `dfz` -- one
additive, one exponential) are genuinely correlated from this file's
generic, non-domain-tuned `p0`, the same class of equation/initial-guess
sensitivity CLAUDE.md quirk #18 and the Mz term finder's test module
already describe for Mz -- a synthetic "true" `Kx3` of the opposite sign
from `p0` sent the optimizer to a badly-fitting local minimum in testing;
the test fixture's true coefficients were chosen close in sign/magnitude
to `p0` to avoid exercising that unrelated sensitivity. Full suite:
**124 passed** (117 before this change + 7 new).

Also run end-to-end against real `RawDataFiles/BrakeDrive/` data for all
three 18x6-10 tires (R20, LCO, R25B) via `run_longitudinal_fit` +
`pacejka.regression.fit_quality_table_fx` (new, mirroring
`fit_quality_table`). This surfaced two real pre-existing robustness
gaps in `pacejka.detection` (used identically by the Fy/Mz cornering
pipeline, not new to Fx), both fixed the same way -- a candidate level
is only reported as "detected" if it would actually survive the
downstream per-condition check, not just a coarser detection-time one:
- `detect_fz_levels` accepted any candidate with >= `min_samples` raw
  samples, with no check that the swept channel (SL/SA) had more than
  one distinct value. On R20's BrakeDrive data, Fz=100 and Fz=350 lbf
  each matched a brief transient/calibration segment (1-2 distinct SL
  values, well short of a real sweep) that happened to clear
  `min_samples` on sample count alone, crashing `csaps` downstream
  (`'xdata' must contain at least 2 data points'`) once the pipeline
  tried to spline-fit it. Fixed by also requiring `nunique() >= 2` on
  the swept channel; `pacejka.quality.check_condition_quality` gained
  the same check (as a hard error, not just the existing range warning)
  as defense in depth for any caller that bypasses detection with an
  explicit `fz_noms`.
- `detect_camber_levels` rounds raw IA readings to the nearest degree
  and accepts any bucket with >= `min_samples` points -- but that
  rounding bucket (+/-0.5 deg by default) is much wider than
  `para_range`'s real IA acceptance band (+/-0.075 deg), so a transient
  reading while the rig settles between two real camber sweeps can clear
  `min_samples` in the coarse bucket while having almost none in the
  tight band `segment_condition` actually uses downstream. Confirmed on
  LCO's BrakeDrive data: a spurious "IA=1 deg" cluster (33 points
  rounded-bucket, real sweep was 0/2/4 deg) had only 5 points in the real
  band -- enough to pass detection, not enough to fit, raising
  downstream instead of being excluded at detection time. Fixed by
  re-checking each rounded candidate with the real `ia_nom`/`min_samples`
  semantics before reporting it as detected.

With both fixes, all three tires auto-detect clean load/camber sweeps
and fit well: LCO and R25B both land on the real 4-point load sweep
(50/150/200/250 lbf) with R^2 >= 0.95 at every load and >= 0.998 at
every camber. R20 additionally has real (not transient -- 2+ distinct
SL values, not caught by either fix above) data at Fz=100 lbf, but its
R^2 there (0.65) and at Fz=50 lbf (0.77) are noticeably worse than the
150-250 lbf range (>= 0.996) or either of the other two tires' Fz=50
fits -- flagged as an open item for the team to look into (possibly a
genuinely noisier low-load condition in this specific round, or a
dFz-stage identifiability issue specific to having 5 load points instead
of 4), not something this change attempts to diagnose further.

**Not changed:** The combined-slip Fx/Fy stages (deferred, quirk #24);
`Raw_Data_Fitter_Mx_V2.m`/`Pacejka_Term_Finder_MX_V1.m` (still unported);
anything in the Fy/Mz cornering pipeline.

---

## 2026-10-06 -- Fit Base and dIA jointly instead of staged, for both Fy and Mz

**What:** `pacejka/fitters/mz.py`'s `fit_mz_coefficients` and
`pacejka/fitters/fy.py`'s `fit_fy_coefficients` no longer fit the Base
coefficients alone (against only the single zero-camber reference
condition) and then freeze them before fitting the dIA coefficients
(against the camber sweep). They now fit Base and dIA *jointly*, in one
optimization, against the reference condition plus the full camber sweep
together. The dFz stage is unchanged in both files -- same fields,
bounds, loss function, and load-sweep data as before, run as its own
stage afterward, just starting from the jointly-fit Base values instead
of a Base fit that never saw camber data.

**Why:** the original MATLAB term finders (and this port, until now)
always staged Base before dIA, so Base's coefficients were chosen with
zero regard for anything off-camber -- by the time dIA ran, it was stuck
correcting around values that were never asked to accommodate camber
variation. This was investigated at length in `research/` (see that
folder's `OPTIMIZATION_NOTES.md` for the full experiment log, including
two approaches that were tried and rejected first):

- Fitting *all* coefficients (Base, dFz, and dIA) jointly in one pass
  fixed Mz's camber sweep but cost real load-sweep accuracy, since the
  load sweep ended up competing with the camber sweep in the same
  unweighted objective.
- Weighting that joint objective by each condition's own scale recovered
  some of the load-sweep accuracy but overcorrected, visibly clipping
  the high-load peaks.
- Fitting Base+dIA jointly while leaving dFz as its own untouched stage
  (this change) avoided both problems, because the load sweep never has
  to compete with anything -- it keeps its own dedicated stage exactly
  as production always ran it.

**Verified with:** two real tires (R20 16x7.5, LCO 16x7.5, both from the
bundled `RawDataFiles`) and the synthetic fixture in
`tests/unit/test_regression.py`. Mz's camber sweep improves
substantially on both tires (R20: IA=2° R² 0.894->0.970, IA=4°
0.750->0.971; LCO's camber sweep was already good, and still improved
slightly). Fy improves slightly across several conditions on both tires
(e.g. LCO Fz=250 lbf RMSE 17.5->3.5) despite having no camber-sweep
problem to fix, and was never worse. The one place a small cost showed
up -- R20's Mz load sweep dips by 0.001-0.013 R² -- was traced to
`Bz9`/`Bz10` (the residual-moment stiffness term, which has no
dIA-stage correction term of its own) shifting substantially to also
explain the camber sweep; see `research/OPTIMIZATION_NOTES.md`'s
2026-10-02 entry for the full coefficient-level comparison. No
regression found on any other condition, either tire, either equation.
All 117 existing tests pass unmodified -- the staging order was never
something any test depended on.

**Not changed:** the dFz stage's own fields, bounds, data, or loss
function, in either file. `Dz2` staying pinned to `0.0` (quirk from the
2026-10-01 entry below) and the deferred cross-term coefficients
(`Hz4`/`Dz9`/`Dz11` for Mz, `Ky7`/`Vsy4` for Fy) are unaffected by this
change -- they're still never fit, for the same reasons as before.

---

## 2026-10-01 -- Pinned the dead `Dz2` parameter; investigated and reverted widening the dIA/Base-stage bounds

**Context:** after the smoothing fix below, a real R20 16x7.5 fit (team's
own bundled `RawDataFiles` cornering runs) still looked visibly off at
higher loads on the Mz vs. slip-angle plot, so this was investigated
against that real data rather than just the synthetic test fixture.

**What (kept):** `pacejka/fitters/mz.py`'s dFz stage no longer fits
`Dz2` -- it's pinned to `0.0` in `fit_mz_coefficients`, the same
treatment as the already-deferred `Hz4`/`Dz9`/`Dz11` cross-term
coefficients.

**Why:** Traced a previously-undocumented issue back to the original
MATLAB source itself (`Pacejka_Term_Finder_MZ_V1_redo.m`): `Dz2` is
declared as a free dFz-stage parameter (`qstat.Dz2 = [0 1 0 0 0]`), but
every `Dto` formula in the file (`BaseFit.Dto`, `dFzFit.Dto`, etc.) uses
`Xb(7) + Xf(5)*dfz` -- `Dz1 + Dz7*dfz` -- and never references `Dz2` at
all. Confirmed on the real R20 data: the fitted `Dz2` came back as an
arbitrary, meaningless value (`-38.45`) with zero relationship to fit
quality, since the residual has no gradient with respect to it. Not a
porting bug -- `pacejka/model.py`'s `mz_pure` faithfully matches the
original's formula -- but it was silently wasting one of only 7
dFz-stage degrees of freedom on a parameter the model can't use. Pinning
it to `0.0` is honest about that rather than reporting a fitted value
that means nothing.

**Impact:** Verified via `tests/unit/test_mz_term_finder.py` (new test:
`test_dz2_is_always_zero_not_fit`) and by re-running the real R20 fit:
removing `Dz2` from the free parameters changes nothing measurable in
fit quality (R² identical to 5 decimal places), as expected for a
parameter that was never affecting the residual in the first place --
this is a correctness/honesty fix, not an accuracy improvement.

**What (investigated, then reverted):** the real R20 fit also pegs
`Hz1` (Base stage) and `Hz3`/`Bz5`/`Dz4` (dIA stage) exactly at their
original MATLAB bounds, which looked at first like the same class of
problem as FY's `Ky1` bounds (CLAUDE.md quirk #9) -- bounds copied from
MATLAB without validation against real data, capping an otherwise-better
fit. Widening them (tried `(-0.05, 0.05)` for the two shift terms,
`(-50, 50)` for `Bz5`/`Dz4`) turned out to be the wrong read: re-running
the real fit with much wider bounds (±1 and ±200) showed these
parameters don't converge to an interior optimum at all -- they run
straight to whatever bound they're given. That's the signature of
under-identification, not an overly tight bound: with only 3 tested
camber angles (0/2/4 deg) fitting 7 dIA-stage parameters, several of
which multiply different functions of gamma, the data doesn't actually
pin these coefficients down independently of each other. The original
MATLAB bounds are inadvertently acting as a regularizer here. This was
also confirmed destabilizing the synthetic fixture's fit quality
(`tests/unit/test_regression.py`), which was the tell that something was
wrong with the widening rather than with the original bounds. **Reverted
to the original MATLAB bounds** for `Hz1`, `Hz3`, `Bz5`, and `Dz4`.
Genuinely resolving this needs either a richer camber sweep (more than 3
tested angles) or a reparameterization that reduces how many dIA-stage
terms compete for the same information -- not a wider bracket. Flagged
here, not in CLAUDE.md's quirks list, since it's not a MATLAB-source
quirk -- it's a real identifiability limitation of this fitting stage
given realistic test data, worth knowing before anyone else tries the
same "just widen the bound" fix.

**Verified with:** full `pytest` suite (117 passed) and the real R20
16x7.5 fit's `fit_quality_table` before/after, at each step of the
investigation above.

---

## 2026-09-29 -- Reverted Mz spline over-smoothing (`_MZ_SMOOTHING_PARAM`)

**What:** `pacejka/fitters/mz.py`'s `_MZ_SMOOTHING_PARAM` changed from
`0.999` back to `0.75`.

**Why:** The app's Mz vs. slip-angle plots looked visibly ill-fitted.
Diagnosed via `pacejka.regression.fit_quality_table` against the
synthetic fixture in `tests/unit/test_regression.py`: at `0.999`,
`csaps`'s smoothing spline is close to pure interpolation (in its
Reinsch `p`-in-`[0,1]` formulation, `p` near 1 means almost no
smoothing), so the spline the Magic Formula gets fit against tracks raw
measurement noise instead of the underlying curve. Reverting to `0.75`
-- the original MATLAB `Raw_Data_Fitter_Mz_V2.m`'s own hand-tuned value,
per `CLAUDE.md`'s "Fitting stack" note -- fixed it:

| Condition | R² at 0.999 | R² at 0.75 |
|---|---|---|
| Fz=100 lbf | 0.835 | 0.986 |
| Fz=50 lbf | 0.954 | 0.981 |
| Fz=250 lbf | 0.992 | 0.998 |
| Fz=200 lbf | 0.992 | 0.999 |
| Fz=150 lbf / IA conditions | ~0.999 | ~0.9998 |

Lower-load conditions were hit hardest, since Mz's absolute signal is
smaller there, so the same noise floor eats a bigger share of the curve.
0.9 and 0.5 were also tried as sanity checks: 0.9 was actually *worse*
than 0.999 for the low-load conditions (non-monotonic, an unstable
region for this spline), while 0.5 performed about the same as 0.75. 0.75
was chosen over 0.5 specifically because it's the original tool's actual
tuned value, not a new number picked to fit this one synthetic test.

**How this regressed:** `_MZ_SMOOTHING_PARAM` was `0.75` when this
module was first ported, then changed directly on `main` to `0.999` at
some point without a PR. The likely explanation: `pacejka/fitters/fy.py`
has its own, separate `_SMOOTHING_PARAMS["MZ"] = 0.999` -- a legitimately
different value, for `Raw_Data_Fitter_Fy_V3.m`'s own internal MZ-channel
smoothing (part of `fit_alpha_sweep`, not the actual Mz-vs-SA fit the app
plots). It looks like that value was copied into the wrong file's
constant. This file's fix only touches `pacejka/fitters/mz.py`;
`fy.py`'s `_SMOOTHING_PARAMS["MZ"]` is untouched since it's a distinct,
correctly-tuned value for a different purpose.

**Verified with:** `tests/unit/test_regression.py::test_a_good_fit_has_high_r_squared`,
which had been failing (Mz Fz=100 lbf R² = 0.835, below the test's 0.9
threshold) since the `0.999` change landed -- now passes.

---

## Earlier changes (backfilled)

These predate this file's creation; backfilled here since they're
exactly the kind of physics/math decision this log is meant to capture.
Fuller technical detail for each is in the `CLAUDE.md` quirk cited.

- **Mz residual-moment shifted slip angle (`alpha_r` vs. `alpha_t`)** --
  `pacejka/model.py`'s `mz_pure` uses `alpha_r` (the FY-derived shifted
  angle) in the residual-moment term, where the original MATLAB
  (`Pacejka_Term_Finder_MZ_V1_redo.m`) used `alpha_t` (the trail-specific
  shift) in both the trail *and* residual terms -- a copy-paste bug, since
  `alpha_r` is computed but never referenced anywhere else in that file.
  Fixed per the standard, documented MF-Tire 6.1 formulation, which uses
  the two shifted angles for two different terms. Produces a materially
  different (multiple-times-larger) result, not a rounding difference.
  See CLAUDE.md quirk #13.

- **FY Base-stage `Ky1` bounds widened** -- the original's bounds
  (`[-70, -50]`) excluded its own initial guess (`175.5`) and had the
  wrong sign for a physically sane cornering stiffness. Widened to a
  permissive `[0, 1000]` in `pacejka/fitters/fy.py` that at least contains
  the correctly-signed initial guess -- flagged as needing real
  domain-informed re-tuning, not treated as a validated final choice.
  See CLAUDE.md quirk #9.

- **FY `dFz` (load-sensitivity) stage given a real multi-load sweep** --
  the original hardcoded a single load (`Fz_vals = [50]`) for every fit
  regardless of what load was requested, so the load-sensitivity terms
  (`Dy2`, `Ey2`, `Hsy2`, `Vsy2`) were never actually identifiable from
  data spanning more than one load. `pacejka/fitters/fy.py`'s
  `fit_fy_coefficients` takes a real `load_sweep` argument spanning every
  tested load instead. See CLAUDE.md quirks #7 and #10 (the `dFz` stage
  also had an independent lbf->N unit-conversion bug, fixed at the same
  time).

- **FY `dIA` (camber-sensitivity) stage given a real multi-camber
  sweep** -- the original hardcoded zero camber (`gamma_vals = [0]`),
  making every camber-sensitivity term's contribution identically zero
  during fitting -- pure optimizer noise, not a real fit.
  `fit_fy_coefficients`'s `camber_sweep` argument spans multiple tested
  camber angles instead. See CLAUDE.md quirk #11.

- **FY/MZ load x camber cross-terms deferred, not fit from unidentifiable
  data** -- fixing the `dFz`/`dIA` stages above still leaves the
  load-camber cross term (e.g. `Ky7`, `Vsy4` in FY; `Hz4`, `Dz9`, `Dz11`
  in MZ) unidentifiable, since that needs data at combined off-nominal
  load *and* camber simultaneously, which nothing in the pipeline
  collects yet. Decided with the user: these coefficients are left at
  `0.0` rather than fit from data that structurally can't support them,
  or carrying forward the original's arbitrary, never-validated initial
  guess. Real cross-term support needs genuine multi-dimensional (Fz x
  IA) sweep data -- a follow-up task, not in scope now. See CLAUDE.md
  quirks #12 and #16.

- **MZ `dFz` and `dIA` stages given real sweeps, same reasoning as FY** --
  `Pacejka_Term_Finder_MZ_V1_redo.m` had the same class of bug as FY's,
  independently: `Fz_vals = Fz_nom` (identically zero `dfz` throughout)
  and a single hardcoded nonzero camber. `pacejka/fitters/mz.py`'s
  `fit_mz_coefficients` takes real `load_sweep` and `camber_sweep`
  arguments instead. See CLAUDE.md quirks #14 and #15.
