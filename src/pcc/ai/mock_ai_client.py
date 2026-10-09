"""Default/fallback AI client. Deterministic, offline, never fails.

Mock mode is a first-class feature (blueprint Section 14.12): it makes the
demo reliable and tests deterministic, and is always available regardless
of provider configuration.
"""

from pcc.ai.ai_client import AiClient


class MockAiClient(AiClient):
    def generate(self, prompt: str, *, system: str | None = None, temperature: float = 0.2) -> str:
        return "{}"
