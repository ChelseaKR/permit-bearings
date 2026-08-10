# Public/synthetic evidence export and restore

Status: implemented tooling for a frozen 58-file schema-v1 compatibility
profile and a registry-aware 59-file schema-v2 public/synthetic profile. These
are not exhaustive exports of later repository artifacts. This is not a
production applicant-data export, a backup system, a contractual offboarding
procedure, partner acceptance, or a beta result.

## What the package proves

Each package is a deterministic, standard ZIP containing only the files named
by its versioned profile. Schema v1 retains the exact pre-workflow-registry
58-file identity in
[`public-synthetic-evidence-v1.json`](../data/export/public-synthetic-evidence-v1.json).
Schema v2 has 59 files, replaces the self-referential profile member with
[`public-synthetic-evidence-v2.json`](../data/export/public-synthetic-evidence-v2.json),
and adds the raw-byte-pinned workflow registry; its other artifact membership
matches v1.
The manifest binds the exact Git commit, freeze ID and date, artifact roles,
raw byte counts and SHA-256 digests, the profile digest, a tree fingerprint,
the public/synthetic claim boundary, known absences, and official source
records that do not have a retained local copy.

Build and restore also replay the repository's strict source, rule, Golden,
readiness, journey, program-availability, rule-review, conformance, and
jurisdiction loaders. Schema v1 retains its original fixed Woodland artifact
paths. Schema v2 loads the versioned registry and rejects a profile unless it
exports every input and generated output referenced by every registry entry.
The readiness and journey artifacts are replayed using their recorded
evaluation date; the package freeze date does not rewrite the historical
evaluation.

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
  --profile-version 2 \
  --output /absolute/new/path/permit-bearings-evidence.zip \
  --freeze-id public-synthetic-evidence-2026-08-09 \
  --frozen-on 2026-08-09

PYTHONPATH=src python3 -m permit_pathways.evidence_export_cli verify \
  --archive /absolute/new/path/permit-bearings-evidence.zip

PYTHONPATH=src python3 -m permit_pathways.evidence_export_cli restore \
  --archive /absolute/new/path/permit-bearings-evidence.zip \
  --destination /absolute/new/path/restored-evidence
```

The build command auto-selects the newest profile present (schema v2 in the
current repository and schema v1 in a legacy v1-only root) and accepts an
explicit `--profile-version 1` or `--profile-version 2`. The frozen v1 profile
is kept for archive compatibility; a new v1 build correctly fails when any
current selected byte no longer matches its historical pin. Verify and restore
infer the version from the archive manifest and do not need a selector. The
optional `--repository-commit-sha` argument is accepted only when it is the full
lowercase SHA of the verified `HEAD`. The destination must not exist; there is
no merge or force mode. Each successful command prints the validated manifest
as JSON. `make evidence-export-check` performs a disposable schema-v2
build/verify/restore round trip.

Build and verify use cross-platform Python standard-library formats. Restore
currently publishes with the operating system's no-replace directory
rename on macOS or Linux and fails closed elsewhere; the restored evidence
bytes remain ordinary files in either case.

The manifest and tree hashes are integrity records, not digital signatures.
For a handoff, record the whole archive's SHA-256 through a trusted channel,
for example with `shasum -a 256`, and keep that receipt outside the archive.
Signing and partner acceptance remain separate future controls.

## Canonical and fail-closed format

Each supported schema intentionally has one representation:

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

The frozen v1 profile includes its selected official/public source copies,
portable rules and sources, Golden and conformance development fixtures,
synthetic Woodland readiness and journey records, jurisdiction/HCD snapshots,
generated evidence, prepared validation ledgers, the repository license,
third-party notices, and provenance record. V2 adds only the raw-byte-pinned
workflow registry and requires closure over that registry's referenced
workflow inputs and outputs. This is a portable membership guarantee, not
evidence that another jurisdiction is implemented, reviewed, or approved.

The later `data/conformance/evaluations/heldout-v1/manifest.json`, its evaluator
and CLI, the beta-operations ADR/runbook/ledger/validator/tests, and any future
frozen cases, answer key, blind predictions, execution or approval receipts,
or results are outside export profiles v1 and v2. Exporting those artifacts requires a
separately reviewed future profile/version with an updated membership,
classification, and claim boundary; their presence elsewhere in the repository
does not make either package incomplete against its own pinned contract.

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
