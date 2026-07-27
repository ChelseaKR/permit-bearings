"""Ordinance conformance scanner.

Screens local ordinance or handout text against State ADU/SB 9 Law
invariants — the failure modes HCD's Housing Accountability Unit documents
in its findings letters. Checks are data (data/conformance/checks.json):
each carries regex screens, the controlling state law, and the HCD
enforcement letter where that failure mode actually appeared.

Presence-based only, and deliberately so: it flags candidate provisions
for staff or counsel review; it cannot detect *missing* required language
and it never certifies compliance. The output is a review queue with
citations, not a legal conclusion.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

EXCERPT_WINDOW = 120  # characters of context on each side of a match


CONTEXT_WINDOW = 300  # chars around a match searched for context patterns


@dataclass(frozen=True)
class Check:
    check_id: str
    title: str
    severity: str            # "definite" | "review"
    patterns: list[str]
    state_law: str
    explanation: str
    hcd_precedent: str
    exclude_patterns: list[str] | None = None
    context_patterns: list[str] | None = None  # one must appear near the match


@dataclass(frozen=True)
class Finding:
    check: Check
    excerpt: str
    offset: int

    def summary(self) -> str:
        flag = "FINDING" if self.check.severity == "definite" else "review"
        return (f"[{flag}] {self.check.title}\n"
                f"  matched: …{self.excerpt}…\n"
                f"  state law: {self.check.state_law}\n"
                f"  precedent: {self.check.hcd_precedent}")


def load_checks(path: Path) -> list[Check]:
    return [Check(**record) for record in json.loads(path.read_text())]


def _excluded(match: re.Match, text: str, check: Check) -> bool:
    """A match is suppressed when an exclude pattern overlaps it — e.g. the
    SB 477 stale-citation screen must not fire on § 65852.21, which is
    current SB 9 law."""
    for pattern in check.exclude_patterns or []:
        for ex in re.finditer(pattern, text, re.IGNORECASE):
            if ex.start() <= match.start() and match.end() <= ex.end():
                return True
    return False


def _in_context(match: re.Match, text: str, check: Check) -> bool:
    """When a check declares context patterns (e.g. the size-cap screen only
    applies near ADU language), at least one must appear within the window —
    otherwise a multi-topic code chapter produces noise from unrelated uses."""
    if not check.context_patterns:
        return True
    start = max(0, match.start() - CONTEXT_WINDOW)
    end = min(len(text), match.end() + CONTEXT_WINDOW)
    window = text[start:end]
    return any(re.search(p, window, re.IGNORECASE)
               for p in check.context_patterns)


def scan(text: str, checks: list[Check]) -> list[Finding]:
    findings = []
    for check in checks:
        seen_spans: list[tuple[int, int]] = []
        for pattern in check.patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                if _excluded(match, text, check):
                    continue
                if not _in_context(match, text, check):
                    continue
                if any(s <= match.start() < e for s, e in seen_spans):
                    continue
                seen_spans.append((match.start(), match.end()))
                start = max(0, match.start() - EXCERPT_WINDOW)
                end = min(len(text), match.end() + EXCERPT_WINDOW)
                excerpt = " ".join(text[start:end].split())
                findings.append(Finding(check=check, excerpt=excerpt,
                                        offset=match.start()))
    return sorted(findings, key=lambda f: f.offset)


def scan_file(ordinance_path: Path, checks_path: Path) -> list[Finding]:
    return scan(ordinance_path.read_text(), load_checks(checks_path))


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="permit_pathways.conformance",
        description="Screen ordinance text against State ADU/SB 9 Law invariants.")
    parser.add_argument("ordinance", type=Path, help="text file to scan")
    parser.add_argument("--checks", type=Path,
                        default=Path(__file__).resolve().parents[2]
                        / "data" / "conformance" / "checks.json")
    args = parser.parse_args()

    findings = scan_file(args.ordinance, args.checks)
    if not findings:
        print("No candidate provisions flagged. (Presence-based screen only — "
              "this is not a certification of compliance.)")
        return 0
    print(f"{len(findings)} provision(s) flagged for review:\n")
    for f in findings:
        print(f.summary(), end="\n\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
