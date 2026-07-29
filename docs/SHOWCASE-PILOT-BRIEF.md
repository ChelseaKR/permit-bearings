# Small-jurisdiction ADU pilot brief

Status: deployment hypothesis for discussion. This is not an active pilot, a
binding quote, or evidence from a prior deployment.

## Proposed outcome

Configure Permit Bearings for one California jurisdiction and one new detached
ADU workflow. The proposed 8 to 12 week result assumes applicant-supplied
project and parcel facts, each labeled as an assertion. It does not assume a
live parcel or permitting-system connection. A usable first result would let a
person receive:

- a candidate route produced by deterministic criteria;
- the state and local records that may apply;
- a locally reviewed list of submission materials for that workflow;
- direct questions for facts the system cannot verify;
- a visible source record and source status for each published rule; and
- an evidence manifest that the jurisdiction can export and retain.

This pilot would not approve a permit, certify legal compliance, perform full
building-code plan review, or encode the jurisdiction's entire development
code.

## Reference jurisdiction

The planning assumption is a small jurisdiction with limited technical staff.
It has a published ADU ordinance, application form, checklist, procedures, and
agency calendar. It can designate a planning or building subject-matter expert
and identify its legal, language-access, accessibility, privacy, security, and
records-review process.

The current public prototype is the starting point. It already demonstrates
deterministic matching, source-linked results, review-pending explanation
drafts, uncertainty routing, source-status handling, and portable data files.
Parcel retrieval, packet-level completeness, locally approved explanations,
and an administrative review queue are not currently implemented.

## Proposed scope

In scope:

- one new detached ADU route;
- one jurisdiction's official ordinance, form, checklist, procedures, and
  closure calendar;
- synthetic or properly redacted test projects;
- a locally owned rule, source, question, and document-requirement set;
- explicit unknown and staff-review states;
- a read-only parcel and zoning data feasibility assessment;
- applicant and staff usability sessions;
- source-change and rollback rehearsal; and
- export of rules, evidence, review metadata, and test cases.

Out of scope:

- production applicant accounts or document uploads;
- autonomous legal interpretation;
- comprehensive local-code coverage;
- SB 35, AB 2011, entitlement review, or building-code plan review;
- replacement of the jurisdiction's permitting system;
- automated approval or compliance certification; and
- a production integration unless separately approved after security and
  privacy review.

## Proposed 8 to 12 week sequence

This is a planning estimate, not a prior deployment result.

The estimate assumes one English-language workflow, applicant-supplied parcel
facts, a complete source package at kickoff, synthetic test projects,
file-based review, timely jurisdiction decisions, and no production
integration, accounts, uploads, hosting authorization, or Spanish semantic
review. The delivery team and capacity are not yet identified. Do not use the
estimate until that team confirms it. Re-estimate if any assumption changes.

### 1. Confirm the workflow and evidence

Select the route, identify authoritative sources, map decision points, and
record unresolved legal or procedural questions. Confirm which agency record
controls when sources conflict.

### 2. Encode the local layer

Add stable source and rule identifiers, objective criteria, required materials,
dependencies, citations, excerpts, source dates, and synthetic golden cases.
Keep explanation drafts separate from matching logic.

### 3. Add packet-readiness behavior

Represent the jurisdiction's actual required materials for the selected route.
Distinguish whether an item is present from whether it is consistent or legally
sufficient. Route unsupported, conflicting, and parcel-dependent questions to
staff.

### 4. Review and test

Replay positive, negative, boundary, ambiguous, and wrong-jurisdiction cases.
Have designated reviewers evaluate legal fidelity, applicant comprehension,
staff usefulness, language parity if Spanish is included, and accessibility.
Record reviewer, method, date, version, and disposition.

### 5. Exercise operations

Rehearse a source change, identify every dependent output, reject stale
guidance, restore an approved revision, and export the complete evidence set.
Document ownership, access, retention, deletion, records retrieval, and
support responsibilities before any production data is accepted.

## Jurisdiction participation

Proposed staff participation:

- a planning or building subject-matter expert to identify the workflow and
  review encoded criteria;
- a form or permit-program owner to confirm required materials and remedies;
- counsel or an authorized policy reviewer according to local practice;
- information technology, security, privacy, accessibility, language-access,
  and records staff at the points required by jurisdiction policy; and
- a named owner for future source review and rule approval.

The prototype has no administrative workbench. During a pilot, authoring and
review would be collaborative and file-based. A production review interface is
separate scope.

## Data and integration posture

The pilot would begin with official public sources and synthetic or properly
redacted project facts. No production applicant record is required to
demonstrate the workflow.

Potential inputs:

- local ordinance and published procedures;
- application forms and checklists;
- agency closure calendar;
- parcel, zoning, overlay, and authoritative GIS sources;
- permit-system field definitions and status codes; and
- review and records-retention policies.

The proposed first result does not require a live connection. A read-only
export or documented API is a separate feasibility assessment and could become
later scope only after the jurisdiction and delivery team revise the estimate.
Rules, source records, review artifacts, geographic data, and test cases use
portable formats that can be inspected without vendor-only tooling. Ownership,
operational export, and offboarding terms require agreement. Any later storage,
identity, upload, telemetry, external model call, or write-back integration
requires a documented data flow and deployment-specific approval.

## Acceptance evidence

A pilot should not be called successful only because the software runs.
Evidence should include:

- deterministic replay passes for the agreed scenario set;
- no unknown material fact silently treated as favorable;
- each published rule linked to an official source and dated evidence record;
- explanation display fails closed when version or source fingerprints drift;
- a source-change rehearsal identifies affected and unaffected controls;
- packet presence is reported separately from consistency or compliance;
- applicant and staff observations are recorded with method and participant
  profile;
- accessibility findings distinguish automated checks from human
  assistive-technology testing;
- language review is recorded separately from English legal review; and
- a complete jurisdiction-owned export can be opened without vendor-only
  tooling.

Proposed outcome measures must be agreed before testing. Examples include
task completion, correctly routed synthetic cases, unresolved questions
identified before submission, and staff time spent on the selected routing
task. No reduction in delay, rework, or staff time has yet been measured.

## Decisions still needed

- legal entity and delivery team;
- target jurisdiction and designated reviewers;
- exact ADU route and authoritative local source set;
- whether parcel data is available through an authoritative read-only source;
- whether Spanish is included and who can review semantic parity;
- security, privacy, records, accessibility, and hosting requirements;
- support and source-review ownership after the pilot;
- total cost and procurement path; and
- whether 8 to 12 weeks is acceptable as the submission planning estimate.
