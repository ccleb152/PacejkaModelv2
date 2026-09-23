"""Tests for pacejka.feedback. Not a MATLAB port, so plain unit tests."""

import csv
from datetime import datetime, timezone

from pacejka.feedback import FEEDBACK_CSV_NAME, submit_feedback


def test_creates_the_file_with_a_header_on_first_submission(tmp_path):
    path = submit_feedback(tmp_path, "Ada", "Loved the color grouping!")
    assert path == tmp_path / FEEDBACK_CSV_NAME
    assert path.exists()

    with path.open(newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["timestamp", "name", "feedback"]
    assert rows[1][1] == "Ada"
    assert rows[1][2] == "Loved the color grouping!"


def test_appends_without_duplicating_the_header(tmp_path):
    submit_feedback(tmp_path, "Ada", "First comment")
    submit_feedback(tmp_path, "Grace", "Second comment")

    with (tmp_path / FEEDBACK_CSV_NAME).open(newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["timestamp", "name", "feedback"]
    assert len(rows) == 3  # header + 2 submissions
    assert rows[1][1] == "Ada"
    assert rows[2][1] == "Grace"


def test_creates_the_root_folder_if_missing(tmp_path):
    nested = tmp_path / "does" / "not" / "exist" / "yet"
    submit_feedback(nested, "Ada", "hello")
    assert (nested / FEEDBACK_CSV_NAME).exists()


def test_uses_the_given_timestamp(tmp_path):
    fixed = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    submit_feedback(tmp_path, "Ada", "hello", timestamp=fixed)

    with (tmp_path / FEEDBACK_CSV_NAME).open(newline="") as f:
        rows = list(csv.reader(f))
    assert rows[1][0] == "2026-01-02T03:04:05+00:00"


def test_feedback_containing_commas_and_newlines_round_trips(tmp_path):
    tricky = "Line one, with a comma.\nLine two."
    submit_feedback(tmp_path, "Ada", tricky)

    with (tmp_path / FEEDBACK_CSV_NAME).open(newline="") as f:
        rows = list(csv.reader(f))
    assert rows[1][2] == tricky
