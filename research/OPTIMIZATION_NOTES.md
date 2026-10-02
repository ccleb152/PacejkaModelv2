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
