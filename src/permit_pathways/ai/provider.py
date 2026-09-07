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

There is a third provider, ``local``, and what it changes is not the
controls but the destination. Every mechanical guard the AI layer relies on
— allowed-value checks, verbatim quote binding, corpus verification, the
withheld counts — sits above :meth:`Provider.complete_json` and is
provider-independent. What differs between providers is where the
applicant's own words go. ``anthropic`` and ``bedrock`` send them to a
third party; ``local`` sends them to an OpenAI-compatible chat-completions
endpoint the operator runs, so a jurisdiction whose counsel will not approve
an off-host flow still has an AI option rather than none. It speaks plain
HTTP through the standard library: no second SDK, no streaming, and no
weights or runtime bundled here.

What a smaller open-weight model costs in abstention and citation resolution
is a question for ``make ai-eval``, not for this docstring. Run it against
the local provider and read the numbers; do not assume they match Bedrock's,
and do not weaken a threshold to make them.

The two providers deliberately default to different models, and that is not
drift to tidy up. ``claude-sonnet-5`` on the Anthropic API is ADR 0004's
settled choice and stays the default for a deployer with ordinary API access.
The same model is not invokable on Bedrock from this project's AWS account:
``InvokeModel`` answers ``403 anthropic.claude-sonnet-5 is not available for
this account``, verified live on 2026-09-02, and the entitlement API reporting
it authorised does not change that. Bedrock is the path every live evaluation
in ``evals/ai/results/`` actually ran on, so its default has to be a model
that answers. Change either one only against a live invocation, never against
an availability listing.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlsplit

# ADR 0004's configurable default for the public API. Do not lower this to
# match the Bedrock default below; they answer different questions.
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5"
# The newest model this project's AWS account can actually invoke on Bedrock.
# `global.` rather than `us.` is the cheaper of the two inference-profile
# prefixes and is the one every committed result in `evals/ai/results/` names.
DEFAULT_BEDROCK_MODEL = "global.anthropic.claude-sonnet-4-6"
DEFAULT_BEDROCK_REGION = "us-west-2"
PROVIDER_NAMES = ("anthropic", "bedrock", "local")
# Providers that send the applicant's own words to a third party. `local`
# is deliberately absent, and that absence is the whole point of it.
HOSTED_PROVIDER_NAMES = ("anthropic", "bedrock")
# How long to wait on a self-hosted endpoint. One explanation call takes
# 20-40 s on a hosted frontier model and can take longer on commodity local
# hardware, so this is generous; it is a ceiling, not an expectation.
DEFAULT_LOCAL_TIMEOUT_SECONDS = 180.0


def provider_kind(name: str) -> str:
    """``hosted`` or ``local`` — what a page may tell an applicant.

    The browser needs to label where the text goes without having to know
    every provider name this package might grow, so the mapping lives here
    and `/health` reports the answer rather than the raw name.
    """
    return "hosted" if name in HOSTED_PROVIDER_NAMES else "local"


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
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


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
                # The system prompt is the stable prefix of every call of a
                # kind; marking it cacheable lets the provider reuse it across
                # requests (prefixes under the provider's minimum simply do not
                # cache). Applicant content never enters the cached block.
                system=[
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
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
            cache_read_input_tokens=int(
                getattr(usage, "cache_read_input_tokens", 0) or 0
            ),
            cache_creation_input_tokens=int(
                getattr(usage, "cache_creation_input_tokens", 0) or 0
            ),
        )


class LocalProvider:
    """Adapter over an OpenAI-compatible ``/v1/chat/completions`` endpoint.

    The request shape is the same question :class:`SDKProvider` asks — one
    system prompt, one user message, a JSON schema the answer must conform
    to, a token ceiling — expressed in the other wire format. It uses
    ``urllib`` rather than a second SDK because the shape is four keys and a
    POST, and because a dependency added for an optional self-hosted path
    would ship to every deployment that never uses it.

    Two honesty notes about the schema. The endpoint is asked for
    ``response_format: json_schema``; a runtime that ignores it, or supports
    only ``json_object``, will still return prose or loosely-shaped JSON and
    the caller's own verification is what catches that. This adapter does not
    pretend the constraint was enforced, and it does not retry: a model that
    cannot hold the shape should show up in the evaluation as a worse model,
    not be papered over here.
    """

    def __init__(
        self,
        *,
        url: str,
        model: str,
        api_key: str | None = None,
        timeout: float = DEFAULT_LOCAL_TIMEOUT_SECONDS,
        opener: Any = None,
    ) -> None:
        self._url = validated_local_url(url)
        self._model = model
        self._api_key = api_key
        self._timeout = timeout
        # Injected only by tests; production always uses urllib directly.
        self._opener = opener

    @property
    def name(self) -> str:
        return "local"

    @property
    def model(self) -> str:
        return self._model

    @property
    def url(self) -> str:
        return self._url

    def _post(self, payload: bytes) -> Mapping[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "permit-bearings-ai/1",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        request = urllib.request.Request(  # noqa: S310
            self._url, data=payload, headers=headers, method="POST"
        )
        opener = self._opener or _urlopen
        try:
            status, body = opener(request, self._timeout)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ProviderError(
                f"the local endpoint at {self._url} is unreachable"
            ) from exc
        if status != 200:
            raise ProviderError(f"local request failed with status {status}")
        try:
            document = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ProviderError(
                "the local endpoint did not return a JSON document"
            ) from exc
        if not isinstance(document, Mapping):
            raise ProviderError("the local endpoint did not return a JSON object")
        return document

    def complete_json(
        self, *, system: str, user: str, schema: Mapping[str, Any], max_tokens: int
    ) -> Completion:
        payload = json.dumps(
            {
                "model": self._model,
                "max_tokens": max_tokens,
                # Some runtimes read only the newer spelling; sending both is
                # harmless and stops a silent truncation on either.
                "max_completion_tokens": max_tokens,
                # Deterministic as far as the runtime allows. This is not a
                # reproducibility claim: the same weights and sampler are the
                # operator's to pin, not this adapter's to assert.
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "permit_bearings_response",
                        "strict": True,
                        "schema": dict(schema),
                    },
                },
            },
            separators=(",", ":"),
        ).encode("utf-8")
        document = self._post(payload)
        choices = document.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderError("the local endpoint returned no choices")
        first = choices[0]
        if not isinstance(first, Mapping):
            raise ProviderError("the local endpoint returned no choices")
        finish_reason = str(first.get("finish_reason") or "")
        if finish_reason == "content_filter":
            raise ProviderError("the model declined this request")
        if finish_reason == "length":
            raise ProviderError("the model response was truncated")
        message = first.get("message")
        text = ""
        if isinstance(message, Mapping):
            content = message.get("content")
            if isinstance(content, str):
                text = content
        if not text.strip():
            raise ProviderError("the model returned no text")
        usage = document.get("usage")
        usage_map: Mapping[str, Any] = usage if isinstance(usage, Mapping) else {}
        return Completion(
            text=text,
            provider="local",
            model=str(document.get("model") or self._model),
            input_tokens=_token_count(usage_map.get("prompt_tokens")),
            output_tokens=_token_count(usage_map.get("completion_tokens")),
            stop_reason=finish_reason or "stop",
        )


def _urlopen(request: urllib.request.Request, timeout: float) -> tuple[int, bytes]:
    with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310  # noqa: S310
        return int(response.status), response.read()


def _token_count(value: Any) -> int:
    """A usage field a runtime did not send is zero, and says so.

    It is not evidence that the call was free. `budget.py` counts requests,
    not tokens, so a missing count cannot silently buy anyone a larger
    allowance; recording it as 0 keeps the shape rather than inventing a
    number.
    """
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def validated_local_url(value: str) -> str:
    """Reject anything that is not a plain HTTP(S) endpoint without credentials.

    The value is operator configuration rather than applicant input, so this
    is not an injection boundary; it exists so that a typo, a `file://` path
    or a URL with an inline password fails at startup with a sentence instead
    of at the first request with a stack trace.
    """
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ProviderError(
            "PERMIT_AI_LOCAL_URL must be an HTTP(S) URL without credentials or "
            f"a fragment; got {value!r}"
        )
    return value


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
    local_url: str | None = None

    @property
    def kind(self) -> str:
        return provider_kind(self.provider)

    @classmethod
    def from_environ(cls, environ: Mapping[str, str] | None = None) -> ProviderSettings:
        env = os.environ if environ is None else environ
        provider = env.get("PERMIT_AI_PROVIDER", "anthropic").strip().lower()
        if provider not in PROVIDER_NAMES:
            raise ProviderError(
                f"PERMIT_AI_PROVIDER must be one of {', '.join(PROVIDER_NAMES)}; got {provider!r}"
            )
        model = env.get("PERMIT_AI_MODEL", "").strip()
        if provider == "local":
            # No default model, on purpose. Every self-hosted runtime serves
            # something different, and a guessed name would reach the endpoint
            # as a request for a model it does not have — an error about the
            # wrong thing, at the first applicant request rather than at
            # startup.
            if not model:
                raise ProviderError(
                    "PERMIT_AI_MODEL is required with PERMIT_AI_PROVIDER=local: "
                    "there is no default model name a self-hosted endpoint would serve"
                )
            url = env.get("PERMIT_AI_LOCAL_URL", "").strip()
            if not url:
                raise ProviderError(
                    "PERMIT_AI_LOCAL_URL is required with PERMIT_AI_PROVIDER=local"
                )
            return cls(provider, model, None, None, validated_local_url(url))
        default_model = (
            DEFAULT_ANTHROPIC_MODEL
            if provider == "anthropic"
            else DEFAULT_BEDROCK_MODEL
        )
        model = model or default_model
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
    if settings.provider == "local":
        if not settings.local_url:
            raise ProviderError(
                "PERMIT_AI_LOCAL_URL is required with PERMIT_AI_PROVIDER=local"
            )
        # An optional shared secret for an endpoint on the jurisdiction's own
        # network. Absent is the normal case for a loopback runtime, and
        # absent means no Authorization header rather than an empty one.
        api_key = os.environ.get("PERMIT_AI_LOCAL_API_KEY", "").strip() or None
        return LocalProvider(
            url=settings.local_url, model=settings.model, api_key=api_key
        )
    try:
        import anthropic
    except ImportError as exc:
        raise ProviderError(
            f"the `anthropic` SDK could not be imported ({exc}); run `uv sync --extra ai`"
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
