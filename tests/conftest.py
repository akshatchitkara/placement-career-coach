import pytest

from pcc.domain.schemas.assessment_schemas import SkillScore


@pytest.fixture
def skill_score_factory():
    def _make(
        skill_id: str, *, score: float, answered: int = 3, sufficient: bool = True
    ) -> SkillScore:
        correct = round(score / 100 * answered)
        return SkillScore(
            skill_id=skill_id,
            correct_count=correct,
            answered_count=answered,
            score=score,
            has_sufficient_evidence=sufficient,
        )

    return _make
