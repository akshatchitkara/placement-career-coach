"""Typed config for the active AI provider, sourced from the ai_provider_settings table."""

from typing import Literal

from pydantic import BaseModel

ProviderType = Literal["mock", "anthropic", "openai", "nvidia", "custom_openai_compatible"]

DEFAULT_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "nvidia": "https://integrate.api.nvidia.com/v1",
}


class AiProviderConfig(BaseModel):
    provider_type: ProviderType = "mock"
    base_url: str | None = None
    api_key: str | None = None
    model_name: str | None = None
    timeout_seconds: int = 30

    def __repr__(self) -> str:  # never let a stray log/print leak the key
        return (
            f"AiProviderConfig(provider_type={self.provider_type!r}, "
            f"base_url={self.base_url!r}, model_name={self.model_name!r}, api_key='***')"
        )


class AiStatus(BaseModel):
    """What the student is told about AI. Offline mode is a normal, fully working state."""

    offline: bool
    label: str
    warning: str = ""


_PLACEHOLDERS = {"", "changeme"}


def resolve_provider_config(
    saved: AiProviderConfig | None,
    *,
    env_mode: str,
    env_api_key: str,
    env_model_name: str,
    env_timeout_seconds: int,
) -> tuple[AiProviderConfig, str]:
    """Precedence: provider saved on the AI Settings page, then .env, then mock.

    Returns the config and a warning (empty unless live mode was requested but cannot work).
    """
    if saved is not None:
        return saved, ""
    if env_mode.lower() == "live":
        if env_api_key.strip().lower() in _PLACEHOLDERS:
            return AiProviderConfig(), "PCC_AI_MODE is 'live' but no API key is set."
        model = None if env_model_name.strip().lower() in _PLACEHOLDERS else env_model_name
        return (
            AiProviderConfig(
                provider_type="anthropic",
                api_key=env_api_key,
                model_name=model,
                timeout_seconds=env_timeout_seconds,
            ),
            "",
        )
    return AiProviderConfig(), ""
