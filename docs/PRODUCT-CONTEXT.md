# Product context and opportunity map

Status: 2026-08-02. This is the canonical product and claim context for the
repository. It summarizes the supplied California AI Permitting Innovation
Showcase challenge statement; the original challenge remains authoritative.

## Outcome and product thesis

California's desired outcome is more housing permitted faster by making
permitting clearer for applicants and less burdensome for staff, without
assuming every jurisdiction can replace its existing systems.

Permit Bearings should be the **auditable assurance layer behind a legible
applicant journey**:

> Turn official sources into testable rules and requirements; turn project
> facts into a cited permit-readiness packet; show when any conclusion is
> unsupported, unverified, or stale.

The strongest differentiation is not a conversational interface. It is the
traceable lifecycle from source to output:

`official source → provision → rule/check → applicant or staff output`

A changed source should create a review queue containing every affected rule,
test, jurisdiction, and output. This makes Scenario C the trust mechanism
under a focused Scenario A product rather than a disconnected supplementary
feature.

## Users and jobs

| User | Job to be done |
|---|---|
| Homeowner or small builder | Understand the likely route, assemble the right material once, fix omissions, and know what still requires staff judgment. |
| Experienced applicant | Resolve project- and parcel-specific routing and standards without reconstructing state/local interactions by hand. |
| Permit-counter and review staff | Spend less time on repetitive questions and incomplete packets while keeping judgment and approval authority. |
| Planning/building leadership, counsel, and IT | Know which guidance is current and supported, own/export the data, and manage privacy, security, and records obligations. |
| Lower-capacity jurisdiction | Adopt one useful module beside existing tools at modest operational cost. |
| Permitting platform or implementation partner | Consume an open evidence/verification layer instead of replacing it. |

## Challenge fit

- **Scenario A, primary product:** project-, parcel-, and
  jurisdiction-specific routing; packet completeness; common gap detection;
  detailed remedies; plain-language and multilingual guidance.
- **Scenario B, later extension:** cross-department status, cited staff
  drafts, objective-standard review, and review-comment resolution.
- **Scenario C, assurance layer:** current state/HCD/local sources,
  comparable-jurisdiction examples, legislative-change discovery, dependency
  impact, and human re-verification.
- **Across all scenarios:** data minimization and ownership, CPRA-aware
  records handling, affordability, accessibility, security, annual change,
  and decision support rather than legal agency.

The challenge explicitly values specialized, composable tools and permits a
jurisdiction to start small. Scenario B breadth is therefore not required for
a credible v1.

## Capability truth

Status meanings are defined in `AGENTS.md`.

| Capability | Current status | Evidence and boundary |
|---|---|---|
| ADU/JADU/SB 9 structured pathway screening | Prototype | Seventeen statewide rules in `data/rules/statewide.json`; deterministic matching in `screening.py`. SB 35 and AB 2011 are not encoded. |
| Browser result packet | Implemented surface for prototype data | After submission, `check.html` renders a temporary answers-used cover sheet, a count summary and jump links for nonempty result groups, one explicitly configured candidate route open when it matches, and compact supporting records. Citations and source-status labels remain visible outside each disclosure. The submitted facts exist only in current page memory, and an ordinary answer edit clears the old result and disclosure state until resubmission. This is not a persisted applicant record, an exportable evidence manifest, a parcel verification, or a completeness assessment. |
| Plain-language decision records | Prototype | `data/explanations/plain-language.json` contains a versioned English and Spanish draft for all 19 current statewide/local rule records. Results group routes, standards, and local information records and separate meaning, scannable deadline/threshold highlights where needed, suggested first steps, direct staff questions, and cited evidence. Copy is AI-assisted and review-pending; it has no legal, jurisdiction, comprehension, or semantic-parity review and cannot affect deterministic matching. Source-date, citation-fingerprint, or full-rule-fingerprint drift invalidates display copy; completed reviews must name the reviewed explanation version; and stale/unverified records withhold action copy, interpretive notes, and generic document hints. `tests/test_explanations.py` checks these contracts and selected semantic/jargon boundaries, not overall accuracy or comprehension. |
| Local jurisdiction records | Prototype | Davis and Woodland records exist. The Davis record is bound to a January 2026 City handout and an October 2025 HCD technical-assistance letter; it verifies only the City's published processing categories, preserves HCD's unresolved ordinance-status warning, and does not determine which category lawfully applies. Neither record is comprehensive local-code coverage. |
| Bounded packet-presence evaluation | Prototype | `readiness.py` and `readiness_cli.py` compare explicit facts and inventory statuses with 25 source-bound requirements from one City of Woodland preapproved detached ADU checklist. The generated public sample is synthetic. Two fabricated fact values are bound to the `CITY` and `LU_Descr` fields in dated Yolo County public parcel-layer metadata; the evaluator performs no address/APN or live parcel query. It produces per-item findings, staff questions, fingerprints, source bindings, a source-status date and review deadline, and a machine-readable evidence manifest; unknown conditions and changed or stale checklist or parcel-schema sources fail closed. With an exact current journey ID and version, `prepare.html` renders the Python-generated result rather than reimplementing the evaluator; direct, malformed, mismatched, or stale entry withholds it. AI-assisted checklist mapping and action copy remain review-pending and cannot affect the deterministic evaluation. Mapping metadata binds exact input-source fingerprints and explicitly records that provider, model, and a reproducible run record are unavailable. No runtime model or applicant-data storage is used. No applicant, planner, or jurisdiction has validated the workflow or output. |
| Versioned Woodland journey contract | Implemented surface for prototype data | `data/journeys/woodland-preapproved-detached-adu.json` references one golden screening case and candidate route, the bounded readiness workflow and synthetic packet, and its applicant-editable applicability fact. `journey.py` resolves those references only when the complete fixture, scope, applicability, fingerprints, and recorded review windows agree. The browser repeats those contract and current-source checks. Only the active, unedited canonical sample can offer the handoff, and no applicability answer is preselected: a matching **Yes** exposes the versioned packet URL; **No** or **I'm not sure** withholds it. The URL contains only the public journey ID and version and uses no browser storage. This remains a replayable made-up example, not a live parcel journey, eligibility finding, completeness assessment, authorization, persisted applicant record, or externally validated workflow. |
| Printable synthetic journey summary | Implemented surface for prototype data | After the exact entry and integrity checks pass, `prepare.html` derives a print-focused summary from the already-normalized journey and readiness records: candidate route, labeled made-up facts, the three reported-missing preparation actions, three staff questions, route/checklist/parcel-metadata evidence, prototype boundary, and journey ID/version. The action block remains labeled AI-assisted, review-pending, and not human-reviewed. Direct or invalid entry withholds the summary. The button delegates Print or Save as PDF to the browser; the app does not create, upload, store, or retrieve an export. This is a portable view of one public synthetic fixture, not an applicant case, official checklist, completeness finding, authorization, or jurisdiction-approved packet. |
| Application completeness | Planned | The bounded readiness slice checks reported presence in one made-up inventory. It does not query or verify a live parcel, inspect files, test document contents or consistency, determine legal sufficiency, certify completeness, limit staff requests, or predict approval. There is no parcel-specific document ingestion, cross-document validation, or externally reviewed remedy engine. |
| Golden regression harness | Prototype | 29 structured intake-to-expected-rule-ID fixtures. It does not evaluate natural-language answers, citation fidelity, remedies, or supporting passages. |
| Source currency monitoring | Prototype | Nineteen HCD, statute, and selected local-source URLs are hash-watched. Each run classifies every watched source as unchanged, changed (fetched, hash moved), or unverifiable (fetch failed after three backed-off retries); a fetch failure never counts as a change and never marks a rule stale. The scheduled workflow preserves the watched command's exit status through `tee` and distinguishes exit `1` (review needed) from exit `2` (could not check). The current Davis handout and HCD letter are watched; the blocked municipal-code host remains an unwatched reference, new statutes are not discovered, and watcher state is not persisted to the public dashboard. |
| Source-impact demonstration | Prototype | Rules carry stable source-dependency IDs. The CLI marks every rule linked to an assumed-changed source stale, and the browser rehearses a § 66321 change. The public demo still lacks persisted changed state and a staffed re-verification queue. |
| Ordinance conformance scanner | Prototype | Presence-based review flags with an HCD-derived regression fixture containing six quoted Santa Clara provisions, one negative control, and one committed San Diego scan. This is not a compliance test or measured statewide accuracy. |
| Review clocks | Prototype | The 15-business-day date is withheld unless an agency closure calendar is supplied. The separate 60-day illustration appears only when the applicant explicitly confirms both a complete-on-receipt application and an existing primary dwelling. Cure/completion events, tolling, resubmissions, and agency closures are not modeled in the public demo, so neither output is a production deadline determination. |
| Transit proximity | Prototype | GTFS and statewide high-quality-transit data support screening in a CLI. Peak-window edge gaps and ferry-to-bus/rail connections are covered by regression tests. Service effective dates/exceptions, planned-facility filtering, multi-operator completeness, walking-network confirmation, and parcel integration still require correction before applicant-facing eligibility use. |
| Jurisdiction/HCD-letter registry | Implemented dataset | 541 entries: 483 incorporated cities and 58 counties. The 2020 Census source is supplemented with official Mountain House incorporation evidence; an ongoing incorporation/dissolution refresh is still needed. Statewide baseline availability does not mean local codes are encoded. |
| Static browser delivery | Implemented surface for prototype data | Five task-focused pages use relative links and can run directly from disk or over HTTP. The applicant-first landing page loads no data JavaScript; the applicant, packet, review, and evidence pages load the generated `data/demo-data.js` artifact before shared page-gated application code. Canonical JSON remains authoritative; static tests and the build check fail when the bundle, generated readiness evidence, or generated journey envelope drifts. The route-to-packet URL accepts exactly a journey ID and version and carries no project facts. |
| Shareable hypothetical ADU sample | Implemented surface for prototype data | `check.html?sample=adu` resolves the existing `woodland-new-detached-adu-local-layer` golden fixture, fills the normal intake, and submits through the same validation and matcher path as manual answers. The result cover sheet labels the facts as made up. While that sample remains active and unedited, an explicit applicability answer can expose or withhold the versioned packet example. Editing a prefilled fact removes the sample URL state and clears the old result before recalculation. It is not a real parcel, applicant record, pilot, or external validation result. |
| English/Spanish experience | Prototype | Intake, interface controls, applicant-facing result titles, and plain-language result explanations have English/Spanish variants. Spanish explanation copy is labeled as an unreviewed machine draft. Canonical pathway labels, rule notes, document hints, source excerpts, and much dashboard content remain English; no semantic-parity review has been completed. |
| Accessibility | Prototype | Static/code audit targets WCAG 2.2 AAA. Automated browser checks cover all five initial pages, 320px and 390px reflow without document overflow, compact mobile navigation, one populated applicant result, labeled mobile evidence records, valid/invalid journey-summary disclosure, and an isolated no-overflow print-media state. `docs/MANUAL-VALIDATION.md` defines the signed human test matrix, but physical-device, virtual-keyboard, screen-reader, keyboard, zoom, forced-colors, printed-output, and Spanish-pronunciation rows remain `not_run`. |
| Free-text grounded Q&A | Planned | Described as an architectural direction; no executable question-answering surface exists. |
| Scenario B staff workflows | Not targeted in v1 | No live status integration, report/letter drafting, plan check, or comment-resolution workflow exists. |
| Applicant-data privacy | Implemented for the no-storage demo; production planned | The current browser/server demo does not persist submissions. Production retention, CPRA export, security controls, and deployment documentation are not implemented. |

In the current schema, `verified_on` means that dated source evidence is
recorded. It does not by itself mean a human, jurisdiction, or counsel has
approved the interpretation.

## Known correctness risks to resolve first

These are implementation defects or evidence gaps, not general roadmap ideas:

1. **Source discovery remains incomplete.** Watched sources and rules use
   stable IDs with explicit dependency edges, and a source whose fetched
   content hash moved invalidates every directly dependent rule. A source the
   watcher could not fetch is reported as unverifiable, keeps its last
   successful verification date, and invalidates nothing. The registry still covers
   only selected known sources; it does not discover newly enacted law or new
   local materials.
2. **Live watcher state is not persisted into applicant results.** The browser
   rehearsal rerenders matching cards and withholds their actions when the
   simulated dependency changes, and both demos apply the 180-day age window.
   A real watcher result is still not persisted or passed into screening.
   Changed/unknown dependency state must flow into every applicant output.
3. **Verification strength remains underspecified.** Explanation records bind
   to digests of selected citation fields and the full normalized rule record;
   completed review claims require reviewer, method, date, and reviewed
   version. Source bytes/version, verification method, rule-author review, and
   jurisdiction approval are not yet jointly required or independently signed.
4. **Clock event modeling remains bounded.** The public tool withholds the
   15-business-day date without an agency closure calendar and shows the
   60-day illustration only after explicit applicability assertions. It still
   lacks separate cure/resubmission events, applicant-requested delay, and
   other tolling facts needed for a production deadline determination.
5. **Transit can overstate certainty.** Planned statewide stops, incomplete
   or single-operator feeds, service-calendar exceptions, and unverified
   walking distance can change the result. Return `unknown` unless data
   completeness supports a narrower conclusion.
6. **Local records are not applicant-ready layers.** The bounded Davis record
   has dated evidence for three City-published processing categories, but it
   does not establish the operative ordinance, resolve HCD's October 2025
   warning, or determine which category lawfully applies. The Woodland rule
   record still cites an adoption/CEQA record rather than a complete operative
   ordinance. The separate Woodland readiness workflow is bound to one
   official preapproved-plan checklist, but its mapping and action copy remain
   review-pending and are not comprehensive local-code coverage.
7. **Browser and Python behavior can drift.** Screening, staleness, scanning,
   and clocks are duplicated without cross-runtime contract tests. The
   readiness page avoids a second evaluator by rendering a result generated by
   the Python implementation. The browser now validates and consumes the
   generated Woodland journey contract for one synthetic route-to-packet
   transition. That bounds this case but does not remove the need for
   cross-runtime tests whenever either implementation changes.
8. **Explanation review is pending.** The versioned English and Spanish
   plain-language records are AI-assisted drafts. Schema and regression tests
   catch missing links, same-day citation drift, malformed review metadata,
   and selected wording boundaries, but no named reviewer has evaluated legal
   fidelity, comprehension, or English/Spanish semantic parity.

## Product strategy

### The best next product: a permit-readiness evidence packet

Build one deep ADU journey for one willing pilot jurisdiction. Given an
address/APN, proposal facts, and a bounded set of application documents, the
output should contain:

- retrieved and applicant-asserted parcel facts, each labeled by source;
- candidate pathway, disqualifiers, assumptions, and unresolved facts;
- a requirement manifest separating `required`, `conditional`, and
  `not applicable`;
- packet findings labeled `present`, `missing`, `conflicting`, or
  `needs staff review`, with document/page evidence;
- a cited, plain-language remedy for each incomplete item;
- relevant completeness and decision clocks;
- an exportable evidence manifest containing source versions/hashes,
  verification level, and the rules used.

This creates a coherent Scenario A proof while making the currency harness
essential: a source revision can invalidate a requirement or remedy in a
specific packet.

The bounded Woodland slice is a first executable step. It provides one
source-bound 25-item requirement manifest, one synthetic inventory, explicit
`present`, `missing`, `not applicable`, and `needs staff review` findings,
review-pending action drafts, two fabricated values bound to exact public
parcel-layer fields, and a generated evidence manifest. It has no real
documents or queried parcel record, so it cannot supply page evidence, verify
parcel facts, test consistency, certify completeness, or support an applicant
record.

A versioned generated contract now composes that evidence with the existing
synthetic Woodland route fixture and candidate-route evidence recorded as
current on the sample's evaluation date. This makes route-to-packet agreement
testable at build time, including explicit workflow applicability and shared
fingerprints. The browser uses the same contract for one fail-closed
continuation: the canonical sample must remain active and unedited, sources
must still be current, and the applicant must answer the remaining
applicability question without a default. The public ID/version link carries
no project facts and does not turn the synthetic records into a real applicant
case.

The current browser routing result remains a transient presentation of
applicant-supplied facts and matched prototype records. The linked packet page
replays a generated synthetic record and demonstrates parcel-field provenance
with fabricated values. On the exact valid entry it can also present those
integrity-checked route and packet records as a print-focused synthetic
summary. Browser Print/Save may create a user-controlled artifact, but the app
does not store or retrieve it. Neither surface implements live parcel retrieval
or the planned document-aware, persisted permit-readiness packet for a real
application.

### Bounded AI role

The challenge asks for AI-enabled solutions, while today's executable core is
mostly deterministic. The credible AI contribution is bounded and
inspectable:

- extract fields and document presence with page-level evidence;
- align local forms and code provisions to a candidate requirement schema,
  prototyped for one Woodland checklist;
- retrieve passages for explanations and remedy drafts, with review-pending
  action copy prototyped for the same workflow;
- propose rule/test updates for human approval after a source change;
- cluster HCD letters by issue for comparable-jurisdiction research; and
- draft staff text from locked case facts and cited standards.

Objective eligibility and completeness rules remain deterministic. AI output
must cite evidence, expose uncertainty, and abstain when evidence is absent or
conflicting. The public readiness sample makes no runtime model call. Its
AI-assisted mapping and remedies are versioned, fingerprint-bound drafts with
no named human, planner, counsel, applicant, or jurisdiction review. Mapping
metadata records exact input-source fingerprints but no retained provider,
model, or reproducible run record.

## Ranked opportunity portfolio

| Priority | Opportunity | Why it matters | Cheapest credible test |
|---|---|---|---|
| P0 | Make every public claim traceable to a capability status and artifact | Trust is the product; overclaiming destroys the differentiation. | Review README, demo, design, and live UI against the capability table on every release. |
| P0 | Extend the bounded ADU packet-presence slice into a reviewed pilot workflow | Moves from one synthetic inventory and review-pending checklist mapping toward Scenario A completeness and remedies. | Compare results on a small set of public, synthetic, or redacted packets with staff-authored completeness notices. |
| P0 | Evidence manifest and durable source-state propagation | Turns the strongest demo simulation into operational assurance. | Replay a historical or simulated source revision and verify the exact affected/unaffected rules, cases, and packet fields across persisted outputs. |
| P0 | Verification levels and evaluator provenance | Makes “verified” meaningful to staff and counsel. | Add machine-linked, human-reviewed, and jurisdiction-approved states to one pilot rule set and test status transitions. |
| P1 | Parcel fact retrieval for one jurisdiction | Replaces high-risk self-attestation for zoning, hazards, historic status, and transit with sourced facts. | Run a known parcel set and have staff review disagreements and unknowns. |
| P1 | Local-rule authoring and re-verification workbench | Gives lower-capacity jurisdictions a maintainable way to adopt the layer. | Have a reviewer approve/reject AI-proposed rules beside exact source passages; measure time and disagreement. |
| P1 | Held-out conformance evaluation | Establishes scanner precision/recall beyond the fixture that shaped it. | Blindly test additional HCD-quoted provisions and conforming controls; report false positives/negatives by check. |
| P1 | Comparable-jurisdiction precedent explorer | Converts the existing HCD-letter dataset into a useful Scenario C workflow. | Ask staff to resolve a known issue using cited, issue-matched examples and compare time to their normal search. |
| P2 | Review-comment resolution matrix | Extends the evidence model into Scenario B without attempting full plan check. | Track each public/synthetic comment as addressed, partial, conflicting, or unresolved with response evidence. |
| P2 | Read-only status adapter and cited staff drafts | Reduces calls and transcription while preserving existing systems and staff sign-off. | Map one jurisdiction export/API to a small common event model and generate a clearly marked draft from locked facts. |
| Later | SB 35, AB 2011, and additional domains | Broadens routing after the pilot proves the schema and maintenance loop. | Add one domain only with official sources, negative/boundary fixtures, local interaction tests, and an owner for updates. |

### What to remove or defer

- Do not lead with the registry count without immediately distinguishing the
  statewide candidate-rule set from the two incomplete local metadata records.
- Do not add more demo modules until the applicant journey reads as one
  coherent flow.
- Defer autonomous legal interpretation, full building-code/engineering plan
  review, and a rip-and-replace permit-management platform.
- Do not store applicant documents in the demo merely to make the AI story
  look richer; use local/browser processing or controlled synthetic/redacted
  material until the data lifecycle is designed.

## Quality expansion

### Evidence and data model

Add explicit source IDs, source type, effective dates, jurisdiction and
project scope, content digest, dependency IDs, verification level,
reviewer/method, supersession links, and conflicts. Validate rule, source,
golden-case, and review-queue JSON against schemas in CI.

### Evaluation

Grow fixtures across positive, negative, boundary, ambiguous, stale,
wrong-jurisdiction, local/state conflict, and unsupported cases. Evaluate:

- route and requirement precision/recall;
- document extraction and page-evidence accuracy;
- citation entailment and source freshness;
- calibrated abstention and staff-escalation usefulness;
- Python/browser behavior parity;
- English/Spanish semantic parity; and
- conformance-screen false positives/negatives on held-out material.

### Applicant and staff experience

Organize outputs around four separate questions:

1. **Which candidate route and why?**
2. **What must be submitted, and what is missing?**
3. **Which standards appear relevant, and what still needs review?**
4. **What happens next, by when, and who owns the next action?**

Never mix completeness findings with consistency or compliance findings.
Show the evidence and remedy beside each item rather than in a separate legal
dump.

### Production posture

`docs/DATA-FLOW.md` records the current no-storage synthetic-demo boundary.
Before a pilot, extend it with the proposed deployment flow and add a cost
envelope, retention/export design, CPRA search workflow, security control
mapping, incident path, and human accessibility test record. Describe these
as deployment-specific controls, not blanket legal compliance.

## Measures

Primary outcome:

- first-pass complete application rate for the selected pilot workflow.

Supporting applicant/staff outcomes:

- missing items caught before submission;
- correction cycles per application;
- days from first submission to deemed complete;
- applicant comprehension and successful self-remedy rate;
- staff minutes spent on completeness questions and notices.

Trust guardrails:

- percentage of output claims with a canonical citation and dependency ID;
- percentage at each verification level;
- time from source change to impact detection and re-verification;
- false-positive, false-negative, and abstention rates;
- local coverage depth, reported separately from statewide baseline;
- accessibility and translation-parity defects.

## Assumptions and research questions

The repository contains one generated synthetic packet and one
machine-assisted Woodland checklist mapping. It does not yet contain pilot
user research, a jurisdiction-owned local requirements corpus, or real
application packets. Before committing to the roadmap, resolve:

- Which jurisdiction and one permit subtype will sponsor a deep pilot?
- Which parcel, application, and status data are available and authoritative?
- What does staff treat as “complete” versus “consistent” in that workflow?
- Who may approve rule interpretations and translations, and on what cadence?
- Which records must be retained, exported, or excluded in that deployment?
- Which source changes matter immediately versus at a future effective date?
- Is the buyer seeking an applicant tool, an internal assurance layer, or a
  component inside an incumbent permitting platform?

## Showcase-ready definition

A credible showcase can demonstrate the current synthetic routing and
packet-presence records as bounded prototypes, including their
unsupported/abstention paths and source bindings. A stronger pilot would add
one sourced parcel journey, real or properly redacted file evidence, reviewed
requirements and remedies, and an exact affected-output review queue after a
source revision. Every narrated claim should be reproducible from the
repository, and every simulation, sample, untranslated surface, unreviewed
draft, and unverified rule should be visible as such.
