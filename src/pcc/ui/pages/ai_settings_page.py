"""AI Settings page -- lets the student configure the AI provider at runtime.

New in the AI-provider-configuration addendum: the blueprint's .env-only
config (Section 16) is extended so provider/endpoint/key can be set here
instead. Precedence: this page's saved row > .env > mock.
"""

from contextlib import closing

import streamlit as st

from pcc.ai.ai_client_factory import build_ai_client
from pcc.ai.provider_config import DEFAULT_BASE_URLS, AiProviderConfig
from pcc.core.config import settings
from pcc.persistence.database import get_connection
from pcc.persistence.repositories.ai_provider_settings_repository import (
    get_active_config,
    save_config,
)

_PROVIDER_LABELS = {
    "mock": "Mock (offline, deterministic)",
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "nvidia": "NVIDIA NIM",
    "custom_openai_compatible": "Custom (OpenAI-compatible endpoint)",
}


def render() -> None:
    st.title("AI Settings")
    st.caption(
        "Configure which AI backend drafts roadmap and coaching text. "
        "Scoring, levels and routing are always decided by code, never by AI."
    )

    with closing(get_connection(settings.db_path)) as conn:  # closed even if the page fails
        current = get_active_config(conn)

    provider_type = st.selectbox(
        "Provider",
        options=list(_PROVIDER_LABELS),
        format_func=lambda key: _PROVIDER_LABELS[key],
        index=list(_PROVIDER_LABELS).index(current.provider_type),
    )

    base_url, api_key, model_name = None, None, None
    if provider_type != "mock":
        default_base_url = current.base_url or DEFAULT_BASE_URLS.get(provider_type, "")
        base_url = st.text_input(
            "Base URL",
            value=default_base_url,
            disabled=provider_type in ("openai", "nvidia"),
            help="Editable only for 'Custom' -- OpenAI and NVIDIA use their standard endpoint.",
        )
        saved_key = current.api_key if current.provider_type == provider_type else None
        typed_key = st.text_input(
            "API key",
            value="",  # the saved key is never sent back to the browser
            type="password",
            placeholder="A key is saved; leave blank to keep it" if saved_key else "",
        )
        api_key = typed_key or saved_key
        model_name = st.text_input(
            "Model name",
            value=current.model_name or "",
            help="For OpenAI-compatible providers (such as Groq) you can list several models "
            "separated by commas. The first is used; if it fails (rate limit, retired model), "
            "the next one is tried.",
        )

    col1, col2 = st.columns(2)
    candidate = AiProviderConfig(
        provider_type=provider_type, base_url=base_url, api_key=api_key, model_name=model_name
    )

    if col1.button("Test connection"):
        client = build_ai_client(candidate)
        if client.__class__.__name__ == "MockAiClient" and provider_type != "mock":
            st.error("Could not reach this provider -- falling back to mock. Check the key/URL.")
        else:
            try:
                client.generate("Reply with the single word: ok")
                st.success("Connection succeeded.")
            except Exception as exc:  # noqa: BLE001 -- surface any failure, never crash the page
                message = str(exc)
                if api_key:
                    message = message.replace(api_key, "***")  # providers can echo the key
                st.error(f"Connection failed: {message}")

    if col2.button("Save"):
        with closing(get_connection(settings.db_path)) as conn:
            save_config(conn, candidate)
        st.success("Saved. This provider will be used from now on.")
