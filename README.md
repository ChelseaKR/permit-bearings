# Permit Bearings

**Check a California ADU, JADU, or SB 9 project. See the sources behind the
result. Take unresolved questions to staff.**

Permit Bearings is a prototype decision-support tool for California ADU, JADU,
and SB 9 projects. Structured applicant facts produce candidate routes,
relevant standards, cited official sources, and questions for local staff. The
matcher is deterministic. Separate English and Spanish explanations are
AI-assisted, review-pending drafts.

A separate bounded sample compares a made-up Woodland packet inventory with
25 source-bound items from one City preapproved ADU checklist. Two fabricated
parcel values are bound to the `CITY` and `LU_Descr` fields exposed by Yolo
County's public parcel-layer metadata; no address, APN, or live parcel is
queried. The sample does not open files, verify parcel facts, reproduce a
complete local checklist, determine final eligibility, certify submission
completeness, or approve permits.

**Live demo:** https://chelseakr.github.io/permit-pathways/

**Hypothetical ADU sample:**
https://chelseakr.github.io/permit-pathways/check.html?sample=adu

**Synthetic packet-presence sample:**
https://chelseakr.github.io/permit-pathways/prepare.html

**Local static demo:** open `index.html` directly, or run
`python3 -m http.server 8765` and visit `http://localhost:8765/`. The landing,
applicant guide, packet sample, ordinance screen, and evidence page use
relative links and work without network requests. Only the four data-driven
pages load the generated `data/demo-data.js` bundle.

See [docs/PRODUCT-CONTEXT.md](docs/PRODUCT-CONTEXT.md) for the capability
truth, challenge fit, and prioritized opportunity map. Repository-specific
contributor and agent guardrails live in [AGENTS.md](AGENTS.md). The visual
and interaction alignment with California Web Standards is recorded in
[docs/DESIGN-SYSTEM.md](docs/DESIGN-SYSTEM.md).

## Run it

```sh
make verify                                        # locked Python quality/security/data gates
npm ci && npx playwright install chromium          # one-time browser test setup
npm run test:a11y                                  # axe across all five public pages
npm run test:perf                                  # Lighthouse category budgets
PYTHONPATH=src python3 -m permit_pathways.transit --gtfs corpus/gtfs/unitrans.zip --lat 38.5449 --lon -121.7442
PYTHONPATH=src python3 -m permit_pathways.conformance <ordinance.txt>  # scan
PYTHONPATH=src python3 -m permit_pathways.harness   # verification report
PYTHONPATH=src python3 -m permit_pathways.harness --fetch            # live source diff
PYTHONPATH=src python3 -m permit_pathways.harness --assume-changed ca-gov-66321
PYTHONPATH=src python3 -m permit_pathways.readiness_cli --as-of 2026-07-30
python3 -m http.server 8765                         # full static showcase
PYTHONPATH=src python3 demo/app.py 8766             # Python reference demo
# The Python server exposes the landing at /index.html and tools at
# /check.html, /prepare.html, /review.html, and /evidence.html.
python3 scripts/build_demo_bundle.py                # after canonical JSON changes
```

## Standards Conformance

The repository follows a pinned private portfolio standards baseline, fetched
and enforced by the `Standards` workflow in CI.
This table reports implemented automation separately from review work that
still needs a person.

| Standard | Current declaration and evidence |
|---|---|
| Responsible-Tech Framework | Applies. Product, privacy, source, AI-use, accessibility, and unresolved-review boundaries are recorded in `docs/PRODUCT-CONTEXT.md`, `docs/DESIGN.md`, `PROVENANCE.md`, and `docs/ACCESSIBILITY.md`. |
| Code Quality | Python 3.12 and development dependencies are locked; Ruff, strict mypy, 85% branch coverage, generated-data parity, and 29 golden cases run through `make verify`. Ruff enforces complexity 10 across the Python codebase; the former `WVR-007` loader/evaluator waiver has been retired. |
| Security & Supply-Chain | Event-armed CodeQL, Bandit, pip-audit, gitleaks, zizmor, Dependabot, and Scorecard; all workflow actions are pinned to full commit SHAs and use scoped token permissions. |
| CI/CD | Pull requests and default-branch pushes run Python, browser, security, and source-integrity gates. GitHub Pages deploys the default branch after merge. |
| Observability | N/A — the deployed artifact is a static, no-account, no-telemetry showcase rather than a long-running production service. Storage, telemetry, uploads, or external model calls would trigger a new operational design review. |
| Accessibility | Axe and Lighthouse run on all five public pages. Browser tests also check 320px and 390px reflow, compact mobile navigation, a populated applicant result, labeled mobile evidence records, and document-level overflow. The versioned human test matrix in `docs/MANUAL-VALIDATION.md` keeps physical-device, virtual-keyboard, keyboard, screen-reader, zoom, forced-colors, and Spanish semantic review explicitly `not_run` until signed evidence exists. |
| Internationalization | Applies, deferred to pre-pilot acceptance. The exact mixed-language boundary and required native Spanish review are recorded in `docs/I18N.md`. |
| AI Evaluation | Applies to the offline AI-assisted rule/explanation workflow. Deterministic matching has model-independent fixtures; natural-language legal fidelity, applicant comprehension, and Spanish semantic parity remain unreviewed and are not inferred from those tests. |
| Documentation | Capability status and public claims are maintained in the README, product context, design, demo script, accessibility notes, and ADR log. |
| Quality & Metrics | Automated evidence includes 203 tests, 85.98% branch coverage, 29/29 golden cases, and six mobile Lighthouse states at 1.00 for accessibility, best practices, performance, and SEO, plus dependency audits and source-currency output. All 19 rule records have dated source evidence inside the review window, so the current verification report is `trustworthy: yes`; that status does not mean human, counsel, or jurisdiction approval. |
| Versioned release | N/A — this remains a branch-deployed showcase with no published package, container, action, or signed release. The trigger for replacing this N/A is recorded in `docs/adr/0001-no-versioned-release.md`. |

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
local rule records. Parcel retrieval, application-file inspection,
packet-level completeness, reviewed remedies, SB 35, AB 2011, reviewed
translation, and comprehensive local rules are planned rather than
implemented. The temporary result packet does not change those boundaries.

## How the bounded packet sample works

1. `data/readiness/workflows/woodland-preapproved-detached-adu.json` encodes
   25 requirements from one dated City of Woodland checklist for projects
   using a City preapproved detached ADU plan.
2. `data/readiness/samples/woodland-preapproved-adu.json` supplies one made-up
   project and an explicit inventory status for every requirement. Two
   concrete parcel-fact fixtures are tied to exact fields in the recorded Yolo
   County parcel-layer metadata; the values themselves are fabricated and the
   evaluator does not query a live parcel or inspect a plan, form, or file.
3. `src/permit_pathways/readiness.py` deterministically applies the workflow
   conditions. Missing items remain gaps, unknown facts become staff
   questions, and a changed or stale checklist or parcel-schema source
   prevents a favorable packet summary.
4. `python3 -m permit_pathways.readiness_cli` prints the machine-readable
   evidence manifest. By default, source age is checked against the current
   UTC date; historical replay requires an explicit `--as-of` date. The build
   uses the same Python evaluator with the sample's recorded date to generate
   `data/readiness/generated/woodland-preapproved-adu-evidence.json` and the
   static bundle.
5. `prepare.html` validates and renders that generated Python result. It does
   not contain a second packet evaluator.
6. The checklist mapping and plain-language action copy are AI-assisted
   drafts. They are versioned, fingerprint-bound, and marked
   `prototype_review_pending`; no named human, planner, or Woodland reviewer
   has approved them. Mapping metadata binds the exact checklist and
   parcel-schema source digests and records that provider, model, and a
   reproducible run record are unknown or were not retained.
7. No model runs in the CLI, build evaluator, or public browser. The public
   sample is bundled synthetic data, and the page stores no applicant record.

The sample reports item presence against one checklist and demonstrates
source-shaped parcel evidence with fabricated values. It does not query or
verify a live parcel, inspect file contents, determine legal sufficiency,
certify completeness, limit what staff may request, or predict approval. It
has not been validated with applicants, planners, or a jurisdiction.

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

The separate readiness tests cover positive, negative, boundary, unknown,
wrong-workflow, changed-source, schema, fingerprint, review-metadata, manifest,
and CLI behavior for the synthetic Woodland packet. These tests establish
bounded software behavior, not checklist completeness, legal accuracy, or
external validation.

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
| Scenario 1 (A): guiding applicants to a complete, well-routed application | Primary prototype. Candidate ADU, JADU, and SB 9 routing, a temporary grouped result packet, citations, uncertainty routing, and one generated synthetic Woodland packet-presence sample are implemented. The sample uses 25 source-bound checklist requirements, two fabricated values tied to official parcel-layer fields, and review-pending AI-assisted action drafts. Live parcel retrieval, file inspection, parcel-specific packet completeness, reviewed remedies, and reviewed translation are planned. |
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

The separate Woodland readiness workflow is also machine-assisted. Its 25
checklist mappings, two parcel-field bindings, and action drafts have
automated schema, coverage, source, and fingerprint checks, but remain
review-pending. The parcel values are fabricated and do not represent a query
or verified parcel. Mapping metadata explicitly records the absence of
retained provider, model, and run details. The generated synthetic packet
result has not been reviewed or validated by an applicant, planner, Woodland
staff member, counsel, or another jurisdiction representative.

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
bounded local metadata records for the Cities of Davis and Woodland. A weekly
GitHub Action re-fetches selected statewide sources and is intended to open an
issue if any changed or became unreachable. Two selected Woodland workflow
sources, the January 2026 Davis ADU handout, and HCD's October 2025 Davis
technical-assistance letter are recorded and watched. The Davis record reports
only the City's published processing categories; it preserves HCD's unresolved
ordinance-status warning and does not determine which category lawfully
applies. Comprehensive local-source and newly enacted-law discovery are not
implemented.

The full static showcase has five task-focused pages: a lightweight landing
page; an English/Spanish applicant guide with review clocks; the generated
synthetic packet-presence sample; a bounded ordinance screen; and an
evidence-and-updates page. The applicant guide renders a temporary
answers-used cover sheet, a dynamic grouped summary with jump links, one
candidate route open by default when the configured route matches, and compact
supporting records. Citations and source-status badges stay visible outside
the disclosures. Ordinary answer edits clear the old result until the
applicant submits again. The applicant guide also includes plain-language
explanation drafts and an abstention path ("needs staff review") when no
encoded state pathway matches. Spanish explanation copy is an unreviewed
machine draft; applicant-facing titles are localized drafts while canonical
pathway labels, excerpts, citations, and document hints remain English when
shown. Stale and unverified records suppress action copy, interpretive notes,
and document hints. The packet page renders a Python-generated result and
links its evidence manifest. The evidence page includes a clearly labeled
one-click rehearsal of an amendment to Gov. Code § 66321; matching applicant
records can be opened in the stale state, but the rehearsal is not persisted
production state. The smaller Python reference demo renders the same
explanation sidecar and keeps a separate `/trust` route.

## Layout

- `src/permit_pathways/screening.py`: deterministic pathway-screening engine
- `src/permit_pathways/explanations.py`: versioned explanation validation
- `src/permit_pathways/readiness.py`: deterministic bounded packet-presence
  evaluator and evidence-manifest generator
- `src/permit_pathways/readiness_cli.py`: packet-presence CLI
- `src/permit_pathways/harness/`: verification runner and CLI
- `data/rules/`: the cited rule base; `data/golden/`: golden cases
- `data/explanations/plain-language.json`: English/Spanish explanation drafts
- `data/readiness/`: the Woodland workflow, synthetic packet, review-pending
  remedies, and generated evidence manifest
- `data/demo-data.js`: generated offline bundle for the static showcase
- `index.html`, `check.html`, `prepare.html`, `review.html`,
  `evidence.html`: task-focused static pages; `assets/`: shared browser
  application and visual system
- `corpus/hcd/`: HCD source documents recorded by rule citations
- `demo/app.py`: stdlib reference demo and safe static-file server
- `scripts/build_demo_bundle.py`: rebuild/check the static data bundle
- `docs/DESIGN.md`: architecture and demo plan
- `docs/DATA-FLOW.md`: current build-time and browser data boundaries
- `docs/DESIGN-SYSTEM.md`: California Web Standards alignment and local
  extensions
- `docs/PRODUCT-CONTEXT.md`: capability truth and opportunity priorities
- `docs/SHOWCASE-SUBMISSION-DRAFT.md`: word-limited application working draft
- `docs/SHOWCASE-PILOT-BRIEF.md`: bounded small-jurisdiction deployment
  hypothesis
- `AGENTS.md`: evidence, scope, privacy, and quality guardrails
- `LICENSE` and `THIRD_PARTY_NOTICES.md`: original-project license and
  attribution or separate terms for bundled source material
