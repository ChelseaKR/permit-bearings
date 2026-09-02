"""Provider adapter: settings from the environment, SDK error translation."""

from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass
from pathlib import Path
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

ROOT = Path(__file__).resolve().parents[1]


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


def test_the_bedrock_default_is_a_model_this_account_can_invoke() -> None:
    """The two provider defaults differ on purpose; hold both literals.

    Every other assertion in this file compares against the constants, so a
    wrong constant would travel through all of them unnoticed. This one names
    the strings.

    `global.anthropic.claude-sonnet-5` was the Bedrock default and is not
    invokable from this project's AWS account: `InvokeModel` answers
    `403 anthropic.claude-sonnet-5 is not available for this account`
    (verified live 2026-09-02), while the entitlement API reports it
    authorised. Bedrock is the path every committed result under
    `evals/ai/results/` actually ran on, so a Bedrock default that 403s makes
    the documented `PERMIT_AI_PROVIDER=bedrock` invocation fail with no model
    override. The Anthropic-API default is ADR 0004's settled choice and is
    not the thing to "fix" into agreement with it.
    """
    assert DEFAULT_ANTHROPIC_MODEL == "claude-sonnet-5"
    assert DEFAULT_BEDROCK_MODEL == "global.anthropic.claude-sonnet-4-6"
    assert DEFAULT_ANTHROPIC_MODEL != DEFAULT_BEDROCK_MODEL
    # The Bedrock default must name an inference profile, not a bare model id.
    assert DEFAULT_BEDROCK_MODEL.startswith("global.")
    # Selecting bedrock with nothing else set must land on that model.
    assert (
        ProviderSettings.from_environ({"PERMIT_AI_PROVIDER": "bedrock"}).model
        == DEFAULT_BEDROCK_MODEL
    )
    # Every committed live result names the model it ran on; the Bedrock
    # default has to be one of them rather than a model nothing has answered.
    recorded = {
        json.loads(path.read_text(encoding="utf-8"))["run"]["model"]
        for path in (ROOT / "evals" / "ai" / "results").glob("*.json")
        if json.loads(path.read_text(encoding="utf-8"))["run"]["status"]
        == "recorded_live_run"
    }
    assert DEFAULT_BEDROCK_MODEL in recorded


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
    assert call["system"] == [
        {"type": "text", "text": "s", "cache_control": {"type": "ephemeral"}}
    ]
    assert completion.cache_read_input_tokens == 0
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
    with pytest.raises(ProviderError, match="could not be imported"):
        provider_from_settings(ProviderSettings("anthropic", "m", None, None))
