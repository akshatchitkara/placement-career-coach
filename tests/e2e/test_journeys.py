"""Whole student journeys in a real browser, checked against what the database holds."""

import pytest
from tests.e2e.helpers import (
    answer_check,
    body,
    build_roadmap,
    db_rows,
    nav,
    settle,
    sign_in,
    start_check,
)

CASES = [
    ("devops_engineer", 3, 12),
    ("mean_stack_developer", 4, 12),
    ("java_backend_developer", 5, 12),
    ("ai_developer", 6, 6),  # semester 6: two quiz skills, the rest are not quizzed
]


@pytest.mark.parametrize(("career", "semester", "questions"), CASES)
def test_full_journey(page, app, career, semester, questions):
    name = f"Journey {career} {semester}"
    sign_in(page, name)
    build_roadmap(page, career, semester)

    nav(page, "Roadmap")
    assert page.locator("[data-testid=stExpander]").count() == 16
    assert page.get_by_text("you are in this semester").count() == 1

    start_check(page)
    assert page.get_by_text(f"Question 1 of {questions}").count() == 1
    answered = answer_check(page, career, correct_per_skill=None)  # every answer right
    assert answered == questions

    nav(page, "Results")
    page.wait_for_selector("text=Review your answers", timeout=30000)
    assert "100.0%" in body(page)

    for page_name, marker in (
        ("Coaching Plan", "No coaching plan"),  # a perfect check has no weak skill
        ("Weekly Plan", "Tasks done"),
        ("Progress", "Your score over time"),
    ):
        nav(page, page_name)
        assert marker in body(page), page_name
    assert not page.pcc_errors, page.pcc_errors

    rows = db_rows(
        app.db_path,
        "SELECT a.id, a.overall_score, a.level, p.workflow_state, p.current_semester, "
        "(SELECT count(*) FROM assessment_responses r WHERE r.attempt_id = a.id) "
        "FROM assessment_attempts a JOIN profiles p ON p.id = a.profile_id "
        "WHERE p.display_name = ? AND a.submitted_at IS NOT NULL",
        (name,),
    )
    assert len(rows) == 1
    _, score, level, state, saved_semester, responses = rows[0]
    assert score == 100.0 and responses == questions and saved_semester == semester
    assert state.lower() == "weekly_plan_active"
    plans = db_rows(
        app.db_path,
        "SELECT count(*) FROM weekly_plans w JOIN profiles p ON p.id = w.profile_id "
        "WHERE p.display_name = ?",
        (name,),
    )
    assert plans[0][0] == 1


def test_weak_result_leads_to_coaching_weekly_plan_and_progress(page, app):
    name = "Weak result"
    sign_in(page, name)
    build_roadmap(page, "devops_engineer")
    start_check(page)
    answer_check(
        page,
        "devops_engineer",
        {
            "linux_fundamentals": 1,
            "shell_scripting": 1,
            "python_for_automation": 2,
            "git_version_control": 2,
        },
    )
    nav(page, "Results")
    text = body(page)
    assert "50.0%" in text and "Intermediate" in text
    assert "Your biggest opportunity: Linux Fundamentals" in text

    nav(page, "Coaching Plan")
    assert page.get_by_text("Do this:").count() >= 3
    assert "http" not in body(page)

    nav(page, "Weekly Plan")
    assert 2 <= page.locator("[data-testid=stCheckbox]").count() <= 4

    nav(page, "Progress")
    assert "A message you can send about Linux Fundamentals" in body(page)
    assert not page.pcc_errors, page.pcc_errors


def test_recheck_after_a_baseline_shows_improvement(page, app):
    sign_in(page, "Improver")
    build_roadmap(page, "devops_engineer")
    start_check(page)
    answer_check(page, "devops_engineer", {"linux_fundamentals": 0, "shell_scripting": 0})

    start_check(page)  # offers "Start re-check", early, from the Skills Check page
    answer_check(page, "devops_engineer", None)

    nav(page, "Progress")
    settle(page, 1500)
    text = body(page)
    assert "Checks taken" in text and "+" in text  # a positive change is shown
    assert page.locator("svg[role=img] circle").count() == 2
    assert not page.pcc_errors, page.pcc_errors
