"""Statewide jurisdiction registry.

Every California locality in the registry — 483 incorporated cities and 58
counties, built from the Census 2020 FIPS place files and supplemented for
post-vintage incorporation — is selectable. Statewide rules can be screened
for each entry by construction; the registry records, per jurisdiction,
whether a local rule layer has been encoded and any known HCD Housing
Accountability Unit letter history, so coverage claims stay honest:
"statewide baseline available" and "local layer encoded" are different
things and are labeled as such.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

COVERAGE_INDEX_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Jurisdiction:
    slug: str
    name: str
    kind: str  # "city" | "county"
    county: str
    has_local_layer: bool
    hcd_letters: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class Coverage:
    total: int
    cities: int
    counties: int
    local_layers: int
    with_hcd_letters: int

    def summary(self) -> str:
        return (
            f"{self.total} California jurisdictions in registry "
            f"({self.cities} cities, {self.counties} counties); "
            f"same statewide candidate-rule set is screenable for each; "
            f"jurisdiction-scoped records: "
            f"{self.local_layers}; known HCD letter history: "
            f"{self.with_hcd_letters}."
        )


def _read_json(path: Path, *, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path}: {label} could not be loaded") from error


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: expected non-blank text")
    return value.strip()


def _required_recorded_date(value: Any, field: str) -> str:
    """Return one canonical, non-future ISO calendar date.

    The coverage index is emitted directly into the static browser bundle.
    Validate this datum at build time as well as in the browser so a malformed
    HCD dataset cannot turn into a runtime-only failure.
    """

    recorded_on = _required_text(value, field)
    try:
        parsed = date.fromisoformat(recorded_on)
    except ValueError as error:
        raise ValueError(f"{field}: expected an ISO calendar date") from error
    if parsed.isoformat() != recorded_on:
        raise ValueError(f"{field}: expected an ISO calendar date")
    if parsed > date.today():
        raise ValueError(f"{field}: cannot be in the future")
    return recorded_on


def _registry_records(registry_path: Path) -> list[dict[str, Any]]:
    data = _read_json(registry_path, label="jurisdiction registry")
    if not isinstance(data, dict):
        raise ValueError(f"{registry_path}: expected a registry object")
    records = data.get("jurisdictions")
    if not isinstance(records, list) or not records:
        raise ValueError(f"{registry_path}.jurisdictions: expected a non-empty list")

    seen: set[str] = set()
    for index, record in enumerate(records):
        field = f"{registry_path}.jurisdictions[{index}]"
        if not isinstance(record, dict):
            raise ValueError(f"{field}: expected an object")
        slug = _required_text(record.get("slug"), f"{field}.slug")
        if slug in seen:
            raise ValueError(f"{registry_path}.jurisdictions: duplicate slug {slug!r}")
        seen.add(slug)
        _required_text(record.get("name"), f"{field}.name")
        _required_text(record.get("kind"), f"{field}.kind")
        _required_text(record.get("county"), f"{field}.county")
    return records


def _rule_ids_by_scope(rules_dir: Path) -> dict[str, list[str]]:
    """Return deterministic rule IDs keyed by jurisdiction scope.

    This reader deliberately operates on the canonical JSON rather than the
    matcher objects: the coverage index is a data-inventory artifact, not a
    second screening engine. It still rejects duplicate IDs and malformed
    scopes so a generated local-coverage claim cannot silently omit a rule.
    """

    by_scope: dict[str, list[str]] = {}
    seen_rule_ids: set[str] = set()
    files = sorted(
        path for path in rules_dir.glob("*.json") if path.name != "index.json"
    )
    if not files:
        raise ValueError(f"{rules_dir}: no canonical rule files found")
    for path in files:
        payload = _read_json(path, label="rule data")
        if not isinstance(payload, list):
            raise ValueError(f"{path}: expected a list of rules")
        for index, rule in enumerate(payload):
            field = f"{path}[{index}]"
            if not isinstance(rule, dict):
                raise ValueError(f"{field}: expected a rule object")
            rule_id = _required_text(rule.get("rule_id"), f"{field}.rule_id")
            if rule_id in seen_rule_ids:
                raise ValueError(f"duplicate rule ID {rule_id!r}")
            seen_rule_ids.add(rule_id)
            scope = _required_text(
                rule.get("jurisdiction_scope"), f"{field}.jurisdiction_scope"
            )
            by_scope.setdefault(scope, []).append(rule_id)
    return {scope: sorted(rule_ids) for scope, rule_ids in sorted(by_scope.items())}


def _validate_local_rule_scopes(
    rule_ids_by_scope: dict[str, list[str]], registry_slugs: set[str]
) -> None:
    unknown = sorted(set(rule_ids_by_scope) - {"statewide"} - registry_slugs)
    if unknown:
        raise ValueError(
            "unknown local rule scope(s) not present in the jurisdiction registry: "
            + ", ".join(unknown)
        )


def _letter_records(letters_path: Path) -> dict[str, Any]:
    payload = _read_json(letters_path, label="HCD letter dataset")
    if not isinstance(payload, dict):
        raise ValueError(f"{letters_path}: expected an HCD letter dataset object")
    letters = payload.get("letters")
    if not isinstance(letters, dict):
        raise ValueError(f"{letters_path}.letters: expected an object keyed by slug")
    for slug, records in letters.items():
        _required_text(slug, f"{letters_path}.letters key")
        if not isinstance(records, list):
            raise ValueError(f"{letters_path}.letters[{slug!r}]: expected a list")
    return payload


def _supplemental_letter_count(value: Any, field: str) -> int:
    """Count non-profile HCD rows without exposing their contents in the index."""

    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        total = 0
        for key, records in value.items():
            _required_text(key, field)
            if not isinstance(records, list):
                raise ValueError(f"{field}[{key!r}]: expected a list")
            total += len(records)
        return total
    raise ValueError(f"{field}: expected a list or object")


def build_coverage_index(
    registry_path: Path,
    rules_dir: Path,
    letters_path: Path,
) -> dict[str, Any]:
    """Build a compact statewide coverage inventory from canonical records.

    The result deliberately records only IDs and counts. In particular, HCD
    letter rows remain in their source dataset and are not classified or
    interpreted by this index. A listed statewide rule is a candidate-rule
    baseline; ``local_rule_ids`` is independently empty until a locality has
    an encoded rule record.
    """

    registry = _registry_records(registry_path)
    registry_slugs = {record["slug"] for record in registry}
    rule_ids_by_scope = _rule_ids_by_scope(rules_dir)
    _validate_local_rule_scopes(rule_ids_by_scope, registry_slugs)

    letter_data = _letter_records(letters_path)
    letters = letter_data["letters"]
    unknown_letter_slugs = sorted(set(letters) - registry_slugs)
    if unknown_letter_slugs:
        raise ValueError(
            "HCD letter dataset references unknown jurisdiction slug(s): "
            + ", ".join(unknown_letter_slugs)
        )

    retrieved_on = _required_recorded_date(
        letter_data.get("retrieved_on"), f"{letters_path}.retrieved_on"
    )
    source = _required_text(letter_data.get("source"), f"{letters_path}.source")
    letter_count = letter_data.get("letter_count")
    if (
        not isinstance(letter_count, int)
        or isinstance(letter_count, bool)
        or letter_count < 0
    ):
        raise ValueError(
            f"{letters_path}.letter_count: expected a non-negative integer"
        )

    statewide_record_count = _supplemental_letter_count(
        letter_data.get("_statewide", []), f"{letters_path}._statewide"
    )
    unmatched_record_count = _supplemental_letter_count(
        letter_data.get("_unmatched", {}), f"{letters_path}._unmatched"
    )
    profiled_record_count = sum(len(records) for records in letters.values())
    if letter_count != (
        profiled_record_count + statewide_record_count + unmatched_record_count
    ):
        raise ValueError(
            f"{letters_path}.letter_count: does not match the contained HCD records"
        )

    profiles: dict[str, dict[str, object]] = {}
    for record in sorted(registry, key=lambda item: item["slug"]):
        slug = record["slug"]
        local_rule_ids = rule_ids_by_scope.get(slug, [])
        profiles[slug] = {
            "local_rule_ids": local_rule_ids,
            "hcd_record_count": len(letters.get(slug, [])),
        }

    return {
        "schema_version": COVERAGE_INDEX_SCHEMA_VERSION,
        "statewide_rule_ids": rule_ids_by_scope.get("statewide", []),
        "hcd_dataset": {
            "retrieved_on": retrieved_on,
            "letter_count": letter_count,
            "source": source,
            "statewide_record_count": statewide_record_count,
            "unmatched_record_count": unmatched_record_count,
        },
        "profiles": profiles,
    }


def load_registry(
    registry_path: Path, rules_dir: Path, letters_path: Path | None = None
) -> list[Jurisdiction]:
    records = _registry_records(registry_path)
    letters = {}
    if letters_path and letters_path.exists():
        letters = _letter_records(letters_path)["letters"]
    rule_ids_by_scope = _rule_ids_by_scope(rules_dir)
    _validate_local_rule_scopes(
        rule_ids_by_scope,
        {record["slug"] for record in records},
    )
    local = set(rule_ids_by_scope) - {"statewide"}
    out = []
    for rec in records:
        out.append(
            Jurisdiction(
                slug=rec["slug"],
                name=rec["name"],
                kind=rec["kind"],
                county=rec["county"],
                has_local_layer=rec["slug"] in local,
                hcd_letters=tuple(letters.get(rec["slug"], [])),
            )
        )
    return out


def coverage(registry: list[Jurisdiction]) -> Coverage:
    return Coverage(
        total=len(registry),
        cities=sum(1 for j in registry if j.kind == "city"),
        counties=sum(1 for j in registry if j.kind == "county"),
        local_layers=sum(1 for j in registry if j.has_local_layer),
        with_hcd_letters=sum(1 for j in registry if j.hcd_letters),
    )
