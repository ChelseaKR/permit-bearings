"""Model providers: one narrow interface, one SDK, credentials from the environment.

Every model call in the service goes through :class:`Provider.complete_json`,
which asks for a JSON document conforming to a schema and returns the raw
text plus usage. Nothing else about the provider leaks into the rest of the
package, so the intake, explanation, and evaluation code can run against a
:class:`ScriptedProvider` in tests and against the Anthropic API or Amazon
Bedrock in production through the public ``anthropic`` SDK.

The credential is never read from a file this package writes and never
logged. A missing credential fails at startup with a message, not at the
first applicant request.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5"
DEFAULT_BEDROCK_MODEL = "global.anthropic.claude-sonnet-5"
DEFAULT_BEDROCK_REGION = "us-west-2"
PROVIDER_NAMES = ("anthropic", "bedrock")


class ProviderError(RuntimeError):
    """The model call did not produce a usable completion."""


@dataclass(frozen=True)
class Completion:
    text: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    stop_reason: str


class Provider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def model(self) -> str: ...

    def complete_json(
        self, *, system: str, user: str, schema: Mapping[str, Any], max_tokens: int
    ) -> Completion: ...


class SDKProvider:
    """Adapter over an ``anthropic`` SDK client (first-party or Bedrock)."""

    def __init__(
        self, client: Any, *, model: str, name: str, effort: str | None = None
    ) -> None:
        self._client = client
        self._model = model
        self._name = name
        self._effort = effort

    @property
    def name(self) -> str:
        return self._name

    @property
    def model(self) -> str:
        return self._model

    def complete_json(
        self, *, system: str, user: str, schema: Mapping[str, Any], max_tokens: int
    ) -> Completion:
        import anthropic

        output_config: dict[str, Any] = {
            "format": {"type": "json_schema", "schema": dict(schema)}
        }
        if self._effort:
            output_config["effort"] = self._effort
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config=output_config,
            )
        except anthropic.APIStatusError as exc:
            raise ProviderError(
                f"{self._name} request failed with status {exc.status_code}"
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise ProviderError(f"{self._name} is unreachable") from exc
        stop_reason = str(getattr(response, "stop_reason", "") or "")
        if stop_reason == "refusal":
            raise ProviderError("the model declined this request")
        if stop_reason == "max_tokens":
            raise ProviderError("the model response was truncated")
        text = "".join(
            block.text
            for block in response.content
            if getattr(block, "type", "") == "text"
        )
        if not text.strip():
            raise ProviderError("the model returned no text")
        usage = getattr(response, "usage", None)
        return Completion(
            text=text,
            provider=self._name,
            model=str(getattr(response, "model", self._model)),
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            stop_reason=stop_reason,
        )


@dataclass
class ScriptedCall:
    system: str
    user: str
    schema: dict[str, Any]
    max_tokens: int


class ScriptedProvider:
    """Returns canned JSON text in order; records every call. For tests and
    offline evaluation replay only — it is never selected from the environment."""

    def __init__(
        self, responses: Sequence[str], *, model: str = "scripted-model"
    ) -> None:
        self._responses = list(responses)
        self._model = model
        self.calls: list[ScriptedCall] = []

    @property
    def name(self) -> str:
        return "scripted"

    @property
    def model(self) -> str:
        return self._model

    def complete_json(
        self, *, system: str, user: str, schema: Mapping[str, Any], max_tokens: int
    ) -> Completion:
        self.calls.append(ScriptedCall(system, user, dict(schema), max_tokens))
        if not self._responses:
            raise ProviderError("scripted provider has no response left")
        text = self._responses.pop(0)
        return Completion(
            text=text,
            provider="scripted",
            model=self._model,
            input_tokens=0,
            output_tokens=0,
            stop_reason="end_turn",
        )


@dataclass(frozen=True)
class ProviderSettings:
    provider: str
    model: str
    region: str | None
    effort: str | None

    @classmethod
    def from_environ(cls, environ: Mapping[str, str] | None = None) -> ProviderSettings:
        env = os.environ if environ is None else environ
        provider = env.get("PERMIT_AI_PROVIDER", "anthropic").strip().lower()
        if provider not in PROVIDER_NAMES:
            raise ProviderError(
                f"PERMIT_AI_PROVIDER must be one of {', '.join(PROVIDER_NAMES)}; got {provider!r}"
            )
        default_model = (
            DEFAULT_ANTHROPIC_MODEL
            if provider == "anthropic"
            else DEFAULT_BEDROCK_MODEL
        )
        model = env.get("PERMIT_AI_MODEL", "").strip() or default_model
        region = (
            env.get("PERMIT_AI_AWS_REGION", "").strip()
            or env.get("AWS_REGION", "").strip()
            or env.get("AWS_DEFAULT_REGION", "").strip()
            or DEFAULT_BEDROCK_REGION
        )
        effort = env.get("PERMIT_AI_EFFORT", "").strip() or None
        return cls(provider, model, region if provider == "bedrock" else None, effort)


def provider_from_settings(settings: ProviderSettings) -> Provider:
    """Build the real provider. Raises :class:`ProviderError` when the SDK or
    credential is absent so the service fails at startup, not per request."""
    try:
        import anthropic
    except ImportError as exc:
        raise ProviderError(
            "the `anthropic` SDK is not installed; run `uv sync --extra ai`"
        ) from exc
    try:
        if settings.provider == "bedrock":
            client: Any = anthropic.AnthropicBedrock(aws_region=settings.region)
        else:
            client = anthropic.Anthropic()
    except anthropic.AnthropicError as exc:
        raise ProviderError(
            f"could not configure the {settings.provider} client: {exc.__class__.__name__}"
        ) from exc
    return SDKProvider(
        client, model=settings.model, name=settings.provider, effort=settings.effort
    )


def provider_from_env(environ: Mapping[str, str] | None = None) -> Provider:
    return provider_from_settings(ProviderSettings.from_environ(environ))
