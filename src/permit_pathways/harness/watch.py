"""Source currency watcher.

Re-fetches every watched source document and compares its content hash to
the hash recorded when rules were last verified. Each watched source lands
in exactly one of three states:

* ``unchanged`` — fetched, and the hash still matches the recorded one.
* ``changed``   — fetched, and the hash differs. The source has been
  revised; every rule citing it must be treated as stale until a person
  re-verifies the rule against the new text.
* ``unverifiable`` — the fetch itself failed (network error, non-2xx
  response, timeout, or a bot/WAF block). This is *not* evidence about the
  content. The recorded hash and the last successful verification date
  still stand, so dependent rules keep whatever status their own review
  dates give them and are never marked stale by a failed download.

Conflating the third state with the second is what this module exists to
avoid: a runner that gets rate-limited would otherwise report every
statewide source as "changed" and flip every dependent rule to stale.
Fetch failures are still reported, never swallowed — they are just
reported as what they are.
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
from typing import Any, cast
from urllib.parse import urlsplit

from ..dates import resolve_today

FETCH_TIMEOUT_SECONDS = 30
# A scheduled run must tolerate a transient blip without crying "changed".
FETCH_ATTEMPTS = 3
FETCH_BACKOFF_SECONDS = 2.0
USER_AGENT = "permit-pathways-currency-watch/0.1"
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

    Raised only for transport-level outcomes. It never carries information
    about whether the document's content changed, because a failed fetch
    tells us nothing about the content.
    """


@dataclass(frozen=True)
class UnverifiableSource:
    """A watched source this run could not download.

    ``last_verified_on`` is the date the recorded hash was captured, so the
    freshness claim degrades to "last confirmed on <date>" rather than
    flipping to an alarming and unsupported "changed".
    """

    source_id: str
    reason: str
    last_verified_on: str | None
    attempts: int

    def describe(self) -> str:
        confirmed = (
            f"last confirmed {self.last_verified_on}"
            if self.last_verified_on
            else "no recorded verification date"
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

    def summary(self, labels: dict[str, str]) -> str:
        lines = [
            "Source currency check",
            f"  {len(self.unchanged)} unchanged, {len(self.changed)} changed, "
            f"{len(self.unverifiable)} unverifiable "
            f"(of {self.checked} watched sources)",
        ]
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
            lines.append(
                f"  unverifiable: {labels.get(source_id, source_id)} "
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


def _describe_fetch_error(error: BaseException) -> str:
    """Render a transport failure as a short, factual reason."""

    if isinstance(error, urllib.error.HTTPError):
        return f"HTTP {error.code} {error.reason}"
    if isinstance(error, urllib.error.URLError):
        reason = error.reason
        if isinstance(reason, TimeoutError):
            return "timed out"
        return f"network error: {reason}"
    if isinstance(error, TimeoutError):
        return "timed out"
    text = str(error).strip()
    return f"{type(error).__name__}: {text}" if text else type(error).__name__


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
            raise FetchFailure(f"HTTP {status}")
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
    """

    budget = FETCH_ATTEMPTS if attempts is None else attempts
    backoff = FETCH_BACKOFF_SECONDS if backoff_seconds is None else backoff_seconds
    budget = max(1, budget)
    reason = "no attempt was made"
    for attempt in range(1, budget + 1):
        try:
            return normalized_digest(_fetch_once(source), source.normalize)
        except FetchFailure as error:
            reason = str(error)
        except Exception as error:
            # Deliberately broad: one dead source must not end the run, and
            # every transport outcome maps to "unverifiable", not "changed".
            reason = _describe_fetch_error(error)
        if attempt < budget:
            time.sleep(backoff * (2 ** (attempt - 1)))
    raise FetchFailure(reason)


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
                reason=str(failure),
                last_verified_on=source.fetched_on,
                attempts=budget,
            )
            continue
        result.observed_digests[source_id] = digest
        if digest == source.sha256:
            result.unchanged.append(source_id)
        else:
            result.changed.append(source_id)
    return result
