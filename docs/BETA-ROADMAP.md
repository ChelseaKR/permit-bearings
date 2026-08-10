# Tested-prototype to limited-beta roadmap

Status: 2026-08-09. This roadmap defines an evidence gate; it does not report
that a beta, pilot, review, jurisdiction approval, or production deployment
exists.

## Status today

Permit Bearings is a **tested prototype with automated evidence only**. It has
deterministic screening, source and fingerprint checks, Golden regression cases, generated
browser data, accessibility and performance automation, a static no-storage
deployment, and a statewide orientation profile for all 541 registry entries.
Those entries share a bounded statewide candidate-rule baseline; only Davis
and Woodland have limited jurisdiction-scoped records, and neither is
comprehensive local-code coverage.

The strongest packet example is still a source-bound, made-up Woodland
future-state simulation. The official program record says the City's
preapproved-plan list is coming soon. The example does not inspect files,
query a parcel, certify completeness, or represent a currently usable City
workflow.

All 19 published rule records are currently `machine_linked`, with zero named
human reviews and zero jurisdiction approvals. The prepared content-review,
participant, manual-access, Spanish, partner, and source-change-rehearsal
evidence remains `not_run` or pending. The held-out scanner manifest is also
`not_run`: it has no case set, answer key, blind predictions, result, evaluator
or result hash, or freeze/prediction/scoring receipt. Automated checks cannot
promote any of those states.

A pilot-neutral beta operations package is now machine-testable but remains
**PREPARED / NOT APPROVED**. It proposes a public/static boundary with no
accounts, uploads, application-managed applicant storage, browser persistence,
application telemetry, runtime external model calls, or permitting-system
writeback. All nine role approvals, deployment/hosting fields, records
rehearsals, execution receipts, and partner decisions remain null/`not_run`.
Host request metadata and every deployment-specific privacy, security,
records, access, accessibility, language, support, and hosting decision remain
external work.

Current capability boundaries are canonical in
[`PRODUCT-CONTEXT.md`](PRODUCT-CONTEXT.md#capability-truth). Current automated
quality evidence is summarized in the
[`README`](../README.md#quality-standards), and source/review provenance is in
[`PROVENANCE.md`](../PROVENANCE.md).

## Definition of a limited tested beta

A limited tested beta is **one frozen, deployed workflow for one active
California jurisdiction and one permit subtype**, evaluated against the exact
reviewed sources, rules, requirements, test cases, commit, URL, and content
fingerprints recorded in its evidence gate.

The first beta should:

- use an active local workflow with a named jurisdiction sponsor, source owner,
  and review owner;
- use official public sources and synthetic or properly redacted test material;
- produce candidate guidance and reported packet-presence findings while
  preserving explicit unknown and staff-review states;
- keep packet presence separate from consistency, legal sufficiency,
  compliance, eligibility, acceptance, and approval;
- persist no production applicant data and make no runtime model call; and
- remain portable beside, rather than replace, the jurisdiction's permitting
  system.

The beta claim applies only to that named jurisdiction/workflow. The statewide
navigator, unreviewed routes, other jurisdictions, Spanish machine drafts, and
the ordinance scanner retain their documented prototype boundaries. A
jurisdiction-approved claim is allowed only when a formally authorized
jurisdiction reviewer has approved the exact version and scope.

## Measurable exit gates

All evidence must bind to one immutable commit SHA, HTTPS deployment, source
snapshot, workflow version, and fingerprint set. A blocking product or content
change closes the old cohort and requires a new lock; results from different
versions are never combined.

| Gate | Exit criterion | Current state | Dependency |
|---|---|---|---|
| Active scope | One named jurisdiction and active permit subtype; authoritative ordinance, form, checklist, procedure, and agency calendar; named sponsor and maintenance owner. | No active pilot workflow or sponsor is recorded. Woodland remains a future-state simulation. | External jurisdiction |
| Frozen artifact | Exact SHA, URL, freeze date, source snapshot and receipt, route/workflow/packet fingerprints, and a passing internal dry run are recorded. The same commit passes repository verification, browser accessibility checks, Lighthouse budgets, production smoke tests, and rollback verification. | Automation exists; the external-evidence artifact lock is `not_run`. | Mostly autonomous; deployed URL required |
| Content authority | Two independent qualified reviewers classify 100% of reachable requirement mappings and action drafts. For the prepared 25-item workflow, at least 22 of 25 rows agree initially; every disagreement is sourced, suppressed, or routed to staff; zero blocking content defects remain. A differently sized pilot must freeze its threshold before review. | Two reviewer slots are `not_run`; no completed content-review claim exists. | External reviewers |
| Review levels | Every rule and explanation reachable in the beta path is at least `human_reviewed`, bound to reviewer, method, date, exact version, citation fingerprint, and full-rule fingerprint. Local records use `jurisdiction_approved` only with institutional authorization. | All 19 rules are effectively `machine_linked`. | External reviewers and jurisdiction authority |
| Deterministic evaluation | The local Golden set includes positive, negative, boundary, ambiguous, wrong-jurisdiction, local/state-conflict, stale, and unsupported cases, with at least one case per category and every material rule boundary. All expected IDs and withheld states pass; zero unknown or conflicting material fact is treated favorably. Held-out fixtures and raw result counts are reported separately from development fixtures. | Twenty-nine structured Golden cases exist. A validated planned held-out scanner manifest records `not_run`, per-check official flag/targeted-quiet minima, structured development-source and near-duplicate exclusions, and a blind freeze/prediction/unblind/scoring sequence. Its case, answer-key, prediction, result, evaluator-hash, and execution-receipt fields are null; there is no independently adjudicated corpus or result for an active local workflow. | Autonomous harness; external source custody and answer-key review |
| Packet behavior | Every requirement condition is exercised across applicable `present`, `missing`, `not applicable`, `conflicting`, `needs staff review`, and `not evaluated` states. No material false-favorable finding remains, and the interface never relabels presence as completeness or compliance. | Implemented for one synthetic 25-item manifest; no real or redacted packet evaluation exists. | Autonomous fixtures; external content adjudication |
| Applicant evidence | Six same-version sessions meet the prepared cohort rules. At least 5/6 correctly describe candidate guidance, 5/6 correctly find source status and unknown escalation, and 5/6 identify the packet gap and next action. Median route time is at most 300 seconds, median packet time at most 360 seconds, no more than one repeated navigation-blocker session occurs, and there are zero confident critical over-trust errors. | Six scorecards are prepared and `not_run`. | External recruitment and moderation |
| Problem evidence | At least three participants, including at least two primary beneficiaries, describe a specific recent pain, consequence, and workaround; at least one domain participant reports monthly-or-more recurrence. Raw counts and denominators remain visible. | No participant evidence exists. | External recruitment |
| Human access | All 21 version-bound manual checks pass, including keyboard, VoiceOver/Safari, NVDA, physical iOS and Android, zoom/reflow, forced colors, three print browsers, and PDF/assistive-technology review. Automated axe and Lighthouse results remain separate. | All manual rows are `not_run`. | Human and assistive-technology testers |
| Language | If Spanish is presented as applicant-ready within the beta, every reachable Spanish source-derived record has exact-version semantic-parity approval and `ES-USABILITY-JOURNEY` passes. Otherwise Spanish stays explicitly review-pending and outside the beta claim. | Nineteen semantic-review rows and Spanish usability are `not_run`. | Qualified Spanish reviewers and participants |
| Maintainability | One controlled source change completes detection, affected/unaffected mapping, review, approval, republication, and rollback. The receipt records named human owners, elapsed and active-role time, defects, and the prospective partner's maintenance-burden decision. | Rehearsal is prepared and `not_run`; no human owner or burden decision is recorded. | External reviewer and partner |
| Ownership and export | A jurisdiction-owned export of sources, rules, requirements, review receipts, fixtures, dependencies, and checksums opens and restores without vendor-only tooling. | A deterministic, Git-bound package now builds, verifies, and restores the pinned schema-v1 public/synthetic evidence set. Its pinned profile excludes known sensitive records but is not a privacy classifier, and it does not establish contractual ownership, a production offboarding test, or partner acceptance. The later held-out planning artifact and future evaluation inputs/results are outside profile v1 and require a separately reviewed profile version. | Implemented mechanism; external partner acceptance and any sensitive-data design |
| Privacy, records, and security | The first beta remains public/synthetic/redacted with no accounts, uploads, applicant store, telemetry, external model call, or write-back. Any expanded flow first records fields and purpose, access, retention/deletion, subprocessors, CPRA search/export and legal-hold behavior, threat model, control mapping, incident path, and deployment-specific approvals. | ADR 0002, a role-based runbook, a 17-control/nine-approval portable ledger, and a strict prepared-state validator now cover the proposed no-application-storage boundary, exact current-page fields, host metadata caveat, records routing, incident/support, release, and rollback. The ADR is proposed; every deployment field, execution receipt, records rehearsal, human approval, and partner decision is null/`not_run`. This is not privacy/security approval or CPRA, Information Practices Act, SAM, or SIMM compliance. | Implemented planning validator; external deployment inventory, rehearsals, role assignment, and approvals |
| Partner and decision | A credible partner supplies a written next step with an owner role and date, accepts the maintenance plan, and signs a `proceed`, `extend`, `pivot`, or `stop` decision after every supporting receipt. | Partner gate and aggregate decision are pending. | External partner |

Passing these gates permits a bounded statement such as:

> Permit Bearings is a tested beta for **[jurisdiction] [permit workflow]** on
> **[commit and date]**, evaluated with **[methods and raw denominators]**. It
> provides cited candidate guidance and packet-presence support. It does not
> provide legal advice, certify completeness or compliance, determine final
> eligibility, approve a permit, or establish coverage outside the named
> workflow.

It does not permit “statewide beta,” “applicant-ready statewide service,”
“validated law,” “comprehensive local coverage,” “compliance determination,”
or permitting-outcome claims.

## Roadmap

### Now — autonomous foundations

This roadmap tranche completes seven machine-testable foundations without
changing the product's maturity claim:

- the Statewide Coverage Navigator is deployed as orientation, not statewide
  local-code coverage;
- every populated applicant result has a state-specific decision boundary for
  candidate, unresolved, no-route, and source-review-hold outcomes;
- source changes can produce exact fingerprint-bound rule, Golden, readiness,
  remedy, packet, and journey work plus a separate blank decision ledger; and
- a repeatable deployment smoke command checks the five public routes and the
  generated 541-profile/17-rule artifact contract; and
- a pinned canonical ZIP can package, verify, and inertly restore the pinned
  schema-v1 public/synthetic evidence set while rejecting uncommitted selected
  files,
  asserted validation-state drift, unsafe members, and existing destinations;
  its allowlist excludes known sensitive material but is not a privacy
  classifier; and
- a validated held-out scanner manifest freezes the evaluation semantics,
  current scanner/check hashes, development-source exclusions, raw count
  names and reporting grains, the full pair universe, per-check targeted-pair
  roles/minima, blind execution chronology, and claim boundary while keeping
  every case, answer-key, prediction, result path, evaluator hash, and execution
  field explicitly null and `not_run`; a future result-artifact hash is
  recorded out of band. A strict Python interface validates each future input,
  generates blind predictions, scores raw pairs, and writes an exclusive
  receipt. Its CLI exposes `validate-plan`, blind `predict` without an
  answer-key argument, and `score` with frozen predictions plus the declared
  reviewer/adjudication key. `validate-result` reloads all frozen inputs and
  recomputes the recorded result before accepting it; the tooling does not
  supply the external evidence; and
- a proposed no-storage ADR, precise operations runbook, portable 17-control
  and nine-approval ledger, and strict CLI pin the public/static beta boundary,
  empty service field/purpose inventory, exact current-page facts, host
  metadata caveat, retention/deletion, CPRA routing, access, incident,
  support, release, rollback, and export limits. The ledger and validator bind
  the ADR/runbook to exact raw-byte SHA-256 digests. The validator accepts only
  `prepared_not_approved`; all future-beta deployment, rehearsal, approval,
  receipt, and partner-decision fields remain null/`not_run`, and later
  execution requires a separately reviewed schema.

The remaining autonomous work is:

1. Generalize the hard-coded Woodland journey, program-availability, bundle,
   and CLI paths into a registry-configured multi-workflow boundary while
   preserving fail-closed behavior.
2. Derive a pilot-neutral beta gate from the existing specialized ledgers;
   validate every aggregate and prevent a hand-edited status promotion.
3. Add a local-source onboarding validator for operative passages and effective
   dates; forms, checklists, fees, and process pages; source fingerprints;
   scope, exceptions, and open questions; and named review ownership/cadence.
4. Exercise the new exact affected-output worklist in a controlled rehearsal;
   complete assignments and dispositions with authorized people, and add
   separate approval, publication, and rollback receipts without allowing the
   decision ledger to clear a hold by itself.
5. After independent source collection, two-reviewer adjudication, and freeze
   custody are available, execute the held-out scanner contract with frozen
   cases and answer key; generate blind pair-level predictions before
   unblinding, publish the six recomputable raw confusion/abstention counts,
   and keep development fixtures and synthetic controls separate. Record the
   freeze, prediction, unblind, and scoring chronology, then retire the
   revealed corpus from use with future scanner versions.
6. Execute the deployment-specific host/subprocessor inventory, threat and
   control review, CPRA search/export and rollback rehearsals, and role
   approvals described by the prepared operations package. Record them in a
   separately reviewed execution schema; the prepared ledger cannot be
   promoted.
7. Add applicant-copy catalog parity, placeholder checks, and
   pseudolocalization tests without promoting Spanish review status.

These tasks can make the product pilot-ready, but they cannot supply a sponsor,
source authority, human review, applicant observation, accessibility signoff,
language approval, or jurisdiction acceptance.

### Next — execute with one partner

1. Select an active jurisdiction and one detached-ADU workflow; obtain the
   authoritative local source package and identify conflict-resolution
   authority.
2. Encode the locally owned route, requirements, staff questions, source
   dependencies, and staff-adjudicated synthetic or redacted cases.
3. Complete the independent content reviews and resolve or suppress every
   blocking issue before applicant testing.
4. Freeze the exact deployment and execute the six participant sessions,
   manual access matrix, and language gates included in scope.
5. Complete the source-change, republication, rollback, export, and support
   rehearsals; have the partner judge maintenance burden.
6. Obtain deployment-specific privacy, records, security, accessibility,
   language-access, hosting, and support decisions.
7. Publish the gate result and exact bounded claim. Use `extend`, `pivot`, or
   `stop` when the evidence does not support `proceed`.

### Later — expand only after the loop works

- Measure first-pass completeness, correction cycles, time to deemed complete,
  applicant self-remedy, and staff effort on an agreed, appropriately handled
  pilot dataset.
- Add authoritative read-only parcel and zoning retrieval for the pilot
  jurisdiction, with disagreements and unknowns reviewed by staff.
- Build a human re-verification and local-rule authoring workbench.
- Evaluate the ordinance scanner on held-out positive and negative material,
  and build a cited comparable-jurisdiction HCD precedent explorer.
- Add new jurisdictions and permit subtypes one at a time with their own source
  owners, review evidence, Golden cases, and maintenance gate.
- Consider new-law discovery, bounded Scenario B comment resolution, SB 35,
  AB 2011, accounts, uploads, telemetry, model calls, and permitting-system
  integrations only after the beta proves its maintenance and governance loop.

## Canonical evidence map

| Evidence | Canonical record |
|---|---|
| Capability status and priority | [`PRODUCT-CONTEXT.md`](PRODUCT-CONTEXT.md) |
| Public behavior and automated quality | [`README.md`](../README.md) |
| Architecture and deployment gaps | [`DESIGN.md`](DESIGN.md) and [`DATA-FLOW.md`](DATA-FLOW.md) |
| Source and claim provenance | [`PROVENANCE.md`](../PROVENANCE.md) |
| Proposed pilot scope and participation | [`SHOWCASE-PILOT-BRIEF.md`](SHOWCASE-PILOT-BRIEF.md) |
| External validation method and thresholds | [`SHOWCASE-VALIDATION-PLAN.md`](SHOWCASE-VALIDATION-PLAN.md) |
| Aggregate evidence gate | [`woodland-flagship-gate.json`](../data/validation/woodland-flagship-gate.json) |
| Content-review ledger | [`woodland-content-review.json`](../data/validation/woodland-content-review.json) |
| Participant-session ledger | [`woodland-participant-sessions.json`](../data/validation/woodland-participant-sessions.json) |
| Human accessibility and language ledger | [`woodland-manual-evidence.json`](../data/validation/woodland-manual-evidence.json) and [`MANUAL-VALIDATION.md`](MANUAL-VALIDATION.md) |
| Source-change rehearsal | [`woodland-source-change-rehearsal.json`](../data/validation/woodland-source-change-rehearsal.json) |
| Rule review levels | [`rule-verification.json`](../data/validation/rule-verification.json) |
| Adopted source-state receipt | [`current.json`](../data/source-status/current.json) |
| Current Woodland program boundary | [`woodland-preapproved-adu-program.json`](../data/availability/woodland-preapproved-adu-program.json) |
| Held-out scanner evaluation contract (`not_run`) | [`manifest.json`](../data/conformance/evaluations/heldout-v1/manifest.json) |
| Proposed no-storage beta decision | [`ADR 0002`](adr/0002-retain-no-storage-beta-boundary.md) |
| Beta operations procedure | [`BETA-OPERATIONS-RUNBOOK.md`](BETA-OPERATIONS-RUNBOOK.md) |
| Beta operations control ledger (`prepared_not_approved`) | [`beta-operations-readiness.json`](../data/validation/beta-operations-readiness.json) |

Machine-readable ledgers remain authoritative for activity state. Narrative
documentation may explain a recorded result, but it cannot turn `not_run`,
pending, unreviewed, or machine-linked evidence into a pass or approval.
