from pcc.content.content_loader import (
    load_careers,
    load_question_bank,
    load_roadmap_template,
    load_skills,
)
from pcc.content.content_validator import (
    validate_all,
    validate_question_bank,
    validate_roadmap,
    validate_skills,
)
from pcc.core.exceptions import ContentValidationError
from pcc.domain.schemas.career_schemas import Career
from pcc.domain.schemas.question_schemas import Option, Question
from pcc.domain.schemas.roadmap_schemas import Roadmap, RoadmapMonth, Skill


def _month(semester, month_index, skill_id):
    return RoadmapMonth(
        semester=semester,
        month_index=month_index,
        skill_id=skill_id,
        focus="f",
        topics=["t1", "t2"],
        deliverable="d",
    )


def test_real_content_passes_validation():
    careers = load_careers()
    skills = load_skills()
    roadmaps = {c.career_id: load_roadmap_template(c.career_id) for c in careers}
    question_banks = {c.career_id: load_question_bank(c.career_id) for c in careers}

    validate_all(careers, skills, roadmaps, question_banks)  # raises on any issue


def test_duplicate_skill_id_is_rejected():
    careers = [Career(career_id="x", name="X", tier="A")]
    skills = [
        Skill(skill_id="s1", name="S1", career_ids=["x"], skill_type="conceptual"),
        Skill(skill_id="s1", name="S1 dup", career_ids=["x"], skill_type="conceptual"),
    ]
    issues = validate_skills(skills, careers)
    assert any("duplicate skill_id" in issue for issue in issues)


def test_skill_shared_across_multiple_careers_is_not_a_duplicate():
    careers = [
        Career(career_id="x", name="X", tier="A"),
        Career(career_id="y", name="Y", tier="A"),
    ]
    skills = [
        Skill(skill_id="shared", name="Shared", career_ids=["x", "y"], skill_type="conceptual")
    ]
    assert validate_skills(skills, careers) == []


def test_roadmap_missing_a_semester_is_rejected():
    months = [_month(3, i, f"s{i}") for i in range(1, 5)]  # only semester 3, missing 4/5/6
    roadmap = Roadmap.model_construct(career_id="x", months=months, generation_source="template")
    issues = validate_roadmap(roadmap, [])
    assert any("semesters must be exactly" in issue for issue in issues)


def test_roadmap_with_unknown_skill_id_is_rejected():
    months = (
        [_month(3, i, f"s{i}") for i in range(1, 5)]
        + [_month(4, i, f"s{i + 4}") for i in range(1, 5)]
        + [_month(5, i, f"s{i + 8}") for i in range(1, 5)]
        + [_month(6, i, f"s{i + 12}") for i in range(1, 5)]
    )
    roadmap = Roadmap(career_id="x", months=months)
    issues = validate_roadmap(roadmap, [])  # no known skills at all
    assert any("unknown skill_id" in issue for issue in issues)


def _question(question_id, skill_id, correct_option_id, stem="stem", explanation="exp"):
    return Question(
        question_id=question_id,
        skill_id=skill_id,
        concept_tag="t",
        difficulty="easy",
        stem=stem,
        options=[Option(option_id=f"opt_{c}", text=c) for c in "abcd"],
        correct_option_id=correct_option_id,
        explanation=explanation,
    )


def test_question_with_dangling_skill_id_is_rejected():
    questions = [_question("q1", "unknown_skill", "opt_a")]
    issues = validate_question_bank(questions, [], "x")
    assert any("unknown skill_id" in issue for issue in issues)


def test_question_with_url_in_stem_is_rejected():
    skill = Skill(skill_id="s", name="S", career_ids=["x"], skill_type="conceptual")
    questions = [_question("q1", "s", "opt_a", stem="See https://example.com for details")]
    issues = validate_question_bank(questions, [skill], "x")
    assert any("URL" in issue for issue in issues)


def test_question_with_correct_option_not_among_options_is_rejected():
    skill = Skill(skill_id="s", name="S", career_ids=["x"], skill_type="conceptual")
    questions = [_question("q1", "s", "opt_z")]
    issues = validate_question_bank(questions, [skill], "x")
    assert any("not one of its options" in issue for issue in issues)


def test_validate_all_raises_contentvalidationerror_on_any_issue():
    careers = [Career(career_id="x", name="X", tier="A")]
    skills = [
        Skill(skill_id="s1", name="S1", career_ids=["unknown_career"], skill_type="conceptual")
    ]
    try:
        validate_all(careers, skills, {}, {})
    except ContentValidationError as exc:
        assert "unknown career_id" in str(exc)
    else:
        raise AssertionError("expected ContentValidationError")
