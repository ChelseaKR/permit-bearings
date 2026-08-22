"""Readability regression gate over English plain-language explanation copy.

Plain language is a user-interface requirement of this repository, and
AGENTS.md asks for measurement to flag regressions even though no automated
score can replace human review. This gate makes that measurement enforced:

- it computes a Flesch Reading Ease score and a Flesch-Kincaid grade level
  for each rule's concatenated English explanation copy;
- it compares them against the committed baseline in
  ``scripts/readability-baseline.json``;
- it fails when any entry's copy gets harder to read beyond a small
  float-noise tolerance, or when the covered rule set changes without a
  deliberate baseline update.

The syllable heuristic is intentionally simple: the gate exists to catch
large regressions, not to grade prose. Human readability review with
applicants remains a separate, unautomated activity.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EXPLANATIONS = ROOT / "data" / "explanations" / "plain-language.json"
DEFAULT_BASELINE = Path(__file__).resolve().parent / "readability-baseline.json"

BASELINE_SCHEMA_VERSION = 1
FK_TOLERANCE = 0.25
FRE_TOLERANCE = 1.0

_VOWEL_GROUP = re.compile(r"[aeiouy]+")
_WORD = re.compile(r"[A-Za-z]+'?[A-Za-z]*")
_SENTENCE_SPLIT = re.compile(r"[.!?]+")
_NUMBER = re.compile(r"^\d+([.,]\d+)?$")


def _collect_text(value: object) -> list[str]:
    """Collect every string leaf; lists are scanned, dicts recurse."""

    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [part for item in value for part in _collect_text(item)]
    if isinstance(value, dict):
        return [part for item in value.values() for part in _collect_text(item)]
    return []


def _syllables(word: str) -> int:
    cleaned = word.lower().strip("'")
    groups = _VOWEL_GROUP.findall(cleaned)
    count = len(groups)
    if cleaned.endswith("e") and count > 1 and not cleaned.endswith(("le", "ee")):
        count -= 1
    return max(1, count)


def _words(text: str) -> list[str]:
    return [word for word in _WORD.findall(text) if not _NUMBER.fullmatch(word)]


def text_metrics(text: str) -> tuple[float, float]:
    """Return (flesch_reading_ease, fk_grade) for one block of copy."""

    sentences = [s for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    words = _words(text)
    if not words or not sentences:
        raise ValueError("readability gate: an entry has no measurable English copy")
    syllables = sum(_syllables(word) for word in words)
    words_per_sentence = len(words) / len(sentences)
    syllables_per_word = syllables / len(words)
    fre = 206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word
    fk = 0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59
    return round(fre, 2), round(fk, 2)


def entry_text(entry: dict[str, object]) -> str:
    """All English display copy for one explanation record."""

    english = entry.get("en")
    if not isinstance(english, dict):
        raise ValueError(
            "readability gate: "
            f"{entry.get('source_rule_id', '?')} has no English copy object"
        )
    return " ".join(_collect_text(english))


def measured_entries(path: Path) -> dict[str, tuple[float, float]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"{path}: expected a non-empty entries list")
    measured: dict[str, tuple[float, float]] = {}
    for entry in entries:
        rule_id = entry.get("source_rule_id")
        if not isinstance(rule_id, str) or not rule_id.strip():
            raise ValueError(f"{path}: entry missing source_rule_id")
        if rule_id in measured:
            raise ValueError(f"{path}: duplicate source_rule_id {rule_id!r}")
        measured[rule_id] = text_metrics(entry_text(entry))
    return measured


def build_baseline_payload(
    measured: dict[str, tuple[float, float]],
) -> dict[str, object]:
    return {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "generated_on": date.today().isoformat(),
        "note": (
            "Flesch Reading Ease (fre) and Flesch-Kincaid grade (fk) per rule "
            "over English explanation copy. Update only deliberately, with "
            "the diff reviewed as part of the change that moved the numbers."
        ),
        "per_rule": {
            rule_id: {"fre": fre, "fk": fk}
            for rule_id, (fre, fk) in sorted(measured.items())
        },
    }


def check(
    measured: dict[str, tuple[float, float]],
    baseline: dict[str, object],
) -> list[str]:
    failures: list[str] = []
    per_rule = baseline.get("per_rule")
    if not isinstance(per_rule, dict):
        return ["baseline is missing its per_rule mapping"]
    added = sorted(set(measured) - set(per_rule))
    removed = sorted(set(per_rule) - set(measured))
    if added:
        failures.append("entries added since baseline: " + ", ".join(added))
    if removed:
        failures.append("entries removed since baseline: " + ", ".join(removed))
    for rule_id in sorted(set(measured) & set(per_rule)):
        recorded = per_rule[rule_id]
        fre, fk = measured[rule_id]
        if (
            not isinstance(recorded, dict)
            or "fre" not in recorded
            or "fk" not in recorded
        ):
            failures.append(f"{rule_id}: baseline record is malformed")
            continue
        if fk > recorded["fk"] + FK_TOLERANCE:
            failures.append(
                f"{rule_id}: fk grade rose {recorded['fk']} -> {fk} (harder to read)"
            )
        if fre < recorded["fre"] - FRE_TOLERANCE:
            failures.append(
                f"{rule_id}: reading ease fell {recorded['fre']} -> {fre} "
                "(harder to read)"
            )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--explanations", type=Path, default=DEFAULT_EXPLANATIONS)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="recompute and rewrite the baseline; review the diff deliberately",
    )
    args = parser.parse_args(argv)

    measured = measured_entries(args.explanations)
    if args.update_baseline:
        args.baseline.write_text(
            json.dumps(build_baseline_payload(measured), ensure_ascii=True, indent=2)
            + "\n",
            encoding="utf-8",
        )
        print(f"baseline updated for {len(measured)} entr(ies); review the diff")
        return 0
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    failures = check(measured, baseline)
    if failures:
        print("readability gate: REVIEW NEEDED")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"readability gate: pass ({len(measured)} entries within baseline)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
