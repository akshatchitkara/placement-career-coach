"""Generic adapter for any OpenAI-compatible /chat/completions endpoint.

Covers OpenAI, NVIDIA NIM, and "custom" providers the user points at via
base_url in the AI settings page -- these all speak the same request shape,
so one adapter is enough rather than one per vendor.
"""

import logging

import httpx

from pcc.ai.ai_client import AiClient
from pcc.ai.provider_config import AiProviderConfig
from pcc.core.exceptions import AiUnavailableError

logger = logging.getLogger(__name__)


def split_models(model_name: str | None) -> list[str]:
    """'a, b, c' -> ['a', 'b', 'c']: the first model is preferred, the rest are fallbacks."""
    return [m for m in (part.strip() for part in (model_name or "").split(",")) if m]


class OpenAiCompatibleAiClient(AiClient):
    def __init__(self, config: AiProviderConfig) -> None:
        if not config.base_url:
            raise AiUnavailableError("base_url is required for an OpenAI-compatible provider")
        self._base_url = config.base_url.rstrip("/")
        self._api_key = config.api_key
        self._models = split_models(config.model_name) or ["gpt-4o-mini"]
        self._timeout = config.timeout_seconds

    def generate(self, prompt: str, *, system: str | None = None, temperature: float = 0.2) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        last_error: httpx.HTTPError | None = None
        for model in self._models:
            try:
                response = httpx.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={"model": model, "messages": messages, "temperature": temperature},
                    timeout=self._timeout,
                )
                response.raise_for_status()
                break
            except httpx.HTTPError as exc:  # rate limit, retired model, outage: try the next one
                last_error = exc
                logger.warning("ai_model_failed model=%s error_type=%s", model, type(exc).__name__)
        else:
            raise AiUnavailableError(str(last_error)) from last_error

        try:
            return str(response.json()["choices"][0]["message"]["content"])
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise AiUnavailableError("provider returned an unexpected response shape") from exc
