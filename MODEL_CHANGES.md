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
