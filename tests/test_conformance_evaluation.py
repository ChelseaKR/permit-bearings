from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from permit_pathways.conformance import Check, load_checks
from permit_pathways.conformance_evaluation import (
    NEAR_DUPLICATE_DISPOSITION,
    RAW_COUNT_FIELDS,
    AnswerKey,
    CaseSet,
    DevelopmentExclusion,
    EvaluationManifest,
    Predictions,
    expected_pair_keys,
    generate_blind_predictions,
    load_answer_key,
    load_case_set,
    load_evaluation_manifest,
    load_predictions,
    load_result,
    score_predictions,
    write_json_exclusive,
)
from permit_pathways.conformance_evaluation_cli import main as evaluation_cli_main

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data/conformance/evaluations/heldout-v1/manifest.json"
CHECKS_PATH = ROOT / "data/conformance/checks.json"
SCANNER_PATH = ROOT / "src/permit_pathways/conformance.py"
EVALUATOR_PATH = ROOT / "src/permit_pathways/conformance_evaluation.py"

COMMIT_A = "a" * 40
COMMIT_B = "b" * 40
COMMIT_C = "c" * 40
EXCLUDED_DIGEST = "e" * 64


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _manifest(
    *,
    scanner_sha256: str = "1" * 64,
    checks_sha256: str = "2" * 64,
) -> EvaluationManifest:
    return EvaluationManifest(
        evaluation_id="synthetic-heldout-test",
        check_ids=("alpha-check", "beta-check"),
        scanner_path="scanner.py",
        scanner_sha256=scanner_sha256,
        checks_path="checks.json",
        checks_sha256=checks_sha256,
        evaluator_path="evaluator.py",
        exclusions=(
            DevelopmentExclusion(
                source_id="excluded-source",
                canonical_url="https://example.invalid/excluded.pdf",
                retained_raw_sha256=EXCLUDED_DIGEST,
            ),
        ),
        official_flag_minimum=1,
        official_quiet_minimum=1,
        synthetic_flag_minimum=0,
        synthetic_quiet_minimum=0,
        required_category_ids=(),
        raw_sha256="3" * 64,
        payload={},
    )


def _checks() -> list[Check]:
    return [
        Check(
            check_id="alpha-check",
            title="Synthetic alpha check",
            severity="review",
            patterns=[r"trigger alpha"],
            state_law="Synthetic test rule.",
            explanation="Synthetic test explanation.",
            hcd_precedent="Synthetic test precedent.",
        ),
        Check(
            check_id="beta-check",
            title="Synthetic beta check",
            severity="review",
            patterns=[r"trigger beta"],
            state_law="Synthetic test rule.",
            explanation="Synthetic test explanation.",
            hcd_precedent="Synthetic test precedent.",
        ),
    ]


def _prediction_repository(tmp_path: Path) -> tuple[Path, EvaluationManifest]:
    repository = tmp_path / "synthetic-repository"
    repository.mkdir()
    scanner = repository / "scanner.py"
    evaluator = repository / "evaluator.py"
    checks = repository / "checks.json"
    scanner.write_text(
        "# Synthetic scanner binding for unit tests.\n", encoding="utf-8"
    )
    evaluator.write_text(
        "# Synthetic evaluator binding for unit tests.\n", encoding="utf-8"
    )
    checks.write_text(
        json.dumps(
            [
                {
                    "check_id": check.check_id,
                    "title": check.title,
                    "severity": check.severity,
                    "patterns": check.patterns,
                    "state_law": check.state_law,
                    "explanation": check.explanation,
                    "hcd_precedent": check.hcd_precedent,
                }
                for check in _checks()
            ],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return repository, _manifest(
        scanner_sha256=_sha256(scanner.read_bytes()),
        checks_sha256=_sha256(checks.read_bytes()),
    )


def _case_record(
    case_id: str,
    target_check_id: str,
    passage: str,
    *,
    source_id: str | None = None,
    canonical_url: str | None = None,
    document_sha256: str | None = None,
    selection_role: str | None = None,
) -> dict[str, Any]:
    source_id = source_id or f"source-{case_id}"
    canonical_url = canonical_url or f"https://example.invalid/{case_id}.pdf"
    document_sha256 = document_sha256 or _sha256(f"document:{case_id}".encode())
    selection_role = selection_role or (
        "candidate_near_miss" if case_id.endswith("-quiet") else "candidate_flag"
    )
    return {
        "case_id": case_id,
        "category_id": f"category-{target_check_id}",
        "stratum": "official",
        "target_check_id": target_check_id,
        "selection_role": selection_role,
        "selection_rationale": (
            "Fabricated target-role rationale for unit testing only."
        ),
        "passage": passage,
        "passage_sha256": _sha256(passage.encode()),
        "source": {
            "source_id": source_id,
            "canonical_url": canonical_url,
            "document_sha256": document_sha256,
            "passage_locator": f"synthetic locator for {case_id}",
            "retrieved_on": "2026-01-01",
        },
    }


def _case_payload() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "evaluation_id": "synthetic-heldout-test",
        "freeze_id": "synthetic-freeze-v1",
        "frozen_at": "2026-01-01T00:00:00Z",
        "corpus_repository_commit_sha": COMMIT_A,
        "selection": {
            "method": "Fabricated temporary passages for unit testing only.",
            "custodian_id": "test-custodian",
            "selected_before_scanner_run": True,
            "near_duplicate_review_completed": True,
        },
        "cases": [
            _case_record(
                "official-alpha-flag",
                "alpha-check",
                "Fabricated passage: trigger alpha.",
            ),
            _case_record(
                "official-alpha-quiet",
                "alpha-check",
                "Fabricated quiet passage for alpha.",
            ),
            _case_record(
                "official-beta-flag",
                "beta-check",
                "Fabricated passage: trigger beta, then trigger beta.",
            ),
            _case_record(
                "official-beta-quiet",
                "beta-check",
                "Fabricated quiet passage for beta.",
            ),
        ],
    }


def _load_cases(tmp_path: Path, manifest: EvaluationManifest) -> CaseSet:
    path = tmp_path / "cases.json"
    _write_json(path, _case_payload())
    return load_case_set(path, manifest)


def _base_labels() -> dict[tuple[str, str], str]:
    return {
        ("official-alpha-flag", "alpha-check"): "should_flag",
        ("official-alpha-flag", "beta-check"): "reference_abstain",
        ("official-alpha-quiet", "alpha-check"): "should_stay_quiet",
        ("official-alpha-quiet", "beta-check"): "should_stay_quiet",
        ("official-beta-flag", "alpha-check"): "should_flag",
        ("official-beta-flag", "beta-check"): "should_flag",
        ("official-beta-quiet", "alpha-check"): "should_stay_quiet",
        ("official-beta-quiet", "beta-check"): "should_stay_quiet",
    }


def _judgments(labels: dict[tuple[str, str], str]) -> list[dict[str, str]]:
    return [
        {"case_id": case_id, "check_id": check_id, "label": label}
        for (case_id, check_id), label in sorted(labels.items())
    ]


def _answer_payload(cases: CaseSet, manifest: EvaluationManifest) -> dict[str, Any]:
    final_labels = _base_labels()
    reviewer_one = dict(final_labels)
    reviewer_two = dict(final_labels)
    disagreement = ("official-alpha-quiet", "beta-check")
    reviewer_two[disagreement] = "should_flag"
    return {
        "schema_version": 1,
        "evaluation_id": cases.evaluation_id,
        "freeze_id": cases.freeze_id,
        "cases_sha256": cases.raw_sha256,
        "checks_sha256": manifest.checks_sha256,
        "law_as_of": "2026-01-01",
        "check_registry_as_of": "2026-01-01",
        "reviewers": [
            {
                "reviewer_id": "reviewer-one",
                "qualification": "Synthetic qualified reviewer one.",
                "method": "Separate blind pair review.",
                "reviewed_at": "2026-01-03T00:00:00Z",
                "predictions_seen_before_initial_labels": False,
                "judgments": _judgments(reviewer_one),
            },
            {
                "reviewer_id": "reviewer-two",
                "qualification": "Synthetic qualified reviewer two.",
                "method": "Separate blind pair review.",
                "reviewed_at": "2026-01-03T12:00:00Z",
                "predictions_seen_before_initial_labels": False,
                "judgments": _judgments(reviewer_two),
            },
        ],
        "adjudication": {
            "adjudicator_id": "test-adjudicator",
            "method": "Resolve only the recorded synthetic disagreement.",
            "adjudicated_at": "2026-01-04T00:00:00Z",
            "disagreements": [
                {
                    "case_id": disagreement[0],
                    "check_id": disagreement[1],
                    "rationale": "Synthetic adjudication rationale.",
                    "citation": "Synthetic test citation.",
                }
            ],
            "final_judgments": _judgments(final_labels),
        },
        "unblinded_at": "2026-01-05T00:00:00Z",
    }


def _load_answer(
    tmp_path: Path, manifest: EvaluationManifest, cases: CaseSet
) -> AnswerKey:
    path = tmp_path / "answer-key.json"
    _write_json(path, _answer_payload(cases, manifest))
    return load_answer_key(path, manifest, cases)


def _load_blind_predictions(
    tmp_path: Path,
    manifest: EvaluationManifest,
    cases: CaseSet,
    repository: Path,
) -> Predictions:
    generated = generate_blind_predictions(
        manifest,
        cases,
        repository,
        generated_at="2026-01-02T00:00:00Z",
        repository_commit_sha=COMMIT_B,
    )
    path = tmp_path / "predictions.json"
    _write_json(path, generated.payload)
    return load_predictions(path, manifest, cases, repository)


def _copy_committed_manifest(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    path = tmp_path / "manifest.json"
    return path, payload


def _write_synthetic_plan(repository: Path, manifest: EvaluationManifest) -> Path:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    payload["evaluation_id"] = manifest.evaluation_id
    payload["scanner"].update(
        {
            "scanner_path": manifest.scanner_path,
            "scanner_sha256": manifest.scanner_sha256,
            "checks_path": manifest.checks_path,
            "checks_sha256": manifest.checks_sha256,
            "check_ids": list(manifest.check_ids),
            "evaluator_path": manifest.evaluator_path,
            "evaluator_sha256": None,
        }
    )
    payload["coverage_contract"]["official_targeted_pairs_per_check"] = {
        "should_flag": manifest.official_flag_minimum,
        "should_stay_quiet": manifest.official_quiet_minimum,
    }
    payload["coverage_contract"]["synthetic_targeted_pairs_per_check"] = {
        "should_flag": manifest.synthetic_flag_minimum,
        "should_stay_quiet": manifest.synthetic_quiet_minimum,
    }
    payload["coverage_contract"]["required_category_ids"] = list(
        manifest.required_category_ids
    )
    payload["development_source_exclusions"] = [
        {
            "source_id": exclusion.source_id,
            "canonical_url": exclusion.canonical_url,
            "retained_raw_sha256": exclusion.retained_raw_sha256,
            "reason": "Synthetic excluded source for unit testing.",
            "near_duplicate_disposition": NEAR_DUPLICATE_DISPOSITION,
        }
        for exclusion in manifest.exclusions
    ]
    path = repository / "manifest.json"
    _write_json(path, payload)
    return path


def test_committed_not_run_manifest_pins_live_scanner_and_checks() -> None:
    manifest = load_evaluation_manifest(MANIFEST_PATH, ROOT)
    checks = load_checks(CHECKS_PATH)

    assert manifest.payload["status"] == "not_run"
    assert all(
        value is None
        for key, value in manifest.payload["freeze"].items()
        if key != "corpus_status"
    )
    assert manifest.payload["freeze"]["corpus_status"] == "not_frozen"
    assert all(value is None for value in manifest.payload["inputs"].values())
    assert manifest.payload["output"] == {"result_path": None}
    assert manifest.check_ids == tuple(sorted(check.check_id for check in checks))
    assert manifest.scanner_sha256 == _sha256(SCANNER_PATH.read_bytes())
    assert manifest.checks_sha256 == _sha256(CHECKS_PATH.read_bytes())
    assert manifest.evaluator_path == EVALUATOR_PATH.relative_to(ROOT).as_posix()
    coverage = manifest.payload["coverage_contract"]
    assert coverage["pair_universe"] == "full_case_check_cartesian_product"
    assert coverage["target_checks_per_case"] == 1
    assert coverage["multi_target_cases_supported"] is False
    assert coverage["reporting_grains"] == [
        "overall",
        "per_check",
        "official_targeted",
        "synthetic_targeted",
        "official_incidental",
        "synthetic_incidental",
    ]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda payload: payload["scanner"].__setitem__("scanner_sha256", "0" * 64),
            "scanner bytes drifted",
        ),
        (
            lambda payload: payload["freeze"].__setitem__(
                "freeze_id", "premature-freeze"
            ),
            "null execution fields",
        ),
        (
            lambda payload: payload.__setitem__("schema_version", True),
            "expected integer 1",
        ),
        (
            lambda payload: payload["coverage_contract"].__setitem__(
                "multi_target_cases_supported", 0
            ),
            "does not support multi-target",
        ),
    ],
)
def test_manifest_rejects_drift_null_state_and_bool_confusion(
    tmp_path: Path, mutate: Any, message: str
) -> None:
    path, payload = _copy_committed_manifest(tmp_path)
    mutate(payload)
    _write_json(path, payload)

    with pytest.raises(ValueError, match=message):
        load_evaluation_manifest(path, ROOT)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("status", "not_run case_check_pair"),
        ("scanner-module", "unexpected scanner module"),
        ("checks-hash", "check registry bytes drifted"),
        ("check-ids", "check registry coverage drifted"),
        ("evaluator-missing", "evaluator is unavailable"),
        ("inputs", "must have null inputs"),
        ("output", "must remain null"),
        ("reference-labels", "invalid queue labels"),
        ("raw-counts", "invalid raw-count contract"),
        ("category-duplicates", "duplicate values"),
        ("incidental-coverage", "incidental pairs cannot satisfy"),
        ("synthetic-reporting", "synthetic controls must be separate"),
        ("pair-universe", "full Cartesian pair universe"),
        ("target-count", "exactly one target check"),
        ("reporting-grains", "invalid reporting grains"),
        ("exclusions-empty", "expected a non-empty list"),
        ("exclusion-source-duplicate", "duplicate source ID"),
        ("exclusion-url-duplicate", "duplicate canonical URL"),
        ("blockers", "source, review, and custody blockers"),
        ("near-duplicate-policy", "expected the exclusion policy"),
    ],
)
def test_manifest_rejects_additional_invalid_contract_states(  # noqa: C901
    tmp_path: Path, mutation: str, message: str
) -> None:
    path, payload = _copy_committed_manifest(tmp_path)
    if mutation == "status":
        payload["status"] = "completed"
    elif mutation == "scanner-module":
        payload["scanner"]["module"] = "different.scanner"
    elif mutation == "checks-hash":
        payload["scanner"]["checks_sha256"] = "0" * 64
    elif mutation == "check-ids":
        payload["scanner"]["check_ids"].pop()
    elif mutation == "evaluator-missing":
        payload["scanner"]["evaluator_path"] = "missing-evaluator.py"
    elif mutation == "inputs":
        payload["inputs"]["cases_path"] = "cases.json"
    elif mutation == "output":
        payload["output"]["result_path"] = "result.json"
    elif mutation == "reference-labels":
        payload["reference_labels"].reverse()
    elif mutation == "raw-counts":
        payload["raw_count_fields"].reverse()
    elif mutation == "category-duplicates":
        payload["coverage_contract"]["required_category_ids"] = ["same", "same"]
    elif mutation == "incidental-coverage":
        payload["coverage_contract"]["incidental_findings_count_toward_coverage"] = True
    elif mutation == "synthetic-reporting":
        payload["coverage_contract"]["synthetic_controls_reported_separately"] = False
    elif mutation == "pair-universe":
        payload["coverage_contract"]["pair_universe"] = "target_pairs_only"
    elif mutation == "target-count":
        payload["coverage_contract"]["target_checks_per_case"] = 2
    elif mutation == "reporting-grains":
        payload["coverage_contract"]["reporting_grains"].pop()
    elif mutation == "exclusions-empty":
        payload["development_source_exclusions"] = []
    elif mutation == "exclusion-source-duplicate":
        exclusions = payload["development_source_exclusions"]
        exclusions[1]["source_id"] = exclusions[0]["source_id"]
    elif mutation == "exclusion-url-duplicate":
        exclusions = payload["development_source_exclusions"]
        exclusions[1]["canonical_url"] = exclusions[0]["canonical_url"]
    elif mutation == "blockers":
        payload["external_blockers"] = ["Only one blocker remains."]
    else:
        payload["development_source_exclusions"][0]["near_duplicate_disposition"] = (
            "A different policy."
        )
    _write_json(path, payload)

    with pytest.raises(ValueError, match=message):
        load_evaluation_manifest(path, ROOT)


def test_manifest_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    raw = MANIFEST_PATH.read_text(encoding="utf-8")
    path.write_text(
        raw.replace(
            '  "schema_version": 1,',
            '  "schema_version": 1,\n  "schema_version": 1,',
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate JSON key"):
        load_evaluation_manifest(path, ROOT)


def test_manifest_rejects_claim_boundary_with_contradictory_accuracy_claim(
    tmp_path: Path,
) -> None:
    path, payload = _copy_committed_manifest(tmp_path)
    payload["claim_boundary"] += (
        " This evaluation proves statewide scanner accuracy and coverage."
    )
    _write_json(path, payload)

    with pytest.raises(ValueError, match="exact schema-v1 policy"):
        load_evaluation_manifest(path, ROOT)


@pytest.mark.parametrize("excluded_by", ["source_id", "canonical_url", "digest"])
def test_case_set_rejects_every_development_source_binding(
    tmp_path: Path, excluded_by: str
) -> None:
    manifest = _manifest()
    payload = _case_payload()
    case = payload["cases"][0]
    if excluded_by == "source_id":
        case["source"]["source_id"] = "excluded-source"
    elif excluded_by == "canonical_url":
        case["source"]["canonical_url"] = "https://example.invalid/excluded.pdf"
    else:
        case["source"]["document_sha256"] = EXCLUDED_DIGEST
    path = tmp_path / "cases.json"
    _write_json(path, payload)

    with pytest.raises(ValueError, match="development"):
        load_case_set(path, manifest)


@pytest.mark.parametrize(
    "alias",
    [
        "https://EXAMPLE.INVALID/excluded.pdf",
        "https://example.invalid./excluded.pdf",
        "https://example.invalid:443/excluded.pdf",
        "https://example.invalid/excluded.pdf?download=1",
        "https://example.invalid/%65xcluded.pdf",
        "https://example.invalid/%2e/excluded.pdf",
        "https://example.invalid/folder\\excluded.pdf",
        "https://example.invalid//excluded.pdf",
        "https://example.invalid/excluded.pdf/",
        "https://example.invalid/./excluded.pdf",
        "https://example.invalid/../excluded.pdf",
        "https://example.invalid/excludéd.pdf",
    ],
)
def test_case_set_rejects_noncanonical_source_url_aliases(
    tmp_path: Path, alias: str
) -> None:
    payload = _case_payload()
    payload["cases"][0]["source"]["canonical_url"] = alias
    path = tmp_path / "cases.json"
    _write_json(path, payload)

    with pytest.raises(ValueError, match="URL"):
        load_case_set(path, _manifest())


def test_case_set_binds_exact_passage_bytes(tmp_path: Path) -> None:
    payload = _case_payload()
    payload["cases"][0]["passage"] += " Altered after hashing."
    path = tmp_path / "cases.json"
    _write_json(path, payload)

    with pytest.raises(ValueError, match="passage bytes drifted"):
        load_case_set(path, _manifest())


def test_case_set_rejects_source_retrieval_after_corpus_freeze(
    tmp_path: Path,
) -> None:
    payload = _case_payload()
    payload["cases"][0]["source"]["retrieved_on"] = "2026-01-02"
    path = tmp_path / "cases.json"
    _write_json(path, payload)

    with pytest.raises(ValueError, match="retrieval postdates freeze"):
        load_case_set(path, _manifest())


def test_case_set_rejects_duplicate_passage_bytes_across_ids_and_targets(
    tmp_path: Path,
) -> None:
    payload = _case_payload()
    first = payload["cases"][0]
    different_target = payload["cases"][2]
    assert first["case_id"] != different_target["case_id"]
    assert first["target_check_id"] != different_target["target_check_id"]
    different_target["passage"] = first["passage"]
    different_target["passage_sha256"] = first["passage_sha256"]
    path = tmp_path / "cases.json"
    _write_json(path, payload)

    with pytest.raises(ValueError, match="duplicate passages"):
        load_case_set(path, _manifest())


@pytest.mark.parametrize(
    ("conflict", "message"),
    [
        ("source-id-url", "source ID maps to conflicting documents"),
        ("source-id-digest", "source ID maps to conflicting documents"),
        ("canonical-url-source-id", "canonical URL maps to conflicting sources"),
        ("canonical-url-digest", "canonical URL maps to conflicting sources"),
    ],
)
def test_case_set_rejects_inconsistent_official_source_identity(
    tmp_path: Path, conflict: str, message: str
) -> None:
    payload = _case_payload()
    first_source = payload["cases"][0]["source"]
    second_source = payload["cases"][1]["source"]
    if conflict == "source-id-url":
        second_source["source_id"] = first_source["source_id"]
        second_source["document_sha256"] = first_source["document_sha256"]
    elif conflict == "source-id-digest":
        second_source["source_id"] = first_source["source_id"]
        second_source["canonical_url"] = first_source["canonical_url"]
    elif conflict == "canonical-url-source-id":
        second_source["canonical_url"] = first_source["canonical_url"]
        second_source["document_sha256"] = first_source["document_sha256"]
    else:
        second_source["canonical_url"] = first_source["canonical_url"]
    path = tmp_path / "cases.json"
    _write_json(path, payload)

    with pytest.raises(ValueError, match=message):
        load_case_set(path, _manifest())


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("schema-bool", "expected integer 1"),
        ("evaluation-id", "does not match manifest"),
        ("selection-order", "selected before scanner run"),
        ("near-duplicate-review", "near-duplicate review is required"),
        ("empty-cases", "bounded non-empty list"),
        ("duplicate-case-id", "sorted unique case IDs"),
        ("unknown-target", "unknown check"),
        ("selection-role", "candidate_flag or candidate_near_miss"),
        ("synthetic-id", "synthetic ID must be explicit"),
        ("synthetic-document", "cannot claim a document"),
        ("synthetic-retrieval", "synthetic control must be null"),
        ("required-category", "required category coverage is missing"),
    ],
)
def test_case_set_rejects_additional_invalid_contract_states(  # noqa: C901
    tmp_path: Path, mutation: str, message: str
) -> None:
    manifest = _manifest()
    payload = _case_payload()
    first = payload["cases"][0]
    source = first["source"]
    if mutation == "schema-bool":
        payload["schema_version"] = True
    elif mutation == "evaluation-id":
        payload["evaluation_id"] = "different-evaluation"
    elif mutation == "selection-order":
        payload["selection"]["selected_before_scanner_run"] = False
    elif mutation == "near-duplicate-review":
        payload["selection"]["near_duplicate_review_completed"] = False
    elif mutation == "empty-cases":
        payload["cases"] = []
    elif mutation == "duplicate-case-id":
        payload["cases"][1]["case_id"] = first["case_id"]
    elif mutation == "unknown-target":
        first["target_check_id"] = "missing-check"
    elif mutation == "selection-role":
        first["selection_role"] = "unrelated-control"
    elif mutation == "synthetic-id":
        first["stratum"] = "synthetic"
    elif mutation == "synthetic-document":
        first["stratum"] = "synthetic"
        source["source_id"] = "synthetic-test-source"
    elif mutation == "synthetic-retrieval":
        first["stratum"] = "synthetic"
        source["source_id"] = "synthetic-test-source"
        source["canonical_url"] = None
        source["document_sha256"] = None
    else:
        manifest = replace(
            manifest, required_category_ids=("absent-required-category",)
        )
    path = tmp_path / "cases.json"
    _write_json(path, payload)

    with pytest.raises(ValueError, match=message):
        load_case_set(path, manifest)


def test_answer_key_requires_exact_cartesian_pair_coverage(
    tmp_path: Path,
) -> None:
    manifest = _manifest()
    cases = _load_cases(tmp_path, manifest)
    assert len(expected_pair_keys(cases, manifest)) == len(cases.cases) * len(
        manifest.check_ids
    )
    payload = _answer_payload(cases, manifest)
    payload["reviewers"][0]["judgments"].pop()
    path = tmp_path / "answer-key.json"
    _write_json(path, payload)

    with pytest.raises(ValueError, match="exact case/check coverage"):
        load_answer_key(path, manifest, cases)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("schema-bool", "expected integer 1"),
        ("evaluation-id", "does not match manifest"),
        ("freeze-id", "does not match cases"),
        ("cases-binding", "case set drifted"),
        ("checks-binding", "check registry drifted"),
        ("reviewer-count", "exactly two reviewers"),
        ("invalid-label", "invalid reference label"),
        ("duplicate-pair", "duplicate case/check pair"),
        ("disagreements-type", "expected a list"),
        ("disagreement-unknown", "unknown or duplicate pair"),
    ],
)
def test_answer_key_rejects_additional_invalid_contract_states(
    tmp_path: Path, mutation: str, message: str
) -> None:
    manifest = _manifest()
    cases = _load_cases(tmp_path, manifest)
    payload = _answer_payload(cases, manifest)
    if mutation == "schema-bool":
        payload["schema_version"] = True
    elif mutation == "evaluation-id":
        payload["evaluation_id"] = "different-evaluation"
    elif mutation == "freeze-id":
        payload["freeze_id"] = "different-freeze"
    elif mutation == "cases-binding":
        payload["cases_sha256"] = "f" * 64
    elif mutation == "checks-binding":
        payload["checks_sha256"] = "f" * 64
    elif mutation == "reviewer-count":
        payload["reviewers"].pop()
    elif mutation == "invalid-label":
        payload["reviewers"][0]["judgments"][0]["label"] = "legal-conclusion"
    elif mutation == "duplicate-pair":
        payload["reviewers"][0]["judgments"].append(
            dict(payload["reviewers"][0]["judgments"][0])
        )
    elif mutation == "disagreements-type":
        payload["adjudication"]["disagreements"] = None
    else:
        payload["adjudication"]["disagreements"][0]["case_id"] = "missing-case"
    path = tmp_path / "answer-key.json"
    _write_json(path, payload)

    with pytest.raises(ValueError, match=message):
        load_answer_key(path, manifest, cases)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("duplicate-reviewer", "reviewer IDs must be distinct"),
        ("reviewer-adjudicator", "adjudicator ID must be distinct"),
        ("unblind-reviewer", "initial judgments were not blind"),
        ("missing-disagreement", "does not match reviewers"),
        ("changed-agreement", "agreement was changed"),
    ],
)
def test_answer_key_enforces_distinct_blind_review_and_exact_adjudication(
    tmp_path: Path, mutation: str, message: str
) -> None:
    manifest = _manifest()
    cases = _load_cases(tmp_path, manifest)
    payload = _answer_payload(cases, manifest)
    if mutation == "duplicate-reviewer":
        payload["reviewers"][1]["reviewer_id"] = "reviewer-one"
    elif mutation == "reviewer-adjudicator":
        payload["adjudication"]["adjudicator_id"] = "reviewer-one"
    elif mutation == "unblind-reviewer":
        payload["reviewers"][1]["predictions_seen_before_initial_labels"] = True
    elif mutation == "missing-disagreement":
        payload["adjudication"]["disagreements"] = []
    else:
        final = payload["adjudication"]["final_judgments"]
        record = next(
            item
            for item in final
            if item["case_id"] == "official-beta-quiet"
            and item["check_id"] == "alpha-check"
        )
        record["label"] = "should_flag"
    path = tmp_path / "answer-key.json"
    _write_json(path, payload)

    with pytest.raises(ValueError, match=message):
        load_answer_key(path, manifest, cases)


@pytest.mark.parametrize(
    ("field", "timestamp", "message"),
    [
        ("review", "2025-12-31T23:59:59Z", "review predates corpus freeze"),
        ("adjudication", "2026-01-02T00:00:00Z", "adjudication predates review"),
        ("unblind", "2026-01-03T00:00:00Z", "unblinding predates adjudication"),
    ],
)
def test_answer_key_enforces_freeze_review_adjudication_unblind_chronology(
    tmp_path: Path, field: str, timestamp: str, message: str
) -> None:
    manifest = _manifest()
    cases = _load_cases(tmp_path, manifest)
    payload = _answer_payload(cases, manifest)
    if field == "review":
        payload["reviewers"][0]["reviewed_at"] = timestamp
    elif field == "adjudication":
        payload["adjudication"]["adjudicated_at"] = timestamp
    else:
        payload["unblinded_at"] = timestamp
    path = tmp_path / "answer-key.json"
    _write_json(path, payload)

    with pytest.raises(ValueError, match=message):
        load_answer_key(path, manifest, cases)


@pytest.mark.parametrize("field", ["law_as_of", "check_registry_as_of"])
def test_answer_key_rejects_future_reference_dates(tmp_path: Path, field: str) -> None:
    manifest = _manifest()
    cases = _load_cases(tmp_path, manifest)
    payload = _answer_payload(cases, manifest)
    payload[field] = "2026-01-07"
    path = tmp_path / "answer-key.json"
    _write_json(path, payload)

    with pytest.raises(ValueError, match="future source state"):
        load_answer_key(path, manifest, cases, today=date(2026, 1, 6))


@pytest.mark.parametrize("field", ["law_as_of", "check_registry_as_of"])
def test_answer_key_reference_state_cannot_postdate_unblinding(
    tmp_path: Path, field: str
) -> None:
    manifest = _manifest()
    cases = _load_cases(tmp_path, manifest)
    payload = _answer_payload(cases, manifest)
    payload[field] = "2026-01-06"
    path = tmp_path / "answer-key.json"
    _write_json(path, payload)

    with pytest.raises(ValueError, match="source state postdates unblinding"):
        load_answer_key(path, manifest, cases, today=date(2026, 1, 6))


@pytest.mark.parametrize(
    ("case_id", "replacement"),
    [
        ("official-alpha-flag", "reference_abstain"),
        ("official-alpha-quiet", "reference_abstain"),
    ],
)
def test_answer_key_enforces_targeted_official_flag_and_quiet_minima(
    tmp_path: Path, case_id: str, replacement: str
) -> None:
    manifest = _manifest()
    cases = _load_cases(tmp_path, manifest)
    payload = _answer_payload(cases, manifest)
    for reviewer in payload["reviewers"]:
        for judgment in reviewer["judgments"]:
            if judgment["case_id"] == case_id and judgment["check_id"] == "alpha-check":
                judgment["label"] = replacement
    for judgment in payload["adjudication"]["final_judgments"]:
        if judgment["case_id"] == case_id and judgment["check_id"] == "alpha-check":
            judgment["label"] = replacement
    path = tmp_path / "answer-key.json"
    _write_json(path, payload)

    with pytest.raises(ValueError, match="targeted coverage minimum"):
        load_answer_key(path, manifest, cases)


def test_quiet_minimum_requires_preselected_near_miss_role(tmp_path: Path) -> None:
    manifest = _manifest()
    payload = _case_payload()
    quiet_case = next(
        case for case in payload["cases"] if case["case_id"] == "official-alpha-quiet"
    )
    quiet_case["selection_role"] = "candidate_flag"
    cases_path = tmp_path / "cases.json"
    _write_json(cases_path, payload)
    cases = load_case_set(cases_path, manifest)
    answer_path = tmp_path / "answer-key.json"
    _write_json(answer_path, _answer_payload(cases, manifest))

    with pytest.raises(ValueError, match="targeted coverage minimum"):
        load_answer_key(answer_path, manifest, cases)


def test_blind_predictions_record_counts_without_reference_labels(
    tmp_path: Path,
) -> None:
    repository, manifest = _prediction_repository(tmp_path)
    cases = _load_cases(tmp_path, manifest)
    predictions = generate_blind_predictions(
        manifest,
        cases,
        repository,
        generated_at="2026-01-02T00:00:00Z",
        repository_commit_sha=COMMIT_B,
    )

    encoded = json.dumps(predictions.payload)
    assert "reference_label" not in encoded
    assert "should_flag" not in encoded
    assert "should_stay_quiet" not in encoded
    records = {record["case_id"]: record for record in predictions.payload["cases"]}
    assert records["official-alpha-flag"]["finding_counts"] == {
        "alpha-check": 1,
        "beta-check": 0,
    }
    assert records["official-beta-flag"]["finding_counts"] == {
        "alpha-check": 0,
        "beta-check": 2,
    }
    assert records["official-beta-flag"]["observed_check_ids"] == ["beta-check"]
    assert predictions.raw_sha256 is None
    assert predictions.payload["bindings"]["manifest_sha256"] == manifest.raw_sha256
    assert predictions.payload["bindings"]["evaluator_sha256"] == _sha256(
        (repository / "evaluator.py").read_bytes()
    )


def test_prediction_generation_rejects_changed_pinned_checks_with_same_ids(
    tmp_path: Path,
) -> None:
    repository, manifest = _prediction_repository(tmp_path)
    cases = _load_cases(tmp_path, manifest)
    checks_path = repository / manifest.checks_path
    records = json.loads(checks_path.read_text(encoding="utf-8"))
    records[0]["patterns"] = ["different synthetic pattern"]
    checks_path.write_text(
        json.dumps(records, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="check bytes drifted"):
        generate_blind_predictions(
            manifest,
            cases,
            repository,
            generated_at="2026-01-02T00:00:00Z",
            repository_commit_sha=COMMIT_B,
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("count", "observed IDs and finding counts disagree"),
        ("binding", "binding drifted"),
        ("evaluator", "evaluator_sha256: binding drifted"),
        ("abstain", "must report zero"),
    ],
)
def test_prediction_receipt_rejects_tamper_and_machine_abstention(
    tmp_path: Path, mutation: str, message: str
) -> None:
    repository, manifest = _prediction_repository(tmp_path)
    cases = _load_cases(tmp_path, manifest)
    generated = generate_blind_predictions(
        manifest,
        cases,
        repository,
        generated_at="2026-01-02T00:00:00Z",
        repository_commit_sha=COMMIT_B,
    )
    payload = generated.payload
    if mutation == "count":
        payload["cases"][0]["finding_counts"]["alpha-check"] = 0
    elif mutation == "binding":
        payload["bindings"]["cases_sha256"] = "f" * 64
    elif mutation == "evaluator":
        payload["bindings"]["evaluator_sha256"] = "f" * 64
    else:
        payload["machine_abstain"] = 1
    path = tmp_path / "predictions.json"
    _write_json(path, payload)

    with pytest.raises(ValueError, match=message):
        load_predictions(path, manifest, cases, repository)


def _recompute_counts(
    outcomes: list[dict[str, Any]], *, key: str, value: str
) -> dict[str, int]:
    counts: Counter[str] = Counter(
        outcome["raw_cell"] for outcome in outcomes if outcome[key] == value
    )
    return {field: counts[field] for field in RAW_COUNT_FIELDS}


def test_scoring_reports_recomputable_raw_counts_and_retires_corpus(
    tmp_path: Path,
) -> None:
    repository, manifest = _prediction_repository(tmp_path)
    cases = _load_cases(tmp_path, manifest)
    predictions = _load_blind_predictions(tmp_path, manifest, cases, repository)
    answer = _load_answer(tmp_path, manifest, cases)

    result = score_predictions(
        manifest,
        cases,
        answer,
        predictions,
        scored_at="2026-01-06T00:00:00Z",
        repository_commit_sha=COMMIT_C,
    )

    outcomes = result["pair_outcomes"]
    assert len(outcomes) == len(cases.cases) * len(manifest.check_ids)
    assert result["raw_counts_by_partition"]["overall"] == {
        "expected_flag_observed_flag": 2,
        "expected_flag_observed_quiet": 1,
        "expected_quiet_observed_flag": 0,
        "expected_quiet_observed_quiet": 4,
        "reference_abstain": 1,
        "machine_abstain": 0,
    }
    for partition in (
        "official_targeted",
        "synthetic_targeted",
        "official_incidental",
        "synthetic_incidental",
    ):
        assert result["raw_counts_by_partition"][partition] == _recompute_counts(
            outcomes, key="partition", value=partition
        )
    for check_id in manifest.check_ids:
        assert result["raw_counts_by_check"][check_id]["overall"] == _recompute_counts(
            outcomes, key="check_id", value=check_id
        )
        for field in RAW_COUNT_FIELDS:
            assert result["raw_counts_by_check"][check_id]["overall"][field] == sum(
                result["raw_counts_by_check"][check_id][partition][field]
                for partition in (
                    "official_targeted",
                    "synthetic_targeted",
                    "official_incidental",
                    "synthetic_incidental",
                )
            )
    assert result["raw_counts_by_partition"]["official_targeted"] == {
        "expected_flag_observed_flag": 2,
        "expected_flag_observed_quiet": 0,
        "expected_quiet_observed_flag": 0,
        "expected_quiet_observed_quiet": 2,
        "reference_abstain": 0,
        "machine_abstain": 0,
    }
    assert (
        result["raw_counts_by_partition"]["official_incidental"]["reference_abstain"]
        == 1
    )
    assert result["machine_abstain"] == 0
    assert result["corpus_lifecycle"] == {
        "status": "consumed_after_unblinding",
        "reusable_as_held_out_for_future_scanner_versions": False,
    }


def test_scoring_keeps_official_and_synthetic_incidental_pairs_separate(
    tmp_path: Path,
) -> None:
    repository, manifest = _prediction_repository(tmp_path)
    case_payload = _case_payload()
    synthetic = _case_record(
        "synthetic-alpha-flag",
        "alpha-check",
        "Fabricated synthetic passage: trigger alpha.",
    )
    synthetic["stratum"] = "synthetic"
    synthetic["source"] = {
        "source_id": "synthetic-alpha-source",
        "canonical_url": None,
        "document_sha256": None,
        "passage_locator": "fabricated synthetic unit-test passage",
        "retrieved_on": None,
    }
    case_payload["cases"].append(synthetic)
    cases_path = tmp_path / "cases.json"
    _write_json(cases_path, case_payload)
    cases = load_case_set(cases_path, manifest)

    answer_payload = _answer_payload(cases, manifest)
    extra_judgments = [
        {
            "case_id": "synthetic-alpha-flag",
            "check_id": "alpha-check",
            "label": "should_flag",
        },
        {
            "case_id": "synthetic-alpha-flag",
            "check_id": "beta-check",
            "label": "should_stay_quiet",
        },
    ]
    for reviewer in answer_payload["reviewers"]:
        reviewer["judgments"].extend(extra_judgments)
    answer_payload["adjudication"]["final_judgments"].extend(extra_judgments)
    answer_path = tmp_path / "answer-key.json"
    _write_json(answer_path, answer_payload)
    answer = load_answer_key(answer_path, manifest, cases)
    predictions = _load_blind_predictions(tmp_path, manifest, cases, repository)

    result = score_predictions(
        manifest,
        cases,
        answer,
        predictions,
        scored_at="2026-01-06T00:00:00Z",
        repository_commit_sha=COMMIT_C,
    )

    assert sum(result["raw_counts_by_partition"]["synthetic_targeted"].values()) == 1
    assert sum(result["raw_counts_by_partition"]["synthetic_incidental"].values()) == 1
    assert sum(result["raw_counts_by_partition"]["official_incidental"].values()) == 4


def test_scoring_requires_predictions_frozen_before_unblinding(
    tmp_path: Path,
) -> None:
    repository, manifest = _prediction_repository(tmp_path)
    cases = _load_cases(tmp_path, manifest)
    predictions = _load_blind_predictions(tmp_path, manifest, cases, repository)
    answer = _load_answer(tmp_path, manifest, cases)

    with pytest.raises(ValueError, match="before answer-key unblinding"):
        score_predictions(
            manifest,
            cases,
            answer,
            replace(predictions, generated_at=answer.unblinded_at),
            scored_at="2026-01-06T00:00:00Z",
            repository_commit_sha=COMMIT_C,
        )


def test_result_loader_recomputes_and_rejects_hand_edited_counts(
    tmp_path: Path,
) -> None:
    repository, manifest = _prediction_repository(tmp_path)
    cases = _load_cases(tmp_path, manifest)
    predictions = _load_blind_predictions(tmp_path, manifest, cases, repository)
    answer = _load_answer(tmp_path, manifest, cases)
    result = score_predictions(
        manifest,
        cases,
        answer,
        predictions,
        scored_at="2026-01-06T00:00:00Z",
        repository_commit_sha=COMMIT_C,
    )
    valid_path = tmp_path / "valid-result.json"
    _write_json(valid_path, result)

    receipt = load_result(valid_path, manifest, cases, answer, predictions)
    assert receipt.raw_sha256 == _sha256(valid_path.read_bytes())

    tampered = json.loads(json.dumps(result))
    tampered["raw_counts_by_partition"]["overall"]["expected_flag_observed_flag"] += 1
    tampered_path = tmp_path / "tampered-result.json"
    _write_json(tampered_path, tampered)
    with pytest.raises(ValueError, match="does not match recomputed outcomes"):
        load_result(tampered_path, manifest, cases, answer, predictions)


def test_exclusive_result_writer_never_overwrites(tmp_path: Path) -> None:
    path = tmp_path / "result.json"
    payload = {"status": "synthetic-test-only", "raw_count": 1}

    receipt_sha256 = write_json_exclusive(path, payload)
    assert json.loads(path.read_text(encoding="utf-8")) == payload
    original = path.read_bytes()
    assert receipt_sha256 == _sha256(original)

    with pytest.raises(ValueError, match="refusing to overwrite"):
        write_json_exclusive(path, {"status": "replacement"})
    assert path.read_bytes() == original


def test_evaluation_cli_validates_plan_and_returns_two_for_invalid_plan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository, manifest = _prediction_repository(tmp_path)
    _write_synthetic_plan(repository, manifest)

    assert (
        evaluation_cli_main(
            [
                "--root",
                str(repository),
                "validate-plan",
                "--manifest",
                "manifest.json",
            ]
        )
        == 0
    )
    summary = json.loads(capsys.readouterr().out)
    assert summary == {
        "active_check_count": 2,
        "evaluation_id": manifest.evaluation_id,
        "execution_status": "not_run",
        "result_present": False,
        "supports_accuracy_claim": False,
    }

    assert (
        evaluation_cli_main(
            [
                "--root",
                str(repository),
                "validate-plan",
                "--manifest",
                "missing.json",
            ]
        )
        == 2
    )
    assert "invalid input or output" in capsys.readouterr().err


def test_evaluation_cli_predict_is_blind_and_refuses_overwrite(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository, manifest = _prediction_repository(tmp_path)
    _write_synthetic_plan(repository, manifest)
    _write_json(repository / "cases.json", _case_payload())
    (repository / "answer-key.json").write_text("not valid JSON", encoding="utf-8")
    argv = [
        "--root",
        str(repository),
        "predict",
        "--manifest",
        "manifest.json",
        "--cases",
        "cases.json",
        "--output",
        "predictions.json",
        "--generated-at",
        "2026-01-02T00:00:00Z",
        "--repository-commit-sha",
        COMMIT_B,
    ]

    assert evaluation_cli_main(argv) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["reference_labels_loaded"] is False
    receipt = json.loads((repository / "predictions.json").read_text(encoding="utf-8"))
    encoded = json.dumps(receipt)
    assert "reference_label" not in encoded
    assert "should_flag" not in encoded
    assert "should_stay_quiet" not in encoded

    with pytest.raises(SystemExit) as error:
        evaluation_cli_main([*argv, "--answer-key", "answer-key.json"])
    assert error.value.code == 2
    capsys.readouterr()

    assert evaluation_cli_main(argv) == 2
    assert "refusing to overwrite" in capsys.readouterr().err


def test_evaluation_cli_score_requires_frozen_inputs_and_refuses_overwrite(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository, manifest = _prediction_repository(tmp_path)
    plan_path = _write_synthetic_plan(repository, manifest)
    cases_path = repository / "cases.json"
    _write_json(cases_path, _case_payload())
    loaded_manifest = load_evaluation_manifest(plan_path, repository)
    cases = load_case_set(cases_path, loaded_manifest)
    _write_json(
        repository / "answer-key.json",
        _answer_payload(cases, loaded_manifest),
    )
    assert (
        evaluation_cli_main(
            [
                "--root",
                str(repository),
                "predict",
                "--manifest",
                "manifest.json",
                "--cases",
                "cases.json",
                "--output",
                "predictions.json",
                "--generated-at",
                "2026-01-02T00:00:00Z",
                "--repository-commit-sha",
                COMMIT_B,
            ]
        )
        == 0
    )
    capsys.readouterr()
    score_argv = [
        "--root",
        str(repository),
        "score",
        "--manifest",
        "manifest.json",
        "--cases",
        "cases.json",
        "--answer-key",
        "answer-key.json",
        "--predictions",
        "predictions.json",
        "--output",
        "result.json",
        "--scored-at",
        "2026-01-06T00:00:00Z",
        "--repository-commit-sha",
        COMMIT_C,
    ]

    missing_predictions = list(score_argv)
    missing_predictions[missing_predictions.index("predictions.json")] = "missing.json"
    assert evaluation_cli_main(missing_predictions) == 2
    assert "invalid input or output" in capsys.readouterr().err

    missing_answer = list(score_argv)
    missing_answer[missing_answer.index("answer-key.json")] = "missing.json"
    assert evaluation_cli_main(missing_answer) == 2
    assert "invalid input or output" in capsys.readouterr().err

    assert evaluation_cli_main(score_argv) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "completed_bounded_evaluation"
    assert summary["supports_accuracy_claim"] is False
    result = json.loads((repository / "result.json").read_text(encoding="utf-8"))
    assert result["corpus_lifecycle"]["status"] == "consumed_after_unblinding"

    assert (
        evaluation_cli_main(
            [
                "--root",
                str(repository),
                "validate-result",
                "--manifest",
                "manifest.json",
                "--cases",
                "cases.json",
                "--answer-key",
                "answer-key.json",
                "--predictions",
                "predictions.json",
                "--result",
                "result.json",
            ]
        )
        == 0
    )
    validation = json.loads(capsys.readouterr().out)
    assert validation["status"] == "completed_bounded_evaluation"
    assert validation["supports_accuracy_claim"] is False
    assert validation["result_sha256"] == _sha256(
        (repository / "result.json").read_bytes()
    )

    assert evaluation_cli_main(score_argv) == 2
    assert "refusing to overwrite" in capsys.readouterr().err


def test_evaluation_cli_returns_two_for_malformed_case_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository, manifest = _prediction_repository(tmp_path)
    _write_synthetic_plan(repository, manifest)
    (repository / "cases.json").write_text("{", encoding="utf-8")

    assert (
        evaluation_cli_main(
            [
                "--root",
                str(repository),
                "predict",
                "--manifest",
                "manifest.json",
                "--cases",
                "cases.json",
                "--output",
                "predictions.json",
                "--generated-at",
                "2026-01-02T00:00:00Z",
                "--repository-commit-sha",
                COMMIT_B,
            ]
        )
        == 2
    )
    assert "invalid UTF-8 JSON" in capsys.readouterr().err
