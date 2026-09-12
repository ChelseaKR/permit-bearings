"""Authenticity for the portable evidence package (issue #137).

`evidence_export` proves an archive is internally consistent. These tests pin
what a detached signature adds and, more importantly, what it never does: an
unsigned archive is reported ``absent``, never inferred valid; a signature no
one asked to check is ``not_checked``, never ``verified``; and a signer absent
from the supplied signers file is told apart from a signature that does not
check out, because the two call for different responses.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import date, timedelta
from pathlib import Path

import pytest
from tests.attestation_clock import frozen_today

from permit_pathways.evidence_export import build_export, load_export_profile
from permit_pathways.evidence_export_cli import main as evidence_export_main
from permit_pathways.evidence_signature import (
    SignatureState,
    archive_digest,
    check_signature,
    sidecar_path,
    sign_archive,
    statement_matches_manifest,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
# The archive carries the Woodland attestation, and `validate_restored_evidence`
# replays every record against the manifest's own `frozen_on`. An archive
# therefore cannot be frozen before the day that page was checked, so the
# freeze is read from the record instead of written out here.
AS_OF = frozen_today()
FREEZE_ON = AS_OF.isoformat()
FREEZE_ID = f"public-synthetic-evidence-freeze-{FREEZE_ON}"
OTHER_FREEZE_ON = (AS_OF + timedelta(days=1)).isoformat()
SIGNER = "evidence-signing-test@example.invalid"
OTHER_SIGNER = "someone-else@example.invalid"

pytestmark = pytest.mark.skipif(
    shutil.which("ssh-keygen") is None,
    reason="evidence-package signing needs OpenSSH's ssh-keygen",
)


def _git(root: Path, *args: str) -> str:
    executable = shutil.which("git")
    assert executable is not None, "Git is required for evidence export tests"
    return subprocess.run(
        [executable, "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


@pytest.fixture(scope="module")
def committed_evidence_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A minimal committed repository holding exactly the profile's file set."""

    root = tmp_path_factory.mktemp("signed-evidence-repository")
    profile = load_export_profile(REPOSITORY_ROOT)
    for entry in profile.entries:
        source = REPOSITORY_ROOT / entry.path
        target = root / entry.path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    profile_source = REPOSITORY_ROOT / profile.profile_path
    profile_target = root / profile.profile_path
    profile_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(profile_source, profile_target)
    _git(root, "init", "--quiet")
    _git(root, "config", "user.email", "tests@example.invalid")
    _git(root, "config", "user.name", "Evidence signature tests")
    _git(root, "add", "--all")
    _git(root, "commit", "--quiet", "--message", "evidence set")
    return root


def _keypair(directory: Path, name: str, comment: str) -> Path:
    executable = shutil.which("ssh-keygen")
    assert executable is not None
    private = directory / name
    subprocess.run(
        [
            executable,
            "-q",
            "-t",
            "ed25519",
            "-N",
            "",
            "-C",
            comment,
            "-f",
            str(private),
        ],
        check=True,
        capture_output=True,
    )
    return private


def _signers_file(directory: Path, name: str, entries: list[tuple[str, Path]]) -> Path:
    path = directory / name
    lines = []
    for principal, private in entries:
        public = private.with_suffix(private.suffix + ".pub").read_text().split()
        lines.append(f"{principal} {public[0]} {public[1]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def signing_key(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _keypair(tmp_path_factory.mktemp("evidence-keys"), "signer", SIGNER)


@pytest.fixture(scope="module")
def other_key(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _keypair(
        tmp_path_factory.mktemp("evidence-other-keys"), "other", OTHER_SIGNER
    )


def _build(root: Path, output: Path) -> dict[str, object]:
    return build_export(
        root,
        output,
        freeze_id=FREEZE_ID,
        frozen_on=FREEZE_ON,
        repository_commit_sha=_git(root, "rev-parse", "HEAD").strip(),
        today=AS_OF,
    )


@pytest.fixture(scope="module")
def signed_archive(
    committed_evidence_root: Path,
    signing_key: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, dict[str, object]]:
    output = tmp_path_factory.mktemp("signed-archive") / "evidence.zip"
    manifest = _build(committed_evidence_root, output)
    sign_archive(output, manifest, key_path=signing_key)
    return output, manifest


def test_signing_leaves_the_archive_bytes_untouched(
    committed_evidence_root: Path, signing_key: Path, tmp_path: Path
) -> None:
    # The determinism gate is the point: a signature that changed the archive
    # would break byte-for-byte reproduction, so it goes in a sidecar.
    unsigned = tmp_path / "unsigned.zip"
    signed = tmp_path / "signed.zip"
    _build(committed_evidence_root, unsigned)
    manifest = _build(committed_evidence_root, signed)
    before = signed.read_bytes()
    sign_archive(signed, manifest, key_path=signing_key)
    assert signed.read_bytes() == before
    assert unsigned.read_bytes() == before
    assert sidecar_path(signed).is_file()
    assert not sidecar_path(unsigned).exists()


def test_a_signed_archive_verifies_against_a_signers_file_that_lists_it(
    signed_archive: tuple[Path, dict[str, object]],
    signing_key: Path,
    tmp_path: Path,
) -> None:
    archive, manifest = signed_archive
    signers = _signers_file(tmp_path, "allowed_signers", [(SIGNER, signing_key)])
    status = check_signature(archive, manifest, allowed_signers=signers)
    assert status.state == SignatureState.VERIFIED
    assert status.signer == SIGNER
    assert status.archive_sha256 == archive_digest(archive)
    assert statement_matches_manifest(status, manifest)


def test_a_signer_the_file_does_not_list_is_not_reported_as_a_broken_signature(
    signed_archive: tuple[Path, dict[str, object]],
    other_key: Path,
    tmp_path: Path,
) -> None:
    # OpenSSH prints the same message for both, and the two mean different
    # things to a partner: "we do not accept this producer" versus "these bytes
    # are not what was signed".
    archive, manifest = signed_archive
    signers = _signers_file(tmp_path, "others", [(OTHER_SIGNER, other_key)])
    status = check_signature(archive, manifest, allowed_signers=signers)
    assert status.state == SignatureState.UNKNOWN_SIGNER
    assert SIGNER in status.detail


def test_a_signature_by_another_key_under_a_listed_name_does_not_verify(
    committed_evidence_root: Path,
    signing_key: Path,
    other_key: Path,
    tmp_path: Path,
) -> None:
    # The principal in the sidecar is a claim about which line applies, never a
    # credential: signing with a different key while naming a listed principal
    # must fail.
    archive = tmp_path / "impersonated.zip"
    manifest = _build(committed_evidence_root, archive)
    sign_archive(archive, manifest, key_path=other_key, signer_identity=SIGNER)
    signers = _signers_file(tmp_path, "allowed_signers", [(SIGNER, signing_key)])
    status = check_signature(archive, manifest, allowed_signers=signers)
    assert status.state == SignatureState.INVALID


def test_an_unsigned_archive_is_absent_and_never_inferred_valid(
    committed_evidence_root: Path, tmp_path: Path
) -> None:
    archive = tmp_path / "unsigned.zip"
    manifest = _build(committed_evidence_root, archive)
    status = check_signature(archive, manifest)
    assert status.state == SignatureState.ABSENT
    assert not status.is_verified
    assert "say nothing about who produced it" in status.detail


def test_a_present_signature_nobody_asked_to_check_is_not_verified(
    signed_archive: tuple[Path, dict[str, object]],
) -> None:
    # The state that would be easiest to get wrong: a signature is there, so it
    # is tempting to call it good. Without a signers file nothing was checked.
    archive, manifest = signed_archive
    status = check_signature(archive, manifest)
    assert status.state == SignatureState.NOT_CHECKED
    assert not status.is_verified


def test_an_empty_signers_file_accepts_nobody(
    signed_archive: tuple[Path, dict[str, object]], tmp_path: Path
) -> None:
    # "No patterns to compare against" must not read as "cannot tell, allow".
    archive, manifest = signed_archive
    empty = tmp_path / "empty_signers"
    empty.write_text("# only a comment\n", encoding="utf-8")
    status = check_signature(archive, manifest, allowed_signers=empty)
    assert status.state == SignatureState.UNKNOWN_SIGNER


def test_a_negated_principal_vetoes_a_wildcard_that_would_match(
    signed_archive: tuple[Path, dict[str, object]],
    signing_key: Path,
    tmp_path: Path,
) -> None:
    archive, manifest = signed_archive
    public = signing_key.with_suffix(signing_key.suffix + ".pub").read_text().split()
    signers = tmp_path / "negated_signers"
    signers.write_text(
        f"!{SIGNER},*@example.invalid {public[0]} {public[1]}\n", encoding="utf-8"
    )
    status = check_signature(archive, manifest, allowed_signers=signers)
    assert status.state == SignatureState.UNKNOWN_SIGNER


def test_one_altered_byte_is_reported_as_a_broken_signature(
    signed_archive: tuple[Path, dict[str, object]],
    signing_key: Path,
    tmp_path: Path,
) -> None:
    archive, manifest = signed_archive
    tampered = tmp_path / "tampered.zip"
    payload = bytearray(archive.read_bytes())
    payload[5000] ^= 0xFF
    tampered.write_bytes(bytes(payload))
    shutil.copy2(sidecar_path(archive), sidecar_path(tampered))
    signers = _signers_file(tmp_path, "allowed_signers", [(SIGNER, signing_key)])
    status = check_signature(tampered, manifest, allowed_signers=signers)
    assert status.state == SignatureState.INVALID
    assert "different archive digest" in status.detail


def test_a_signature_from_another_freeze_does_not_transfer(
    committed_evidence_root: Path,
    signed_archive: tuple[Path, dict[str, object]],
    signing_key: Path,
    tmp_path: Path,
) -> None:
    # A validly signed sidecar moved next to a different package must not
    # verify: the statement names the digest it covers.
    archive, _manifest = signed_archive
    other = tmp_path / "other.zip"
    other_manifest = build_export(
        committed_evidence_root,
        other,
        freeze_id=f"public-synthetic-evidence-freeze-{OTHER_FREEZE_ON}",
        frozen_on=OTHER_FREEZE_ON,
        repository_commit_sha=_git(
            committed_evidence_root, "rev-parse", "HEAD"
        ).strip(),
        today=date.fromisoformat(OTHER_FREEZE_ON),
    )
    shutil.copy2(sidecar_path(archive), sidecar_path(other))
    signers = _signers_file(tmp_path, "allowed_signers", [(SIGNER, signing_key)])
    status = check_signature(other, other_manifest, allowed_signers=signers)
    assert status.state == SignatureState.INVALID


def test_a_malformed_sidecar_is_reported_rather_than_ignored(
    committed_evidence_root: Path, tmp_path: Path
) -> None:
    archive = tmp_path / "malformed.zip"
    manifest = _build(committed_evidence_root, archive)
    sidecar_path(archive).write_text("{not json", encoding="utf-8")
    status = check_signature(archive, manifest)
    assert status.state == SignatureState.MALFORMED
    assert not status.is_verified


def test_signing_refuses_to_overwrite_an_existing_signature(
    committed_evidence_root: Path, signing_key: Path, tmp_path: Path
) -> None:
    archive = tmp_path / "twice.zip"
    manifest = _build(committed_evidence_root, archive)
    sign_archive(archive, manifest, key_path=signing_key)
    with pytest.raises(ValueError, match="existing signature"):
        sign_archive(archive, manifest, key_path=signing_key)


# --- The command line ---------------------------------------------------


def _build_argv(root: Path, archive: Path, *extra: str) -> list[str]:
    return [
        "build",
        "--root",
        str(root),
        "--output",
        str(archive),
        "--freeze-id",
        FREEZE_ID,
        "--frozen-on",
        FREEZE_ON,
        *extra,
    ]


def test_cli_signed_round_trip_and_its_three_failure_codes(
    committed_evidence_root: Path,
    signing_key: Path,
    other_key: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    archive = tmp_path / "cli-signed.zip"
    assert (
        evidence_export_main(
            _build_argv(
                committed_evidence_root, archive, "--sign-key", str(signing_key)
            )
        )
        == 0
    )
    built = json.loads(capsys.readouterr().out)
    assert built["signature"]["state"] == SignatureState.NOT_CHECKED

    signers = _signers_file(tmp_path, "allowed_signers", [(SIGNER, signing_key)])
    assert (
        evidence_export_main(
            ["verify", "--archive", str(archive), "--allowed-signers", str(signers)]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["signature"]["state"] == (
        SignatureState.VERIFIED
    )

    # Unsigned, with authenticity demanded.
    unsigned = tmp_path / "cli-unsigned.zip"
    assert evidence_export_main(_build_argv(committed_evidence_root, unsigned)) == 0
    capsys.readouterr()
    assert (
        evidence_export_main(
            ["verify", "--archive", str(unsigned), "--allowed-signers", str(signers)]
        )
        == 3
    )
    capsys.readouterr()

    # Signed by a key the file does not list.
    unlisted = tmp_path / "cli-unlisted.zip"
    manifest = _build(committed_evidence_root, unlisted)
    sign_archive(unlisted, manifest, key_path=other_key)
    assert (
        evidence_export_main(
            ["verify", "--archive", str(unlisted), "--allowed-signers", str(signers)]
        )
        == 5
    )
    capsys.readouterr()

    # A signature over bytes that changed.
    tampered = tmp_path / "cli-tampered.zip"
    payload = bytearray(archive.read_bytes())
    payload[5000] ^= 0xFF
    tampered.write_bytes(bytes(payload))
    shutil.copy2(sidecar_path(archive), sidecar_path(tampered))
    assert (
        evidence_export_main(
            ["verify", "--archive", str(tampered), "--allowed-signers", str(signers)]
        )
        == 4
    )
    capsys.readouterr()


def test_cli_verify_without_a_signers_file_still_passes_an_unsigned_archive(
    committed_evidence_root: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # The complement of the gating tests. If the only effect of this change
    # were to fail unsigned archives, every existing unsigned package and every
    # `make evidence-export-check` run would break. They do not.
    archive = tmp_path / "cli-plain.zip"
    assert evidence_export_main(_build_argv(committed_evidence_root, archive)) == 0
    capsys.readouterr()
    assert evidence_export_main(["verify", "--archive", str(archive)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["signature"]["state"] == SignatureState.ABSENT
    assert payload["tree_fingerprint"]


def test_cli_restore_honours_the_same_authenticity_demand(
    committed_evidence_root: Path,
    signing_key: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    archive = tmp_path / "cli-restore.zip"
    manifest = _build(committed_evidence_root, archive)
    sign_archive(archive, manifest, key_path=signing_key)
    signers = _signers_file(tmp_path, "allowed_signers", [(SIGNER, signing_key)])
    destination = tmp_path / "restored"
    assert (
        evidence_export_main(
            [
                "restore",
                "--archive",
                str(archive),
                "--destination",
                str(destination),
                "--allowed-signers",
                str(signers),
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert (destination / "MANIFEST.json").is_file()

    unsigned = tmp_path / "cli-restore-unsigned.zip"
    _build(committed_evidence_root, unsigned)
    refused = tmp_path / "not-restored"
    assert (
        evidence_export_main(
            [
                "restore",
                "--archive",
                str(unsigned),
                "--destination",
                str(refused),
                "--allowed-signers",
                str(signers),
            ]
        )
        == 3
    )
    capsys.readouterr()
    # The refusal happens before the archive is opened, so nothing is published.
    assert not refused.exists()


def test_cli_use_repository_signers_needs_the_file_to_exist(
    committed_evidence_root: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    archive = tmp_path / "cli-repo-signers.zip"
    assert evidence_export_main(_build_argv(committed_evidence_root, archive)) == 0
    capsys.readouterr()
    assert (
        evidence_export_main(
            [
                "verify",
                "--archive",
                str(archive),
                "--use-repository-signers",
                "--root",
                str(committed_evidence_root),
            ]
        )
        == 2
    )
    assert "allowed_signers" in capsys.readouterr().err


def test_a_signed_statement_that_names_a_different_package_does_not_verify(
    signed_archive: tuple[Path, dict[str, object]],
    signing_key: Path,
    tmp_path: Path,
) -> None:
    # The manifest cross-check is defence in depth and unreachable for a
    # well-formed archive -- the manifest is *inside* the archive, so a matching
    # digest already implies a matching manifest. Exercised directly so it is
    # not a branch that cannot fail: hand the same archive a manifest it does
    # not describe.
    archive, manifest = signed_archive
    signers = _signers_file(tmp_path, "allowed_signers", [(SIGNER, signing_key)])
    substituted = json.loads(json.dumps(manifest))
    substituted["freeze"]["freeze_id"] = "some-other-freeze"
    status = check_signature(archive, substituted, allowed_signers=signers)
    assert status.state == SignatureState.INVALID
    assert "different freeze or profile" in status.detail
    # And the unsubstituted manifest still verifies, so the check is not simply
    # rejecting everything.
    assert (
        check_signature(archive, manifest, allowed_signers=signers).state
        == SignatureState.VERIFIED
    )
