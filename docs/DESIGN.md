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
facts, comprehensive local requirements, application-file review, or detailed
remedies.

The result surface now groups matched records into candidate routes, relevant
standards, and local process records instead of visually presenting every
standard as a separate route. The next coherent output is a single
permit-readiness evidence packet that also separates submission completeness,
consistency standards, and unresolved staff questions.

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

Both demos preserve the matched rule, source citation, and available excerpt
when explanation copy is unavailable. If the source is stale or unverified,
they deliberately withhold the action-oriented explanation, interpretive rule
notes, and generic document hints; a weak evidence record cannot become an
applicant checklist.

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

### 2. Citation-grounded Q&A (planned)

For free-text questions the deterministic core can't answer, a retrieval layer
over the jurisdiction's corpus (state law, HCD guidance, local zoning/municipal
code) answers **only from retrieved text, with the citation inline**. Abstention
is a first-class outcome: no supporting passage → "this needs staff review,"
with a routing hint. Bilingual output (EN/ES) from the same grounded passage.

No free-text Q&A or live LLM/NLP layer is currently implemented. The existing
abstention path is a structured intake with no matching encoded rule.

### 3. Currency & verification harness (prototype differentiator)

- **Golden set:** 29 structured intake records map to expected rule IDs.
  They are regression fixtures, not natural-language answer, citation, or
  jurisdiction-acceptance evaluations.
- **Verification runner:** replays the deterministic matcher, checks recorded
  verification dates, and can mark citation-matched sources stale.
- **Currency watcher:** monitors the source corpus (statute text, HCD guidance,
  and selected local-source pages) for hash changes. Fifteen sources are
  watched. New-law discovery and durable changed-state persistence are not
  implemented; stable source dependency IDs are.
- **Public trust surface:** the dashboard shows date-based rule status and a
  labeled amendment rehearsal. It does not currently ingest persisted output
  from the scheduled watcher.

The target dependency model is:

`source ID → provision → rule/check → golden case → applicant/staff output`

A changed or unreachable source should create a durable review queue for all
affected nodes while proving that unrelated nodes remain current.

### 4. Static delivery (implemented)

The browser showcase remains dependency-free and static-host friendly.
Canonical rules, explanations, registries, fixtures, checks, and source
metadata stay in JSON. `scripts/build_demo_bundle.py` deterministically
compiles those files into `data/demo-data.js`, which loads before the page
application code. This lets `index.html` work when opened directly from disk,
where browsers normally block JSON `fetch()` calls, while retaining
checked-HTTP JSON loading as a fallback. The stdlib server exposes the static
page at `/index.html` and `/showcase` and limits static-file access to
`index.html` and `data/`.

The generated bundle must never become a second hand-edited source of truth;
the test suite compares it byte-for-byte with the canonical JSON inputs.

## Cross-cutting requirement mapping

| Challenge requirement | Current evidence | Next gap |
|---|---|---|
| Privacy (Info Practices Act, Gov C §§ 11015.5/11019.9) | Public demo persists no applicant input. | Deployment data inventory, flow, purpose, access, retention/deletion, subprocessors, and privacy review. |
| Jurisdiction data ownership | Rules, corpus, fixtures, and source metadata use open repository formats. | Tested full export/offboarding once any hosted or case data exists. |
| CPRA (Gov C § 7920.000 et seq.) | No applicant record store exists. | Deployment-specific retention, search/export, legal-hold, exemption handling, and audit design; no blanket compliance claim. |
| Low-capacity affordability | Dependency-light Python core and static-friendly browser demo. | Pilot deployment/TCO evidence and an integration contract beside existing systems. |
| Keep pace with legislative change | Selected-source hash watcher, stable source IDs with explicit rule dependencies, date aging, and staleness rehearsal. | Source discovery, persisted source state and review queue, broader local-source coverage, and human approval history. |
| Decision support, not legal agent | Candidate labels, source links, disclaimers, visible unverified state, and abstention. | Ensure stale and unverified rules cannot appear as actionable green results. |
| SAM 5300 / SIMM / accessibility | Static WCAG 2.2 AAA-target audit; no-storage demo reduces the current data boundary. | Human/AT audit, threat model, control mapping, incident path, and deployment security review. |

## Demo plan (for the 40-minute showcase slot, if selected)

1. Live structured intake for a hypothetical ADU project → candidate rules
   with citations and generic document hints (current Scenario A prototype).
2. Select an unsupported fact combination → visible abstention + staff routing
   (current trust moment; free-text Q&A remains planned).
3. Simulate a statute change → watch dependent answers flip to stale → staff
   review state (Scenario C rehearsal, the differentiator).
4. Show the trust dashboard.

The stronger next demo is one pilot jurisdiction's sourced parcel facts →
ADU requirement manifest → missing-item remedies → exportable evidence packet
→ changed-source impact queue.

## Non-goals for v1

- Scenario B (live status, staff report generation, plan-check) — the evidence
  architecture can extend there, but v1 does one thing well, per the
  challenge's "start small" principle.
- Being an authoritative legal source. Ever.
