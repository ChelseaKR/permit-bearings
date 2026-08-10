"""Strict portable registry for bounded readiness and journey workflows.

The registry selects repository-relative artifacts; it does not make a
workflow active, approved, applicant-ready, or jurisdiction-accepted. One
entry is selected as the browser default while build and CLI code can validate
additional bounded prototype entries without path constants.
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .program_availability import (
    GENERIC_PROTOTYPE_AVAILABILITY_POLICY,
    WOODLAND_AVAILABILITY_POLICY,
)
from .program_availability import (
    WORKFLOW_ID as WOODLAND_WORKFLOW_ID,
)

SCHEMA_VERSION = 1
WORKFLOW_STATUSES = ("prototype",)
MAX_REGISTRY_BYTES = 256 * 1024
MAX_ARTIFACT_BYTES = 4 * 1024 * 1024

_STABLE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PORTABLE_FILENAME = re.compile(r"^[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?\.json$")
_WINDOWS_RESERVED_STEMS = {
    "aux",
    "con",
    "nul",
    "prn",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}
_AVAILABILITY_POLICIES = {
    GENERIC_PROTOTYPE_AVAILABILITY_POLICY,
    WOODLAND_AVAILABILITY_POLICY,
}
_TOP_LEVEL_KEYS = {"schema_version", "browser_default_workflow_id", "workflows"}
_ENTRY_KEYS = {
    "workflow_id",
    "packet_id",
    "journey_id",
    "program_id",
    "jurisdiction",
    "status",
    "availability_policy",
    "artifacts",
}
_ARTIFACT_KEYS = {
    "readiness_workflow",
    "readiness_packet",
    "readiness_remedies",
    "readiness_evidence",
    "journey",
    "journey_evidence",
    "program_availability",
}
_INPUT_LAYOUT = {
    "readiness_workflow": "data/readiness/workflows",
    "readiness_packet": "data/readiness/samples",
    "readiness_remedies": "data/readiness/remedies",
    "journey": "data/journeys",
    "program_availability": "data/availability",
}
_OUTPUT_LAYOUT = {
    "readiness_evidence": "data/readiness/generated",
    "journey_evidence": "data/journeys/generated",
}


@dataclass(frozen=True)
class FingerprintedArtifact:
    """One canonical JSON input pinned by its raw repository bytes."""

    path: str
    sha256: str

    def resolve(self, root: Path) -> Path:
        return _inside_root(root, self.path, require_file=True)


@dataclass(frozen=True)
class GeneratedArtifact:
    """One generated JSON destination owned by the bundle builder."""

    path: str

    def resolve(self, root: Path) -> Path:
        return _inside_root(root, self.path, require_file=False)


@dataclass(frozen=True)
class WorkflowArtifacts:
    readiness_workflow: FingerprintedArtifact
    readiness_packet: FingerprintedArtifact
    readiness_remedies: FingerprintedArtifact
    readiness_evidence: GeneratedArtifact
    journey: FingerprintedArtifact
    journey_evidence: GeneratedArtifact
    program_availability: FingerprintedArtifact

    def inputs(self) -> tuple[FingerprintedArtifact, ...]:
        return (
            self.readiness_workflow,
            self.readiness_packet,
            self.readiness_remedies,
            self.journey,
            self.program_availability,
        )

    def outputs(self) -> tuple[GeneratedArtifact, ...]:
        return (self.readiness_evidence, self.journey_evidence)


@dataclass(frozen=True)
class WorkflowRegistryEntry:
    workflow_id: str
    packet_id: str
    journey_id: str
    program_id: str
    jurisdiction: str
    status: str
    availability_policy: str
    artifacts: WorkflowArtifacts


@dataclass(frozen=True)
class WorkflowRegistry:
    browser_default_workflow_id: str
    workflows: tuple[WorkflowRegistryEntry, ...]

    def select(self, workflow_id: str | None = None) -> WorkflowRegistryEntry:
        """Return exactly one entry, defaulting to the browser selection."""

        selected_id = (
            self.browser_default_workflow_id if workflow_id is None else workflow_id
        )
        matches = [item for item in self.workflows if item.workflow_id == selected_id]
        if len(matches) != 1:
            raise ValueError(f"workflow registry: unknown workflow ID {selected_id!r}")
        return matches[0]


def _exact_keys(record: dict[str, Any], expected: set[str], field: str) -> None:
    unknown = sorted(set(record) - expected)
    missing = sorted(expected - set(record))
    if unknown:
        raise ValueError(f"{field}: unknown fields: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"{field}: missing fields: {', '.join(missing)}")


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{field}: expected non-blank trimmed text")
    return value


class _DuplicateKeyError(ValueError):
    """Raised before an ambiguous JSON object can overwrite an earlier key."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    record: dict[str, Any] = {}
    for key, value in pairs:
        if key in record:
            raise _DuplicateKeyError(key)
        record[key] = value
    return record


def _reject_constant(value: str) -> Any:
    raise ValueError(f"non-finite JSON constant {value!r} is not allowed")


def _strict_json(raw: bytes, field: str) -> Any:
    try:
        text = raw.decode("utf-8")
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except UnicodeDecodeError as error:
        raise ValueError(f"{field}: expected UTF-8 JSON") from error
    except _DuplicateKeyError as error:
        raise ValueError(f"{field}: duplicate JSON object key {error}") from error
    except (json.JSONDecodeError, RecursionError, ValueError) as error:
        raise ValueError(f"{field}: invalid JSON") from error


def _stable_id(value: Any, field: str) -> str:
    identifier = _required_text(value, field)
    if not _STABLE_ID.fullmatch(identifier):
        raise ValueError(f"{field}: expected a stable ID")
    return identifier


def _portable_json_path(value: Any, field: str, parent: str) -> str:
    raw = _required_text(value, field)
    if "\\" in raw:
        raise ValueError(f"{field}: backslashes are not portable")
    path = PurePosixPath(raw)
    name = path.name
    if (
        path.is_absolute()
        or path.as_posix() != raw
        or path.parent.as_posix() != parent
        or path.suffix != ".json"
        or any(part in {"", ".", ".."} for part in path.parts)
        or not raw.isascii()
        or len(raw.encode("ascii")) > 240
        or len(name.encode("ascii")) > 100
        or not _PORTABLE_FILENAME.fullmatch(name)
        or ".." in name
        or name.split(".", 1)[0] in _WINDOWS_RESERVED_STEMS
    ):
        raise ValueError(
            f"{field}: expected one repository-relative JSON path in {parent}"
        )
    return raw


def _real_root(root: Path) -> Path:
    try:
        resolved = root.resolve(strict=True)
        metadata = resolved.stat()
    except OSError as error:
        raise ValueError(f"{root}: repository root is unavailable") from error
    if not stat.S_ISDIR(metadata.st_mode):
        raise ValueError(f"{root}: repository root is not a directory")
    return resolved


def _reject_linked_components(root: Path, relative: PurePosixPath) -> Path:
    candidate = root
    for part in relative.parts:
        candidate = candidate / part
        try:
            metadata = candidate.lstat()
        except FileNotFoundError:
            continue
        except OSError as error:
            raise ValueError(
                f"{relative.as_posix()}: path could not be inspected"
            ) from error
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"{relative.as_posix()}: symbolic links are not allowed")
    return candidate


def _inside_root(root: Path, relative: str, *, require_file: bool) -> Path:
    resolved_root = _real_root(root)
    portable = PurePosixPath(relative)
    candidate = _reject_linked_components(resolved_root, portable)
    resolved_candidate = candidate.resolve(strict=False)
    if resolved_candidate != candidate or (
        resolved_candidate != resolved_root
        and resolved_root not in resolved_candidate.parents
    ):
        raise ValueError(f"{relative}: path leaves repository root")
    try:
        metadata = candidate.lstat()
    except FileNotFoundError:
        metadata = None
    except OSError as error:
        raise ValueError(f"{relative}: path could not be inspected") from error
    if require_file:
        if metadata is None or not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"{relative}: registered input is unavailable")
    elif metadata is not None and not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"{relative}: generated path is not a regular file")
    if metadata is not None and metadata.st_nlink != 1:
        raise ValueError(f"{relative}: linked files are not allowed")
    return candidate


def _bounded_bytes(path: Path, field: str, *, maximum: int) -> bytes:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise ValueError(f"{field}: file is unavailable") from error
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise ValueError(f"{field}: expected one unlinked regular file")
    if metadata.st_size > maximum:
        raise ValueError(f"{field}: file exceeds {maximum} bytes")
    try:
        with path.open("rb") as stream:
            raw = stream.read(maximum + 1)
    except OSError as error:
        raise ValueError(f"{field}: file could not be read") from error
    if len(raw) > maximum:
        raise ValueError(f"{field}: file exceeds {maximum} bytes")
    return raw


def _fingerprinted_artifact(
    value: Any,
    field: str,
    parent: str,
    root: Path,
) -> FingerprintedArtifact:
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected an object")
    _exact_keys(value, {"path", "sha256"}, field)
    path = _portable_json_path(value["path"], f"{field}.path", parent)
    digest = _required_text(value["sha256"], f"{field}.sha256")
    if not _SHA256.fullmatch(digest):
        raise ValueError(f"{field}.sha256: expected lowercase SHA-256")
    artifact_path = _inside_root(root, path, require_file=True)
    actual = hashlib.sha256(
        _bounded_bytes(artifact_path, field, maximum=MAX_ARTIFACT_BYTES)
    )
    if actual.hexdigest() != digest:
        raise ValueError(f"{field}.sha256: registered fingerprint does not match")
    return FingerprintedArtifact(path=path, sha256=digest)


def _generated_artifact(
    value: Any,
    field: str,
    parent: str,
    root: Path,
) -> GeneratedArtifact:
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected an object")
    _exact_keys(value, {"path"}, field)
    path = _portable_json_path(value["path"], f"{field}.path", parent)
    _inside_root(root, path, require_file=False)
    return GeneratedArtifact(path=path)


def _artifacts(value: Any, field: str, root: Path) -> WorkflowArtifacts:
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected an object")
    _exact_keys(value, _ARTIFACT_KEYS, field)
    inputs = {
        key: _fingerprinted_artifact(value[key], f"{field}.{key}", parent, root)
        for key, parent in _INPUT_LAYOUT.items()
    }
    outputs = {
        key: _generated_artifact(value[key], f"{field}.{key}", parent, root)
        for key, parent in _OUTPUT_LAYOUT.items()
    }
    return WorkflowArtifacts(
        readiness_workflow=inputs["readiness_workflow"],
        readiness_packet=inputs["readiness_packet"],
        readiness_remedies=inputs["readiness_remedies"],
        readiness_evidence=outputs["readiness_evidence"],
        journey=inputs["journey"],
        journey_evidence=outputs["journey_evidence"],
        program_availability=inputs["program_availability"],
    )


def _entry(value: Any, index: int, root: Path) -> WorkflowRegistryEntry:
    field = f"workflow registry.workflows[{index}]"
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected an object")
    _exact_keys(value, _ENTRY_KEYS, field)
    status = _required_text(value["status"], f"{field}.status")
    if status not in WORKFLOW_STATUSES:
        raise ValueError(f"{field}.status: unsupported value {status!r}")
    workflow_id = _stable_id(value["workflow_id"], f"{field}.workflow_id")
    availability_policy = _required_text(
        value["availability_policy"],
        f"{field}.availability_policy",
    )
    if availability_policy not in _AVAILABILITY_POLICIES:
        raise ValueError(
            f"{field}.availability_policy: unsupported value {availability_policy!r}"
        )
    return WorkflowRegistryEntry(
        workflow_id=workflow_id,
        packet_id=_stable_id(value["packet_id"], f"{field}.packet_id"),
        journey_id=_stable_id(value["journey_id"], f"{field}.journey_id"),
        program_id=_stable_id(value["program_id"], f"{field}.program_id"),
        jurisdiction=_stable_id(value["jurisdiction"], f"{field}.jurisdiction"),
        status=status,
        availability_policy=availability_policy,
        artifacts=_artifacts(value["artifacts"], f"{field}.artifacts", root),
    )


def _reject_duplicates(registry: WorkflowRegistry) -> None:
    identifiers = {
        "workflow ID": [entry.workflow_id for entry in registry.workflows],
        "packet ID": [entry.packet_id for entry in registry.workflows],
        "journey ID": [entry.journey_id for entry in registry.workflows],
        "program ID": [entry.program_id for entry in registry.workflows],
        "input path": [
            artifact.path
            for entry in registry.workflows
            for artifact in entry.artifacts.inputs()
        ],
        "generated path": [
            artifact.path
            for entry in registry.workflows
            for artifact in entry.artifacts.outputs()
        ],
    }
    for label, values in identifiers.items():
        if len(values) != len(set(values)):
            raise ValueError(f"workflow registry: duplicate {label}")
        if len(values) != len({value.casefold() for value in values}):
            raise ValueError(f"workflow registry: case-colliding {label}")
    input_paths = set(identifiers["input path"])
    output_paths = set(identifiers["generated path"])
    if input_paths & output_paths:
        raise ValueError("workflow registry: input and generated paths overlap")


def _validate_policy_bindings(registry: WorkflowRegistry) -> None:
    for entry in registry.workflows:
        if (
            entry.workflow_id == WOODLAND_WORKFLOW_ID
            and entry.availability_policy != WOODLAND_AVAILABILITY_POLICY
        ):
            raise ValueError(
                f"{entry.workflow_id}: the Woodland workflow requires its "
                "exact source policy"
            )
        if (
            entry.availability_policy == WOODLAND_AVAILABILITY_POLICY
            and entry.workflow_id != WOODLAND_WORKFLOW_ID
        ):
            raise ValueError(
                f"{entry.workflow_id}: the Woodland source policy cannot bind "
                "another workflow"
            )


def _inventory_paths(root: Path, parent: str) -> set[str]:
    resolved_root = _real_root(root)
    directory = _reject_linked_components(resolved_root, PurePosixPath(parent))
    try:
        metadata = directory.lstat()
    except OSError as error:
        raise ValueError(
            f"{parent}: registered artifact directory is unavailable"
        ) from error
    if not stat.S_ISDIR(metadata.st_mode):
        raise ValueError(f"{parent}: registered artifact directory is unavailable")
    paths: set[str] = set()
    for path in directory.iterdir():
        if not path.name.casefold().endswith(".json"):
            continue
        relative = path.relative_to(resolved_root).as_posix()
        if (
            not path.name.isascii()
            or len(path.name.encode("ascii")) > 100
            or not _PORTABLE_FILENAME.fullmatch(path.name)
            or ".." in path.name
            or path.name.split(".", 1)[0] in _WINDOWS_RESERVED_STEMS
        ):
            raise ValueError(f"{relative}: unsafe canonical artifact filename")
        try:
            item_metadata = path.lstat()
        except OSError as error:
            raise ValueError(
                f"{relative}: canonical artifact is unavailable"
            ) from error
        if not stat.S_ISREG(item_metadata.st_mode) or item_metadata.st_nlink != 1:
            raise ValueError(f"{relative}: expected one unlinked regular JSON file")
        paths.add(relative)
    return paths


def _validate_inventory(registry: WorkflowRegistry, root: Path) -> None:
    for key, parent in _INPUT_LAYOUT.items():
        expected = {getattr(entry.artifacts, key).path for entry in registry.workflows}
        observed = _inventory_paths(root, parent)
        if observed != expected:
            extras = sorted(observed - expected)
            missing = sorted(expected - observed)
            detail = []
            if extras:
                detail.append("orphan files: " + ", ".join(extras))
            if missing:
                detail.append("missing files: " + ", ".join(missing))
            raise ValueError(f"workflow registry {parent}: {'; '.join(detail)}")
    for key, parent in _OUTPUT_LAYOUT.items():
        expected = {getattr(entry.artifacts, key).path for entry in registry.workflows}
        extras = sorted(_inventory_paths(root, parent) - expected)
        if extras:
            raise ValueError(
                f"workflow registry {parent}: orphan files: {', '.join(extras)}"
            )


def _artifact_record(
    root: Path,
    artifact: FingerprintedArtifact,
    container: str | None,
) -> dict[str, Any]:
    try:
        artifact_path = artifact.resolve(root)
        payload = _strict_json(
            _bounded_bytes(
                artifact_path,
                artifact.path,
                maximum=MAX_ARTIFACT_BYTES,
            ),
            artifact.path,
        )
    except ValueError as error:
        raise ValueError(
            f"{artifact.path}: registered JSON could not be loaded"
        ) from error
    if not isinstance(payload, dict):
        raise ValueError(f"{artifact.path}: expected an object")
    record: Any = payload if container is None else payload.get(container)
    if not isinstance(record, dict):
        raise ValueError(f"{artifact.path}: missing {container or 'record'} object")
    return record


def _expect_declared(value: Any, expected: str, field: str) -> None:
    if value != expected:
        raise ValueError(f"{field}: does not match the workflow registry")


def _validate_declared_ids(registry: WorkflowRegistry, root: Path) -> None:
    for entry in registry.workflows:
        workflow = _artifact_record(
            root,
            entry.artifacts.readiness_workflow,
            "workflow",
        )
        packet = _artifact_record(root, entry.artifacts.readiness_packet, "packet")
        remedies = _artifact_record(
            root,
            entry.artifacts.readiness_remedies,
            None,
        )
        journey = _artifact_record(root, entry.artifacts.journey, "journey")
        availability = _artifact_record(
            root,
            entry.artifacts.program_availability,
            "availability",
        )
        expected = (
            (workflow.get("workflow_id"), entry.workflow_id, "workflow.workflow_id"),
            (workflow.get("jurisdiction"), entry.jurisdiction, "workflow.jurisdiction"),
            (packet.get("workflow_id"), entry.workflow_id, "packet.workflow_id"),
            (packet.get("packet_id"), entry.packet_id, "packet.packet_id"),
            (packet.get("jurisdiction"), entry.jurisdiction, "packet.jurisdiction"),
            (remedies.get("workflow_id"), entry.workflow_id, "remedies.workflow_id"),
            (journey.get("journey_id"), entry.journey_id, "journey.journey_id"),
            (
                journey.get("readiness_workflow_id"),
                entry.workflow_id,
                "journey.readiness_workflow_id",
            ),
            (
                journey.get("readiness_packet_id"),
                entry.packet_id,
                "journey.readiness_packet_id",
            ),
            (
                availability.get("workflow_id"),
                entry.workflow_id,
                "availability.workflow_id",
            ),
            (
                availability.get("program_id"),
                entry.program_id,
                "availability.program_id",
            ),
            (
                availability.get("jurisdiction"),
                entry.jurisdiction,
                "availability.jurisdiction",
            ),
        )
        for value, declared, field in expected:
            _expect_declared(value, declared, f"{entry.workflow_id}: {field}")


def load_workflow_registry(
    path: Path,
    *,
    root: Path,
    validate_inventory: bool = True,
) -> WorkflowRegistry:
    """Load, pin, and inventory every registered workflow artifact."""

    resolved_root = _real_root(root)
    try:
        specified = path if path.is_absolute() else Path.cwd() / path
        resolved_path = specified.resolve(strict=False)
        if resolved_path != specified.absolute() or (
            resolved_path != resolved_root
            and resolved_root not in resolved_path.parents
        ):
            raise ValueError("path leaves repository root or uses a symbolic link")
        raw = _bounded_bytes(
            resolved_path,
            str(path),
            maximum=MAX_REGISTRY_BYTES,
        )
        payload = _strict_json(raw, str(path))
    except ValueError as error:
        raise ValueError(f"{path}: workflow registry could not be loaded") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected an object")
    _exact_keys(payload, _TOP_LEVEL_KEYS, "workflow registry")
    if (
        type(payload["schema_version"]) is not int
        or payload["schema_version"] != SCHEMA_VERSION
    ):
        raise ValueError(f"workflow registry.schema_version: expected {SCHEMA_VERSION}")
    values = payload["workflows"]
    if not isinstance(values, list) or not values:
        raise ValueError("workflow registry.workflows: expected a non-empty list")
    registry = WorkflowRegistry(
        browser_default_workflow_id=_stable_id(
            payload["browser_default_workflow_id"],
            "workflow registry.browser_default_workflow_id",
        ),
        workflows=tuple(
            _entry(value, index, root) for index, value in enumerate(values)
        ),
    )
    _reject_duplicates(registry)
    registry.select()
    _validate_declared_ids(registry, root)
    _validate_policy_bindings(registry)
    if validate_inventory:
        _validate_inventory(registry, root)
    return registry


def registry_digest(path: Path) -> str:
    """Return the raw SHA-256 used by the browser bundle's input receipt."""

    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise ValueError(f"{path}: workflow registry could not be read") from error
