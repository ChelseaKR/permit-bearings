"""The what-if explorer, and the four boundaries it must not lose.

The interesting assertions here are not "a delta was produced". They are the
three states where a delta would be a lie: a branch that still has an
unanswered material fact, a fact every rule reads the same way, and a fact read
by a rule whose source is on review hold.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from permit_pathways.screening import load_rules
from permit_pathways.what_if import (
    WHAT_IF_SCHEMA_VERSION,
    WITHHELD_SOURCE_HOLD,
    applicable_rules,
    held_rule_ids,
    rules_reading,
    what_if,
)

ROOT = Path(__file__).resolve().parents[1]
RULES = load_rules(ROOT / "data" / "rules")
GOLDEN: list[dict[str, Any]] = json.loads(
    (ROOT / "data" / "golden" / "example.json").read_text(encoding="utf-8")
)
WOODLAND_FIXTURE: dict[str, Any] = json.loads(
    (ROOT / "tests" / "fixtures" / "what-if-woodland.json").read_text(encoding="utf-8")
)
AS_OF = "2026-09-07"


def intake_for(case_id: str) -> dict[str, Any]:
    matching = [case for case in GOLDEN if case["case_id"] == case_id]
    assert len(matching) == 1, case_id
    return dict(matching[0]["intake"])


def explore(case_id: str, source_state: dict[str, Any] | None = None) -> dict[str, Any]:
    return what_if(
        intake=intake_for(case_id),
        rules=RULES,
        as_of=AS_OF,
        source_state=source_state,
    )


def fact(payload: dict[str, Any], field: str) -> dict[str, Any]:
    matching = [entry for entry in payload["facts"] if entry["field"] == field]
    assert len(matching) == 1, field
    return matching[0]


def alternative(entry: dict[str, Any], value: str) -> dict[str, Any]:
    matching = [item for item in entry["alternatives"] if item["value"] == value]
    assert len(matching) == 1, value
    return matching[0]


def test_woodland_deltas_match_the_committed_fixture() -> None:
    """The issue's own acceptance case, against hand-written expectations."""
    payload = explore(WOODLAND_FIXTURE["case_id"])
    assert payload["facts"] == WOODLAND_FIXTURE["facts"]
    assert payload["what_if_schema_version"] == WHAT_IF_SCHEMA_VERSION


def test_the_envelope_carries_its_own_schema_version() -> None:
    """Not the screening envelope's. They describe different documents, and
    moving the screening version for a change here would tell every screening
    consumer their contract had changed when it had not."""
    from permit_pathways.screening_contract import SCHEMA_VERSION

    payload = explore("woodland-new-detached-adu-local-layer")
    assert "schema_version" not in payload
    assert payload["what_if_schema_version"] == WHAT_IF_SCHEMA_VERSION
    assert SCHEMA_VERSION == 1


def test_an_unknown_branch_needs_staff_review_and_shows_no_route() -> None:
    payload = explore("woodland-new-detached-adu-local-layer")
    branch = alternative(fact(payload, "adu_project_form"), "unknown")
    assert branch["decision_boundary"] == "needs_staff_review"
    assert branch["unresolved_facts"] == ["adu_project_form"]
    assert branch["candidate_routes"] == []
    # The point of the case: the matched rules do not move at all, so a reader
    # of rule deltas alone would conclude that not answering costs nothing.
    assert branch["rules_added"] == []
    assert branch["rules_removed"] == []
    assert branch["routes_removed"] == ["ministerial"]


def test_a_baseline_that_already_needs_review_still_explores() -> None:
    payload = explore("adu-project-form-unknown")
    assert payload["baseline"]["decision_boundary"] == "needs_staff_review"
    assert payload["baseline"]["candidate_routes"] == []
    answered = alternative(fact(payload, "adu_project_form"), "new_detached")
    assert answered["decision_boundary"] == "candidate_rules_only"
    # Routes appear relative to a baseline that withheld them, which is the
    # question an applicant with an unanswered fact is actually asking.
    assert answered["routes_added"] == ["ministerial"]


def test_one_answer_does_not_clear_a_second_unknown() -> None:
    """Single-fact perturbation is the whole contract, and this is where it
    shows: `adu-primary-status-unknown` leaves two facts unanswered, so
    answering either one still lands in needs_staff_review with no route. A
    what-if that reported a route here would be answering a question the
    applicant has not answered."""
    payload = explore("adu-primary-status-unknown")
    answered = alternative(
        fact(payload, "primary_dwelling_status"), "existing_single_family"
    )
    assert answered["decision_boundary"] == "needs_staff_review"
    assert answered["unresolved_facts"] == ["unpermitted_existing"]
    assert answered["candidate_routes"] == []
    assert answered["routes_added"] == []
    # The rules it would add are still reported; only the route is withheld.
    assert answered["rules_added"]


def test_a_fact_no_rule_reads_differently_is_reported_not_omitted() -> None:
    """`sb9-duplex-tenant-occupied` already answers a disqualifying fact, so
    nothing else it says changes which rules match."""
    payload = explore("sb9-duplex-tenant-occupied")
    entry = fact(payload, "in_urbanized_area")
    assert entry["no_rule_reads_this_differently"] is True
    assert entry["read_by_rule_ids"], "the fact is read by rules; they just agree"
    assert all(
        item["rules_added"] == [] and item["rules_removed"] == []
        for item in entry["alternatives"]
    )
    # Reported, not dropped.
    assert entry["field"] in [item["field"] for item in payload["facts"]]


def test_a_fact_that_does_change_rules_is_not_marked_as_agreeing() -> None:
    payload = explore("woodland-new-detached-adu-local-layer")
    assert fact(payload, "adu_project_form")["no_rule_reads_this_differently"] is False


def test_a_fact_read_by_a_held_rule_gets_null_deltas_not_empty_ones() -> None:
    """`ca-gov-66311-7` is the only source under the two legalization rules,
    and those are the only rules reading `unpermitted_existing`.

    Both are named as held, including the JADU one, which cannot match an ADU
    intake as encoded today. That is deliberate and is the fail-closed reading
    of a source hold: a hold says the *encoding* may no longer match its
    source, so filtering the hold set down to rules that match under the
    current encoding would assume the very thing the hold puts in doubt.
    """
    snapshot = {
        "snapshot_id": "test-hold",
        "checked_at": "2026-09-07T00:00:00Z",
        "changed_source_ids": ["ca-gov-66311-7"],
        "unverifiable_source_ids": [],
        "affected_rule_ids": [],
        "receipt": {"status": "reviewed"},
    }
    payload = explore("woodland-new-detached-adu-local-layer", snapshot)

    held = fact(payload, "unpermitted_existing")
    assert held["deltas_withheld"] == WITHHELD_SOURCE_HOLD
    assert held["rules_on_source_hold"] == [
        "adu-unpermitted-legalization",
        "jadu-unpermitted-legalization",
    ]
    for item in held["alternatives"]:
        # null, never []: an empty delta reads as "this answer changes
        # nothing", which is a finding a held rule set cannot support.
        assert item["rules_added"] is None
        assert item["rules_removed"] is None
        assert item["routes_added"] is None
        assert item["routes_removed"] is None
        assert item["candidate_routes"] is None
    assert held["no_rule_reads_this_differently"] is None
    # The boundary is a property of the intake, so the hold cannot hide it.
    assert alternative(held, "unknown")["decision_boundary"] == "needs_staff_review"

    # And the hold is displayed rather than left for a reader to infer.
    assert any("No delta is reported for" in notice for notice in payload["notices"])

    # Facts no held rule reads keep their deltas.
    unheld = fact(payload, "adu_project_form")
    assert unheld["deltas_withheld"] is None
    assert alternative(unheld, "conversion")["rules_added"] == [
        "adu-conversion-exemptions"
    ]


def test_two_held_facts_are_named_in_one_notice() -> None:
    snapshot = {
        "snapshot_id": "test-hold",
        "changed_source_ids": ["ca-gov-66314"],
        "receipt": {"status": "reviewed"},
    }
    payload = explore("woodland-new-detached-adu-local-layer", snapshot)
    withheld = [
        entry["field"] for entry in payload["facts"] if entry["deltas_withheld"]
    ]
    assert withheld == ["primary_dwelling_status", "adu_project_form"]
    notice = next(n for n in payload["notices"] if "No delta is reported" in n)
    assert "each of those facts" in notice


def test_a_silent_snapshot_holds_nothing_and_says_so() -> None:
    """`changed_source_ids: null` is "the snapshot did not report", which is
    not "nothing changed" — the screening envelope already publishes that
    distinction as a notice, and this reuses it rather than restating it."""
    payload = explore(
        "woodland-new-detached-adu-local-layer",
        {"snapshot_id": "silent", "receipt": {"status": "reviewed"}},
    )
    assert payload["source_state"]["changed_source_ids"] is None
    assert all(entry["deltas_withheld"] is None for entry in payload["facts"])
    assert any("does not record" in notice for notice in payload["notices"])


def test_held_rule_ids_treats_absent_and_empty_alike_but_documents_why() -> None:
    assert held_rule_ids(RULES, None) == frozenset()
    assert held_rule_ids(RULES, []) == frozenset()
    assert "adu-unpermitted-legalization" in held_rule_ids(RULES, ["ca-gov-66311-7"])


def test_scope_and_reading_helpers() -> None:
    in_scope = applicable_rules(RULES, "woodland")
    assert {rule.jurisdiction_scope for rule in in_scope} == {
        "statewide",
        "woodland",
    }
    assert "davis-adu-handout-2026" not in {rule.rule_id for rule in in_scope}
    assert rules_reading(in_scope, "adu_project_form") == ["adu-conversion-exemptions"]
    assert rules_reading(in_scope, "not_a_field") == []


def test_only_material_facts_are_perturbed() -> None:
    """`project_type` and `jurisdiction` decide which project is screened, not
    what the rules say about one; moving them answers a different question."""
    payload = explore("woodland-new-detached-adu-local-layer")
    fields = [entry["field"] for entry in payload["facts"]]
    assert fields == [
        "primary_dwelling_status",
        "adu_project_form",
        "unpermitted_existing",
    ]
    assert "project_type" not in fields
    assert "jurisdiction" not in fields


@pytest.mark.parametrize("case", GOLDEN, ids=lambda case: str(case["case_id"]))
def test_every_golden_case_explores_without_ranking(case: dict[str, Any]) -> None:
    payload = explore(str(case["case_id"]))
    assert payload["what_if_boundary_statement"]
    for entry in payload["facts"]:
        # Values in the vocabulary's declared order, so nothing in the output
        # presents one branch as preferable to another.
        assert [item["value"] for item in entry["alternatives"]]
        assert sum(item["is_current_answer"] for item in entry["alternatives"]) <= 1
        for item in entry["alternatives"]:
            if item["decision_boundary"] == "needs_staff_review":
                assert item["unresolved_facts"]
                assert item["candidate_routes"] in ([], None)
            else:
                assert item["unresolved_facts"] == []
