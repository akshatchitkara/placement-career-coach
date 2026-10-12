"""The full-path check: every skill on the roadmap, and the only route to Industry-ready.

Also a scenario sweep over every career and every skill: whichever skill is made weakest, the
level, roadmap position, coaching plan and weekly plan must all agree with one another.
"""

import pytest

from pcc.agents.evaluation_agent import full_path_mix, select_questions
from pcc.content.content_loader import (
    load_app_settings,
    load_question_bank,
    load_roadmap_template,
    load_skills,
)
from pcc.core.exceptions import PccError
from pcc.domain.enums import Difficulty, Level, WorkflowState, is_quiz_assessable
from pcc.workflow import workflow_controller
from pcc.workflow.workflow_controller import WorkflowController

CAREERS = ["devops_engineer", "mean_stack_developer", "java_backend_developer", "ai_developer"]
SKILLS = {s.skill_id: s for s in load_skills()}


def _quiz_skills(career: str) -> list[str]:
    template = load_roadmap_template(career)
    months = sorted(template.months, key=lambda m: (m.semester, m.month_index))
    return [m.skill_id for m in months if is_quiz_assessable(SKILLS[m.skill_id].skill_type)]


def _start(tmp_path, career, semester=3, name="Asha"):
    controller = WorkflowController(str(tmp_path / "pcc.db"))
    profile = controller.open_profile(name)
    controller.select_career(profile.id, career_id=career, custom_text="", semester=semester)
    return controller, profile


def _answers(session, bank, wrong_skills=(), wrong_all=False):
    picks = {}
    for q in session.questions:
        right = bank[q.question_id].correct_option_id
        want_wrong = wrong_all or q.skill_id in wrong_skills
        picks[q.question_id] = next(
            o.option_id for o in q.options if (o.option_id != right) == want_wrong
        )
    return picks


def _bank(career):
    return {q.question_id: q for q in load_question_bank(career)}


# --- the check itself -----------------------------------------------------------------------
@pytest.mark.parametrize("career", CAREERS)
def test_full_path_covers_every_quiz_skill_with_one_easy_and_one_hard_question(tmp_path, career):
    controller, profile = _start(tmp_path, career)
    session = controller.start_assessment(profile.id, full_path=True)
    skills = _quiz_skills(career)
    assert session.attempt_type == "full_path"
    assert session.scope_description == "the full roadmap"
    assert len(session.questions) == 2 * len(skills) == 28
    assert [q.skill_id for q in session.questions[::2]] == skills  # roadmap order, no gaps
    for first, second in zip(session.questions[::2], session.questions[1::2], strict=True):
        assert first.skill_id == second.skill_id
        assert {first.difficulty, second.difficulty} == {Difficulty.EASY, Difficulty.HARD}


def test_the_question_mix_follows_the_configured_count():
    assert full_path_mix(2) == {"easy": 1, "hard": 1}
    assert full_path_mix(3) == {"easy": 1, "hard": 1, "medium": 1}
    assert full_path_mix(0) == {}


def test_full_path_selection_is_repeatable_and_prefers_unseen_questions():
    settings = load_app_settings()
    bank = load_question_bank("devops_engineer")
    skills = _quiz_skills("devops_engineer")
    first = select_questions(skills, bank, settings, [], seed=5, full_path=True)
    assert first == select_questions(skills, bank, settings, [], seed=5, full_path=True)
    seen = [q.question_id for q in first]
    second = select_questions(skills, bank, settings, seen, seed=5, full_path=True)
    assert not {q.question_id for q in first} & {q.question_id for q in second}


# --- Industry-ready -------------------------------------------------------------------------
@pytest.mark.parametrize("career", CAREERS)
def test_a_perfect_full_path_check_reaches_industry_ready(tmp_path, career):
    controller, profile = _start(tmp_path, career)
    session = controller.start_assessment(profile.id, full_path=True)
    result = controller.submit_assessment(
        profile.id, session.attempt_id, _answers(session, _bank(career))
    )
    assert result.overall_score == 100.0
    assert result.level == Level.INDUSTRY_READY
    assert result.coverage_ratio == 1.0
    assert result.level_notes == []
    assert result.scope_description == "the full roadmap"
    assert result.weakest.status == "no_major_gap"
    assert controller.get_profile(profile.id).workflow_state == WorkflowState.WEEKLY_PLAN_ACTIVE


def test_a_semester_check_still_caps_at_advanced_and_points_to_the_full_path_check(tmp_path):
    controller, profile = _start(tmp_path, "devops_engineer")
    session = controller.start_assessment(profile.id)
    result = controller.submit_assessment(
        profile.id, session.attempt_id, _answers(session, _bank("devops_engineer"))
    )
    assert result.overall_score == 100.0 and result.level == Level.ADVANCED
    assert any("full-path check" in note for note in result.level_notes)
    assert controller.can_take_full_path(profile.id)  # and that check now exists


def test_one_weak_skill_blocks_industry_ready_even_with_a_high_overall_score(tmp_path):
    controller, profile = _start(tmp_path, "devops_engineer")
    session = controller.start_assessment(profile.id, full_path=True)
    picks = _answers(session, _bank("devops_engineer"), wrong_skills={"terraform_iac"})
    result = controller.submit_assessment(profile.id, session.attempt_id, picks)
    assert result.overall_score == pytest.approx(26 / 28 * 100)
    assert result.level == Level.ADVANCED
    assert any("terraform_iac" in note for note in result.level_notes)


# 14 skills, 2 questions each. Right answers / 28: 0 -> 0.0, 10 -> 35.7, 12 -> 42.9, 18 -> 64.3,
# 20 -> 71.4, 26 -> 92.9. The cut-offs are 40 and 65, so these sit on both sides of each one.
@pytest.mark.parametrize(
    ("wrong_skill_count", "expected"),
    [
        (14, Level.BEGINNER),
        (9, Level.BEGINNER),
        (8, Level.INTERMEDIATE),
        (5, Level.INTERMEDIATE),
        (4, Level.ADVANCED),
        (1, Level.ADVANCED),
    ],
)
def test_each_level_is_reachable_by_changing_only_the_answers(
    tmp_path, wrong_skill_count, expected
):
    controller, profile = _start(tmp_path, "mean_stack_developer")
    session = controller.start_assessment(profile.id, full_path=True)
    skills = _quiz_skills("mean_stack_developer")
    picks = _answers(
        session, _bank("mean_stack_developer"), wrong_skills=set(skills[:wrong_skill_count])
    )
    result = controller.submit_assessment(profile.id, session.attempt_id, picks)
    assert result.level == expected, (wrong_skill_count, result.overall_score)


# --- availability and later cycles ----------------------------------------------------------
def test_the_full_path_check_is_refused_when_a_skill_has_too_few_questions(tmp_path, monkeypatch):
    real = workflow_controller.load_question_bank
    monkeypatch.setattr(
        workflow_controller,
        "load_question_bank",
        lambda career_id: [q for q in real(career_id) if q.skill_id != "terraform_iac"],
    )
    controller, profile = _start(tmp_path, "devops_engineer")
    assert not controller.can_take_full_path(profile.id)
    with pytest.raises(PccError, match="not available yet"):
        controller.start_assessment(profile.id, full_path=True)
    assert controller.get_profile(profile.id).workflow_state == WorkflowState.ROADMAP_READY


def test_a_full_path_check_can_follow_a_baseline_and_progress_labels_it(tmp_path):
    controller, profile = _start(tmp_path, "devops_engineer")
    bank = _bank("devops_engineer")
    first = controller.start_assessment(profile.id)
    controller.submit_assessment(
        profile.id, first.attempt_id, _answers(first, bank, wrong_all=True)
    )
    second = controller.start_assessment(profile.id, full_path=True)  # before the re-check date
    assert second.attempt_type == "full_path"
    result = controller.submit_assessment(profile.id, second.attempt_id, _answers(second, bank))
    assert result.level == Level.INDUSTRY_READY

    progress = controller.get_progress(profile.id)
    assert [a.attempt_type for a in progress.attempts] == ["baseline", "full_path"]
    assert progress.attempts[-1].level == Level.INDUSTRY_READY
    assert progress.overall_delta is None  # different scopes are not compared
    assert progress.scope_changed is True
    assert controller.get_latest_results(profile.id).level == Level.INDUSTRY_READY


def test_the_full_path_result_is_rederived_identically_after_reopening(tmp_path):
    controller, profile = _start(tmp_path, "ai_developer")
    session = controller.start_assessment(profile.id, full_path=True)
    original = controller.submit_assessment(
        profile.id,
        session.attempt_id,
        _answers(session, _bank("ai_developer"), wrong_skills={"mlops_basics"}),
    )
    reopened = WorkflowController(str(tmp_path / "pcc.db")).get_latest_results(profile.id)
    assert reopened == original


def test_a_full_path_draft_resumes_the_same_questions_and_answers(tmp_path):
    controller, profile = _start(tmp_path, "java_backend_developer")
    session = controller.start_assessment(profile.id, full_path=True)
    q = session.questions[0]
    controller.save_check_draft(
        profile.id, session.attempt_id, {q.question_id: q.options[0].option_id}
    )
    again = WorkflowController(str(tmp_path / "pcc.db")).start_assessment(profile.id)
    assert [x.question_id for x in again.questions] == [x.question_id for x in session.questions]
    assert again.attempt_type == "full_path"
    assert controller.get_check_draft(profile.id, session.attempt_id) == {
        q.question_id: q.options[0].option_id
    }


# --- scenario sweep: every career, every skill ----------------------------------------------
SWEEP = [(career, skill) for career in CAREERS for skill in _quiz_skills(career)]


@pytest.mark.parametrize(("career", "weak_skill"), SWEEP)
def test_whichever_skill_is_weakest_every_stage_agrees(tmp_path, career, weak_skill):
    controller, profile = _start(tmp_path, career)
    session = controller.start_assessment(profile.id, full_path=True)
    picks = _answers(session, _bank(career), wrong_skills={weak_skill})
    result = controller.submit_assessment(profile.id, session.attempt_id, picks)

    # evaluation
    assert result.weakest.status == "weakest_found" and result.weakest.skill_id == weak_skill
    assert [s.skill_id for s in result.skill_scores if s.is_weakest] == [weak_skill]
    assert next(s for s in result.skill_scores if s.skill_id == weak_skill).score == 0.0
    assert result.level == Level.ADVANCED  # 26 of 28 right, but one skill under the 60 bar
    # roadmap position: the first skill not yet mastered is the weak one
    assert result.position.skill_id == weak_skill
    # coaching is about that skill and every task traces back to a missed question
    view = controller.get_coaching_plan(profile.id)
    assert view.plan.skill_id == weak_skill
    missed = {r.question_id for r in result.reviews if not r.is_correct}
    assert len(missed) == 2
    for task in view.plan.tasks:
        assert task.linked_question_id in missed or task.concept_tag
    # the weekly plan starts with that coaching and keeps the re-check
    weekly = controller.get_weekly_plan(profile.id).plan
    assert weekly.tasks[0].kind == "coaching" and weekly.tasks[0].skill_id == weak_skill
    assert weekly.tasks[-1].kind == "recheck"


# --- the assessment's own DevOps example ----------------------------------------------------
def _per_skill_picks(session, bank, right_count):
    """right_count: skill_id -> how many of its (two) questions are answered correctly."""
    seen: dict[str, int] = {}
    picks = {}
    for q in session.questions:
        n = seen.get(q.skill_id, 0)
        seen[q.skill_id] = n + 1
        right = bank[q.question_id].correct_option_id
        want_right = n < right_count.get(q.skill_id, 0)
        picks[q.question_id] = next(
            o.option_id for o in q.options if (o.option_id == right) == want_right
        )
    return picks


def test_a_student_who_knows_only_basic_linux_and_git_is_placed_at_beginner(tmp_path):
    controller, profile = _start(tmp_path, "devops_engineer")
    session = controller.start_assessment(profile.id, full_path=True)
    picks = _per_skill_picks(
        session, _bank("devops_engineer"), {"linux_fundamentals": 2, "git_version_control": 2}
    )
    result = controller.submit_assessment(profile.id, session.attempt_id, picks)
    assert result.level == Level.BEGINNER
    assert result.overall_score == pytest.approx(4 / 28 * 100)
    assert result.weakest.status == "weakest_found"
    assert result.position.skill_id == "shell_scripting"  # first roadmap skill not yet mastered


def test_a_student_who_can_run_containers_but_is_weak_on_terraform_is_intermediate(tmp_path):
    controller, profile = _start(tmp_path, "devops_engineer")
    session = controller.start_assessment(profile.id, full_path=True)
    solid = {
        s: 2
        for s in (
            "linux_fundamentals",
            "shell_scripting",
            "python_for_automation",
            "git_version_control",
            "networking_fundamentals",
            "ci_cd_pipelines",
            "docker_containers",
            "cloud_fundamentals",
        )
    }
    picks = _per_skill_picks(
        session, _bank("devops_engineer"), {**solid, "kubernetes_orchestration": 1}
    )
    result = controller.submit_assessment(profile.id, session.attempt_id, picks)
    assert result.level == Level.INTERMEDIATE
    assert result.overall_score == pytest.approx(17 / 28 * 100)
    # Kubernetes scored 50; Terraform and the rest of Semesters 5 and 6 scored 0, and the
    # earliest of those on the roadmap is the weakest skill to coach.
    assert result.weakest.skill_id == "terraform_iac"
    assert controller.get_coaching_plan(profile.id).plan.skill_id == "terraform_iac"
