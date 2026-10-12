from pcc.domain.enums import Level
from pcc.domain.progress import (
    AttemptSummary,
    WeekRecord,
    build_effort,
    mentor_message,
)


def _attempt(attempt_id: int, score: float) -> AttemptSummary:
    return AttemptSummary(
        attempt_id=attempt_id,
        attempt_type="baseline" if attempt_id == 1 else "retest",
        submitted_at="2026-10-12T10:00:00+00:00",
        overall_score=score,
        level=Level.INTERMEDIATE,
        skill_scores=[],
    )


def _week(attempt_id: int, done: int, total: int = 4) -> WeekRecord:
    return WeekRecord(
        attempt_id=attempt_id, tasks_done=done, tasks_total=total, minutes_done=done * 30
    )


def test_each_week_is_paired_with_the_check_that_followed_it():
    attempts = [_attempt(1, 50.0), _attempt(2, 75.0), _attempt(3, 70.0)]
    effort = build_effort(attempts, [_week(1, 3), _week(2, 1)])
    assert [(e.from_attempt_id, e.tasks_done, e.score_change) for e in effort] == [
        (1, 3, 25.0),
        (2, 1, -5.0),
    ]


def test_a_week_with_no_later_check_is_left_out():
    attempts = [_attempt(1, 50.0), _attempt(2, 80.0)]
    effort = build_effort(attempts, [_week(1, 4), _week(2, 2)])
    assert [e.from_attempt_id for e in effort] == [1]  # week 2 is still in progress


def test_weeks_from_unknown_checks_and_no_history_are_ignored():
    assert build_effort([], [_week(1, 2)]) == []
    assert build_effort([_attempt(1, 50.0)], [_week(9, 2)]) == []
    assert build_effort([_attempt(1, 50.0)], [_week(1, 2)]) == []  # a single check: no later one


def test_mentor_message_is_ready_to_send():
    text = mentor_message("DevOps Engineer", "Linux Fundamentals", 33.3, ["file permissions"])
    assert "DevOps Engineer" in text and "Linux Fundamentals at 33%" in text
    assert "I got stuck on file permissions." in text
    assert "30 minutes" in text


def test_mentor_message_without_known_concepts_has_no_dangling_phrase():
    text = mentor_message("AI Developer", "Math for ML", 20.0, [])
    assert "stuck" not in text and "  " not in text
