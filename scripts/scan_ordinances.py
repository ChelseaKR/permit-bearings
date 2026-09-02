"""Batch-scan local ordinance texts through the conformance scanner.

Drop ordinance text files at corpus/ordinances/<registry-slug>.txt (PDFs:
extract with pdftotext first) and record provenance in
corpus/ordinances/SOURCES.json. Results land at
data/conformance/results/<slug>.json plus an index the demo site reads.

The published per-slug result denormalises each matched check's title,
state_law and hcd_precedent out of data/conformance/checks.json, so editing
a check without rescanning leaves a dated, jurisdiction-named artifact that
disagrees with the checks that produced it. ``--check`` re-derives every
committed result from the committed corpus and fails when they differ, so
that drift breaks the build instead of being served.

Usage:
  python3 scripts/scan_ordinances.py <scanned-on-ISO>   # write
  python3 scripts/scan_ordinances.py --check            # verify, write nothing
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from permit_pathways.conformance import load_checks, scan  # noqa: E402

CORPUS = ROOT / "corpus/ordinances"
RESULTS = ROOT / "data/conformance/results"
INDEX = RESULTS / "index.json"
DISCLAIMER = (
    "Presence-based screening for staff/counsel review; not a certification "
    "of compliance and silence is not a clean bill of health. Point-in-time: "
    "this result reflects the ordinance text retrieved on the date in "
    "source.retrieved, which no source-currency watch monitors for amendment."
)


def corpus_slugs() -> list[str]:
    return sorted(path.stem for path in CORPUS.glob("*.txt"))


def build_results(scanned_on: Callable[[str], str]) -> dict[Path, str]:
    """Re-derive every published artifact from the committed corpus.

    ``scanned_on`` supplies the recorded scan date per slug: a fresh date
    when writing, the committed file's own date when checking, so a check
    compares derived content rather than flagging the date as drift.
    """
    checks = load_checks(ROOT / "data/conformance/checks.json")
    sources = json.loads((CORPUS / "SOURCES.json").read_text())
    registry_slugs = {
        j["slug"]
        for j in json.loads((ROOT / "data/jurisdictions/registry.json").read_text())[
            "jurisdictions"
        ]
    }

    outputs: dict[Path, str] = {}
    index = {}
    for slug in corpus_slugs():
        if slug not in registry_slugs:
            raise SystemExit(f"{slug}: not a registry slug")
        if slug not in sources:
            raise SystemExit(f"{slug}: missing provenance in SOURCES.json")
        findings = scan((CORPUS / f"{slug}.txt").read_text(), checks)
        out = {
            "slug": slug,
            "source": sources[slug],
            "scanned_on": scanned_on(slug),
            "disclaimer": DISCLAIMER,
            "findings": [
                {
                    "check_id": f.check.check_id,
                    "title": f.check.title,
                    "severity": f.check.severity,
                    "excerpt": f.excerpt,
                    "state_law": f.check.state_law,
                    "hcd_precedent": f.check.hcd_precedent,
                }
                for f in findings
            ],
        }
        outputs[RESULTS / f"{slug}.json"] = json.dumps(out, indent=1) + "\n"
        by_sev: dict[str, int] = {}
        for f in findings:
            by_sev[f.check.severity] = by_sev.get(f.check.severity, 0) + 1
        index[slug] = {
            "scanned_on": scanned_on(slug),
            "findings": len(findings),
            "by_severity": by_sev,
            "source_title": sources[slug]["title"],
        }
    outputs[INDEX] = json.dumps(index, indent=1) + "\n"
    return outputs


def committed_scan_dates(results_dir: Path = RESULTS) -> dict[str, str]:
    """The `scanned_on` each committed result records, for --check.

    A missing or unreadable result file is itself drift: the corpus carries
    an ordinance with no published scan, or one that cannot be re-derived.
    """
    dates = {}
    for slug in corpus_slugs():
        path = results_dir / f"{slug}.json"
        if not path.exists():
            raise SystemExit(
                f"{slug}: no published result at {_label(path)}; "
                f"run python3 scripts/scan_ordinances.py <scanned-on-ISO>"
            )
        try:
            recorded = json.loads(path.read_text())["scanned_on"]
        except (ValueError, KeyError) as exc:
            raise SystemExit(f"{slug}: unreadable published result ({exc})") from exc
        dates[slug] = recorded
    return dates


def recorded_scan_dates(results_dir: Path | None = None) -> dict[str, str]:
    """`scanned_on` per slug, tolerating a slug with no published result yet.

    The strict `committed_scan_dates` is for `--check`, where a missing file
    is itself drift. Writing is the case where a missing file is ordinary:
    it is how a new jurisdiction arrives.
    """
    results_dir = RESULTS if results_dir is None else results_dir
    dates: dict[str, str] = {}
    for slug in corpus_slugs():
        path = results_dir / f"{slug}.json"
        if not path.exists():
            continue
        try:
            dates[slug] = json.loads(path.read_text())["scanned_on"]
        except (ValueError, KeyError):
            # Unreadable is the same as absent here: it needs a fresh scan.
            continue
    return dates


def slugs_needing_a_new_date(
    new_date: str, results_dir: Path | None = None
) -> set[str]:
    """Slugs whose published result is absent or genuinely moved.

    A scan date says when this ordinance was scanned. Stamping one global
    date on every result each run made it say when the writer last ran, which
    is a different and much less useful fact: a reader could not tell a fresh
    scan from a file rewritten in passing while another jurisdiction was
    added. So each result is first re-derived with its own recorded date, and
    only the ones that come back different, or that have no published result,
    take the new one.
    """
    results_dir = RESULTS if results_dir is None else results_dir
    recorded = recorded_scan_dates(results_dir)
    rederived = {
        path.stem: content
        for path, content in build_results(
            lambda slug: recorded.get(slug, new_date)
        ).items()
    }
    moved = set()
    for slug in corpus_slugs():
        path = results_dir / f"{slug}.json"
        if slug not in recorded or not path.exists():
            moved.add(slug)
            continue
        if path.read_text() != rederived[slug]:
            moved.add(slug)
    return moved


def _label(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return path.name


def _differing_fields(want: object, have: object, path: str = "") -> list[str]:
    """Field paths whose published and re-derived values disagree."""
    if isinstance(want, dict) and isinstance(have, dict):
        out: list[str] = []
        for key in sorted(set(want) | set(have)):
            child = f"{path}.{key}" if path else str(key)
            out.extend(_differing_fields(want.get(key), have.get(key), child))
        return out
    if isinstance(want, list) and isinstance(have, list) and len(want) == len(have):
        out = []
        for position, (a, b) in enumerate(zip(want, have, strict=True)):
            out.extend(_differing_fields(a, b, f"{path}[{position}]"))
        return out
    return [] if want == have else [path or "(whole file)"]


def describe_drift(path: Path, expected: str, actual: str | None) -> list[str]:
    """Name the fields that moved, so the failure is actionable."""
    if actual is None:
        return [f"{_label(path)}: missing"]
    try:
        want, have = json.loads(expected), json.loads(actual)
    except ValueError:
        return [f"{_label(path)}: not valid JSON"]
    fields = _differing_fields(want, have)
    return [f"{_label(path)}:"] + [
        f"  {field}: published and re-derived values differ" for field in fields
    ]


def check_published(results_dir: Path = RESULTS) -> int:
    """Re-derive every published artifact and fail if any of them moved.

    Wired into ``make bundle-check``. `results_dir` is a seam for tests;
    production always checks the committed directory.
    """
    dates = committed_scan_dates(results_dir)
    expected = build_results(lambda slug: dates[slug])
    drift: list[str] = []
    for path, content in expected.items():
        published = results_dir / path.name
        actual = published.read_text() if published.exists() else None
        if actual != content:
            drift.extend(describe_drift(published, content, actual))
    if drift:
        print("published ordinance scan results have drifted from checks.json")
        for line in drift:
            print(line)
        print("rescan with: python3 scripts/scan_ordinances.py <scanned-on-ISO>")
        return 1
    print(
        f"published ordinance scan results match a fresh scan "
        f"({len(corpus_slugs())} jurisdiction(s) + index)"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan committed ordinance texts, or verify the published results."
    )
    parser.add_argument(
        "scanned_on",
        nargs="?",
        help="ISO date to record as the scan date (omit with --check)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if a published result differs from a fresh scan; writes nothing",
    )
    parser.add_argument(
        "--redate-all",
        action="store_true",
        help="record the new date on every result, including ones whose scan "
        "output did not move; use after a deliberate re-retrieval of the "
        "whole corpus",
    )
    args = parser.parse_args(argv)

    if args.check:
        if args.scanned_on:
            parser.error("--check re-uses each published scanned_on; pass no date")
        if args.redate_all:
            parser.error("--check writes nothing, so it cannot re-date")
        return check_published()

    if not args.scanned_on:
        parser.error("a scanned-on ISO date is required when writing")
    RESULTS.mkdir(parents=True, exist_ok=True)
    recorded = recorded_scan_dates()
    moved = (
        set(corpus_slugs())
        if args.redate_all
        else slugs_needing_a_new_date(args.scanned_on)
    )
    outputs = build_results(
        lambda slug: (
            args.scanned_on if slug in moved else recorded.get(slug, args.scanned_on)
        )
    )
    for path, content in outputs.items():
        path.write_text(content)
        print(f"wrote {_label(path)}")
    kept = sorted(set(corpus_slugs()) - moved)
    if moved:
        print(f"dated {args.scanned_on}: {', '.join(sorted(moved))}")
    if kept:
        print(f"kept their own scan date (output unchanged): {', '.join(kept)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
