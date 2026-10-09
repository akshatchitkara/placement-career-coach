from pcc.content.content_loader import (
    AppSettings,
    WeeklyPlanSettings,
    compute_skill_assessability,
    load_app_settings,
    load_careers,
    load_question_bank,
    load_skills_for_career,
)
from pcc.domain.enums import SkillType, is_quiz_assessable
from pcc.domain.schemas.question_schemas import Option, Question


def _settings():
    return AppSettings(
        level_lower_bounds={"intermediate": 40, "advanced": 65, "industry_ready": 85},
        mastery_threshold=60,
        industry_ready_min_skill_score=60,
        min_answered_for_evidence=2,
        questions_per_skill=3,
        difficulty_mix_per_skill={"easy": 1, "medium": 1, "hard": 1},
        min_bank_questions_per_skill=6,
        full_path_questions_per_skill=2,
        learning_months_per_semester=4,
        weekly_plan=WeeklyPlanSettings(min_tasks=3, max_tasks=5, max_total_minutes=240),
        retest_after_days=7,
    )


def _question(qid, skill_id, difficulty):
    return Question(
        question_id=qid,
        skill_id=skill_id,
        concept_tag="t",
        difficulty=difficulty,
        stem="s",
        options=[Option(option_id=f"opt_{c}", text=c) for c in "abcd"],
        correct_option_id="opt_a",
        explanation="e",
    )


def test_T21_only_conceptual_skill_type_is_quiz_assessable():
    assert is_quiz_assessable(SkillType.CONCEPTUAL) is True
    assert is_quiz_assessable(SkillType.REASONING) is False
    assert is_quiz_assessable(SkillType.BUILD) is False
    assert is_quiz_assessable(SkillType.COMMUNICATION) is False


def test_T22_skill_with_fewer_than_six_questions_is_not_assessable():
    questions = [_question(f"q{i}", "s", "easy") for i in range(3)]  # only 3, need 6
    assert compute_skill_assessability("s", questions, _settings()) is False


def test_T22_skill_with_uneven_difficulty_split_is_not_assessable():
    # 6 total, but all easy -- fails the 2/2/2 split even though the count is right
    questions = [_question(f"q{i}", "s", "easy") for i in range(6)]
    assert compute_skill_assessability("s", questions, _settings()) is False


def test_T22_skill_with_six_questions_split_two_per_difficulty_is_assessable():
    questions = (
        [_question(f"qe{i}", "s", "easy") for i in range(2)]
        + [_question(f"qm{i}", "s", "medium") for i in range(2)]
        + [_question(f"qh{i}", "s", "hard") for i in range(2)]
    )
    assert compute_skill_assessability("s", questions, _settings()) is True


def test_real_devops_sem3_bank_is_fully_assessable():
    settings = load_app_settings()
    questions = load_question_bank("devops_engineer")
    skill_ids = [
        "linux_fundamentals",
        "shell_scripting",
        "python_for_automation",
        "git_version_control",
    ]
    for skill_id in skill_ids:
        assert compute_skill_assessability(skill_id, questions, settings) is True


def test_real_tier_b_careers_have_no_bank_yet_and_are_not_assessable():
    settings = load_app_settings()
    for career_id in ["mean_stack_developer", "java_backend_developer", "ai_developer"]:
        questions = load_question_bank(career_id)
        assert questions == []
        skills = load_skills_for_career(career_id)
        any_assessable = any(
            compute_skill_assessability(s.skill_id, questions, settings) for s in skills
        )
        assert any_assessable is False


def test_careers_json_has_all_four_launch_careers():
    career_ids = {c.career_id for c in load_careers()}
    assert career_ids == {
        "devops_engineer",
        "mean_stack_developer",
        "java_backend_developer",
        "ai_developer",
    }
