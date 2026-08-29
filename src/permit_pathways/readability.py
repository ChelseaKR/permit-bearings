"""Deterministic readability proxy for English explanation copy.

The score is a Flesch Reading Ease variant computed with a fixed
vowel-group syllable heuristic. It is a regression tripwire, not a
comprehension judgment: no formula establishes that copy is readable,
only that it did not quietly get harder. Human review with applicants
remains the only readability evidence this repository accepts.

What the committed baseline is, and what it is not
--------------------------------------------------
``data/explanations/readability-baseline.json`` was produced by this module
from the copy as it stood on the ``generated_on`` date. That is what a
baseline is; it is not independent evidence, and it says nothing about
whether the pinned scores are good. Several are not: the corpus opens
around 30, which is graduate-level prose.

It is still a gate that can fail, because ``regenerate`` and ``check`` are
separate commands and only ``check`` runs in ``make verify``. The baseline
is a committed artifact, so lowering it is a reviewable diff rather than a
side effect of running the suite. A gate that rewrote its own expectation
on every run could not report anything.

Scope limits, stated rather than implied
-----------------------------------------
* English only. Flesch Reading Ease is calibrated on English; running it
  over the Spanish drafts would produce a number with no meaning attached.
  Spanish copy needs a translation review, which this cannot substitute
  for, so no Spanish score is recorded at all.
* Every text-bearing key under ``en`` is scored, and an unrecognised key is
  a hard error rather than a silent omission. New copy that no score
  covered would leave a hole exactly where the tripwire is supposed to be.
* A rising score is not an improvement. Shorter words and shorter sentences
  move the number; clarity is not the same measurement.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast

METRIC_ID = "flesch-reading-ease-vowel-group-v1"
_BASELINE_KEYS = {
    "schema_version",
    "metric_id",
    "generated_on",
    "scores",
}
_SCORES_KEYS = {"en"}
# Every key permitted under an entry's ``en`` object. Text-bearing keys are
# scored; anything unrecognised raises, so new applicant copy cannot enter
# the repository unmeasured while the gate keeps reporting pass.
_ENGLISH_KEYS = {"title", "summary", "highlights", "next_steps", "confirm_with_staff"}
_ENGLISH_TEXT_KEYS = ("title", "summary")
_ENGLISH_LIST_KEYS = ("next_steps", "confirm_with_staff")
_HIGHLIGHT_KEYS = {"title", "items"}
_HIGHLIGHT_ITEM_KEYS = {"label", "text"}
_ISO_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_WORD = re.compile(r"[A-Za-z]+")
_SENTENCE = re.compile(r"[.!?]+")
_VOWEL_GROUP = re.compile(r"[aeiouy]+")


def _syllables(word: str) -> int:
    groups = _VOWEL_GROUP.findall(word.lower())
    count = len(groups)
    if word.lower().endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def text_score(text: str) -> float | None:
    """Return Flesch Reading Ease for one text, or None without sentences."""

    words = _WORD.findall(text)
    sentences = [s for s in _SENTENCE.split(text) if s.strip()]
    if not words or not sentences:
        return None
    syllables = sum(_syllables(word) for word in words)
    words_per_sentence = len(words) / len(sentences)
    syllables_per_word = syllables / len(words)
    return 206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word


def _highlight_text(english: dict[str, Any], parts: list[str], rule_id: str) -> None:
    highlights = english.get("highlights")
    if highlights is None:
        return
    if not isinstance(highlights, dict):
        raise ValueError(f"{rule_id}: en.highlights must be an object")
    _reject_unknown(highlights, _HIGHLIGHT_KEYS, f"{rule_id}: en.highlights")
    title = highlights.get("title")
    if isinstance(title, str):
        parts.append(title)
    items = highlights.get("items")
    if items is None:
        return
    if not isinstance(items, list):
        raise ValueError(f"{rule_id}: en.highlights.items must be a list")
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f"{rule_id}: en.highlights.items entries must be objects")
        _reject_unknown(item, _HIGHLIGHT_ITEM_KEYS, f"{rule_id}: en.highlights.items[]")
        parts.extend(
            value
            for value in (item.get(key) for key in sorted(_HIGHLIGHT_ITEM_KEYS))
            if isinstance(value, str)
        )


def _reject_unknown(record: dict[str, Any], known: set[str], field: str) -> None:
    """Refuse copy this module would not score.

    Silently skipping an unrecognised key is the failure this gate exists to
    prevent: the copy gets harder somewhere the score never looks, and the
    check keeps reporting pass. Adding a key is a deliberate decision about
    whether it is applicant-facing text.
    """

    unknown = sorted(set(record) - known)
    if unknown:
        raise ValueError(
            f"{field}: unscored copy key(s) {unknown}; add them to the "
            "readability scorer or state why they are not applicant copy"
        )


def _list_texts(
    english: dict[str, Any], key: str, parts: list[str], rule_id: str
) -> None:
    values = english.get(key)
    if values is None:
        return
    if not isinstance(values, list):
        raise ValueError(f"{rule_id}: en.{key} must be a list")
    parts.extend(value for value in values if isinstance(value, str))


def _entry_text(entry: dict[str, Any], rule_id: str) -> str:
    english = entry.get("en")
    if english is None:
        return ""
    if not isinstance(english, dict):
        raise ValueError(f"{rule_id}: en must be an object")
    _reject_unknown(english, _ENGLISH_KEYS, f"{rule_id}: en")
    parts: list[str] = []
    for key in _ENGLISH_TEXT_KEYS:
        value = english.get(key)
        if isinstance(value, str):
            parts.append(value)
    _highlight_text(english, parts, rule_id)
    for key in _ENGLISH_LIST_KEYS:
        _list_texts(english, key, parts, rule_id)
    return " ".join(parts)


def explanation_scores(
    entries: list[dict[str, Any]],
) -> dict[str, dict[str, float | None]]:
    """Score every entry's English copy, keyed by source rule ID."""

    scores: dict[str, dict[str, float | None]] = {}
    for entry in entries:
        rule_id = entry.get("source_rule_id")
        if not isinstance(rule_id, str) or not rule_id:
            raise ValueError("explanation entry: missing source_rule_id")
        if rule_id in scores:
            raise ValueError(f"{rule_id}: duplicate explanation entry")
        scores[rule_id] = {"en": text_score(_entry_text(entry, rule_id))}
    return scores


def load_explanations_payload(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path}: explanations could not be loaded") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("entries"), list):
        raise ValueError(f"{path}: expected an object with an entries list")
    entries = payload["entries"]
    if any(not isinstance(entry, dict) for entry in entries):
        raise ValueError(f"{path}: explanation entries must be objects")
    return cast(list[dict[str, Any]], entries)


def load_baseline(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path}: readability baseline could not be loaded") from error
    if not isinstance(payload, dict) or set(payload) != _BASELINE_KEYS:
        raise ValueError(f"{path}: unexpected baseline fields")
    if payload["schema_version"] != 1:
        raise ValueError(f"{path}: unsupported schema_version")
    if payload["metric_id"] != METRIC_ID:
        raise ValueError(f"{path}: baseline was generated by another metric")
    if not isinstance(payload["generated_on"], str) or not _ISO_DATE.fullmatch(
        payload["generated_on"]
    ):
        raise ValueError(f"{path}: generated_on must be an ISO date")
    scores = payload["scores"]
    if not isinstance(scores, dict) or not scores:
        raise ValueError(f"{path}: expected a non-empty scores object")
    for rule_id, score in scores.items():
        if (
            not isinstance(rule_id, str)
            or not isinstance(score, dict)
            or set(score) != _SCORES_KEYS
            or not isinstance(score["en"], (int, float))
            or isinstance(score["en"], bool)
        ):
            raise ValueError(f"{path}: invalid score record for {rule_id!r}")
    return payload


def build_baseline(scores: dict[str, dict[str, float | None]]) -> dict[str, Any]:
    """Round and order a baseline payload deterministically."""

    validated: dict[str, float] = {}
    for rule_id, score in sorted(scores.items()):
        en = score["en"]
        if en is None:
            raise ValueError(
                f"readability baseline: {rule_id} has no English copy to score"
            )
        validated[rule_id] = round(float(en), 1)
    return {
        "schema_version": 1,
        "metric_id": METRIC_ID,
        "generated_on": _today_iso(),
        "scores": {rule_id: {"en": value} for rule_id, value in validated.items()},
    }


def _today_iso() -> str:
    from .dates import utc_today

    return utc_today().isoformat()


def regressions(
    baseline: dict[str, Any],
    current: dict[str, dict[str, float | None]],
) -> list[str]:
    """Return human-readable findings for any per-rule ease drop.

    Flesch Reading Ease rises as copy gets easier, so a regression is the
    recomputed score falling below the pinned baseline. Equal or easier
    copy passes without touching the baseline.
    """

    findings: list[str] = []
    baseline_scores = baseline["scores"]
    for rule_id, score in current.items():
        en = score["en"]
        if rule_id not in baseline_scores:
            findings.append(
                f"{rule_id}: new explanation has no baseline score; "
                "run the readability CLI to extend the baseline deliberately"
            )
            continue
        if en is None:
            findings.append(f"{rule_id}: English copy disappeared")
            continue
        pinned = float(baseline_scores[rule_id]["en"])
        rounded = round(en, 1)
        if rounded < pinned:
            findings.append(
                f"{rule_id}: reading ease fell from {pinned} to {rounded}; "
                "simplify the copy or re-baseline as a recorded decision"
            )
    for rule_id in baseline_scores:
        if rule_id not in current:
            findings.append(f"{rule_id}: baseline rule no longer has explanations")
    return findings
