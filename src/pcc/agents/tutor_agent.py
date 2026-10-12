"""Tutor Agent. Explains a coaching task in more depth; never scores, grades or routes.

Flow: build a prompt from the task and the student's mistakes -> AI reply -> validate
(V-TU-01..04) -> otherwise a deterministic reply from the curated explanation. With no AI client
(offline mode) the deterministic reply is used directly.
"""

import json
import logging
import time
from pathlib import Path

from pcc.agents.fallbacks.tutor_fallback import template_reply
from pcc.agents.validators.tutor_validator import validate_tutor_reply
from pcc.ai.ai_client import AiClient
from pcc.ai.safe_generate import generate_with_retry
from pcc.core.exceptions import AiUnavailableError
from pcc.domain.schemas.tutor_schemas import (
    MAX_STUDENT_TEXT,
    TutorContext,
    TutorKind,
    TutorReply,
)

logger = logging.getLogger(__name__)

PROMPT_VERSION = "tutor_reply_v1"
_PROMPT_PATH = Path(__file__).resolve().parents[1] / "ai" / "prompts" / f"{PROMPT_VERSION}.md"
_HISTORY_TURNS = 6

_REQUESTS: dict[TutorKind, str] = {
    "explain_differently": "Explain the idea again in a different way than the task did.",
    "example": "Give one small, concrete example that shows the idea working.",
    "question": "Answer the student's question below.",
}


def _build_prompt(context: TutorContext, kind: TutorKind, student_text: str) -> str:
    task = context.task.model_dump(include={"title", "misconception", "action", "success_check"})
    missed = [
        m.model_dump(include={"stem", "selected_option_text", "correct_option_text", "explanation"})
        for m in context.missed
    ]
    history = [{"role": m.role, "text": m.content} for m in context.history[-_HISTORY_TURNS:]]
    return _PROMPT_PATH.read_text(encoding="utf-8").format(
        career_name=context.career_name,
        skill_name=context.skill_name,
        task_json=json.dumps(task),
        missed_json=json.dumps(missed),
        history_json=json.dumps(history),
        request=_REQUESTS[kind],
        student_text=student_text[:MAX_STUDENT_TEXT] if student_text else "(none)",
    )


def tutor_reply(
    context: TutorContext, kind: TutorKind, student_text: str, ai_client: AiClient | None
) -> TutorReply:
    if ai_client is None:
        return TutorReply(text=template_reply(context, kind), used_fallback=False)

    started = time.monotonic()
    try:
        text = generate_with_retry(
            ai_client, _build_prompt(context, kind, student_text), temperature=0.4
        ).strip()
        errors = validate_tutor_reply(text)
        if not errors:
            logger.info(
                "tutor_agent prompt=%s status=ok fallback=False latency_ms=%d",
                PROMPT_VERSION,
                (time.monotonic() - started) * 1000,
            )
            return TutorReply(text=text, used_fallback=False)
        rules = ",".join(sorted({e.split(":", 1)[0] for e in errors}))  # rule ids only
        logger.info("tutor_agent prompt=%s reply_rejected rules=%s", PROMPT_VERSION, rules)
        status, message = "invalid", "The AI reply did not pass checks; showing a built-in answer."
    except AiUnavailableError:
        status, message = "unavailable", "AI is unavailable; showing a built-in answer."
    logger.info(
        "tutor_agent prompt=%s status=%s fallback=True latency_ms=%d",
        PROMPT_VERSION,
        status,
        (time.monotonic() - started) * 1000,
    )
    return TutorReply(text=template_reply(context, kind), used_fallback=True, message=message)
