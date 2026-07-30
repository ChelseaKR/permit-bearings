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
from pathlib import Path
from typing import Any


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


def _local_layer_slugs(rules_dir: Path) -> set[str]:
    slugs: set[str] = set()
    for path in sorted(rules_dir.glob("*.json")):
        if path.name == "index.json":
            continue
        payload = json.loads(path.read_text())
        if not isinstance(payload, list):
            raise ValueError(f"{path}: expected a list of rules")
        for rule in payload:
            if not isinstance(rule, dict):
                raise ValueError(f"{path}: expected rule objects")
            scope = rule.get("jurisdiction_scope", "statewide")
            if scope != "statewide":
                slugs.add(scope)
    return slugs


def load_registry(
    registry_path: Path, rules_dir: Path, letters_path: Path | None = None
) -> list[Jurisdiction]:
    data = json.loads(registry_path.read_text())
    letters = {}
    if letters_path and letters_path.exists():
        letters = json.loads(letters_path.read_text())["letters"]
    local = _local_layer_slugs(rules_dir)
    out = []
    for rec in data["jurisdictions"]:
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
