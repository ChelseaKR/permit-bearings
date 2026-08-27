"""Source currency watcher.

Re-fetches every watched source document and compares its content hash to
the hash recorded when rules were last verified. Each watched source lands
in exactly one of three states:

* ``unchanged`` — fetched, and the hash still matches the recorded one.
* ``changed``   — fetched, and the hash differs. The source has been
  revised; every rule citing it must be treated as stale until a person
  re-verifies the rule against the new text.
* ``unverifiable`` — the fetch itself failed. This is *not* evidence about
  the content. The recorded hash and the last successful verification date
  still stand, so dependent rules keep whatever status their own review
  dates give them and are never marked stale by a failed download.

Conflating the third state with the second is what this module exists to
avoid: a runner that gets rate-limited would otherwise report every
statewide source as "changed" and flip every dependent rule to stale.
Fetch failures are still reported, never swallowed — they are just
reported as what they are.

The same argument applies once more *inside* ``unverifiable``, so every
failure also carries a ``kind``:

* ``transport`` — no authoritative answer arrived. DNS, TLS, timeout,
  connection reset, 5xx, throttling, a bot/WAF block. It says nothing
  about the document or its address.
* ``not_found`` — the server answered, and its answer was that the
  document is not at that address (HTTP 404 or 410). That is still not
  evidence that the law changed, and the retained copy and its recorded
  hash still stand. It *is* evidence about the published address: the
  citation this project prints for applicants no longer resolves, so a
  reader who follows it gets nothing. Retrying an authoritative answer is
  waste, so ``not_found`` short-circuits the retry budget.

Reporting the two together is how a local certificate-store failure and a
withdrawn city handout end up looking identical in a run summary. They are
not the same finding and they have different owners.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Literal, cast
from urllib.parse import urlsplit

from ..dates import resolve_today

FETCH_TIMEOUT_SECONDS = 30
# A scheduled run must tolerate a transient blip without crying "changed".
FETCH_ATTEMPTS = 3
FETCH_BACKOFF_SECONDS = 2.0
USER_AGENT = "permit-pathways-currency-watch/0.1"

UnverifiableKind = Literal["transport", "not_found"]
UNVERIFIABLE_KINDS: tuple[UnverifiableKind, ...] = ("transport", "not_found")
# The server answered about this exact address, and the answer was "no
# document here". 404 and 410 only: a 403 is a refusal to say, a 5xx is the
# server failing, and a 429 is throttling. Those are transport outcomes.
NOT_FOUND_HTTP_STATUSES = frozenset({404, 410})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SOURCE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def normalized_digest(content: bytes, mode: str | None) -> str:
    """Hash a fetched source. mode=None hashes raw bytes (stable documents
    like PDFs). mode="html-text" hashes the page's extracted text — needed
    for pages like leginfo statute views whose raw HTML embeds per-request
    tokens; tag stripping removes those, so the hash tracks only what the
    statute actually says."""
    if mode == "html-text":
        import re

        text = content.decode("utf-8", "replace")
        text = re.sub(
            r"<(script|style)\b.*?</\1>", " ", text, flags=re.IGNORECASE | re.DOTALL
        )
        text = re.sub(r"<[^>]+>", " ", text)
        text = " ".join(text.split())
        content = text.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


class FetchFailure(Exception):
    """A watched source could not be downloaded.

    Never carries information about whether the document's *content*
    changed, because a failed fetch tells us nothing about the content.
    ``kind`` records only how the fetch failed: ``transport`` for no
    authoritative answer, ``not_found`` for a server that answered that the
    document is not at that address.
    """

    def __init__(
        self,
        reason: str,
        *,
        kind: UnverifiableKind = "transport",
        attempts: int = 1,
    ) -> None:
        super().__init__(reason)
        self.reason = reason
        self.kind: UnverifiableKind = kind
        self.attempts = attempts


@dataclass(frozen=True)
class UnverifiableSource:
    """A watched source this run could not download.

    ``last_verified_on`` is the date the recorded hash was captured, so the
    freshness claim degrades to "last confirmed on <date>" rather than
    flipping to an alarming and unsupported "changed".

    ``kind`` separates a fetch that got no answer from one whose answer was
    that the published address holds no document. Neither stales a rule.
    """

    source_id: str
    reason: str
    last_verified_on: str | None
    attempts: int
    kind: UnverifiableKind = "transport"

    @property
    def is_not_found(self) -> bool:
        return self.kind == "not_found"

    def describe(self) -> str:
        confirmed = (
            f"last confirmed {self.last_verified_on}"
            if self.last_verified_on
            else "no recorded verification date"
        )
        if self.kind == "not_found":
            return (
                f"the published address answered {self.reason}; no document is "
                f"there; {confirmed}; the retained copy and its recorded hash "
                "still stand and no dependent rule was marked stale, but the "
                "citation link no longer resolves for a reader"
            )
        return (
            f"could not fetch after {self.attempts} "
            f"attempt{'' if self.attempts == 1 else 's'} ({self.reason}); "
            f"{confirmed}; recorded hash and dependent rules unchanged"
        )


@dataclass
class WatchResult:
    unchanged: list[str] = field(default_factory=list)  # stable source IDs
    changed: list[str] = field(default_factory=list)
    # Recorded for every successfully fetched source so a persisted receipt
    # can bind the observed bytes without re-fetching or inferring a digest.
    observed_digests: dict[str, str] = field(default_factory=dict)
    # Fetch failures. Deliberately separate from ``changed``: an unreachable
    # source is not a revised source.
    unverifiable: dict[str, UnverifiableSource] = field(default_factory=dict)

    @property
    def checked(self) -> int:
        return len(self.unchanged) + len(self.changed) + len(self.unverifiable)

    @property
    def not_found(self) -> list[str]:
        """Watched sources whose published address answered "no document"."""

        return sorted(
            source_id
            for source_id, failure in self.unverifiable.items()
            if failure.is_not_found
        )

    @property
    def unreachable(self) -> list[str]:
        """Watched sources this run could not get an answer about at all."""

        return sorted(
            source_id
            for source_id, failure in self.unverifiable.items()
            if not failure.is_not_found
        )

    def _headline(self) -> list[str]:
        lines = [
            f"  {len(self.unchanged)} unchanged, {len(self.changed)} changed, "
            f"{len(self.unverifiable)} unverifiable "
            f"(of {self.checked} watched sources)"
        ]
        if self.unverifiable:
            not_found = len(self.not_found)
            lines.append(
                f"  of the unverifiable: {len(self.unreachable)} got no answer, "
                f"{not_found} published address"
                f'{"" if not_found == 1 else "es"} answered "not found"'
            )
        return lines

    def summary(self, labels: dict[str, str]) -> str:
        lines = ["Source currency check", *self._headline()]
        for source_id in self.unchanged:
            lines.append(
                f"  unchanged:    {labels.get(source_id, source_id)} [{source_id}]"
            )
        for source_id in self.changed:
            lines.append(
                f"  CHANGED:      {labels.get(source_id, source_id)} "
                f"[{source_id}] — content differs from the recorded hash; "
                f"re-verify dependent rules"
            )
        for source_id, unverifiable in self.unverifiable.items():
            prefix = "NOT FOUND:   " if unverifiable.is_not_found else "unverifiable:"
            lines.append(
                f"  {prefix} {labels.get(source_id, source_id)} "
                f"[{source_id}] — {unverifiable.describe()}"
            )
        return "\n".join(lines)


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    url: str
    label: str
    sha256: str | None
    fetched_on: str | None
    normalize: str | None
    local_copy: str | None
    watch: bool


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: expected non-blank text or null")
    return value.strip()


def _source_date(value: Any, field: str, today: date) -> str | None:
    value = _optional_text(value, field)
    if value is None:
        return None
    if not _DATE.fullmatch(value):
        raise ValueError(f"{field}: expected YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field}: invalid date {value!r}") from error
    if parsed > today:
        raise ValueError(f"{field}: future dates are not allowed")
    return str(value)


def _load_source_payload(path: Path) -> dict[Any, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path}: source registry could not be loaded") from error
    if not isinstance(payload, dict) or not payload:
        raise ValueError(f"{path}: expected a non-empty source object")
    return payload


def _validated_source_url(value: Any) -> str:
    parsed_url = urlsplit(value) if isinstance(value, str) else None
    if (
        parsed_url is None
        or parsed_url.scheme != "https"
        or not parsed_url.hostname
        or parsed_url.username is not None
        or parsed_url.password is not None
    ):
        raise ValueError("source registry keys must be HTTPS URLs")
    return cast(str, value)


def _source_record(url: str, meta: Any, as_of: date) -> SourceRecord:
    if not isinstance(meta, dict):
        raise ValueError(f"{url}: expected source metadata object")
    source_id = _optional_text(meta.get("source_id"), f"{url}.source_id")
    if source_id is None or not _SOURCE_ID.fullmatch(source_id):
        raise ValueError(f"{url}.source_id: invalid stable source ID")
    label = _optional_text(meta.get("label"), f"{source_id}.label")
    if label is None:
        raise ValueError(f"{source_id}.label: expected non-blank text")
    watch = meta.get("watch", True)
    if not isinstance(watch, bool):
        raise ValueError(f"{source_id}.watch: expected boolean")
    digest = _optional_text(meta.get("sha256"), f"{source_id}.sha256")
    if digest is not None and not _SHA256.fullmatch(digest):
        raise ValueError(f"{source_id}.sha256: invalid SHA-256 digest")
    fetched_on = _source_date(meta.get("fetched_on"), f"{source_id}.fetched_on", as_of)
    normalize = _optional_text(meta.get("normalize"), f"{source_id}.normalize")
    if normalize not in (None, "html-text"):
        raise ValueError(f"{source_id}.normalize: unsupported mode")
    local_copy = _optional_text(meta.get("local_copy"), f"{source_id}.local_copy")
    if watch and (digest is None or fetched_on is None):
        raise ValueError(f"{source_id}: watched source requires sha256 and fetched_on")
    return SourceRecord(
        source_id=source_id,
        url=url,
        label=label,
        sha256=digest,
        fetched_on=fetched_on,
        normalize=normalize,
        local_copy=local_copy,
        watch=watch,
    )


def load_sources(
    path: Path,
    *,
    today: date | None = None,
) -> dict[str, SourceRecord]:
    """Load the URL-keyed registry as stable-ID-keyed source records."""

    as_of = resolve_today(today)
    sources: dict[str, SourceRecord] = {}
    for raw_url, meta in _load_source_payload(path).items():
        url = _validated_source_url(raw_url)
        source = _source_record(url, meta, as_of)
        if source.source_id in sources:
            raise ValueError(f"{source.source_id}: duplicate source ID")
        sources[source.source_id] = source
    return sources


def _classify_fetch_error(error: BaseException) -> tuple[str, UnverifiableKind]:
    """Render a failed fetch as a short, factual reason and its kind.

    Only an HTTP 404 or 410 is ``not_found``: the server answered about
    this exact address and said no document is there. Everything else is a
    ``transport`` outcome, including a 403 refusal and a 5xx, because those
    say nothing about whether the document is published at that address.
    """

    if isinstance(error, urllib.error.HTTPError):
        kind: UnverifiableKind = (
            "not_found" if error.code in NOT_FOUND_HTTP_STATUSES else "transport"
        )
        return f"HTTP {error.code} {error.reason}", kind
    if isinstance(error, urllib.error.URLError):
        reason = error.reason
        if isinstance(reason, TimeoutError):
            return "timed out", "transport"
        return f"network error: {reason}", "transport"
    if isinstance(error, TimeoutError):
        return "timed out", "transport"
    text = str(error).strip()
    label = f"{type(error).__name__}: {text}" if text else type(error).__name__
    return label, "transport"


def _fetch_once(source: SourceRecord) -> bytes:
    request = urllib.request.Request(
        source.url,
        headers={"User-Agent": USER_AGENT},
    )
    # The registry loader rejects non-HTTPS URLs, credentials, and missing
    # hostnames before a SourceRecord can reach this call.
    with urllib.request.urlopen(  # nosec B310
        request, timeout=FETCH_TIMEOUT_SECONDS
    ) as resp:
        status = getattr(resp, "status", None)
        if status is not None and not 200 <= int(status) < 300:
            # Belt and braces: urlopen already raises HTTPError for non-2xx,
            # but a redirect handler can surface one here too. A non-2xx body
            # is an error page, never the statute text.
            code = int(status)
            raise FetchFailure(
                f"HTTP {code}",
                kind="not_found" if code in NOT_FOUND_HTTP_STATUSES else "transport",
            )
        return cast(bytes, resp.read())


def fetch_digest(
    source: SourceRecord,
    *,
    attempts: int | None = None,
    backoff_seconds: float | None = None,
) -> str:
    """Fetch a watched source and return its normalized digest.

    Retries a small number of times with exponential backoff so a single
    blip, throttle, or handshake failure does not get misread. Raises
    :class:`FetchFailure` once the budget is spent — the caller must treat
    that as *unverifiable*, never as changed content.

    A 404 or 410 ends the loop on the first attempt. The server already
    answered about that address; asking twice more cannot change the answer
    and would only make a dead citation look like a flaky network.
    """

    budget = FETCH_ATTEMPTS if attempts is None else attempts
    backoff = FETCH_BACKOFF_SECONDS if backoff_seconds is None else backoff_seconds
    budget = max(1, budget)
    reason = "no attempt was made"
    kind: UnverifiableKind = "transport"
    attempt = 0
    for attempt in range(1, budget + 1):
        try:
            return normalized_digest(_fetch_once(source), source.normalize)
        except FetchFailure as error:
            reason, kind = error.reason, error.kind
        except Exception as error:
            # Deliberately broad: one dead source must not end the run, and
            # no fetch outcome ever maps to "changed".
            reason, kind = _classify_fetch_error(error)
        if kind == "not_found":
            break
        if attempt < budget:
            time.sleep(backoff * (2 ** (attempt - 1)))
    raise FetchFailure(reason, kind=kind, attempts=max(1, attempt))


def check_sources(
    sources_path: Path,
    *,
    today: date | None = None,
    attempts: int | None = None,
    backoff_seconds: float | None = None,
) -> WatchResult:
    """Classify every watched source as unchanged, changed, or unverifiable.

    One unreachable source never aborts the run and never contributes to
    ``changed``: the loop records it under ``unverifiable`` and moves on.
    Each unverifiable record also carries its ``kind`` so a withdrawn
    published address is not reported as a flaky network.
    """

    sources = load_sources(sources_path, today=resolve_today(today))
    budget = max(1, FETCH_ATTEMPTS if attempts is None else attempts)
    result = WatchResult()
    for source_id, source in sources.items():
        if not source.watch:
            continue
        try:
            digest = fetch_digest(
                source,
                attempts=budget,
                backoff_seconds=backoff_seconds,
            )
        except FetchFailure as failure:
            result.unverifiable[source_id] = UnverifiableSource(
                source_id=source_id,
                reason=failure.reason,
                last_verified_on=source.fetched_on,
                attempts=failure.attempts,
                kind=failure.kind,
            )
            continue
        result.observed_digests[source_id] = digest
        if digest == source.sha256:
            result.unchanged.append(source_id)
        else:
            result.changed.append(source_id)
    return result
