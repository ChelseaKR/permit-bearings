"""Provider adapter: settings from the environment, SDK error translation."""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from typing import Any

import pytest

from permit_pathways.ai import provider as provider_module
from permit_pathways.ai.provider import (
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_BEDROCK_MODEL,
    ProviderError,
    ProviderSettings,
    ScriptedProvider,
    SDKProvider,
    provider_from_env,
    provider_from_settings,
)


@dataclass
class _Block:
    type: str
    text: str = ""


@dataclass
class _Usage:
    input_tokens: int
    output_tokens: int


@dataclass
class _Response:
    content: list[_Block]
    stop_reason: str
    model: str = "served-model"
    usage: _Usage | None = None


class _Messages:
    def __init__(self, outcome: Any) -> None:
        self.outcome = outcome
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class _Client:
    def __init__(self, outcome: Any) -> None:
        self.messages = _Messages(outcome)


def _provider(outcome: Any, **kwargs: Any) -> SDKProvider:
    return SDKProvider(_Client(outcome), model="m", name="anthropic", **kwargs)


def test_settings_defaults_and_overrides() -> None:
    default = ProviderSettings.from_environ({})
    assert default == ProviderSettings("anthropic", DEFAULT_ANTHROPIC_MODEL, None, None)
    bedrock = ProviderSettings.from_environ(
        {
            "PERMIT_AI_PROVIDER": "Bedrock",
            "AWS_REGION": "us-east-1",
            "PERMIT_AI_EFFORT": "low",
        }
    )
    assert bedrock == ProviderSettings(
        "bedrock", DEFAULT_BEDROCK_MODEL, "us-east-1", "low"
    )
    custom = ProviderSettings.from_environ(
        {
            "PERMIT_AI_PROVIDER": "bedrock",
            "PERMIT_AI_MODEL": "global.anthropic.claude-sonnet-4-6",
        }
    )
    assert custom.model == "global.anthropic.claude-sonnet-4-6"
    assert custom.region == provider_module.DEFAULT_BEDROCK_REGION
    with pytest.raises(ProviderError, match="PERMIT_AI_PROVIDER"):
        ProviderSettings.from_environ({"PERMIT_AI_PROVIDER": "openai"})


def test_sdk_provider_returns_text_and_usage() -> None:
    provider = _provider(
        _Response(
            [_Block("thinking"), _Block("text", '{"a": 1}')],
            "end_turn",
            usage=_Usage(10, 2),
        ),
        effort="medium",
    )
    completion = provider.complete_json(
        system="s", user="u", schema={"type": "object"}, max_tokens=5
    )
    assert completion.text == '{"a": 1}'
    assert (completion.input_tokens, completion.output_tokens) == (10, 2)
    assert completion.model == "served-model"
    assert provider.name == "anthropic" and provider.model == "m"
    call = provider._client.messages.calls[0]  # type: ignore[attr-defined]
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert call["output_config"]["effort"] == "medium"
    assert call["messages"] == [{"role": "user", "content": "u"}]


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (_Response([_Block("text", "{}")], "refusal"), "declined"),
        (_Response([_Block("text", "{")], "max_tokens"), "truncated"),
        (_Response([_Block("text", "   ")], "end_turn"), "no text"),
    ],
)
def test_sdk_provider_rejects_unusable_completions(
    response: _Response, message: str
) -> None:
    with pytest.raises(ProviderError, match=message):
        _provider(response).complete_json(system="s", user="u", schema={}, max_tokens=5)


def test_sdk_provider_translates_sdk_errors() -> None:
    import anthropic
    import httpx

    request = httpx.Request("POST", "https://example.test")
    status = anthropic.APIStatusError(
        "boom", response=httpx.Response(429, request=request), body=None
    )
    with pytest.raises(ProviderError, match="status 429"):
        _provider(status).complete_json(system="s", user="u", schema={}, max_tokens=5)
    connection = anthropic.APIConnectionError(request=request)
    with pytest.raises(ProviderError, match="unreachable"):
        _provider(connection).complete_json(
            system="s", user="u", schema={}, max_tokens=5
        )


def test_scripted_provider_records_calls_and_runs_dry() -> None:
    scripted = ScriptedProvider(['{"ok": true}'])
    completion = scripted.complete_json(
        system="sys", user="usr", schema={"x": 1}, max_tokens=3
    )
    assert completion.text == '{"ok": true}' and completion.provider == "scripted"
    assert scripted.calls[0].user == "usr" and scripted.calls[0].schema == {"x": 1}
    assert scripted.name == "scripted" and scripted.model == "scripted-model"
    with pytest.raises(ProviderError, match="no response left"):
        scripted.complete_json(system="s", user="u", schema={}, max_tokens=1)


def test_provider_from_settings_builds_sdk_clients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built: list[tuple[str, dict[str, Any]]] = []

    class _Error(Exception):
        pass

    def anthropic_factory(**kwargs: Any) -> object:
        built.append(("anthropic", kwargs))
        if kwargs.get("fail"):
            raise _Error("no key")
        return object()

    def bedrock_factory(**kwargs: Any) -> object:
        built.append(("bedrock", kwargs))
        return object()

    fake = types.SimpleNamespace(
        Anthropic=anthropic_factory,
        AnthropicBedrock=bedrock_factory,
        AnthropicError=_Error,
    )
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    anthropic_provider = provider_from_env({})
    assert isinstance(anthropic_provider, SDKProvider)
    assert anthropic_provider.model == DEFAULT_ANTHROPIC_MODEL
    bedrock_provider = provider_from_settings(
        ProviderSettings(
            "bedrock", "global.anthropic.claude-sonnet-5", "us-west-2", None
        )
    )
    assert bedrock_provider.name == "bedrock"
    assert built[1] == ("bedrock", {"aws_region": "us-west-2"})

    def failing(**kwargs: Any) -> object:
        raise _Error("no credential")

    fake.Anthropic = failing
    with pytest.raises(ProviderError, match="could not configure the anthropic client"):
        provider_from_env({})


def test_provider_from_settings_reports_missing_sdk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "anthropic", None)
    with pytest.raises(ProviderError, match="not installed"):
        provider_from_settings(ProviderSettings("anthropic", "m", None, None))
