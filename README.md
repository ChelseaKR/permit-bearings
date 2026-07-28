# Permit Pathways

**Housing-law conformance infrastructure for California jurisdictions:
an ordinance conformance scanner regression-checked against provisions from
an HCD enforcement letter, a citation-grounded permit navigator, statutory
review clocks, and a verification harness for detecting source drift.**

**Live demo:** https://chelseakr.github.io/permit-pathways/

**Local static demo:** open `index.html` directly, or run
`python3 -m http.server 8765` and visit `http://localhost:8765/`. The page
loads its generated `data/demo-data.js` bundle without network requests.

See [docs/PRODUCT-CONTEXT.md](docs/PRODUCT-CONTEXT.md) for the capability
truth, challenge fit, and prioritized opportunity map. Repository-specific
contributor and agent guardrails live in [AGENTS.md](AGENTS.md).

## The conformance scanner

Local housing ordinances drift out of conformance with state law every
legislative session — SB 477 (2024) alone renumbered all of State ADU Law,
and HCD's Housing Accountability Unit corrects jurisdictions one findings
letter at a time. The scanner screens ordinance/handout text against the
failure modes those letters document: stale statutory citations, height caps
below the 18/25-ft allowances, "only one ADU per lot" undercounts, size caps
that reach protected conversions, subjective design standards, owner-occupancy
requirements, over-cap parking, and pre-SB 450 fire-exclusion language.

**Named regression fixture:** run against six ordinance provisions HCD quoted
in its June 24, 2025 findings letter to Santa Clara County
(`corpus/hcd/letters/`), the scanner reproduces the six expected review flags
(`tests/test_conformance.py`). This is not an independent statewide accuracy
evaluation. Presence-based screening flags candidate provisions with the
controlling state law and HCD precedent for staff/counsel review; it cannot
certify compliance or detect every omission.

Working title. Conceived 2026-07-27 for the California AI Permitting Innovation
Showcase (ODI / GovOps / CHHA / GO-Biz). See [PROVENANCE.md](PROVENANCE.md).

## The premise

Every vendor can demo a permitting chatbot. The question jurisdictions actually
ask is: *how do we know the answers are right — and how do we know they're
still right after the next legislative session?*

Permit Pathways treats that question as the product:

1. **Pathway screening** — structured intake (project type, applicant-supplied
   lot facts, jurisdiction) produces candidate ADU, JADU, and SB 9 pathways
   with cited objective rules. Parcel-data retrieval, SB 35, AB 2011, and
   AI-assisted interpretation are expansion directions, not current runtime
   capabilities.
2. **Plain-language decision records** — matched rules are grouped into
   candidate routes, relevant standards, and local process records. Each card
   separates what the rule may mean, scannable deadlines or thresholds,
   suggested next steps, direct staff questions, and its source basis. The
   English and Spanish explanations are versioned AI-assisted prototype
   drafts, not reviewed guidance; they never
   participate in matching. When a matched source is stale or unverified, the
   action-oriented explanation and generic document hints are withheld while
   the warning and available source evidence remain visible.
3. **Citation-grounded guidance** — every answer carries the specific statute,
   HCD guidance document, or local code section that supports it. When the
   corpus doesn't support an answer, the system abstains and routes to staff
   instead of guessing.
4. **Currency & verification harness** — 29 structured golden cases replay
   intake against expected rule IDs; each underlying rule carries dated source
   evidence or an explicit unverified state. The CLI hash-checks selected
   sources and uses stable source-dependency IDs to mark every dependent rule
   stale; the browser separately rehearses a source amendment. Durable
   changed-state persistence and a staffed review queue remain planned.

## Showcase scenario mapping

| Scenario | Coverage |
|---|---|
| A — Guiding applicants to a complete, well-routed application | Primary prototype: ADU/JADU/SB 9 routing, grouped plain-language decision records, citations, and generic document hints. English and Spanish explanation drafts are AI-assisted and unreviewed. Parcel-specific packet completeness, remedies, and reviewed translation are planned. |
| B — Supporting internal review | Not targeted in v1 (harness architecture extends there later) |
| C — Staying current with changing state housing law (supplementary) | Core prototype: selected-source watcher, staleness harness, and HCD-letter dataset. Search, change discovery, comparables UI, and a durable review queue are planned. |

## Design commitments (from the challenge statement's cross-cutting requirements)

- Decision support, never a legal agent; abstention over confabulation.
- Rules, sources, cases, and review artifacts use portable files that a
  deploying jurisdiction can export and own; this prototype has no accounts,
  uploads, or applicant-data store.
- A production applicant-data flow would require deployment-specific privacy,
  retention, access-control, deletion, and public-records export review. This
  prototype does not claim CPRA or Information Practices Act compliance.
- Deployable and affordable for low-capacity jurisdictions; sits alongside
  existing permitting systems rather than replacing them.
- WCAG 2.2 AAA target with a static computed-contrast audit
  (`docs/ACCESSIBILITY.md`); required human/assistive-technology checks remain
  open. English/Spanish intake, interface controls, and plain-language result
  drafts are prototyped. Spanish drafts have no human or semantic-parity
  review. Applicant-facing result titles are localized drafts; canonical
  source citations, excerpts, and generic document hints remain English.
  Styling uses the open-source California Design System's cagov theme tokens
  (no state branding; use implies no affiliation).

## Status

Working prototype. The statewide rule base covers ADU, JADU, and both SB 9
pathways, encoded from the **March 2026 HCD ADU Handbook** and the **April
2026 HCD SB 9 fact sheet** (both in `corpus/hcd/`), each rule carrying the
recorded supporting excerpt and a `verified_on` date.
Machine-assisted encoding — a documented human spot-check against the PDFs in
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

A period detail that proves the concept: state ADU law was renumbered from
Gov. Code § 65852.2 et seq. to §§ 66310–66342 by SB 477 (2024), with further
renumbering in 2025 legislation. Any tool that cited the old sections — as
this repo's own first-day placeholder did — is exactly the staleness the
harness is built to catch. (HCD's own first finding against Santa Clara
County's ordinance was this renumbering; see the conformance scanner below.)

## Run it

## Transit-proximity determinations (GTFS)

Two ADU standards turn on transit proximity, and both are computable from a
jurisdiction's GTFS feed instead of applicant self-attestation: the
§ 66322(a)(1) parking exemption (half-mile walking distance of public
transit) and the § 66321(b)(4)(B) 18-ft height allowance (half-mile of a
major transit stop, PRC § 21064.3, or a high-quality transit corridor,
PRC § 21155(b) — both requiring peak-headway analysis). `transit.py` parses
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

```sh
python3 -m pytest                                   # test suite
PYTHONPATH=src python3 -m permit_pathways.transit --gtfs corpus/gtfs/unitrans.zip --lat 38.5449 --lon -121.7442
PYTHONPATH=src python3 -m permit_pathways.conformance <ordinance.txt>  # scan
PYTHONPATH=src python3 -m permit_pathways.harness   # verification report
PYTHONPATH=src python3 -m permit_pathways.harness --fetch            # live source diff
PYTHONPATH=src python3 -m permit_pathways.harness --assume-changed ca-gov-66321
python3 -m http.server 8765                         # full static showcase
PYTHONPATH=src python3 demo/app.py 8766             # Python reference demo
# The Python server also exposes the static showcase at /index.html.
python3 scripts/build_demo_bundle.py                # after canonical JSON changes
```

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
SB 9 urban lot splits, and the SB 9 × ADU unit-count interaction — plus
pilot local metadata records for the Cities of Davis and Woodland. A weekly
GitHub Action re-fetches selected statewide sources and is intended to open an
issue if any changed or became unreachable. Local-code sources and newly
enacted-law discovery are not yet covered.

The full static showcase serves an English/Spanish structured-intake shell,
grouped decision-record results with plain-language explanation drafts,
always-visible citations and source-status badges, an abstention path ("needs
staff review") when no encoded state pathway matches, the conformance scanner,
review clocks, and a trust dashboard. Spanish explanation copy is an
unreviewed machine draft; applicant-facing titles are localized drafts while
canonical pathway labels, excerpts, citations, and document hints remain
English when shown. Stale and unverified records suppress action copy,
interpretive notes, and document hints. The dashboard includes a clearly
labeled one-click rehearsal of an amendment to Gov. Code § 66321; matching
result cards rerender as stale, but that rehearsal is not persisted production
state. The smaller Python reference demo renders the same explanation sidecar
and keeps a separate `/trust` route.

## Layout

- `src/permit_pathways/screening.py` — deterministic pathway-screening engine
- `src/permit_pathways/explanations.py` — versioned explanation validation
- `src/permit_pathways/harness/` — verification runner + CLI
- `data/rules/` — the cited rule base; `data/golden/` — golden cases
- `data/explanations/plain-language.json` — English/Spanish explanation drafts
- `data/demo-data.js` — generated offline bundle for the static showcase
- `corpus/hcd/` — HCD source documents recorded by rule citations
- `demo/app.py` — stdlib reference demo and safe static-file server
- `scripts/build_demo_bundle.py` — rebuild/check the static data bundle
- `docs/DESIGN.md` — architecture and demo plan
- `docs/PRODUCT-CONTEXT.md` — capability truth and opportunity priorities
- `AGENTS.md` — evidence, scope, privacy, and quality guardrails
- `LICENSE` and `THIRD_PARTY_NOTICES.md` — original-project license and
  attribution or separate terms for bundled source material
