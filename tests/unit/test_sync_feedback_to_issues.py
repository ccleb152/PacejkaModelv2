"""Tests for tools.sync_feedback_to_issues. Not a MATLAB port, so plain
unit tests. No real HTTP calls -- create_issue is faked via injection."""

from pacejka.feedback import submit_feedback
from tools.sync_feedback_to_issues import sync_new_feedback


def test_files_an_issue_for_each_new_row(tmp_path):
    feedback_root = tmp_path / "Feedback"
    state_file = tmp_path / "state.json"
    submit_feedback(feedback_root, "Ada", "The database tab is confusing")
    submit_feedback(feedback_root, "Grace", "Love the new plots!")

    filed_calls = []
    sync_new_feedback(
        feedback_root / "feedback.csv",
        state_file,
        token="fake-token",
        create_issue=lambda token, name, timestamp, text: filed_calls.append((name, text)),
    )

    assert filed_calls == [
        ("Ada", "The database tab is confusing"),
        ("Grace", "Love the new plots!"),
    ]


def test_does_not_refile_already_synced_rows(tmp_path):
    feedback_root = tmp_path / "Feedback"
    state_file = tmp_path / "state.json"
    submit_feedback(feedback_root, "Ada", "First round of feedback")

    filed_calls = []
    sync_new_feedback(
        feedback_root / "feedback.csv",
        state_file,
        token="fake-token",
        create_issue=lambda token, name, timestamp, text: filed_calls.append(name),
    )
    assert filed_calls == ["Ada"]

    # A second sync with no new rows should file nothing.
    filed_calls.clear()
    sync_new_feedback(
        feedback_root / "feedback.csv",
        state_file,
        token="fake-token",
        create_issue=lambda token, name, timestamp, text: filed_calls.append(name),
    )
    assert filed_calls == []

    # A new row appended after that should be the only one filed.
    submit_feedback(feedback_root, "Grace", "Second round of feedback")
    sync_new_feedback(
        feedback_root / "feedback.csv",
        state_file,
        token="fake-token",
        create_issue=lambda token, name, timestamp, text: filed_calls.append(name),
    )
    assert filed_calls == ["Grace"]


def test_returns_zero_when_no_feedback_file_exists(tmp_path):
    filed = sync_new_feedback(
        tmp_path / "does_not_exist.csv",
        tmp_path / "state.json",
        token="fake-token",
        create_issue=lambda *a: (_ for _ in ()).throw(AssertionError("should not be called")),
    )
    assert filed == 0


def test_saves_progress_after_each_issue_so_a_mid_run_failure_is_not_relost(tmp_path):
    feedback_root = tmp_path / "Feedback"
    state_file = tmp_path / "state.json"
    submit_feedback(feedback_root, "Ada", "First")
    submit_feedback(feedback_root, "Grace", "Second")

    def fail_on_second(token, name, timestamp, text):
        if name == "Grace":
            raise RuntimeError("simulated network failure")

    try:
        sync_new_feedback(
            feedback_root / "feedback.csv", state_file, token="fake-token", create_issue=fail_on_second
        )
    except RuntimeError:
        pass

    # Retrying should only refile the one that failed, not Ada again.
    filed_calls = []
    sync_new_feedback(
        feedback_root / "feedback.csv",
        state_file,
        token="fake-token",
        create_issue=lambda token, name, timestamp, text: filed_calls.append(name),
    )
    assert filed_calls == ["Grace"]
