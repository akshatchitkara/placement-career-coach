import json

import httpx
import pytest
from tests.conftest import ScriptedAiClient

from pcc.ai.json_response_parser import parse_json_object
from pcc.ai.openai_compatible_ai_client import OpenAiCompatibleAiClient
from pcc.ai.provider_config import AiProviderConfig, resolve_provider_config
from pcc.ai.safe_generate import generate_with_retry
from pcc.core.exceptions import AiOutputInvalidError, AiUnavailableError


# --- one retry, then give up as "unavailable" -----------------------------------------------
def test_success_makes_one_call():
    client = ScriptedAiClient("ok")
    assert generate_with_retry(client, "p") == "ok"
    assert client.calls == 1


def test_a_brief_failure_is_retried_once():
    client = ScriptedAiClient(AiUnavailableError("blip"), "ok")
    assert generate_with_retry(client, "p") == "ok"
    assert client.calls == 2


def test_two_failures_raise_unavailable_without_a_third_call():
    client = ScriptedAiClient(AiUnavailableError("down"))
    with pytest.raises(AiUnavailableError):
        generate_with_retry(client, "p")
    assert client.calls == 2


def test_a_slow_failure_is_not_retried_so_the_student_never_waits_for_two_timeouts(monkeypatch):
    clock = iter([0.0, 31.0, 31.0, 62.0])  # first attempt "took" 31 s

    monkeypatch.setattr("pcc.ai.safe_generate.time.monotonic", lambda: next(clock))
    client = ScriptedAiClient(AiUnavailableError("timeout"))
    with pytest.raises(AiUnavailableError):
        generate_with_retry(client, "p")
    assert client.calls == 1


def test_a_fast_failure_is_still_retried(monkeypatch):
    clock = iter([0.0, 0.2, 0.2, 0.4])
    monkeypatch.setattr("pcc.ai.safe_generate.time.monotonic", lambda: next(clock))
    client = ScriptedAiClient(AiUnavailableError("503"), "ok")
    assert generate_with_retry(client, "p") == "ok"
    assert client.calls == 2


@pytest.mark.parametrize("error", [KeyError("choices"), ValueError("x"), RuntimeError("sdk bug")])
def test_unexpected_provider_errors_are_treated_as_unavailable(error):
    client = ScriptedAiClient(error)
    with pytest.raises(AiUnavailableError):
        generate_with_retry(client, "p")
    assert client.calls == 2


# --- provider responses of the wrong shape -------------------------------------------------
class _FakeResponse:
    def __init__(self, payload, status=200):
        self._payload, self.status_code = payload, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("bad", request=None, response=None)

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _client() -> OpenAiCompatibleAiClient:
    config = AiProviderConfig(
        provider_type="custom_openai_compatible", base_url="http://x/v1", api_key="k"
    )
    return OpenAiCompatibleAiClient(config)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"choices": []},
        {"choices": [{}]},
        {"choices": [{"message": {}}]},
        ValueError("not json"),
    ],
)
def test_openai_compatible_malformed_success_is_unavailable_not_a_crash(monkeypatch, payload):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _FakeResponse(payload))
    with pytest.raises(AiUnavailableError):
        _client().generate("hi")


def test_openai_compatible_http_error_is_unavailable(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _FakeResponse({}, status=500))
    with pytest.raises(AiUnavailableError):
        _client().generate("hi")


def test_openai_compatible_good_response(monkeypatch):
    good = {"choices": [{"message": {"content": "hello"}}]}
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _FakeResponse(good))
    assert _client().generate("hi") == "hello"


# --- parser ---------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "raw", ["", "   ", "plain words", "[1, 2]", "{broken", '"just a string"', "null"]
)
def test_parser_rejects_non_objects_with_a_typed_error(raw):
    with pytest.raises(AiOutputInvalidError):
        parse_json_object(raw)


def test_parser_accepts_fenced_and_preambled_json():
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_object('Sure! Here it is: {"a": 1} Hope that helps.') == {"a": 1}
    assert parse_json_object(json.dumps({"b": [1]})) == {"b": [1]}


# --- which provider is used -----------------------------------------------------------------
def _resolve(saved=None, mode="mock", key="changeme", model="changeme", timeout=30):
    return resolve_provider_config(
        saved,
        env_mode=mode,
        env_api_key=key,
        env_model_name=model,
        env_timeout_seconds=timeout,
    )


def test_default_is_mock_with_no_warning():
    config, warning = _resolve()
    assert config.provider_type == "mock" and warning == ""


def test_env_live_with_a_key_uses_anthropic_and_the_env_timeout():
    config, warning = _resolve(mode="live", key="sk-abc", model="claude-x", timeout=12)
    assert (config.provider_type, config.api_key, config.model_name) == (
        "anthropic",
        "sk-abc",
        "claude-x",
    )
    assert config.timeout_seconds == 12 and warning == ""


def test_env_live_with_placeholder_model_leaves_the_default_model():
    config, _ = _resolve(mode="LIVE", key="sk-abc", model="changeme")
    assert config.model_name is None


@pytest.mark.parametrize("key", ["", "  ", "changeme", "CHANGEME"])
def test_env_live_without_a_real_key_falls_back_to_mock_with_a_warning(key):
    config, warning = _resolve(mode="live", key=key)
    assert config.provider_type == "mock" and "no API key" in warning


def test_a_provider_saved_in_the_app_beats_the_env():
    saved = AiProviderConfig(provider_type="openai", api_key="k")
    config, warning = _resolve(saved, mode="live", key="sk-env")
    assert config.provider_type == "openai" and warning == ""


def test_an_explicitly_saved_mock_beats_env_live():
    config, _ = _resolve(AiProviderConfig(provider_type="mock"), mode="live", key="sk-env")
    assert config.provider_type == "mock"


def test_the_retry_waits_a_moment_first_so_an_overloaded_provider_can_recover(monkeypatch):
    pauses = []
    monkeypatch.setattr("pcc.ai.safe_generate.RETRY_PAUSE_SECONDS", 2.0)
    monkeypatch.setattr("pcc.ai.safe_generate.time.sleep", pauses.append)
    client = ScriptedAiClient(AiUnavailableError("503 overloaded"), "ok")
    assert generate_with_retry(client, "p") == "ok"
    assert pauses == [2.0]  # once, only before the retry


def test_no_pause_when_the_first_call_succeeds(monkeypatch):
    pauses = []
    monkeypatch.setattr("pcc.ai.safe_generate.RETRY_PAUSE_SECONDS", 2.0)
    monkeypatch.setattr("pcc.ai.safe_generate.time.sleep", pauses.append)
    generate_with_retry(ScriptedAiClient("ok"), "p")
    assert pauses == []


def test_openai_compatible_client_falls_back_to_the_next_model(monkeypatch):
    import httpx

    from pcc.ai.openai_compatible_ai_client import OpenAiCompatibleAiClient, split_models
    from pcc.ai.provider_config import AiProviderConfig

    assert split_models(" a, b ,,c ") == ["a", "b", "c"] and split_models(None) == []
    tried: list[str] = []

    def fake_post(url, *, json, **kwargs):
        tried.append(json["model"])
        request = httpx.Request("POST", url)
        if json["model"] != "good":
            return httpx.Response(429, request=request, text="rate limited")
        body = {"choices": [{"message": {"content": "ok"}}]}
        return httpx.Response(200, request=request, json=body)

    monkeypatch.setattr(httpx, "post", fake_post)
    config = AiProviderConfig(
        provider_type="custom_openai_compatible",
        base_url="https://example.test/v1",
        api_key="k",
        model_name="slow, broken, good",
    )
    assert OpenAiCompatibleAiClient(config).generate("hi") == "ok"
    assert tried == ["slow", "broken", "good"]

    tried.clear()
    all_bad = config.model_copy(update={"model_name": "x, y"})
    import pytest

    from pcc.core.exceptions import AiUnavailableError

    with pytest.raises(AiUnavailableError):
        OpenAiCompatibleAiClient(all_bad).generate("hi")
    assert tried == ["x", "y"]


def test_environment_can_select_groq_with_a_model_chain():
    config, warning = resolve_provider_config(
        None,
        env_mode="live",
        env_api_key="gsk_x",
        env_model_name="openai/gpt-oss-20b, openai/gpt-oss-120b",
        env_timeout_seconds=30,
        env_provider="custom_openai_compatible",
        env_base_url="https://api.groq.com/openai/v1",
    )
    assert warning == "" and config.provider_type == "custom_openai_compatible"
    assert config.base_url == "https://api.groq.com/openai/v1"
    assert config.model_name == "openai/gpt-oss-20b, openai/gpt-oss-120b"


def test_environment_provider_needs_a_url_when_custom_and_must_be_known():
    common = dict(env_mode="live", env_api_key="k", env_model_name="m", env_timeout_seconds=30)
    config, warning = resolve_provider_config(
        None, **common, env_provider="custom_openai_compatible", env_base_url=""
    )
    assert config.provider_type == "mock" and "PCC_AI_BASE_URL" in warning
    config, warning = resolve_provider_config(None, **common, env_provider="nope")
    assert config.provider_type == "mock" and "not supported" in warning
