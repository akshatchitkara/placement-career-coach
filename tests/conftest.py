import json

import pytest

from pcc.ai.ai_client import AiClient
from pcc.content.content_loader import load_roadmap_template, load_skills
from pcc.core.exceptions import AiUnavailableError
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


class ScriptedAiClient(AiClient):
    """Returns queued responses in order (the last repeats); an Exception item is raised."""

    def __init__(self, *responses: str | Exception) -> None:
        self._responses = list(responses)
        self.calls = 0

    def generate(self, prompt: str, *, system: str | None = None, temperature: float = 0.2) -> str:
        item = self._responses[min(self.calls, len(self._responses) - 1)]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture
def unavailable_ai() -> ScriptedAiClient:
    return ScriptedAiClient(AiUnavailableError("down"))


@pytest.fixture
def devops_template():
    return load_roadmap_template("devops_engineer")


@pytest.fixture
def devops_skill_ids() -> set[str]:
    return {s.skill_id for s in load_skills() if "devops_engineer" in s.career_ids}


@pytest.fixture
def roadmap_response(devops_template):
    """Builds a raw AI reply from the template, optionally mutated by `edit(months)`."""

    def _make(edit=None) -> str:
        months = devops_template.model_dump(mode="json")["months"]
        if edit:
            edit(months)
        return json.dumps({"months": months})

    return _make


@pytest.fixture(autouse=True)
def no_retry_pause(monkeypatch):
    """The real pause before an AI retry would only slow the tests down."""
    monkeypatch.setattr("pcc.ai.safe_generate.RETRY_PAUSE_SECONDS", 0.0)
