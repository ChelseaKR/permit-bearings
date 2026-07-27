"""Statewide jurisdiction registry.

Every California locality — 482 incorporated cities and 58 counties from
the Census 2020 FIPS place files — is a first-class jurisdiction in the
system. Statewide rules apply everywhere by construction; the registry
records, per jurisdiction, whether a local rule layer has been encoded and
any known HCD Housing Accountability Unit letter history, so coverage
claims stay honest: "statewide baseline" and "local layer encoded" are
different things and are labeled as such.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Jurisdiction:
    slug: str
    name: str
    kind: str                 # "city" | "county"
    county: str
    has_local_layer: bool
    hcd_letters: tuple


@dataclass(frozen=True)
class Coverage:
    total: int
    cities: int
    counties: int
    local_layers: int
    with_hcd_letters: int

    def summary(self) -> str:
        return (f"{self.total} California jurisdictions in registry "
                f"({self.cities} cities, {self.counties} counties); "
                f"statewide rules apply to all; local layers encoded: "
                f"{self.local_layers}; known HCD letter history: "
                f"{self.with_hcd_letters}.")


def _local_layer_slugs(rules_dir: Path) -> set:
    slugs = set()
    for path in rules_dir.glob("*.json"):
        for rule in json.loads(path.read_text()):
            scope = rule.get("jurisdiction_scope", "statewide")
            if scope != "statewide":
                slugs.add(scope)
    return slugs


def load_registry(registry_path: Path, rules_dir: Path,
                  letters_path: Path | None = None) -> list[Jurisdiction]:
    data = json.loads(registry_path.read_text())
    letters = {}
    if letters_path and letters_path.exists():
        letters = json.loads(letters_path.read_text())["letters"]
    local = _local_layer_slugs(rules_dir)
    out = []
    for rec in data["jurisdictions"]:
        out.append(Jurisdiction(
            slug=rec["slug"], name=rec["name"], kind=rec["kind"],
            county=rec["county"],
            has_local_layer=rec["slug"] in local,
            hcd_letters=tuple(letters.get(rec["slug"], []))))
    return out


def coverage(registry: list[Jurisdiction]) -> Coverage:
    return Coverage(
        total=len(registry),
        cities=sum(1 for j in registry if j.kind == "city"),
        counties=sum(1 for j in registry if j.kind == "county"),
        local_layers=sum(1 for j in registry if j.has_local_layer),
        with_hcd_letters=sum(1 for j in registry if j.hcd_letters))
