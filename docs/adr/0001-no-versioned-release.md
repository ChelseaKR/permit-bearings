# Keep the showcase outside the versioned-release pipeline

- Status: Accepted
- Date: 2026-07-29
- Decider: Chelsea Kelly-Reif

## Context

The repository publishes a static showcase from the default branch but does
not publish a Python distribution, container, reusable action, signed tag, or
other versioned artifact. Its `0.0.1` project value is packaging metadata, not
an announced release, and there are no SemVer tags.

## Decision

The portfolio Release & Versioning standard is N/A for the current
branch-deployed showcase. Do not add a decorative release workflow merely to
make a presence check green. Before the project publishes any versioned
artifact, replace this decision with the standards-compliant signed-tag,
SBOM, provenance, changelog, and immutable-publication path.

## Consequences

`CHANGELOG.md` maintains an `[Unreleased]` record. The branch deployment still
requires CI, security, accessibility, and responsible-technology controls.
This N/A expires as soon as a versioned artifact is offered to another user.
