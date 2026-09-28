# Alabama FSAE PacejkaModelv3
Alabama FSAE Tire Model version 3

Created by: CC LeBlanc

Last Updated: 09/22/2026

Python port of the team's Pacejka Magic Formula tire-fitting toolchain
(originally MATLAB). Loads raw TTC round data, fits Magic Formula
coefficients across every tested load and camber angle, and shows the
results in a Streamlit app.

## Running the app

**No terminal required.** Just double-click the launcher for your OS:

- Windows: `run_windows.bat`
- Mac: `run_mac.command`
- Linux: `run_linux.sh`

The first time you run it, it sets up everything it needs automatically
(this can take a minute or two — you'll see some setup text). Every time
after that, it starts in a few seconds. Once it's ready, the app opens in
your browser.

**Requirement:** Python 3.11 or later must be installed on your computer.
If it isn't, the launcher will tell you and point you to
[python.org/downloads](https://www.python.org/downloads/). On Windows,
make sure to check "Add python.exe to PATH" during install.

**Mac only:** the first double-click may bring up a warning that the file
is from an "unidentified developer." Right-click (or Control-click) the
file → **Open** → **Open** once to allow it — after that, double-clicking
works normally.

**Linux only:** double-click support depends on your file manager. If
double-clicking opens the script in a text editor instead of running it,
either enable "Allow executing file as program" in the file's properties,
or run `chmod +x run_linux.sh && ./run_linux.sh` once from a terminal.

## One-time setup: your tire-data folder

The app needs to know where your tire-testing data lives on your
computer (e.g. your locally-synced OneDrive/SharePoint folder). The first
time you open the app, use the sidebar to point it at that folder — it
remembers this afterward, so you only do it once per computer.

## What it does

1. Load a raw TTC round (browse your configured data folder, or upload a
   file directly).
2. The app auto-detects every load and camber angle tested in that round.
3. Run the fit — it fits the Magic Formula coefficients across the full
   sweep automatically.
4. Review the Fy/Mz vs. slip-angle plots and fitted coefficient tables.
5. Export the fitted coefficients (CSV) and graphs to a folder of your choice.

## Distributing this to your team

This whole project folder is meant to live inside a **team-shared OneDrive
folder**, not to be cloned from git by each teammate:

1. Put this folder inside your team's shared OneDrive (or move it there
   once, if you're reading this from a git checkout).
2. Share that OneDrive folder with your teammates. Once they accept, their
   own OneDrive client syncs it down to their computer automatically.
3. Each teammate needs Python 3.11+ installed once (see the Requirement
   above) — after that, they just double-click the launcher for their OS.
4. Everyone reads/writes the same synced `RawDataFiles/` tire database and
   `Feedback/feedback.csv` file, since OneDrive syncs any changes back out
   to the rest of the team.

**Why the app still works smoothly even though it lives in a synced
folder:** the launchers deliberately create each teammate's Python virtual
environment *outside* this folder (under their own account's local
app-data directory, e.g. `%LOCALAPPDATA%` on Windows) instead of inside
it. A venv is hundreds of megabytes of small files tied to one specific
Python install, so if it lived inside the synced folder, OneDrive would
try to sync one teammate's (unusable, machine-specific) venv onto
everyone else's computer. Keeping it out of the synced folder means every
teammate gets their own working venv, built once, and OneDrive only ever
has to sync the actual app code and data.

## For developers

See `CLAUDE.md` for the MATLAB → Python migration conventions and known
source-code quirks, and `MIGRATION_PLAN.md` for the translation plan.
Running the test suite requires the dev dependencies:

```
pip install -r requirements.txt
pytest
```

See `tools/README.md` for the feedback-to-GitHub-Issues sync script and
the automated triage Routine that watches for new feedback issues.
