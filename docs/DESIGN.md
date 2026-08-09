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
packet completeness, or an exportable evidence manifest. For every recognized
city or county, it can derive a bilingual print-focused orientation receipt
from those same in-memory facts and matches. The receipt reports candidate
route sources and currency, explicitly distinguishes the statewide baseline
from bounded local coverage, and carries questions to local staff. It is not
stored and does not generalize a local packet workflow. The bounded Woodland
continuation demonstrates the deeper portable output: a print-focused view of
its integrity-checked synthetic route and packet evidence. A real
permit-readiness record that separates submission completeness, consistency
standards, and unresolved staff questions remains planned.

#### Statewide Coverage Navigator (implemented surface for prototype data)

At a recognized jurisdiction selection, before the applicant supplies or
submits project facts, `check.html` presents a static coverage profile. The
profile is generated at build time by `src/permit_pathways/jurisdictions.py`
into `data/jurisdictions/generated/coverage-index.json`, then carried in the
browser bundle as `coverage_index`. It joins the portable jurisdiction
registry, the bounded rule corpus, and the dated public HCD Housing
Accountability Unit history without making a browser request or retaining a
selection as an applicant record.

The compact schema-version-1 index contains only the 17 statewide rule IDs,
per-jurisdiction local rule IDs and HCD-record counts, and HCD source/date/
count metadata. It leaves the source HCD rows in their canonical dataset and
does not classify or interpret them. Build validation rejects rule scopes or
HCD slugs that do not resolve to a registry entry, malformed or future HCD
retrieval dates, and HCD-count drift.

Each profile makes three independent boundaries visible:

- the same bounded statewide ADU/JADU/SB 9 candidate-rule inventory is
  screenable for every registry entry;
- a local layer is either `not encoded` or a limited set of existing
  jurisdiction-scoped source records, neither of which is comprehensive
  local-code or packet coverage; and
- public HCD correspondence linked in the committed, dated dataset is
  historical reference material, not a current ordinance, compliance,
  eligibility, or approval conclusion. The absence of linked correspondence does not
  establish no HCD activity, compliance, or complete data coverage.

The profile also consumes the repository-adopted source-state overlay. A
changed dependency puts the affected statewide inventory count or individual
local source record on a visible review hold; the raw local citation remains
available as evidence but the profile does not present it as ready for
screening or coverage. An unverifiable source is kept distinct and does not
create a stale hold.

The profile also displays a local-onboarding checklist rather than silently
filling gaps: operative ordinance sections and effective dates;
current forms, checklist, fee, and process pages; official URLs, source-check
dates, and content fingerprints; project/parcel scope, exceptions, and open
questions; and a named review owner with a re-verification cadence. A source
link alone cannot create a local rule. The checklist is not an uploader,
authoring workflow, or validation of those future inputs. The navigator is
therefore a bounded statewide routing aid, not an ordinance scraper,
local-code finder, parcel lookup, local compliance determination, or statewide
permit service.

One bounded browser continuation is implemented for the canonical made-up
Woodland sample as a **source-bound future-state simulation**. The City's
official program page, checked 2026-08-09, says **“Preapproved ADU List: Coming
soon!”**; no listed City plan was identified. The continuation is therefore
not a currently usable preapproved-plan or applicant-ready workflow. It
appears only while that sample remains active and unedited, its results exactly
match the bound golden route, every journey and readiness fingerprint
validates, the route and readiness sources remain inside their review windows,
and a strict date-bound program-availability record remains valid. The browser
blocks a missing, malformed, or expired availability record. The remaining
workflow-applicability fact has no default. **Yes** exposes a versioned
packet-simulation link; **No** or **I'm not sure** withholds it. **Yes** cannot
establish that a City plan exists. This continuation does not turn the
temporary route result into a stored applicant evidence packet. On an exact
valid simulation entry, it can compose a print-focused synthetic summary
without persisting or transferring applicant facts.

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
one simulated City of Woodland preapproved detached ADU workflow. This is an
implementation exercise against source-bound prototype data, not evidence
that Woodland currently lists a plan. Its canonical inputs are separate
portable records:

- `data/readiness/workflows/woodland-preapproved-detached-adu.json` binds 25
  requirements and their conditions to one City checklist, source checked
  2026-07-29, and its content digest. The checklist is not represented as
  inherently dated. The workflow also binds two synthetic parcel-fact
  definitions to exact fields in Yolo County public parcel-layer metadata;
- `data/readiness/samples/woodland-preapproved-adu.json` provides one labeled
  synthetic project, explicit applicant-assertion or
  `synthetic_public_record_fixture` provenance, source metadata for the two
  fabricated parcel values, and an inventory status for every requirement;
- `data/readiness/remedies/woodland-preapproved-detached-adu.json` stores
  display-only AI-assisted action drafts with workflow and requirement
  fingerprints, a version, and explicit review metadata. The generated
  browser record adds a content fingerprint for drift detection; that
  fingerprint is not a human-review receipt.

Program availability is a separate, non-matching boundary.
`data/availability/woodland-preapproved-adu-program.json` strictly records the
official program URL, 2026-08-09 check date, exact excerpt and fingerprint,
`plans_not_listed` status, future-state boundary, and recheck deadline.
`src/permit_pathways/program_availability.py` validates that schema but is
isolated from deterministic screening and readiness evaluation, so it cannot
create a match or make the workflow applicable. Bundle format 5 carries the
record to the browser, which blocks route-to-packet access when it is missing,
malformed, or expired. A passing availability check authorizes only display of
the labeled simulation.

The evaluator checks exact schema coverage, stable identifiers, parent-child
ordering, workflow applicability, conditional requirements, fact-to-source
field/date bindings, synthetic-record boundaries, source bindings, and source
age. Runtime and CLI defaults use the current UTC date for source currency;
historical replay requires an explicit date. The result records both the
source-status date and the review deadline. It never treats an unknown
condition as favorable. Findings use `present`, `missing`, `not applicable`,
`conflicting`,
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

After those same entry, integrity, current-source, and program-availability
checks pass,
`prepare.html` also derives a print-focused summary from the normalized journey
and readiness objects. It combines the candidate route and source status,
labeled synthetic facts, the three reported-missing actions, direct staff
questions, route/checklist/parcel-metadata evidence, boundary text, and the
public journey ID/version. Its native button calls the browser print dialog;
the action block retains its AI-assisted, review-pending, not-human-reviewed
label. Print CSS isolates the summary while the browser owns Print/Save as
PDF. No second evaluation, app-side file generation, upload, or storage is
introduced.

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

This future-state slice compares reported item presence against one checklist. Two
fabricated parcel values demonstrate how exact public dataset fields and
source dates travel into an evidence manifest. It does not query or verify a
live parcel, open files, evaluate document contents or consistency, determine
legal sufficiency, certify completeness, limit staff requests, or predict
approval. The sample is made up and has not been validated by an applicant,
planner, Woodland staff member, counsel, or another jurisdiction
representative. It is not currently available to a Woodland applicant.

#### Versioned Woodland journey contract (implemented data and browser contract)

`data/journeys/woodland-preapproved-detached-adu.json` is a strict,
reference-only definition that joins the existing synthetic Woodland golden
screening case and candidate route to the bounded readiness workflow and
packet. `src/permit_pathways/journey.py` resolves those references at build
time, replays the deterministic screening case, and reuses the existing
readiness result rather than evaluating the packet a second time. Resolution
fails closed unless the route matches the complete named fixture and is
inside its source-review window on the sample's recorded evaluation date, the
screening and readiness scopes agree, the packet is synthetic, and the
readiness result explicitly reports that the workflow applies.

The generated envelope includes resolved route evidence with its source-status
as-of date and review deadline, the emitted shared synthetic fact envelope
with per-fact provenance, the applicability facts and applicant-editable
subset, the complete readiness evidence manifest, and fingerprints for the
screening case, rule, shared fact envelope, workflow, packet, and journey.
`scripts/build_demo_bundle.py` writes it to
`data/journeys/generated/woodland-preapproved-detached-adu.json` and includes
it in `data/demo-data.js`.

The browser consumes this envelope as a fail-closed transition for the active,
unedited canonical sample. It independently checks the linked golden result,
candidate route, applicability provenance, route/readiness evidence,
fingerprints, current source-review windows, and the separate strict
program-availability record. Only a current, well-formed record and an
explicit matching applicability answer expose
`prepare.html?journey=<public-id>&version=<version>`; the other answers preserve
the not-applicable boundary or exact staff question. The URL contains no
project answers, and the browser uses no local or session storage, cookies, or
server-side applicant record. This is a future-state simulation URL, not
evidence that the City has listed or preapproved a plan.

`prepare.html` accepts exactly the supported journey ID and version and reruns
the contract, source-currency, and program-availability checks before showing
packet findings. Direct, malformed, duplicated, extra, mismatched, stale, or
expired-availability entry fails closed. The printable view is one replayable
future-state synthetic journey summary, not authorization, a currently listed
City plan, a real or persisted applicant case, a completeness or eligibility
finding, an official checklist, or jurisdiction-approved packet.

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
- **Verification-level ledger (implemented evidence surface, no promoted
  rules):** schema version 2 in
  `src/permit_pathways/rule_verification.py` and
  `data/validation/rule-verification.json` adds explicit `machine_linked` /
  `human_reviewed` / `jurisdiction_approved` levels on top of the bare
  `verified_on` date. A promotion must bind both the exact citation
  fingerprint and exact full-rule fingerprint, which covers every rule field
  that affects meaning. Citation drift, full-rule drift, a changed source
  dependency, source age, or review age demotes the effective claim to
  `machine_linked`. The ledger never changes which rules match an intake.
  `python -m permit_pathways.harness` prints effective-level counts and the
  exact bounded automation phrase `automated source/regression checks: pass`
  when those checks pass. Bundle format 5 exposes the same effective coverage
  on `evidence.html`: all 19 rules are currently `machine_linked`, with zero
  named human reviews and zero jurisdiction approvals.
- **Currency watcher:** monitors the source corpus (statute text, HCD guidance,
  and selected local-source artifacts) for hash changes. Nineteen sources are
  watched, including the current Davis handout and the HCD letter that records
  its unresolved ordinance-status issue; the blocked Davis municipal-code host
  remains an unwatched reference. Every run classifies each watched source as
  `unchanged`, `changed`, or `unverifiable`. Only a source that was actually
  fetched can be called changed; a fetch that fails after its retry budget is
  `unverifiable`, carries the last successful verification date, and marks no
  rule stale. When requested, the watcher also emits a complete proposed
  source-state receipt with observed digests, the run/commit binding, and
  exact affected and unaffected rule/Golden IDs. The scheduled workflow keeps
  that proposal as a 30-day artifact and never adopts it automatically.
- **Reviewed publication overlay:** `src/permit_pathways/source_state.py`
  validates one deliberately adopted receipt in
  `data/source-status/current.json`. A public bundle requires receipt status
  `reviewed`, binds it to the current source registry, re-derives every
  observation and direct rule/Golden impact, and fails closed on drift. Here,
  `reviewed` means selected by repository maintenance for publication; it is
  not legal, jurisdiction, counsel, or substantive content approval and does
  not identify a human reviewer.
- **Public trust surface:** bundle format 5 carries the adopted overlay, rule
  verification ledger, and strict program-availability record to the browser
  as distinct claims. Exact changed dependencies stale statewide rule cards and
  orientation receipts. A changed candidate-route source blocks the Woodland
  handoff; a changed checklist or parcel-metadata binding withholds the
  Woodland findings, actions, and print summary. Independently, missing,
  malformed, or expired official program-availability evidence blocks the
  future-state simulation. An unrelated changed source leaves those local
  surfaces available. An unverifiable source produces a warning and does not
  stale a dependent. The evidence page exposes review levels without implying
  review. The § 66321 amendment control is a separate temporary layer and
  never rewrites the committed receipt.

New-law discovery, automatic receipt adoption/publication, a named reviewer
record, and a staffed re-verification assignment workflow are not implemented.

The implemented bounded dependency model is:

`source ID → provision → rule/check → golden case → applicant/staff output`

The bounded readiness slice also records:

`source ID → requirement → finding → synthetic packet evidence manifest`

The versioned Woodland contract composes the two bounded traces as:

`golden case + candidate route current on the recorded date + applicable readiness evidence → synthetic journey envelope`

The separate availability boundary gates display without entering either
decision path:

`official program page → strict date-bound availability record → future-state simulation hold/display`

A fetched changed source creates the public review hold described above while
preserving explicit unaffected controls. The exact persisted impact list
covers rules and Golden cases; journey and readiness effects are re-derived
from their source bindings in the browser. An unreachable source creates a
warning, not a change claim. Packet-field assignments and human ownership of
the queue remain planned.

### 5. Static delivery (implemented)

The browser showcase remains dependency-free and static-host friendly.
Canonical rules, explanations, registries, fixtures, checks, source metadata,
the generated jurisdiction-coverage index, the program-availability record,
rule-verification ledger, and adopted source-state receipt stay in JSON.
`scripts/build_demo_bundle.py` deterministically compiles those files, the
generated readiness record, the generated journey envelope, and the strict
source-state overlay into `data/demo-data.js`. The static surface is split by
user job:

- `index.html`: lightweight orientation and scope; it loads no data bundle;
- `check.html`: a generated Statewide Coverage Navigator after a recognized
  jurisdiction selection, applicant intake, a temporary grouped result packet,
  a statewide orientation receipt, a labeled shareable sample that reuses a
  canonical golden fixture, its explicit applicability gate, and the separate
  clock;
- `prepare.html`: a fail-closed versioned and availability-gated entry to the
  generated future-state Woodland packet-presence simulation,
  evidence-manifest link, and print-focused journey evidence summary;
- `review.html`: bounded ordinance-text screen; and
- `evidence.html`: adopted source-state receipt, source status, derived review
  queue, rule-review coverage, regression summary, and separate change
  rehearsal.

The four data-driven pages load the generated bundle before shared,
page-gated `assets/demo.js`. The applicant page resolves a coverage profile
only for a recognized registry value; it does not infer an unlisted local
source or carry a profile selection into the packet URL. Relative URLs let all
five pages work from disk and under a project subpath. The stdlib server
exposes the same pages, keeps `/showcase` as an alias for `/check.html`, and
limits static-file access to those five HTML files plus `assets/` and `data/`.

At phone widths, the full primary link row is replaced by a native
`details`/`summary` section menu while preserving current-page semantics and
44–48px targets without adding navigation JavaScript. Multi-column content
collapses to one column, primary task actions span the available width, and
the evidence tables render as labeled source/rule records instead of requiring
horizontal page scrolling. Browser checks exercise every page at 320px and
390px plus populated applicant and evidence states. They also exercise the
statewide handoff across an ordinary city, a county, post-2020 Mountain House,
and Davis's bounded local layer. The generated coverage index separately
represents normal-city, county, post-2020 Mountain House, limited-local-layer,
and linked/no-linked-HCD-history states without conflating any of them with
local-code coverage. An automated navigator test also exercises Albany's
zero-HCD state, Alameda's linked HCD disclosure, Davis's limited local layer,
and Los Angeles County's `Not encoded` state; it verifies the 17-record
baseline, storage boundary, no document overflow, and an axe scan. Dedicated
assistive-technology, keyboard-only, and physical-device coverage remains
pending.
Separate print-media checks confirm that each print-focused summary remains
visible while navigation, task chrome, detailed results, and print controls
are withheld without horizontal document overflow. Physical-device,
printed-output, and assistive-technology validation remain separate manual
work.

The generated bundle must never become a second hand-edited source of truth;
the test suite compares it byte-for-byte with the canonical JSON inputs and
checks the committed readiness evidence and journey envelope against fresh
Python resolution.
All five pages load `assets/california-design-system.css` before
`assets/site.css`. The first asset is the locally maintained California Design
System version-0 preview compatibility layer: it provides selected semantic
`ca-*` structures for buttons, fields, shouts, boxes, meshes, and table
treatments, plus the shared `#skip-to-content` pattern. The second asset owns
Permit Bearings composition and the product-specific service header/footer,
decision and evidence records, status chips, journey rail, and print packet.
Native disclosures remain native.

The optional Python-rendered `/`, `/screen`, and `/trust` reference routes use
the same two style assets and additive component classes on native form,
notice, card, action, and table elements. Their small inline style block is
scoped to reference-flow composition; it no longer defines a separate visual
token or component system.

The local layer is compared with successor-system commit
`f8775cfac090de08b9e0083eb3008bd585f33e91` (2026-01-27), not imported from it.
The successor is pre-Alpha, has no production-supported release, and its
repository/package licensing is not yet unambiguous enough for this project to
redistribute its source or bundle. The static site therefore has no upstream
runtime dependency. Archived, MIT-licensed `cagov/design-system` material
remains the documented source for adapted legacy tokens and the local Public
Sans files; the fonts retain their separate SIL Open Font License 1.1.

This boundary is component alignment, not conformance or certification. The
product-specific header intentionally omits the State banner, logo, wordmark,
and agency identity; the prototype does not represent an official California
site or State endorsement. The exact adoption and extensions are documented
in `docs/DESIGN-SYSTEM.md`.
The current build-time and browser boundaries are documented in
`docs/DATA-FLOW.md`.

## Cross-cutting requirement mapping

| Challenge requirement | Current evidence | Next gap |
|---|---|---|
| Privacy (Info Practices Act, Gov C §§ 11015.5/11019.9) | Public demo persists no applicant input. Its handoff URL carries only a public journey ID and version; the packet page uses one committed synthetic record and makes no runtime model call. | Deployment data inventory, flow, purpose, access, retention/deletion, subprocessors, and privacy review. |
| Jurisdiction data ownership | Rules, corpus, fixtures, and source metadata use open repository formats. | Tested full export/offboarding once any hosted or case data exists. |
| CPRA (Gov C § 7920.000 et seq.) | No applicant record store exists. | Deployment-specific retention, search/export, legal-hold, exemption handling, and audit design; no blanket compliance claim. |
| Low-capacity affordability | Dependency-light Python core and static-friendly browser demo. | Pilot deployment/TCO evidence and an integration contract beside existing systems. |
| Keep pace with legislative change | Selected-source hash watcher, proposed run artifacts, a strict repository-adopted source-state overlay, exact rule/Golden impact, applicant-output holds, date aging, and a separate staleness rehearsal. | New-law discovery, automatic adoption/publication, staffed assignment, packet-field queue records, broader local-source coverage, and human approval history. |
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
   is submitted again. Restore the canonical sample and show the official-page
   record: checked 2026-08-09, it says **“Preapproved ADU List: Coming soon!”**
   State that this makes Woodland a source-bound future-state simulation, not
   a currently usable plan or applicant-ready workflow. A missing, malformed,
   or expired availability record blocks the handoff. The applicability
   question has no default: **No** and **I'm not sure** withhold the packet
   simulation, while **Yes** exposes the versioned link only when the
   availability record passes.
2. Follow that simulation link to `prepare.html`. Point out that the URL
   contains only a public journey ID and version. Show the 25 source-bound
   requirements from the checklist source checked 2026-07-29, three
   known gaps, five items needing confirmation, the review-pending AI-assisted
   action wording, and the generated evidence manifest. Show the print-focused
   summary's candidate route, labeled made-up facts, three preparation actions,
   direct staff questions, source evidence, boundary, and ID/version on one
   portable surface. State that Print/Save is the browser's operation and that
   the app stores no export. The Python evaluator compared explicit synthetic
   inventory statuses and never opened a file or verified a parcel. Direct or
   invalid or availability-blocked entry withholds both findings and summary.
3. Select an unsupported fact combination → visible abstention + staff routing
   (current trust moment; free-text Q&A remains planned).
4. Use the ordinance-review page to flag a documented sample provision.
5. On Evidence & updates, show that all 19 current rules are
   `machine_linked`, with zero named reviews. Explain that schema-v2 promotion
   binds citation and full-rule fingerprints and demotes on source change,
   source age, or review age. Then simulate a statute change → watch dependent
   answers flip to stale → open the applicant guide in that state (Scenario C
   rehearsal, the differentiator).

The stronger next demo moves the future-state slice to an active jurisdiction
workflow with reviewed local requirements and remedies, sourced parcel facts,
real or properly redacted file evidence, and a changed-source impact queue.

## Non-goals for v1

- Scenario B (live status, staff report generation, plan-check). The evidence
  architecture can extend there, but v1 does one thing well, per the
  challenge's "start small" principle.
- Being an authoritative legal source. Ever.
