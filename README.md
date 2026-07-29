# Permit Bearings

**Check a California ADU, JADU, or SB 9 project. See the sources behind the
result. Take unresolved questions to staff.**

Permit Bearings is a prototype decision-support tool for California ADU, JADU,
and SB 9 projects. Structured applicant facts produce candidate routes,
relevant standards, cited official sources, and questions for local staff. The
matcher is deterministic. Separate English and Spanish explanations are
AI-assisted, review-pending drafts.

It does not verify parcel facts, reproduce a complete local checklist,
determine final eligibility, certify submission completeness, or approve
permits.

**Live demo:** https://chelseakr.github.io/permit-pathways/

**Hypothetical ADU sample:**
https://chelseakr.github.io/permit-pathways/check.html?sample=adu

**Local static demo:** open `index.html` directly, or run
`python3 -m http.server 8765` and visit `http://localhost:8765/`. The landing,
applicant guide, ordinance screen, and evidence page use relative links and
work without network requests. Only the three interactive pages load the
generated `data/demo-data.js` bundle.

See [docs/PRODUCT-CONTEXT.md](docs/PRODUCT-CONTEXT.md) for the capability
truth, challenge fit, and prioritized opportunity map. Repository-specific
contributor and agent guardrails live in [AGENTS.md](AGENTS.md). The visual
and interaction alignment with California Web Standards is recorded in
[docs/DESIGN-SYSTEM.md](docs/DESIGN-SYSTEM.md).

## Run it

```sh
python3 -m pytest                                   # test suite
PYTHONPATH=src python3 -m permit_pathways.transit --gtfs corpus/gtfs/unitrans.zip --lat 38.5449 --lon -121.7442
PYTHONPATH=src python3 -m permit_pathways.conformance <ordinance.txt>  # scan
PYTHONPATH=src python3 -m permit_pathways.harness   # verification report
PYTHONPATH=src python3 -m permit_pathways.harness --fetch            # live source diff
PYTHONPATH=src python3 -m permit_pathways.harness --assume-changed ca-gov-66321
python3 -m http.server 8765                         # full static showcase
PYTHONPATH=src python3 demo/app.py 8766             # Python reference demo
# The Python server exposes the landing at /index.html and tools at
# /check.html, /review.html, and /evidence.html.
python3 scripts/build_demo_bundle.py                # after canonical JSON changes
```

## How the project check works

1. The applicant selects a jurisdiction and supplies structured project facts.
2. Deterministic criteria match those facts to the bounded rule set. No live
   model and no free-text answer determine eligibility.
3. The browser creates a temporary "answers used" cover sheet, summarizes the
   matching records by group, and provides jump links to each nonempty group.
   The cover sheet exists only in the current page and is not a stored or
   exportable applicant record.
4. When present, one explicitly configured candidate route for the selected
   project type starts open. Supporting standards and local information records
   use compact disclosures. Their citations and source-status labels remain
   visible when the disclosures are closed.
5. Every match includes source status and a citation. When the explanation
   record passes the prototype's schema and fingerprint checks and the source
   evidence is inside its review window, the result can also show a candidate
   consequence, available excerpt, starting steps, and questions for staff.
6. Changing the jurisdiction or any project answer clears the old cover sheet
   and result. The applicant must submit the edited answers to produce a new
   result.
7. Material facts marked "I'm not sure" stop the candidate result and become
   questions for the local planning counter.
8. A stale, unverified, or fingerprint-mismatched source leaves the rule and
   available evidence visible but suppresses action copy and document hints.
9. If complete answers match no encoded route, the app says the bounded rule
   set found no path and routes the applicant generally to local staff.

The current app covers statewide ADU, JADU, and SB 9 screening and two bounded
local records. Parcel retrieval, packet-level completeness, detailed remedies,
SB 35, AB 2011, reviewed translation, and comprehensive local rules are
planned rather than implemented. The temporary result packet does not change
those boundaries.

## Trust and source currency

The browser and Python demos render explanations from a sidecar that cannot
change the matching result. Each explanation is linked to a stable rule ID,
source date, citation fingerprint, full-rule fingerprint, version, authorship
status, and review status. English and Spanish status are checked
independently.

The deterministic matcher replays 29 structured fixtures against expected rule
IDs. The command-line harness checks selected source hashes and uses explicit
dependency IDs to mark affected rules stale. The browser source-change control
is a rehearsal, not persisted production state. Durable change discovery,
review assignment, approval, and publication remain planned.

## Supporting ordinance screen

The separate ordinance screen checks pasted ordinance or handout text for
selected phrases and patterns documented in an HCD enforcement letter. Against
six quoted provisions from HCD's June 24, 2025 Santa Clara County findings
letter, it reproduces six expected review flags in
`tests/test_conformance.py`.

This is a bounded presence-based screen. It is not a compliance test,
statewide accuracy evaluation, legal interpretation, or proof that required
language is present. Findings point staff or counsel to a candidate provision,
state source, and documented precedent for review.

Conceived 2026-07-27 for the California AI Permitting Innovation Showcase
(ODI / GovOps / CHHA / GO-Biz). See [PROVENANCE.md](PROVENANCE.md).

## Showcase scenario mapping

| Scenario | Coverage |
|---|---|
| Scenario 1 (A): guiding applicants to a complete, well-routed application | Primary prototype. Candidate ADU, JADU, and SB 9 routing, a temporary grouped result packet, citations, uncertainty routing, and generic document hints are implemented. Parcel-specific packet completeness, detailed remedies, and reviewed translation are planned. |
| Scenario 2 (B): supporting internal review | Not targeted in v1. |
| Scenario 3 (C): keeping current with housing law | Prototype assurance layer beneath Scenario 1. Selected-source checking, dependency invalidation, and an HCD-letter dataset are implemented in bounded form. Search, change discovery, comparable-jurisdiction research, and a durable review queue are planned. |

## Design commitments (from the challenge statement's cross-cutting requirements)

- Decision support, never a legal agent; abstention over confabulation.
- Rules, sources, cases, and review artifacts use portable files that can be
  copied and inspected without vendor-only tooling. Operational export and
  ownership terms remain deployment work. This prototype has no accounts,
  uploads, or applicant-data store.
- A production applicant-data flow would require deployment-specific privacy,
  retention, access-control, deletion, and public-records export review. This
  prototype does not claim CPRA or Information Practices Act compliance.
- Dependency-light and designed to sit alongside existing permitting systems.
  Pilot integration, staffing, hosting, and cost evidence remain planned.
- WCAG 2.2 AAA target with a static computed-contrast audit
  (`docs/ACCESSIBILITY.md`); required human/assistive-technology checks remain
  open. English/Spanish intake, interface controls, and plain-language result
  drafts are prototyped. Spanish drafts have no human or semantic-parity
  review. Applicant-facing result titles are localized drafts; canonical
  source citations, excerpts, and generic document hints remain English.
  Styling implements the published California Design System `cagov` color,
  type, spacing, and width tokens locally, alongside California Web Standards
  design principles. No State branding or affiliation is claimed.

## Status

Working prototype. The statewide rule base covers ADU, JADU, and both SB 9
pathways, encoded from the **March 2026 HCD ADU Handbook** and the **April
2026 HCD SB 9 fact sheet** (both in `corpus/hcd/`), each rule carrying the
recorded supporting excerpt and a `verified_on` date.
Machine-assisted encoding. A documented human spot-check against the PDFs in
`corpus/hcd/` is the intended next verification pass. In the current schema,
`verified_on` means dated source evidence is recorded; it does not mean a
jurisdiction, counsel, or named human reviewer approved the interpretation.
The separate plain-language layer records its own version, linked rule-source
date, citation fingerprint, full-rule fingerprint, AI-assisted authorship, and
pending review status. Review metadata is bound to the explanation version it
covered. If browser-side fingerprint validation is unavailable, the display
fails closed to matched rules and evidence without explanation copy. All 19
current rule records have English and Spanish drafts; none is represented as
human-reviewed or jurisdiction-approved.

A period detail that demonstrates the currency problem: state ADU law was
renumbered from
Gov. Code § 65852.2 et seq. to §§ 66310–66342 by SB 477 (2024), with further
renumbering in 2025 legislation. Any tool that cited the old sections, as
this repo's own first-day placeholder did, has exactly the staleness the
harness is built to catch. (HCD's own first finding against Santa Clara
County's ordinance was this renumbering; see the conformance scanner below.)

## Transit-proximity determinations (GTFS)

Two ADU standards turn on transit proximity, and both are computable from a
jurisdiction's GTFS feed instead of applicant self-attestation: the
§ 66322(a)(1) parking exemption (half-mile walking distance of public
transit) and the § 66321(b)(4)(B) 18-ft height allowance (half-mile of a
major transit stop, PRC § 21064.3, or a high-quality transit corridor,
PRC § 21155(b), both requiring peak-headway analysis). `transit.py` parses
the feed, measures worst peak-window gaps per stop/route, clusters corner
stops into intersections, and returns screening results over the supplied
datasets. Straight-line distance can eliminate a supplied stop, but it cannot
establish that every relevant operator, stop, or service record is present.

Run against the bundled summer Unitrans (Davis) feed, no local bus stops meet
the encoded ≤15/≤20-minute peak screens. The separate statewide high-quality
transit dataset supplies the Davis Amtrak major-stop candidate near the depot.
That disagreement is the useful finding: a local feed alone is incomplete,
and schedule dates, planned facilities, multiple operators, and walking
distance all need explicit confirmation before applicant-facing use.

**Jurisdiction registry:** 541 California jurisdictions (483 incorporated
cities + 58 counties) are selectable. The original Census 2020 FIPS snapshot
is supplemented with [Mountain House](https://www.mountainhouseca.gov/27/Government),
incorporated in 2024. The same statewide candidate-rule set can be screened
for each registry entry; that is not a claim that its local code, parcel
facts, forms, or exceptions are encoded. The two local metadata records
(Davis and Woodland) are labeled separately, and neither represents
comprehensive local-code coverage.

The rule base currently covers, statewide: ADU ministerial review and the
15-business-day/60-day clocks, protected minimum unit, size allowances,
height allowances, parking limits and exemptions, the owner-occupancy
prohibition, conversion exemptions, pre-2020 unpermitted-unit legalization,
multifamily-lot 66323 allowances, JADU standards, SB 9 two-unit developments,
SB 9 urban lot splits, and the SB 9 × ADU unit-count interaction, plus
pilot local metadata records for the Cities of Davis and Woodland. A weekly
GitHub Action re-fetches selected statewide sources and is intended to open an
issue if any changed or became unreachable. Local-code sources and newly
enacted-law discovery are not yet covered.

The full static showcase has four task-focused pages: a lightweight landing
page; an English/Spanish applicant guide with review clocks; a bounded
ordinance screen; and an evidence-and-updates page. The applicant guide renders
a temporary answers-used cover sheet, a dynamic grouped summary with jump
links, one candidate route open by default when the configured route matches,
and compact supporting records. Citations and source-status badges stay
visible outside the disclosures. Ordinary answer edits clear the old result
until the applicant submits again. The applicant guide also includes
plain-language explanation drafts and an abstention path ("needs staff review")
when no encoded state pathway matches. Spanish explanation copy is an
unreviewed machine draft; applicant-facing titles are localized drafts while
canonical pathway labels, excerpts, citations, and document hints remain
English when shown. Stale and unverified records suppress action copy,
interpretive notes, and document hints. The evidence page includes a clearly
labeled one-click rehearsal of an amendment to Gov. Code § 66321; matching
applicant records can be opened in the stale state, but the rehearsal is not
persisted production state. The smaller Python reference demo renders the same
explanation sidecar and keeps a separate `/trust` route.

## Layout

- `src/permit_pathways/screening.py`: deterministic pathway-screening engine
- `src/permit_pathways/explanations.py`: versioned explanation validation
- `src/permit_pathways/harness/`: verification runner and CLI
- `data/rules/`: the cited rule base; `data/golden/`: golden cases
- `data/explanations/plain-language.json`: English/Spanish explanation drafts
- `data/demo-data.js`: generated offline bundle for the static showcase
- `index.html`, `check.html`, `review.html`, `evidence.html`: task-focused
  static pages; `assets/`: shared browser application and visual system
- `corpus/hcd/`: HCD source documents recorded by rule citations
- `demo/app.py`: stdlib reference demo and safe static-file server
- `scripts/build_demo_bundle.py`: rebuild/check the static data bundle
- `docs/DESIGN.md`: architecture and demo plan
- `docs/DESIGN-SYSTEM.md`: California Web Standards alignment and local
  extensions
- `docs/PRODUCT-CONTEXT.md`: capability truth and opportunity priorities
- `docs/SHOWCASE-SUBMISSION-DRAFT.md`: word-limited application working draft
- `docs/SHOWCASE-PILOT-BRIEF.md`: bounded small-jurisdiction deployment
  hypothesis
- `AGENTS.md`: evidence, scope, privacy, and quality guardrails
- `LICENSE` and `THIRD_PARTY_NOTICES.md`: original-project license and
  attribution or separate terms for bundled source material
