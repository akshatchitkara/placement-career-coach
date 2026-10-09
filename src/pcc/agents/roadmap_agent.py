"""Roadmap Agent (blueprint Section 9.2). AI may reword months; it can never reorder skills.

Flow: AI personalises -> validate -> one repair attempt -> otherwise the curated template.
With no AI client (mock mode) the template is used directly.
"""

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from pcc.agents.fallbacks.roadmap_fallback import template_roadmap
from pcc.agents.validators.roadmap_validator import validate_roadmap
from pcc.ai.ai_client import AiClient
from pcc.ai.json_response_parser import parse_json_object
from pcc.ai.safe_generate import generate_with_retry
from pcc.core.exceptions import AiOutputInvalidError, AiUnavailableError
from pcc.domain.schemas.roadmap_schemas import Roadmap

logger = logging.getLogger(__name__)

PROMPT_VERSION = "roadmap_personalisation_v1"
_PROMPT_PATH = Path(__file__).resolve().parents[1] / "ai" / "prompts" / f"{PROMPT_VERSION}.md"


@dataclass(frozen=True)
class RoadmapResult:
    roadmap: Roadmap
    used_fallback: bool
    message: str = ""


def _build_prompt(career_name: str, template: Roadmap, repair_errors: list[str]) -> str:
    note = ""
    if repair_errors:
        note = "Your previous answer was rejected for: " + "; ".join(repair_errors) + "\n"
    return _PROMPT_PATH.read_text(encoding="utf-8").format(
        career_name=career_name,
        template_json=json.dumps(template.model_dump(mode="json")["months"]),
        repair_note=note,
    )


def _attempt(
    client: AiClient,
    career_name: str,
    template: Roadmap,
    catalog_skill_ids: set[str],
    repair_errors: list[str],
) -> tuple[Roadmap | None, list[str]]:
    raw = generate_with_retry(client, _build_prompt(career_name, template, repair_errors))
    try:
        payload = parse_json_object(raw)
        candidate = Roadmap.model_validate(
            {
                "career_id": template.career_id,
                "months": payload.get("months"),
                "generation_source": "ai_personalised",
            }
        )
    except (AiOutputInvalidError, ValidationError) as exc:
        logger.info(
            "roadmap_agent prompt=%s attempt_rejected reason=%s", PROMPT_VERSION, type(exc).__name__
        )
        return None, [f"unparseable or incomplete roadmap ({type(exc).__name__})"]
    errors = validate_roadmap(candidate, template, catalog_skill_ids)
    if errors:
        rules = sorted({e.split(":", 1)[0] for e in errors})  # rule ids only
        logger.info(
            "roadmap_agent prompt=%s attempt_rejected rules=%s", PROMPT_VERSION, ",".join(rules)
        )
        return None, errors
    return candidate, []


def generate_roadmap(
    career_name: str,
    template: Roadmap,
    catalog_skill_ids: set[str],
    ai_client: AiClient | None,
) -> RoadmapResult:
    if ai_client is None:
        return RoadmapResult(template_roadmap(template), used_fallback=False)

    started = time.monotonic()
    errors: list[str] = []
    try:
        for _ in range(2):  # first try + one repair attempt
            candidate, errors = _attempt(
                ai_client, career_name, template, catalog_skill_ids, errors
            )
            if candidate is not None:
                logger.info(
                    "roadmap_agent prompt=%s status=ok fallback=False latency_ms=%d",
                    PROMPT_VERSION,
                    (time.monotonic() - started) * 1000,
                )
                return RoadmapResult(candidate, used_fallback=False)
        status, message = "invalid", "AI output failed validation; showing the curated roadmap."
    except AiUnavailableError:
        status, message = "unavailable", "AI is unavailable; showing the curated roadmap."
    logger.info(
        "roadmap_agent prompt=%s status=%s fallback=True latency_ms=%d",
        PROMPT_VERSION,
        status,
        (time.monotonic() - started) * 1000,
    )
    return RoadmapResult(template_roadmap(template), used_fallback=True, message=message)
