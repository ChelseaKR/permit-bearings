#!/usr/bin/env python3
"""Build the browser demo's deterministic, offline-safe data bundle.

The JSON files remain canonical. ``data/demo-data.js`` is a generated
JavaScript assignment so ``index.html`` can be opened directly from disk
without browser-blocked ``file://`` fetches.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from permit_pathways.explanations import load_explanations  # noqa: E402
from permit_pathways.harness.watch import (  # noqa: E402
    load_sources,
    normalized_digest,
)
from permit_pathways.readiness import (  # noqa: E402
    SOURCE_MAX_AGE_DAYS,
    load_and_evaluate_readiness,
    load_readiness_remedies,
)
from permit_pathways.screening import load_rules  # noqa: E402

OUTPUT = ROOT / "data" / "demo-data.js"
RULE_MANIFEST_OUTPUT = ROOT / "data" / "rules" / "index.json"
READINESS_WORKFLOW = Path(
    "data/readiness/workflows/woodland-preapproved-detached-adu.json"
)
READINESS_SAMPLE = Path(
    "data/readiness/samples/woodland-preapproved-adu.json"
)
READINESS_REMEDIES = Path(
    "data/readiness/remedies/woodland-preapproved-detached-adu.json"
)
READINESS_EVIDENCE_OUTPUT = ROOT / (
    "data/readiness/generated/woodland-preapproved-adu-evidence.json"
)
INPUTS = {
    "golden": Path("data/golden/example.json"),
    "sources": Path("data/sources.json"),
    "checks": Path("data/conformance/checks.json"),
    "registry": Path("data/jurisdictions/registry.json"),
    "letters": Path("data/jurisdictions/hcd-letters.json"),
    "scans": Path("data/conformance/results/index.json"),
    "plain_language": Path("data/explanations/plain-language.json"),
}


def discover_rule_files(root: Path = ROOT) -> list[Path]:
    """Return every canonical rule file, excluding generated metadata."""

    return sorted(
        path
        for path in (root / "data" / "rules").glob("*.json")
        if path.name != "index.json"
    )


def rule_manifest(root: Path = ROOT) -> dict[str, object]:
    files = discover_rule_files(root)
    if not files:
        raise ValueError("data/rules: no canonical rule files found")
    return {
        "schema_version": 1,
        "files": [path.name for path in files],
    }


def encoded_rule_manifest(root: Path = ROOT) -> str:
    return json.dumps(
        rule_manifest(root),
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    ) + "\n"


def aggregate_rule_records(
    root: Path = ROOT,
) -> tuple[list[object], dict[str, str]]:
    """Load every discovered rule file and return records plus digests."""

    aggregate: list[object] = []
    digests: dict[str, str] = {}
    for rule_path in discover_rule_files(root):
        raw = rule_path.read_bytes()
        records = json.loads(raw)
        if not isinstance(records, list):
            raise ValueError(f"{rule_path}: expected a list of rules")
        aggregate.extend(records)
        relative_path = rule_path.relative_to(root)
        digests[relative_path.as_posix()] = hashlib.sha256(raw).hexdigest()
    return aggregate, digests


def build_readiness_payload(
    root: Path = ROOT,
) -> tuple[dict[str, object], dict[str, str]]:
    """Build one deterministic, source-bound synthetic readiness sample."""

    workflow_path = root / READINESS_WORKFLOW
    sample_path = root / READINESS_SAMPLE
    remedies_path = root / READINESS_REMEDIES
    sample_payload = json.loads(sample_path.read_text(encoding="utf-8"))
    try:
        canonical_evaluated_on = sample_payload["packet"]["evaluated_on"]
        evaluation_date = date.fromisoformat(canonical_evaluated_on)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(
            f"{READINESS_SAMPLE}: invalid packet.evaluated_on"
        ) from error
    workflow, packet, result = load_and_evaluate_readiness(
        workflow_path,
        sample_path,
        root / "data" / "sources.json",
        today=evaluation_date,
    )
    if not packet.synthetic:
        raise ValueError(
            f"{READINESS_SAMPLE}: public demo packets must be synthetic"
        )
    remedies = load_readiness_remedies(
        remedies_path,
        workflow,
        today=evaluation_date,
    )
    manifest = result.to_manifest(workflow, packet)
    source_review_due_on = min(
        date.fromisoformat(binding.source_checked_on)
        + timedelta(days=SOURCE_MAX_AGE_DAYS)
        for binding in workflow.source_bindings
    ).isoformat()
    if source_review_due_on != result.source_review_due_on:
        raise AssertionError("readiness source-review deadline drifted")
    payload: dict[str, object] = {
        "workflow": asdict(workflow),
        "packet": asdict(packet),
        "result": asdict(result),
        "counts": result.counts(),
        "source_review_due_on": source_review_due_on,
        "remedies": asdict(remedies),
        "evidence_manifest": manifest,
        "ai_trace": {
            "role": (
                "AI proposed the checklist-to-requirement mapping, parcel-field "
                "bindings, and plain-language missing-item actions from the "
                "linked official sources."
            ),
            "runtime_model_call": False,
            "applicant_data_sent_to_model": False,
            "input_source_ids": [
                binding.source_id for binding in workflow.source_bindings
            ],
            "mapping_version": workflow.mapping_provenance.version,
            "mapping_review_status": (
                workflow.mapping_provenance.review_status
            ),
            "mapping_provider": workflow.mapping_provenance.provider,
            "mapping_model": workflow.mapping_provenance.model,
            "mapping_run_record_status": (
                workflow.mapping_provenance.run_record_status
            ),
            "output_workflow_fingerprint": workflow.fingerprint(),
            "output_remedy_version": remedies.version,
            "remedy_review_status": remedies.review.status,
            "remedy_reviewer": remedies.review.reviewer,
        },
    }
    digests = {
        relative.as_posix(): hashlib.sha256(
            (root / relative).read_bytes()
        ).hexdigest()
        for relative in (
            READINESS_WORKFLOW,
            READINESS_SAMPLE,
            READINESS_REMEDIES,
        )
    }
    return payload, digests


def encoded_readiness_evidence(root: Path = ROOT) -> str:
    payload, _ = build_readiness_payload(root)
    return json.dumps(
        payload["evidence_manifest"],
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    ) + "\n"


def _validate_local_source_copies(root: Path) -> None:
    """Ensure preserved evidence bytes still match the source registry."""

    sources = load_sources(root / "data" / "sources.json")
    resolved_root = root.resolve()
    for source in sources.values():
        if source.watch and source.local_copy is None:
            raise ValueError(
                f"{source.source_id}: watched source requires local_copy"
            )
        if source.local_copy is None:
            continue
        local_path = (root / source.local_copy).resolve()
        if resolved_root not in local_path.parents:
            raise ValueError(
                f"{source.source_id}.local_copy: path leaves repository"
            )
        try:
            content = local_path.read_bytes()
        except OSError as error:
            raise ValueError(
                f"{source.source_id}.local_copy: unavailable"
            ) from error
        digest = normalized_digest(content, source.normalize)
        if digest != source.sha256:
            raise ValueError(
                f"{source.source_id}.local_copy: digest does not match registry"
            )


def build_bundle(root: Path = ROOT) -> str:
    """Return the generated bundle text from canonical JSON inputs."""

    rules = load_rules(root / "data" / "rules")
    sources = load_sources(root / "data" / "sources.json")
    known_sources = set(sources)
    for rule in rules:
        unknown = sorted(set(rule.source_dependencies) - known_sources)
        if unknown:
            raise ValueError(
                f"{rule.rule_id}: unknown source dependencies: "
                + ", ".join(unknown)
            )
        dependency_urls = {
            sources[source_id].url for source_id in rule.source_dependencies
        }
        if rule.citation.url not in dependency_urls:
            raise ValueError(
                f"{rule.rule_id}: citation URL is not an explicit dependency"
            )
        cited_source = next(
            sources[source_id]
            for source_id in rule.source_dependencies
            if sources[source_id].url == rule.citation.url
        )
        if rule.citation.verified_on is not None:
            if (
                cited_source.fetched_on is None
                or cited_source.sha256 is None
                or cited_source.local_copy is None
            ):
                raise ValueError(
                    f"{rule.rule_id}: dated citation has no preserved "
                    "source evidence"
                )
            if cited_source.fetched_on > rule.citation.verified_on:
                raise ValueError(
                    f"{rule.rule_id}: citation verification predates "
                    "the preserved source evidence"
                )
    _validate_local_source_copies(root)
    load_explanations(
        root / "data" / "explanations" / "plain-language.json",
        rules,
    )

    payload: dict[str, object] = {}
    digests: dict[str, str] = {}
    aggregate_rules, rule_digests = aggregate_rule_records(root)
    digests.update(rule_digests)
    payload["rules"] = aggregate_rules
    payload["rule_manifest"] = rule_manifest(root)
    readiness, readiness_digests = build_readiness_payload(root)
    payload["readiness"] = readiness
    digests.update(readiness_digests)

    for key, relative_path in INPUTS.items():
        raw = (root / relative_path).read_bytes()
        payload[key] = json.loads(raw)
        digests[relative_path.as_posix()] = hashlib.sha256(raw).hexdigest()

    payload["_meta"] = {
        "format_version": 1,
        "generated_from": digests,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return (
        "/* Generated by scripts/build_demo_bundle.py; do not edit by hand. */\n"
        f"globalThis.PERMIT_PATHWAYS_DEMO_DATA={encoded};\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the committed bundle differs from the canonical JSON",
    )
    args = parser.parse_args()
    expected = build_bundle()
    expected_manifest = encoded_rule_manifest()
    expected_readiness_evidence = encoded_readiness_evidence()

    if args.check:
        bundle_current = (
            OUTPUT.exists()
            and OUTPUT.read_text(encoding="utf-8") == expected
        )
        manifest_current = (
            RULE_MANIFEST_OUTPUT.exists()
            and RULE_MANIFEST_OUTPUT.read_text(encoding="utf-8")
            == expected_manifest
        )
        readiness_current = (
            READINESS_EVIDENCE_OUTPUT.exists()
            and READINESS_EVIDENCE_OUTPUT.read_text(encoding="utf-8")
            == expected_readiness_evidence
        )
        if (
            not bundle_current
            or not manifest_current
            or not readiness_current
        ):
            print(
                "generated demo data is out of date; "
                "run python3 scripts/build_demo_bundle.py"
            )
            return 1
        print(
            "demo bundle, rule manifest, and readiness evidence are in sync"
        )
        return 0

    RULE_MANIFEST_OUTPUT.write_text(expected_manifest, encoding="utf-8")
    READINESS_EVIDENCE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    READINESS_EVIDENCE_OUTPUT.write_text(
        expected_readiness_evidence,
        encoding="utf-8",
    )
    OUTPUT.write_text(expected, encoding="utf-8")
    print(f"wrote {RULE_MANIFEST_OUTPUT.relative_to(ROOT)}")
    print(f"wrote {READINESS_EVIDENCE_OUTPUT.relative_to(ROOT)}")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
