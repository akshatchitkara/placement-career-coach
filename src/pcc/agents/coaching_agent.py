"""Coaching Agent (blueprint Section 9.4). Writes advice only; never scores or routes.

Flow: AI drafts a plan -> validate (V-CO-01..06) -> one repair attempt -> curated template plan.
With no AI client (mock mode) the template plan is used directly.
"""

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from pcc.agents.fallbacks.coaching_fallback import template_plan
from pcc.agents.validators.coaching_validator import validate_coaching_plan
from pcc.ai.ai_client import AiClient
from pcc.ai.json_response_parser import parse_json_object
from pcc.ai.safe_generate import generate_with_retry
from pcc.core.exceptions import AiOutputInvalidError, AiUnavailableError
from pcc.domain.schemas.coaching_schemas import CoachingInput, CoachingPlan

logger = logging.getLogger(__name__)

PROMPT_VERSION = "coaching_plan_v1"
_PROMPT_PATH = Path(__file__).resolve().parents[1] / "ai" / "prompts" / f"{PROMPT_VERSION}.md"


@dataclass(frozen=True)
class CoachingResult:
    plan: CoachingPlan
    used_fallback: bool
    message: str = ""


def _build_prompt(context: CoachingInput, repair_errors: list[str]) -> str:
    note = ""
    if repair_errors:
        note = "Your previous answer was rejected for: " + "; ".join(repair_errors) + "\n"
    missed = [m.model_dump() for m in context.missed]  # no student identity is in this data
    return _PROMPT_PATH.read_text(encoding="utf-8").format(
        career_name=context.career_name,
        skill_id=context.skill_id,
        skill_name=context.skill_name,
        level=context.level,
        missed_json=json.dumps(missed),
        max_total_minutes=context.max_total_minutes,
        retest_after_days=context.retest_after_days,
        repair_note=note,
    )


def _log_rejection(errors: list[str]) -> None:
    rules = sorted({e.split(":", 1)[0] for e in errors})  # rule ids only, never AI or student text
    logger.info(
        "coaching_agent prompt=%s attempt_rejected rules=%s", PROMPT_VERSION, ",".join(rules)
    )


def _attempt(
    client: AiClient, context: CoachingInput, repair_errors: list[str]
) -> tuple[CoachingPlan | None, list[str]]:
    raw = generate_with_retry(client, _build_prompt(context, repair_errors))
    try:
        payload = parse_json_object(raw)
        payload["generation_source"] = "ai"
        plan = CoachingPlan.model_validate(payload)
    except (AiOutputInvalidError, ValidationError) as exc:
        logger.info(
            "coaching_agent prompt=%s attempt_rejected reason=%s",
            PROMPT_VERSION,
            type(exc).__name__,
        )
        return None, [f"unparseable or incomplete plan ({type(exc).__name__})"]
    errors = validate_coaching_plan(plan, context.skill_id, context)
    if errors:
        _log_rejection(errors)
        return None, errors
    plan = plan.model_copy(
        update={
            "tasks": [t.model_copy(update={"order": i}) for i, t in enumerate(plan.tasks, start=1)],
            "retest_after_days": context.retest_after_days,  # config decides, not the model
        }
    )
    return plan, []


def generate_coaching_plan(context: CoachingInput, ai_client: AiClient | None) -> CoachingResult:
    if ai_client is None:
        return CoachingResult(template_plan(context), used_fallback=False)

    started = time.monotonic()
    errors: list[str] = []
    try:
        for _ in range(2):  # first try + one repair attempt
            plan, errors = _attempt(ai_client, context, errors)
            if plan is not None:
                logger.info(
                    "coaching_agent prompt=%s status=ok fallback=False latency_ms=%d",
                    PROMPT_VERSION,
                    (time.monotonic() - started) * 1000,
                )
                return CoachingResult(plan, used_fallback=False)
        status, message = "invalid", "AI advice failed validation; showing the curated plan."
    except AiUnavailableError:
        status, message = "unavailable", "AI is unavailable; showing the curated plan."
    logger.info(
        "coaching_agent prompt=%s status=%s fallback=True latency_ms=%d",
        PROMPT_VERSION,
        status,
        (time.monotonic() - started) * 1000,
    )
    return CoachingResult(template_plan(context), used_fallback=True, message=message)
