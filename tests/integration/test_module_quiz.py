"""End-of-module quizzes, XP and the career wish list. None of it may touch check scores."""

import sqlite3

import pytest

from pcc.content.content_loader import load_question_bank, load_roadmap_template, load_skills
from pcc.core.exceptions import PccError
from pcc.domain.enums import is_quiz_assessable
from pcc.workflow.workflow_controller import WorkflowController

CAREERS = ["devops_engineer", "mean_stack_developer", "java_backend_developer", "ai_developer"]
SKILLS = {s.skill_id: s for s in load_skills()}


def _start(tmp_path, career="devops_engineer"):
    controller = WorkflowController(str(tmp_path / "pcc.db"))
    profile = controller.open_profile("Asha")
    controller.select_career(profile.id, career_id=career, custom_text="", semester=3)
    return controller, profile


def _skill(career, quiz=True):
    months = sorted(load_roadmap_template(career).months, key=lambda m: m.month_index)
    return next(
        m.skill_id for m in months if is_quiz_assessable(SKILLS[m.skill_id].skill_type) == quiz
    )


def _answer(controller, profile, skill, right: bool):
    bank = {q.question_id: q for q in load_question_bank(profile_career(controller, profile))}
    quiz = controller.get_module_quiz(profile.id, skill)
    picks = {}
    for q in quiz:
        correct = bank[q.question_id].correct_option_id
        picks[q.question_id] = next(
            o.option_id for o in q.options if (o.option_id == correct) == right
        )
    return controller.grade_module_quiz(profile.id, skill, picks)


def profile_career(controller, profile):
    return controller.get_profile(profile.id).career_id


@pytest.mark.parametrize("career", CAREERS)
def test_quiz_is_one_easy_one_medium_one_hard_question_on_the_module_skill(tmp_path, career):
    controller, profile = _start(tmp_path, career)
    skill = _skill(career)
    quiz = controller.get_module_quiz(profile.id, skill)
    assert [q.difficulty for q in quiz] == ["easy", "medium", "hard"]
    assert {q.skill_id for q in quiz} == {skill}


def test_passing_marks_the_module_and_earns_xp_once(tmp_path):
    controller, profile = _start(tmp_path)
    skill = _skill("devops_engineer")
    assert controller.get_game_state(profile.id).xp == 0

    first = _answer(controller, profile, skill, right=True)
    assert first.passed and first.newly_passed and first.correct == 3
    assert first.xp_gained == 50
    assert controller.get_module_progress(profile.id)[skill].passed

    again = _answer(controller, profile, skill, right=True)
    assert again.passed and not again.newly_passed and again.xp_gained == 0
    assert controller.get_game_state(profile.id).xp == 50


def test_failing_earns_nothing_and_a_retry_shows_different_questions(tmp_path):
    controller, profile = _start(tmp_path)
    skill = _skill("devops_engineer")
    first_ids = [q.question_id for q in controller.get_module_quiz(profile.id, skill)]
    failed = _answer(controller, profile, skill, right=False)
    assert not failed.passed and failed.xp_gained == 0 and failed.correct == 0
    assert all(r.explanation for r in failed.results)  # the student learns from the miss

    progress = controller.get_module_progress(profile.id)[skill]
    assert not progress.passed and progress.attempts == 1
    retry_ids = [q.question_id for q in controller.get_module_quiz(profile.id, skill)]
    assert set(retry_ids).isdisjoint(first_ids)  # 2 per difficulty: the retry uses the other

    passed = _answer(controller, profile, skill, right=True)
    assert passed.passed and passed.newly_passed and passed.xp_gained == 50


def test_two_of_three_is_enough_and_one_is_not(tmp_path):
    controller, profile = _start(tmp_path)
    skill = _skill("devops_engineer")
    bank = {q.question_id: q for q in load_question_bank("devops_engineer")}

    def attempt(n_right):
        quiz = controller.get_module_quiz(profile.id, skill)
        picks = {}
        for i, q in enumerate(quiz):
            correct = bank[q.question_id].correct_option_id
            picks[q.question_id] = next(
                o.option_id for o in q.options if (o.option_id == correct) == (i < n_right)
            )
        return controller.grade_module_quiz(profile.id, skill, picks)

    assert not attempt(1).passed
    assert attempt(2).passed


def test_the_quiz_never_changes_check_results_and_prefers_unseen_questions(tmp_path):
    controller, profile = _start(tmp_path)
    bank = {q.question_id: q for q in load_question_bank("devops_engineer")}
    session = controller.start_assessment(profile.id)
    picks = {
        q.question_id: next(
            o.option_id for o in q.options if o.option_id == bank[q.question_id].correct_option_id
        )
        for q in session.questions
    }
    controller.submit_assessment(profile.id, session.attempt_id, picks)
    before = controller.get_latest_results(profile.id)
    seen = {q.question_id for q in session.questions}

    skill = session.questions[0].skill_id
    quiz = controller.get_module_quiz(profile.id, skill)
    assert not {q.question_id for q in quiz} & seen  # 2 per difficulty: unseen ones exist
    _answer(controller, profile, skill, right=False)

    after = controller.get_latest_results(profile.id)
    assert after.overall_score == before.overall_score and after.level == before.level


def test_modules_without_quiz_questions_are_marked_done_instead(tmp_path):
    controller, profile = _start(tmp_path)
    skill = _skill("devops_engineer", quiz=False)
    assert controller.get_module_quiz(profile.id, skill) == []
    controller.complete_module_without_quiz(profile.id, skill)
    assert controller.get_module_progress(profile.id)[skill].passed

    with pytest.raises(PccError):
        controller.complete_module_without_quiz(profile.id, _skill("devops_engineer"))


def test_bad_module_ids_and_incomplete_answers_are_rejected(tmp_path):
    controller, profile = _start(tmp_path)
    with pytest.raises(PccError):
        controller.get_module_quiz(profile.id, "not_a_skill")
    with pytest.raises(PccError):
        controller.grade_module_quiz(profile.id, _skill("devops_engineer"), {})


def test_rank_up_is_reported_when_xp_crosses_a_threshold(tmp_path):
    controller, profile = _start(tmp_path)
    months = sorted(load_roadmap_template("devops_engineer").months, key=lambda m: m.month_index)
    ranks = []
    for month in months:
        if not is_quiz_assessable(SKILLS[month.skill_id].skill_type):
            continue
        ranks.append(_answer(controller, profile, month.skill_id, right=True))
        if len(ranks) == 2:
            break
    assert ranks[0].rank_before == "Rookie" and ranks[0].rank_after == "Rookie"  # 50 XP
    assert ranks[1].rank_before == "Rookie" and ranks[1].rank_after == "Explorer"  # 100 XP


def test_career_wish_list_saves_validates_and_points_at_existing_careers(tmp_path):
    controller, profile = _start(tmp_path)
    assert "noted" in controller.request_career(profile.id, "  Cybersecurity   Analyst ")
    assert "already" in controller.request_career(profile.id, "devops")
    with pytest.raises(PccError):
        controller.request_career(profile.id, "<script>alert(1)</script>")
    with pytest.raises(PccError):
        controller.request_career(profile.id, "x" * 200)
    with pytest.raises(PccError):
        controller.request_career(profile.id, "   ")

    conn = sqlite3.connect(tmp_path / "pcc.db")
    rows = conn.execute("SELECT requested_text FROM career_requests").fetchall()
    assert rows == [("Cybersecurity Analyst",)]
