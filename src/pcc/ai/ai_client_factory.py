"""Builds the correct AiClient for the active provider config. Never raises on bad config.

Precedence (AI provider only -- business thresholds are unaffected and still
come solely from app_settings.json): an active row in ai_provider_settings,
then .env (PCC_AI_MODE / PCC_AI_API_KEY), then mock.
"""

import logging

from pcc.ai.ai_client import AiClient
from pcc.ai.anthropic_ai_client import AnthropicAiClient
from pcc.ai.mock_ai_client import MockAiClient
from pcc.ai.openai_compatible_ai_client import OpenAiCompatibleAiClient
from pcc.ai.provider_config import DEFAULT_BASE_URLS, AiProviderConfig

logger = logging.getLogger(__name__)


def build_ai_client(config: AiProviderConfig) -> AiClient:
    """Fallback is always mock -- a bad key or unreachable endpoint must never crash the app."""
    try:
        if config.provider_type == "anthropic":
            return AnthropicAiClient(config)
        if config.provider_type in ("openai", "nvidia", "custom_openai_compatible"):
            if not config.base_url and config.provider_type in DEFAULT_BASE_URLS:
                default_url = DEFAULT_BASE_URLS[config.provider_type]
                config = config.model_copy(update={"base_url": default_url})
            return OpenAiCompatibleAiClient(config)
        return MockAiClient()
    except Exception:
        logger.warning(
            "ai_client_factory: falling back to mock (provider_type=%s)",
            config.provider_type,
        )
        return MockAiClient()
