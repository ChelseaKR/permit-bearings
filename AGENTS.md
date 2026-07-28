# Repository agent instructions

## Read first

Before changing product behavior or public claims, read:

1. `docs/PRODUCT-CONTEXT.md` — product thesis, capability truth, priorities,
   and open questions.
2. `README.md` — public description and runnable surface.
3. `docs/DESIGN.md` — architecture and implementation boundaries.
4. `PROVENANCE.md` — origin and source constraints.

This repository supports a public-sector permitting showcase. Trustworthy
scope and evidence are product behavior, not editorial polish.

## Product objective and scope

Permit Pathways is an auditable decision-support and verification layer for
California housing permitting. Its primary wedge is Scenario A: help an
applicant identify a candidate route and reach a complete, well-routed
submission. Scenario C is the assurance layer underneath that experience:
source currency, provenance, dependency tracking, and re-verification.

Scenario B is an expansion area, not a v1 commitment. Prefer depth for one
real applicant workflow and one local jurisdiction over shallow coverage of
many statutes, jurisdictions, or staff workflows.

Never position the system as legal advice, a compliance certification, an
approval, or an authoritative source of law.

## Capability and claim discipline

Use these labels consistently:

- **Implemented** — executable code/data exists, is testable, and is exposed
  by a documented interface.
- **Prototype** — executable in a bounded corpus, sample, simulation, or
  manual workflow; production breadth is not established.
- **Planned** — a design direction with no executable end-to-end path.
- **Not targeted** — intentionally outside the current scope.

A claim inherits the lowest status of its required parts. Link important
claims to a test, data artifact, or runnable path. Do not convert aspirations
in `docs/DESIGN.md` into present-tense README or demo claims.

Keep these distinctions explicit:

- A statewide baseline is not a locally encoded jurisdiction.
- A typical-document hint is not packet-level completeness validation.
- Structured intake-to-rule fixtures are not natural-language answer or
  citation evaluations.
- A source-change rehearsal is not a durable production review queue.
- Interface localization is not translated source-derived guidance.
- A presence-based text screen is not a compliance determination and cannot
  prove that required language is present.
- A source-linked rule is not necessarily human-reviewed,
  jurisdiction-approved, or counsel-approved.
- A candidate transit or pathway result is not a final eligibility finding.

When a capability changes, update the matrix in
`docs/PRODUCT-CONTEXT.md`, the README, design, demo script, and accessibility
notes as applicable.

## Source and evidence rules

Prefer sources in this order:

1. Official California statutory and regulatory text.
2. Official HCD guidance and technical-assistance material.
3. Official jurisdiction code, forms, GIS, and published procedures.
4. HCD enforcement or technical-assistance letters as documented precedent,
   not controlling authority for every jurisdiction.
5. Secondary sources only for discovery.

Search snippets, summaries, and model output are never verification evidence.
If an official source cannot be retrieved, mark the item unverified and
surface the gap.

Every published rule should have a stable ID, jurisdiction scope, criteria,
canonical citation and URL, a short supporting excerpt or content digest, a
source-check date, and explicit dependencies. Preserve effective dates and
distinguish enactment, effective, and source-check dates.

The current `verified_on` field means that dated source evidence is recorded;
it does not encode who reviewed it or whether a jurisdiction accepted the
interpretation. New verification work should move toward explicit levels such
as `machine_linked`, `human_reviewed`, and `jurisdiction_approved`, with
reviewer/method metadata.

Treat a changed or unreachable source as a currency problem. Prefer explicit
source IDs and dependency edges over substring matching. A source change must
identify every affected rule, golden case, and user-facing output until a
person re-verifies them.

## Decision-support and AI boundaries

- Use deterministic rules for objective, testable standards.
- Use AI for bounded extraction, retrieval, explanation, translation drafts,
  and staff-document drafts when its evidence can be shown.
- Never let model prose silently create or modify a published rule.
- Require page/passage evidence for extracted facts and citations for
  generated remedies or explanations.
- Expose unknown, conflicting, stale, and unsupported states. Abstain and
  route to staff instead of filling gaps with inference.
- Keep model-independent regression fixtures for any AI-assisted workflow.
- Separate **submission completeness** (required material is present) from
  **consistency/compliance review** (the proposal satisfies applicable
  standards). Do not use one as a proxy for the other.

## Privacy, records, and public-sector posture

Use public, synthetic, or properly redacted project material in the
repository and demo. Do not commit applicant PII, credentials, private permit
files, or model-provider payloads.

The current public demo persists no applicant data. Before adding storage,
accounts, telemetry, uploads, or external model calls, document:

- collected fields and purpose;
- data flow and subprocessors;
- access controls and security boundary;
- retention and deletion behavior;
- jurisdiction ownership and full export;
- records-search/export behavior for CPRA workflows; and
- deployment-specific privacy and security review needs.

Do not claim CPRA, Information Practices Act, SAM, or SIMM compliance merely
because the design anticipates it.

## Architecture and implementation

- Keep rules, sources, golden cases, and review artifacts in portable,
  human-readable formats owned by the jurisdiction.
- Preserve the dependency-light Python core and static-friendly demo unless a
  change has a clear product reason.
- `data/demo-data.js` is generated from canonical JSON by
  `scripts/build_demo_bundle.py`. Never hand-edit it; rebuild it whenever an
  input dataset changes.
- The Python and browser demos currently duplicate matching and clock logic.
  Update both or establish a single generated source, and add parity coverage
  for behavior that appears in both.
- Never hard-code a favorable demo answer that bypasses the same data and
  logic under test.
- Keep stable identifiers for rules, sources, jurisdictions, and fixtures.
- Label samples, simulations, and manually curated data in the interface.

## Quality bar

For rule or screening changes, add positive, negative, boundary, ambiguous,
and wrong-jurisdiction cases as relevant. For source changes, test both the
affected dependency set and unaffected controls. For the conformance scanner,
use held-out positive and negative material before publishing accuracy or
coverage metrics.

Before handing off a code or data change:

1. Run `python -m pytest -q` with an interpreter that has pytest.
2. Run the verification harness when rules, sources, or golden cases changed.
3. Run `python3 scripts/build_demo_bundle.py --check`.
4. Check JSON and public-demo/Python parity where applicable.
5. Run `git diff --check`.
6. Update capability status and public claims.

Maintain the WCAG 2.2 AAA target while clearly separating automated/static
checks from completed human assistive-technology testing. Translation of
source-derived guidance requires semantic parity review; translating only UI
controls is not enough.

## Priority order

Unless the task explicitly changes strategy, prefer:

1. Claim integrity, source dependencies, and verification semantics.
2. One pilot jurisdiction's parcel-aware ADU permit-readiness packet,
   including missing-item remedies and an evidence manifest.
3. A human re-verification and local-rule authoring workflow.
4. Held-out scanner evaluation and comparable-jurisdiction discovery.
5. Bounded Scenario B extensions such as comment-resolution tracking.

Defer autonomous legal interpretation, full building-code plan review,
rip-and-replace permitting infrastructure, and claims of comprehensive local
coverage.
