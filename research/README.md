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
loaders in `pacejka.fitters.*`) rather than modifying them in place, and
rather than reaching into their private `_`-prefixed internals. That
keeps every experiment self-contained and easy to compare against the
production behavior side by side.

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
