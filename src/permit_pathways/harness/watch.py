"""Source currency watcher.

Re-fetches every watched source document and compares its content hash to
the hash recorded when rules were last verified. A changed hash means the
source has been revised — every rule citing it must be treated as stale
until a person re-verifies the rule against the new text. Fetch failures
are reported, never swallowed: an unwatchable source is a currency problem
in itself.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from ..dates import resolve_today

FETCH_TIMEOUT_SECONDS = 30
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
        text = re.sub(r"<(script|style)\b.*?</\1>", " ", text,
                      flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = " ".join(text.split())
        content = text.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


@dataclass
class WatchResult:
    unchanged: list[str] = field(default_factory=list)   # stable source IDs
    changed: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)  # source ID -> reason

    def summary(self, labels: dict[str, str]) -> str:
        lines = ["Source currency check"]
        for source_id in self.unchanged:
            lines.append(
                f"  unchanged: {labels.get(source_id, source_id)} "
                f"[{source_id}]"
            )
        for source_id in self.changed:
            lines.append(
                f"  CHANGED:   {labels.get(source_id, source_id)} "
                f"[{source_id}] — re-verify dependent rules"
            )
        for source_id, reason in self.errors.items():
            lines.append(
                f"  ERROR:     {labels.get(source_id, source_id)} "
                f"[{source_id}] — {reason}"
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
    return value


def load_sources(
    path: Path,
    *,
    today: date | None = None,
) -> dict[str, SourceRecord]:
    """Load the URL-keyed registry as stable-ID-keyed source records."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path}: source registry could not be loaded") from error
    if not isinstance(payload, dict) or not payload:
        raise ValueError(f"{path}: expected a non-empty source object")

    as_of = resolve_today(today)
    sources: dict[str, SourceRecord] = {}
    for url, meta in payload.items():
        parsed_url = urlsplit(url) if isinstance(url, str) else None
        if (
            parsed_url is None
            or parsed_url.scheme != "https"
            or not parsed_url.hostname
            or parsed_url.username is not None
            or parsed_url.password is not None
        ):
            raise ValueError("source registry keys must be HTTPS URLs")
        if not isinstance(meta, dict):
            raise ValueError(f"{url}: expected source metadata object")
        source_id = _optional_text(meta.get("source_id"), f"{url}.source_id")
        if source_id is None or not _SOURCE_ID.fullmatch(source_id):
            raise ValueError(f"{url}.source_id: invalid stable source ID")
        if source_id in sources:
            raise ValueError(f"{source_id}: duplicate source ID")
        label = _optional_text(meta.get("label"), f"{source_id}.label")
        if label is None:
            raise ValueError(f"{source_id}.label: expected non-blank text")
        watch = meta.get("watch", True)
        if not isinstance(watch, bool):
            raise ValueError(f"{source_id}.watch: expected boolean")
        digest = _optional_text(meta.get("sha256"), f"{source_id}.sha256")
        if digest is not None and not _SHA256.fullmatch(digest):
            raise ValueError(f"{source_id}.sha256: invalid SHA-256 digest")
        fetched_on = _source_date(
            meta.get("fetched_on"), f"{source_id}.fetched_on", as_of
        )
        normalize = _optional_text(
            meta.get("normalize"), f"{source_id}.normalize"
        )
        if normalize not in (None, "html-text"):
            raise ValueError(f"{source_id}.normalize: unsupported mode")
        local_copy = _optional_text(
            meta.get("local_copy"), f"{source_id}.local_copy"
        )
        if watch and (digest is None or fetched_on is None):
            raise ValueError(
                f"{source_id}: watched source requires sha256 and fetched_on"
            )
        sources[source_id] = SourceRecord(
            source_id=source_id,
            url=url,
            label=label,
            sha256=digest,
            fetched_on=fetched_on,
            normalize=normalize,
            local_copy=local_copy,
            watch=watch,
        )
    return sources


def check_sources(
    sources_path: Path,
    *,
    today: date | None = None,
) -> WatchResult:
    sources = load_sources(sources_path, today=resolve_today(today))
    result = WatchResult()
    for source_id, source in sources.items():
        if not source.watch:
            continue
        try:
            request = urllib.request.Request(
                source.url,
                headers={"User-Agent": USER_AGENT},
            )
            with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as resp:
                digest = normalized_digest(resp.read(), source.normalize)
        except Exception as exc:  # noqa: BLE001 — any fetch failure is reportable
            result.errors[source_id] = str(exc)
            continue
        if digest == source.sha256:
            result.unchanged.append(source_id)
        else:
            result.changed.append(source_id)
    return result
