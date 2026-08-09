# Public/synthetic evidence export and restore

Status: implemented tooling for the repository's current public and synthetic
evidence set. This is not a production applicant-data export, a backup system,
a contractual offboarding procedure, partner acceptance, or a beta result.

## What the package proves

The schema-v1 package is a deterministic, standard ZIP containing only the
files named by
[`public-synthetic-evidence-v1.json`](../data/export/public-synthetic-evidence-v1.json).
Its manifest binds the exact Git commit, freeze ID and date, artifact roles,
raw byte counts and SHA-256 digests, the profile digest, a tree fingerprint,
the public/synthetic claim boundary, known absences, and official source
records that do not have a retained local copy.

Build and restore also replay the repository's strict source, rule, Golden,
readiness, journey, program-availability, rule-review, conformance, and
jurisdiction loaders. The readiness and journey artifacts are replayed using
their recorded evaluation date; the package freeze date does not rewrite the
historical evaluation.

A successful result proves that the named public/synthetic bytes can be
packaged, independently checked, and restored without a vendor database. It
does not prove legal or content accuracy, source currency, human review,
jurisdiction approval, applicant comprehension, accessibility signoff,
completeness, compliance, eligibility, approval, authenticity, or ownership
of third-party source material.

## Build, verify, and restore

For `build`, the selected profile files must be tracked and byte-identical to
Git `HEAD`. Unrelated working-tree changes are ignored. The output archive must
be outside the repository and must not already exist. Archive-only `verify`
and `restore` do not need a repository; they validate the recorded full commit
identifier and all internal bindings, but do not retrieve or authenticate that
commit.

```bash
PYTHONPATH=src python3 -m permit_pathways.evidence_export_cli build \
  --output /absolute/new/path/permit-bearings-evidence.zip \
  --freeze-id public-synthetic-evidence-2026-08-09 \
  --frozen-on 2026-08-09

PYTHONPATH=src python3 -m permit_pathways.evidence_export_cli verify \
  --archive /absolute/new/path/permit-bearings-evidence.zip

PYTHONPATH=src python3 -m permit_pathways.evidence_export_cli restore \
  --archive /absolute/new/path/permit-bearings-evidence.zip \
  --destination /absolute/new/path/restored-evidence
```

The optional `--repository-commit-sha` argument is accepted only when it is
the full lowercase SHA of the verified `HEAD`. The destination must not exist;
there is no merge or force mode. Each successful command prints the validated
manifest as JSON. `make evidence-export-check` performs a disposable
build/verify/restore round trip for the current committed profile.

Build and verify use cross-platform Python standard-library formats. Schema-v1
restore currently publishes with the operating system's no-replace directory
rename on macOS or Linux and fails closed elsewhere; the restored evidence
bytes remain ordinary files in either case.

The manifest and tree hashes are integrity records, not digital signatures.
For a handoff, record the whole archive's SHA-256 through a trusted channel,
for example with `shasum -a 256`, and keep that receipt outside the archive.
Signing and partner acceptance remain separate future controls.

## Canonical and fail-closed format

Schema v1 intentionally has one representation:

- stored, uncompressed members only, with ZIP64 disabled;
- one fixed archive root and one canonical `MANIFEST.json`;
- sorted ASCII POSIX paths, fixed 1980 timestamps, regular `0644` file modes,
  and no directory records, comments, encryption, extra fields, prefixes, or
  trailing bytes;
- at most 128 members, 16 MiB per member, and 32 MiB for the archive and
  declared payload; and
- byte-for-byte reconstruction during verification.

The verifier rejects missing, unknown, duplicate, case-colliding, unsafe,
compressed, encrypted, oversized, malformed, or tampered members. Nested
public source archives such as the Unitrans GTFS file are treated as opaque
bytes and are never recursively extracted.

Restore never calls ZIP extraction helpers. It validates the complete archive,
streams files into a private sibling staging directory, rechecks hashes and
canonical loaders, and publishes the restored directory only after all checks
pass. On failure, the command does not create, merge into, overwrite, or remove
the requested target; a target created concurrently by another process remains
untouched. Restore does not adopt source state, clear a hold, promote a review
level, invoke Git against or adopt records into the originating repository, or
publish guidance.

## Privacy and evidence boundary

The exact profile includes the current official/public source copies,
portable rules and sources, Golden and conformance development fixtures,
synthetic Woodland readiness and journey records, jurisdiction/HCD snapshots,
generated evidence, and the prepared validation ledgers. It also includes the
repository license, third-party notices, and provenance record.

Every payload except the self-referential profile is pinned by its raw digest.
Public-state assertions additionally require the mutable validation records
to remain pending, prepared, or `not_run`, with key private evidence and
execution fields empty. A later filled reviewer, participant, accessibility,
language, partner, or maintenance record therefore stops this profile until a
person deliberately classifies and revises the export boundary.

The package excludes applicant submissions, permit files, accounts, uploads,
telemetry, model-provider payloads, contact or identity mappings, private
review receipts, credentials, portal/submission material, Git metadata,
caches, environments, dependencies, and every unlisted local file. It does
not implement retention, deletion, legal hold, exemption handling, CPRA
search/export, encrypted transfer, access control, disaster recovery, or a
sensitive-data export. Those require a deployment-specific records, privacy,
security, and authorization design.

## Maintenance rule

Any selected file change requires an explicit profile digest refresh and
review. Generated files must first pass their normal bundle and fingerprint
checks. A new profile version is required when membership, classification,
privacy posture, archive format, or claim boundary changes. Never broaden this
ordinary ZIP profile to applicant, reviewer, participant, or other sensitive
records.
