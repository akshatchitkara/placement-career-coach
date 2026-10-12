from pcc.domain.enums import Level
from pcc.domain.progress import AttemptSummary
from pcc.domain.schemas.assessment_schemas import SkillScore
from pcc.ui.components.progress_visuals import skill_change_rows, sparkline_svg, trend_svg

BOUNDS = {"intermediate": 40.0, "advanced": 65.0, "industry_ready": 85.0}
NAMES = {"a": "Skill <A>", "b": "Skill B"}


def _score(skill_id: str, score: float, evidence: bool = True) -> SkillScore:
    return SkillScore(
        skill_id=skill_id,
        correct_count=1,
        answered_count=3,
        score=score,
        has_sufficient_evidence=evidence,
    )


def _attempt(n: int, overall: float, skills: list[SkillScore]) -> AttemptSummary:
    return AttemptSummary(
        attempt_id=n,
        attempt_type="baseline" if n == 1 else "retest",
        submitted_at=f"2026-10-0{n}T10:00:00+00:00",
        overall_score=overall,
        level=Level.INTERMEDIATE,
        skill_scores=skills,
    )


def test_trend_with_one_check_draws_a_point_and_no_line():
    svg = trend_svg([_attempt(1, 50.0, [])], BOUNDS)
    assert svg.count("<circle") == 1 and "<polyline" not in svg
    assert "Baseline" in svg and "50%" in svg
    assert "Intermediate 40%" in svg and "Industry-ready 85%" in svg


def test_trend_with_several_checks_joins_them_in_order():
    attempts = [_attempt(1, 50.0, []), _attempt(2, 70.0, []), _attempt(3, 90.0, [])]
    svg = trend_svg(attempts, BOUNDS)
    assert svg.count("<circle") == 3 and svg.count("<polyline") == 1
    assert "Re-check 1" in svg and "Re-check 2" in svg
    assert "Baseline 50%, Re-check 1 70%, Re-check 2 90%" in svg  # screen-reader summary


def test_sparkline_skips_missing_values_and_handles_none():
    assert sparkline_svg([None, None]) == ""
    one = sparkline_svg([None, 60.0])
    assert "<circle" in one and "<polyline" not in one
    assert "<polyline" in sparkline_svg([20.0, None, 80.0])


def test_skill_rows_show_change_and_escape_names():
    before = _attempt(1, 40.0, [_score("a", 33.0), _score("b", 100.0)])
    after = _attempt(2, 70.0, [_score("a", 67.0), _score("b", 100.0)])
    html_rows = skill_change_rows([before, after], NAMES, 60.0)
    assert "Skill &lt;A&gt;" in html_rows and "<A>" not in html_rows
    assert "+34 points" in html_rows and "pcc-up" in html_rows
    assert "no change" in html_rows
    assert "<b style" in html_rows  # previous-check tick


def test_skill_rows_for_a_first_check_and_thin_evidence():
    first = _attempt(1, 40.0, [_score("a", 33.0), _score("b", 0.0, evidence=False)])
    rows = skill_change_rows([first], NAMES, 60.0)
    assert "first time measured" in rows and "Not enough answers yet" in rows


def test_sparklines_appear_once_there_are_three_checks():
    attempts = [_attempt(n, 50.0 + n, [_score("a", 30.0 + 10 * n)]) for n in (1, 2, 3)]
    assert "pcc-spark" in skill_change_rows(attempts, NAMES, 60.0)
    assert "pcc-spark" not in skill_change_rows(attempts[:2], NAMES, 60.0)
