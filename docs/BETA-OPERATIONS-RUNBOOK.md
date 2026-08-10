# Runbook: proposed no-application-storage limited beta

- Owner: Unassigned `product_scope_owner`
- Frequency: Before every candidate release; after every incident or material
  boundary change
- Last updated: 2026-08-09
- Last run: Not run
- Status: **PREPARED / NOT APPROVED**
- Decision: Proposed in
  [`ADR 0002`](adr/0002-retain-no-storage-beta-boundary.md)
- Machine-readable plan:
  [`beta-operations-readiness.json`](../data/validation/beta-operations-readiness.json)

## Purpose and limit

Use this runbook to prepare, verify, operate, hold, and roll back one frozen
public static beta candidate for one active California jurisdiction and one
permit subtype. It preserves a no-application-storage boundary: applicant
answers stay in the current browser page and are not submitted to or retained
by the application.

This runbook has not been executed or approved. It is not evidence of a beta,
partner acceptance, privacy or security approval, CPRA or Information
Practices Act compliance, SAM or SIMM compliance, accessibility or language
approval, legal advice, a complete application, eligibility, or permit
approval. Automated checks validate software and record shape only.

Stop and require a new ADR, data flow, threat model, records design, control
map, and approvals before adding any account, identity, upload, applicant-data
store, cookie/browser persistence, application telemetry, runtime external
model or parcel call, real applicant record, or writeback.

## Required roles

No person or contact channel is assigned in the prepared package. Assign roles
in an approved system outside this repository before execution; use role codes
in public receipts and keep personal contact details out of the repository.

| Role code | Responsibility | Current assignment |
|---|---|---|
| `product_scope_owner` | Confirms the exact workflow, claim boundary, and release/hold decision. | Not assigned |
| `jurisdiction_authority` | Confirms institutional authority, active workflow, and partner decision. | Not assigned |
| `content_source_owner` | Owns official sources, currency, rule/requirement review, and holds. | Not assigned |
| `deployment_owner` | Owns host inventory, immutable deployment, smoke check, and rollback. | Not assigned |
| `security_owner` | Reviews threat boundary, access, vulnerabilities, and incident severity. | Not assigned |
| `privacy_owner` | Reviews data minimization, host metadata, accidental disclosure, and boundary changes. | Not assigned |
| `records_owner` | Owns retention, legal-hold routing, CPRA search/export coordination, and authorized responses. | Not assigned |
| `accessibility_owner` | Owns required human and assistive-technology execution and disposition. | Not assigned |
| `language_access_owner` | Decides whether Spanish is excluded or exact-version reviewed for the beta claim. | Not assigned |
| `support_owner` | Owns support intake, safe reproduction, status communication, and escalation. | Not assigned |
| `incident_lead` | Coordinates containment, evidence preservation, role decisions, and recovery. | Not assigned |

One person may hold multiple roles only if the partner explicitly accepts the
separation-of-duty trade-off. Content review independence and any authority
required by another evidence gate remain separate requirements.

## Exact data and processing inventory

### Application service

| Item | Value in this boundary |
|---|---|
| Applicant fields collected by the application service | None (`[]`) |
| Service purposes for applicant-data collection | None (`[]`) |
| Accounts or identity | None |
| Applicant uploads | None |
| Application database/object store | None |
| Applicant cookies, local storage, or session storage | None |
| Application telemetry/analytics | None |
| Runtime external model or parcel-service call | None |
| Permitting-system or records-system writeback | None |

### Current-page browser memory

The browser may hold only the following structured input names while the page
is open:

`adu_project_form`, `adjacent_sb9_split_same_actor`,
`demolishes_protected_housing`, `ellis_withdrawal_last_15_years`,
`in_urbanized_area`, `journey_applicability`, `jurisdiction`,
`jurisdiction_name`, `lot_split_alters_historic_district_resource`,
`lot_split_on_historic_landmark_site`, `on_protected_site`,
`parcel_created_by_sb9_split`, `primary_dwelling_status`, `project_type`,
`proposed_lot_ratio_compliant`, `proposed_lot_size_compliant`, `sf_zone`,
`tenant_occupied_last_3_years`,
`two_unit_contributing_historic_location`,
`two_unit_individually_listed_historic_property`, and
`unpermitted_existing`.

Purpose: render deterministic candidate guidance, source status, unresolved
questions, and temporary print-oriented outputs. Answers are cleared by page
refresh/close and are not transmitted by application code. The packet page
accepts no applicant input and replays committed public synthetic records.

If a beta workflow uses fewer fields, freeze that smaller set. Adding a field
requires updating the inventory and schema before release. Do not collect
name, email, address, APN, permit number, account identifier, applicant file,
or free text under this boundary.

### Boundaries outside application code

- The static host, DNS/CDN, and network intermediaries may process ordinary
  request metadata such as IP address, user agent, requested path, timestamp,
  and security events. The actual fields, purposes, locations, recipients,
  retention, deletion, and transfer terms are unknown until a host is selected
  and reviewed.
- Following an official-source link transfers the user to that site's policy
  and logging boundary.
- Browser Print or Save as PDF may create a local user-controlled artifact.
  The application cannot retrieve or delete it.
- Repository, deployment, support, and incident systems can create
  operational records even though the application has no applicant store.
- Do not ask users to send applicant PII or permit files through support. If
  they do, stop distribution and use the receiving system's approved privacy,
  records, and incident procedure.

## Prerequisites and release worksheet

Do not begin deployment until every item has an owner and evidence location.
Blank values block release.

- [ ] Active jurisdiction and permit subtype: `__________`
- [ ] Authorized jurisdiction role: `__________`
- [ ] Frozen commit SHA: `__________`
- [ ] Candidate HTTPS URL: `__________`
- [ ] Last-known-good commit and URL: `__________`
- [ ] Source snapshot/receipt ID: `__________`
- [ ] Workflow/rule/requirement fingerprints: `__________`
- [ ] Hosting, DNS, and CDN providers: `__________`
- [ ] Host request-metadata inventory and retention: `__________`
- [ ] Subprocessor and data-location review: `__________`
- [ ] Repository/deployment/DNS access review: `__________`
- [ ] Privacy, security, records, accessibility, language, support, hosting,
  product-scope, and partner decisions: `__________`
- [ ] Approved host-specific deploy and rollback procedure IDs: `__________`

The committed readiness ledger deliberately keeps these deployment and
approval fields null/`not_run`. Record execution in a separately reviewed
receipt; never edit the prepared ledger to claim approval.

## Procedure

### 1. Validate the prepared operating package

From the repository root, run:

```sh
PYTHONPATH=src .venv/bin/python -m permit_pathways.beta_operations
```

Expected result:

```text
beta operations package: PREPARED / NOT APPROVED
  17 controls prepared; 9 approvals not_run
  schema validation is not deployment, approval, or compliance evidence
```

If it fails: stop. Do not deploy. Correct an accidental schema/path drift or
open a reviewed schema change if the boundary intentionally changed.

### 2. Confirm the source still has no applicant-data transmission path

Run these read-only checks:

```sh
rg -n "localStorage|sessionStorage|document\.cookie|sendBeacon|XMLHttpRequest" \
  index.html check.html prepare.html review.html evidence.html assets/demo.js
rg -n "fetch\(|<form|FormData" \
  index.html check.html prepare.html review.html evidence.html assets/demo.js
```

Expected result: the first command has no matches. Manually classify every
second-command match. Static `fetch` calls may retrieve repository data; forms
and `FormData` may process current-page answers. Any applicant-answer network
submission, telemetry endpoint, upload, or persistence match blocks release.

Also inspect the candidate diff for dependencies, network endpoints, form
actions, uploads, telemetry, storage, accounts, or writeback. This textual
screen is a change-review aid, not proof that no behavior exists.

### 3. Inventory hosting and subprocessors

The `deployment_owner`, `privacy_owner`, `security_owner`, and `records_owner`
must jointly record:

1. static host, DNS, CDN, certificate, repository/deploy integration, status
   service, support system, and incident system;
2. ordinary request/security metadata each may receive;
3. purpose, retention, deletion, location/transfer, access, and downstream
   service terms;
4. which settings can minimize logs, previews, branch deployments, indexing,
   and public access; and
5. the approved owner and offboarding/export path for each system.

Expected result: a deployment-specific inventory receipt and explicit role
decisions. A provider name alone is not approval. If any provider requires
applicant answers, uploads, behavioral telemetry, runtime model calls, or
writeback, stop and supersede the boundary before implementation.

### 4. Review access

Record authorized role codes—not personal details—for:

- repository administration and merge;
- deployment configuration and release;
- DNS and certificate changes;
- security settings and log access;
- rollback or site-hold authority; and
- incident evidence and support records.

Require least privilege, individual accounts in the owning system, removal
procedures, and an emergency-access decision. Do not place credentials,
tokens, access lists, or personal contact data in the repository.

Expected result: `access_review_status` can be approved only in the separate
execution record. A valid prepared ledger still reports `not_run`.

### 4a. Complete the deployment threat and control review

Treat this table as a minimum hypothesis set, not a completed threat model or
control assessment:

| Threat | Required prevention/detection | Failure response |
|---|---|---|
| Unauthorized repository, DNS, or deploy change | Least privilege, protected merge/deploy path, immutable commit-to-URL receipt, and independent smoke verification. | Hold the site; preserve authorized evidence; rotate/revoke through the owning system; restore the last known-good commit. |
| Applicant answers unexpectedly leave the page | No form action/submission endpoint, telemetry, upload, persistence, runtime model/network call, or writeback; inspect every candidate diff and browser request path. | Treat as critical; hold, bound affected versions, and escalate to incident/security/privacy/records roles. |
| Host or CDN records more metadata than approved | Deployment-specific field/purpose/retention/subprocessor inventory and minimization settings. | Stop release or disable the affected deployment; follow provider and records procedures. |
| Stale, wrong-jurisdiction, tampered, or false-favorable guidance | Source/fingerprint holds, exact journey/rule bindings, Golden cases, generated-data checks, and bounded claims. | Withhold affected guidance; run source/content re-verification; release only on a new verified commit. |
| Dependency or build compromise | Locked dependencies, CodeQL/Bandit/audit workflows, pinned actions, clean build, and exact commit receipt. | Stop release, investigate scope, rebuild from reviewed inputs, and rerun all gates. |
| Applicant PII enters support or incident tooling | Instructions prohibit PII/files, synthetic reproduction, role-limited access, and owning-system handling rules. | Restrict copying, invoke approved privacy/records/incident handling, and preserve/delete only under authorized direction. |
| Static site unavailable or rollback fails | Five-route deployment smoke, recorded last-known-good commit, approved host rollback, and hold option. | Keep beta unavailable; do not fall forward to an unreviewed build. |
| Accessibility or language barrier creates unsafe over-trust | Human/AT matrix, exact-version language review, visible review-pending boundaries, and staff escalation. | Hold the affected language/journey or narrow the beta claim until reviewed. |

For the selected deployment, add provider-specific threats, likelihood/impact,
control owner, evidence, residual risk, and acceptance decision. The
`security_owner`, `privacy_owner`, `records_owner`, `deployment_owner`, and
`jurisdiction_authority` must review the result. No row in this prepared table
is tested, accepted, or approved.

### 5. Verify the frozen candidate locally

Start from the exact clean candidate commit and run:

```sh
git status --short
git rev-parse HEAD
make verify
npm ci
npx playwright install chromium
npm run test:a11y
npm run test:perf
```

Expected result: the working tree is clean for the candidate; the recorded
SHA matches `HEAD`; locked Python quality, security, data, export, browser,
accessibility automation, and performance budgets succeed.

If any command fails: stop. Fix the candidate, create a new commit, and rerun
the complete sequence. Never copy results from another commit. Automated
accessibility checks do not replace the required human/assistive-technology
matrix.

### 6. Confirm content and source gates

Before deployment, verify that the exact beta path:

- uses one active jurisdiction workflow and current official source package;
- carries the required rule, explanation, requirement, source, and review
  fingerprints;
- has no changed dependency or unresolved blocking content defect;
- preserves `unknown`, conflicting, and staff-review outcomes;
- does not relabel presence as completeness/compliance; and
- has the human/jurisdiction review levels required by the beta roadmap.

Expected result: separate content/source receipts bound to the same commit.
The current Woodland future-state simulation and `machine_linked` rules do not
satisfy this step.

### 7. Deploy by an approved immutable procedure

There is no approved beta host or deploy command in this package. The
`deployment_owner` must use the host-specific procedure approved in Step 3,
target the exact recorded commit, require HTTPS, and prevent unreviewed preview
or branch content from becoming the beta URL.

Expected result: one immutable commit-to-URL receipt. If the host cannot bind
the deployed content to the frozen commit, stop. Do not substitute the public
prototype deployment as beta evidence.

### 8. Run the bounded production smoke check

Replace the placeholder with the exact reviewed HTTPS base URL:

```sh
PYTHONPATH=src .venv/bin/python -m permit_pathways.deployment_smoke \
  --base-url https://beta.example.gov/permit-bearings/
```

Expected result: HTTP 200 and required artifact markers for all five routes,
plus the expected generated coverage-index shape. This proves only deployed
availability and artifact shape.

If it fails: do not release. Check commit binding, base path, generated data,
cache/CDN state, and host routing. Roll back or hold the site if the prior
known-good state cannot be restored immediately.

### 9. Execute required human checks

On the same URL and commit, execute the roadmap's manual accessibility,
assistive-technology, physical-device, print/PDF, content, language, applicant,
and maintenance gates. If Spanish has not passed exact-version semantic and
usability review, keep it visibly review-pending and outside the beta claim.

Expected result: separately retained receipts with raw denominators and
dispositions. A schema-complete or automated record is not a human result.

### 10. Make the release decision

The required roles review the immutable deployment, source/content evidence,
host boundary, operations evidence, and external gates. The jurisdiction role
makes the partner decision within its authority. Record `proceed`, `extend`,
`pivot`, or `stop` in a separately reviewed execution record.

Expected result: either a bounded tested-beta claim meeting
`docs/BETA-ROADMAP.md`, or an explicit hold/extend/pivot/stop decision. This
prepared ledger never changes from `prepared_not_approved`.

## Routine support

1. Accept only product-behavior reports, public URLs, public source citations,
   browser/OS versions, and synthetic reproduction steps through the approved
   support channel.
2. Tell the reporter not to send an address, APN, permit/application number,
   contact information, applicant file, screenshot containing PII, or other
   private case material.
3. Reproduce with a committed synthetic fixture where possible.
4. Record the deployed commit, URL, observed time, browser/OS, affected page,
   expected/observed behavior, source IDs, and whether the issue could produce
   false-favorable guidance.
5. Route source/content issues to `content_source_owner`; availability and
   release issues to `deployment_owner`; potential disclosure or compromise to
   `incident_lead`, `security_owner`, and `privacy_owner`; records questions to
   `records_owner`; accessibility/language issues to their owning roles.
6. Do not provide project-specific legal conclusions or tell an applicant that
   a packet is complete, compliant, eligible, accepted, or approved.

## Incident triage

### Severity

| Severity | Examples | Immediate action |
|---|---|---|
| Critical | Suspected credential compromise; applicant data unexpectedly transmitted or exposed; unauthorized deployment/writeback; false approval/compliance output. | Place affected surface on hold, preserve authorized evidence, and escalate immediately to incident, security, privacy, records, deployment, product, and jurisdiction roles. |
| High | Stale/changed source shown as actionable; integrity binding bypass; inaccessible critical journey; wrong-jurisdiction candidate result. | Hold the affected workflow, preserve evidence, notify content/deployment/product roles, and assess broader impact. |
| Medium | Material support, print, localization, performance, or noncritical accessibility defect with a safe staff route. | Log, bound affected versions, assign owner, and set a release/repair decision. |
| Low | Cosmetic or documentation issue that does not change meaning, evidence, access, or routing. | Schedule normal review; verify claim impact before classifying low. |

### First response

1. Record detection time, URL, commit, reporter channel, symptom, and role code.
2. Do not copy applicant data into tickets or the repository. If accidentally
   received, restrict further disclosure and invoke the receiving system's
   approved handling process.
3. Determine whether the issue affects confidentiality, integrity,
   availability, source currency, accessibility, language, or claim accuracy.
4. Place the workflow on hold when a false-favorable, approval-like, stale,
   wrong-jurisdiction, or integrity-bypass result is plausible.
5. Preserve only authorized operational evidence. Ask `records_owner` about
   legal hold before deleting potentially responsive records.
6. Identify affected and unaffected commits, URLs, source IDs, rules,
   requirements, packets, and journeys.
7. Repair on a new commit; repeat the complete release procedure. Do not edit
   evidence receipts to make the prior release appear successful.
8. Record recovery, validation, notification decisions, residual risk, and
   follow-up owner roles.

## Records, retention, deletion, and CPRA routing

The application has no applicant record store, so it cannot search, export,
retain, delete, place on legal hold, or retrieve applicant answers. Do not turn
that technical fact into a legal conclusion that no responsive public record
exists.

Potential records may exist in the repository/release system, deployment and
configuration systems, host security logs, source-review records, support
systems, incident systems, and partner-controlled evaluation materials. The
`records_owner`, with authorized counsel or other authority as applicable,
decides scope, preservation, retention, exemptions, redaction, and response.

For a records request or legal-hold question:

1. Record receipt in the partner-approved records system, not this repository.
2. Route immediately to `records_owner`; do not promise a deadline, exemption,
   deletion, or “no records” result from this runbook.
3. Preserve potentially responsive systems when authorized; suspend ordinary
   deletion only through the owning system's approved process.
4. Search the frozen repository/release records, deployment/configuration
   records, host records made available to the partner, source/review records,
   support records, and incident records identified in the deployment
   inventory.
5. Document search systems, custodial roles, date ranges, queries, exports,
   gaps, and checksums. Confirm separately that there is no application
   applicant store or searchable applicant-field index.
6. Route review, redaction, exemptions, and release to authorized records/legal
   roles. Do not release credentials, private reviewer/participant material,
   or third-party data merely because repository evidence is portable.

Retention and deletion schedules for hosting, repository, support, incident,
and review records remain deployment-specific and `not_run`. Browser memory
ends with the page session; a user-controlled print/PDF is controlled by the
user or their device, not deletable by the application.

## Export and offboarding

The frozen schema-v1 evidence ZIP exports only its pinned 58-file
public/synthetic compatibility profile. The current schema-v2 profile exports
59 files and adds registry-aware closure; its sole substantive membership
addition is `data/workflows/registry.json`. Neither is an applicant-data
export, sensitive-record export, CPRA workflow, backup, contractual ownership
finding, or partner acceptance.

The ADR, this runbook, the beta-operations ledger, validator, and tests remain
outside profiles v1 and v2. Do not claim they are included. A future reviewed
profile/version must classify new files, update membership and assertions,
and rerun build/verify/restore.
Any operational, reviewer, participant, support, incident, or applicant
record needs a separate authorized export design.

## Rollback and hold

Before release, record a last-known-good immutable commit and URL and test the
host-specific rollback procedure. To recover:

1. Stop promotion and place the affected workflow on hold when integrity or
   false-favorable behavior is possible.
2. Use the approved host-specific procedure to redeploy the recorded
   last-known-good commit; do not rewrite Git history or mutate the old
   evidence receipt.
3. Purge/invalidate deployment caches only through the approved host procedure.
4. Run the deployment smoke command and the issue-specific regression against
   the restored URL.
5. Verify that source holds, review levels, and claim boundaries match the
   restored commit.
6. Record rollback start/end, actor role, from/to commits, reason, verification,
   gaps, and follow-up decision.

If no tested last-known-good deployment exists, keep the beta unavailable and
escalate; do not fall forward to an unreviewed commit.

## Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| Validator reports `INVALID` | Schema drift, filled approval/deployment field, weakened boundary, missing evidence file, or malformed JSON. | Stop; restore the prepared contract or propose a new schema. Do not bypass validation. |
| Smoke check fails on a subpath | Host routing/base-path or stale CDN content. | Confirm exact URL and commit, use approved cache procedure, rerun; otherwise roll back/hold. |
| Applicant answers appear in a request or log | Boundary violation or host instrumentation. | Treat as critical, hold the workflow, preserve authorized evidence, and escalate to incident/security/privacy/records roles. |
| Source changed or is stale | Currency hold applies. | Withhold affected action guidance and run the source re-verification/publication process. |
| Support receives PII/file | Reporter used an external channel outside instructions. | Restrict copying, stop redistribution, invoke that system's approved privacy/records/incident handling. |
| Browser print contains sensitive facts | User created a local artifact. | Explain the user-controlled boundary; application cannot retrieve/delete it. Escalate only if application behavior exposed data to another party. |
| An approval is requested by editing the prepared ledger | Wrong lifecycle artifact. | Refuse the edit; use a separately reviewed execution/approval schema. |

## Escalation by role

| Situation | Required roles | Channel |
|---|---|---|
| Applicant data unexpectedly transmitted, stored, or exposed | `incident_lead`, `security_owner`, `privacy_owner`, `records_owner`, `deployment_owner`, `product_scope_owner`, `jurisdiction_authority` | Partner-approved incident channel; not repository issue text |
| Credential, DNS, host, or deployment compromise | `incident_lead`, `security_owner`, `deployment_owner`, `records_owner` | Partner-approved incident channel |
| Stale source, wrong rule, false-favorable or approval-like output | `content_source_owner`, `product_scope_owner`, `jurisdiction_authority`, plus `incident_lead` for critical impact | Source-review and incident channels |
| CPRA request, legal hold, retention, deletion, or export question | `records_owner`, with authorized legal/records authority | Partner records system |
| Critical accessibility or language barrier | `accessibility_owner` or `language_access_owner`, `product_scope_owner`, `support_owner` | Approved support/escalation channel |
| Release, smoke, or rollback failure | `deployment_owner`, `security_owner`, `product_scope_owner` | Approved release/incident channel |
| Request to add account, upload, storage, telemetry, model/network call, or writeback | `product_scope_owner`, `privacy_owner`, `security_owner`, `records_owner`, `jurisdiction_authority` | Architecture-decision process before implementation |

Contact methods are intentionally absent until a partner assigns them. That
absence blocks operation; it must not be filled with personal data in this
public repository.

## Run history

| Date | Commit/URL | Run by role | Result |
|---|---|---|---|
| Not run | None | None | Prepared procedure only; no deployment or approval evidence |
