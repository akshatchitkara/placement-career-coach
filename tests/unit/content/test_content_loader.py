from pcc.content.content_loader import (
    AppSettings,
    WeeklyPlanSettings,
    compute_skill_assessability,
    load_app_settings,
    load_careers,
    load_question_bank,
    load_roadmap_template,
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


def test_every_quiz_skill_of_every_career_is_assessable():
    """Semesters 3-6: all 14 quiz skills per career have a reviewed-size bank (6+, 2 per level)."""
    settings = load_app_settings()
    for career_id in [
        "devops_engineer",
        "mean_stack_developer",
        "java_backend_developer",
        "ai_developer",
    ]:
        questions = load_question_bank(career_id)
        quiz_skills = [s for s in load_skills_for_career(career_id) if s.skill_type == "conceptual"]
        assert len(quiz_skills) == 14, career_id
        for skill in quiz_skills:
            assert compute_skill_assessability(skill.skill_id, questions, settings), (
                career_id,
                skill.skill_id,
            )


def test_each_semester_has_the_expected_number_of_questions():
    """24 per full semester (4 skills x 6), 12 in semester 6 where two skills are not quizzed."""
    for career_id in ["devops_engineer", "mean_stack_developer"]:
        template = load_roadmap_template(career_id)
        questions = load_question_bank(career_id)
        per_skill = {q.skill_id for q in questions}
        for semester, expected in ((3, 24), (4, 24), (5, 24), (6, 12)):
            skill_ids = {m.skill_id for m in template.months if m.semester == semester}
            count = sum(1 for q in questions if q.skill_id in skill_ids)
            assert count == expected, (career_id, semester, count)
        assert len(per_skill) == 14


def test_careers_json_has_all_four_launch_careers():
    career_ids = {c.career_id for c in load_careers()}
    assert career_ids == {
        "devops_engineer",
        "mean_stack_developer",
        "java_backend_developer",
        "ai_developer",
    }


def test_no_question_gives_away_its_answer_by_length():
    """The right option may not be twice as long as every wrong one (a test-taking cue)."""
    for career_id in [
        "devops_engineer",
        "mean_stack_developer",
        "java_backend_developer",
        "ai_developer",
    ]:
        for q in load_question_bank(career_id):
            right = next(len(o.text) for o in q.options if o.option_id == q.correct_option_id)
            wrong = max(len(o.text) for o in q.options if o.option_id != q.correct_option_id)
            assert right < 2 * wrong or right - wrong < 15, q.question_id
            assert len({o.text for o in q.options}) == len(q.options), q.question_id


def test_roadmap_months_are_specific_not_templated_filler():
    """Every month of every roadmap has its own deliverable and real topics."""
    for career_id in [
        "devops_engineer",
        "mean_stack_developer",
        "java_backend_developer",
        "ai_developer",
    ]:
        months = load_roadmap_template(career_id).months
        deliverables = [m.deliverable for m in months]
        assert len(set(deliverables)) == len(deliverables), career_id
        for m in months:
            assert len(m.topics) >= 3, (career_id, m.skill_id)
            assert not {"core concepts", "common pitfalls"} & set(m.topics), (career_id, m.skill_id)
            assert len(m.deliverable.split()) >= 12, (career_id, m.skill_id)  # a real task
            assert "short artifact demonstrating" not in m.deliverable, (career_id, m.skill_id)


def test_every_career_explains_itself_and_validation_catches_gaps():
    from pcc.content.content_loader import load_careers
    from pcc.content.content_validator import validate_careers

    careers = load_careers()
    assert validate_careers(careers) == []
    for career in careers:
        assert career.overview and len(career.day_to_day) == 3 and len(career.growth_path) == 4

    bare = careers[0].model_copy(update={"overview": " ", "day_to_day": [], "growth_path": ["a"]})
    issues = validate_careers([bare])
    assert len(issues) == 3
