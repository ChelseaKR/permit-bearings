import copy
import json
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest

from permit_pathways.explanations import citation_fingerprint
from permit_pathways.harness.runner import DEFAULT_MAX_AGE_DAYS
from permit_pathways.rule_verification import (
    VERIFICATION_LEVELS,
    effective_status,
    level_coverage,
    load_rule_verifications,
)
from permit_pathways.screening import load_rules, screen

ROOT = Path(__file__).parent.parent
RULES_PATH = ROOT / "data" / "rules"
LEDGER_PATH = ROOT / "data" / "validation" / "rule-verification.json"
TODAY = date(2026, 8, 4)


@pytest.fixture()
def rules():
    return load_rules(RULES_PATH, today=TODAY)


@pytest.fixture()
def ledger(rules):
    return load_rule_verifications(LEDGER_PATH, rules, today=TODAY)


def _payload():
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def _write(tmp_path, payload):
    path = tmp_path / "rule-verification.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _entry(payload, rule_id):
    return next(e for e in payload["entries"] if e["rule_id"] == rule_id)


def _reviewed_entry(rule, level, *, reviewed_on="2026-08-01"):
    return {
        "rule_id": rule.rule_id,
        "level": level,
        "reviewer": "Named reviewer",
        "method": "Compared line by line against the cited source",
        "reviewed_on": reviewed_on,
        "reviewed_citation_fingerprint": citation_fingerprint(rule),
    }


# ---------------------------------------------------------------------------
# Loading the committed pilot ledger


def test_every_rule_has_exactly_one_ledger_entry(rules, ledger):
    assert set(ledger) == {rule.rule_id for rule in rules}


def test_committed_pilot_ledger_claims_no_review_yet(ledger):
    # Honest current state: no rule has actually been human- or
    # jurisdiction-reviewed under this schema yet. Claiming otherwise here
    # would fabricate evidence no one has produced.
    assert {entry.level for entry in ledger.values()} == {"machine_linked"}
    for entry in ledger.values():
        assert entry.reviewer is None
        assert entry.method is None
        assert entry.reviewed_on is None
        assert entry.reviewed_citation_fingerprint is None


def test_loading_the_ledger_cannot_change_deterministic_matches(rules, ledger):
    intake = {
        "project_type": "adu",
        "primary_dwelling_status": "existing_single_family",
        "adu_project_form": "new_detached",
        "unpermitted_existing": "no",
        "jurisdiction": "davis",
    }
    before = [result.rule.rule_id for result in screen(intake, rules)]
    load_rule_verifications(LEDGER_PATH, rules, today=TODAY)
    after = [result.rule.rule_id for result in screen(intake, rules)]
    assert after == before


# ---------------------------------------------------------------------------
# Schema validation


def test_unknown_and_missing_fields_are_rejected(tmp_path, rules):
    extra_field = _payload()
    _entry(extra_field, "adu-ministerial-review")["unexpected"] = "value"
    with pytest.raises(ValueError, match="unknown fields"):
        load_rule_verifications(_write(tmp_path, extra_field), rules, today=TODAY)

    missing_field = _payload()
    del _entry(missing_field, "adu-ministerial-review")["method"]
    with pytest.raises(ValueError, match="missing fields"):
        load_rule_verifications(_write(tmp_path, missing_field), rules, today=TODAY)


def test_unknown_level_is_rejected(tmp_path, rules):
    payload = _payload()
    _entry(payload, "adu-ministerial-review")["level"] = "invented_status"
    with pytest.raises(ValueError, match="level: unknown value"):
        load_rule_verifications(_write(tmp_path, payload), rules, today=TODAY)


def test_orphaned_and_duplicate_rule_ids_are_rejected(tmp_path, rules):
    orphan = _payload()
    orphan["entries"][0]["rule_id"] = "not-a-real-rule"
    with pytest.raises(ValueError, match="references unknown rule ID"):
        load_rule_verifications(_write(tmp_path, orphan), rules, today=TODAY)

    duplicate = _payload()
    duplicate["entries"].append(copy.deepcopy(duplicate["entries"][0]))
    with pytest.raises(ValueError, match="duplicate rule-verification entry"):
        load_rule_verifications(_write(tmp_path, duplicate), rules, today=TODAY)


def test_non_strict_duplicate_entries_leave_the_rule_id_unlisted(tmp_path, rules):
    duplicate = _payload()
    duplicated_id = duplicate["entries"][0]["rule_id"]
    duplicate["entries"].append(copy.deepcopy(duplicate["entries"][0]))
    path = _write(tmp_path, duplicate)

    display = load_rule_verifications(path, rules, strict=False, today=TODAY)
    assert duplicated_id not in display
    assert len(display) == len(rules) - 1


def test_blank_rule_id_is_rejected(tmp_path, rules):
    payload = _payload()
    payload["entries"][0]["rule_id"] = "   "
    with pytest.raises(ValueError, match="expected non-blank text"):
        load_rule_verifications(_write(tmp_path, payload), rules, today=TODAY)


def test_non_dict_entry_is_rejected(tmp_path, rules):
    payload = _payload()
    payload["entries"][0] = "not an object"
    path = _write(tmp_path, payload)
    with pytest.raises(ValueError, match="expected an object"):
        load_rule_verifications(path, rules, today=TODAY)
    assert (
        len(load_rule_verifications(path, rules, strict=False, today=TODAY))
        == len(rules) - 1
    )


def test_duplicate_rule_ids_in_the_canonical_rule_set_are_rejected(rules):
    duplicated = [*rules, rules[0]]
    with pytest.raises(ValueError, match="duplicate rule IDs"):
        load_rule_verifications(LEDGER_PATH, duplicated, today=TODAY)


def test_non_strict_schema_mismatch_and_non_list_entries_degrade_to_empty(
    tmp_path, rules
):
    wrong_version = _payload()
    wrong_version["schema_version"] = 2
    assert (
        load_rule_verifications(
            _write(tmp_path, wrong_version), rules, strict=False, today=TODAY
        )
        == {}
    )

    not_a_list = _payload()
    not_a_list["entries"] = {}
    assert (
        load_rule_verifications(
            _write(tmp_path, not_a_list), rules, strict=False, today=TODAY
        )
        == {}
    )


def test_missing_rule_coverage_is_rejected(tmp_path, rules):
    incomplete = _payload()
    incomplete["entries"].pop()
    with pytest.raises(ValueError, match="missing rule IDs"):
        load_rule_verifications(_write(tmp_path, incomplete), rules, today=TODAY)


def test_wrong_schema_version_and_malformed_payloads_are_rejected(tmp_path, rules):
    wrong_version = _payload()
    wrong_version["schema_version"] = 2
    with pytest.raises(ValueError, match="schema_version"):
        load_rule_verifications(_write(tmp_path, wrong_version), rules, today=TODAY)

    not_a_list = _payload()
    not_a_list["entries"] = {}
    with pytest.raises(ValueError, match="entries: expected a list"):
        load_rule_verifications(_write(tmp_path, not_a_list), rules, today=TODAY)

    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not valid JSON", encoding="utf-8")
    with pytest.raises(ValueError, match="could not be loaded"):
        load_rule_verifications(malformed, rules, today=TODAY)


# ---------------------------------------------------------------------------
# Status transitions: promoting machine_linked -> human_reviewed / jurisdiction_approved


def test_machine_linked_cannot_carry_reviewer_metadata(tmp_path, rules):
    payload = _payload()
    entry = _entry(payload, "adu-ministerial-review")
    entry["reviewer"] = "Named reviewer"
    with pytest.raises(ValueError, match="cannot claim reviewer metadata"):
        load_rule_verifications(_write(tmp_path, payload), rules, today=TODAY)


@pytest.mark.parametrize("level", ["human_reviewed", "jurisdiction_approved"])
def test_promotion_requires_reviewer_method_date_and_fingerprint(
    tmp_path, rules, level
):
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    payload = _payload()
    incomplete = {
        "rule_id": rule.rule_id,
        "level": level,
        "reviewer": None,
        "method": None,
        "reviewed_on": None,
        "reviewed_citation_fingerprint": None,
    }
    payload["entries"] = [
        incomplete if e["rule_id"] == rule.rule_id else e for e in payload["entries"]
    ]
    with pytest.raises(
        ValueError,
        match="requires reviewer, method, reviewed_on, and "
        "reviewed_citation_fingerprint",
    ):
        load_rule_verifications(_write(tmp_path, payload), rules, today=TODAY)


@pytest.mark.parametrize("level", ["human_reviewed", "jurisdiction_approved"])
def test_a_correctly_bound_promotion_loads_successfully(tmp_path, rules, level):
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    payload = _payload()
    payload["entries"] = [
        _reviewed_entry(rule, level) if e["rule_id"] == rule.rule_id else e
        for e in payload["entries"]
    ]
    ledger = load_rule_verifications(_write(tmp_path, payload), rules, today=TODAY)
    assert ledger[rule.rule_id].level == level
    assert ledger[rule.rule_id].reviewer == "Named reviewer"
    status = effective_status(rule, ledger, today=TODAY)
    assert status.level == level
    assert status.stale is False


def test_reviewed_citation_fingerprint_must_match_the_current_rule(tmp_path, rules):
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    payload = _payload()
    wrong_fingerprint = _reviewed_entry(rule, "human_reviewed")
    wrong_fingerprint["reviewed_citation_fingerprint"] = "sha256:" + "0" * 64
    payload["entries"] = [
        wrong_fingerprint if e["rule_id"] == rule.rule_id else e
        for e in payload["entries"]
    ]
    with pytest.raises(ValueError, match="does not match the rule's current citation"):
        load_rule_verifications(_write(tmp_path, payload), rules, today=TODAY)


def test_citation_drift_after_review_is_rejected_at_load_time(tmp_path, rules):
    # A review binds to the exact citation it checked. If the rule's cited
    # excerpt changes later without a fresh review, strict loading must
    # catch it rather than silently keep the stronger claim alive.
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    payload = _payload()
    payload["entries"] = [
        _reviewed_entry(rule, "human_reviewed") if e["rule_id"] == rule.rule_id else e
        for e in payload["entries"]
    ]
    path = _write(tmp_path, payload)

    changed_rules = [
        replace(
            r,
            citation=replace(
                r.citation, excerpt=(r.citation.excerpt or "") + " changed"
            ),
        )
        if r.rule_id == rule.rule_id
        else r
        for r in rules
    ]
    with pytest.raises(ValueError, match="does not match the rule's current citation"):
        load_rule_verifications(path, changed_rules, today=TODAY)


def test_reviewed_on_cannot_predate_the_rules_source_date(tmp_path, rules):
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    payload = _payload()
    entry = _reviewed_entry(rule, "human_reviewed", reviewed_on="2020-01-01")
    payload["entries"] = [
        entry if e["rule_id"] == rule.rule_id else e for e in payload["entries"]
    ]
    with pytest.raises(ValueError, match="predates the rule's source date"):
        load_rule_verifications(_write(tmp_path, payload), rules, today=TODAY)


def test_reviewed_on_must_match_the_iso_date_format(tmp_path, rules):
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    payload = _payload()
    entry = _reviewed_entry(rule, "human_reviewed", reviewed_on="08/01/2026")
    payload["entries"] = [
        entry if e["rule_id"] == rule.rule_id else e for e in payload["entries"]
    ]
    with pytest.raises(ValueError, match="expected YYYY-MM-DD"):
        load_rule_verifications(_write(tmp_path, payload), rules, today=TODAY)


def test_reviewed_on_rejects_a_calendar_date_that_does_not_exist(tmp_path, rules):
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    payload = _payload()
    entry = _reviewed_entry(rule, "human_reviewed", reviewed_on="2026-02-30")
    payload["entries"] = [
        entry if e["rule_id"] == rule.rule_id else e for e in payload["entries"]
    ]
    with pytest.raises(ValueError, match="invalid ISO date"):
        load_rule_verifications(_write(tmp_path, payload), rules, today=TODAY)


def test_reviewed_on_cannot_be_in_the_future(tmp_path, rules):
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    payload = _payload()
    entry = _reviewed_entry(rule, "human_reviewed", reviewed_on="2026-12-31")
    payload["entries"] = [
        entry if e["rule_id"] == rule.rule_id else e for e in payload["entries"]
    ]
    with pytest.raises(ValueError, match="future dates are not allowed"):
        load_rule_verifications(_write(tmp_path, payload), rules, today=TODAY)


def test_reviewed_citation_fingerprint_must_be_valid_sha256(tmp_path, rules):
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    payload = _payload()
    entry = _reviewed_entry(rule, "human_reviewed")
    entry["reviewed_citation_fingerprint"] = "not-a-fingerprint"
    payload["entries"] = [
        entry if e["rule_id"] == rule.rule_id else e for e in payload["entries"]
    ]
    with pytest.raises(ValueError, match="invalid SHA-256"):
        load_rule_verifications(_write(tmp_path, payload), rules, today=TODAY)


def test_a_rule_without_a_dated_citation_cannot_be_promoted(tmp_path, rules):
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    unverified_rules = [
        replace(r, citation=replace(r.citation, verified_on=None))
        if r.rule_id == rule.rule_id
        else r
        for r in rules
    ]
    payload = _payload()
    entry = _reviewed_entry(rule, "human_reviewed")
    payload["entries"] = [
        entry if e["rule_id"] == rule.rule_id else e for e in payload["entries"]
    ]
    with pytest.raises(ValueError, match="requires the rule to carry a dated"):
        load_rule_verifications(
            _write(tmp_path, payload), unverified_rules, today=TODAY
        )


# ---------------------------------------------------------------------------
# Tolerant display load (strict=False)


def test_tolerant_display_load_drops_invalid_entries_individually(tmp_path, rules):
    payload = _payload()
    invalid_id = payload["entries"][0]["rule_id"]
    payload["entries"][0]["level"] = "invented_status"
    path = _write(tmp_path, payload)

    with pytest.raises(ValueError):
        load_rule_verifications(path, rules, today=TODAY)

    display = load_rule_verifications(path, rules, strict=False, today=TODAY)
    assert invalid_id not in display
    assert len(display) == len(rules) - 1


def test_tolerant_display_load_degrades_missing_or_malformed_data_to_empty(
    tmp_path, rules
):
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not valid JSON", encoding="utf-8")
    assert load_rule_verifications(malformed, rules, strict=False, today=TODAY) == {}
    assert (
        load_rule_verifications(
            tmp_path / "missing.json", rules, strict=False, today=TODAY
        )
        == {}
    )


# ---------------------------------------------------------------------------
# effective_status: default floor and time-based staleness


def test_a_rule_absent_from_the_ledger_defaults_to_machine_linked(rules):
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    status = effective_status(rule, {}, today=TODAY)
    assert status.level == "machine_linked"
    assert status.recorded_level == "machine_linked"
    assert status.stale is False
    assert status.reason is None


def test_machine_linked_ledger_entry_never_goes_stale(rules, ledger):
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    far_future = date(2030, 1, 1)
    status = effective_status(rule, ledger, today=far_future)
    assert status.level == "machine_linked"
    assert status.stale is False


@pytest.mark.parametrize("level", ["human_reviewed", "jurisdiction_approved"])
def test_a_fresh_review_holds_its_level_within_the_window(tmp_path, rules, level):
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    payload = _payload()
    payload["entries"] = [
        _reviewed_entry(rule, level, reviewed_on="2026-08-01")
        if e["rule_id"] == rule.rule_id
        else e
        for e in payload["entries"]
    ]
    ledger = load_rule_verifications(_write(tmp_path, payload), rules, today=TODAY)

    still_fresh = date(2026, 8, 1) + timedelta(days=DEFAULT_MAX_AGE_DAYS)
    status = effective_status(rule, ledger, today=still_fresh)
    assert status.level == level
    assert status.recorded_level == level
    assert status.stale is False
    assert status.reason is None


@pytest.mark.parametrize("level", ["human_reviewed", "jurisdiction_approved"])
def test_a_review_fails_closed_to_machine_linked_once_its_window_elapses(
    tmp_path, rules, level
):
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    payload = _payload()
    payload["entries"] = [
        _reviewed_entry(rule, level, reviewed_on="2026-08-01")
        if e["rule_id"] == rule.rule_id
        else e
        for e in payload["entries"]
    ]
    ledger = load_rule_verifications(_write(tmp_path, payload), rules, today=TODAY)

    just_past_window = date(2026, 8, 1) + timedelta(days=DEFAULT_MAX_AGE_DAYS + 1)
    status = effective_status(rule, ledger, today=just_past_window)
    assert status.level == "machine_linked"
    assert status.recorded_level == level
    assert status.stale is True
    assert "review window elapsed" in status.reason


def test_effective_status_rejects_a_future_reviewed_on(rules):
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    from permit_pathways.rule_verification import RuleVerification

    entry = RuleVerification(
        rule_id=rule.rule_id,
        level="human_reviewed",
        reviewer="Named reviewer",
        method="Compared line by line",
        reviewed_on="2026-08-10",
        reviewed_citation_fingerprint=citation_fingerprint(rule),
    )
    with pytest.raises(ValueError, match="reviewed_on is in the future"):
        effective_status(rule, {rule.rule_id: entry}, today=TODAY)


def test_effective_status_rejects_negative_max_age(rules):
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    with pytest.raises(ValueError, match="max_age_days must be non-negative"):
        effective_status(rule, {}, today=TODAY, max_age_days=-1)


def test_default_max_age_matches_the_harness_review_window():
    # Reuse one shared review-window constant rather than duplicating it, so
    # the source-currency harness and the verification-level ledger cannot
    # silently drift apart.
    assert DEFAULT_MAX_AGE_DAYS == 180


def test_all_verification_levels_are_exercised_by_the_pilot_module():
    assert VERIFICATION_LEVELS == (
        "machine_linked",
        "human_reviewed",
        "jurisdiction_approved",
    )


# ---------------------------------------------------------------------------
# Level-coverage summary (read-only visibility, not a claim)


def test_level_coverage_reports_the_committed_ledger_as_entirely_machine_linked(
    rules, ledger
):
    cov = level_coverage(rules, ledger, today=TODAY)
    assert cov.total == len(rules)
    assert cov.machine_linked == len(rules)
    assert cov.human_reviewed == 0
    assert cov.jurisdiction_approved == 0
    assert cov.reverted_stale == 0
    summary = cov.summary()
    assert f"{len(rules)} rules; effective verification level:" in summary
    assert "reverted" not in summary


@pytest.mark.parametrize("level", ["human_reviewed", "jurisdiction_approved"])
def test_level_coverage_counts_a_fresh_review_under_its_promoted_level(
    tmp_path, rules, level
):
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    payload = _payload()
    payload["entries"] = [
        _reviewed_entry(rule, level, reviewed_on="2026-08-01")
        if e["rule_id"] == rule.rule_id
        else e
        for e in payload["entries"]
    ]
    ledger = load_rule_verifications(_write(tmp_path, payload), rules, today=TODAY)

    still_fresh = date(2026, 8, 1) + timedelta(days=DEFAULT_MAX_AGE_DAYS)
    cov = level_coverage(rules, ledger, today=still_fresh)
    assert cov.total == len(rules)
    assert getattr(cov, level) == 1
    assert cov.machine_linked == len(rules) - 1
    assert cov.reverted_stale == 0


@pytest.mark.parametrize("level", ["human_reviewed", "jurisdiction_approved"])
def test_level_coverage_tallies_an_elapsed_review_as_reverted_stale(
    tmp_path, rules, level
):
    rule = next(r for r in rules if r.rule_id == "adu-ministerial-review")
    payload = _payload()
    payload["entries"] = [
        _reviewed_entry(rule, level, reviewed_on="2026-08-01")
        if e["rule_id"] == rule.rule_id
        else e
        for e in payload["entries"]
    ]
    ledger = load_rule_verifications(_write(tmp_path, payload), rules, today=TODAY)

    just_past_window = date(2026, 8, 1) + timedelta(days=DEFAULT_MAX_AGE_DAYS + 1)
    cov = level_coverage(rules, ledger, today=just_past_window)
    # The elapsed claim reverts closed to machine_linked, exactly as
    # effective_status reports it — the reversion is tallied separately
    # rather than silently counted as if the rule were never reviewed.
    assert cov.machine_linked == len(rules)
    assert getattr(cov, level) == 0
    assert cov.reverted_stale == 1
    assert "1 reverted to machine_linked: review window elapsed" in cov.summary()
