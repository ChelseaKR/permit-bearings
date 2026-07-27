# Permit Pathways

**Citation-grounded housing-permit guidance for California jurisdictions, with a
built-in verification harness that keeps every answer current with state law.**

**Live demo:** https://chelseakr.github.io/permit-pathways/

Working title. Conceived 2026-07-27 for the California AI Permitting Innovation
Showcase (ODI / GovOps / CHHA / GO-Biz). See [PROVENANCE.md](PROVENANCE.md).

## The premise

Every vendor can demo a permitting chatbot. The question jurisdictions actually
ask is: *how do we know the answers are right — and how do we know they're
still right after the next legislative session?*

Permit Pathways treats that question as the product:

1. **Pathway screening** — structured intake (project type, parcel facts,
   jurisdiction) produces candidate permitting pathways: ministerial vs.
   discretionary routing, with eligibility flags for state streamlining
   measures (ADU law, SB 9, SB 35, AB 2011). Deterministic rules where the
   standard is objective; AI-assisted interpretation only where it isn't — and
   always cited.
2. **Citation-grounded guidance** — every answer carries the specific statute,
   HCD guidance document, or local code section that supports it. When the
   corpus doesn't support an answer, the system abstains and routes to staff
   instead of guessing.
3. **Currency & verification harness** — a golden set of jurisdiction-specific
   questions, each tied to source text and a `last_verified` date. When a
   statute or HCD guidance document changes, affected answers are flagged stale
   until re-verified. A jurisdiction can see, at any moment, which guidance is
   verified-current, which is stale, and what changed.

## Showcase scenario mapping

| Scenario | Coverage |
|---|---|
| A — Guiding applicants to a complete, well-routed application | Primary: pathway screening + cited completeness guidance, plain-language and multilingual |
| B — Supporting internal review | Not targeted in v1 (harness architecture extends there later) |
| C — Staying current with changing state housing law (supplementary) | Core: the currency watcher and re-verification loop are the differentiator |

## Design commitments (from the challenge statement's cross-cutting requirements)

- Decision support, never a legal agent; abstention over confabulation.
- Jurisdiction owns its data and corpus; everything is exportable; no lock-in
  if an engagement ends.
- California Public Records Act-aware record handling; Information Practices
  Act (Civil Code § 1798 et seq.) respected in any applicant-data flow.
- Deployable and affordable for low-capacity jurisdictions; sits alongside
  existing permitting systems rather than replacing them.
- Accessible and bilingual (English/Spanish) by default.

## Status

Working prototype. The statewide rule base covers ADU, JADU, and both SB 9
pathways, encoded from the **March 2026 HCD ADU Handbook** and the **April
2026 HCD SB 9 fact sheet** (both in `corpus/hcd/`), each rule carrying the
quoted source excerpt it was verified against and a `verified_on` date.
Machine-assisted encoding — a human spot-check against the PDFs in
`corpus/hcd/` is the intended next verification pass.

A period detail that proves the concept: state ADU law was renumbered from
Gov. Code § 65852.2 et seq. to §§ 66310–66342 by SB 477 (2024), with further
renumbering in 2025 legislation. Any tool that cited the old sections — as
this repo's own first-day placeholder did — is exactly the staleness the
harness is built to catch.

## Run it

```sh
python3 -m pytest                                   # 7 tests
PYTHONPATH=src python3 -m permit_pathways.harness   # verification report
PYTHONPATH=src python3 -m permit_pathways.harness --assume-changed 66321
PYTHONPATH=src python3 demo/app.py                  # demo at localhost:8765
```

The demo serves a bilingual (EN/ES) structured intake, pathway results with
inline statutory citations and verification badges, an abstention path
("needs staff review") when no state pathway matches, and a trust dashboard
at `/trust` — including a one-click rehearsal of a legislative amendment to
Gov. Code § 66321 that flips dependent guidance to stale until re-verified.

## Layout

- `src/permit_pathways/screening.py` — deterministic pathway-screening engine
- `src/permit_pathways/harness/` — verification runner + CLI
- `data/rules/` — the cited rule base; `data/golden/` — golden cases
- `corpus/hcd/` — the HCD source documents rules are verified against
- `demo/app.py` — stdlib demo server
- `docs/DESIGN.md` — architecture and demo plan
