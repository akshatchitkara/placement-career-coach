"""One guarded call to the AI (blueprint Sections 9.7 and 14.4).

Any failure from the provider is reported as AiUnavailableError so the agents can fall
back. One retry is made first because most real failures (429/5xx, a dropped connection)
are brief; a failure that already took a long time (a timeout) is not retried, so the
student never waits for two full timeouts.
"""

import logging
import time

from pcc.ai.ai_client import AiClient
from pcc.core.exceptions import AiUnavailableError

logger = logging.getLogger(__name__)

RETRY_ONLY_IF_FAILED_WITHIN_SECONDS = 10.0


def generate_with_retry(client: AiClient, prompt: str, *, temperature: float = 0.2) -> str:
    last_error: Exception | None = None
    for attempt in (1, 2):
        started = time.monotonic()
        try:
            return client.generate(prompt, temperature=temperature)
        except Exception as exc:  # noqa: BLE001 -- a provider SDK may raise anything
            last_error = exc
        elapsed = time.monotonic() - started
        logger.warning(
            "ai_call failed attempt=%d error_type=%s seconds=%.1f",
            attempt,
            type(last_error).__name__,
            elapsed,
        )
        if elapsed > RETRY_ONLY_IF_FAILED_WITHIN_SECONDS:
            break
    raise AiUnavailableError("AI provider failed") from last_error
