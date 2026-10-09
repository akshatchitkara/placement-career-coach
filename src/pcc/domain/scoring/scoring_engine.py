"""Section 10.3. Pure, offline, no AI. Same answers always produce the same scores (T-01)."""

from pcc.domain.schemas.assessment_schemas import Answer, SkillScore
from pcc.domain.schemas.question_schemas import Question


def compute_skill_scores(
    answers: list[Answer],
    questions_by_id: dict[str, Question],
    min_answered_for_evidence: int,
) -> dict[str, SkillScore]:
    correct_by_skill: dict[str, int] = {}
    answered_by_skill: dict[str, int] = {}

    for answer in answers:
        question = questions_by_id[answer.question_id]
        answered_by_skill[question.skill_id] = answered_by_skill.get(question.skill_id, 0) + 1
        if answer.selected_option_id == question.correct_option_id:
            correct_by_skill[question.skill_id] = correct_by_skill.get(question.skill_id, 0) + 1

    scores: dict[str, SkillScore] = {}
    for skill_id, answered_count in answered_by_skill.items():
        correct_count = correct_by_skill.get(skill_id, 0)
        scores[skill_id] = SkillScore(
            skill_id=skill_id,
            correct_count=correct_count,
            answered_count=answered_count,
            score=correct_count / answered_count * 100,
            has_sufficient_evidence=answered_count >= min_answered_for_evidence,
        )
    return scores


def compute_overall_score(answers: list[Answer], questions_by_id: dict[str, Question]) -> float:
    if not answers:
        return 0.0
    correct = sum(
        1
        for answer in answers
        if answer.selected_option_id == questions_by_id[answer.question_id].correct_option_id
    )
    return correct / len(answers) * 100
