# Design

This document describes both implemented architecture and intended
extensions. `docs/PRODUCT-CONTEXT.md` is the canonical capability inventory:
**implemented** means runnable and tested, **prototype** means bounded or
simulated, and **planned** means no executable end-to-end path yet.

## Problem shape

Housing-permit guidance has three failure modes AI tends to make worse, not
better: confident wrong answers, answers that were right until the law changed,
and answers nobody can trace to a source. The design goal is to make all three
visible and mechanically checkable.

## Components

### 1. Structured intake → pathway screening (prototype)

A short structured interview (project type, applicant-supplied lot facts,
zone, jurisdiction) feeds a rules engine that emits *candidate rules*, each
with:

- route class: ministerial | discretionary | mixed
- ADU, JADU, or SB 9 applicability rationale
- generic typical-document hints on some rules
- citations: every rule carries the statute / HCD document / local code section
  it encodes, plus a `verified_on` date

Rules are JSON data with `criteria`, `citation`, `jurisdiction_scope`,
`verified_on`, and a supporting excerpt. The current runtime covers ADU,
JADU, and SB 9; it does not yet encode SB 35, AB 2011, authoritative parcel
facts, comprehensive local requirements, application-file review, or
human-reviewed detailed remedies.

The browser result surface is implemented for prototype data as a temporary
result packet. It starts with an answers-used cover sheet built from the last
submitted jurisdiction and material project facts. It then generates a count
summary and jump links for each nonempty group: candidate routes, relevant
standards, local information records, and any other matching records. One
explicitly configured candidate route for the selected project type starts
open when it is among the matches. This default is a presentation choice, not
a ranking, recommendation, final route, or eligibility finding. Supporting
records use compact disclosures. Each citation and source-status label remains
visible when its disclosure is closed.

The submitted facts, grouped summary, jump links, and disclosure state exist
only in current browser page memory. Changing the jurisdiction or any named
project answer clears the old packet and requires a new submission. The
surface does not persist an applicant record or implement parcel verification,
packet completeness, or an exportable evidence manifest. The next coherent
output is a permit-readiness evidence packet that also separates submission
completeness, consistency standards, and unresolved staff questions.

#### Plain-language explanation layer (prototype)

`data/explanations/plain-language.json` is a canonical sidecar keyed by stable
rule ID. It stores an explanation version, the linked rule's source-check
date, citation fingerprint, and full-rule fingerprint, plus display group,
AI-assisted authorship, explicit review metadata, and English/Spanish copy for:

- what this candidate result may mean;
- an optional scannable highlight group for multiple deadlines or thresholds;
- suggested next steps;
- facts or interpretations staff still need to confirm; and
- the evidence record shown separately in the interface.

`src/permit_pathways/explanations.py` requires exact rule coverage, rejects
duplicates and orphaned IDs, and fails validation when an explanation's
recorded source date, normalized citation fingerprint, or normalized full-rule
fingerprint drifts from its linked rule. The latter covers criteria, pathway,
scope, route class, notes, document hints, citation, and rule ID. A completed
review requires reviewer, method, date, and the exact explanation version
reviewed; translation review is tracked and displayed independently. The build
performs strict whole-corpus validation. At display time, malformed records
fail independently and missing Spanish copy visibly falls back to English. If
browser-side SHA-256 is unavailable or rejects, all explanation copy is
withheld while deterministic screening remains available. The rule engine
neither imports nor accepts explanation data, so copy cannot create or change
a match.

Both demos preserve the matched rule, source citation, source status, and
available excerpt when explanation copy is unavailable. In the browser result
packet, the citation and source status remain outside the expandable
explanation and evidence body. If the source is stale or unverified, both
demos deliberately withhold the action-oriented explanation, interpretive
rule notes, and generic document hints; a weak evidence record cannot become
an applicant checklist.

All current English explanations are labeled AI-assisted and not
human-reviewed. Spanish records are additionally labeled `machine_draft`;
source excerpts and document hints stay in English. Human legal/content
review, comprehension testing, and English/Spanish semantic-parity review are
required before these drafts can be treated as applicant-ready guidance.
The applicant-facing style starts with the practical consequence, keeps one
condition or number per sentence, defines unavoidable legal terms, and uses
direct questions for unresolved facts. The structured highlight group is used
for the ADU review deadlines so the 15-business-day and conditional 60-day
rules are not compressed into one paragraph.

### 2. Bounded packet-presence evaluation (prototype)

`src/permit_pathways/readiness.py` implements a deterministic evaluator for
one City of Woodland preapproved detached ADU workflow. Its canonical inputs
are separate portable records:

- `data/readiness/workflows/woodland-preapproved-detached-adu.json` binds 25
  requirements and their conditions to one dated City checklist and content
  digest;
- `data/readiness/samples/woodland-preapproved-adu.json` provides one labeled
  synthetic project, explicit fact provenance, and an inventory status for
  every requirement; and
- `data/readiness/remedies/woodland-preapproved-detached-adu.json` stores
  display-only AI-assisted action drafts with workflow and requirement
  fingerprints, a version, and explicit review metadata.

The evaluator checks exact schema coverage, stable identifiers, parent-child
ordering, workflow applicability, conditional requirements, source bindings,
and source age. Runtime and CLI defaults use the current UTC date for source
currency; historical replay requires an explicit date. The result records
both the source-status date and the review deadline. It never treats an
unknown condition as favorable. Findings use `present`, `missing`, `not
applicable`, `conflicting`,
`needs staff review`, or `not evaluated`. Even an all-present inventory uses
`no_known_gaps_in_bounded_manifest`, never `complete`. A changed or stale
source moves every bound item to staff review.

`ReadinessResult.to_manifest()` produces a deterministic evidence record with
source bindings, facts, inventory, per-item findings, source locators,
fingerprints, staff questions, and the prototype boundary.
`src/permit_pathways/readiness_cli.py` exposes the same path on the command
line. `scripts/build_demo_bundle.py` runs the Python evaluator at build time,
commits the generated evidence JSON, and embeds the result in the static
bundle. `prepare.html` validates and renders that generated result. The
browser does not contain a second packet evaluator.

The checklist mapping and action wording are recorded as AI-assisted,
`prototype_review_pending` drafts. Remedy copy cannot affect evaluation.
Mapping metadata records its version, date, exact input-source fingerprints,
and review scope. Provider and model are `unknown`, and no reproducible run
record is retained, so the artifact does not support a model-performance or
reproduction claim.
Completed review metadata would have to name the reviewer, method, date,
exact version, and reviewed content fingerprint. No such review is recorded.
No model runs in the evaluator, CLI, build, or public browser, and no applicant
data is stored or sent to a model.

This slice compares reported item presence against one checklist. It does not
open files, verify parcel facts, evaluate document contents or consistency,
determine legal sufficiency, certify completeness, limit staff requests, or
predict approval. The sample is made up and has not been validated by an
applicant, planner, Woodland staff member, counsel, or another jurisdiction
representative.

### 3. Citation-grounded Q&A (planned)

For free-text questions the deterministic core can't answer, a retrieval layer
over the jurisdiction's corpus (state law, HCD guidance, local zoning/municipal
code) answers **only from retrieved text, with the citation inline**. Abstention
is a first-class outcome: no supporting passage → "this needs staff review,"
with a routing hint. Bilingual output (EN/ES) from the same grounded passage.

No free-text Q&A or live LLM/NLP layer is currently implemented. The existing
abstention path is a structured intake with no matching encoded rule.

### 4. Currency & verification harness (prototype differentiator)

- **Golden set:** 29 structured intake records map to expected rule IDs.
  They are regression fixtures, not natural-language answer, citation, or
  jurisdiction-acceptance evaluations.
- **Verification runner:** replays the deterministic matcher, checks recorded
  verification dates, and can mark citation-matched sources stale.
- **Currency watcher:** monitors the source corpus (statute text, HCD guidance,
  and selected local-source pages) for hash changes. Seventeen sources are
  watched. New-law discovery and durable changed-state persistence are not
  implemented; stable source dependency IDs are.
- **Public trust surface:** the dashboard shows date-based rule status and a
  labeled amendment rehearsal. It does not currently ingest persisted output
  from the scheduled watcher.

The target dependency model is:

`source ID → provision → rule/check → golden case → applicant/staff output`

The bounded readiness slice also records:

`source ID → requirement → finding → synthetic packet evidence manifest`

A changed or unreachable source should create a durable review queue for all
affected nodes while proving that unrelated nodes remain current.

### 5. Static delivery (implemented)

The browser showcase remains dependency-free and static-host friendly.
Canonical rules, explanations, registries, fixtures, checks, and source
metadata stay in JSON. `scripts/build_demo_bundle.py` deterministically
compiles those files into `data/demo-data.js`. The static surface is split by
user job:

- `index.html`: lightweight orientation and scope; it loads no data bundle;
- `check.html`: applicant intake, a temporary grouped result packet, a labeled
  shareable sample that reuses a canonical golden fixture, and the separate
  clock;
- `prepare.html`: the generated synthetic Woodland packet-presence result and
  evidence-manifest link;
- `review.html`: bounded ordinance-text screen; and
- `evidence.html`: source status, regression summary, and change rehearsal.

The four data-driven pages load the generated bundle before shared,
page-gated `assets/demo.js`. Relative URLs let all five pages work from disk
and under a project subpath. The stdlib server exposes the same pages, keeps
`/showcase` as an alias for `/check.html`, and limits static-file access to
those five HTML files plus `assets/` and `data/`.

The generated bundle must never become a second hand-edited source of truth;
the test suite compares it byte-for-byte with the canonical JSON inputs and
checks the committed readiness evidence against a fresh Python evaluation.
Visual primitives follow the published California Design System token
vocabulary and California Web Standards principles; the exact adoption and
product-specific extensions are documented in `docs/DESIGN-SYSTEM.md`.
The current build-time and browser boundaries are documented in
`docs/DATA-FLOW.md`.

## Cross-cutting requirement mapping

| Challenge requirement | Current evidence | Next gap |
|---|---|---|
| Privacy (Info Practices Act, Gov C §§ 11015.5/11019.9) | Public demo persists no applicant input. The packet page uses one committed synthetic record and makes no runtime model call. | Deployment data inventory, flow, purpose, access, retention/deletion, subprocessors, and privacy review. |
| Jurisdiction data ownership | Rules, corpus, fixtures, and source metadata use open repository formats. | Tested full export/offboarding once any hosted or case data exists. |
| CPRA (Gov C § 7920.000 et seq.) | No applicant record store exists. | Deployment-specific retention, search/export, legal-hold, exemption handling, and audit design; no blanket compliance claim. |
| Low-capacity affordability | Dependency-light Python core and static-friendly browser demo. | Pilot deployment/TCO evidence and an integration contract beside existing systems. |
| Keep pace with legislative change | Selected-source hash watcher, stable source IDs with explicit rule dependencies, date aging, and staleness rehearsal. | Source discovery, persisted source state and review queue, broader local-source coverage, and human approval history. |
| Decision support, not legal agent | Candidate labels, source links, disclaimers, visible unverified state, and abstention. | Ensure stale and unverified rules cannot appear as actionable green results. |
| SAM 5300 / SIMM / accessibility | Static WCAG 2.2 AAA-target audit and a versioned `not_run` human-validation matrix; no-storage demo reduces the current data boundary. | Execute the human/AT matrix, then complete the threat model, control mapping, incident path, and deployment security review. |

## Demo plan (for the 40-minute showcase slot, if selected)

1. Start on the landing page to state the prototype boundary, then open
   `check.html?sample=adu`. The labeled hypothetical Woodland facts are
   submitted through the normal intake and matcher path. Show the temporary
   answers-used cover sheet, dynamic group summary and jump links, one
   candidate route open by default, compact supporting records, and
   always-visible citations and source status. These are prototype candidate
   rules and generic document hints, not a complete application checklist.
   Change one answer to show that the old result is invalidated until the form
   is submitted again.
2. Continue to `prepare.html`. Show the 25 source-bound requirements, three
   known gaps, five items needing confirmation, the review-pending
   AI-assisted action wording, and the generated evidence manifest. State that
   the Python evaluator compared explicit synthetic inventory statuses and
   never opened a file or verified a parcel.
3. Select an unsupported fact combination → visible abstention + staff routing
   (current trust moment; free-text Q&A remains planned).
4. Use the ordinance-review page to flag a documented sample provision.
5. On Evidence & updates, simulate a statute change → watch dependent answers
   flip to stale → open the applicant guide in that state (Scenario C
   rehearsal, the differentiator).

The stronger next demo extends the synthetic packet-presence slice with
reviewed local requirements and remedies, sourced parcel facts, real or
properly redacted file evidence, and a changed-source impact queue.

## Non-goals for v1

- Scenario B (live status, staff report generation, plan-check). The evidence
  architecture can extend there, but v1 does one thing well, per the
  challenge's "start small" principle.
- Being an authoritative legal source. Ever.
