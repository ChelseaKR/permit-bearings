import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from permit_pathways.explanations import citation_fingerprint, rule_fingerprint
from permit_pathways.reviewer_roster import (
    COI_ATTESTATION_MAX_AGE_DAYS,
    load_reviewer_roster,
    maybe_load_reviewer_roster,
)
from permit_pathways.rule_verification import load_rule_verifications
from permit_pathways.screening import load_rules

ROOT = Path(__file__).parent.parent
RULES_PATH = ROOT / "data" / "rules"
ROSTER_PATH = ROOT / "reviewer-roster.json"
LEDGER_PATH = ROOT / "data" / "validation" / "rule-verification.json"
TODAY = date(2026, 8, 21)


@pytest.fixture()
def rules():
    return load_rules(RULES_PATH, today=TODAY)


def _roster(members):
    return {
        "schema_version": 1,
        "roles": [
            {"role_id": "rule-content-reviewer", "level": "human_reviewed"},
            {"role_id": "jurisdiction-approver", "level": "jurisdiction_approved"},
        ],
        "members": members,
    }


def _write_roster(tmp_path, payload):
    path = tmp_path / "reviewer-roster.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _member(
    member_id="reviewer-1",
    name="Named reviewer",
    role_id="rule-content-reviewer",
    attested_on="2026-08-01",
):
    return {
        "member_id": member_id,
        "reviewer_name": name,
        "role_id": role_id,
        "coi_attested_on": attested_on,
    }


def _promoted_payload(rule, level="human_reviewed"):
    payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    for entry in payload["entries"]:
        if entry["rule_id"] == rule.rule_id:
            entry.update(
                {
                    "level": level,
                    "reviewer": "Named reviewer",
                    "method": "Compared line by line against the cited source",
                    "reviewed_on": "2026-08-02",
                    "reviewed_citation_fingerprint": citation_fingerprint(rule),
                    "reviewed_rule_fingerprint": rule_fingerprint(rule),
                }
            )
    return payload


def _write_ledger(tmp_path, payload):
    path = tmp_path / "rule-verification.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# The committed template


def test_committed_template_declares_roles_and_zero_members():
    roster = load_reviewer_roster(ROSTER_PATH, today=TODAY)
    assert {role.level for role in roster.roles} == {
        "human_reviewed",
        "jurisdiction_approved",
    }
    assert roster.members == ()
    # Aggregate-only public surface: no names exist to leak, and the summary
    # format must stay count-only even when they do.
    assert roster.public_summary() == "2 roster role(s); 0 attested reviewer(s) active"


def test_missing_roster_file_returns_none_from_optional_helper(tmp_path):
    assert maybe_load_reviewer_roster(tmp_path / "absent.json", today=TODAY) is None


# ---------------------------------------------------------------------------
# Roster schema validation


def test_role_schema_errors_are_rejected(tmp_path):
    wrong_level = _roster([])
    wrong_level["roles"][0]["level"] = "machine_linked"
    with pytest.raises(ValueError, match="unsupported value"):
        load_reviewer_roster(_write_roster(tmp_path, wrong_level), today=TODAY)

    duplicate = _roster([])
    duplicate["roles"].append(dict(duplicate["roles"][0]))
    with pytest.raises(ValueError, match="duplicate role ID"):
        load_reviewer_roster(_write_roster(tmp_path, duplicate), today=TODAY)

    uncovered = _roster([])
    uncovered["roles"] = [uncovered["roles"][0]]
    with pytest.raises(ValueError, match="no role supports required level"):
        load_reviewer_roster(_write_roster(tmp_path, uncovered), today=TODAY)

    extra_field = _roster([])
    extra_field["roles"][0]["note"] = "unexpected"
    with pytest.raises(ValueError, match="unknown fields"):
        load_reviewer_roster(_write_roster(tmp_path, extra_field), today=TODAY)


def test_member_schema_errors_are_rejected(tmp_path):
    cases = [
        (
            [_member(member_id="a"), _member(member_id="a")],
            "duplicate member ID",
        ),
        ([_member(role_id="undeclared-role")], "references undeclared role"),
        ([_member(attested_on="2026-12-31")], "future dates are not allowed"),
        (
            [
                _member(
                    attested_on=(TODAY - timedelta(days=366)).isoformat(),
                )
            ],
            "must be renewed",
        ),
        ([_member(attested_on="08/01/2026")], "expected YYYY-MM-DD"),
        ([_member(name="   ")], "expected non-blank text"),
    ]
    for members, match in cases:
        with pytest.raises(ValueError, match=match):
            load_reviewer_roster(_write_roster(tmp_path, _roster(members)), today=TODAY)


def test_attestation_at_exact_max_age_is_still_valid(tmp_path):
    edge = (TODAY - timedelta(days=COI_ATTESTATION_MAX_AGE_DAYS)).isoformat()
    roster = load_reviewer_roster(
        _write_roster(tmp_path, _roster([_member(attested_on=edge)])),
        today=TODAY,
    )
    assert roster.allows("Named reviewer", "human_reviewed", today=TODAY)


# ---------------------------------------------------------------------------
# Membership semantics


def test_allows_requires_exact_name_matching_role_and_current_attestation(tmp_path):
    roster = load_reviewer_roster(
        _write_roster(tmp_path, _roster([_member()])), today=TODAY
    )
    assert roster.allows("Named reviewer", "human_reviewed", today=TODAY)
    assert not roster.allows("named reviewer", "human_reviewed", today=TODAY)
    assert not roster.allows("Someone else", "human_reviewed", today=TODAY)
    # The content-reviewer role does not support jurisdiction approval.
    assert not roster.allows("Named reviewer", "jurisdiction_approved", today=TODAY)
    assert not roster.allows(None, "human_reviewed", today=TODAY)


# ---------------------------------------------------------------------------
# Promotion gating in strict ledger loading


def test_promotion_without_attested_reviewer_is_rejected(tmp_path, rules):
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    roster = load_reviewer_roster(_write_roster(tmp_path, _roster([])), today=TODAY)
    with pytest.raises(ValueError, match="not a currently attested member"):
        load_rule_verifications(
            _write_ledger(tmp_path, _promoted_payload(rule)),
            rules,
            today=TODAY,
            roster=roster,
        )


def test_promotion_by_wrong_level_role_is_rejected(tmp_path, rules):
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    approver_only = _roster([_member(role_id="jurisdiction-approver")])
    roster = load_reviewer_roster(_write_roster(tmp_path, approver_only), today=TODAY)
    with pytest.raises(ValueError, match="not a currently attested member"):
        load_rule_verifications(
            _write_ledger(tmp_path, _promoted_payload(rule)),
            rules,
            today=TODAY,
            roster=roster,
        )


def test_promotion_by_attested_member_loads(tmp_path, rules):
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    roster = load_reviewer_roster(
        _write_roster(tmp_path, _roster([_member()])), today=TODAY
    )
    ledger = load_rule_verifications(
        _write_ledger(tmp_path, _promoted_payload(rule)),
        rules,
        today=TODAY,
        roster=roster,
    )
    assert ledger[rule.rule_id].level == "human_reviewed"


def test_non_strict_loading_drops_unattested_promotions(tmp_path, rules):
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    roster = load_reviewer_roster(_write_roster(tmp_path, _roster([])), today=TODAY)
    display = load_rule_verifications(
        _write_ledger(tmp_path, _promoted_payload(rule)),
        rules,
        strict=False,
        today=TODAY,
        roster=roster,
    )
    assert rule.rule_id not in display


def test_callers_without_a_roster_keep_the_historical_behavior(tmp_path, rules):
    # Synthetic promotions in developer tests intentionally have no roster;
    # gating activates only where a caller supplies one (canonical builds).
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    ledger = load_rule_verifications(
        _write_ledger(tmp_path, _promoted_payload(rule)), rules, today=TODAY
    )
    assert ledger[rule.rule_id].level == "human_reviewed"


def test_committed_machine_linked_ledger_passes_the_real_roster_gate(rules):
    roster = load_reviewer_roster(ROSTER_PATH, today=TODAY)
    ledger = load_rule_verifications(LEDGER_PATH, rules, today=TODAY, roster=roster)
    assert {entry.level for entry in ledger.values()} == {"machine_linked"}
