"""Team feedback capture.

Not a MATLAB port -- the original tool has no equivalent. Appends one row
per submission to a plain CSV file rather than a database: this app's
whole folder is expected to live inside the team's synced OneDrive (see
CLAUDE.md), so a plain file write here reaches every teammate through
OneDrive's own sync the moment it's saved -- no server, no commit, no
push. The file is deliberately *not* git-tracked (see .gitignore): it
changes on every submission, and if it were tracked, every submission
would show up as an uncommitted change, and two people submitting around
the same time would produce a real git merge conflict rather than just
an OneDrive "conflicted copy." Only the containing `Feedback/` folder
itself is tracked (via a placeholder file), so the path always exists on
a fresh checkout.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

FEEDBACK_CSV_NAME = "feedback.csv"
_FIELDNAMES = ("timestamp", "name", "feedback")


def submit_feedback(root: Path | str, name: str, feedback: str, timestamp: datetime | None = None) -> Path:
    """Append one feedback submission to `root/feedback.csv`, creating the
    folder and the file (with a header row) if they don't exist yet.

    `timestamp` defaults to now (UTC) -- exposed as a parameter mainly so
    tests can pass a fixed value. Returns the path written to.
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    csv_path = root / FEEDBACK_CSV_NAME
    is_new = not csv_path.exists()

    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
        if is_new:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": timestamp.isoformat(timespec="seconds"),
                "name": name,
                "feedback": feedback,
            }
        )
    return csv_path
