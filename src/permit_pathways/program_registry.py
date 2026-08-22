"""Program-status watcher registry for official program pages.

The Woodland availability record is bound to one dated excerpt of one
official program page. Until now, noticing that the page changed depended on
someone remembering to look. This module generalizes that tripwire: a small
registry of official program pages (preapproved-plan lists, pilot programs)
that a scheduled watcher re-fetches, classifying each page as

- ``unchanged`` — the expected excerpt is still present verbatim after the
  same normalization the availability record uses;
- ``changed`` — the page was fetched and no longer contains the expected
  excerpt; this produces a pre-written review-issue proposal and nothing
  else (no automatic adoption, no record edit, no status flip);
- ``unverifiable`` — the fetch failed; evidence about the network, not
  about the law. The last successful observation stands and nothing is
  marked stale on its account.

This module never changes matching, readiness evaluation, or availability
policies. It proposes human work; people adopt it through the existing
receipt machinery.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .dates import resolve_today
from .program_availability import normalize_excerpt

REGISTRY_SCHEMA_VERSION = 1

PAGE_STATUSES = ("unchanged", "changed", "unverifiable")

_STABLE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$")
_PAGE_KEYS = {"page_id", "label", "url", "excerpt", "excerpt_fingerprint"}
_TOP_LEVEL_KEYS = {"schema_version", "pages"}

Fetch = Callable[[str], str]


@dataclass(frozen=True)
class ProgramPage:
    """One watched official program page and its expected excerpt."""

    page_id: str
    label: str
    url: str
    excerpt: str
    excerpt_fingerprint: str


@dataclass(frozen=True)
class PageObservation:
    """One classified fetch of one registered page."""

    page_id: str
    url: str
    status: str
    detail: str


@dataclass(frozen=True)
class RegistryCheckResult:
    """One run's classifications across every registered page."""

    checked_at: str
    observations: tuple[PageObservation, ...]

    @property
    def changed_page_ids(self) -> tuple[str, ...]:
        return tuple(
            observation.page_id
            for observation in self.observations
            if observation.status == "changed"
        )

    def summary(self) -> str:
        counts = {status: 0 for status in PAGE_STATUSES}
        for observation in self.observations:
            counts[observation.status] += 1
        return (
            f"{len(self.observations)} program page(s): "
            f"{counts['unchanged']} unchanged, {counts['changed']} changed, "
            f"{counts['unverifiable']} unverifiable"
        )


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: expected non-blank text")
    return value.strip()


def _https_url(value: Any, field: str) -> str:
    text = _required_text(value, field)
    parts = urlsplit(text)
    if parts.scheme != "https" or not parts.netloc or any(c in text for c in "\r\n\t"):
        raise ValueError(f"{field}: expected a canonical HTTPS URL")
    return text


def _fingerprint(value: Any, field: str) -> str:
    text = _required_text(value, field)
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", text):
        raise ValueError(f"{field}: expected a normalized SHA-256 fingerprint")
    return text


def _exact_keys(value: Any, expected: set[str], field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected an object")
    unknown = sorted(set(value) - expected)
    missing = sorted(expected - set(value))
    if unknown:
        raise ValueError(f"{field}: unknown fields: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"{field}: missing fields: {', '.join(missing)}")
    return value


def load_program_registry(path: Path) -> list[ProgramPage]:
    """Strictly load the program-page registry at ``path``.

    Every declared fingerprint must equal the fingerprint of its own
    recorded excerpt under :func:`normalize_excerpt`, so a registry entry
    can never claim an excerpt it does not actually expect.
    """

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"program registry could not be loaded: {error}") from error
    record = _exact_keys(payload, _TOP_LEVEL_KEYS, str(path))
    if record["schema_version"] != REGISTRY_SCHEMA_VERSION:
        raise ValueError(
            f"{path}.schema_version: expected {REGISTRY_SCHEMA_VERSION}; "
            f"got {record['schema_version']!r}"
        )
    raw_pages = record["pages"]
    if not isinstance(raw_pages, list):
        raise ValueError(f"{path}.pages: expected a list")
    pages: list[ProgramPage] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_pages):
        field = f"pages[{index}]"
        data = _exact_keys(raw, _PAGE_KEYS, field)
        page_id = _required_text(data["page_id"], f"{field}.page_id")
        if not _STABLE_ID.fullmatch(page_id):
            raise ValueError(f"{field}.page_id: expected a stable identifier")
        if page_id in seen:
            raise ValueError(f"{field}: duplicate page ID {page_id!r}")
        seen.add(page_id)
        label = _required_text(data["label"], f"{field}.label")
        url = _https_url(data["url"], f"{field}.url")
        excerpt = _required_text(data["excerpt"], f"{field}.excerpt")
        fingerprint = _fingerprint(
            data["excerpt_fingerprint"], f"{field}.excerpt_fingerprint"
        )
        expected = (
            "sha256:"
            + hashlib.sha256(normalize_excerpt(excerpt).encode("utf-8")).hexdigest()
        )
        if fingerprint != expected:
            raise ValueError(
                f"{field}.excerpt_fingerprint does not match the recorded "
                "excerpt under normalization"
            )
        pages.append(
            ProgramPage(
                page_id=page_id,
                label=label,
                url=url,
                excerpt=excerpt,
                excerpt_fingerprint=fingerprint,
            )
        )
    return pages


def _default_fetch(url: str) -> str:
    import urllib.request

    request = urllib.request.Request(  # noqa: S310 - https-only by validation
        url,
        headers={"User-Agent": "permit-bearings-program-watcher/1"},
    )
    # The URL has already been validated as canonical HTTPS at load time.
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310  # nosec B310 - https-only by validation
        charset = response.headers.get_content_charset() or "utf-8"
        return str(response.read().decode(charset, errors="replace"))


def check_program_pages(
    pages: list[ProgramPage],
    *,
    fetch: Fetch | None = None,
    today: date | None = None,
) -> RegistryCheckResult:
    """Fetch and classify every registered page; propose nothing automatically."""

    resolve_today(today)
    fetcher = fetch if fetch is not None else _default_fetch
    observations: list[PageObservation] = []
    for page in pages:
        try:
            content = fetcher(page.url)
        except Exception as error:
            observations.append(
                PageObservation(
                    page_id=page.page_id,
                    url=page.url,
                    status="unverifiable",
                    detail=f"fetch failed: {type(error).__name__}",
                )
            )
            continue
        if not isinstance(content, str):
            observations.append(
                PageObservation(
                    page_id=page.page_id,
                    url=page.url,
                    status="unverifiable",
                    detail="fetch returned non-text content",
                )
            )
            continue
        if normalize_excerpt(page.excerpt) in normalize_excerpt(content):
            observations.append(
                PageObservation(
                    page_id=page.page_id,
                    url=page.url,
                    status="unchanged",
                    detail="expected excerpt still present",
                )
            )
        else:
            observations.append(
                PageObservation(
                    page_id=page.page_id,
                    url=page.url,
                    status="changed",
                    detail=(
                        "expected excerpt no longer present; candidate change "
                        "requiring human review"
                    ),
                )
            )
    checked_at = (
        datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    return RegistryCheckResult(
        checked_at=checked_at,
        observations=tuple(sorted(observations, key=lambda item: item.page_id)),
    )


def issue_proposal(page: ProgramPage, result: RegistryCheckResult) -> dict[str, str]:
    """Return the exact pre-written title and body for a changed page.

    The proposal is the whole deliverable: filing the issue, re-checking the
    source, and adopting any updated availability record remain separate,
    deliberate human steps.
    """

    observation = next(
        item for item in result.observations if item.page_id == page.page_id
    )
    title = f"Program page changed: {page.label}"
    body = "\n".join(
        [
            "The program-status watcher could no longer find the expected",
            "excerpt on this official page. This is a candidate change, not",
            "a determination: only a person can read the page and decide what",
            "it now says.",
            "",
            f"- Page ID: `{page.page_id}`",
            f"- URL: <{page.url}>",
            f'- Expected excerpt: "{page.excerpt}"',
            f"- Expected excerpt fingerprint: `{page.excerpt_fingerprint}`",
            f"- Watch result: {observation.detail}",
            "",
            "Next steps:",
            "",
            "1. Re-fetch the page manually and confirm what changed.",
            "2. If the underlying observation moved, update the linked",
            "   availability record through the existing review-and-receipt",
            "   process. Do not edit the published record directly here.",
            "3. If this was presentation-only churn that normalization missed,",
            "   record that finding and keep the current fingerprint.",
            "",
            "A changed page never marks anything stale by itself, and an",
            "unverifiable network state would have been reported separately.",
        ]
    )
    return {"page_id": page.page_id, "title": title, "body": body}


def encoded_report(result: RegistryCheckResult) -> str:
    """Stable machine-readable report for a single watch run."""

    payload = {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "checked_at": result.checked_at,
        "observations": [
            {
                "page_id": item.page_id,
                "url": item.url,
                "status": item.status,
                "detail": item.detail,
            }
            for item in result.observations
        ],
        "changed_page_ids": list(result.changed_page_ids),
    }
    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--report-out", type=Path, default=None)
    parser.add_argument("--issues-out", type=Path, default=None)
    args = parser.parse_args(argv)

    pages = load_program_registry(args.registry)
    result = check_program_pages(pages)
    report = encoded_report(result)
    if args.report_out is not None:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)
    if result.changed_page_ids and args.issues_out is not None:
        args.issues_out.mkdir(parents=True, exist_ok=True)
        by_id = {page.page_id: page for page in pages}
        for page_id in result.changed_page_ids:
            proposal = issue_proposal(by_id[page_id], result)
            target = args.issues_out / f"{page_id}.md"
            target.write_text(
                f"# {proposal['title']}\n\n{proposal['body']}\n", encoding="utf-8"
            )
    print(result.summary())
    # Exit codes mirror the source watcher's contract: 1 means review
    # needed (a fetched page moved); 2 means we could not check anything.
    statuses = {observation.status for observation in result.observations}
    if "changed" in statuses:
        return 1
    if statuses == {"unverifiable"}:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
