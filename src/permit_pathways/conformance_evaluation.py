"""Held-out evaluation scaffolding for the presence-based conformance scanner.

The committed manifest is deliberately ``not_run``.  This module validates
that planning record and provides deterministic building blocks for a later,
independently frozen passage/check evaluation.  It does not supply passages,
reviewer judgments, or an accuracy claim.

Labels describe review-queue behavior only:

* ``should_flag`` means one exact passage/check pair should enter review;
* ``should_stay_quiet`` means that pair should not enter review; and
* ``reference_abstain`` means reviewers could not establish a defensible
  expected queue behavior.  It is counted separately and never enters the
  binary matrix.

The current scanner itself is binary.  Scanner errors fail a run; they are not
converted into machine abstentions.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .conformance import load_checks, scan

SCHEMA_VERSION = 1
REFERENCE_LABELS = (
    "should_flag",
    "should_stay_quiet",
    "reference_abstain",
)
RAW_COUNT_FIELDS = (
    "expected_flag_observed_flag",
    "expected_flag_observed_quiet",
    "expected_quiet_observed_flag",
    "expected_quiet_observed_quiet",
    "reference_abstain",
    "machine_abstain",
)
PARTITIONS = (
    "official_targeted",
    "synthetic_targeted",
    "official_incidental",
    "synthetic_incidental",
    "overall",
)

NEAR_DUPLICATE_DISPOSITION = (
    "Materially overlapping passages are excluded before freeze."
)
# This pins the complete policy text, so a contradictory sentence cannot be
# appended while preserving a few required substrings.
_CLAIM_BOUNDARY_SHA256 = (
    "43201a7fc960ccf3cbc615cddbc78b94ad81be78d0dd30e68092c5c47da0566b"
)

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_SAFE_PATH_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_MAX_JSON_BYTES = 8 * 1024 * 1024
_MAX_CASES = 500
_MAX_TEXT_BYTES = 256 * 1024

_MANIFEST_KEYS = {
    "schema_version",
    "evaluation_id",
    "status",
    "scoring_unit",
    "scanner",
    "freeze",
    "inputs",
    "output",
    "reference_labels",
    "raw_count_fields",
    "coverage_contract",
    "development_source_exclusions",
    "external_blockers",
    "claim_boundary",
}
_SCANNER_KEYS = {
    "module",
    "scanner_path",
    "scanner_sha256",
    "checks_path",
    "checks_sha256",
    "check_ids",
    "evaluator_path",
    "evaluator_sha256",
}
_FREEZE_KEYS = {
    "freeze_id",
    "corpus_frozen_at",
    "corpus_repository_commit_sha",
    "prediction_generated_at",
    "prediction_repository_commit_sha",
    "answer_key_unblinded_at",
    "scoring_run_at",
    "scoring_repository_commit_sha",
    "corpus_status",
}
_INPUT_KEYS = {
    "cases_path",
    "cases_sha256",
    "answer_key_path",
    "answer_key_sha256",
    "predictions_path",
    "predictions_sha256",
}
_COVERAGE_KEYS = {
    "official_targeted_pairs_per_check",
    "synthetic_targeted_pairs_per_check",
    "required_category_ids",
    "incidental_findings_count_toward_coverage",
    "synthetic_controls_reported_separately",
    "pair_universe",
    "target_checks_per_case",
    "multi_target_cases_supported",
    "reporting_grains",
}
_MINIMUM_KEYS = {"should_flag", "should_stay_quiet"}
_EXCLUSION_KEYS = {
    "source_id",
    "canonical_url",
    "retained_raw_sha256",
    "reason",
    "near_duplicate_disposition",
}

_CASES_KEYS = {
    "schema_version",
    "evaluation_id",
    "freeze_id",
    "frozen_at",
    "corpus_repository_commit_sha",
    "selection",
    "cases",
}
_SELECTION_KEYS = {
    "method",
    "custodian_id",
    "selected_before_scanner_run",
    "near_duplicate_review_completed",
}
_CASE_KEYS = {
    "case_id",
    "category_id",
    "stratum",
    "target_check_id",
    "selection_role",
    "selection_rationale",
    "passage",
    "passage_sha256",
    "source",
}
_SOURCE_KEYS = {
    "source_id",
    "canonical_url",
    "document_sha256",
    "passage_locator",
    "retrieved_on",
}

_ANSWER_KEY_KEYS = {
    "schema_version",
    "evaluation_id",
    "freeze_id",
    "cases_sha256",
    "checks_sha256",
    "law_as_of",
    "check_registry_as_of",
    "reviewers",
    "adjudication",
    "unblinded_at",
}
_REVIEWER_KEYS = {
    "reviewer_id",
    "qualification",
    "method",
    "reviewed_at",
    "predictions_seen_before_initial_labels",
    "judgments",
}
_JUDGMENT_KEYS = {"case_id", "check_id", "label"}
_ADJUDICATION_KEYS = {
    "adjudicator_id",
    "method",
    "adjudicated_at",
    "disagreements",
    "final_judgments",
}
_DISAGREEMENT_KEYS = {
    "case_id",
    "check_id",
    "rationale",
    "citation",
}

_PREDICTIONS_KEYS = {
    "schema_version",
    "evaluation_id",
    "freeze_id",
    "generated_at",
    "repository_commit_sha",
    "bindings",
    "machine_output",
    "machine_abstain",
    "cases",
}
_PREDICTION_BINDING_KEYS = {
    "manifest_sha256",
    "cases_sha256",
    "checks_sha256",
    "scanner_sha256",
    "evaluator_sha256",
}
_PREDICTION_CASE_KEYS = {
    "case_id",
    "observed_check_ids",
    "finding_counts",
}

_RESULT_KEYS = {
    "schema_version",
    "evaluation_id",
    "freeze_id",
    "status",
    "scored_at",
    "repository_commit_sha",
    "bindings",
    "chronology",
    "reference_as_of",
    "machine_output",
    "machine_abstain",
    "raw_counts_by_partition",
    "raw_counts_by_check",
    "pair_outcomes",
    "corpus_lifecycle",
    "claim_boundary",
}
_RESULT_BINDING_KEYS = {
    "manifest_sha256",
    "cases_sha256",
    "answer_key_sha256",
    "predictions_sha256",
    "checks_sha256",
    "scanner_sha256",
    "evaluator_sha256",
    "corpus_repository_commit_sha",
    "prediction_repository_commit_sha",
}


class _DuplicateKey(ValueError):
    """Raised before JSON decoding can overwrite a duplicate object key."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"unsupported JSON constant {value!r}")


def _read_json_bytes(raw: bytes, field: str) -> Any:
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except _DuplicateKey as error:
        raise ValueError(f"{field}: duplicate JSON key {error}") from error
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError(f"{field}: invalid UTF-8 JSON") from error


def _read_json_file(path: Path, field: str) -> tuple[Any, bytes]:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise ValueError(f"{field}: expected a readable regular file") from error
    if path.is_symlink() or not path.is_file() or metadata.st_size > _MAX_JSON_BYTES:
        raise ValueError(f"{field}: expected a bounded regular file")
    raw = path.read_bytes()
    if len(raw) > _MAX_JSON_BYTES:
        raise ValueError(f"{field}: file exceeds the size limit")
    return _read_json_bytes(raw, field), raw


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected an object")
    return value


def _exact_keys(value: dict[str, Any], keys: set[str], field: str) -> None:
    if set(value) != keys:
        raise ValueError(f"{field}: invalid fields")


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field}: expected exact non-blank text")
    return value


def _identifier(value: Any, field: str) -> str:
    result = _text(value, field)
    if not _IDENTIFIER.fullmatch(result):
        raise ValueError(f"{field}: invalid stable identifier")
    return result


def _sha256(value: Any, field: str) -> str:
    result = _text(value, field)
    if not _SHA256.fullmatch(result):
        raise ValueError(f"{field}: expected lowercase SHA-256")
    return result


def _optional_sha256(value: Any, field: str) -> str | None:
    return None if value is None else _sha256(value, field)


def _commit(value: Any, field: str) -> str:
    result = _text(value, field)
    if not _COMMIT_SHA.fullmatch(result):
        raise ValueError(f"{field}: expected a full lowercase Git SHA")
    return result


def _iso_date(value: Any, field: str) -> str:
    result = _text(value, field)
    try:
        parsed = date.fromisoformat(result)
    except ValueError as error:
        raise ValueError(f"{field}: expected an ISO date") from error
    if parsed.isoformat() != result:
        raise ValueError(f"{field}: expected an exact ISO date")
    return result


def _iso_datetime(value: Any, field: str) -> str:
    result = _text(value, field)
    if not result.endswith("Z"):
        raise ValueError(f"{field}: expected a UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(result[:-1] + "+00:00")
    except ValueError as error:
        raise ValueError(f"{field}: expected an ISO UTC timestamp") from error
    if parsed.tzinfo != UTC or parsed.microsecond:
        raise ValueError(f"{field}: expected second-precision UTC")
    return result


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value[:-1] + "+00:00")


def _https_url(value: Any, field: str) -> str:
    result = _text(value, field)
    parsed = urlsplit(result)
    if (
        not result.isascii()
        or parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"{field}: expected an HTTPS URL")
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError(f"{field}: invalid URL port") from error
    host = parsed.hostname
    path_parts = parsed.path.split("/")
    if (
        host is None
        or host.endswith(".")
        or "%" in parsed.path
        or "\\" in parsed.path
        or any(part in {".", ".."} for part in path_parts)
        or any(not part for part in path_parts[1:])
    ):
        raise ValueError(f"{field}: invalid canonical URL")
    normalized_host = host.casefold()
    if ":" in normalized_host:
        normalized_host = f"[{normalized_host}]"
    netloc = normalized_host if port in {None, 443} else f"{normalized_host}:{port}"
    normalized = f"https://{netloc}{parsed.path or '/'}"
    if result != normalized:
        raise ValueError(f"{field}: expected a canonical HTTPS URL")
    return result


def _safe_path(value: Any, field: str) -> str:
    result = _text(value, field)
    if not result.isascii() or result.startswith("/") or "\\" in result:
        raise ValueError(f"{field}: expected a portable relative path")
    parts = result.split("/")
    if any(
        part in {"", ".", ".."} or not _SAFE_PATH_COMPONENT.fullmatch(part)
        for part in parts
    ):
        raise ValueError(f"{field}: unsafe path")
    return result


def _string_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field}: expected a list")
    result = tuple(_text(item, f"{field}[{index}]") for index, item in enumerate(value))
    if len(result) != len(set(result)):
        raise ValueError(f"{field}: duplicate values")
    return result


def _raw_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _file_sha256(root: Path, relative: str, field: str) -> str:
    path = root / Path(*relative.split("/"))
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"{field}: expected a readable file") from error
    if (
        not resolved.is_relative_to(root.resolve())
        or path.is_symlink()
        or not path.is_file()
    ):
        raise ValueError(f"{field}: expected a regular file inside the repository")
    return _raw_sha256(path.read_bytes())


@dataclass(frozen=True)
class DevelopmentExclusion:
    source_id: str
    canonical_url: str
    retained_raw_sha256: str | None


@dataclass(frozen=True)
class EvaluationManifest:
    evaluation_id: str
    check_ids: tuple[str, ...]
    scanner_path: str
    scanner_sha256: str
    checks_path: str
    checks_sha256: str
    evaluator_path: str
    exclusions: tuple[DevelopmentExclusion, ...]
    official_flag_minimum: int
    official_quiet_minimum: int
    synthetic_flag_minimum: int
    synthetic_quiet_minimum: int
    required_category_ids: tuple[str, ...]
    raw_sha256: str
    payload: dict[str, Any]


def load_evaluation_manifest(  # noqa: C901 - strict schema branches fail closed.
    path: Path, repository_root: Path
) -> EvaluationManifest:
    """Validate the committed ``not_run`` planning manifest and its live pins."""

    raw_payload, raw = _read_json_file(path, "evaluation manifest")
    payload = _object(raw_payload, "evaluation manifest")
    _exact_keys(payload, _MANIFEST_KEYS, "evaluation manifest")
    if type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
        raise ValueError("evaluation manifest.schema_version: expected integer 1")
    evaluation_id = _identifier(payload.get("evaluation_id"), "evaluation_id")
    if (
        payload.get("status") != "not_run"
        or payload.get("scoring_unit") != "case_check_pair"
    ):
        raise ValueError("evaluation manifest: expected not_run case_check_pair plan")

    scanner = _object(payload.get("scanner"), "scanner")
    _exact_keys(scanner, _SCANNER_KEYS, "scanner")
    if scanner.get("module") != "permit_pathways.conformance":
        raise ValueError("scanner.module: unexpected scanner module")
    scanner_path = _safe_path(scanner.get("scanner_path"), "scanner.scanner_path")
    scanner_sha = _sha256(scanner.get("scanner_sha256"), "scanner.scanner_sha256")
    checks_path = _safe_path(scanner.get("checks_path"), "scanner.checks_path")
    checks_sha = _sha256(scanner.get("checks_sha256"), "scanner.checks_sha256")
    evaluator_path = _safe_path(scanner.get("evaluator_path"), "scanner.evaluator_path")
    if scanner.get("evaluator_sha256") is not None:
        raise ValueError("scanner.evaluator_sha256: not_run plan must remain null")
    check_ids = _string_list(scanner.get("check_ids"), "scanner.check_ids")
    if not check_ids or check_ids != tuple(sorted(check_ids)):
        raise ValueError("scanner.check_ids: expected a sorted non-empty list")
    root = repository_root.resolve()
    if _file_sha256(root, scanner_path, "scanner.scanner_path") != scanner_sha:
        raise ValueError("scanner.scanner_sha256: scanner bytes drifted")
    if _file_sha256(root, checks_path, "scanner.checks_path") != checks_sha:
        raise ValueError("scanner.checks_sha256: check registry bytes drifted")
    live_check_ids = tuple(
        sorted(check.check_id for check in load_checks(root / checks_path))
    )
    if live_check_ids != check_ids:
        raise ValueError("scanner.check_ids: check registry coverage drifted")
    if not (root / evaluator_path).is_file():
        raise ValueError("scanner.evaluator_path: evaluator is unavailable")

    freeze = _object(payload.get("freeze"), "freeze")
    _exact_keys(freeze, _FREEZE_KEYS, "freeze")
    if freeze.get("corpus_status") != "not_frozen" or any(
        freeze.get(key) is not None for key in _FREEZE_KEYS - {"corpus_status"}
    ):
        raise ValueError("freeze: not_run plan must have null execution fields")
    inputs = _object(payload.get("inputs"), "inputs")
    _exact_keys(inputs, _INPUT_KEYS, "inputs")
    if any(value is not None for value in inputs.values()):
        raise ValueError("inputs: not_run plan must have null inputs")
    output = _object(payload.get("output"), "output")
    _exact_keys(output, {"result_path"}, "output")
    if output.get("result_path") is not None:
        raise ValueError("output.result_path: not_run plan must remain null")
    if (
        _string_list(payload.get("reference_labels"), "reference_labels")
        != REFERENCE_LABELS
    ):
        raise ValueError("reference_labels: invalid queue labels")
    if (
        _string_list(payload.get("raw_count_fields"), "raw_count_fields")
        != RAW_COUNT_FIELDS
    ):
        raise ValueError("raw_count_fields: invalid raw-count contract")

    coverage = _object(payload.get("coverage_contract"), "coverage_contract")
    _exact_keys(coverage, _COVERAGE_KEYS, "coverage_contract")
    official = _minimums(
        coverage.get("official_targeted_pairs_per_check"),
        "coverage_contract.official_targeted_pairs_per_check",
    )
    synthetic = _minimums(
        coverage.get("synthetic_targeted_pairs_per_check"),
        "coverage_contract.synthetic_targeted_pairs_per_check",
    )
    categories = tuple(
        _identifier(item, f"coverage_contract.required_category_ids[{index}]")
        for index, item in enumerate(
            _string_list(
                coverage.get("required_category_ids"),
                "coverage_contract.required_category_ids",
            )
        )
    )
    if len(categories) != len(set(categories)):
        raise ValueError("coverage_contract.required_category_ids: duplicates")
    if coverage.get("incidental_findings_count_toward_coverage") is not False:
        raise ValueError("coverage_contract: incidental pairs cannot satisfy coverage")
    if coverage.get("synthetic_controls_reported_separately") is not True:
        raise ValueError("coverage_contract: synthetic controls must be separate")
    if coverage.get("pair_universe") != "full_case_check_cartesian_product":
        raise ValueError("coverage_contract: full Cartesian pair universe is required")
    if (
        type(coverage.get("target_checks_per_case")) is not int
        or coverage.get("target_checks_per_case") != 1
    ):
        raise ValueError("coverage_contract: exactly one target check is required")
    if coverage.get("multi_target_cases_supported") is not False:
        raise ValueError(
            "coverage_contract: schema v1 does not support multi-target cases"
        )
    if _string_list(
        coverage.get("reporting_grains"), "coverage_contract.reporting_grains"
    ) != (
        "overall",
        "per_check",
        "official_targeted",
        "synthetic_targeted",
        "official_incidental",
        "synthetic_incidental",
    ):
        raise ValueError("coverage_contract: invalid reporting grains")

    exclusions_raw = payload.get("development_source_exclusions")
    if not isinstance(exclusions_raw, list) or not exclusions_raw:
        raise ValueError("development_source_exclusions: expected a non-empty list")
    exclusions = tuple(
        _parse_exclusion(item, index) for index, item in enumerate(exclusions_raw)
    )
    if len({item.source_id for item in exclusions}) != len(exclusions):
        raise ValueError("development_source_exclusions: duplicate source ID")
    if len({item.canonical_url for item in exclusions}) != len(exclusions):
        raise ValueError("development_source_exclusions: duplicate canonical URL")
    blockers = _string_list(payload.get("external_blockers"), "external_blockers")
    if len(blockers) < 3:
        raise ValueError(
            "external_blockers: expected source, review, and custody blockers"
        )
    claim_boundary = _text(payload.get("claim_boundary"), "claim_boundary")
    if _raw_sha256(claim_boundary.encode("utf-8")) != _CLAIM_BOUNDARY_SHA256:
        raise ValueError("claim_boundary: expected the exact schema-v1 policy")

    return EvaluationManifest(
        evaluation_id=evaluation_id,
        check_ids=check_ids,
        scanner_path=scanner_path,
        scanner_sha256=scanner_sha,
        checks_path=checks_path,
        checks_sha256=checks_sha,
        evaluator_path=evaluator_path,
        exclusions=exclusions,
        official_flag_minimum=official["should_flag"],
        official_quiet_minimum=official["should_stay_quiet"],
        synthetic_flag_minimum=synthetic["should_flag"],
        synthetic_quiet_minimum=synthetic["should_stay_quiet"],
        required_category_ids=categories,
        raw_sha256=_raw_sha256(raw),
        payload=payload,
    )


def _minimums(value: Any, field: str) -> dict[str, int]:
    result = _object(value, field)
    _exact_keys(result, _MINIMUM_KEYS, field)
    for key, minimum in result.items():
        if type(minimum) is not int or minimum < 0:
            raise ValueError(f"{field}.{key}: expected a non-negative integer")
    return result


def _parse_exclusion(value: Any, index: int) -> DevelopmentExclusion:
    field = f"development_source_exclusions[{index}]"
    record = _object(value, field)
    _exact_keys(record, _EXCLUSION_KEYS, field)
    _text(record.get("reason"), f"{field}.reason")
    if record.get("near_duplicate_disposition") != NEAR_DUPLICATE_DISPOSITION:
        raise ValueError(
            f"{field}.near_duplicate_disposition: expected the exclusion policy"
        )
    return DevelopmentExclusion(
        source_id=_identifier(record.get("source_id"), f"{field}.source_id"),
        canonical_url=_https_url(record.get("canonical_url"), f"{field}.canonical_url"),
        retained_raw_sha256=_optional_sha256(
            record.get("retained_raw_sha256"), f"{field}.retained_raw_sha256"
        ),
    )


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    category_id: str
    stratum: str
    target_check_id: str
    selection_role: str
    passage: str
    source_id: str
    canonical_url: str | None
    document_sha256: str | None


@dataclass(frozen=True)
class CaseSet:
    evaluation_id: str
    freeze_id: str
    frozen_at: str
    corpus_repository_commit_sha: str
    cases: tuple[EvaluationCase, ...]
    raw_sha256: str


def load_case_set(path: Path, manifest: EvaluationManifest) -> CaseSet:
    """Load a frozen passage set without opening or requiring an answer key."""

    raw_payload, raw = _read_json_file(path, "case set")
    payload = _object(raw_payload, "case set")
    _exact_keys(payload, _CASES_KEYS, "case set")
    if type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
        raise ValueError("case set.schema_version: expected integer 1")
    if payload.get("evaluation_id") != manifest.evaluation_id:
        raise ValueError("case set.evaluation_id: does not match manifest")
    freeze_id = _identifier(payload.get("freeze_id"), "case set.freeze_id")
    frozen_at = _iso_datetime(payload.get("frozen_at"), "case set.frozen_at")
    corpus_commit = _commit(
        payload.get("corpus_repository_commit_sha"),
        "case set.corpus_repository_commit_sha",
    )
    selection = _object(payload.get("selection"), "case set.selection")
    _exact_keys(selection, _SELECTION_KEYS, "case set.selection")
    _text(selection.get("method"), "case set.selection.method")
    _identifier(selection.get("custodian_id"), "case set.selection.custodian_id")
    if selection.get("selected_before_scanner_run") is not True:
        raise ValueError(
            "case set.selection: cases must be selected before scanner run"
        )
    if selection.get("near_duplicate_review_completed") is not True:
        raise ValueError("case set.selection: near-duplicate review is required")
    cases_raw = payload.get("cases")
    if not isinstance(cases_raw, list) or not cases_raw or len(cases_raw) > _MAX_CASES:
        raise ValueError("case set.cases: expected a bounded non-empty list")
    cases = tuple(
        _parse_case(
            item,
            index,
            manifest,
            frozen_on=_timestamp(frozen_at).date(),
        )
        for index, item in enumerate(cases_raw)
    )
    case_ids = tuple(item.case_id for item in cases)
    if case_ids != tuple(sorted(case_ids)) or len(case_ids) != len(set(case_ids)):
        raise ValueError("case set.cases: expected sorted unique case IDs")
    passage_digests = tuple(_raw_sha256(item.passage.encode("utf-8")) for item in cases)
    if len(passage_digests) != len(set(passage_digests)):
        raise ValueError("case set.cases: duplicate passages cannot be counted twice")
    _validate_case_source_identity(cases)
    categories = {item.category_id for item in cases}
    if not set(manifest.required_category_ids) <= categories:
        raise ValueError("case set.cases: required category coverage is missing")
    return CaseSet(
        evaluation_id=manifest.evaluation_id,
        freeze_id=freeze_id,
        frozen_at=frozen_at,
        corpus_repository_commit_sha=corpus_commit,
        cases=cases,
        raw_sha256=_raw_sha256(raw),
    )


def _validate_case_source_identity(cases: tuple[EvaluationCase, ...]) -> None:
    by_source_id: dict[str, tuple[str, str]] = {}
    by_url: dict[str, tuple[str, str]] = {}
    for case in cases:
        if case.stratum != "official":
            continue
        if case.canonical_url is None or case.document_sha256 is None:
            raise ValueError("case set.cases: official source binding is incomplete")
        source_binding = (case.canonical_url, case.document_sha256)
        previous_source = by_source_id.setdefault(case.source_id, source_binding)
        if previous_source != source_binding:
            raise ValueError("case set.cases: source ID maps to conflicting documents")
        url_binding = (case.source_id, case.document_sha256)
        previous_url = by_url.setdefault(case.canonical_url, url_binding)
        if previous_url != url_binding:
            raise ValueError(
                "case set.cases: canonical URL maps to conflicting sources"
            )


def _parse_case(
    value: Any,
    index: int,
    manifest: EvaluationManifest,
    *,
    frozen_on: date,
) -> EvaluationCase:
    field = f"case set.cases[{index}]"
    record = _object(value, field)
    _exact_keys(record, _CASE_KEYS, field)
    case_id = _identifier(record.get("case_id"), f"{field}.case_id")
    category_id = _identifier(record.get("category_id"), f"{field}.category_id")
    stratum = record.get("stratum")
    if stratum not in {"official", "synthetic"}:
        raise ValueError(f"{field}.stratum: expected official or synthetic")
    target_check_id = _identifier(
        record.get("target_check_id"), f"{field}.target_check_id"
    )
    if target_check_id not in manifest.check_ids:
        raise ValueError(f"{field}.target_check_id: unknown check")
    selection_role = record.get("selection_role")
    if selection_role not in {"candidate_flag", "candidate_near_miss"}:
        raise ValueError(
            f"{field}.selection_role: expected candidate_flag or candidate_near_miss"
        )
    _text(record.get("selection_rationale"), f"{field}.selection_rationale")
    passage = _text(record.get("passage"), f"{field}.passage")
    if len(passage.encode("utf-8")) > _MAX_TEXT_BYTES:
        raise ValueError(f"{field}.passage: text exceeds the size limit")
    if _raw_sha256(passage.encode("utf-8")) != _sha256(
        record.get("passage_sha256"), f"{field}.passage_sha256"
    ):
        raise ValueError(f"{field}.passage_sha256: passage bytes drifted")
    source = _object(record.get("source"), f"{field}.source")
    _exact_keys(source, _SOURCE_KEYS, f"{field}.source")
    source_id, canonical_url, document_sha = _parse_case_source(
        source, field, stratum, manifest, frozen_on
    )
    return EvaluationCase(
        case_id=case_id,
        category_id=category_id,
        stratum=stratum,
        target_check_id=target_check_id,
        selection_role=selection_role,
        passage=passage,
        source_id=source_id,
        canonical_url=canonical_url,
        document_sha256=document_sha,
    )


def _parse_case_source(
    source: dict[str, Any],
    field: str,
    stratum: str,
    manifest: EvaluationManifest,
    frozen_on: date,
) -> tuple[str, str | None, str | None]:
    source_id = _identifier(source.get("source_id"), f"{field}.source.source_id")
    _text(source.get("passage_locator"), f"{field}.source.passage_locator")
    if stratum == "official":
        canonical_url = _https_url(
            source.get("canonical_url"), f"{field}.source.canonical_url"
        )
        document_sha = _sha256(
            source.get("document_sha256"), f"{field}.source.document_sha256"
        )
        retrieved_on = _iso_date(
            source.get("retrieved_on"), f"{field}.source.retrieved_on"
        )
        if date.fromisoformat(retrieved_on) > frozen_on:
            raise ValueError(f"{field}.source.retrieved_on: retrieval postdates freeze")
        _reject_development_source(
            manifest, source_id, canonical_url, document_sha, field
        )
    else:
        if not source_id.startswith("synthetic-"):
            raise ValueError(f"{field}.source.source_id: synthetic ID must be explicit")
        if (
            source.get("canonical_url") is not None
            or source.get("document_sha256") is not None
        ):
            raise ValueError(
                f"{field}.source: synthetic controls cannot claim a document"
            )
        if source.get("retrieved_on") is not None:
            raise ValueError(
                f"{field}.source.retrieved_on: synthetic control must be null"
            )
        canonical_url = None
        document_sha = None
    return source_id, canonical_url, document_sha


def _reject_development_source(
    manifest: EvaluationManifest,
    source_id: str,
    canonical_url: str,
    document_sha256: str,
    field: str,
) -> None:
    for exclusion in manifest.exclusions:
        if source_id == exclusion.source_id or canonical_url == exclusion.canonical_url:
            raise ValueError(
                f"{field}.source: development-influencing source is excluded"
            )
        if exclusion.retained_raw_sha256 == document_sha256:
            raise ValueError(f"{field}.source: development-source digest is excluded")


def expected_pair_keys(
    cases: CaseSet, manifest: EvaluationManifest
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (case.case_id, check_id)
        for case in cases.cases
        for check_id in manifest.check_ids
    )


@dataclass(frozen=True)
class AnswerKey:
    final_labels: dict[tuple[str, str], str]
    unblinded_at: str
    law_as_of: str
    check_registry_as_of: str
    raw_sha256: str


def load_answer_key(  # noqa: C901 - reviewer/adjudication invariants are explicit.
    path: Path,
    manifest: EvaluationManifest,
    cases: CaseSet,
    *,
    today: date | None = None,
) -> AnswerKey:
    """Load a two-reviewer, pair-complete key after blind predictions exist."""

    raw_payload, raw = _read_json_file(path, "answer key")
    payload = _object(raw_payload, "answer key")
    _exact_keys(payload, _ANSWER_KEY_KEYS, "answer key")
    if type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
        raise ValueError("answer key.schema_version: expected integer 1")
    if payload.get("evaluation_id") != manifest.evaluation_id:
        raise ValueError("answer key.evaluation_id: does not match manifest")
    if payload.get("freeze_id") != cases.freeze_id:
        raise ValueError("answer key.freeze_id: does not match cases")
    if (
        _sha256(payload.get("cases_sha256"), "answer key.cases_sha256")
        != cases.raw_sha256
    ):
        raise ValueError("answer key.cases_sha256: case set drifted")
    if (
        _sha256(payload.get("checks_sha256"), "answer key.checks_sha256")
        != manifest.checks_sha256
    ):
        raise ValueError("answer key.checks_sha256: check registry drifted")
    law_as_of = _iso_date(payload.get("law_as_of"), "answer key.law_as_of")
    registry_as_of = _iso_date(
        payload.get("check_registry_as_of"), "answer key.check_registry_as_of"
    )
    current_date = date.today() if today is None else today
    if date.fromisoformat(law_as_of) > current_date:
        raise ValueError("answer key.law_as_of: future source state is not allowed")
    if date.fromisoformat(registry_as_of) > current_date:
        raise ValueError(
            "answer key.check_registry_as_of: future source state is not allowed"
        )
    reviewers_raw = payload.get("reviewers")
    if not isinstance(reviewers_raw, list) or len(reviewers_raw) != 2:
        raise ValueError("answer key.reviewers: exactly two reviewers are required")
    expected = set(expected_pair_keys(cases, manifest))
    reviewer_maps: list[dict[tuple[str, str], str]] = []
    reviewer_ids: list[str] = []
    reviewed_at: list[str] = []
    for index, raw_reviewer in enumerate(reviewers_raw):
        field = f"answer key.reviewers[{index}]"
        reviewer = _object(raw_reviewer, field)
        _exact_keys(reviewer, _REVIEWER_KEYS, field)
        reviewer_ids.append(
            _identifier(reviewer.get("reviewer_id"), f"{field}.reviewer_id")
        )
        _text(reviewer.get("qualification"), f"{field}.qualification")
        _text(reviewer.get("method"), f"{field}.method")
        reviewed_at.append(
            _iso_datetime(reviewer.get("reviewed_at"), f"{field}.reviewed_at")
        )
        if reviewer.get("predictions_seen_before_initial_labels") is not False:
            raise ValueError(f"{field}: initial judgments were not blind")
        reviewer_maps.append(
            _judgment_map(reviewer.get("judgments"), expected, f"{field}.judgments")
        )
    if len(reviewer_ids) != len(set(reviewer_ids)):
        raise ValueError("answer key.reviewers: reviewer IDs must be distinct")

    adjudication = _object(payload.get("adjudication"), "answer key.adjudication")
    _exact_keys(adjudication, _ADJUDICATION_KEYS, "answer key.adjudication")
    adjudicator_id = _identifier(
        adjudication.get("adjudicator_id"), "answer key.adjudication.adjudicator_id"
    )
    if adjudicator_id in reviewer_ids:
        raise ValueError("answer key.adjudication: adjudicator ID must be distinct")
    _text(adjudication.get("method"), "answer key.adjudication.method")
    adjudicated_at = _iso_datetime(
        adjudication.get("adjudicated_at"), "answer key.adjudication.adjudicated_at"
    )
    final_labels = _judgment_map(
        adjudication.get("final_judgments"),
        expected,
        "answer key.adjudication.final_judgments",
    )
    disagreements = {
        pair
        for pair in expected
        if len({mapping[pair] for mapping in reviewer_maps}) > 1
    }
    recorded_disagreements = _disagreement_keys(
        adjudication.get("disagreements"), expected
    )
    if disagreements != recorded_disagreements:
        raise ValueError(
            "answer key.adjudication.disagreements: does not match reviewers"
        )
    for pair in expected - disagreements:
        if final_labels[pair] != reviewer_maps[0][pair]:
            raise ValueError("answer key.adjudication: agreement was changed")
    unblinded_at = _iso_datetime(payload.get("unblinded_at"), "answer key.unblinded_at")
    if any(_timestamp(cases.frozen_at) > _timestamp(item) for item in reviewed_at):
        raise ValueError("answer key: review predates corpus freeze")
    if max(_timestamp(item) for item in reviewed_at) > _timestamp(adjudicated_at):
        raise ValueError("answer key: adjudication predates review")
    if _timestamp(adjudicated_at) > _timestamp(unblinded_at):
        raise ValueError("answer key: unblinding predates adjudication")
    unblinded_date = _timestamp(unblinded_at).date()
    if date.fromisoformat(law_as_of) > unblinded_date:
        raise ValueError("answer key.law_as_of: source state postdates unblinding")
    if date.fromisoformat(registry_as_of) > unblinded_date:
        raise ValueError(
            "answer key.check_registry_as_of: source state postdates unblinding"
        )
    _validate_coverage(manifest, cases, final_labels)
    return AnswerKey(
        final_labels=final_labels,
        unblinded_at=unblinded_at,
        law_as_of=law_as_of,
        check_registry_as_of=registry_as_of,
        raw_sha256=_raw_sha256(raw),
    )


def _judgment_map(
    value: Any,
    expected: set[tuple[str, str]],
    field: str,
) -> dict[tuple[str, str], str]:
    if not isinstance(value, list):
        raise ValueError(f"{field}: expected a list")
    result: dict[tuple[str, str], str] = {}
    for index, raw in enumerate(value):
        item_field = f"{field}[{index}]"
        record = _object(raw, item_field)
        _exact_keys(record, _JUDGMENT_KEYS, item_field)
        pair = (
            _identifier(record.get("case_id"), f"{item_field}.case_id"),
            _identifier(record.get("check_id"), f"{item_field}.check_id"),
        )
        label = record.get("label")
        if label not in REFERENCE_LABELS:
            raise ValueError(f"{item_field}.label: invalid reference label")
        if pair in result:
            raise ValueError(f"{field}: duplicate case/check pair")
        result[pair] = label
    if set(result) != expected:
        raise ValueError(f"{field}: expected exact case/check coverage")
    return result


def _disagreement_keys(
    value: Any, expected: set[tuple[str, str]]
) -> set[tuple[str, str]]:
    if not isinstance(value, list):
        raise ValueError("answer key.adjudication.disagreements: expected a list")
    result: set[tuple[str, str]] = set()
    for index, raw in enumerate(value):
        field = f"answer key.adjudication.disagreements[{index}]"
        record = _object(raw, field)
        _exact_keys(record, _DISAGREEMENT_KEYS, field)
        pair = (
            _identifier(record.get("case_id"), f"{field}.case_id"),
            _identifier(record.get("check_id"), f"{field}.check_id"),
        )
        if pair not in expected or pair in result:
            raise ValueError(f"{field}: unknown or duplicate pair")
        _text(record.get("rationale"), f"{field}.rationale")
        _text(record.get("citation"), f"{field}.citation")
        result.add(pair)
    return result


def _validate_coverage(
    manifest: EvaluationManifest,
    cases: CaseSet,
    labels: dict[tuple[str, str], str],
) -> None:
    case_by_id = {case.case_id: case for case in cases.cases}
    required = {
        "official": {
            "should_flag": manifest.official_flag_minimum,
            "should_stay_quiet": manifest.official_quiet_minimum,
        },
        "synthetic": {
            "should_flag": manifest.synthetic_flag_minimum,
            "should_stay_quiet": manifest.synthetic_quiet_minimum,
        },
    }
    for stratum, minima in required.items():
        for check_id in manifest.check_ids:
            for label, minimum in minima.items():
                count = sum(
                    1
                    for (case_id, pair_check_id), pair_label in labels.items()
                    if pair_check_id == check_id
                    and case_by_id[case_id].target_check_id == check_id
                    and case_by_id[case_id].stratum == stratum
                    and case_by_id[case_id].selection_role
                    == (
                        "candidate_flag"
                        if label == "should_flag"
                        else "candidate_near_miss"
                    )
                    and pair_label == label
                )
                if count < minimum:
                    raise ValueError(
                        "answer key: targeted coverage minimum is not satisfied"
                    )


@dataclass(frozen=True)
class Predictions:
    payload: dict[str, Any]
    generated_at: str
    repository_commit_sha: str
    observations: dict[str, dict[str, int]]
    raw_sha256: str | None = None


def generate_blind_predictions(
    manifest: EvaluationManifest,
    cases: CaseSet,
    repository_root: Path,
    *,
    generated_at: str,
    repository_commit_sha: str,
) -> Predictions:
    """Run the scanner without accepting or reading an answer key."""

    timestamp = _iso_datetime(generated_at, "predictions.generated_at")
    commit_sha = _commit(repository_commit_sha, "predictions.repository_commit_sha")
    if _timestamp(timestamp) < _timestamp(cases.frozen_at):
        raise ValueError("predictions.generated_at: prediction predates corpus freeze")
    root = repository_root.resolve()
    if _file_sha256(root, manifest.scanner_path, "scanner") != manifest.scanner_sha256:
        raise ValueError("predictions: scanner bytes drifted after plan validation")
    if _file_sha256(root, manifest.checks_path, "checks") != manifest.checks_sha256:
        raise ValueError("predictions: check bytes drifted after plan validation")
    evaluator_digest = _file_sha256(root, manifest.evaluator_path, "evaluator")
    checks = load_checks(root / manifest.checks_path)
    if tuple(sorted(check.check_id for check in checks)) != manifest.check_ids:
        raise ValueError("predictions: active checks do not match the manifest")
    observations: dict[str, dict[str, int]] = {}
    records: list[dict[str, Any]] = []
    for case in cases.cases:
        try:
            findings = scan(case.passage, checks)
        except (re.error, RecursionError) as error:
            raise ValueError(
                f"predictions: scanner failed for {case.case_id}"
            ) from error
        counts = Counter(finding.check.check_id for finding in findings)
        if not set(counts) <= set(manifest.check_ids):
            raise ValueError("predictions: scanner emitted an unknown check")
        observed = {
            check_id: counts.get(check_id, 0) for check_id in manifest.check_ids
        }
        observations[case.case_id] = observed
        records.append(
            {
                "case_id": case.case_id,
                "observed_check_ids": [
                    check_id
                    for check_id in manifest.check_ids
                    if observed[check_id] > 0
                ],
                "finding_counts": observed,
            }
        )
    payload = {
        "schema_version": 1,
        "evaluation_id": manifest.evaluation_id,
        "freeze_id": cases.freeze_id,
        "generated_at": timestamp,
        "repository_commit_sha": commit_sha,
        "bindings": {
            "manifest_sha256": manifest.raw_sha256,
            "cases_sha256": cases.raw_sha256,
            "checks_sha256": manifest.checks_sha256,
            "scanner_sha256": manifest.scanner_sha256,
            "evaluator_sha256": evaluator_digest,
        },
        "machine_output": "binary_flag_or_quiet",
        "machine_abstain": 0,
        "cases": records,
    }
    return Predictions(
        payload=payload,
        generated_at=timestamp,
        repository_commit_sha=commit_sha,
        observations=observations,
    )


def load_predictions(  # noqa: C901 - every receipt field is checked independently.
    path: Path,
    manifest: EvaluationManifest,
    cases: CaseSet,
    repository_root: Path,
) -> Predictions:
    raw_payload, raw = _read_json_file(path, "predictions")
    payload = _object(raw_payload, "predictions")
    _exact_keys(payload, _PREDICTIONS_KEYS, "predictions")
    if type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
        raise ValueError("predictions.schema_version: expected integer 1")
    if payload.get("evaluation_id") != manifest.evaluation_id:
        raise ValueError("predictions.evaluation_id: does not match manifest")
    if payload.get("freeze_id") != cases.freeze_id:
        raise ValueError("predictions.freeze_id: does not match cases")
    generated_at = _iso_datetime(
        payload.get("generated_at"), "predictions.generated_at"
    )
    repository_commit = _commit(
        payload.get("repository_commit_sha"), "predictions.repository_commit_sha"
    )
    bindings = _object(payload.get("bindings"), "predictions.bindings")
    _exact_keys(bindings, _PREDICTION_BINDING_KEYS, "predictions.bindings")
    evaluator_sha256 = _file_sha256(
        repository_root.resolve(), manifest.evaluator_path, "predictions.evaluator"
    )
    expected_bindings = {
        "manifest_sha256": manifest.raw_sha256,
        "cases_sha256": cases.raw_sha256,
        "checks_sha256": manifest.checks_sha256,
        "scanner_sha256": manifest.scanner_sha256,
        "evaluator_sha256": evaluator_sha256,
    }
    for key, expected in expected_bindings.items():
        if _sha256(bindings.get(key), f"predictions.bindings.{key}") != expected:
            raise ValueError(f"predictions.bindings.{key}: binding drifted")
    if payload.get("machine_output") != "binary_flag_or_quiet":
        raise ValueError("predictions.machine_output: expected binary scanner")
    if (
        type(payload.get("machine_abstain")) is not int
        or payload["machine_abstain"] != 0
    ):
        raise ValueError(
            "predictions.machine_abstain: current scanner must report zero"
        )
    records = payload.get("cases")
    if not isinstance(records, list):
        raise ValueError("predictions.cases: expected a list")
    observations: dict[str, dict[str, int]] = {}
    for index, raw_record in enumerate(records):
        field = f"predictions.cases[{index}]"
        record = _object(raw_record, field)
        _exact_keys(record, _PREDICTION_CASE_KEYS, field)
        case_id = _identifier(record.get("case_id"), f"{field}.case_id")
        if case_id in observations:
            raise ValueError("predictions.cases: duplicate case")
        observed_ids = _string_list(
            record.get("observed_check_ids"), f"{field}.observed_check_ids"
        )
        if observed_ids != tuple(sorted(observed_ids)) or not set(observed_ids) <= set(
            manifest.check_ids
        ):
            raise ValueError(f"{field}.observed_check_ids: invalid check list")
        raw_counts = _object(record.get("finding_counts"), f"{field}.finding_counts")
        if set(raw_counts) != set(manifest.check_ids):
            raise ValueError(f"{field}.finding_counts: expected every active check")
        counts: dict[str, int] = {}
        for check_id in manifest.check_ids:
            count = raw_counts[check_id]
            if type(count) is not int or count < 0:
                raise ValueError(f"{field}.finding_counts.{check_id}: invalid count")
            counts[check_id] = count
        if set(observed_ids) != {key for key, value in counts.items() if value > 0}:
            raise ValueError(f"{field}: observed IDs and finding counts disagree")
        observations[case_id] = counts
    if set(observations) != {case.case_id for case in cases.cases}:
        raise ValueError("predictions.cases: expected exact case coverage")
    if _timestamp(generated_at) < _timestamp(cases.frozen_at):
        raise ValueError("predictions.generated_at: prediction predates corpus freeze")
    return Predictions(
        payload=payload,
        generated_at=generated_at,
        repository_commit_sha=repository_commit,
        observations=observations,
        raw_sha256=_raw_sha256(raw),
    )


def _empty_counts() -> dict[str, int]:
    return {field: 0 for field in RAW_COUNT_FIELDS}


def _cell(label: str, observed: bool) -> str:
    if label == "reference_abstain":
        return "reference_abstain"
    if label == "should_flag":
        return (
            "expected_flag_observed_flag"
            if observed
            else "expected_flag_observed_quiet"
        )
    return (
        "expected_quiet_observed_flag" if observed else "expected_quiet_observed_quiet"
    )


def score_predictions(
    manifest: EvaluationManifest,
    cases: CaseSet,
    answer_key: AnswerKey,
    predictions: Predictions,
    *,
    scored_at: str,
    repository_commit_sha: str,
) -> dict[str, Any]:
    """Score frozen blind predictions and return raw, recomputable counts only."""

    scored = _iso_datetime(scored_at, "result.scored_at")
    scoring_commit = _commit(repository_commit_sha, "result.repository_commit_sha")
    if _timestamp(predictions.generated_at) >= _timestamp(answer_key.unblinded_at):
        raise ValueError(
            "result: predictions must be frozen before answer-key unblinding"
        )
    if _timestamp(answer_key.unblinded_at) > _timestamp(scored):
        raise ValueError("result: scoring predates answer-key unblinding")
    if predictions.raw_sha256 is None:
        raise ValueError("result: score only predictions reloaded from frozen bytes")

    case_by_id = {case.case_id: case for case in cases.cases}
    counts_by_partition = {partition: _empty_counts() for partition in PARTITIONS}
    per_check = {
        check_id: {partition: _empty_counts() for partition in PARTITIONS}
        for check_id in manifest.check_ids
    }
    outcomes: list[dict[str, Any]] = []
    for case_id, check_id in expected_pair_keys(cases, manifest):
        case = case_by_id[case_id]
        label = answer_key.final_labels[(case_id, check_id)]
        finding_count = predictions.observations[case_id][check_id]
        observed = finding_count > 0
        if check_id == case.target_check_id:
            partition = f"{case.stratum}_targeted"
        else:
            partition = f"{case.stratum}_incidental"
        cell = _cell(label, observed)
        counts_by_partition[partition][cell] += 1
        counts_by_partition["overall"][cell] += 1
        per_check[check_id][partition][cell] += 1
        per_check[check_id]["overall"][cell] += 1
        outcomes.append(
            {
                "case_id": case_id,
                "check_id": check_id,
                "partition": partition,
                "source_stratum": case.stratum,
                "targeted": check_id == case.target_check_id,
                "selection_role": case.selection_role,
                "reference_label": label,
                "observed_flag": observed,
                "finding_count": finding_count,
                "raw_cell": cell,
            }
        )
    _validate_count_sums(counts_by_partition, per_check, len(outcomes))
    return {
        "schema_version": 1,
        "evaluation_id": manifest.evaluation_id,
        "freeze_id": cases.freeze_id,
        "status": "completed_bounded_evaluation",
        "scored_at": scored,
        "repository_commit_sha": scoring_commit,
        "bindings": {
            "manifest_sha256": manifest.raw_sha256,
            "cases_sha256": cases.raw_sha256,
            "answer_key_sha256": answer_key.raw_sha256,
            "predictions_sha256": predictions.raw_sha256,
            "checks_sha256": manifest.checks_sha256,
            "scanner_sha256": manifest.scanner_sha256,
            "evaluator_sha256": predictions.payload["bindings"]["evaluator_sha256"],
            "corpus_repository_commit_sha": cases.corpus_repository_commit_sha,
            "prediction_repository_commit_sha": predictions.repository_commit_sha,
        },
        "chronology": {
            "corpus_frozen_at": cases.frozen_at,
            "predictions_generated_at": predictions.generated_at,
            "answer_key_unblinded_at": answer_key.unblinded_at,
            "scored_at": scored,
        },
        "reference_as_of": {
            "law": answer_key.law_as_of,
            "check_registry": answer_key.check_registry_as_of,
        },
        "machine_output": "binary_flag_or_quiet",
        "machine_abstain": 0,
        "raw_counts_by_partition": counts_by_partition,
        "raw_counts_by_check": per_check,
        "pair_outcomes": outcomes,
        "corpus_lifecycle": {
            "status": "consumed_after_unblinding",
            "reusable_as_held_out_for_future_scanner_versions": False,
        },
        "claim_boundary": (
            "Raw passage/check review-queue counts for this frozen corpus only; "
            "not compliance, legal accuracy, precision, recall, statewide coverage, "
            "or evidence for a scanner version tuned after unblinding."
        ),
    }


def _validate_count_sums(
    partitions: dict[str, dict[str, int]],
    per_check: dict[str, dict[str, dict[str, int]]],
    pair_count: int,
) -> None:
    if partitions["overall"]["machine_abstain"] != 0:
        raise ValueError("raw counts: machine abstention must remain zero")
    if sum(partitions["overall"].values()) != pair_count:
        raise ValueError("raw counts: overall denominator drifted")
    for field in RAW_COUNT_FIELDS:
        partition_sum = sum(
            partitions[name][field] for name in PARTITIONS if name != "overall"
        )
        if partition_sum != partitions["overall"][field]:
            raise ValueError("raw counts: partition totals drifted")
        check_sum = sum(
            check_counts["overall"][field] for check_counts in per_check.values()
        )
        if check_sum != partitions["overall"][field]:
            raise ValueError("raw counts: per-check totals drifted")
        for check_counts in per_check.values():
            check_partition_sum = sum(
                check_counts[name][field] for name in PARTITIONS if name != "overall"
            )
            if check_partition_sum != check_counts["overall"][field]:
                raise ValueError("raw counts: per-check partition totals drifted")


@dataclass(frozen=True)
class ResultReceipt:
    payload: dict[str, Any]
    raw_sha256: str


def load_result(
    path: Path,
    manifest: EvaluationManifest,
    cases: CaseSet,
    answer_key: AnswerKey,
    predictions: Predictions,
) -> ResultReceipt:
    """Reload and recompute a result so altered counts cannot pass validation."""

    raw_payload, raw = _read_json_file(path, "result")
    payload = _object(raw_payload, "result")
    _exact_keys(payload, _RESULT_KEYS, "result")
    bindings = _object(payload.get("bindings"), "result.bindings")
    _exact_keys(bindings, _RESULT_BINDING_KEYS, "result.bindings")
    scored_at = _iso_datetime(payload.get("scored_at"), "result.scored_at")
    repository_commit_sha = _commit(
        payload.get("repository_commit_sha"), "result.repository_commit_sha"
    )
    expected = score_predictions(
        manifest,
        cases,
        answer_key,
        predictions,
        scored_at=scored_at,
        repository_commit_sha=repository_commit_sha,
    )
    if payload != expected:
        raise ValueError("result: stored receipt does not match recomputed outcomes")
    return ResultReceipt(payload=payload, raw_sha256=_raw_sha256(raw))


def write_json_exclusive(path: Path, payload: dict[str, Any]) -> str:
    """Write deterministic JSON exclusively and return its out-of-band SHA-256."""

    if path.is_symlink() or path.exists():
        raise ValueError(f"{path}: refusing to overwrite an existing result")
    parent = path.parent.resolve()
    if not parent.is_dir() or path.parent.is_symlink():
        raise ValueError(f"{path.parent}: expected a real output directory")
    encoded = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    try:
        with path.open("xb") as stream:
            stream.write(encoded)
    except FileExistsError as error:
        raise ValueError(f"{path}: refusing to overwrite an existing result") from error
    return _raw_sha256(encoded)
