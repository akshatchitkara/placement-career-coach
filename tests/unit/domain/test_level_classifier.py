import pytest

from pcc.domain.enums import Level
from pcc.domain.scoring.level_classifier import classify_level

LEVEL_LOWER_BOUNDS = {"intermediate": 40, "advanced": 65, "industry_ready": 85}
INDUSTRY_READY_MIN_SKILL_SCORE = 60


@pytest.mark.parametrize(
    "overall_score,expected_level",
    [
        (0, Level.BEGINNER),
        (39.9, Level.BEGINNER),
        (40, Level.INTERMEDIATE),
        (64.9, Level.INTERMEDIATE),
        (65, Level.ADVANCED),
        (84.9, Level.ADVANCED),
        (85, Level.INDUSTRY_READY),
        (100, Level.INDUSTRY_READY),
    ],
)
def test_level_boundaries_when_gates_trivially_pass(overall_score, expected_level):
    # Empty skill_scores + full coverage means neither gate can fail, isolating
    # the raw lower-bound mapping (Section 17.2).
    level, notes = classify_level(
        overall_score=overall_score,
        skill_scores={},
        coverage_ratio=1.0,
        level_lower_bounds=LEVEL_LOWER_BOUNDS,
        industry_ready_min_skill_score=INDUSTRY_READY_MIN_SKILL_SCORE,
    )
    assert level == expected_level
    if expected_level != Level.INDUSTRY_READY:
        assert notes == []


def test_T02_industry_ready_downgraded_when_a_sufficient_skill_is_below_gate(skill_score_factory):
    skill_scores = {
        "linux_fundamentals": skill_score_factory("linux_fundamentals", score=55, sufficient=True),
        "shell_scripting": skill_score_factory("shell_scripting", score=95, sufficient=True),
    }
    level, notes = classify_level(
        overall_score=90,
        skill_scores=skill_scores,
        coverage_ratio=1.0,
        level_lower_bounds=LEVEL_LOWER_BOUNDS,
        industry_ready_min_skill_score=INDUSTRY_READY_MIN_SKILL_SCORE,
    )
    assert level == Level.ADVANCED
    assert any("linux_fundamentals" in note for note in notes)


def test_T03_industry_ready_downgraded_when_coverage_is_partial(skill_score_factory):
    skill_scores = {
        "linux_fundamentals": skill_score_factory("linux_fundamentals", score=95, sufficient=True),
    }
    level, notes = classify_level(
        overall_score=90,
        skill_scores=skill_scores,
        coverage_ratio=0.25,
        level_lower_bounds=LEVEL_LOWER_BOUNDS,
        industry_ready_min_skill_score=INDUSTRY_READY_MIN_SKILL_SCORE,
    )
    assert level == Level.ADVANCED
    assert any("full-path check" in note for note in notes)


def test_T04_full_path_all_gates_pass_grants_industry_ready(skill_score_factory):
    skill_scores = {
        "a": skill_score_factory("a", score=80, sufficient=True),
        "b": skill_score_factory("b", score=65, sufficient=True),
    }
    level, notes = classify_level(
        overall_score=90,
        skill_scores=skill_scores,
        coverage_ratio=1.0,
        level_lower_bounds=LEVEL_LOWER_BOUNDS,
        industry_ready_min_skill_score=INDUSTRY_READY_MIN_SKILL_SCORE,
    )
    assert level == Level.INDUSTRY_READY
    assert notes == []


def test_T20_old_attempts_config_snapshot_is_unaffected_by_later_threshold_changes():
    original_bounds = {"intermediate": 40, "advanced": 65, "industry_ready": 85}
    changed_bounds = {"intermediate": 50, "advanced": 75, "industry_ready": 90}

    level_then, _ = classify_level(70, {}, 1.0, original_bounds, 60)
    level_now_if_recomputed_with_new_config, _ = classify_level(70, {}, 1.0, changed_bounds, 60)

    assert level_then == Level.ADVANCED
    assert level_now_if_recomputed_with_new_config == Level.INTERMEDIATE
    # The point of a stored config snapshot: re-running with the OLD snapshot
    # must still give the OLD result, proving scoring never reads global state.
    level_then_again, _ = classify_level(70, {}, 1.0, original_bounds, 60)
    assert level_then_again == level_then
