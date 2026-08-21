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

The applicant intake remains one native form rather than a scripted wizard.
Three visible stage labels—place, project, and details—plus a restrained
California-token bearing rail expose the sequence without hiding later
questions or creating client-side navigation state. The language toggle stays
beside the form heading; the shareable sample keeps its made-up-data boundary
and adds a direct result jump only while the canonical sample is active.
One project-specific machine-generated local WebP illustration appears beside the project-check
introduction on wider screens and is omitted at the single-column breakpoint,
so it adds orientation without competing with the form. The landing uses a
second project-specific illustration in the same published-token palette. Both are
decorative, contain no interface copy or approval mark, and make no product or
legal claim.

The browser result surface is implemented for prototype data as a temporary
result packet. After a count summary and group links, it renders the candidate
route before relevant standards, local information, and other matching
records. The configured candidate route has stronger visual hierarchy, but
every longer explanation, next-step, and evidence body starts closed. This is
a presentation choice, not a ranking, recommendation, final route, or
eligibility finding. Each consequence, citation, and source-status label
remains visible when its disclosure is closed. Temporary answers used and the
statewide staff handoff follow all matching records in separate closed native
disclosures. Directly below the result heading, a
semantic decision-boundary note states what the result shows, what is still
unconfirmed, and the next jurisdiction-staff step. Its state is derived from
the same result and source overlay: candidate, unresolved material fact,
no route in the bounded rule set, or source review required. Candidate cards
use a non-approval heading and separately retain the exact rule pathway name.

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
submits project facts, `check.html` presents a closed native disclosure whose
summary names the jurisdiction and bounded record counts. Its body contains a
static coverage profile. The
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
questions; and an accountable review-owner role with a re-verification cadence. A source
link alone cannot create a local rule. The browser checklist is not an
uploader or authoring workflow. A separate offline intake contract validates
the shape and completeness of those future inputs without publishing them.
The navigator is therefore a bounded statewide routing aid, not an ordinance
scraper, local-code finder, parcel lookup, local compliance determination, or
statewide permit service.

#### Local-source onboarding intake (implemented tooling; template not run)

`data/onboarding/local-source-intake-template.json` is a portable, generic
schema-version-1 intake with no encoded jurisdiction or local source. The
dependency-light loader and read-only CLI validate exact keys, unique sorted
stable IDs, the five required official-source roles, HTTPS URL shape, source
content fingerprints and check dates, and exact operative-passage text
fingerprints bound to the ordinance's enactment, effective, and check dates.
The same record carries project scope, parcel-fact provenance and fail-closed
unknown handling, candidate exceptions, unresolved source conflicts, direct
open questions, planned accountable source/review/approval/publication role
IDs, and a re-verification cadence. Every operative passage source must equal
the declared ordinance-role source set. Input is bounded to 1 MiB of UTF-8
JSON; duplicate keys, non-finite values, excessive nesting, malformed/control-
bearing URLs, and noncanonical metadata fail closed. Historical CLI replay is
explicitly labeled, reports its validation and earliest recheck dates, and
cannot emit current `ready_for_review: true`.

The lifecycle is intentionally one-way only as far as collection:
`not_run` → `collection_in_progress` → `prepared_for_review`. The validator
has no reviewed, approved, encoded, or published state. Review and approval
evidence fields must remain null, conflicts cannot be marked resolved, and a
fixed claim boundary says the record cannot establish operative law, create a
rule, prove comprehensive coverage, determine compliance or eligibility, or
record human or jurisdiction approval. A `prepared_for_review` intake is an
input to a future, separate fingerprint-bound review/authoring/publication
workflow; it is not that workflow and is not bundled into the public browser.
The empty template is also outside public/synthetic evidence export profiles
v1 and v2. The current schema records role IDs rather than people; a filled partner
intake could still contain unpublished candidate work and needs a separate
data-classification and export-profile decision.

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

The bounded interface dictionary is also checked as a structural catalog.
`scripts/check_applicant_copy.mjs` evaluates only the `STRINGS` declaration in
an isolated context, then requires English/Spanish key order, nested shapes,
stable option identifiers, formatter arity, static and formatter placeholders,
and nonblank singular/plural string outputs to agree. Its copy-leaf
pseudo-expansion test excludes stable option identifiers, preserves formatter
tokens, and enforces an aggregate expansion threshold. It does not generate a
runnable pseudolocale catalog or render expanded copy. This is a structural
regression check, not a translation-quality or rendered-layout evaluation; its
result deliberately leaves semantic review, Spanish applicant readiness, and
layout compatibility unclaimed.

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
create a match or make the workflow applicable. Bundle format 6 carries the
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
No model runs in the evaluator, CLI, build, or packet page, and the packet
sample sends no applicant data to a model. (The optional runtime AI service
under ADR-0004 serves the project-check page; see section 3.)

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

#### Portable workflow registry boundary (implemented infrastructure)

`data/workflows/registry.json` is the canonical selector for readiness,
packet, remedy, journey, program-availability, and generated-evidence paths.
Each input path is repository-relative, constrained to a lowercase ASCII JSON
filename in its expected direct directory, and pinned to the SHA-256 of its
bounded raw bytes. Stable workflow, packet, journey, program, and jurisdiction
IDs must agree with the referenced records. An explicit availability policy
keeps the exact Woodland source contract separate from a conservative generic
prototype contract used only in tests. That generic contract requires a fixed
negative excerpt, a source ID derived from the program ID, a canonical HTTPS
URL whose path is the program ID, and the matching excerpt fingerprint. The
loader rejects duplicate JSON keys, non-finite, recursive, or oversized
records, non-integer schema versions, symlinks and hard links, portable-name
and case collisions, and inventories each canonical input and generated-output
directory so an unregistered JSON file, duplicate ID/path, shared input/output
path, traversal, absolute path, wrong-directory path, fingerprint drift, or
orphan cross-reference fails closed.

The registry is a list boundary, and the build validates every entry.
`readiness_cli.py` selects one entry by `--workflow-id`; legacy `--workflow`
and `--packet` flags remain compatibility assertions but cannot bypass the
registered paths. `review_queue_cli.py` includes all registered contexts by
default or one explicit registered ID. Its legacy path flags are also
assertions. Neither command can register, approve, activate, or publish a
workflow.

Bundle format 6 intentionally changes the generated contract: it embeds the
exact raw registry text alongside its parsed form. The browser verifies the
raw registry SHA-256 against `generated_from`, requires the two forms to agree,
then validates the registry shape, unique portable paths, every registered
input pin, the selected default's dispatched availability policy, and artifact
IDs before using
the singular `readiness`, one-element `journeys`, and
`program_availability` aliases. Browser code cannot inventory files that were
not bundled; orphan detection remains a Python build/loader responsibility.
This repository has one registered prototype entry—the Woodland future-state
simulation. A test-only second entry is selected as a generic browser default
to prove build, browser-policy, and review-queue traversal,
but registry infrastructure is not multiple active workflows, broader local
coverage, external validation, applicant readiness, or jurisdiction approval.

### 3. Runtime AI at the edges (prototype under ADR-0004)

ADR-0004 records the owner's decision to add runtime AI in three bounded
roles through a separate optional service, `permit_pathways.ai`
(`make serve-ai`; FastAPI on `127.0.0.1:8787`; provider through the public
`anthropic` SDK, default `claude-sonnet-5`, or Amazon Bedrock), that the
static site calls only when the applicant asks for it:

- **Intake extraction** (`intake.py`, `POST /intake/extract`). The applicant
  describes the project in English or Spanish. The model returns a draft of
  the same structured facts the deterministic matcher consumes — the
  vocabulary in `facts.py`, nothing outside it — and for each value a quoted
  span of the applicant's text that supports it. The service enforces the
  allowed-value list and the quote binding; a value without a verbatim
  supporting quote becomes `unknown`. Unanswered fields are returned as
  "could not tell from what you wrote". The jurisdiction name is resolved
  against the registry deterministically. The draft pre-fills the existing
  form; the applicant confirms; only confirmed values reach `screen()`.
- **Grounded explanation** (`explain.py`, `POST /explain`). The service
  re-runs the Python matcher on the confirmed facts and refuses (409) a rule
  set that disagrees with the browser's. It indexes the corpus documents
  `data/sources.json` binds (`corpus.py`: leginfo HTML via the stdlib
  parser, PDFs via pypdf, paragraph-bounded passages), offers the model
  passages only from the matched rules' `source_dependencies` (a rule's
  own located excerpt plus lexical BM25 matches, interleaved across rules),
  and asks for claims that cite passage IDs with verbatim quotes. Every
  quote is then checked against the extracted text of the named document
  after typography, case, and whitespace folding, with a minimum length; a
  claim with an unverifiable citation is withheld and the withheld count is
  displayed beside the explanation.
- **Staff questions** (`staff_questions.py`, `POST /staff-questions`).
  Drafted for the applicant's unresolved facts, matched rules, and whether
  the jurisdiction has a local record; pointers that do not resolve are
  dropped; labeled drafts. Offered alone on the "needs staff review" state.
- **Follow-up answers** (`explain.answer_question`, `POST /ask`). One
  question, answered only from the matched rules' cited passages with the
  same verifier; abstains with a staff question when they do not settle it.
- **Budget** (`budget.py`). Every model-backed route is metered: a
  per-client sliding window and a hard daily cap (in memory locally; a
  DynamoDB conditional update when hosted). 429 `budget_exhausted` leaves the
  deterministic result untouched. The provider marks the system prompt
  cacheable so the stable prefix is reused across requests.
- **Ordinance-to-rule drafting** (`rule_drafts.py`, CLI only, not a
  service endpoint). Proposes rule entries from one ordinance text; keeps a
  proposal only if its excerpt occurs verbatim in that text, its criteria
  use the intake vocabulary, and it loads through `screening.load_rules`;
  writes a wrapper object marked `unreviewed_ai_draft` to Git-ignored
  `ai-drafts/` and refuses `data/rules`. A person authors any real rule.

The browser side is `assets/ai.js`, loaded after `demo.js` on `check.html`
and inert until the applicant presses "Use AI assistance". Only then does the
page probe `/health` on each candidate origin in the `permit-ai-service`
meta tag in order (local development first, then a hosted service), render
the free-text field, and, on the next explicit action, send anything. Each
citation links into the official source with a text fragment for the quoted
words where the source is HTML. With the service absent the page makes no
request beyond its origin, the pinned form fields are exactly what ADR-0002's
ledger describes, and the AI controls show "needs the service running". The
service URL list is the `permit-ai-service` meta tag and the page's
`connect-src`; a hosted deployment adds to both. `deploy/ai-service/` holds
a prepared AWS Lambda shape with a hard daily cap.

Open-ended question answering stays out of scope; the follow-up box answers
only within a matched result, which is what keeps the citation check exact. The evaluation set and harness
are in `evals/ai/`; the capability matrix carries the measured numbers and
their limits. Nothing in this layer is imported by the matcher, the
readiness evaluator, the build, or the bundle.

### 4. Currency & verification harness (prototype differentiator)

- **Golden set:** 29 structured intake records map to expected rule IDs.
  They are regression fixtures, not natural-language answer, citation, or
  jurisdiction-acceptance evaluations.
- **Held-out conformance evaluation contract (implemented strict evaluator
  scaffold/Python interface; planned execution):**
  `data/conformance/evaluations/heldout-v1/manifest.json` is a validated
  `not_run` record, not an evaluation result. The Python interface validates
  the plan, frozen cases, a key carrying two distinct declared blind reviewer
  records and adjudication, and blind predictions; it can generate predictions,
  score raw pairs, and exclusively
  write a receipt while returning its out-of-band SHA-256. The CLI provides
  `validate-plan`; blind `predict`, which has no answer-key argument; and
  `score`, which requires frozen predictions and the key carrying declared
  reviewer/adjudication records. `validate-result` requires the frozen cases,
  key, predictions, and result, then recomputes and validates every binding,
  pair, partition, raw count, chronology, and lifecycle field. Invalid
  input/output returns exit 2, and result writes do not overwrite. The
  interface supplies none of the external evidence. The plan pins the current
  scanner
  and nine-check registry, excludes the sources that shaped scanner
  development, and fixes `(case_id, check_id)` as the scoring unit.
  `should_flag` and `should_stay_quiet` mean only that the exact passage enters
  or stays out of one check's staff/counsel review queue; neither is a
  compliance judgment. `reference_abstain` pairs are excluded from the binary
  comparison and counted separately. The scanner itself can only flag or stay
  quiet, so `machine_abstain` is fixed at zero and an execution error fails
  the run. Each active check requires one targeted official flag pair and one
  preselected candidate near-miss quiet pair. Incidental findings do
  not satisfy that coverage; synthetic controls remain separately denominated.
  Every case is scored against every active check, preventing unexpected
  cross-check flags from being omitted. Each case has exactly one target check;
  schema v1 does not permit multi-target reuse. Raw counts must be
  reconstructable overall, per check, and by official/synthetic stratum from
  the complete pair observations.
  Excluded development sources are URL-bound and use retained digests where
  available. The case-set schema requires a custodian attestation that
  materially overlapping passages were excluded, while the manifest fixes the
  exclusion disposition; semantic overlap review remains external. Cases,
  answer key,
  blind predictions, result, evaluator hash, and execution receipts remain
  null until official passages are retrieved and fingerprinted, two independent
  qualified reviewers' initial judgments are retained and adjudicated, and an
  independent custodian freezes the inputs. A future receipt must record corpus
  freeze, blind prediction, answer-key unblinding, and scoring; the interface
  validates that recorded order. Pair-level predictions retain the observed
  flag and finding count so the aggregates remain recomputable. A future
  result binds the manifest
  digest, evaluation and freeze IDs, scanner, checks, evaluator, cases,
  predictions, and
  answer-key digests internally; its whole-artifact SHA-256 is returned and
  recorded out of band because it cannot contain its own byte hash. Receipt
  commit SHAs are recorded bindings, not authenticated Git-object evidence.
  Revealing the key retires that corpus for subsequent scanner versions; any
  post-run tuning requires a newly selected corpus. Any eventual report starts
  and ends with the six raw
  confusion/abstention counts, keeps synthetic controls separate, and does not
  create a compliance, accuracy, precision, recall, or statewide-coverage
  claim.
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
  when those checks pass. Bundle format 6 exposes the same effective coverage
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
  exact affected and unaffected rule/Golden IDs. Every Golden fixture declares
  sorted `rule_dependency_ids`, so expected-empty negative and ambiguous cases
  are replayed when a rule they exercise changes. The scheduled workflow keeps
  every proposal as a 30-day artifact and never adopts it automatically. It
  adds the exact worklist package only when the receipt contains changed source
  IDs; stale-only and Golden-regression-only alerts remain independent of that
  package step.
- **Reviewed publication overlay:** `src/permit_pathways/source_state.py`
  validates one deliberately adopted receipt in
  `data/source-status/current.json`. A public bundle requires receipt status
  `reviewed`, binds it to the current source registry, re-derives every
  observation and direct rule/Golden impact, and fails closed on drift. Here,
  `reviewed` means selected by repository maintenance for publication; it is
  not legal, jurisdiction, counsel, or substantive content approval and does
  not identify a human reviewer.
- **Portable re-verification worklist:**
  `src/permit_pathways/review_queue.py` derives a schema-v2 worklist from the
  validated receipt and explicit source IDs. It re-derives source/rule/Golden
  impact and, for supplied readiness contexts, binds the exact workflow,
  packet, remedies, and configured journeys even when the queue is clear. A
  changed checklist creates exact requirement and linked-remedy tasks; a
  changed parcel schema creates only its source-backed fact/field tasks;
  affected contexts add packet and journey revalidation. A route source adds a
  journey task only when that journey explicitly names the affected candidate
  route. The separate decision ledger binds every entry to both worklist and
  item fingerprints. Assignment or resolution never changes source state,
  matching, verification level, or publication.
- **Separate release receipts (implemented strict scaffold; not executed):**
  `src/permit_pathways/source_release.py` validates approval, publication, and
  rollback as three independent records. The CLI uses the same shared registry
  context loader as the review-worklist CLI and includes every registered
  workflow by default; it exposes no unregistered-path or single-workflow
  release mode. Their common binding covers the exact
  changed-source snapshot, generated worklist, and complete decision-ledger
  fingerprints. A resolved ledger is necessary but never sufficient:
  approval requires a declared reviewer code, authority-scope receipt ID, and
  evidence receipt IDs plus one explicit digest-bound resolution for every
  changed source. The release contract never infers source adoption from a
  generic work-item disposition. Publication must bind that exact approval and
  a separately re-derived `reviewed` publication source snapshot; rollback
  must bind that exact publication and the separately re-derived restored
  source snapshot. Timestamp, commit, URL, and hold-state
  consistency fail closed, while fixed effects state that validation cannot
  mutate, adopt, deploy, restore, or clear anything. The committed templates
  carry null evidence and `not_run`; no rehearsal or human action is recorded.
  Decision-ledger dates establish only calendar-date ordering relative to the
  approval timestamp, not intraday order. Bounded, open-once strict JSON
  loading rejects duplicate fields, non-finite values, malformed URLs,
  non-UTF-8 data, symlinks, and non-file or oversized input. Source, rule, and
  Golden inputs are raw-fingerprinted before and after context derivation so a
  detected concurrent change fails closed; this is a stability check, not an
  immutable snapshot or adversarial filesystem guarantee. Preparation
  exclusively creates a new directory, durably writes each receipt, and writes
  the durable completion marker last; consumers must reject an unmarked
  package. Opaque IDs are format- and binding-checked, not authenticated,
  and the validator does not retrieve Git objects or inspect a live deployment.
- **Public trust surface:** bundle format 6 carries the adopted overlay, rule
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

The scheduled watcher retains a generated worklist and blank decision template
when its review-needed exit fires, but new-law discovery, automatic receipt
adoption/publication, authorized reviewer selection, completed assignments,
and approval history are not implemented.

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
`scripts/build_demo_bundle.py` first resolves every readiness/journey artifact
through the raw-byte-pinned workflow registry. It deterministically compiles
the registry-declared browser-default entry, the generated readiness record, the
generated journey envelope, and the strict source-state overlay into
`data/demo-data.js`. Bundle format 6 also carries the exact raw registry text
and its receipt digest so the browser can prove that the parsed embedded copy
came from those bytes. Other registered entries are validated and have their
configured generated records checked or written; changing the explicit default
makes that entry's singular aliases browser-active only after its declared
availability policy also passes. The static surface is split by user job:

- `index.html`: lightweight orientation and scope; it loads no data bundle;
- `check.html`: a generated Statewide Coverage Navigator after a recognized
  jurisdiction selection, applicant intake, a temporary grouped result packet,
  a statewide orientation receipt, a labeled shareable sample that reuses a
  canonical golden fixture, its explicit applicability gate, and the separate
  optional clock; longer coverage, answer, orientation, rule, and clock content
  uses native disclosures so the candidate route remains the primary path;
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

### 6. Proposed no-storage beta operations (implemented planning validator; not approved)

ADR 0002 proposes retaining the static delivery boundary for the first
limited beta: no accounts, uploads, application-managed applicant storage,
browser persistence, application telemetry, runtime external model or parcel
calls, or permitting-system writeback. The service-collected field and purpose
inventories remain empty. The exact current structured input names are pinned
as current-page browser-memory fields, and the synthetic packet page continues
to accept no applicant submission.

This does not mean the deployment has no metadata or records. A static host,
DNS/CDN, linked third-party site, repository/release system, support system,
or incident system may process request or operational metadata outside the
application. Browser Print/Save may create a user-controlled local artifact.
The selected systems, fields, purposes, access, subprocessors, location,
retention, deletion, export, and offboarding terms remain deployment-specific
and unreviewed.

The portable planning record at
`data/validation/beta-operations-readiness.json` contains 17 stable controls
and nine role approvals for architecture, data, hosting, access, privacy,
security, records, retention, export, incident, support, release, rollback,
accessibility, language access, claims, and deployment. Its only valid state is
`prepared_not_approved`: deployment identifiers, host/subprocessor details,
records rehearsals, decisions, approvers, and execution receipts must remain
null/`not_run`.

`src/permit_pathways/beta_operations.py` strictly validates exact schema,
duplicate-free finite JSON, record size, the no-storage capability booleans,
empty service collection, exact browser-memory inventory, exact sorted
approval/control registries, unchanged claim boundaries, repository-local
evidence paths, and the ADR/runbook's exact raw-byte SHA-256 bindings. Its CLI
prints **PREPARED / NOT APPROVED**. Exit 0 proves only
that the proposed planning package has not been promoted or weakened. The
schema cannot record an approval; a later deployment/execution record requires
a separately reviewed schema.

`docs/BETA-OPERATIONS-RUNBOOK.md` provides the role model, exact data/purpose
inventory, deployment/subprocessor worksheet, release checks, support and
incident handling, retention/deletion boundaries, CPRA search/export routing,
rollback, and escalation. No role is assigned and no procedure is represented
as executed. This package does not establish a beta, partner acceptance,
privacy/security approval, accessibility/language approval, or CPRA,
Information Practices Act, SAM, or SIMM compliance.

The ADR, runbook, readiness ledger, validator, and tests are outside both the
frozen 58-file export profile v1 and the registry-aware 59-file profile v2.
Their presence in the repository is not evidence that either profile includes
them; another reviewed profile version must classify any future additions.

### 7. Pilot-neutral aggregate beta gate (implemented planning validator; not run)

`data/validation/pilot-beta-gate.json` is a portable schema-v1 planning
record with an empty pilot scope. It binds 12 existing specialized records by
canonical repository path and raw-byte SHA-256: the Woodland external gate
and its four activity ledgers, generated synthetic journey and packet,
rule-verification ledger, adopted source-state receipt, held-out evaluation
plan, beta-operations package, and public/synthetic export profile. Woodland
is carried only as a synthetic future-state reference and is explicitly not
an active pilot.

`src/permit_pathways/beta_gate.py` strictly parses the aggregate and every
bound JSON artifact, rejects duplicate keys, non-finite values, unknown or
missing fields, unsafe or noncanonical role paths, leaf or ancestor symlinks,
digest drift, duplicate roles, and status-only promotion. Descriptor-relative,
no-follow reads capture the complete live `data/` tree exactly once, including
its path and entry-type inventory, plus each non-data validator dependency.
Specialized loaders see only a private snapshot. A post-validation inventory
rejects added, removed, linked, special, or content-mutated entries. Every
not-run planning ledger is also independently raw-byte pinned; source-state
arrays remain structurally flexible and are accepted only after the strict
source-state loader re-derives their observation and dependency semantics.

The validator cross-checks the shared journey, screening case, fact envelope,
workflow, packet, frozen-lock versions, source snapshot, sample routes,
thresholds, requirement registry, and artifact-receipt identities. It
reconciles the legacy aggregate summaries with the four specialized ledgers
and invokes the existing strict source-state, effective rule-level,
held-out-evaluation, and beta-operations loaders. It inventories the exact live
rule-directory membership and rebuilds the registry-selected readiness packet
and journey from their canonical inputs, then reconciles program availability
and adopted route/readiness source dependencies. Both export profiles are
independently byte-pinned for exclusion checking; the profile ID and aggregate
gate path remain canonical bindings. All tranche files remain outside profiles
v1 and v2. A valid export profile remains mechanism evidence
and cannot satisfy the ownership/partner gate.

The 14 beta exit categories are generated by code and compared with the
record. Source-change and unverifiable counts, effective stale/unverified rule
counts, and route/packet/program currency blockers are recomputed against the
single caller-selected current date rather than `prepared_on`. In the
committed state every category is `not_run`; the record itself is only
`prepared`. Every stronger-claim boolean is fixed false, and schema v1 has no
`pass`, `approved`, `tested_beta`, or `proceed` representation. Editing an
aggregate row cannot promote it, and coordinated artifact/digest edits must
still satisfy the exact nested, cross-ledger, current-currency, and specialized
pending-state contracts. Real execution and decisions require a separately
reviewed schema that binds external receipts and preserves unfavorable
outcomes.

`beta_gate_cli.py validate` emits a machine-readable conservative summary and
returns exit 2 for invalid bindings or attempted promotion. Exit 0 means only
that the prepared/not-run record agrees with the bound repository state. When
`--repository-root` is supplied, the default aggregate path is rebased under
that root rather than retained from the installed checkout. The aggregate
record, validator, tests, and any future filled execution record are outside
export profiles v1 and v2 and require a separately reviewed profile version.

### 8. Public/synthetic evidence handoff (implemented tooling)

`src/permit_pathways/evidence_export.py` packages the exact files named in a
selected versioned profile as one deterministic ZIP outside the repository.
Schema v1 is frozen at its original 58 members; schema v2 has 59 members and
adds the workflow registry as the only substantive artifact delta, with the
bundle pin advanced to format 6. Each profile uses raw byte pins for every
ordinary member and a versioned self-reference; separate assertions keep
mutable validation ledgers in their public prepared/pending/`not_run` states.
The manifest binds Git `HEAD`,
the freeze ID/date, artifact roles, raw member hashes and sizes, a tree
fingerprint, scope/exclusions, and official source records without retained
copies. Normalized source-content hashes remain distinct from archive-member
hashes and are rechecked against `data/sources.json`.

Each schema has one canonical uncompressed ZIP representation with fixed
member metadata and strict size/path/member limits. Verification reconstructs and
compares the complete archive, so alternate ordering, compression, metadata,
prefixes, trailers, unknown files, and tampering fail. Restore streams into a
private sibling staging directory, replays the canonical loaders, and exposes
a new destination only after every check succeeds. It never uses ZIP
extraction helpers, merges into a destination, or changes publication state.

This is an evidence-data portability mechanism for the selected versioned
public and synthetic repository scope. Schema v1 is the frozen 58-file
compatibility contract. Schema v2 adds registry-aware closure at 59 files.
The later held-out evaluation planning artifact, beta-operations package,
source-change release-receipt templates, pilot-neutral aggregate beta gate,
and any future cases, answer key, execution receipt, approval, or result are
outside profiles v1 and v2; adding them requires a separately reviewed profile
version. It is not a
sensitive-data export, applicant record, proof of authenticity,
backup/disaster-recovery system, copyright or
contractual ownership finding, partner acceptance, CPRA workflow, completed
review, or beta evidence. The operator and maintenance contract is in
`docs/EXPORT-RESTORE.md`.

## Cross-cutting requirement mapping

| Challenge requirement | Current evidence | Next gap |
|---|---|---|
| Privacy (Info Practices Act, Gov C §§ 11015.5/11019.9) | Public demo persists no applicant input. Its handoff URL carries only a public journey ID and version; the packet page uses one committed synthetic record and makes no runtime model call. A proposed beta package pins the empty service collection inventory, exact current-page fields, host-metadata caveat, and privacy/incident procedure. | Select and review the actual host/subprocessors, execute the threat/privacy controls, assign authorized roles, and record approval in a separate execution schema. No compliance claim exists. |
| Jurisdiction data ownership | Rules, corpus, fixtures, workflow registry, and source metadata use open repository formats. The current schema-v2 canonical ZIP builds from 59 exact public/synthetic files verified against Git HEAD and adds registry-aware closure; the frozen schema-v1 compatibility profile remains exactly 58 files. Archive-only verification and inert restore check the selected profile, raw and normalized-source hashes, tree fingerprint, asserted validation states, licensing, and provenance without authenticating that commit. The allowlist excludes known sensitive material but is not a privacy classifier. | Partner acceptance, contractual custody/offboarding, signing, and a separately classified export after any hosted, applicant, reviewer, or participant data exists. |
| CPRA (Gov C § 7920.000 et seq.) | No applicant record store exists. The proposed runbook routes requests and legal holds to an authorized records role and identifies possible repository, deployment, source/review, support, and incident records outside the application. | Assign authority and execute the deployment-specific retention, search/export, legal-hold, exemption/redaction, and audit design. The prepared ledger remains `not_run`; no blanket compliance claim. |
| Low-capacity affordability | Dependency-light Python core and static-friendly browser demo. | Pilot deployment/TCO evidence and an integration contract beside existing systems. |
| Keep pace with legislative change | Selected-source hash watcher, proposed run artifacts, a strict repository-adopted source-state overlay, exact rule/Golden and bounded packet-context worklists, separate decision templates, applicant-output holds, date aging, and a separate staleness rehearsal. | New-law discovery, automatic adoption/publication, completed staffed assignments and dispositions, broader local-source coverage, and human approval history. |
| Decision support, not legal agent | Candidate labels, source links, disclaimers, visible unverified state, and abstention. | Ensure stale and unverified rules cannot appear as actionable green results. |
| SAM 5300 / SIMM / accessibility | Static WCAG 2.2 AAA-target audit, a versioned `not_run` human-validation matrix, and a proposed incident/release/rollback/security operations package; no-storage delivery reduces but does not eliminate the deployment boundary. | Execute the human/AT matrix, threat model, control mapping, incident/rollback rehearsal, and deployment security review. No conformance or approval is claimed. |

## Demo plan (for the 40-minute showcase slot, if selected)

1. Start on the landing page to state the prototype boundary, then open
   `check.html?sample=adu`. The labeled hypothetical Woodland facts are
   submitted through the normal intake and matcher path. Show the temporary
   collapsed answers-used receipt, dynamic group summary and jump links, the
   candidate route first, all detailed rule bodies closed, and
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
