# Design

## Problem shape

Housing-permit guidance has three failure modes AI tends to make worse, not
better: confident wrong answers, answers that were right until the law changed,
and answers nobody can trace to a source. The design goal is to make all three
visible and mechanically checkable.

## Components

### 1. Structured intake → pathway screening (deterministic core)

A short structured interview (project type, unit count, lot facts, zone,
jurisdiction) feeds a rules engine that emits *candidate pathways*, each with:

- route class: ministerial | discretionary | mixed
- applicable streamlining measures: ADU law, SB 9, SB 35, AB 2011 (flags with
  eligibility rationale)
- required-document checklist for that pathway in that jurisdiction
- citations: every rule carries the statute / HCD document / local code section
  it encodes, plus a `last_verified` date

Rules are data, not code: each rule is a YAML/JSON record with `criteria`,
`citation`, `jurisdiction_scope`, `last_verified`, and `verified_against`
(a content hash or excerpt of the source text). That makes the rule base
auditable and re-verifiable by machine.

### 2. Citation-grounded Q&A (retrieval layer)

For free-text questions the deterministic core can't answer, a retrieval layer
over the jurisdiction's corpus (state law, HCD guidance, local zoning/municipal
code) answers **only from retrieved text, with the citation inline**. Abstention
is a first-class outcome: no supporting passage → "this needs staff review,"
with a routing hint. Bilingual output (EN/ES) from the same grounded passage.

### 3. Currency & verification harness (the differentiator)

- **Golden set:** jurisdiction-specific question → expected answer → supporting
  source passage → `last_verified`. Curated with jurisdiction staff; grows from
  real applicant questions.
- **Verification runner:** re-asks every golden question against the current
  corpus and current rule base; diffs answers and citations; fails loudly on
  drift.
- **Currency watcher:** monitors the source corpus (statute text, HCD guidance
  pages, local code) for changes; a changed source marks every dependent rule
  and golden answer **stale** until re-verified. Legislative-session updates
  surface as a review queue for staff — this is Scenario C.
- **Public trust surface:** a jurisdiction-facing dashboard: % of guidance
  verified-current, what's stale, what changed and when. This is what a
  jurisdiction shows its council and its counsel.

## Cross-cutting requirement mapping

| Challenge requirement | Design answer |
|---|---|
| Privacy (Info Practices Act, Gov C §§ 11015.5/11019.9) | Intake stores minimum project facts; no accounts required to browse guidance; data-handling disclosure page per deployment |
| Jurisdiction data ownership | Corpus, rule base, and golden set live in the jurisdiction's storage; full export at any time |
| CPRA (Gov C § 7920.000 et seq.) | Q&A logs retained per jurisdiction schedule; export tooling for records requests |
| Low-capacity affordability | Static-friendly architecture; runs without integrating into existing permitting systems; open formats |
| Keep pace with legislative change | Currency watcher + stale-flagging is the core loop, not an add-on |
| Decision support, not legal agent | Abstention, citations, prominent scope disclaimer, staff routing |
| SAM 5300 / SIMM / accessibility | WCAG 2.1 AA target; security posture documented per deployment |

## Demo plan (for the 40-minute showcase slot, if selected)

1. Live intake for a hypothetical ADU project in one pilot jurisdiction →
   pathway result with citations and document checklist (Scenario A).
2. Ask a free-text question with no corpus support → visible abstention +
   staff routing (trust moment).
3. Simulate a statute change → watch dependent answers flip to stale → staff
   review queue → re-verify (Scenario C, the differentiator).
4. Show the trust dashboard.

Pilot corpus candidates: one small and one mid-size jurisdiction with public
zoning codes; ADU + SB 9 as the first two rule domains (best public HCD
summaries available).

## Non-goals for v1

- Scenario B (staff report generation, plan-check) — the harness architecture
  extends there, but v1 does one thing well, per the challenge's "start small"
  principle.
- Being an authoritative legal source. Ever.
