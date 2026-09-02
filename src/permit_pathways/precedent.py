"""Comparable-jurisdiction precedent from the committed HCD letter dataset.

`AGENTS.md` priority 4 includes comparable-jurisdiction discovery, and
`docs/PRODUCT-CONTEXT.md` records it as a P1 opportunity: "Converts the
existing HCD-letter dataset into a useful Scenario C workflow." The dataset is
already in the repository. `data/jurisdictions/hcd-letters.json` holds 1,314
letters keyed to 470 of the 541 registry entries, retrieved 2026-08-03, and
nothing here fetches anything.

What this answers, for a maintainer or a staff planner looking at one
jurisdiction: which other jurisdictions HCD wrote to about the same authority
and the same kind of letter, so the reader can go and read those letters. That
is discovery of documented precedent, and nothing more.

What it does not answer, and cannot:

- Whether any jurisdiction is compliant. `AGENTS.md` ranks HCD letters as
  "documented precedent, not controlling authority for every jurisdiction",
  and `docs/PRODUCT-CONTEXT.md` says not to turn a linked letter, or the
  absence of one, into a compliance, enforcement, or local-coverage
  conclusion.
- Whether a jurisdiction with no letter has no HCD activity. It means the
  dated snapshot linked none.
- Whether a letter is still operative. Each row carries its own date, and the
  snapshot has a retrieval date; neither is a currency check, and no watcher
  monitors an individual letter for later action.
- Anything about the text of a local ordinance. This reads correspondence
  metadata, not code.

Read-only. It loads two committed files, prints, and writes nothing.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LETTERS = ROOT / "data" / "jurisdictions" / "hcd-letters.json"
DEFAULT_REGISTRY = ROOT / "data" / "jurisdictions" / "registry.json"

EXIT_OK = 0
EXIT_INVALID = 2

#: Every rendering carries this. A precedent list that a reader could mistake
#: for a compliance finding would be worse than no list.
BOUNDARY = (
    "HCD correspondence is documented precedent, not controlling authority "
    "for another jurisdiction and not a compliance finding. A jurisdiction "
    "with no row here is one the dated snapshot linked no letter to, which is "
    "not evidence of compliance or of no HCD activity. Read the letters."
)

_REQUIRED_LETTER_FIELDS = ("date", "kind", "authority", "subject", "url")


@dataclass(frozen=True)
class Letter:
    """One row of the HCD accountability dashboard, as committed."""

    jurisdiction: str
    date: str | None
    kind: str
    authority: str | None
    statutes: str | None
    subject: str
    url: str | None
    hau_number: str | None


@dataclass(frozen=True)
class LetterSet:
    """The committed snapshot, with the provenance a citation needs."""

    source: str
    retrieved_on: str
    letters: tuple[Letter, ...]

    def jurisdictions(self) -> set[str]:
        return {letter.jurisdiction for letter in self.letters}


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"expected text or null, got {type(value).__name__}")
    return value


def _letter(slug: str, entry: Any) -> Letter:
    """One validated row. A shape this cannot describe is rejected, not
    coerced: a letter silently dropped would understate a jurisdiction's
    correspondence, and a blank kind would land in a group nobody asked for."""

    if not isinstance(entry, dict):
        raise ValueError(f"{slug}: each letter must be an object")
    for field in _REQUIRED_LETTER_FIELDS:
        if field not in entry:
            raise ValueError(f"{slug}: letter is missing {field!r}")
    kind = _text(entry["kind"])
    if not kind or not kind.strip():
        raise ValueError(f"{slug}: letter kind cannot be blank")
    return Letter(
        jurisdiction=slug,
        date=_text(entry["date"]),
        kind=kind,
        authority=_text(entry["authority"]),
        statutes=_text(entry.get("statutes")),
        subject=_text(entry["subject"]) or "",
        url=_text(entry["url"]),
        hau_number=_text(entry.get("hau_number")),
    )


def load_letters(path: Path = DEFAULT_LETTERS) -> LetterSet:
    """Load the committed dataset, rejecting a shape it cannot describe."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("letters dataset must be an object")
    for field in ("source", "retrieved_on", "letters"):
        if field not in payload:
            raise ValueError(f"letters dataset is missing {field!r}")
    keyed = payload["letters"]
    if not isinstance(keyed, dict):
        raise ValueError("letters must be keyed by jurisdiction slug")
    rows: list[Letter] = []
    for slug, entries in sorted(keyed.items()):
        if not isinstance(entries, list):
            raise ValueError(f"{slug}: letters must be a list")
        rows.extend(_letter(slug, entry) for entry in entries)
    return LetterSet(
        source=str(payload["source"]),
        retrieved_on=str(payload["retrieved_on"]),
        letters=tuple(rows),
    )


def load_names(path: Path = DEFAULT_REGISTRY) -> dict[str, str]:
    """Slug to display name, so output names jurisdictions the way people do."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return {entry["slug"]: entry["name"] for entry in payload["jurisdictions"]}


def kind_counts(letters: LetterSet) -> list[tuple[str, int, int]]:
    """(kind, letters, jurisdictions), most letters first."""

    per_kind: Counter[str] = Counter()
    per_kind_jurisdictions: dict[str, set[str]] = {}
    for letter in letters.letters:
        per_kind[letter.kind] += 1
        per_kind_jurisdictions.setdefault(letter.kind, set()).add(letter.jurisdiction)
    return sorted(
        (
            (kind, count, len(per_kind_jurisdictions[kind]))
            for kind, count in per_kind.items()
        ),
        key=lambda row: (-row[1], row[0]),
    )


def with_kind(
    letters: LetterSet,
    kind: str,
    authority: str | None = None,
) -> list[Letter]:
    """Every letter of one kind, optionally narrowed to one authority."""

    return sorted(
        (
            letter
            for letter in letters.letters
            if letter.kind == kind
            and (authority is None or letter.authority == authority)
        ),
        key=lambda letter: (letter.jurisdiction, letter.date or "", letter.kind),
    )


def comparable(
    letters: LetterSet,
    slug: str,
    limit: int | None = None,
) -> dict[tuple[str, str | None], list[Letter]]:
    """Other jurisdictions' letters sharing a (kind, authority) with `slug`.

    The grouping key is what makes this precedent rather than a directory: two
    jurisdictions that both received an ADU-Law repeal request are comparable
    in a way that two jurisdictions on the same list are not.

    `limit` caps each group. A capped group is still a complete count, because
    the caller is told the total; see `comparable_totals`.
    """

    own = [letter for letter in letters.letters if letter.jurisdiction == slug]
    keys = {(letter.kind, letter.authority) for letter in own}
    groups: dict[tuple[str, str | None], list[Letter]] = {}
    for letter in letters.letters:
        if letter.jurisdiction == slug:
            continue
        key = (letter.kind, letter.authority)
        if key in keys:
            groups.setdefault(key, []).append(letter)
    for key, rows in groups.items():
        rows.sort(key=lambda letter: (letter.date or "", letter.jurisdiction))
        rows.reverse()
        if limit is not None:
            groups[key] = rows[:limit]
    return groups


def comparable_totals(
    letters: LetterSet,
    slug: str,
) -> dict[tuple[str, str | None], int]:
    """Full group sizes, so a capped listing can say what it did not print."""

    own = [letter for letter in letters.letters if letter.jurisdiction == slug]
    keys = {(letter.kind, letter.authority) for letter in own}
    totals: Counter[tuple[str, str | None]] = Counter()
    for letter in letters.letters:
        if letter.jurisdiction == slug:
            continue
        key = (letter.kind, letter.authority)
        if key in keys:
            totals[key] += 1
    return dict(totals)


def _provenance(letters: LetterSet) -> str:
    return (
        f"Source: {letters.source}\n"
        f"Snapshot retrieved {letters.retrieved_on}. "
        f"{len(letters.letters)} letters across "
        f"{len(letters.jurisdictions())} jurisdictions.\n"
        f"{BOUNDARY}"
    )


def _render_letter(letter: Letter, names: dict[str, str]) -> str:
    label = names.get(letter.jurisdiction, letter.jurisdiction)
    parts = [f"  {letter.date or 'undated'}  {label}"]
    if letter.statutes:
        parts.append(f"    statutes: {letter.statutes}")
    if letter.subject:
        parts.append(f"    subject: {letter.subject}")
    if letter.url:
        parts.append(f"    {letter.url}")
    return "\n".join(parts)


def render_kinds(letters: LetterSet) -> str:
    lines = ["Letter kinds in the committed snapshot", ""]
    for kind, count, jurisdictions in kind_counts(letters):
        lines.append(f"  {count:5d} letters  {jurisdictions:4d} jurisdictions  {kind}")
    lines.extend(["", _provenance(letters)])
    return "\n".join(lines)


def render_kind_listing(
    letters: LetterSet,
    names: dict[str, str],
    kind: str,
    authority: str | None = None,
) -> str:
    rows = with_kind(letters, kind, authority)
    scope = f"{kind}" + (f", {authority}" if authority else "")
    if not rows:
        return "\n".join(
            [
                f"No letter in the committed snapshot has kind {kind!r}"
                + (f" under authority {authority!r}" if authority else ""),
                "",
                _provenance(letters),
            ]
        )
    jurisdictions = sorted({letter.jurisdiction for letter in rows})
    lines = [
        f"{scope}",
        f"{len(rows)} letters across {len(jurisdictions)} jurisdictions",
        "",
    ]
    for letter in rows:
        lines.append(_render_letter(letter, names))
    lines.extend(["", _provenance(letters)])
    return "\n".join(lines)


def render_comparable(
    letters: LetterSet,
    names: dict[str, str],
    slug: str,
    limit: int,
) -> str:
    label = names.get(slug, slug)
    own = [letter for letter in letters.letters if letter.jurisdiction == slug]
    lines = [f"Comparable HCD precedent for {label} ({slug})", ""]
    if not own:
        lines.extend(
            [
                f"The committed snapshot links no letter to {label}.",
                "That is a fact about this dated snapshot, not about the",
                "jurisdiction: it is not evidence of compliance, and not",
                "evidence that HCD has not written to them.",
                "",
                _provenance(letters),
            ]
        )
        return "\n".join(lines)

    lines.append(f"{label} received {len(own)} letter(s):")
    for letter in sorted(own, key=lambda item: (item.date or "", item.kind)):
        lines.append(f"  {letter.date or 'undated'}  {letter.kind}")
        lines.append(f"    authority: {letter.authority or 'unrecorded'}")
        if letter.url:
            lines.append(f"    {letter.url}")
    lines.append("")

    groups = comparable(letters, slug, limit=limit)
    totals = comparable_totals(letters, slug)
    if not groups:
        lines.append(
            "No other jurisdiction in the snapshot shares a letter kind and "
            "authority with this one."
        )
        lines.extend(["", _provenance(letters)])
        return "\n".join(lines)

    lines.append("Other jurisdictions with the same kind and authority:")
    for key in sorted(groups, key=lambda item: (-totals[item], item[0])):
        kind, authority = key
        total = totals[key]
        shown = groups[key]
        lines.append("")
        lines.append(f"  {kind} | {authority or 'unrecorded authority'}")
        header = f"  {total} other jurisdiction letter(s)"
        if total > len(shown):
            header += f"; showing the {len(shown)} most recent"
        lines.append(header)
        for letter in shown:
            lines.append(_render_letter(letter, names))
    lines.extend(["", _provenance(letters)])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="permit_pathways.precedent",
        description=(
            "Read-only comparable-jurisdiction discovery over the committed "
            "HCD accountability letter snapshot. Fetches nothing, writes "
            "nothing, and makes no compliance finding."
        ),
    )
    parser.add_argument("--letters", type=Path, default=DEFAULT_LETTERS)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "kinds", help="letter kinds and how many jurisdictions received each"
    )

    listing = sub.add_parser("list", help="every letter of one kind")
    listing.add_argument("--kind", required=True)
    listing.add_argument("--authority", default=None)

    for_one = sub.add_parser(
        "for", help="one jurisdiction's letters and comparable precedent"
    )
    for_one.add_argument("slug")
    for_one.add_argument(
        "--limit",
        type=int,
        default=10,
        help="most recent letters to print per comparable group (default 10)",
    )

    args = parser.parse_args(argv)
    try:
        letters = load_letters(args.letters)
        names = load_names(args.registry)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"cannot read the committed dataset: {exc}")
        return EXIT_INVALID

    if args.command == "kinds":
        print(render_kinds(letters))
        return EXIT_OK
    if args.command == "list":
        print(render_kind_listing(letters, names, args.kind, args.authority))
        return EXIT_OK
    if args.limit < 1:
        print("--limit must be at least 1")
        return EXIT_INVALID
    if args.slug not in names:
        print(
            f"{args.slug!r} is not a registry slug. "
            f"The registry holds {len(names)} California jurisdictions."
        )
        return EXIT_INVALID
    print(render_comparable(letters, names, args.slug, args.limit))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
