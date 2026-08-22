"""Adversarial coverage for the portable public/synthetic evidence export."""

from __future__ import annotations

import hashlib
import json
import shutil
import stat
import struct
import subprocess
import zipfile
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

import permit_pathways.evidence_export as evidence_export
from permit_pathways.evidence_export import (
    _safe_relative_path,
    build_export,
    load_export_profile,
    restore_export,
    verify_export,
)
from permit_pathways.evidence_export_cli import main as evidence_export_main

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FREEZE_ID = "public-synthetic-evidence-freeze-2026-08-09"
FREEZE_ON = "2026-08-22"
AS_OF = date.fromisoformat(FREEZE_ON)
V1_PROFILE_PATH = Path("data/export/public-synthetic-evidence-v1.json")
V2_PROFILE_PATH = Path("data/export/public-synthetic-evidence-v2.json")
FROZEN_V1_PROFILE_SHA256 = (
    "30a36dc43f9a52320e3085648a0f383ee2b641bbbe1f4b852651d2110e4d2fbf"
)


def _git(root: Path, *args: str) -> str:
    executable = shutil.which("git")
    assert executable is not None, "Git is required for evidence export tests"
    completed = subprocess.run(
        [executable, "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _commit_sha(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD").strip()


@pytest.fixture(scope="module")
def committed_evidence_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a minimal committed repository containing exactly the profile set."""

    root = tmp_path_factory.mktemp("committed-evidence-repository")
    profile = load_export_profile(REPOSITORY_ROOT)
    for entry in profile.entries:
        source = REPOSITORY_ROOT / entry.path
        destination = root / entry.path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    _git(root, "init", "-q")
    _git(root, "add", ".")
    _git(
        root,
        "-c",
        "user.name=Codex",
        "-c",
        "user.email=codex@example.test",
        "commit",
        "-qm",
        "public synthetic evidence",
    )
    return root


@pytest.fixture()
def legacy_v1_evidence_root(tmp_path: Path) -> Path:
    """Build a committed schema-v1-shaped root without the later registry.

    The repository's frozen v1 profile retains every historical digest. This
    archive-style fixture substitutes current digests in its temporary copy so
    the compatibility parser, verifier, semantic replay, and restore can be
    exercised without changing that frozen profile identity.
    """

    root = tmp_path / "legacy-v1-repository"
    raw_profile = (REPOSITORY_ROOT / V1_PROFILE_PATH).read_bytes()
    profile_payload = json.loads(raw_profile)
    profile = evidence_export._parse_profile(
        profile_payload,
        V1_PROFILE_PATH.as_posix(),
    )
    for entry in profile.entries:
        source = REPOSITORY_ROOT / entry.path
        destination = root / entry.path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    for entry in profile_payload["entries"]:
        if entry.get("raw_sha256") is not None:
            entry["raw_sha256"] = (
                "sha256:"
                + hashlib.sha256((root / entry["path"]).read_bytes()).hexdigest()
            )
    (root / V1_PROFILE_PATH).write_text(
        json.dumps(profile_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    _git(root, "init", "-q")
    _git(root, "add", ".")
    _git(
        root,
        "-c",
        "user.name=Codex",
        "-c",
        "user.email=codex@example.test",
        "commit",
        "-qm",
        "legacy schema v1 evidence fixture",
    )
    return root


def _build(root: Path, output: Path) -> dict[str, object]:
    return build_export(
        root,
        output,
        freeze_id=FREEZE_ID,
        frozen_on=FREEZE_ON,
        repository_commit_sha=_commit_sha(root),
        today=AS_OF,
    )


@pytest.fixture(scope="module")
def valid_archive(
    committed_evidence_root: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, dict[str, object]]:
    output = tmp_path_factory.mktemp("evidence-archive") / "evidence.zip"
    return output, _build(committed_evidence_root, output)


def _canonical_info(
    name: str, *, compression: int = zipfile.ZIP_STORED
) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = compression
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    info.extra = b""
    info.comment = b""
    info.flag_bits = 0
    return info


def _rewrite_archive(
    source: Path,
    output: Path,
    *,
    replace: dict[str, bytes] | None = None,
    extra: tuple[str, bytes] | None = None,
    duplicate: str | None = None,
    compression: int | None = None,
    mode: int | None = None,
    archive_comment: bytes = b"",
) -> None:
    replacements = replace or {}
    members: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(source) as archive:
        for info in archive.infolist():
            members.append(
                (info.filename, replacements.get(info.filename, archive.read(info)))
            )
    if extra is not None:
        members.append(extra)
    if duplicate is not None:
        payload = next(content for name, content in members if name == duplicate)
        members.append((duplicate, payload))
    members.sort(key=lambda item: item[0])
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.comment = archive_comment
        for index, (name, content) in enumerate(members):
            member_compression = (
                compression
                if compression is not None and index == 0
                else zipfile.ZIP_STORED
            )
            info = _canonical_info(name, compression=member_compression)
            if mode is not None and index == 0:
                info.external_attr = mode << 16
            archive.writestr(info, content)


def _set_encrypted_flag(source: Path, output: Path) -> None:
    """Set the ZIP encrypted bit in matching local and central headers."""

    payload = bytearray(source.read_bytes())
    local_header = payload.find(b"PK\x03\x04")
    central_header = payload.find(b"PK\x01\x02")
    assert local_header >= 0 and central_header >= 0
    struct.pack_into("<H", payload, local_header + 6, 1)
    struct.pack_into("<H", payload, central_header + 8, 1)
    output.write_bytes(payload)


def test_frozen_v1_profile_retains_exact_pre_registry_identity() -> None:
    raw = (REPOSITORY_ROOT / V1_PROFILE_PATH).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FROZEN_V1_PROFILE_SHA256
    payload = json.loads(raw)
    assert payload["schema_version"] == 1
    assert len(payload["entries"]) == 59
    assert {entry["path"] for entry in payload["entries"]}.isdisjoint(
        {"data/workflows/registry.json"}
    )
    assert payload["package"] == {
        "archive_root": "permit-bearings-evidence-v1",
        "package_id": "permit-bearings-public-synthetic-evidence-v1",
    }


def test_legacy_v1_archive_style_fixture_verifies_and_restores(
    legacy_v1_evidence_root: Path,
    tmp_path: Path,
) -> None:
    assert load_export_profile(legacy_v1_evidence_root).schema_version == 1
    archive = tmp_path / "legacy-v1.zip"
    manifest = build_export(
        legacy_v1_evidence_root,
        archive,
        freeze_id=FREEZE_ID,
        frozen_on=FREEZE_ON,
        repository_commit_sha=_commit_sha(legacy_v1_evidence_root),
        today=AS_OF,
    )
    assert manifest["schema_version"] == 1
    assert len(manifest["files"]) == 59
    assert all(
        item["path"] != "data/workflows/registry.json" for item in manifest["files"]
    )
    assert verify_export(archive, today=AS_OF) == manifest

    restored = tmp_path / "legacy-v1-restored"
    assert restore_export(archive, restored, today=AS_OF) == manifest
    assert (restored / V1_PROFILE_PATH).is_file()
    assert not (restored / "data/workflows/registry.json").exists()


def test_build_verify_restore_is_deterministic_and_inert(
    committed_evidence_root: Path,
    tmp_path: Path,
) -> None:
    first_archive = tmp_path / "first.zip"
    second_archive = tmp_path / "second.zip"

    manifest = _build(committed_evidence_root, first_archive)
    assert manifest["schema_version"] == 2
    assert _build(committed_evidence_root, second_archive) == manifest
    assert first_archive.read_bytes() == second_archive.read_bytes()
    assert verify_export(first_archive, today=AS_OF) == manifest

    with zipfile.ZipFile(first_archive) as archive:
        assert archive.comment == b""
        infos = archive.infolist()
        assert [info.filename for info in infos] == sorted(
            info.filename for info in infos
        )
        assert all(info.compress_type == zipfile.ZIP_STORED for info in infos)
        assert all(info.compress_size == info.file_size for info in infos)
        assert all(info.flag_bits == 0 for info in infos)
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in infos)
        assert all(
            (info.external_attr >> 16) == (stat.S_IFREG | 0o644) for info in infos
        )
        assert all(not info.extra and not info.comment for info in infos)

    freeze = manifest["freeze"]
    assert isinstance(freeze, dict)
    assert freeze["repository_commit_sha"] == _commit_sha(committed_evidence_root)
    assert manifest["member_sha256_basis"] == "raw_archive_member_bytes"

    source_registry = json.loads(
        (committed_evidence_root / "data/sources.json").read_text(encoding="utf-8")
    )
    normalized = next(
        record["sha256"]
        for record in source_registry.values()
        if record["source_id"] == "ca-gov-66317"
    )
    raw_file = next(
        item
        for item in manifest["files"]
        if item["path"] == "corpus/leginfo/gov-66317.html"
    )
    assert raw_file["sha256"] != f"sha256:{normalized}"

    destination = tmp_path / "restored"
    assert restore_export(first_archive, destination, today=AS_OF) == manifest
    assert (destination / "MANIFEST.json").is_file()
    assert (destination / "data/sources.json").is_file()
    assert (destination / "corpus/gtfs/unitrans.zip").is_file()
    assert (destination.stat().st_mode & 0o777) == 0o700
    assert not (destination / ".git").exists()
    with pytest.raises(ValueError, match="must not already exist"):
        restore_export(first_archive, destination, today=AS_OF)


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../data/sources.json",
        "data//sources.json",
        "data/CON.json",
        "data/edge.",
        "data/colon:name.json",
        "data/ümlaut.json",
    ],
)
def test_path_validation_rejects_nonportable_names(unsafe_path: str) -> None:
    with pytest.raises(ValueError):
        _safe_relative_path(unsafe_path, "test path")


def test_verify_rejects_zip_prefix_trailer_and_metadata_drift(
    valid_archive: tuple[Path, dict[str, object]],
    tmp_path: Path,
) -> None:
    archive, _ = valid_archive
    prefixed = tmp_path / "prefixed.zip"
    prefixed.write_bytes(b"SECRET-PREFIX" + archive.read_bytes())
    trailed = tmp_path / "trailed.zip"
    trailed.write_bytes(archive.read_bytes() + b"SECRET-TRAILER")

    commented = tmp_path / "commented.zip"
    _rewrite_archive(archive, commented, archive_comment=b"not canonical")
    compressed = tmp_path / "compressed.zip"
    _rewrite_archive(archive, compressed, compression=zipfile.ZIP_DEFLATED)
    symlink = tmp_path / "symlink.zip"
    _rewrite_archive(archive, symlink, mode=stat.S_IFLNK | 0o777)
    encrypted = tmp_path / "encrypted.zip"
    _set_encrypted_flag(archive, encrypted)

    package = verify_export(archive, today=AS_OF)["package"]
    assert isinstance(package, dict)
    archive_root = package["archive_root"]
    assert isinstance(archive_root, str)
    case_collision = tmp_path / "case-collision.zip"
    _rewrite_archive(
        archive,
        case_collision,
        extra=(f"{archive_root}/DATA/SOURCES.JSON", b"{}"),
    )

    for candidate in (
        prefixed,
        trailed,
        commented,
        compressed,
        symlink,
        encrypted,
        case_collision,
    ):
        with pytest.raises(ValueError):
            verify_export(candidate, today=AS_OF)


def test_verify_rejects_duplicate_unknown_and_duplicate_key_members(
    valid_archive: tuple[Path, dict[str, object]],
    tmp_path: Path,
) -> None:
    archive, manifest = valid_archive
    package = manifest["package"]
    assert isinstance(package, dict)
    root = package["archive_root"]
    assert isinstance(root, str)
    manifest_name = f"{root}/MANIFEST.json"

    duplicate = tmp_path / "duplicate.zip"
    with pytest.warns(UserWarning, match="Duplicate name"):
        _rewrite_archive(archive, duplicate, duplicate=manifest_name)
    unknown = tmp_path / "unknown.zip"
    _rewrite_archive(archive, unknown, extra=(f"{root}/data/extra.json", b"{}"))
    duplicate_key = tmp_path / "duplicate-key.zip"
    _rewrite_archive(
        archive,
        duplicate_key,
        replace={manifest_name: b'{"schema_version":1,"schema_version":1}'},
    )

    for candidate in (duplicate, unknown, duplicate_key):
        with pytest.raises(ValueError):
            verify_export(candidate, today=AS_OF)

    destination = tmp_path / "no-restore-on-invalid"
    with pytest.raises(ValueError):
        restore_export(unknown, destination, today=AS_OF)
    assert not destination.exists()


def test_restore_cleans_staging_after_loader_failure(
    valid_archive: tuple[Path, dict[str, object]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive, _ = valid_archive
    destination = tmp_path / "restore-failure"

    def fail_validation(*_args: object, **_kwargs: object) -> None:
        raise ValueError("intentional loader failure")

    monkeypatch.setattr(evidence_export, "validate_restored_evidence", fail_validation)
    with pytest.raises(ValueError, match="intentional loader failure"):
        restore_export(archive, destination, today=AS_OF)
    assert not destination.exists()
    assert not list(tmp_path.glob(f".{destination.name}.restore-*"))


def test_build_requires_head_pinned_profile_bytes(
    committed_evidence_root: Path,
    tmp_path: Path,
) -> None:
    altered = tmp_path / "altered"
    shutil.copytree(committed_evidence_root, altered)
    changed = altered / "data/demo-data.js"
    changed.write_bytes(changed.read_bytes() + b"\n")
    profile_path = altered / V2_PROFILE_PATH
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    entry = next(
        item for item in profile["entries"] if item["path"] == "data/demo-data.js"
    )
    entry["raw_sha256"] = "sha256:" + hashlib.sha256(changed.read_bytes()).hexdigest()
    profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    _git(altered, "add", V2_PROFILE_PATH.as_posix())
    _git(
        altered,
        "-c",
        "user.name=Codex",
        "-c",
        "user.email=codex@example.test",
        "commit",
        "-qm",
        "updated profile only",
    )

    with pytest.raises(ValueError, match="differs from the bound Git HEAD"):
        _build(altered, tmp_path / "rejected.zip")
    with pytest.raises(ValueError, match="does not match Git HEAD"):
        build_export(
            committed_evidence_root,
            tmp_path / "wrong-commit.zip",
            freeze_id=FREEZE_ID,
            frozen_on=FREEZE_ON,
            repository_commit_sha="0" * 40,
            today=AS_OF,
        )


def test_state_assertions_preserve_json_type_boundaries() -> None:
    profile = evidence_export.ExportProfile(
        package_id="test-package",
        archive_root="test-root",
        classification=("public", "synthetic"),
        claim_boundary="test boundary",
        exclusions=("test exclusion",),
        known_absences=("test absence",),
        entries=(),
        state_assertions=(
            evidence_export.StateAssertion(
                path="data/validation/state.json",
                pointer="/value",
                equals=True,
            ),
        ),
        profile_path="data/export/public-synthetic-evidence-v1.json",
    )
    with pytest.raises(ValueError, match="public/synthetic state drifted"):
        evidence_export._validate_state_assertions(
            profile,
            {"data/validation/state.json": b'{"value":1}'},
        )


def test_json_parser_rejects_nonstandard_constants_and_recursion() -> None:
    with pytest.raises(ValueError):
        evidence_export._read_json_bytes(b'{"value":NaN}', "manifest")
    nested = b"[" * 10_000 + b"]" * 10_000
    with pytest.raises(ValueError, match="invalid UTF-8 JSON"):
        evidence_export._read_json_bytes(nested, "manifest")


def test_verifier_enforces_member_and_archive_size_bounds(tmp_path: Path) -> None:
    too_many = tmp_path / "too-many.zip"
    with zipfile.ZipFile(too_many, "w", compression=zipfile.ZIP_STORED) as archive:
        for index in range(129):
            archive.writestr(_canonical_info(f"bounded/{index:03d}"), b"x")
    with pytest.raises(ValueError, match="member count"):
        verify_export(too_many, today=AS_OF)

    too_large_member = tmp_path / "too-large-member.zip"
    with zipfile.ZipFile(
        too_large_member,
        "w",
        compression=zipfile.ZIP_STORED,
        allowZip64=False,
    ) as archive:
        archive.writestr(
            _canonical_info("bounded/MANIFEST.json"),
            b"x" * (16 * 1024 * 1024 + 1),
        )
    with pytest.raises(ValueError, match="size limit"):
        verify_export(too_large_member, today=AS_OF)

    oversized_archive = tmp_path / "oversized.zip"
    oversized_archive.write_bytes(b"x" * (32 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="size limit"):
        verify_export(oversized_archive, today=AS_OF)


def test_build_refuses_existing_or_repository_output(
    committed_evidence_root: Path,
    tmp_path: Path,
) -> None:
    existing = tmp_path / "exists.zip"
    existing.write_bytes(b"existing")
    with pytest.raises(ValueError, match="refusing to overwrite"):
        _build(committed_evidence_root, existing)
    with pytest.raises(ValueError, match="outside the repository root"):
        _build(committed_evidence_root, committed_evidence_root / "evidence.zip")


def test_cli_returns_two_without_traceback_for_malformed_archives(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    malformed = tmp_path / "malformed.zip"
    malformed.write_bytes(b"not a zip archive")

    assert evidence_export_main(["verify", "--archive", str(malformed)]) == 2
    captured = capsys.readouterr()
    assert "evidence export: invalid input or output:" in captured.err
    assert "Traceback" not in captured.err


def test_cli_build_verify_restore_round_trip(
    committed_evidence_root: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    archive = tmp_path / "cli-evidence.zip"
    destination = tmp_path / "cli-restored"
    build_args = [
        "build",
        "--root",
        str(committed_evidence_root),
        "--output",
        str(archive),
        "--freeze-id",
        FREEZE_ID,
        "--frozen-on",
        FREEZE_ON,
    ]
    assert evidence_export_main(build_args) == 0
    built = json.loads(capsys.readouterr().out)
    assert built["freeze"]["repository_commit_sha"] == _commit_sha(
        committed_evidence_root
    )

    assert evidence_export_main(["verify", "--archive", str(archive)]) == 0
    assert (
        json.loads(capsys.readouterr().out)["tree_fingerprint"]
        == built["tree_fingerprint"]
    )
    assert (
        evidence_export_main(
            ["restore", "--archive", str(archive), "--destination", str(destination)]
        )
        == 0
    )
    capsys.readouterr()
    assert (destination / "MANIFEST.json").is_file()


def test_cli_build_can_explicitly_select_frozen_v1_contract(
    legacy_v1_evidence_root: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    archive = tmp_path / "cli-v1-evidence.zip"
    assert (
        evidence_export_main(
            [
                "build",
                "--root",
                str(legacy_v1_evidence_root),
                "--output",
                str(archive),
                "--freeze-id",
                FREEZE_ID,
                "--frozen-on",
                FREEZE_ON,
                "--profile-version",
                "1",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["schema_version"] == 1


def test_profile_requires_the_source_registry_entry() -> None:
    profile_path = REPOSITORY_ROOT / "data/export/public-synthetic-evidence-v1.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    missing = dict(profile)
    missing["entries"] = [
        entry for entry in profile["entries"] if entry["path"] != "data/sources.json"
    ]
    with pytest.raises(ValueError, match="must be the source registry"):
        evidence_export._parse_profile(
            missing, profile_path.relative_to(REPOSITORY_ROOT).as_posix()
        )

    wrong_role = json.loads(json.dumps(profile))
    source_entry = next(
        entry for entry in wrong_role["entries"] if entry["path"] == "data/sources.json"
    )
    source_entry["role"] = "rule_index"
    with pytest.raises(ValueError, match="must be the source registry"):
        evidence_export._parse_profile(
            wrong_role,
            profile_path.relative_to(REPOSITORY_ROOT).as_posix(),
        )


def test_profile_requires_the_workflow_registry_entry() -> None:
    profile_path = REPOSITORY_ROOT / V2_PROFILE_PATH
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    missing = dict(profile)
    missing["entries"] = [
        entry
        for entry in profile["entries"]
        if entry["path"] != "data/workflows/registry.json"
    ]
    with pytest.raises(ValueError, match="must be the workflow registry"):
        evidence_export._parse_profile(
            missing,
            profile_path.relative_to(REPOSITORY_ROOT).as_posix(),
        )

    wrong_role = json.loads(json.dumps(profile))
    workflow_entry = next(
        entry
        for entry in wrong_role["entries"]
        if entry["path"] == "data/workflows/registry.json"
    )
    workflow_entry["role"] = "jurisdiction_registry"
    with pytest.raises(ValueError, match="must be the workflow registry"):
        evidence_export._parse_profile(
            wrong_role,
            profile_path.relative_to(REPOSITORY_ROOT).as_posix(),
        )


@pytest.mark.parametrize(
    "missing_path",
    [
        "data/readiness/workflows/woodland-preapproved-detached-adu.json",
        "data/readiness/generated/woodland-preapproved-adu-evidence.json",
        "data/journeys/generated/woodland-preapproved-detached-adu.json",
    ],
)
def test_v2_profile_requires_registry_input_and_output_closure(
    missing_path: str,
) -> None:
    profile = load_export_profile(REPOSITORY_ROOT, profile_version=2)
    payloads = evidence_export._entry_payloads(REPOSITORY_ROOT, profile)
    incomplete = replace(
        profile,
        entries=tuple(entry for entry in profile.entries if entry.path != missing_path),
    )
    payloads.pop(missing_path)
    with pytest.raises(
        ValueError, match="referenced workflow artifact is not exported"
    ):
        evidence_export._validate_workflow_registry_closure(incomplete, payloads)


def test_profile_and_manifest_require_exact_schema_values(
    valid_archive: tuple[Path, dict[str, object]],
) -> None:
    _, manifest = valid_archive
    padded_manifest = json.loads(json.dumps(manifest))
    padded_manifest["freeze"]["freeze_id"] = f" {FREEZE_ID} "
    with pytest.raises(ValueError, match="exact non-blank text"):
        evidence_export._parse_manifest(padded_manifest, today=AS_OF)

    boolean_manifest = json.loads(json.dumps(manifest))
    boolean_manifest["schema_version"] = True
    with pytest.raises(ValueError, match="schema_version"):
        evidence_export._parse_manifest(boolean_manifest, today=AS_OF)

    profile_path = REPOSITORY_ROOT / "data/export/public-synthetic-evidence-v1.json"
    boolean_profile = json.loads(profile_path.read_text(encoding="utf-8"))
    boolean_profile["schema_version"] = True
    with pytest.raises(ValueError, match="schema_version"):
        evidence_export._parse_profile(
            boolean_profile,
            profile_path.relative_to(REPOSITORY_ROOT).as_posix(),
        )


def test_profile_rejects_unknown_artifact_roles() -> None:
    profile_path = REPOSITORY_ROOT / "data/export/public-synthetic-evidence-v1.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile["entries"][0]["role"] = "unbounded_new_role"
    with pytest.raises(ValueError, match="invalid artifact role"):
        evidence_export._parse_profile(
            profile,
            profile_path.relative_to(REPOSITORY_ROOT).as_posix(),
        )


def test_build_rejects_future_freeze_dates(
    committed_evidence_root: Path,
    tmp_path: Path,
) -> None:
    output = tmp_path / "future.zip"
    with pytest.raises(ValueError, match="future dates"):
        build_export(
            committed_evidence_root,
            output,
            freeze_id=FREEZE_ID,
            frozen_on="2026-08-10",
            repository_commit_sha=_commit_sha(committed_evidence_root),
            today=AS_OF,
        )
    assert not output.exists()


def test_verifier_rejects_raw_payload_tampering(
    valid_archive: tuple[Path, dict[str, object]],
    tmp_path: Path,
) -> None:
    archive, manifest = valid_archive
    package = manifest["package"]
    assert isinstance(package, dict)
    archive_root = package["archive_root"]
    assert isinstance(archive_root, str)
    tampered = tmp_path / "tampered.zip"
    member_name = f"{archive_root}/data/demo-data.js"
    with zipfile.ZipFile(archive) as contents:
        replacement = b"x" * len(contents.read(member_name))
    _rewrite_archive(
        archive,
        tampered,
        replace={member_name: replacement},
    )
    with pytest.raises(ValueError, match="raw SHA-256"):
        verify_export(tampered, today=AS_OF)
