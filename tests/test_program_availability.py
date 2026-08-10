import copy
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from permit_pathways.program_availability import (
    BOUNDARY,
    GENERIC_PROTOTYPE_AVAILABILITY_POLICY,
    GENERIC_PROTOTYPE_BOUNDARY,
    JURISDICTION,
    MAX_RECHECK_INTERVAL_DAYS,
    MAX_RECORD_BYTES,
    OFFICIAL_EXCERPT,
    OFFICIAL_PROGRAM_URL,
    PROGRAM_ID,
    SOURCE_ID,
    WOODLAND_AVAILABILITY_POLICY,
    WORKFLOW_ID,
    excerpt_fingerprint,
    load_program_availability,
)

ROOT = Path(__file__).parent.parent
RECORD = ROOT / "data" / "availability" / "woodland-preapproved-adu-program.json"
TODAY = date(2026, 8, 9)


def _payload() -> dict[str, Any]:
    return json.loads(RECORD.read_text(encoding="utf-8"))


def _write(tmp_path: Path, payload: Any) -> Path:
    path = tmp_path / "availability.json"
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_committed_woodland_record_loads_with_exact_bounded_evidence() -> None:
    record = load_program_availability(
        RECORD,
        today=TODAY,
        policy=WOODLAND_AVAILABILITY_POLICY,
    )

    assert record.program_id == PROGRAM_ID
    assert record.workflow_id == WORKFLOW_ID
    assert record.jurisdiction == JURISDICTION
    assert record.mode == "future_state_simulation"
    assert record.status == "plans_not_listed"
    assert record.monitoring_status == "manual_date_bound"
    assert record.boundary == BOUNDARY
    assert record.source.source_id == SOURCE_ID
    assert record.source.url == OFFICIAL_PROGRAM_URL
    assert record.source.label == "City of Woodland Preapproved ADU Plan Program"
    assert record.source.checked_on == "2026-08-09"
    assert record.source.recheck_due_on == "2026-09-08"
    assert record.source.excerpt == OFFICIAL_EXCERPT
    assert record.source.excerpt_sha256 == excerpt_fingerprint(record.source.excerpt)


def test_excerpt_fingerprint_normalizes_unicode_and_whitespace() -> None:
    expected = excerpt_fingerprint("Preapproved ADU List: Coming soon!")
    assert excerpt_fingerprint("  Preapproved  ADU List:\nComing soon!  ") == expected


@pytest.mark.parametrize(
    ("location", "field"),
    [
        ("top", "availability"),
        ("availability", "boundary"),
        ("source", "excerpt_sha256"),
    ],
)
def test_missing_fields_are_rejected(tmp_path: Path, location: str, field: str) -> None:
    payload = _payload()
    target = (
        payload
        if location == "top"
        else payload["availability"]
        if location == "availability"
        else payload["availability"]["source"]
    )
    del target[field]
    with pytest.raises(ValueError, match="missing fields"):
        load_program_availability(_write(tmp_path, payload), today=TODAY)


@pytest.mark.parametrize("location", ["top", "availability", "source"])
def test_unknown_fields_are_rejected(tmp_path: Path, location: str) -> None:
    payload = _payload()
    target = (
        payload
        if location == "top"
        else payload["availability"]
        if location == "availability"
        else payload["availability"]["source"]
    )
    target["unexpected"] = True
    with pytest.raises(ValueError, match="unknown fields"):
        load_program_availability(_write(tmp_path, payload), today=TODAY)


@pytest.mark.parametrize("schema_version", [True, 2, "1"])
def test_schema_version_is_exact(tmp_path: Path, schema_version: Any) -> None:
    payload = _payload()
    payload["schema_version"] = schema_version
    with pytest.raises(ValueError, match="schema_version"):
        load_program_availability(_write(tmp_path, payload), today=TODAY)


def test_malformed_and_non_object_payloads_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="could not be loaded"):
        load_program_availability(_write(tmp_path, "{"), today=TODAY)
    with pytest.raises(ValueError, match="expected an object"):
        load_program_availability(_write(tmp_path, []), today=TODAY)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("checked_on", "2026/08/09", "expected YYYY-MM-DD"),
        ("checked_on", "2026-02-30", "invalid ISO date"),
        ("recheck_due_on", "2026-09-31", "invalid ISO date"),
        ("recheck_due_on", "2026-08-09", "must be after checked_on"),
        ("recheck_due_on", "2026-08-08", "must be after checked_on"),
    ],
)
def test_bad_or_misordered_dates_are_rejected(
    tmp_path: Path, field: str, value: str, message: str
) -> None:
    payload = _payload()
    payload["availability"]["source"][field] = value
    with pytest.raises(ValueError, match=message):
        load_program_availability(_write(tmp_path, payload), today=TODAY)


def test_future_checked_on_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="future dates are not allowed"):
        load_program_availability(RECORD, today=date(2026, 8, 8))


@pytest.mark.parametrize(
    "url",
    [
        "http://www.cityofwoodland.gov/1616/Preapproved-ADU-Plan-Program",
        "https://user@www.cityofwoodland.gov/1616/Preapproved-ADU-Plan-Program",
    ],
)
def test_source_url_requires_safe_https(tmp_path: Path, url: str) -> None:
    payload = _payload()
    payload["availability"]["source"]["url"] = url
    with pytest.raises(ValueError, match="expected HTTPS URL"):
        load_program_availability(_write(tmp_path, payload), today=TODAY)


def test_source_url_must_be_the_official_program_page(tmp_path: Path) -> None:
    payload = _payload()
    payload["availability"]["source"]["url"] = (
        "https://www.cityofwoodland.gov/another-page"
    )
    with pytest.raises(ValueError, match="official Woodland program URL"):
        load_program_availability(_write(tmp_path, payload), today=TODAY)


def test_excerpt_fingerprint_format_and_content_drift_are_rejected(
    tmp_path: Path,
) -> None:
    malformed = _payload()
    malformed["availability"]["source"]["excerpt_sha256"] = "not-a-digest"
    with pytest.raises(ValueError, match="invalid SHA-256 fingerprint"):
        load_program_availability(_write(tmp_path, malformed), today=TODAY)

    mismatched = _payload()
    mismatched["availability"]["source"]["excerpt_sha256"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="does not match the normalized excerpt"):
        load_program_availability(_write(tmp_path, mismatched), today=TODAY)

    drifted = _payload()
    drifted["availability"]["source"]["excerpt"] = (
        "Preapproved ADU List: One plan listed."
    )
    with pytest.raises(ValueError, match="plans_not_listed observation"):
        load_program_availability(_write(tmp_path, drifted), today=TODAY)

    # Updating both the prose and its hash must not let a contradictory
    # observation pass under the fixed plans_not_listed status.
    self_consistent_drift = _payload()
    changed_excerpt = "Preapproved ADU List: One plan listed."
    self_consistent_drift["availability"]["source"]["excerpt"] = changed_excerpt
    self_consistent_drift["availability"]["source"]["excerpt_sha256"] = (
        excerpt_fingerprint(changed_excerpt)
    )
    with pytest.raises(ValueError, match="plans_not_listed observation"):
        load_program_availability(_write(tmp_path, self_consistent_drift), today=TODAY)


def test_recheck_window_is_short_and_bounded(tmp_path: Path) -> None:
    payload = _payload()
    payload["availability"]["source"]["recheck_due_on"] = "2026-09-10"
    with pytest.raises(
        ValueError,
        match=rf"within {MAX_RECHECK_INTERVAL_DAYS} days",
    ):
        load_program_availability(_write(tmp_path, payload), today=TODAY)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mode", "current_program"),
        ("status", "plans_available"),
        ("monitoring_status", "automated"),
    ],
)
def test_unsupported_mode_status_and_monitoring_are_rejected(
    tmp_path: Path, field: str, value: str
) -> None:
    payload = _payload()
    payload["availability"][field] = value
    with pytest.raises(ValueError, match="unsupported value"):
        load_program_availability(_write(tmp_path, payload), today=TODAY)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("program_id", "different-program"),
        ("workflow_id", "different-workflow"),
        ("jurisdiction", "davis"),
    ],
)
def test_record_is_bound_to_the_expected_program_workflow_and_jurisdiction(
    tmp_path: Path, field: str, value: str
) -> None:
    payload = _payload()
    payload["availability"][field] = value
    with pytest.raises(ValueError, match="expected"):
        load_program_availability(_write(tmp_path, payload), today=TODAY)


def test_invalid_stable_identifiers_are_rejected(tmp_path: Path) -> None:
    payload = _payload()
    payload["availability"]["source"]["source_id"] = "Bad Source ID"
    with pytest.raises(ValueError, match="expected a stable ID"):
        load_program_availability(_write(tmp_path, payload), today=TODAY)


def test_boundary_and_label_cannot_be_weakened_or_blank(tmp_path: Path) -> None:
    weakened = _payload()
    weakened["availability"]["boundary"] = "Plans may be available."
    with pytest.raises(ValueError, match="must preserve"):
        load_program_availability(_write(tmp_path, weakened), today=TODAY)

    blank_label = copy.deepcopy(_payload())
    blank_label["availability"]["source"]["label"] = " "
    with pytest.raises(ValueError, match="expected non-blank text"):
        load_program_availability(_write(tmp_path, blank_label), today=TODAY)


def test_generic_prototype_policy_accepts_a_distinct_bound_record(
    tmp_path: Path,
) -> None:
    payload = _payload()
    availability = payload["availability"]
    availability.update(
        {
            "program_id": "second-prototype-program",
            "workflow_id": "second-prototype-workflow",
            "jurisdiction": "davis",
            "boundary": GENERIC_PROTOTYPE_BOUNDARY,
        }
    )
    source = availability["source"]
    source.update(
        {
            "source_id": "davis-prototype-program-page",
            "url": "https://www.cityofdavis.org/prototype-program",
            "label": "City of Davis prototype program page",
            "excerpt": "No plans are listed on this prototype page.",
        }
    )
    source["excerpt_sha256"] = excerpt_fingerprint(source["excerpt"])

    record = load_program_availability(
        _write(tmp_path, payload),
        today=TODAY,
        policy=GENERIC_PROTOTYPE_AVAILABILITY_POLICY,
    )

    assert record.program_id == "second-prototype-program"
    assert record.workflow_id == "second-prototype-workflow"
    assert record.jurisdiction == "davis"
    assert record.source.source_id == "davis-prototype-program-page"


def test_generic_policy_still_requires_the_fixed_non_applicability_boundary(
    tmp_path: Path,
) -> None:
    payload = _payload()
    payload["availability"]["boundary"] = "A plan is probably available."
    with pytest.raises(ValueError, match="must preserve"):
        load_program_availability(
            _write(tmp_path, payload),
            today=TODAY,
            policy=GENERIC_PROTOTYPE_AVAILABILITY_POLICY,
        )


def test_unknown_availability_policy_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported value"):
        load_program_availability(
            _write(tmp_path, _payload()),
            today=TODAY,
            policy="unknown-policy",
        )


@pytest.mark.parametrize(
    "raw",
    [
        '{"schema_version":1,"schema_version":1,"availability":{}}',
        '{"schema_version":NaN,"availability":{}}',
        '{"schema_version":Infinity,"availability":{}}',
    ],
)
def test_ambiguous_and_nonfinite_json_are_rejected(
    tmp_path: Path,
    raw: str,
) -> None:
    with pytest.raises(ValueError, match="could not be loaded"):
        load_program_availability(_write(tmp_path, raw), today=TODAY)


def test_oversized_availability_record_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "availability.json"
    path.write_bytes(b" " * (MAX_RECORD_BYTES + 1))
    with pytest.raises(ValueError, match="could not be loaded"):
        load_program_availability(path, today=TODAY)
