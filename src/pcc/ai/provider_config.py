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
