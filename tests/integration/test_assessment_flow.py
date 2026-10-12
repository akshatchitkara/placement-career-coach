import json
import sqlite3

import pytest

from pcc.content.content_loader import load_question_bank
from pcc.core.exceptions import PccError
from pcc.domain.enums import Level, WorkflowState
from pcc.workflow import workflow_controller
from pcc.workflow.workflow_controller import WorkflowController

BANK = {q.question_id: q for q in load_question_bank("devops_engineer")}


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "pcc.db")


def _ready(db_path, career="devops_engineer", semester=3, name="Asha"):
    controller = WorkflowController(db_path)
    profile = controller.open_profile(name)
    controller.select_career(profile.id, career_id=career, custom_text="", semester=semester)
    return controller, profile


def _answers(session, correct_per_skill: dict[str, int]) -> dict[str, str]:
    """Answers the first N questions of each skill correctly and the rest wrongly."""
    seen: dict[str, int] = {}
    selections = {}
    for q in session.questions:
        n = seen.get(q.skill_id, 0)
        seen[q.skill_id] = n + 1
        bank_q = BANK[q.question_id]
        want_correct = n < correct_per_skill.get(q.skill_id, 0)
        selections[q.question_id] = next(
            o.option_id
            for o in q.options
            if (o.option_id == bank_q.correct_option_id) == want_correct
        )
    return selections


WORKED_EXAMPLE = {
    "linux_fundamentals": 1,
    "shell_scripting": 1,
    "python_for_automation": 2,
    "git_version_control": 2,
}


def test_section_10_7_worked_example_end_to_end(db_path):
    controller, profile = _ready(db_path)
    session = controller.start_assessment(profile.id)
    assert len(session.questions) == 12
    assert session.scope_description == "Semester 3 skills"

    result = controller.submit_assessment(
        profile.id, session.attempt_id, _answers(session, WORKED_EXAMPLE)
    )

    assert result.overall_score == pytest.approx(50.0)
    assert result.level == Level.INTERMEDIATE
    scores = {s.skill_id: s for s in result.skill_scores}
    assert scores["linux_fundamentals"].score == pytest.approx(33.3333, abs=1e-3)
    assert (
        scores["python_for_automation"].correct_count,
        scores["python_for_automation"].answered_count,
    ) == (2, 3)
    assert result.weakest.status == "weakest_found"
    assert result.weakest.skill_id == "linux_fundamentals"  # tie with shell -> roadmap order
    assert scores["linux_fundamentals"].is_weakest and not scores["shell_scripting"].is_weakest
    assert result.position.label == "in_progress"
    assert result.position.skill_id == "linux_fundamentals"
    assert result.coverage_ratio == pytest.approx(4 / 14)
    assert len(result.reviews) == 12
    assert controller.get_profile(profile.id).workflow_state == WorkflowState.WEEKLY_PLAN_ACTIVE


def test_perfect_single_semester_caps_at_advanced_with_coverage_note(db_path):
    controller, profile = _ready(db_path)
    session = controller.start_assessment(profile.id)
    result = controller.submit_assessment(
        profile.id, session.attempt_id, _answers(session, dict.fromkeys(WORKED_EXAMPLE, 3))
    )
    assert result.overall_score == 100
    assert result.level == Level.ADVANCED  # T-03
    assert any("full-path" in n for n in result.level_notes)
    assert result.weakest.status == "no_major_gap"  # T-08
    assert result.position.label == "advance_to_next_semester"
    assert result.position.skill_id == "networking_fundamentals"
    # regression: "next" is the first skill still to do, not the one after the tie-break pick
    assert result.weakest.next_roadmap_skill_id == "networking_fundamentals"


def test_attempt_is_persisted_with_counts_and_config_snapshot(db_path):
    controller, profile = _ready(db_path)
    session = controller.start_assessment(profile.id)
    controller.submit_assessment(profile.id, session.attempt_id, _answers(session, WORKED_EXAMPLE))

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    attempt = conn.execute("SELECT * FROM assessment_attempts").fetchone()
    assert attempt["submitted_at"] and attempt["level"] == "intermediate"
    assert attempt["attempt_type"] == "baseline"
    assert json.loads(attempt["config_snapshot_json"])["level_lower_bounds"]["advanced"] == 65
    assert conn.execute("SELECT COUNT(*) FROM assessment_responses").fetchone()[0] == 12
    assert conn.execute("SELECT COUNT(*) FROM skill_scores").fetchone()[0] == 4
    assert conn.execute("SELECT SUM(is_weakest) FROM skill_scores").fetchone()[0] == 1
    order = json.loads(
        conn.execute("SELECT displayed_order_json FROM assessment_responses").fetchone()[0]
    )
    assert len(order) == 4
    conn.close()


def test_resume_returns_the_same_questions_and_order(db_path):
    controller, profile = _ready(db_path)
    first = controller.start_assessment(profile.id)
    assert controller.get_profile(profile.id).workflow_state == WorkflowState.ASSESSMENT_IN_PROGRESS
    again = WorkflowController(db_path).start_assessment(profile.id)
    assert again == first


def test_fr05_all_questions_must_be_answered(db_path):
    controller, profile = _ready(db_path)
    session = controller.start_assessment(profile.id)
    selections = _answers(session, WORKED_EXAMPLE)
    selections[session.questions[0].question_id] = None
    with pytest.raises(PccError, match="Answer every question"):
        controller.submit_assessment(profile.id, session.attempt_id, selections)
    partial = dict(list(_answers(session, WORKED_EXAMPLE).items())[:5])
    with pytest.raises(PccError, match="Answer every question"):
        controller.submit_assessment(profile.id, session.attempt_id, partial)
    assert controller.get_latest_results(profile.id) is None  # nothing saved


def test_invalid_option_and_double_submit_rejected(db_path):
    controller, profile = _ready(db_path)
    session = controller.start_assessment(profile.id)
    bad = _answers(session, WORKED_EXAMPLE)
    bad[session.questions[0].question_id] = "opt_zzz"
    with pytest.raises(PccError, match="does not match"):
        controller.submit_assessment(profile.id, session.attempt_id, bad)

    good = _answers(session, WORKED_EXAMPLE)
    controller.submit_assessment(profile.id, session.attempt_id, good)
    with pytest.raises(PccError, match="not open"):
        controller.submit_assessment(profile.id, session.attempt_id, good)


def test_t18_results_restored_after_reopening(db_path):
    controller, profile = _ready(db_path)
    session = controller.start_assessment(profile.id)
    submitted = controller.submit_assessment(
        profile.id, session.attempt_id, _answers(session, WORKED_EXAMPLE)
    )
    assert WorkflowController(db_path).get_latest_results(profile.id) == submitted  # T-01 too


def test_t20_changed_thresholds_do_not_alter_a_past_attempt(db_path, monkeypatch):
    controller, profile = _ready(db_path)
    session = controller.start_assessment(profile.id)
    before = controller.submit_assessment(
        profile.id, session.attempt_id, _answers(session, WORKED_EXAMPLE)
    )

    stricter = workflow_controller.load_app_settings().model_copy(
        update={"level_lower_bounds": {"intermediate": 90, "advanced": 95, "industry_ready": 99}}
    )
    monkeypatch.setattr(workflow_controller, "load_app_settings", lambda: stricter)
    after = controller.get_latest_results(profile.id)
    assert after.level == before.level == Level.INTERMEDIATE


@pytest.fixture
def only_semester_3_banks(monkeypatch):
    """Simulates a career whose later semesters have no reviewed questions yet (T-22)."""
    real = workflow_controller.load_question_bank
    early = {
        "linux_fundamentals",
        "shell_scripting",
        "python_for_automation",
        "git_version_control",
        "java_core_oop",
        "collections_and_generics",
        "dsa_problem_solving",
        "sql_and_relational_databases",
    }
    monkeypatch.setattr(
        workflow_controller,
        "load_question_bank",
        lambda career_id: [q for q in real(career_id) if q.skill_id in early],
    )


def test_semester_without_a_bank_says_coming_soon_and_stays_ready(db_path, only_semester_3_banks):
    controller, profile = _ready(db_path, career="java_backend_developer", semester=4, name="Ravi")
    scope = controller.get_assessment_scope(profile.id)
    assert scope.assessable_skill_ids == []
    assert scope.coming_soon_skill_ids  # T-22
    with pytest.raises(PccError, match="coming soon"):
        controller.start_assessment(profile.id)
    assert controller.get_profile(profile.id).workflow_state == WorkflowState.ROADMAP_READY


def test_t21_unbuilt_methods_are_assessed_later_not_scored(db_path):
    controller, profile = _ready(db_path, semester=6, name="Meera")
    scope = controller.get_assessment_scope(profile.id)
    assert {"capstone_devops", "interview_preparation"} <= set(scope.assessed_later_skill_ids)
    assert "capstone_devops" not in scope.assessable_skill_ids


def test_t22_devops_semester_without_a_bank_is_coming_soon(db_path, only_semester_3_banks):
    controller, profile = _ready(db_path, semester=4, name="Kiran")
    scope = controller.get_assessment_scope(profile.id)
    assert scope.assessable_skill_ids == []
    assert "docker_containers" in scope.coming_soon_skill_ids


def test_cannot_start_before_roadmap(db_path):
    controller = WorkflowController(db_path)
    profile = controller.open_profile("Asha")
    with pytest.raises(PccError):
        controller.start_assessment(profile.id)


@pytest.mark.parametrize(
    "career", ["devops_engineer", "mean_stack_developer", "java_backend_developer", "ai_developer"]
)
def test_every_career_completes_a_semester_3_check(db_path, career):
    bank = {q.question_id: q for q in load_question_bank(career)}
    controller, profile = _ready(db_path, career=career, name="Asha")
    session = controller.start_assessment(profile.id)
    assert len(session.questions) == 12
    picks = {q.question_id: bank[q.question_id].correct_option_id for q in session.questions}
    result = controller.submit_assessment(profile.id, session.attempt_id, picks)
    assert result.overall_score == 100.0
    assert controller.get_profile(profile.id).workflow_state == WorkflowState.WEEKLY_PLAN_ACTIVE
    assert controller.get_weekly_plan(profile.id).plan.tasks


def test_every_semester_is_checkable_now_that_all_banks_exist(db_path):
    controller = WorkflowController(db_path)
    for career in (
        "devops_engineer",
        "mean_stack_developer",
        "java_backend_developer",
        "ai_developer",
    ):
        assert controller.checkable_semesters(career) == [3, 4, 5, 6]


def test_checkable_semesters_lists_only_semesters_with_a_bank(db_path, only_semester_3_banks):
    controller = WorkflowController(db_path)
    assert controller.checkable_semesters("java_backend_developer") == [3]
    assert controller.checkable_semesters("devops_engineer") == [3]


@pytest.mark.parametrize("semester", [3, 4, 5, 6])
@pytest.mark.parametrize(
    "career", ["devops_engineer", "mean_stack_developer", "java_backend_developer", "ai_developer"]
)
def test_every_career_completes_a_check_in_every_semester(db_path, career, semester):
    bank = {q.question_id: q for q in load_question_bank(career)}
    controller, profile = _ready(db_path, career=career, semester=semester, name="Asha")
    session = controller.start_assessment(profile.id)
    expected = (
        6 if semester == 6 else 12
    )  # semester 6 has two quiz skills (the rest are not quizzed)
    assert len(session.questions) == expected
    picks = {q.question_id: bank[q.question_id].correct_option_id for q in session.questions}
    result = controller.submit_assessment(profile.id, session.attempt_id, picks)
    assert result.overall_score == 100.0
    assert controller.get_profile(profile.id).workflow_state == WorkflowState.WEEKLY_PLAN_ACTIVE
    assert controller.get_weekly_plan(profile.id).plan.tasks
