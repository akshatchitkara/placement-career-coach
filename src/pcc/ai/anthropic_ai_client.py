"""Anthropic-native adapter (Messages API)."""

import anthropic

from pcc.ai.ai_client import AiClient
from pcc.ai.provider_config import AiProviderConfig
from pcc.core.exceptions import AiUnavailableError


class AnthropicAiClient(AiClient):
    def __init__(self, config: AiProviderConfig) -> None:
        self._model = config.model_name or "claude-sonnet-5-5"
        self._timeout = config.timeout_seconds
        self._client = anthropic.Anthropic(api_key=config.api_key, timeout=config.timeout_seconds)

    def generate(self, prompt: str, *, system: str | None = None, temperature: float = 0.2) -> str:
        # anthropic>=1.13 dropped `temperature` from Messages.create entirely (verified
        # against the installed SDK's signature/source -- not accepted by this API version).
        # The interface still takes it so callers stay provider-agnostic; it's a no-op here.
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=2048,
                system=system or "",
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.AnthropicError as exc:
            raise AiUnavailableError(str(exc)) from exc
        return "".join(block.text for block in response.content if block.type == "text")
