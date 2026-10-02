# Optimization technique notes

A running log of fitting/optimization approaches tried in `research/`,
what happened, and whether they're worth carrying into the production
`pacejka/fitters/` code. This is the research-side counterpart to
`MODEL_CHANGES.md` at the repo root: `MODEL_CHANGES.md` records changes
actually made to the deployed model and why; this file records
*experiments* -- including the ones that didn't pan out -- so nobody
re-runs an experiment that's already been tried, and so the reasoning
behind "we looked at X and decided not to use it" isn't lost.

Add an entry here every time a new fitting/optimization approach is
tried, whether or not it ends up adopted. Each entry should have enough
detail that someone could reproduce the comparison without re-deriving
the setup from scratch.

---

## Tried

### Joint (simultaneous) least-squares fit vs. the production staged fit

- **Script:** `research/mz_joint_vs_staged_fit.py`
- **Date:** 2026-10-02
- **What:** The production `pacejka/fitters/mz.py` fits Mz coefficients
  in three sequential stages (Base -> dFz -> dIA), each freezing the
  previous stage's results. This experiment instead fits every
  non-deferred coefficient in one `scipy.optimize.least_squares` call
  against all conditions (load sweep + camber sweep) at once, using the
  same field list, bounds, and initial guesses as the staged approach
  for a fair comparison.
- **Result (R20 16x7.5, real TTC data):** Joint fitting dramatically
  improved the camber sweep, which the staged approach handled badly:

  | Condition | Staged R² | Joint R² |
  |---|---|---|
  | Fz=50 lbf | 0.699 | 0.475 (worse) |
  | Fz=100 lbf | 0.925 | 0.841 (worse) |
  | Fz=150-250 lbf | 0.966-0.986 | ~unchanged |
  | IA=2 deg | 0.894 | **0.965** |
  | IA=4 deg | 0.750 | **0.961** |

  It did this by letting the camber-sensitive coefficients draw on the
  full 8-condition dataset instead of being stuck with whatever the
  Base stage already froze at the single reference condition -- but at
  the cost of the lower loads, which the staged approach's dedicated
  dFz stage actually handled reasonably well on its own.
- **Likely cause of the load-sweep regression:** an *unweighted* joint
  objective sums squared residuals in raw N*m across every condition.
  The 250 lbf condition's curve peaks around 10x higher than the 50 lbf
  condition's, so it contributes far more to the total sum of squares --
  the optimizer effectively prioritizes fitting the big curve well over
  the small one, once they're competing in the same objective.
- **Decision: not adopted as-is.** Net result is a reallocation, not a
  clear win -- it trades a known weakness (under-identified camber
  sensitivity) for a new one (unbalanced load-sweep accuracy). Promising
  enough to keep investigating, not ready to replace the staged fit in
  `pacejka/fitters/mz.py`.
- **Next step identified:** try the same joint fit with each
  condition's residual normalized by its own scale (e.g. divide by that
  condition's peak |Mz| before computing the sum of squares) so the
  250 lbf condition can't drown out the 50 lbf one. Hypothesis: this
  could recover the camber-sweep improvement without losing load-sweep
  accuracy. Not yet tried.

### Joint (simultaneous) least-squares fit vs. staged -- for Fy, checking whether the Mz trend generalizes

- **Script:** `research/fy_joint_vs_staged_fit.py`
- **Date:** 2026-10-02
- **What:** Same question as the Mz experiment above, same structure,
  same tire (R20 16x7.5) -- does joint fitting trade load-sweep accuracy
  for camber-sweep accuracy here too, or was that an Mz-specific result?
  Uses `pacejka.fitters.fy`'s actual field/bound tables (the dFz-stage
  fields are unconstrained in production, matching MATLAB's `nlinfit`,
  so they're given `(-inf, inf)` bounds here rather than an invented box
  constraint) and fits plain least squares throughout (no robust loss,
  even though production uses `robust=True` for Fy's dFz stage) so the
  staged-vs-joint comparison isn't confounded with a loss-function
  change.
- **Result: does NOT replicate the Mz trend -- in fact closer to the
  opposite.** The staged Fy fit is already excellent everywhere (R²
  0.993-0.9999, both load and camber sweeps), unlike Mz's staged fit,
  where the camber sweep specifically was weak. Joint fitting has
  nothing to gain there and real room to lose:

  | Condition | Staged R² | Joint R² |
  |---|---|---|
  | Fz=50 lbf | 0.994 | 0.805 (worse) |
  | Fz=100 lbf | 0.999 | 0.927 (worse) |
  | Fz=150 lbf | 0.9999 | 0.994 (worse) |
  | Fz=200 lbf | 0.999 | **0.481** (much worse) |
  | Fz=250 lbf | 0.997 | 0.919 (worse) |
  | IA=2 deg | 0.9998 | 0.997 (slightly worse) |
  | IA=4 deg | 0.9998 | 0.9995 (slightly worse) |

  Every condition got worse under joint fitting, load sweep severely so
  (Fz=200 lbf visibly collapses toward a near-flat line in the plot) and
  camber sweep only marginally (it had almost no room to improve, being
  already near-perfect).
- **Why the trend doesn't generalize:** the Mz camber-sweep win wasn't a
  generic property of joint fitting -- it was specific to Mz's dIA stage
  being badly under-identified in the staged approach (see the Mz entry
  above and `MODEL_CHANGES.md`'s 2026-10-01 entry). Fy's dIA stage
  doesn't have that problem on this tire's real data, so joint fitting
  has no weakness to fix there, and the same "everything competes in one
  unweighted objective" effect that helped Mz's camber sweep just costs
  Fy's already-good load sweep instead.
- **Decision: not adopted.** Clearly worse than the staged fit for Fy on
  this data. Confirms that "joint vs. staged" isn't a one-size-fits-all
  answer -- it depends on which stage is actually under-identified in the
  staged approach for a given equation, not something to apply uniformly
  to both Fy and Mz.

---

## Candidates not yet tried

Ideas raised in discussion but not yet implemented as an experiment.
Move an entry to "Tried" (with a script and results) once it's actually
run, rather than editing it in place here.

- **Weighted/normalized joint fit** -- see "Next step identified" above.
  The most immediate follow-up to the joint-fit experiment.
- **Multi-start / global search** (`scipy.optimize.differential_evolution`,
  basin-hopping, or just several randomized local refinements from
  different initial guesses). Motivation: the current fit uses a single
  generic `p0=1` initial guess per coefficient (not domain-tuned), and
  `tests/unit/test_mz_term_finder.py`'s own docstring already notes this
  equation's fit is sensitive to initial conditions even on noise-free
  synthetic data. Multi-start would show whether the staged/joint fits
  above are actually landing near the best achievable optimum, or stuck
  in a worse local one.
- **Soft regularization instead of hard bounds.** The dIA-stage
  under-identification found in `MODEL_CHANGES.md`'s 2026-10-01 entry
  showed that widening hard bounds just lets an under-determined
  parameter run to whatever bound it's given, rather than finding a
  better interior value. A soft penalty (e.g. pulling a coefficient back
  toward its `p0` the further it strays) might behave better for
  genuinely under-determined parameters than a box constraint, without
  either silently capping a real fit (the old `Ky1` problem) or letting
  an under-identified one run away (the `Hz1`/`Hz3`/`Bz5`/`Dz4` problem).
- **Weighted/robust loss for the load sweep specifically** -- `pacejka`'s
  FY dFz stage already uses `robust=True` (see `pacejka/fitting.py`);
  worth checking whether the same robust loss would help the Mz dFz
  stage or the joint fit's load-sweep weighting problem above.
