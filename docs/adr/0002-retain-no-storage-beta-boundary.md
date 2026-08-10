# Retain a public static, no-application-storage beta boundary

- Status: Proposed
- Date: 2026-08-09
- Deciders: Product scope owner, jurisdiction authority, privacy owner,
  security owner, records owner, deployment owner, accessibility owner,
  language-access owner, and support owner
- Decision evidence: Pending; every approval remains `not_run` in
  `data/validation/beta-operations-readiness.json`

## Context

Permit Bearings is a tested prototype, not a tested beta. Its current public
surface is static: project facts are processed in current page memory, the
application submits no applicant answers to a service, and the packet example
replays committed synthetic records. There are no accounts, uploads,
application-managed applicant records, browser persistence, application
telemetry, runtime external model calls, or permitting-system writeback.

A first limited beta still needs one active jurisdiction workflow, named
authority, reviewed content, external testing, and deployment-specific
decisions. Introducing durable applicant data or operational integrations at
the same time would add retention, deletion, access, breach, legal-hold,
public-records, subprocessor, and offboarding obligations before the core
route-to-packet value has been tested.

“No storage” in this decision means **no application-managed applicant-data
storage or applicant-answer submission**. A selected static host, DNS/CDN,
linked third-party site, browser, repository, support channel, or incident
system may separately process request or operational metadata. Those systems
must be inventoried and reviewed for the actual deployment; they are not made
safe or approved by this ADR.

## Proposed decision

Keep the first partner beta inside this boundary:

- public static HTTPS delivery of one frozen workflow;
- no accounts or identity layer;
- no applicant file or document uploads;
- no application-managed database, object store, cookie, local storage, or
  session storage for applicant facts;
- no application telemetry or behavioral analytics;
- no runtime external model or parcel-service call;
- no writeback to a permitting, records, case-management, or communications
  system;
- only the enumerated structured project facts in current page memory;
- only public, synthetic, or properly redacted committed evaluation material;
  and
- browser-owned printing or Save as PDF, with no application retrieval path.

The deployment may not be called approved until the exact commit, HTTPS URL,
host/DNS/CDN boundary, request-metadata behavior, subprocessors, access,
retention, incident path, support path, release evidence, rollback evidence,
and role-based decisions are recorded outside this proposed ADR. Any account,
upload, persistence, telemetry, runtime network/model call, real applicant
record, or writeback is a boundary change requiring a new ADR, data flow,
threat model, records design, control mapping, and approvals before
implementation.

## Options considered

### A. Retain the static no-application-storage boundary (proposed)

| Dimension | Assessment |
|---|---|
| Product learning | Tests the candidate-route and packet-presence journey without coupling it to a case-management build. |
| Privacy and records surface | Lowest of the considered options, but hosting and operational records still require deployment review. |
| Integration complexity | Low; sits beside the jurisdiction's existing permitting process. |
| Applicant continuity | Limited; answers disappear on refresh and the application cannot resume a case. |
| Evidence quality | Supports frozen public/synthetic/redacted evaluations, not production applicant outcome claims. |

### B. Add accounts and applicant packet storage for the first beta

| Dimension | Assessment |
|---|---|
| Product learning | Enables resume and longitudinal outcome measurement. |
| Privacy and records surface | High; creates identity, applicant-record, retention/deletion, access, incident, legal-hold, and export obligations. |
| Integration complexity | Medium to high even without permitting-system writeback. |
| Applicant continuity | Better, but only after deployment-specific governance is approved. |
| Evidence quality | Could support real applicant measures with appropriate authority and handling; none exists now. |

### C. Integrate with an existing permitting platform immediately

| Dimension | Assessment |
|---|---|
| Product learning | Could test workflow fit in operational context. |
| Privacy and records surface | Highest; inherits system, identity, case, audit, vendor, and writeback boundaries. |
| Integration complexity | High and partner-specific. |
| Applicant continuity | Potentially strong. |
| Evidence quality | Depends on partner authority, data quality, and an approved evaluation design. |

### D. Keep only the public prototype and do not run a bounded beta

| Dimension | Assessment |
|---|---|
| Product learning | Avoids operational risk but cannot supply partner, applicant, or maintenance evidence. |
| Privacy and records surface | Current prototype boundary only. |
| Integration complexity | None. |
| Applicant continuity | None. |
| Evidence quality | Remains automated prototype evidence. |

## Trade-off analysis

Option A isolates the first unknown: whether one reviewed, active-jurisdiction
route-to-packet workflow is understandable and useful. It sacrifices account
continuity, real document ingestion, applicant-level analytics, and system
integration. Those features can be reconsidered only after the bounded beta
shows enough value and maintenance feasibility to justify their added public-
sector obligations.

Option A does not remove all privacy, security, or records work. The selected
host and operational channels may create metadata or records, and a person may
save a local print artifact. The beta therefore still requires the runbook's
deployment inventory, role assignments, incident path, CPRA routing, support
process, and release/rollback evidence.

## Consequences

- The application cannot resume or retrieve an applicant session.
- The service cannot receive an applicant document or measure applicant-level
  product usage through telemetry.
- Testing must use public, synthetic, or properly redacted material handled
  outside the application under an approved protocol.
- Outcome measurement must not infer a stored cohort or permitting result from
  static-page use.
- A host's request logs are outside the application boundary and must be
  separately inventoried, minimized where configurable, and reviewed.
- Support and incident channels must instruct users not to send applicant PII
  or permit files; any accidental receipt is handled by the owning system's
  approved process.
- Browser Print/Save can create a user-controlled artifact; the application
  has no deletion or retrieval capability for it.
- A scope-expanding feature cannot be merged as an incidental implementation
  detail. It requires a superseding ADR and evidence package.

## Pending decisions and action items

1. [ ] Select one active jurisdiction workflow and authorized partner roles.
2. [ ] Select and inventory the beta host, DNS/CDN, request metadata, and
   subprocessors.
3. [ ] Complete the deployment-specific threat, privacy, records, access,
   accessibility, language-access, support, and incident reviews.
4. [ ] Freeze one commit and HTTPS URL; execute release and rollback checks.
5. [ ] Rehearse CPRA search/export routing across repository, deployment,
   incident, and support systems while confirming the application has no
   applicant record store.
6. [ ] Record each role-based decision in a separately reviewed execution
   schema. Do not change the prepared ledger to manufacture approval.
7. [ ] Accept, reject, or supersede this ADR. Until then, its status remains
   Proposed and the operating package remains **PREPARED / NOT APPROVED**.
