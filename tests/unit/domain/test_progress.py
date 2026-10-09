import pytest

from pcc.domain.enums import Level
from pcc.domain.progress import (
    AttemptSummary,
    build_progress,
    compare_skill_scores,
    mentor_skill_ids,
    repeated_drop_skill_ids,
)
from pcc.domain.schemas.assessment_schemas import SkillScore


def _score(skill_id: str, score: float, evidence: bool = True) -> SkillScore:
    return SkillScore(
        skill_id=skill_id,
        correct_count=round(score / 100 * 3),
        answered_count=3,
        score=score,
        has_sufficient_evidence=evidence,
    )


def _attempt(n: int, level: Level, overall: float, *scores: SkillScore) -> AttemptSummary:
    return AttemptSummary(
        attempt_id=n,
        attempt_type="baseline" if n == 1 else "retest",
        submitted_at=f"2026-10-0{n}T10:00:00",
        overall_score=overall,
        level=level,
        skill_scores=list(scores),
    )


def test_deltas_show_up_down_same_and_new():
    previous = [_score("a", 33.3333), _score("b", 100), _score("c", 66.6667)]
    current = [_score("a", 66.6667), _score("b", 66.6667), _score("c", 66.6667), _score("d", 100)]
    result = {d.skill_id: d for d in compare_skill_scores(previous, current)}
    assert result["a"].direction == "up" and result["a"].delta == pytest.approx(33.3334)
    assert result["b"].direction == "down"
    assert result["c"].direction == "same"
    assert result["d"].direction == "new" and result["d"].previous_score is None


def test_a_skill_without_evidence_before_counts_as_new():
    result = compare_skill_scores([_score("a", 50, evidence=False)], [_score("a", 100)])
    assert result[0].direction == "new"


def test_mentor_prompt_below_40_only_with_evidence():
    scores = [_score("a", 33.3333), _score("b", 66.6667), _score("c", 0, evidence=False)]
    assert mentor_skill_ids(scores) == ["a"]


def test_repeated_drop_needs_three_checks_and_two_drops_in_a_row():
    first, second, third = [_score("a", 100)], [_score("a", 66.6667)], [_score("a", 33.3333)]
    assert repeated_drop_skill_ids([first, second]) == []
    assert repeated_drop_skill_ids([first, second, third]) == ["a"]
    assert repeated_drop_skill_ids([first, third, second]) == []  # dropped then recovered


def test_progress_with_no_attempts_is_empty():
    view = build_progress([], 60)
    assert view.attempts == [] and view.deltas == [] and view.current_level is None


def test_progress_with_one_attempt_has_no_comparison():
    view = build_progress([_attempt(1, Level.BEGINNER, 33.3, _score("a", 33.3333))], 60)
    assert view.deltas == [] and view.overall_delta is None
    assert view.current_level == Level.BEGINNER and view.skills_below_mastery == 1


def test_progress_compares_latest_to_previous():
    first = _attempt(1, Level.BEGINNER, 33.3, _score("a", 33.3333), _score("b", 33.3333))
    second = _attempt(2, Level.INTERMEDIATE, 50.0, _score("a", 66.6667), _score("b", 33.3333))
    view = build_progress([first, second], 60)
    assert view.overall_delta == pytest.approx(16.7)
    assert (view.previous_level, view.current_level) == (Level.BEGINNER, Level.INTERMEDIATE)
    assert [d.direction for d in view.deltas] == ["up", "same"]
    assert view.mentor_skill_ids == ["b"]
    assert view.skills_below_mastery == 1
