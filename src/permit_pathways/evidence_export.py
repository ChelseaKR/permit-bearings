"""Portable public/synthetic evidence export and restore verification.

The package is deliberately a bounded data handoff.  It contains only files
explicitly named in a versioned profile, uses raw archive-member digests, and
restores inertly into a new directory.  It does not adopt a source snapshot,
publish guidance, create a review decision, or handle applicant data.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import re
import shutil
import stat
import subprocess  # nosec B404
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import date
from errno import EEXIST
from pathlib import Path
from typing import Any

from .dates import resolve_today
from .harness.watch import normalized_digest

# The subprocess boundary below invokes Git only through fixed argument vectors
# with shell execution disabled; the executable is resolved with ``shutil.which``.

PROFILE_PATHS = {
    1: Path("data/export/public-synthetic-evidence-v1.json"),
    2: Path("data/export/public-synthetic-evidence-v2.json"),
}
DEFAULT_PROFILE_VERSION = 2
DEFAULT_PROFILE_PATH = PROFILE_PATHS[DEFAULT_PROFILE_VERSION]
MANIFEST_FILENAME = "MANIFEST.json"
PACKAGE_SCHEMA_VERSION = DEFAULT_PROFILE_VERSION
PROFILE_SCHEMA_VERSION = DEFAULT_PROFILE_VERSION
SUPPORTED_SCHEMA_VERSIONS = frozenset(PROFILE_PATHS)
MEMBER_SHA256_BASIS = "raw_archive_member_bytes"

_FIXED_ZIP_DATETIME = (1980, 1, 1, 0, 0, 0)
_FIXED_ZIP_MODE = stat.S_IFREG | 0o644
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9-]*$")
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_SOURCE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$")
_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_PATH_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_MAX_MEMBERS = 128
_MAX_MEMBER_BYTES = 16 * 1024 * 1024
_MAX_TOTAL_BYTES = 32 * 1024 * 1024
_MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
_MAX_MANIFEST_BYTES = 1 * 1024 * 1024
_CHUNK_BYTES = 1024 * 1024
_MAX_PATH_BYTES = 240
_MAX_COMPONENT_BYTES = 100
_MAX_PATH_DEPTH = 12
_MAX_STATE_ASSERTIONS = 64
_WINDOWS_RESERVED_COMPONENTS = {
    "aux",
    "clock$",
    "con",
    "nul",
    "prn",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}
_ROLES = frozenset(
    {
        "availability_record",
        "conformance_checks",
        "conformance_development_fixture",
        "conformance_result",
        "conformance_results",
        "content_review_ledger",
        "derived_browser_bundle",
        "derived_coverage_index",
        "export_profile",
        "flagship_gate",
        "golden_fixtures",
        "hcd_letter_snapshot",
        "journey_definition",
        "journey_evidence",
        "jurisdiction_registry",
        "license",
        "manual_evidence_ledger",
        "participant_ledger",
        "plain_language_drafts",
        "provenance",
        "public_source_copy",
        "public_source_dataset",
        "public_source_index",
        "public_transit_source",
        "readiness_evidence",
        "readiness_packet",
        "readiness_remedies",
        "readiness_workflow",
        "rule_index",
        "rule_records",
        "rule_verification_ledger",
        "source_change_rehearsal_ledger",
        "source_registry",
        "source_state_receipt",
        "third_party_notices",
        "workflow_registry",
    }
)

_PROFILE_KEYS = {
    "schema_version",
    "package",
    "scope",
    "entries",
    "public_state_assertions",
}
_PROFILE_PACKAGE_KEYS = {"archive_root", "package_id"}
_PROFILE_SCOPE_KEYS = {
    "classification",
    "claim_boundary",
    "exclusions",
    "known_absences",
}
_MANIFEST_KEYS = {
    "schema_version",
    "package",
    "freeze",
    "scope",
    "profile",
    "files",
    "tree_fingerprint",
    "member_sha256_basis",
    "referenced_official_sources_without_retained_copy",
    "exclusions",
    "known_absences",
    "public_state_assertions",
}
_MANIFEST_PACKAGE_KEYS = {"archive_root", "package_id"}
_MANIFEST_FREEZE_KEYS = {"freeze_id", "frozen_on", "repository_commit_sha"}
_MANIFEST_SCOPE_KEYS = {"classification", "claim_boundary"}
_MANIFEST_PROFILE_KEYS = {"path", "sha256"}
_MANIFEST_FILE_KEYS = {"path", "role", "sha256", "bytes"}
_MANIFEST_SOURCE_REFERENCE_KEYS = {"source_id", "label", "url"}
_STATE_ASSERTION_KEYS = {"path", "pointer", "equals"}
_SELF_PROFILE_ENTRY_KEYS = {"path", "role", "raw_sha256", "self_reference"}
_ORDINARY_PROFILE_ENTRY_KEYS = {"path", "role", "raw_sha256"}
_WORKFLOW_ARTIFACT_ROLES = {
    "journey": "journey_definition",
    "journey_evidence": "journey_evidence",
    "program_availability": "availability_record",
    "readiness_evidence": "readiness_evidence",
    "readiness_packet": "readiness_packet",
    "readiness_remedies": "readiness_remedies",
    "readiness_workflow": "readiness_workflow",
}


@dataclass(frozen=True)
class ProfileEntry:
    """One explicitly allowed file and its expected raw-byte digest."""

    path: str
    role: str
    raw_sha256: str | None
    self_reference: bool = False


@dataclass(frozen=True)
class StateAssertion:
    """A public/synthetic state that must remain true for this profile."""

    path: str
    pointer: str
    equals: str | int | float | bool | None


@dataclass(frozen=True)
class ExportProfile:
    """Validated export profile data."""

    package_id: str
    archive_root: str
    classification: tuple[str, ...]
    claim_boundary: str
    exclusions: tuple[str, ...]
    known_absences: tuple[str, ...]
    entries: tuple[ProfileEntry, ...]
    state_assertions: tuple[StateAssertion, ...]
    profile_path: str
    schema_version: int = DEFAULT_PROFILE_VERSION


@dataclass(frozen=True)
class _ManifestFile:
    path: str
    role: str
    sha256: str
    byte_count: int


@dataclass(frozen=True)
class _Manifest:
    """Parsed archive manifest, retained internally after strict validation."""

    payload: dict[str, Any]
    package_id: str
    archive_root: str
    freeze_id: str
    frozen_on: str
    repository_commit_sha: str
    profile_path: str
    profile_sha256: str
    files: tuple[_ManifestFile, ...]
    schema_version: int


def _require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected an object")
    return value


def _require_exact_keys(value: dict[str, Any], expected: set[str], field: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{field}: invalid fields")


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field}: expected exact non-blank text")
    return value


def _require_exact_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field}: expected exact non-blank text")
    return value


def _require_identifier(value: Any, field: str) -> str:
    identifier = _require_text(value, field)
    if not _IDENTIFIER.fullmatch(identifier):
        raise ValueError(f"{field}: invalid stable identifier")
    return identifier


def _require_role(value: Any, field: str) -> str:
    role = _require_text(value, field)
    if role not in _ROLES:
        raise ValueError(f"{field}: invalid artifact role")
    return role


def _require_sha256(value: Any, field: str) -> str:
    digest = _require_text(value, field)
    if not _SHA256.fullmatch(digest):
        raise ValueError(f"{field}: expected a SHA-256 digest")
    return digest


def _require_commit_sha(value: Any, field: str) -> str:
    commit_sha = _require_exact_text(value, field)
    if not _COMMIT_SHA.fullmatch(commit_sha):
        raise ValueError(f"{field}: expected a full lowercase commit SHA")
    return commit_sha


def _safe_relative_path(value: Any, field: str) -> str:
    path = _require_exact_text(value, field)
    if not path.isascii() or len(path.encode("ascii")) > _MAX_PATH_BYTES:
        raise ValueError(f"{field}: path must be short ASCII text")
    if path.startswith("/") or "\\" in path or "\x00" in path or "//" in path:
        raise ValueError(f"{field}: absolute or unsafe path")
    parts = path.split("/")
    if len(parts) > _MAX_PATH_DEPTH or any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"{field}: traversal or normalized path is not allowed")
    for part in parts:
        if (
            len(part.encode("ascii")) > _MAX_COMPONENT_BYTES
            or not _PATH_COMPONENT.fullmatch(part)
            or part.endswith((".", " "))
            or ":" in part
        ):
            raise ValueError(f"{field}: non-canonical path component")
        windows_base = part.split(".", 1)[0].casefold()
        if windows_base in _WINDOWS_RESERVED_COMPONENTS:
            raise ValueError(f"{field}: Windows-reserved path component")
    return path


def _require_string_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field}: expected a non-empty list")
    items = tuple(
        _require_text(item, f"{field}[{index}]") for index, item in enumerate(value)
    )
    if len(items) != len(set(items)):
        raise ValueError(f"{field}: duplicate values are not allowed")
    return items


def _require_iso_date(value: Any, field: str) -> str:
    text = _require_text(value, field)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as error:
        raise ValueError(f"{field}: expected an ISO calendar date") from error
    if parsed.isoformat() != text or parsed < date(1980, 1, 1):
        raise ValueError(f"{field}: expected an ISO date on or after 1980-01-01")
    return text


def _require_frozen_on(value: Any, field: str, *, today: date) -> str:
    frozen_on = _require_iso_date(value, field)
    if date.fromisoformat(frozen_on) > today:
        raise ValueError(f"{field}: future dates are not allowed")
    return frozen_on


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _manifest_json(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _tree_fingerprint(files: tuple[_ManifestFile, ...]) -> str:
    payload = [
        {
            "bytes": item.byte_count,
            "path": item.path,
            "role": item.role,
            "sha256": item.sha256,
        }
        for item in files
    ]
    return _sha256_bytes(_canonical_json(payload))


def _parse_profile_entry(
    value: Any,
    field: str,
    *,
    profile_path: str,
) -> ProfileEntry:
    entry = _require_object(value, field)
    path = _safe_relative_path(entry.get("path"), f"{field}.path")
    role = _require_role(entry.get("role"), f"{field}.role")
    if set(entry) == _ORDINARY_PROFILE_ENTRY_KEYS:
        return ProfileEntry(
            path=path,
            role=role,
            raw_sha256=_require_sha256(entry.get("raw_sha256"), f"{field}.raw_sha256"),
        )
    if set(entry) != _SELF_PROFILE_ENTRY_KEYS:
        raise ValueError(f"{field}: invalid fields")
    if (
        entry.get("self_reference") is not True
        or entry.get("raw_sha256") is not None
        or path != profile_path
        or role != "export_profile"
    ):
        raise ValueError(f"{field}: invalid export-profile self reference")
    return ProfileEntry(path=path, role=role, raw_sha256=None, self_reference=True)


def _scalar(value: Any, field: str) -> str | int | float | bool | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"{field}: expected a scalar JSON value")


def _parse_state_assertion(value: Any, field: str) -> StateAssertion:
    assertion = _require_object(value, field)
    _require_exact_keys(assertion, _STATE_ASSERTION_KEYS, field)
    path = _safe_relative_path(assertion.get("path"), f"{field}.path")
    if not path.startswith("data/validation/"):
        raise ValueError(
            f"{field}.path: only validation ledgers can carry state assertions"
        )
    pointer = _require_text(assertion.get("pointer"), f"{field}.pointer")
    if not pointer.startswith("/") or pointer.endswith("/"):
        raise ValueError(f"{field}.pointer: expected a non-root JSON pointer")
    return StateAssertion(
        path=path,
        pointer=pointer,
        equals=_scalar(assertion.get("equals"), f"{field}.equals"),
    )


def _require_source_registry_entry(
    entries: tuple[ProfileEntry, ...], profile_path: str
) -> None:
    source_entry = next(
        (entry for entry in entries if entry.path == "data/sources.json"), None
    )
    if source_entry is None or source_entry.role != "source_registry":
        raise ValueError(
            f"{profile_path}.entries: data/sources.json must be the source registry"
        )


def _require_workflow_registry_entry(
    entries: tuple[ProfileEntry, ...], profile_path: str
) -> None:
    workflow_entry = next(
        (entry for entry in entries if entry.path == "data/workflows/registry.json"),
        None,
    )
    if workflow_entry is None or workflow_entry.role != "workflow_registry":
        raise ValueError(
            f"{profile_path}.entries: data/workflows/registry.json must be the "
            "workflow registry"
        )


def _profile_schema_version(profile_path: str) -> int:
    matches = [
        version
        for version, canonical_path in PROFILE_PATHS.items()
        if canonical_path.as_posix() == profile_path
    ]
    if len(matches) != 1:
        raise ValueError(
            f"{profile_path}: expected a canonical versioned export profile path"
        )
    return matches[0]


def _validate_profile_registry_membership(
    entries: tuple[ProfileEntry, ...],
    profile_path: str,
    schema_version: int,
) -> None:
    if schema_version == 1:
        if any(entry.role == "workflow_registry" for entry in entries):
            raise ValueError(
                f"{profile_path}.entries: schema v1 cannot include a workflow "
                "registry; use the schema-v2 profile"
            )
        return
    _require_workflow_registry_entry(entries, profile_path)


def _parse_profile(
    payload: Any,
    profile_path: str,
) -> ExportProfile:
    profile = _require_object(payload, profile_path)
    _require_exact_keys(profile, _PROFILE_KEYS, profile_path)
    expected_schema_version = _profile_schema_version(profile_path)
    if (
        type(profile.get("schema_version")) is not int
        or profile.get("schema_version") != expected_schema_version
    ):
        raise ValueError(
            f"{profile_path}.schema_version: expected {expected_schema_version}"
        )

    package = _require_object(profile.get("package"), f"{profile_path}.package")
    _require_exact_keys(package, _PROFILE_PACKAGE_KEYS, f"{profile_path}.package")
    package_id = _require_identifier(package.get("package_id"), "package.package_id")
    archive_root = _require_identifier(
        package.get("archive_root"), "package.archive_root"
    )

    scope = _require_object(profile.get("scope"), f"{profile_path}.scope")
    _require_exact_keys(scope, _PROFILE_SCOPE_KEYS, f"{profile_path}.scope")
    classification = _require_string_list(
        scope.get("classification"), "scope.classification"
    )
    if classification != ("public", "synthetic"):
        raise ValueError("scope.classification: expected public and synthetic")

    entries_raw = profile.get("entries")
    if (
        not isinstance(entries_raw, list)
        or not entries_raw
        or len(entries_raw) > _MAX_MEMBERS - 1
    ):
        raise ValueError(f"{profile_path}.entries: expected a non-empty list")
    entries = tuple(
        _parse_profile_entry(value, f"entries[{index}]", profile_path=profile_path)
        for index, value in enumerate(entries_raw)
    )
    paths = tuple(entry.path for entry in entries)
    if (
        paths != tuple(sorted(paths))
        or len(paths) != len(set(paths))
        or len({path.casefold() for path in paths}) != len(paths)
    ):
        raise ValueError(f"{profile_path}.entries: expected sorted unique paths")
    if any(
        not (entry.path.startswith("data/") or entry.path.startswith("corpus/"))
        and entry.path not in {"LICENSE", "PROVENANCE.md", "THIRD_PARTY_NOTICES.md"}
        for entry in entries
    ):
        raise ValueError(
            f"{profile_path}.entries: path is outside the public allowlist"
        )
    if sum(entry.self_reference for entry in entries) != 1:
        raise ValueError(
            f"{profile_path}.entries: expected one self-referential profile"
        )
    _require_source_registry_entry(entries, profile_path)
    _validate_profile_registry_membership(
        entries,
        profile_path,
        expected_schema_version,
    )

    assertions_raw = profile.get("public_state_assertions")
    if (
        not isinstance(assertions_raw, list)
        or not assertions_raw
        or len(assertions_raw) > _MAX_STATE_ASSERTIONS
    ):
        raise ValueError(
            f"{profile_path}.public_state_assertions: expected a non-empty list"
        )
    assertions = tuple(
        _parse_state_assertion(value, f"public_state_assertions[{index}]")
        for index, value in enumerate(assertions_raw)
    )
    assertion_keys = tuple((item.path, item.pointer) for item in assertions)
    if len(assertion_keys) != len(set(assertion_keys)):
        raise ValueError("public_state_assertions: duplicate path/pointer")
    if not {item.path for item in assertions} <= set(paths):
        raise ValueError("public_state_assertions: path is not exported")

    return ExportProfile(
        package_id=package_id,
        archive_root=archive_root,
        classification=classification,
        claim_boundary=_require_text(
            scope.get("claim_boundary"), "scope.claim_boundary"
        ),
        exclusions=_require_string_list(scope.get("exclusions"), "scope.exclusions"),
        known_absences=_require_string_list(
            scope.get("known_absences"), "scope.known_absences"
        ),
        entries=entries,
        state_assertions=assertions,
        profile_path=profile_path,
        schema_version=expected_schema_version,
    )


def _root_directory(root: Path) -> Path:
    if root.is_symlink():
        raise ValueError(f"{root}: expected a real repository directory")
    resolved = root.resolve()
    if not resolved.is_dir():
        raise ValueError(f"{root}: expected a real repository directory")
    return resolved


def _profile_file(
    root: Path,
    profile_path: Path | None,
    *,
    profile_version: int | None = None,
) -> tuple[Path, str]:
    if profile_path is not None and profile_version is not None:
        raise ValueError("select either profile_path or profile_version, not both")
    if profile_path is None:
        selected_version = profile_version
        if selected_version is None:
            selected_version = next(
                (
                    version
                    for version in sorted(PROFILE_PATHS, reverse=True)
                    if (root / PROFILE_PATHS[version]).exists()
                    or (root / PROFILE_PATHS[version]).is_symlink()
                ),
                DEFAULT_PROFILE_VERSION,
            )
        if (
            type(selected_version) is not int
            or selected_version not in SUPPORTED_SCHEMA_VERSIONS
        ):
            raise ValueError("profile_version: expected 1 or 2")
        selected_path = PROFILE_PATHS[selected_version]
        relative = selected_path.as_posix()
        return root / selected_path, relative
    if profile_path.is_absolute():
        candidate = profile_path.resolve()
        try:
            relative = candidate.relative_to(root).as_posix()
        except ValueError as error:
            raise ValueError(
                "profile path must be inside the repository root"
            ) from error
        return candidate, _safe_relative_path(relative, "profile path")
    relative = _safe_relative_path(profile_path.as_posix(), "profile path")
    return root / Path(*relative.split("/")), relative


def _regular_file(root: Path, relative: str) -> Path:
    path = root
    for part in relative.split("/"):
        path = path / part
        if path.is_symlink():
            raise ValueError(f"{relative}: symbolic links are not allowed")
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"{relative}: expected a readable regular file") from error
    if not resolved.is_relative_to(root) or not path.is_file():
        raise ValueError(f"{relative}: expected a regular file inside the repository")
    return path


def _read_regular_file_bytes(root: Path, relative: str, *, maximum: int) -> bytes:
    path = _regular_file(root, relative)
    try:
        if path.stat().st_size > maximum:
            raise ValueError(f"{relative}: file exceeds the size limit")
        chunks: list[bytes] = []
        total = 0
        with path.open("rb") as stream:
            while chunk := stream.read(_CHUNK_BYTES):
                total += len(chunk)
                if total > maximum:
                    raise ValueError(f"{relative}: file exceeds the size limit")
                chunks.append(chunk)
    except OSError as error:
        raise ValueError(f"{relative}: expected a readable regular file") from error
    return b"".join(chunks)


class _DuplicateJsonKey(ValueError):
    """Raised by the JSON object-pairs hook before a duplicate is overwritten."""


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKey(key)
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"unsupported JSON constant {value!r}")


def _read_json_bytes(value: bytes, field: str) -> Any:
    try:
        return json.loads(
            value.decode("utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except _DuplicateJsonKey as error:
        raise ValueError(f"{field}: duplicate JSON object key {error}") from error
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError(f"{field}: invalid UTF-8 JSON") from error


def _validate_local_source_copy(
    record: dict[str, Any],
    source_id: str,
    copy_path: str,
    exported_paths: set[str],
    payloads: dict[str, bytes] | None,
) -> None:
    if copy_path not in exported_paths:
        raise ValueError(
            f"{source_id}.local_copy: referenced official source is not exported"
        )
    if payloads is None:
        return
    if copy_path not in payloads:
        raise ValueError(f"{source_id}.local_copy: source bytes are unavailable")
    expected_digest = _require_exact_text(record.get("sha256"), f"{source_id}.sha256")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
        raise ValueError(f"{source_id}.sha256: invalid normalized SHA-256")
    normalize = record.get("normalize")
    if normalize not in {None, "html-text"}:
        raise ValueError(f"{source_id}.normalize: unsupported normalization")
    if normalized_digest(payloads[copy_path], normalize) != expected_digest:
        raise ValueError(
            f"{source_id}.local_copy: normalized source digest does not match "
            "data/sources.json"
        )


def _source_references_without_copies(
    value: Any,
    exported_paths: set[str],
    payloads: dict[str, bytes] | None = None,
) -> tuple[dict[str, str], ...]:
    registry = _require_object(value, "data/sources.json")
    references: list[dict[str, str]] = []
    for url, raw_record in registry.items():
        source_url = _require_text(url, "data/sources.json URL")
        record = _require_object(raw_record, f"data/sources.json[{source_url!r}]")
        source_id = _require_text(record.get("source_id"), "source_id")
        if not _SOURCE_ID.fullmatch(source_id):
            raise ValueError("data/sources.json.source_id: invalid stable identifier")
        label = _require_text(record.get("label"), f"{source_id}.label")
        local_copy = record.get("local_copy")
        if local_copy is None:
            references.append(
                {"source_id": source_id, "label": label, "url": source_url}
            )
            continue
        copy_path = _safe_relative_path(local_copy, f"{source_id}.local_copy")
        _validate_local_source_copy(
            record,
            source_id,
            copy_path,
            exported_paths,
            payloads,
        )
    if len({reference["source_id"] for reference in references}) != len(references):
        raise ValueError("data/sources.json: duplicate source IDs without local copies")
    return tuple(sorted(references, key=lambda reference: reference["source_id"]))


def _pointer_value(value: Any, pointer: str) -> Any:
    current = value
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if token not in current:
                raise ValueError(f"{pointer}: missing object field {token!r}")
            current = current[token]
            continue
        if isinstance(current, list) and token.isdecimal():
            index = int(token)
            if index < len(current):
                current = current[index]
                continue
        raise ValueError(f"{pointer}: cannot resolve JSON pointer")
    return current


def _validate_state_assertions(
    profile: ExportProfile,
    payloads: dict[str, bytes],
) -> None:
    parsed: dict[str, Any] = {}
    for assertion in profile.state_assertions:
        if assertion.path not in parsed:
            parsed[assertion.path] = _read_json_bytes(
                payloads[assertion.path], assertion.path
            )
        actual = _pointer_value(parsed[assertion.path], assertion.pointer)
        if type(actual) is not type(assertion.equals) or actual != assertion.equals:
            raise ValueError(
                f"{assertion.path}{assertion.pointer}: public/synthetic state drifted"
            )


def _entry_payloads(root: Path, profile: ExportProfile) -> dict[str, bytes]:
    payloads: dict[str, bytes] = {}
    total = 0
    for entry in profile.entries:
        content = _read_regular_file_bytes(
            root,
            entry.path,
            maximum=_MAX_MEMBER_BYTES,
        )
        total += len(content)
        if total > _MAX_TOTAL_BYTES:
            raise ValueError("export profile: total file size exceeds the limit")
        actual = _sha256_bytes(content)
        if entry.raw_sha256 is not None and actual != entry.raw_sha256:
            raise ValueError(f"{entry.path}: raw SHA-256 does not match the profile")
        payloads[entry.path] = content
    return payloads


def _validate_exported_workflow_artifact(
    artifact: Any,
    *,
    artifact_name: str,
    artifact_field: str,
    required_role: str,
    exported: dict[str, ProfileEntry],
    payloads: dict[str, bytes],
) -> None:
    record = _require_object(artifact, artifact_field)
    generated = artifact_name in {"journey_evidence", "readiness_evidence"}
    _require_exact_keys(
        record,
        {"path"} if generated else {"path", "sha256"},
        artifact_field,
    )
    path = _safe_relative_path(record.get("path"), f"{artifact_field}.path")
    exported_entry = exported.get(path)
    if exported_entry is None or exported_entry.role != required_role:
        raise ValueError(
            f"{artifact_field}.path: referenced workflow artifact is not "
            "exported with its required role"
        )
    if generated:
        return
    expected_digest = _require_text(record.get("sha256"), f"{artifact_field}.sha256")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
        raise ValueError(f"{artifact_field}.sha256: invalid SHA-256")
    if _sha256_bytes(payloads[path]) != f"sha256:{expected_digest}":
        raise ValueError(
            f"{artifact_field}.sha256: registry fingerprint does not match "
            "exported bytes"
        )


def _validate_workflow_registry_closure(
    profile: ExportProfile,
    payloads: dict[str, bytes],
) -> None:
    """Require a registry-aware profile to carry every selected artifact.

    This is an export-membership check, not a workflow approval or a substitute
    for the canonical workflow-registry loader replayed during build/restore.
    """

    registry_entries = tuple(
        entry for entry in profile.entries if entry.role == "workflow_registry"
    )
    if not registry_entries:
        return
    if profile.schema_version == 1:
        raise ValueError("schema v1 cannot include a workflow registry")
    if len(registry_entries) != 1:
        raise ValueError("export profile: expected exactly one workflow registry")
    registry_entry = registry_entries[0]
    registry = _require_object(
        _read_json_bytes(payloads[registry_entry.path], registry_entry.path),
        registry_entry.path,
    )
    workflows = registry.get("workflows")
    if not isinstance(workflows, list) or not workflows:
        raise ValueError(f"{registry_entry.path}.workflows: expected a non-empty list")

    exported = {entry.path: entry for entry in profile.entries}
    for workflow_index, raw_workflow in enumerate(workflows):
        workflow_field = f"{registry_entry.path}.workflows[{workflow_index}]"
        workflow = _require_object(raw_workflow, workflow_field)
        artifacts_field = f"{workflow_field}.artifacts"
        artifacts = _require_object(workflow.get("artifacts"), artifacts_field)
        # A packet-only workflow registers no journey artifacts; a journey
        # workflow must register both. This mirrors the registry loader.
        journey_keys = {"journey", "journey_evidence"}
        core_keys = set(_WORKFLOW_ARTIFACT_ROLES) - journey_keys
        journey_present = journey_keys & set(artifacts)
        if journey_present and journey_present != journey_keys:
            raise ValueError(f"{artifacts_field}: invalid fields")
        _require_exact_keys(
            artifacts,
            core_keys | journey_present,
            artifacts_field,
        )
        for artifact_name in sorted(core_keys | journey_present):
            required_role = _WORKFLOW_ARTIFACT_ROLES[artifact_name]
            _validate_exported_workflow_artifact(
                artifacts.get(artifact_name),
                artifact_name=artifact_name,
                artifact_field=f"{artifacts_field}.{artifact_name}",
                required_role=required_role,
                exported=exported,
                payloads=payloads,
            )


def _git_head(root: Path) -> str:
    git = shutil.which("git")
    if git is None:
        raise ValueError("repository: Git is required to bind an export commit")
    try:
        completed = subprocess.run(  # noqa: S603  # nosec B603
            [git, "-C", str(root), "rev-parse", "HEAD"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError as error:
        raise ValueError(
            "repository: Git is required to bind an export commit"
        ) from error
    if completed.returncode != 0:
        raise ValueError("repository: Git HEAD is required to build an export")
    return _require_commit_sha(
        completed.stdout.decode("ascii", "strict").strip(),
        "repository Git HEAD",
    )


def _verify_profile_matches_git_head(
    root: Path,
    profile: ExportProfile,
    payloads: dict[str, bytes],
    *,
    repository_commit_sha: str | None,
) -> str:
    head = _git_head(root)
    git = shutil.which("git")
    if git is None:
        raise ValueError("repository: Git is required to bind an export commit")
    if repository_commit_sha is not None:
        requested = _require_commit_sha(
            repository_commit_sha,
            "repository_commit_sha",
        )
        if requested != head:
            raise ValueError("repository_commit_sha: does not match Git HEAD")
    for entry in profile.entries:
        completed = subprocess.run(  # noqa: S603  # nosec B603
            [git, "-C", str(root), "show", f"{head}:{entry.path}"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if completed.returncode != 0:
            raise ValueError(
                f"{entry.path}: export profile files must be tracked by Git HEAD"
            )
        if completed.stdout != payloads[entry.path]:
            raise ValueError(f"{entry.path}: differs from the bound Git HEAD")
    return head


def load_export_profile(
    root: Path,
    profile_path: Path | None = None,
    *,
    profile_version: int | None = None,
) -> ExportProfile:
    """Load a pinned, public/synthetic-only export profile from ``root``."""

    repository = _root_directory(root)
    _, relative = _profile_file(
        repository,
        profile_path,
        profile_version=profile_version,
    )
    raw = _read_regular_file_bytes(
        repository,
        relative,
        maximum=_MAX_MANIFEST_BYTES,
    )
    profile = _parse_profile(_read_json_bytes(raw, relative), relative)
    payloads = _entry_payloads(repository, profile)
    _validate_workflow_registry_closure(profile, payloads)
    _source_references_without_copies(
        _read_json_bytes(payloads["data/sources.json"], "data/sources.json"),
        set(payloads),
        payloads,
    )
    _validate_state_assertions(profile, payloads)
    return profile


def _manifest_payload(
    profile: ExportProfile,
    freeze_id: str,
    frozen_on: str,
    repository_commit_sha: str,
    payloads: dict[str, bytes],
) -> dict[str, Any]:
    files = tuple(
        _ManifestFile(
            path=entry.path,
            role=entry.role,
            sha256=_sha256_bytes(payloads[entry.path]),
            byte_count=len(payloads[entry.path]),
        )
        for entry in profile.entries
    )
    profile_entry = next(item for item in files if item.path == profile.profile_path)
    source_references = _source_references_without_copies(
        _read_json_bytes(payloads["data/sources.json"], "data/sources.json"),
        {item.path for item in files},
        payloads,
    )
    return {
        "schema_version": profile.schema_version,
        "package": {
            "archive_root": profile.archive_root,
            "package_id": profile.package_id,
        },
        "freeze": {
            "freeze_id": freeze_id,
            "frozen_on": frozen_on,
            "repository_commit_sha": repository_commit_sha,
        },
        "scope": {
            "classification": list(profile.classification),
            "claim_boundary": profile.claim_boundary,
        },
        "profile": {"path": profile.profile_path, "sha256": profile_entry.sha256},
        "files": [
            {
                "path": item.path,
                "role": item.role,
                "sha256": item.sha256,
                "bytes": item.byte_count,
            }
            for item in files
        ],
        "tree_fingerprint": _tree_fingerprint(files),
        "member_sha256_basis": MEMBER_SHA256_BASIS,
        "referenced_official_sources_without_retained_copy": list(source_references),
        "exclusions": list(profile.exclusions),
        "known_absences": list(profile.known_absences),
        "public_state_assertions": [
            {
                "path": item.path,
                "pointer": item.pointer,
                "equals": item.equals,
            }
            for item in profile.state_assertions
        ],
    }


def _output_path(root: Path, output: Path) -> Path:
    if output.is_symlink():
        raise ValueError(f"{output}: symbolic-link outputs are not allowed")
    specified = Path(os.path.abspath(output))
    if specified.parent.is_symlink():
        raise ValueError(f"{specified.parent}: expected a real output directory")
    target = specified.parent.resolve() / specified.name
    if target.is_relative_to(root):
        raise ValueError("output archive must be outside the repository root")
    if target.exists() or target.is_symlink():
        raise ValueError(f"{target}: refusing to overwrite an existing archive")
    if not target.parent.is_dir() or target.parent.is_symlink():
        raise ValueError(f"{target.parent}: expected a real output directory")
    return target


def _zip_member_name(archive_root: str, path: str) -> str:
    return f"{archive_root}/{path}"


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=_FIXED_ZIP_DATETIME)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = _FIXED_ZIP_MODE << 16
    info.extra = b""
    info.comment = b""
    info.flag_bits = 0
    return info


def _write_archive(
    output: Path,
    profile: ExportProfile,
    manifest: dict[str, Any],
    payloads: dict[str, bytes],
    *,
    today: date,
) -> None:
    members = [
        (
            _zip_member_name(profile.archive_root, MANIFEST_FILENAME),
            _manifest_json(manifest),
        ),
        *[
            (_zip_member_name(profile.archive_root, path), content)
            for path, content in payloads.items()
        ],
    ]
    if [name for name, _ in members] != sorted(name for name, _ in members):
        members.sort(key=lambda item: item[0])
    descriptor, temporary_name = tempfile.mkstemp(
        dir=output.parent,
        prefix=f".{output.name}.",
        suffix=".tmp",
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(
            temporary,
            mode="w",
            compression=zipfile.ZIP_STORED,
            allowZip64=False,
            strict_timestamps=True,
        ) as archive:
            archive.comment = b""
            for name, content in members:
                archive.writestr(_zip_info(name), content)
        if temporary.stat().st_size > _MAX_ARCHIVE_BYTES:
            raise ValueError("archive: encoded size exceeds the size limit")
        _verify_archive_file(temporary, today=today)
        try:
            os.link(temporary, output, follow_symlinks=False)
        except FileExistsError as error:
            raise ValueError(
                f"{output}: refusing to overwrite an existing archive"
            ) from error
        temporary.unlink()
    finally:
        if temporary.exists():
            temporary.unlink()


def build_export(
    root: Path,
    output: Path,
    *,
    freeze_id: str,
    frozen_on: str,
    repository_commit_sha: str | None = None,
    today: date | None = None,
    profile_path: Path | None = None,
    profile_version: int | None = None,
) -> dict[str, Any]:
    """Build one deterministic ZIP_STORED evidence package.

    Each schema uses its own canonical repository profile.  The default is the
    current registry-aware schema v2; callers can explicitly select the frozen
    schema v1 compatibility profile.  Every profile pins included raw files
    except its self-referential entry, so drift stops the build.
    """

    repository = _root_directory(root)
    target = _output_path(repository, output)
    normalized_freeze_id = _require_identifier(freeze_id, "freeze_id")
    normalized_frozen_on = _require_frozen_on(
        frozen_on,
        "frozen_on",
        today=resolve_today(today),
    )
    profile = load_export_profile(
        repository,
        profile_path,
        profile_version=profile_version,
    )
    payloads = _entry_payloads(repository, profile)
    normalized_commit_sha = _verify_profile_matches_git_head(
        repository,
        profile,
        payloads,
        repository_commit_sha=repository_commit_sha,
    )
    validate_restored_evidence(
        repository,
        today=resolve_today(today),
        frozen_on=date.fromisoformat(normalized_frozen_on),
        profile_path=Path(profile.profile_path),
    )
    manifest = _manifest_payload(
        profile,
        normalized_freeze_id,
        normalized_frozen_on,
        normalized_commit_sha,
        payloads,
    )
    _write_archive(target, profile, manifest, payloads, today=resolve_today(today))
    return manifest


def _validate_zip_info(info: zipfile.ZipInfo) -> str:
    name = _safe_relative_path(info.filename, "archive member")
    if info.is_dir():
        raise ValueError(f"{name}: directory members are not allowed")
    if info.compress_type != zipfile.ZIP_STORED:
        raise ValueError(f"{name}: compressed archive members are not allowed")
    if info.compress_size != info.file_size:
        raise ValueError(f"{name}: stored member size is not canonical")
    if info.flag_bits != 0:
        raise ValueError(f"{name}: archive member flags are not canonical")
    if info.extra or info.comment:
        raise ValueError(f"{name}: archive member extras are not allowed")
    if info.date_time != _FIXED_ZIP_DATETIME:
        raise ValueError(f"{name}: archive member timestamp is not canonical")
    if info.create_system != 3 or (info.external_attr >> 16) != _FIXED_ZIP_MODE:
        raise ValueError(f"{name}: archive member mode is not canonical")
    if info.file_size < 0 or info.file_size > _MAX_MEMBER_BYTES:
        raise ValueError(f"{name}: archive member exceeds the size limit")
    return name


def _archive_infos(archive: zipfile.ZipFile) -> tuple[dict[str, zipfile.ZipInfo], str]:
    infos = archive.infolist()
    if not infos or len(infos) > _MAX_MEMBERS:
        raise ValueError("archive: invalid member count")
    by_name: dict[str, zipfile.ZipInfo] = {}
    normalized: set[str] = set()
    total = 0
    names_in_order: list[str] = []
    for info in infos:
        name = _validate_zip_info(info)
        collision = name.casefold()
        if name in by_name or collision in normalized:
            raise ValueError(
                f"{name}: duplicate or normalized-colliding archive member"
            )
        by_name[name] = info
        names_in_order.append(name)
        normalized.add(collision)
        total += info.file_size
    if total > _MAX_TOTAL_BYTES:
        raise ValueError("archive: total uncompressed size exceeds the limit")
    if names_in_order != sorted(names_in_order):
        raise ValueError("archive: members are not in canonical POSIX order")
    manifest_names = [
        name for name in by_name if name.endswith(f"/{MANIFEST_FILENAME}")
    ]
    if len(manifest_names) != 1:
        raise ValueError("archive: expected exactly one manifest")
    manifest_name = manifest_names[0]
    parts = manifest_name.split("/")
    if len(parts) != 2:
        raise ValueError("archive: manifest must sit at the archive root")
    return by_name, parts[0]


def _read_member(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    *,
    maximum: int,
) -> bytes:
    chunks: list[bytes] = []
    total = 0
    with archive.open(info, "r") as stream:
        while chunk := stream.read(_CHUNK_BYTES):
            total += len(chunk)
            if total > maximum:
                raise ValueError(f"{info.filename}: member exceeds the size limit")
            chunks.append(chunk)
    if total != info.file_size:
        raise ValueError(f"{info.filename}: archive member size changed while reading")
    return b"".join(chunks)


def _stream_member_digest(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> str:
    digest = hashlib.sha256()
    total = 0
    with archive.open(info, "r") as stream:
        while chunk := stream.read(_CHUNK_BYTES):
            total += len(chunk)
            if total > _MAX_MEMBER_BYTES:
                raise ValueError(f"{info.filename}: member exceeds the size limit")
            digest.update(chunk)
    if total != info.file_size:
        raise ValueError(f"{info.filename}: archive member size changed while reading")
    return "sha256:" + digest.hexdigest()


def _parse_manifest_file(value: Any, field: str) -> _ManifestFile:
    entry = _require_object(value, field)
    _require_exact_keys(entry, _MANIFEST_FILE_KEYS, field)
    byte_count = entry.get("bytes")
    if (
        not isinstance(byte_count, int)
        or isinstance(byte_count, bool)
        or byte_count < 0
    ):
        raise ValueError(f"{field}.bytes: expected a non-negative integer")
    return _ManifestFile(
        path=_safe_relative_path(entry.get("path"), f"{field}.path"),
        role=_require_role(entry.get("role"), f"{field}.role"),
        sha256=_require_sha256(entry.get("sha256"), f"{field}.sha256"),
        byte_count=byte_count,
    )


def _parse_source_references(value: Any) -> tuple[dict[str, str], ...]:
    if not isinstance(value, list):
        raise ValueError(
            "referenced_official_sources_without_retained_copy: expected list"
        )
    references: list[dict[str, str]] = []
    for index, raw in enumerate(value):
        field = f"referenced_official_sources_without_retained_copy[{index}]"
        record = _require_object(raw, field)
        _require_exact_keys(record, _MANIFEST_SOURCE_REFERENCE_KEYS, field)
        source_id = _require_text(record.get("source_id"), f"{field}.source_id")
        if not _SOURCE_ID.fullmatch(source_id):
            raise ValueError(f"{field}.source_id: invalid stable identifier")
        references.append(
            {
                "source_id": source_id,
                "label": _require_text(record.get("label"), f"{field}.label"),
                "url": _require_text(record.get("url"), f"{field}.url"),
            }
        )
    if [item["source_id"] for item in references] != sorted(
        item["source_id"] for item in references
    ):
        raise ValueError(
            "referenced_official_sources_without_retained_copy: expected sorted sources"
        )
    if len({item["source_id"] for item in references}) != len(references):
        raise ValueError(
            "referenced_official_sources_without_retained_copy: duplicate source"
        )
    return tuple(references)


def _parse_manifest_assertions(value: Any) -> tuple[StateAssertion, ...]:
    if not isinstance(value, list) or not value or len(value) > _MAX_STATE_ASSERTIONS:
        raise ValueError("public_state_assertions: expected a non-empty list")
    assertions = tuple(
        _parse_state_assertion(item, f"public_state_assertions[{index}]")
        for index, item in enumerate(value)
    )
    keys = {(item.path, item.pointer) for item in assertions}
    if len(keys) != len(assertions):
        raise ValueError("public_state_assertions: duplicate path/pointer")
    return assertions


def _parse_manifest_freeze(value: Any, *, today: date) -> tuple[str, str, str]:
    freeze = _require_object(value, "manifest.freeze")
    _require_exact_keys(freeze, _MANIFEST_FREEZE_KEYS, "manifest.freeze")
    freeze_id = _require_identifier(
        freeze.get("freeze_id"), "manifest.freeze.freeze_id"
    )
    frozen_on = _require_frozen_on(
        freeze.get("frozen_on"),
        "manifest.freeze.frozen_on",
        today=today,
    )
    repository_commit_sha = _require_commit_sha(
        freeze.get("repository_commit_sha"),
        "manifest.freeze.repository_commit_sha",
    )
    return freeze_id, frozen_on, repository_commit_sha


def _parse_manifest_files(value: Any) -> tuple[_ManifestFile, ...]:
    if not isinstance(value, list) or not value or len(value) > _MAX_MEMBERS - 1:
        raise ValueError("manifest.files: expected a non-empty list")
    files = tuple(
        _parse_manifest_file(item, f"manifest.files[{index}]")
        for index, item in enumerate(value)
    )
    paths = tuple(item.path for item in files)
    if (
        paths != tuple(sorted(paths))
        or len(paths) != len(set(paths))
        or len({path.casefold() for path in paths}) != len(paths)
    ):
        raise ValueError("manifest.files: expected sorted unique paths")
    return files


def _parse_manifest(payload: Any, *, today: date) -> _Manifest:
    manifest = _require_object(payload, "manifest")
    _require_exact_keys(manifest, _MANIFEST_KEYS, "manifest")
    schema_version = manifest.get("schema_version")
    if (
        type(schema_version) is not int
        or schema_version not in SUPPORTED_SCHEMA_VERSIONS
    ):
        raise ValueError("manifest.schema_version: expected 1 or 2")
    if manifest.get("member_sha256_basis") != MEMBER_SHA256_BASIS:
        raise ValueError("manifest.member_sha256_basis: invalid digest basis")

    package = _require_object(manifest.get("package"), "manifest.package")
    _require_exact_keys(package, _MANIFEST_PACKAGE_KEYS, "manifest.package")
    package_id = _require_identifier(
        package.get("package_id"), "manifest.package.package_id"
    )
    archive_root = _require_identifier(
        package.get("archive_root"), "manifest.package.archive_root"
    )

    freeze_id, frozen_on, repository_commit_sha = _parse_manifest_freeze(
        manifest.get("freeze"),
        today=today,
    )

    scope = _require_object(manifest.get("scope"), "manifest.scope")
    _require_exact_keys(scope, _MANIFEST_SCOPE_KEYS, "manifest.scope")
    classification = _require_string_list(
        scope.get("classification"), "manifest.scope.classification"
    )
    if classification != ("public", "synthetic"):
        raise ValueError("manifest.scope.classification: expected public and synthetic")
    _require_text(scope.get("claim_boundary"), "manifest.scope.claim_boundary")
    _require_string_list(manifest.get("exclusions"), "manifest.exclusions")
    _require_string_list(manifest.get("known_absences"), "manifest.known_absences")

    profile = _require_object(manifest.get("profile"), "manifest.profile")
    _require_exact_keys(profile, _MANIFEST_PROFILE_KEYS, "manifest.profile")
    profile_path = _safe_relative_path(profile.get("path"), "manifest.profile.path")
    if profile_path != PROFILE_PATHS[schema_version].as_posix():
        raise ValueError(
            f"manifest.profile.path: schema v{schema_version} requires its "
            "canonical profile"
        )
    profile_sha256 = _require_sha256(profile.get("sha256"), "manifest.profile.sha256")

    files = _parse_manifest_files(manifest.get("files"))
    paths = tuple(item.path for item in files)
    if profile_path not in paths:
        raise ValueError("manifest.profile.path: profile is not listed as a file")
    profile_file = next(item for item in files if item.path == profile_path)
    if profile_file.sha256 != profile_sha256:
        raise ValueError("manifest.profile.sha256: does not match the profile file")
    if _tree_fingerprint(files) != _require_sha256(
        manifest.get("tree_fingerprint"), "manifest.tree_fingerprint"
    ):
        raise ValueError("manifest.tree_fingerprint: does not match file records")
    _parse_source_references(
        manifest.get("referenced_official_sources_without_retained_copy")
    )
    assertions = _parse_manifest_assertions(manifest.get("public_state_assertions"))
    if not {item.path for item in assertions} <= set(paths):
        raise ValueError("public_state_assertions: path is not listed as a file")
    return _Manifest(
        payload=manifest,
        package_id=package_id,
        archive_root=archive_root,
        freeze_id=freeze_id,
        frozen_on=frozen_on,
        repository_commit_sha=repository_commit_sha,
        profile_path=profile_path,
        profile_sha256=profile_sha256,
        files=files,
        schema_version=schema_version,
    )


def _profile_from_archive(
    archive: zipfile.ZipFile,
    infos: dict[str, zipfile.ZipInfo],
    manifest: _Manifest,
) -> ExportProfile:
    member_name = _zip_member_name(manifest.archive_root, manifest.profile_path)
    profile_info = infos[member_name]
    profile_bytes = _read_member(archive, profile_info, maximum=_MAX_MANIFEST_BYTES)
    if _sha256_bytes(profile_bytes) != manifest.profile_sha256:
        raise ValueError("manifest.profile.sha256: profile content drifted")
    profile = _parse_profile(
        _read_json_bytes(profile_bytes, manifest.profile_path), manifest.profile_path
    )
    if profile.schema_version != manifest.schema_version:
        raise ValueError("manifest.schema_version: does not match the export profile")
    profile_entries = tuple((entry.path, entry.role) for entry in profile.entries)
    manifest_entries = tuple((entry.path, entry.role) for entry in manifest.files)
    if profile_entries != manifest_entries:
        raise ValueError("manifest.files: does not match the export profile")
    if (
        profile.package_id != manifest.package_id
        or profile.archive_root != manifest.archive_root
        or list(profile.classification) != manifest.payload["scope"]["classification"]
        or profile.claim_boundary != manifest.payload["scope"]["claim_boundary"]
        or list(profile.exclusions) != manifest.payload["exclusions"]
        or list(profile.known_absences) != manifest.payload["known_absences"]
    ):
        raise ValueError("manifest: package scope does not match the export profile")
    profile_assertions = [
        {"path": item.path, "pointer": item.pointer, "equals": item.equals}
        for item in profile.state_assertions
    ]
    if profile_assertions != manifest.payload["public_state_assertions"]:
        raise ValueError("manifest: public state assertions do not match the profile")
    return profile


def _validate_archive_contents(
    archive: zipfile.ZipFile,
    infos: dict[str, zipfile.ZipInfo],
    archive_root: str,
    manifest: _Manifest,
) -> ExportProfile:
    if archive_root != manifest.archive_root:
        raise ValueError("archive root does not match the manifest")
    expected_names = {
        _zip_member_name(manifest.archive_root, MANIFEST_FILENAME),
        *(
            _zip_member_name(manifest.archive_root, item.path)
            for item in manifest.files
        ),
    }
    if set(infos) != expected_names:
        raise ValueError("archive: unknown, missing, or unlisted members")
    profile = _profile_from_archive(archive, infos, manifest)
    payloads: dict[str, bytes] = {}
    for item in manifest.files:
        info = infos[_zip_member_name(manifest.archive_root, item.path)]
        if info.file_size != item.byte_count:
            raise ValueError(f"{item.path}: byte count does not match the manifest")
        if _stream_member_digest(archive, info) != item.sha256:
            raise ValueError(f"{item.path}: raw SHA-256 does not match the manifest")
        payloads[item.path] = _read_member(
            archive,
            info,
            maximum=_MAX_MEMBER_BYTES,
        )
    for entry in profile.entries:
        expected = entry.raw_sha256
        if expected is None:
            continue
        actual = next(item.sha256 for item in manifest.files if item.path == entry.path)
        if actual != expected:
            raise ValueError(f"{entry.path}: raw SHA-256 does not match the profile")
    _validate_workflow_registry_closure(profile, payloads)
    sources = _source_references_without_copies(
        _read_json_bytes(payloads["data/sources.json"], "data/sources.json"),
        {item.path for item in manifest.files},
        payloads,
    )
    if (
        list(sources)
        != manifest.payload["referenced_official_sources_without_retained_copy"]
    ):
        raise ValueError("manifest: official-source reference list drifted")
    _validate_state_assertions(profile, payloads)
    return profile


def _canonical_archive_bytes(
    archive: zipfile.ZipFile,
    infos: dict[str, zipfile.ZipInfo],
) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_STORED,
        allowZip64=False,
        strict_timestamps=True,
    ) as rebuilt:
        rebuilt.comment = b""
        for name in sorted(infos):
            rebuilt.writestr(
                _zip_info(name),
                _read_member(archive, infos[name], maximum=_MAX_MEMBER_BYTES),
            )
    return output.getvalue()


def _verify_archive(
    archive: zipfile.ZipFile, *, archive_bytes: bytes, today: date
) -> _Manifest:
    if archive.comment:
        raise ValueError("archive: comments are not allowed")
    infos, archive_root = _archive_infos(archive)
    manifest_name = _zip_member_name(archive_root, MANIFEST_FILENAME)
    manifest_bytes = _read_member(
        archive,
        infos[manifest_name],
        maximum=_MAX_MANIFEST_BYTES,
    )
    manifest = _parse_manifest(
        _read_json_bytes(manifest_bytes, "manifest"),
        today=today,
    )
    if manifest_bytes != _manifest_json(manifest.payload):
        raise ValueError("manifest: expected canonical JSON encoding")
    _validate_archive_contents(archive, infos, archive_root, manifest)
    if archive_bytes != _canonical_archive_bytes(archive, infos):
        raise ValueError("archive: byte layout is not canonical")
    return manifest


def _archive_file(path: Path) -> Path:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise ValueError(f"{path}: expected a regular archive file") from error
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"{path}: expected a regular archive file")
    resolved = path.resolve()
    if resolved.stat().st_size > _MAX_ARCHIVE_BYTES:
        raise ValueError(f"{path}: archive exceeds the size limit")
    return resolved


def _verify_archive_file(path: Path, *, today: date) -> _Manifest:
    archive_file = _archive_file(path)
    archive_bytes = archive_file.read_bytes()
    if len(archive_bytes) > _MAX_ARCHIVE_BYTES:
        raise ValueError(f"{path}: archive exceeds the size limit")
    try:
        with zipfile.ZipFile(
            io.BytesIO(archive_bytes), "r", allowZip64=False
        ) as archive:
            return _verify_archive(archive, archive_bytes=archive_bytes, today=today)
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as error:
        raise ValueError(f"{path}: invalid evidence archive") from error


def verify_export(
    archive_path: Path,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """Verify archive structure, profile pins, raw hashes, and public state."""

    return _verify_archive_file(archive_path, today=resolve_today(today)).payload


def _copy_member(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    destination: Path,
    expected_sha256: str,
) -> None:
    digest = hashlib.sha256()
    total = 0
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with archive.open(info, "r") as source, destination.open("xb") as target:
        while chunk := source.read(_CHUNK_BYTES):
            total += len(chunk)
            if total > _MAX_MEMBER_BYTES:
                raise ValueError(f"{info.filename}: member exceeds the size limit")
            digest.update(chunk)
            target.write(chunk)
    if total != info.file_size or "sha256:" + digest.hexdigest() != expected_sha256:
        raise ValueError(f"{info.filename}: raw SHA-256 changed during restore")


def _restore_target(destination: Path) -> Path:
    if destination.is_symlink():
        raise ValueError(
            f"{destination}: symbolic-link restore destinations are not allowed"
        )
    specified = Path(os.path.abspath(destination))
    if specified.parent.is_symlink():
        raise ValueError(
            f"{specified.parent}: expected a real restore parent directory"
        )
    target = specified.parent.resolve() / specified.name
    if target.exists() or target.is_symlink():
        raise ValueError(f"{target}: restore destination must not already exist")
    if not target.parent.is_dir() or target.parent.is_symlink():
        raise ValueError(f"{target.parent}: expected a real restore parent directory")
    return target


def _rename_no_replace(source: Path, target: Path) -> None:
    """Atomically publish a directory only when its final name is unused.

    ``os.replace`` is deliberately not suitable here: it can replace an empty
    destination directory that appeared after staging.  Darwin and Linux both
    expose an exclusive rename primitive; unsupported platforms fail closed.
    """

    import ctypes

    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source)
    target_bytes = os.fsencode(target)
    system = platform.system()
    if system == "Darwin":
        operation = getattr(libc, "renameatx_np", None)
        if operation is None:
            raise OSError("exclusive directory rename is unavailable")
        operation.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        operation.restype = ctypes.c_int
        result = operation(-2, source_bytes, -2, target_bytes, 0x00000004)
    elif system == "Linux":
        operation = getattr(libc, "renameat2", None)
        if operation is None:
            raise OSError("exclusive directory rename is unavailable")
        operation.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        operation.restype = ctypes.c_int
        result = operation(-100, source_bytes, -100, target_bytes, 1)
    else:
        raise OSError("exclusive directory rename is unavailable")
    if result != 0:
        error_number = ctypes.get_errno()
        if error_number == EEXIST:
            raise FileExistsError(error_number, os.strerror(error_number), target)
        raise OSError(error_number, os.strerror(error_number), target)


def _restore_to_staging(
    archive: zipfile.ZipFile,
    manifest: _Manifest,
    destination: Path,
) -> Path:
    staging = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.restore-", dir=destination.parent)
    )
    os.chmod(staging, 0o700)
    try:
        infos = {info.filename: info for info in archive.infolist()}
        manifest_member = _zip_member_name(manifest.archive_root, MANIFEST_FILENAME)
        _copy_member(
            archive,
            infos[manifest_member],
            staging / MANIFEST_FILENAME,
            _sha256_bytes(_manifest_json(manifest.payload)),
        )
        for item in manifest.files:
            _copy_member(
                archive,
                infos[_zip_member_name(manifest.archive_root, item.path)],
                staging / Path(*item.path.split("/")),
                item.sha256,
            )
        validate_restored_evidence(
            staging,
            today=date.fromisoformat(manifest.frozen_on),
            frozen_on=date.fromisoformat(manifest.frozen_on),
            profile_path=Path(manifest.profile_path),
        )
        return staging
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def restore_export(
    archive_path: Path,
    destination: Path,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """Restore a verified package into a new directory without side effects.

    All archive checks and canonical loaders run in a sibling ``0700`` staging
    directory before the final atomic rename.  The operation never adopts or
    publishes the restored records.
    """

    archive_file = _archive_file(archive_path)
    archive_bytes = archive_file.read_bytes()
    if len(archive_bytes) > _MAX_ARCHIVE_BYTES:
        raise ValueError(f"{archive_path}: archive exceeds the size limit")
    target = _restore_target(destination)
    staging: Path | None = None
    try:
        with zipfile.ZipFile(
            io.BytesIO(archive_bytes), "r", allowZip64=False
        ) as archive:
            manifest = _verify_archive(
                archive,
                archive_bytes=archive_bytes,
                today=resolve_today(today),
            )
            staging = _restore_to_staging(archive, manifest, target)
        _rename_no_replace(staging, target)
        staging = None
        return manifest.payload
    except FileExistsError as error:
        raise ValueError(
            f"{target}: restore destination appeared during staging"
        ) from error
    except (zipfile.BadZipFile, zipfile.LargeZipFile) as error:
        raise ValueError(f"{archive_path}: invalid evidence archive") from error
    finally:
        if staging is not None and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def _read_restored_json(root: Path, relative: str) -> Any:
    return _read_json_bytes(
        _read_regular_file_bytes(root, relative, maximum=_MAX_MEMBER_BYTES),
        relative,
    )


def _validate_v1_workflow_evidence(
    repository: Path,
    data: Path,
    rules: Any,
    *,
    as_of: date,
) -> None:
    """Replay the fixed paths retained by the frozen schema-v1 contract."""

    from .journey import load_journey_config, resolve_journey
    from .program_availability import load_program_availability
    from .readiness import (
        evaluate_readiness,
        load_readiness_packet,
        load_readiness_remedies,
        load_readiness_workflow,
    )

    workflow = load_readiness_workflow(
        data / "readiness/workflows/woodland-preapproved-detached-adu.json",
        data / "sources.json",
        today=as_of,
    )
    packet = load_readiness_packet(
        data / "readiness/samples/woodland-preapproved-adu.json",
        workflow,
        today=as_of,
    )
    result = evaluate_readiness(
        workflow,
        packet,
        today=date.fromisoformat(packet.evaluated_on),
    )
    load_readiness_remedies(
        data / "readiness/remedies/woodland-preapproved-detached-adu.json",
        workflow,
        today=as_of,
    )
    generated_readiness = _read_restored_json(
        repository,
        "data/readiness/generated/woodland-preapproved-adu-evidence.json",
    )
    if generated_readiness != result.to_manifest(workflow, packet):
        raise ValueError("restored readiness evidence does not match the evaluator")
    load_program_availability(
        data / "availability/woodland-preapproved-adu-program.json",
        today=as_of,
    )
    journey = resolve_journey(
        load_journey_config(data / "journeys/woodland-preapproved-detached-adu.json"),
        data / "golden" / "example.json",
        rules,
        workflow,
        packet,
        result,
    )
    generated_journey = _read_restored_json(
        repository,
        "data/journeys/generated/woodland-preapproved-detached-adu.json",
    )
    if generated_journey != journey:
        raise ValueError("restored journey evidence does not match the resolver")


def _validate_v2_workflow_evidence(
    repository: Path,
    data: Path,
    rules: Any,
    *,
    as_of: date,
) -> None:
    """Replay every workflow selected by the schema-v2 registry."""

    from .journey import load_journey_config, resolve_journey
    from .program_availability import load_program_availability
    from .readiness import (
        evaluate_readiness,
        load_readiness_packet,
        load_readiness_remedies,
        load_readiness_workflow,
    )
    from .workflow_registry import load_workflow_registry

    workflow_registry = load_workflow_registry(
        data / "workflows" / "registry.json",
        root=repository,
    )
    for workflow_entry in workflow_registry.workflows:
        artifacts = workflow_entry.artifacts
        workflow = load_readiness_workflow(
            artifacts.readiness_workflow.resolve(repository),
            data / "sources.json",
            today=as_of,
        )
        packet = load_readiness_packet(
            artifacts.readiness_packet.resolve(repository),
            workflow,
            today=as_of,
        )
        result = evaluate_readiness(
            workflow,
            packet,
            today=date.fromisoformat(packet.evaluated_on),
        )
        load_readiness_remedies(
            artifacts.readiness_remedies.resolve(repository),
            workflow,
            today=as_of,
        )
        generated_readiness = _read_restored_json(
            repository,
            artifacts.readiness_evidence.path,
        )
        if generated_readiness != result.to_manifest(workflow, packet):
            raise ValueError("restored readiness evidence does not match the evaluator")
        availability = load_program_availability(
            artifacts.program_availability.resolve(repository),
            today=as_of,
            policy=workflow_entry.availability_policy,
        )
        if (
            availability.workflow_id != workflow_entry.workflow_id
            or availability.program_id != workflow_entry.program_id
        ):
            raise ValueError("restored availability does not match its registry entry")
        if artifacts.journey is None or artifacts.journey_evidence is None:
            # A packet-only workflow registers no journey to replay.
            continue
        journey = resolve_journey(
            load_journey_config(artifacts.journey.resolve(repository)),
            data / "golden" / "example.json",
            rules,
            workflow,
            packet,
            result,
        )
        generated_journey = _read_restored_json(
            repository,
            artifacts.journey_evidence.path,
        )
        if generated_journey != journey:
            raise ValueError("restored journey evidence does not match the resolver")


def validate_restored_evidence(
    root: Path,
    *,
    today: date,
    frozen_on: date | None = None,
    profile_path: Path | None = None,
) -> None:
    """Replay core deterministic loaders against a restored evidence directory."""

    repository = _root_directory(root)
    as_of = frozen_on or today
    profile = load_export_profile(repository, profile_path)
    _validate_state_assertions(profile, _entry_payloads(repository, profile))

    from .conformance import load_checks
    from .harness.runner import load_golden
    from .harness.watch import load_sources
    from .jurisdictions import build_coverage_index, load_registry
    from .rule_verification import load_rule_verifications
    from .screening import load_rules
    from .source_state import load_source_state_snapshot

    data = repository / "data"
    rules = load_rules(data / "rules", today=as_of)
    load_golden(data / "golden" / "example.json", rules)
    load_sources(data / "sources.json", today=as_of)
    load_source_state_snapshot(
        data / "source-status" / "current.json",
        data / "sources.json",
        data / "rules",
        data / "golden" / "example.json",
        require_reviewed=True,
    )
    load_rule_verifications(
        data / "validation" / "rule-verification.json",
        rules,
        today=as_of,
    )
    if profile.schema_version == 1:
        _validate_v1_workflow_evidence(repository, data, rules, as_of=as_of)
    else:
        _validate_v2_workflow_evidence(repository, data, rules, as_of=as_of)
    if not load_checks(data / "conformance" / "checks.json"):
        raise ValueError("restored conformance checks are empty")
    registry = load_registry(
        data / "jurisdictions" / "registry.json",
        data / "rules",
        data / "jurisdictions" / "hcd-letters.json",
    )
    if not registry:
        raise ValueError("restored jurisdiction registry is empty")
    expected_coverage = build_coverage_index(
        data / "jurisdictions" / "registry.json",
        data / "rules",
        data / "jurisdictions" / "hcd-letters.json",
    )
    generated_coverage = _read_restored_json(
        repository,
        "data/jurisdictions/generated/coverage-index.json",
    )
    if generated_coverage != expected_coverage:
        raise ValueError("restored coverage index does not match canonical records")
