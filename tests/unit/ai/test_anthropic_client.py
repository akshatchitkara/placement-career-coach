from types import SimpleNamespace

import anthropic
import pytest

from pcc.ai import anthropic_ai_client
from pcc.ai.anthropic_ai_client import MAX_OUTPUT_TOKENS, AnthropicAiClient
from pcc.ai.provider_config import AiProviderConfig
from pcc.core.exceptions import AiUnavailableError


class _FakeMessages:
    def __init__(self, outcome):
        self.outcome, self.kwargs = outcome, None

    def create(self, **kwargs):
        self.kwargs = kwargs
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def _client(monkeypatch, outcome):
    messages = _FakeMessages(outcome)
    monkeypatch.setattr(
        anthropic_ai_client.anthropic,
        "Anthropic",
        lambda **kwargs: SimpleNamespace(messages=messages),
    )
    config = AiProviderConfig(provider_type="anthropic", api_key="sk-test", model_name="m")
    return AnthropicAiClient(config), messages


def _reply(text: str):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


def test_the_output_limit_is_large_enough_for_a_16_month_roadmap(monkeypatch):
    # Regression: a 2048-token cap cut live roadmap replies off mid-string (stop_reason=max_tokens).
    client, messages = _client(monkeypatch, _reply("{}"))
    client.generate("hi")
    assert messages.kwargs["max_tokens"] == MAX_OUTPUT_TOKENS >= 8192


def test_text_blocks_are_joined(monkeypatch):
    reply = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="a"),
            SimpleNamespace(type="tool_use", text="ignored"),
            SimpleNamespace(type="text", text="b"),
        ]
    )
    client, _ = _client(monkeypatch, reply)
    assert client.generate("hi") == "ab"


def test_sdk_errors_become_unavailable(monkeypatch):
    client, _ = _client(monkeypatch, anthropic.AnthropicError("rate limited"))
    with pytest.raises(AiUnavailableError):
        client.generate("hi")


def test_the_default_model_is_the_current_sonnet():
    config = AiProviderConfig(provider_type="anthropic", api_key="sk-test")
    assert AnthropicAiClient(config)._model == "claude-sonnet-5-5"
