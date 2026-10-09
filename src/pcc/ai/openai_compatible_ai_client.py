"""Generic adapter for any OpenAI-compatible /chat/completions endpoint.

Covers OpenAI, NVIDIA NIM, and "custom" providers the user points at via
base_url in the AI settings page -- these all speak the same request shape,
so one adapter is enough rather than one per vendor.
"""

import httpx

from pcc.ai.ai_client import AiClient
from pcc.ai.provider_config import AiProviderConfig
from pcc.core.exceptions import AiUnavailableError


class OpenAiCompatibleAiClient(AiClient):
    def __init__(self, config: AiProviderConfig) -> None:
        if not config.base_url:
            raise AiUnavailableError("base_url is required for an OpenAI-compatible provider")
        self._base_url = config.base_url.rstrip("/")
        self._api_key = config.api_key
        self._model = config.model_name or "gpt-4o-mini"
        self._timeout = config.timeout_seconds

    def generate(self, prompt: str, *, system: str | None = None, temperature: float = 0.2) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = httpx.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": self._model, "messages": messages, "temperature": temperature},
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AiUnavailableError(str(exc)) from exc

        return response.json()["choices"][0]["message"]["content"]
