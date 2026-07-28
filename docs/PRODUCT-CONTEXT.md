# Product context and opportunity map

Status: 2026-07-28. This is the canonical product and claim context for the
repository. It summarizes the supplied California AI Permitting Innovation
Showcase challenge statement; the original challenge remains authoritative.

## Outcome and product thesis

California's desired outcome is more housing permitted faster by making
permitting clearer for applicants and less burdensome for staff, without
assuming every jurisdiction can replace its existing systems.

Permit Pathways should be the **auditable assurance layer behind a legible
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

- **Scenario A — primary product:** project-, parcel-, and
  jurisdiction-specific routing; packet completeness; common gap detection;
  detailed remedies; plain-language and multilingual guidance.
- **Scenario B — later extension:** cross-department status, cited staff
  drafts, objective-standard review, and review-comment resolution.
- **Scenario C — assurance layer:** current state/HCD/local sources,
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
| ADU/JADU/SB 9 structured pathway screening | Prototype | Thirteen statewide rules in `data/rules/statewide.json`; deterministic matching in `screening.py`. SB 35 and AB 2011 are not encoded. |
| Plain-language decision records | Prototype | `data/explanations/plain-language.json` contains a versioned English and Spanish draft for all 15 current statewide/local rule records. Results group routes, standards, and local process records and separate meaning, scannable deadline/threshold highlights where needed, suggested first steps, direct staff questions, and cited evidence. Copy is AI-assisted and review-pending; it has no legal, jurisdiction, comprehension, or semantic-parity review and cannot affect deterministic matching. Source-date, citation-fingerprint, or full-rule-fingerprint drift invalidates display copy; completed reviews must name the reviewed explanation version; and stale/unverified records withhold action copy, interpretive notes, and generic document hints. `tests/test_explanations.py` checks these contracts and selected semantic/jargon boundaries, not overall accuracy or comprehension. |
| Local jurisdiction records | Prototype | Davis and Woodland records exist. Davis deliberately has no dated source check; neither record is comprehensive local-code coverage. |
| Application completeness | Planned | Several rules list generic typical documents. There is no parcel-specific requirement manifest, document ingestion, cross-document validation, or detailed remedy engine. |
| Golden regression harness | Prototype | Nine structured intake-to-expected-rule-ID fixtures. It does not evaluate natural-language answers, citation fidelity, remedies, or supporting passages. |
| Source currency monitoring | Prototype | Thirteen statewide HCD/statute URLs are hash-watched. The scheduled workflow now preserves the watched command's exit status through `tee`. Local sources are not watched; new statutes are not discovered; changed state is not persisted to the public dashboard. |
| Source-impact demonstration | Prototype | The CLI can treat citation-matched changed URLs/markers as stale and the browser rehearses a § 66321 change. Most handbook-cited rules do not depend explicitly on their official statute URLs, so a real LegInfo URL change does not yet reproduce the marker simulation. |
| Ordinance conformance scanner | Prototype | Presence-based review flags with an HCD-derived regression fixture containing six quoted Santa Clara provisions, one negative control, and one committed San Diego scan. This is not a compliance test or measured statewide accuracy. |
| Review clocks | Prototype | A single input date drives both the 15-business-day completeness notice and 60-day decision outputs. Cure/completion events, tolling, resubmissions, and local holidays are not modeled, so the two clocks should not be presented as one production determination. |
| Transit proximity | Prototype | GTFS and statewide high-quality-transit data support screening in a CLI. Service effective dates/exceptions, peak-boundary gaps, planned-facility filtering, multi-operator completeness, walking-network confirmation, and parcel integration require correction before applicant-facing eligibility use. |
| Jurisdiction/HCD-letter registry | Implemented dataset | 541 entries: 483 incorporated cities and 58 counties. The 2020 Census source is supplemented with official Mountain House incorporation evidence; an ongoing incorporation/dissolution refresh is still needed. Statewide baseline availability does not mean local codes are encoded. |
| Static browser delivery | Implemented surface for prototype data | `index.html` can run directly from disk or over HTTP by loading the generated `data/demo-data.js` artifact. Canonical JSON remains authoritative; `tests/test_static_demo.py` fails when the bundle drifts. |
| English/Spanish experience | Prototype | Intake, interface controls, and plain-language result explanations have English/Spanish variants. Spanish explanation copy is labeled as an unreviewed machine draft. Pathway titles, rule notes, document hints, source excerpts, and much dashboard content remain English; no semantic-parity review has been completed. |
| Accessibility | Prototype | Static/code audit targets WCAG 2.2 AAA. Human screen-reader, keyboard, reflow, forced-colors, and Spanish pronunciation checks remain open. |
| Free-text grounded Q&A | Planned | Described as an architectural direction; no executable question-answering surface exists. |
| Scenario B staff workflows | Not targeted in v1 | No live status integration, report/letter drafting, plan check, or comment-resolution workflow exists. |
| Applicant-data privacy | Implemented for the no-storage demo; production planned | The current browser/server demo does not persist submissions. Production retention, CPRA export, security controls, and deployment documentation are not implemented. |

In the current schema, `verified_on` means that dated source evidence is
recorded. It does not by itself mean a human, jurisdiction, or counsel has
approved the interpretation.

## Known correctness risks to resolve first

These are implementation defects or evidence gaps, not general roadmap ideas:

1. **Real change propagation is incomplete.** The watcher emits changed source
   URLs, but rule impact relies on substring matching against display
   citations. A changed official statute URL may leave handbook-cited rules
   current even when the browser's manually injected section marker makes them
   stale.
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
4. **Clock events are conflated.** Initial receipt and receipt of a completed
   or cured application need separate event dates before a 60-day deadline is
   shown.
5. **Transit can overstate certainty.** Planned statewide stops, incomplete
   feeds, service calendars/exceptions, peak-window coverage, and walking
   distance can change the result. Return `unknown` unless data completeness
   supports a narrower conclusion.
6. **Local records are not applicant-ready layers.** Davis is intentionally
   unverified; Woodland cites an adoption/CEQA record rather than a complete
   operative ordinance and sourced checklist.
7. **Browser and Python behavior can drift.** Screening, staleness, scanning,
   and clocks are duplicated without cross-runtime contract tests.
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

### Bounded AI role

The challenge asks for AI-enabled solutions, while today's executable core is
mostly deterministic. The credible AI contribution is bounded and
inspectable:

- extract fields and document presence with page-level evidence;
- align local forms and code provisions to a candidate requirement schema;
- retrieve passages for explanations and remedy drafts;
- propose rule/test updates for human approval after a source change;
- cluster HCD letters by issue for comparable-jurisdiction research; and
- draft staff text from locked case facts and cited standards.

Objective eligibility and completeness rules remain deterministic. AI output
must cite evidence, expose uncertainty, and abstain when evidence is absent or
conflicting.

## Ranked opportunity portfolio

| Priority | Opportunity | Why it matters | Cheapest credible test |
|---|---|---|---|
| P0 | Make every public claim traceable to a capability status and artifact | Trust is the product; overclaiming destroys the differentiation. | Review README, demo, design, and live UI against the capability table on every release. |
| P0 | Pilot ADU permit-readiness packet | Directly proves Scenario A completeness and remedies instead of showing generic document hints. | Compare results on a small set of public, synthetic, or redacted packets with staff-authored completeness notices. |
| P0 | Evidence manifest and durable source-dependency graph | Turns the strongest demo simulation into operational assurance. | Replay a historical or simulated source revision and verify the exact affected/unaffected rules, cases, and packet fields. |
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

Before a pilot, create a concrete no-storage/data-flow diagram, deployment
and cost envelope, retention/export design, CPRA search workflow, security
control mapping, incident path, and human accessibility test record. Describe
these as deployment-specific controls, not blanket legal compliance.

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

The repository does not yet contain pilot user research, a jurisdiction-owned
local requirements corpus, or real application packets. Before committing to
the roadmap, resolve:

- Which jurisdiction and one permit subtype will sponsor a deep pilot?
- Which parcel, application, and status data are available and authoritative?
- What does staff treat as “complete” versus “consistent” in that workflow?
- Who may approve rule interpretations and translations, and on what cadence?
- Which records must be retained, exported, or excluded in that deployment?
- Which source changes matter immediately versus at a future effective date?
- Is the buyer seeking an applicant tool, an internal assurance layer, or a
  component inside an incumbent permitting platform?

## Showcase-ready definition

A credible showcase should demonstrate one sourced parcel journey from intake
to a permit-readiness evidence packet, an honest unsupported/abstention path,
and a source revision that produces an exact affected-output review queue.
Every narrated claim should be reproducible from the repository, and every
simulation, sample, untranslated surface, and unverified rule should be
visible as such.
