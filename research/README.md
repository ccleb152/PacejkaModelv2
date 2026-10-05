# research/

Experimental tire-model work: new fitting methods, new equations, and
eventually longitudinal (Fx) modeling and load extrapolation/
interpolation studies. This is a sandbox for trying things out and
seeing the result yourself before anything here is considered for the
deployed app.

## The isolation guarantee

Nothing under `research/` is imported by `app/` or by anything the
double-click launcher scripts run. The deployed app only ever touches
`pacejka/` and `app/` as they exist on `main`. You can run, break, and
rewrite anything in here without any risk to what the team is using.

This folder lives on its own branch (`research/mz-fitting-experiments`,
or whatever branch you're currently on -- check `git branch`), not on
the app's deployment branch, and isn't merged into `main` automatically.
If and when something in here proves out, promoting it means a
deliberate, separate change to the actual `pacejka/` module it affects
(with the usual tests, and a `MODEL_CHANGES.md` entry) -- copying a
research script's logic in, not merging this branch wholesale.

## How scripts here are structured

Each script imports `pacejka`'s existing public, stateless functions
directly (`pacejka.model.mz_pure`, `pacejka.model.MzCoefficients`, the
loaders in `pacejka.fitters.*`) rather than modifying them in place.
They don't *modify* any production module's private internals either --
but a script comparing against the production fit may still *import* a
module's private field/bound tables (e.g. `pacejka.fitters.mz`'s
`_BASE_FIELDS`/`_BASE_BOUNDS`) read-only, specifically so the comparison
uses the exact same coefficients/bounds/initial guesses as production
rather than a hand-copied approximation of them. Each script's docstring
says when and why it does this.

Scripts read real data from `RawDataFiles/` (the bundled Calspan
reference set) or your own configured data root
(`pacejka.config.get_data_root`), and write plots to
`research/output/` (gitignored -- regenerate, don't commit, plot
images).

## Current experiments

- `mz_joint_vs_staged_fit.py` -- compares the current staged
  Base -> dFz -> dIA least-squares fit (`pacejka.fitters.mz`'s actual
  production approach) against a joint fit that optimizes all Mz
  coefficients simultaneously against the full multi-condition dataset
  at once. See the script's own docstring for the motivation and how to
  read its output.
- `fy_joint_vs_staged_fit.py` -- same comparison, for Fy. See
  `OPTIMIZATION_NOTES.md` -- the result does NOT match Mz's (joint
  fitting helped Mz's camber sweep but hurts Fy across the board), which
  is itself the useful finding: it's not a generic property of joint
  fitting, it depends on which stage is actually under-identified for a
  given equation.
- `mz_partial_staged_fit.py` / `fy_partial_staged_fit.py` -- the
  follow-up that actually works: keep the production dFz (load-sweep)
  stage completely unchanged, but fit Base+dIA jointly against the
  reference condition plus the full camber sweep instead of staging them
  sequentially. Fixes Mz's camber-sweep weakness with no load-sweep
  cost, and even improves Fy slightly despite Fy having no camber-sweep
  problem to fix. Checked against two real tires (R20 16x7.5, LCO
  16x7.5) with no regression found on either equation -- **recommended
  for promotion to `pacejka/fitters/mz.py` and `fy.py`**. See
  `OPTIMIZATION_NOTES.md` for the full numbers.

See `OPTIMIZATION_NOTES.md` for the running log of what's been tried,
what the results were, and whether each approach is worth carrying into
production -- including ideas raised but not yet implemented.
