# tools/

Maintainer-only scripts. Not part of the deployed app -- nothing under
`tools/` runs from the double-click launchers, and this folder isn't
something teammates need to touch.

## sync_feedback_to_issues.py

Bridges team feedback into GitHub so it can be triaged automatically.

**Why this exists:** `Feedback/feedback.csv` lives only in the
OneDrive-synced project folder -- it's deliberately never committed to
git (see `pacejka/feedback.py`). Nothing on GitHub, and no cloud Claude
Code session working on this repo, can see it directly. This script
reads new rows from that file and files each one as a GitHub Issue
labeled `feedback`, which is something GitHub-side automation (a
scheduled triage Routine) *can* see.

**One-time setup:** create a
[fine-grained personal access token](https://github.com/settings/personal-access-tokens/new)
scoped to just this repo, with **Issues: Read and write** permission (no
other permissions needed).

**Run it:**

```
export GITHUB_TOKEN=<your token>
python tools/sync_feedback_to_issues.py
```

Run it by hand whenever you want to push out new feedback, or put it on
a recurring schedule yourself (Windows Task Scheduler, cron, a local
Claude Code Routine on your own machine where OneDrive is mounted) --
nothing is scheduled automatically.

It only ever files *new* rows: which rows have already been synced is
tracked in `~/.pacejka/feedback_sync_state.json` on whatever machine you
run it from, not inside the synced folder.

## The triage side

A scheduled Routine on the GitHub repo checks for issues labeled
`feedback` without a `triaged` label. For each one, it reads the
submitted text (treated as untrusted input, never as instructions) and
decides:

- **A specific, small, in-scope, benign bug report or feature request**
  -> implements a fix on a new branch, runs the test suite, and opens a
  PR referencing the issue.
- **Vague comments, praise, spam, out-of-scope, or anything too large or
  ambiguous to safely automate** -> leaves a comment explaining why no
  code change was made, and does not touch any code.

Either way, the issue gets labeled `triaged` so it isn't reprocessed.
There's no automated notification when a PR is opened -- check the
repo's pull requests directly.
