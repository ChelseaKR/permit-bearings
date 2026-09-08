"""Is a published ordinance scan still a claim about the document it names?

The seven ordinance texts under ``corpus/ordinances/`` were retrieved once and
scanned once. Every published result carries the date of that retrieval and a
disclaimer saying, in as many words, that *no source-currency watch monitors
the scanned ordinance for later amendment*. That sentence was true, and it is
the gap this module exists to close: a scan result for an ordinance amended
since the scan is a stale claim wearing a date, naming a real city.

The statewide sources already have a watch (:mod:`permit_pathways.harness.watch`)
and it compares **content digests**. That instrument is wrong for this corpus,
and the reason is measured rather than assumed. Re-fetching all seven on
2026-09-08 and re-extracting them with this repository's own extractor
reproduced the committed text **byte-for-byte zero times out of seven** —
municipal-code publishers reflow markup, and a PDF text extractor is not the
one that produced the committed conversion. A digest watch would therefore have
reported every source as changed on its first run, which is how a watch gets
switched off in its first week.

So the unit of comparison here is the **finding set**, not the bytes: re-scan
the fetched text with the committed checks and compare what it flags against
what the published result flags. On the same seven sources that rule reported
five unchanged and two changed, and both of the two were real. A checker whose
false-positive rate is measured before it ships is a different object from one
whose author hoped.

Five outcomes, and the last three exist so the first two cannot be misread:

* ``unchanged`` — the document was fetched, it is the document the source
  names, and it flags exactly what the published result says it flags.
* ``changed`` — same, except the checks no longer agree with the published
  result. This is a **proposal**, never an adoption: which checks newly flag
  and which stopped, with offsets, for a person to act on.
* ``unverifiable``/``transport`` — no authoritative answer arrived. Says
  nothing about the ordinance.
* ``unverifiable``/``not_found`` — the server answered that nothing is at that
  address. Evidence about the published citation, not about the law.
* ``unverifiable``/``not_the_document`` — the server answered ``200`` and the
  page is not the chapter the source names.

That last one is not hypothetical and is the reason it exists. On 2026-09-08
the recorded Angels URL answered ``200`` with a publisher migration notice
("Your municipal code is now hosted on General Code's eCode360 platform"), and
scanning that page yields **zero findings**. Treating it as content would have
published a clean bill of health for a city whose ordinance nobody read — an
absence rendered as a measurement, in the direction that lets a defect through.

The guard against it is a declared ``identifier``: the chapter or section
designation the document must carry, written down per source by a person, and
asserted to appear in the committed text as well. A page that does not carry it
is not the document, whatever its status code. An identifier that stopped
matching the committed corpus fails the local gate, so the anchor cannot quietly
stop meaning anything.

Nothing here adopts. The watch proposes; a person adopts, through the same
re-scan and review the repository already requires.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from .conformance import Check, scan
from .excerpt_survival import text_from_bytes

__all__ = [
    "EXTRACTABLE_SUFFIXES",
    "CorpusProblem",
    "OrdinanceSource",
    "SourceWatch",
    "UnverifiableKind",
    "WatchStatus",
    "corpus_problems",
    "finding_counts",
    "load_sources",
    "published_finding_counts",
    "watch_source",
]

WatchStatus = Literal["unchanged", "changed", "unverifiable"]
UnverifiableKind = Literal[
    "transport", "not_found", "not_extractable", "not_the_document"
]

#: The media types this corpus is retrieved as. Derived from the URL rather than
#: declared beside it: a declared type can disagree with the address it claims to
#: describe, and there is nothing a disagreement could mean.
EXTRACTABLE_SUFFIXES = (".html", ".htm", ".pdf")

#: Keys of a ``SOURCES.json`` entry that describe the document to a reader. The
#: published result carries exactly these, which is why adding watch metadata
#: leaves every committed artifact byte-identical.
PUBLISHED_SOURCE_FIELDS = ("title", "url", "retrieved", "note")


@dataclass(frozen=True, slots=True)
class OrdinanceSource:
    """One watched ordinance: where it came from and how to recognise it."""

    slug: str
    url: str
    suffix: str
    identifier: str
    """The chapter or section designation the document must carry.

    Written by a person, because no pattern can derive "this page is Chapter
    17.74 of the Capitola Municipal Code" from a URL. It is asserted against the
    committed text by :func:`corpus_problems`, so an identifier that has stopped
    describing the corpus fails the gate instead of silently exempting a source
    from the one check that can tell a document from a redirect notice.
    """

    text_sha256: str
    """Digest of the committed text, which is what the scanner actually reads.

    Not the digest recorded in the ``note`` prose: those are truncated hashes of
    the retrieved *pages*, and this repository does not keep those bytes, so
    nobody — human or machine — could ever check one against anything here.
    """


@dataclass(frozen=True, slots=True)
class CorpusProblem:
    """One reason the committed corpus and its provenance do not correspond."""

    slug: str
    detail: str

    def describe(self) -> str:
        return f"{self.slug}: {self.detail}"


@dataclass(frozen=True, slots=True)
class SourceWatch:
    """What one re-fetch established, and nothing more than it established."""

    slug: str
    status: WatchStatus
    kind: UnverifiableKind | None
    detail: str
    newly_flagged: tuple[tuple[str, int], ...] = ()
    """``(check_id, count)`` the current text flags and the published result
    does not, or flags more often."""
    no_longer_flagged: tuple[tuple[str, int], ...] = ()
    """``(check_id, count)`` the published result flags and the current text
    does not, or flags less often."""
    offsets: tuple[tuple[str, int], ...] = ()
    """``(check_id, offset)`` of every match in the current text, in order, so a
    maintainer reviewing a proposal can find each one without re-running it."""

    def describe(self) -> str:
        if self.status == "unverifiable":
            return f"{self.slug}: unverifiable ({self.kind}) — {self.detail}"
        if self.status == "unchanged":
            return f"{self.slug}: unchanged — {self.detail}"
        parts = [f"{self.slug}: changed — {self.detail}"]
        for check_id, count in self.newly_flagged:
            parts.append(f"    now flags {check_id} ({count} more)")
        for check_id, count in self.no_longer_flagged:
            parts.append(f"    no longer flags {check_id} ({count} fewer)")
        for check_id, offset in self.offsets:
            parts.append(f"    current match {check_id} at offset {offset}")
        return "\n".join(parts)


def _text(entry: Mapping[str, Any], slug: str, field: str) -> str:
    value = entry.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{slug}.{field}: expected non-blank text")
    return value.strip()


def load_sources(path: Path) -> dict[str, OrdinanceSource]:
    """Read ``SOURCES.json`` into watchable records, refusing a malformed one.

    A missing or blank field is an error rather than a source quietly dropped
    from the watch. A source nobody watches and nobody is told about is
    indistinguishable, in every report this produces, from a source that was
    watched and found unchanged.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not payload:
        raise ValueError(f"{path}: expected a non-empty object of sources")
    sources: dict[str, OrdinanceSource] = {}
    for slug, entry in sorted(payload.items()):
        if not isinstance(entry, Mapping):
            raise ValueError(f"{slug}: expected an object")
        watch = entry.get("watch")
        if not isinstance(watch, Mapping):
            raise ValueError(
                f"{slug}.watch: expected an object carrying identifier and "
                "text_sha256; a source with no watch metadata cannot be told "
                "apart from one that was watched and found unchanged"
            )
        url = _text(entry, slug, "url")
        suffix = Path(urlsplit(url).path).suffix.lower()
        if suffix not in EXTRACTABLE_SUFFIXES:
            raise ValueError(
                f"{slug}.url: no text extractor for {suffix or 'an unnamed type'}"
            )
        digest = _text(watch, slug, "text_sha256")
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError(f"{slug}.watch.text_sha256: expected 64 lowercase hex")
        sources[slug] = OrdinanceSource(
            slug=slug,
            url=url,
            suffix=suffix,
            identifier=_text(watch, slug, "identifier"),
            text_sha256=digest,
        )
    return sources


def corpus_problems(
    sources: Mapping[str, OrdinanceSource], corpus_dir: Path
) -> list[CorpusProblem]:
    """Everything wrong with the correspondence between provenance and bytes.

    Offline and deterministic, so it can sit in ``make bundle-check`` without
    making a merge gate depend on seven municipal-code publishers being up.

    ``scan_ordinances.py --check`` already re-derives every published result
    from these texts, which proves the results match the corpus. It cannot
    notice the *corpus* moving: an edit that no check matches changes nothing it
    compares. This pins the bytes themselves.
    """
    problems: list[CorpusProblem] = []
    on_disk = {path.stem for path in corpus_dir.glob("*.txt")}
    for slug in sorted(set(sources) | on_disk):
        source = sources.get(slug)
        path = corpus_dir / f"{slug}.txt"
        if source is None:
            problems.append(
                CorpusProblem(slug, "committed text with no entry in SOURCES.json")
            )
            continue
        if slug not in on_disk:
            problems.append(
                CorpusProblem(slug, f"SOURCES.json entry with no text at {path.name}")
            )
            continue
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != source.text_sha256:
            problems.append(
                CorpusProblem(
                    slug,
                    f"{path.name} hashes {digest}, but SOURCES.json records "
                    f"{source.text_sha256}. Either the text was edited without "
                    "re-recording it, or the record is wrong; both make every "
                    "published finding a claim about bytes nobody can identify",
                )
            )
        if source.identifier not in raw.decode("utf-8", "replace"):
            problems.append(
                CorpusProblem(
                    slug,
                    f"{path.name} does not contain the declared identifier "
                    f"{source.identifier!r}, so that identifier cannot tell this "
                    "document apart from a redirect notice served in its place",
                )
            )
    return problems


def finding_counts(findings: Iterable[Any]) -> dict[str, int]:
    """How many times each check fires, keyed by check id.

    Counts rather than a set: a chapter that drops four of its five repealed
    citations and keeps one has changed, and a set comparison would call that
    unchanged.
    """
    return dict(Counter(finding.check.check_id for finding in findings))


def published_finding_counts(result: Mapping[str, Any]) -> dict[str, int]:
    """The same counts, read off a published result rather than recomputed."""
    findings = result.get("findings")
    if not isinstance(findings, list):
        raise ValueError("published result carries no findings list")
    counted: Counter[str] = Counter()
    for finding in findings:
        if not isinstance(finding, Mapping) or not isinstance(
            finding.get("check_id"), str
        ):
            raise ValueError("published finding carries no check_id")
        counted[finding["check_id"]] += 1
    return dict(counted)


def _diff(
    published: Mapping[str, int], current: Mapping[str, int]
) -> tuple[tuple[tuple[str, int], ...], tuple[tuple[str, int], ...]]:
    gained: list[tuple[str, int]] = []
    lost: list[tuple[str, int]] = []
    for check_id in sorted(set(published) | set(current)):
        delta = current.get(check_id, 0) - published.get(check_id, 0)
        if delta > 0:
            gained.append((check_id, delta))
        elif delta < 0:
            lost.append((check_id, -delta))
    return tuple(gained), tuple(lost)


def watch_source(
    source: OrdinanceSource,
    payload: bytes | None,
    *,
    failure: tuple[UnverifiableKind, str] | None,
    published: Mapping[str, int],
    checks: Sequence[Check],
) -> SourceWatch:
    """Classify one re-fetch. Never returns ``changed`` for a failed read.

    ``payload`` is what came back, or ``None`` with ``failure`` naming why. The
    two are the only inputs: this function does no I/O, so the whole rule is
    testable against bytes on disk and the network is the caller's problem.
    """
    if payload is None:
        kind, detail = failure if failure is not None else ("transport", "no answer")
        return SourceWatch(source.slug, "unverifiable", kind, detail)

    text, reason = text_from_bytes(payload, suffix=source.suffix)
    if text is None:
        return SourceWatch(
            source.slug,
            "unverifiable",
            "not_extractable",
            reason or "the bytes carry no text this project can read",
        )
    if source.identifier not in text:
        return SourceWatch(
            source.slug,
            "unverifiable",
            "not_the_document",
            f"the page answered, and it does not carry {source.identifier!r}. "
            "It is not the chapter this source names, so it is not evidence "
            "about the ordinance either way",
        )

    findings = scan(text, list(checks))
    current = finding_counts(findings)
    gained, lost = _diff(published, current)
    offsets = tuple((f.check.check_id, f.offset) for f in findings)
    if not gained and not lost:
        return SourceWatch(
            source.slug,
            "unchanged",
            None,
            f"{sum(current.values())} finding(s), the same set the published "
            "result carries",
            offsets=offsets,
        )
    return SourceWatch(
        source.slug,
        "changed",
        None,
        "the current text does not flag what the published result says it "
        "flags; re-scan and re-adopt deliberately, or record why not",
        newly_flagged=gained,
        no_longer_flagged=lost,
        offsets=offsets,
    )
