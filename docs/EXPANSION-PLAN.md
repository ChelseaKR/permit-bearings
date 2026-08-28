# Multiyear expansion plan

Status: 2026-08-27. Four of the eight phases are built and are open as
separate pull requests. The other four are blocked on people outside this
repository, and the "Planned versus built" table at the end says exactly what
blocks each one. Nothing here is a commitment on behalf of any jurisdiction,
reviewer, or partner, and only the built phases changed anything.

`docs/PRODUCT-CONTEXT.md` remains the canonical capability inventory and
`docs/BETA-ROADMAP.md` remains the evidence gate. This document sits between
them: it says what order the remaining work should happen in, over roughly two
to three years, and why that order and not another.

## How the phases are ranked

Two lists in this repository already rank work, and they do not rank it the
same way.

`AGENTS.md` gives the standing priority order, whose first entry is "Claim
integrity, source dependencies, and verification semantics", followed by the
pilot readiness packet, the re-verification and authoring workflow, held-out
scanner evaluation, and bounded Scenario B.

`docs/PRODUCT-CONTEXT.md` opens its roadmap section with something that
outranks even that: "Known correctness risks to resolve first. These are
implementation defects or evidence gaps, not general roadmap ideas." Nine
numbered items follow. A defect on that list beats an opportunity on the
ranked portfolio, because the ranked portfolio assumes the current output is
honest.

So the ranking rule used here is: correctness defects in what the tool already
says, then `AGENTS.md` priority order, then the ranked opportunity portfolio.
Phase 1 is drawn from the first list. Phases 2 and 3 are `AGENTS.md` priority 1
applied to the build and the maintenance loop. Phases 4 through 8 follow the
`AGENTS.md` order.

## The constraint that shapes the whole arc

Most of what stands between this repository and a tested beta is not
engineering. `docs/BETA-ROADMAP.md` says so directly about its own autonomous
tranche: those tasks "cannot supply a sponsor, source authority, human review,
applicant observation, accessibility signoff, language approval, or
jurisdiction acceptance." Ten of its exit gates name an external dependency.
The reviewer roster has zero members by design, and the promotion gate is
already written so that no amount of code can fill it.

A multiyear plan made entirely of engineering tasks would therefore be
dishonest about its own ceiling. This one separates the years by who can
finish them:

- **Year 1** is work no one else has to agree to.
- **Year 2** is work that one named external person or one partner unlocks,
  where the engineering is the smaller half.
- **Year 3** is work the pilot has to prove first, and which the documents
  already say must wait.

Year 1 can be finished alone. Years 2 and 3 cannot, and listing them as though
they can is the failure this plan is trying not to commit.

That split held when the plan was executed. All of year 1 and the unblocked
half of year 3 are built. Every remaining phase stopped at a person: a
reviewer who has to be named, a jurisdiction that has to say yes, a partner
who has to judge the maintenance burden, a custodian who has to hold a freeze.
None of them was faked, stubbed, or given a placeholder to fill in later.

---

## Year 1: what can be finished without anyone else

### Phase 1: source semantics in derived determinations

**Built.** See "What phase 1 delivered" below.

Where the tool derives a determination from a published dataset, it must not
assert more than the dataset supports. The instance closed here is issue #44:
the statewide Caltrans transit dataset publishes an `hqta_details` column that
separates a stop derived from current service from one a metropolitan planning
organization submitted as planned in its adopted regional transportation plan,
and `transit.py` parsed that column and never read it. Close to one in four
`major_stop_*` rows is planned, and on this repository's own documented Davis
example the tool named a planned stop as the present-tense reason a height
allowance applied.

This ranks first because it is the only open defect in which the product
states something false about the physical world, because
`docs/PRODUCT-CONTEXT.md` risk 5 names "planned statewide stops" as its first
example of transit overstating certainty, and because it is fully closable
offline against committed data.

**Remaining in this class, not built:** the other three corrections risk 5
names. Service effective dates and calendar exceptions, multi-operator feed
completeness, and walking-network confirmation. Each needs either a routing
dependency or a feed-currency model that this phase deliberately did not
introduce.

### Phase 2: make the gate's scope equal its wording

**Built, except the standards pin.** Issue #73, with issue #74 settled as far
as it can be from inside this repository.

`make verify` is presented as local-equivalent verification. Its scope is
`src/`. Roughly 6,300 lines across `assets/demo.js`, `demo/app.py`, and
`scripts/` sit outside lint, strict typing, bandit, and the coverage floor,
including the two files that carry duplicated rule logic. Eight browser
contract tests skip silently when Node is absent, so a local `make verify` can
pass with the entire browser runtime untested and say nothing about it. The
85 percent coverage figure describes one package and reads as describing the
repository.

Work: extend ruff, mypy, and bandit to `scripts` and `demo`, deciding the
`pull_hau_letters.py` network waiver explicitly the way `watch.py`'s was
decided; give `assets/demo.js` a real unit-test runner with thresholds,
starting with the four duplicated domains, which is the same fixture work the
cross-runtime contract tests need; make a missing Node loud instead of silent;
state the coverage scope wherever the number appears; settle whether
`zizmor`'s `min-severity: high` should stay; and, having made the README
conformance table readable, bump the standards pin off a pre-v2.0.0 commit and
record a `.standards-version`.

This is priority 1 applied to verification semantics rather than to source
semantics. It ranks second because every later phase's evidence is only as
good as the gate that produces it.

**Note on a structural blocker, not a work item:** `standards.yml` checks out
the private `ChelseaKR/portfolio-standards` through a deploy key and is a
required check. GitHub does not pass secrets to fork runs, so no fork pull
request can ever make it pass. That is a real property of the setup, it is
worth writing down beside the README row that cites the workflow as evidence,
and it is not something to work around or to mint a credential for.

### Phase 3: currency automation that converges

**Built.** Issue #70, plus the scanner weakness recorded in
`docs/findings/2026-08-15-multi-jurisdiction-adu-ordinance-scan.md`.

The weekly watch files a brand-new issue every Monday with the date in the
title and no deduplication of any kind, so persistent drift becomes an
unbounded pile. Issues #63 and #65 are two weeks of one problem. One step also
conflates three signals with different owners and different urgency: a changed
source hash, an aged-out rule, and a golden regression.

Work: stable titles with the run date in the body; search before create and
comment on the open issue instead; label the class; close on green with a run
record; split or at minimum name which of the three conditions fired; and
consider escalating rather than refiling when drift persists past a grace
window. In the same pass, stop `scan_ordinances.py` re-dating every published
result on every run, which is untidy at seven jurisdictions and misleading at
two hundred.

This ranks third because an alert channel a maintainer has learned to ignore
is worse than no alert channel, and because the source-change operations of
phase 6 run through it.

---

## Year 2: what one external person or partner unlocks

### Phase 4: the first promotion past `machine_linked`

**Blocked on a named reviewer.** All 19 rules are `machine_linked`. Zero named human reviews, zero jurisdiction
approvals. The ledger, the dual fingerprint binding, the five demotion
triggers, and the roster gate that rejects a promotion by an unattested
reviewer are all built and tested against synthetic promotions.

What is missing is a person. `docs/PRODUCT-CONTEXT.md` states the cheapest
credible move exactly: recruit a named reviewer and promote one rule.

Engineering in this phase is small and mostly about making the first real
promotion survivable: a reviewer-facing worksheet that presents one rule
beside its exact source passage, and an end-to-end test over a real promotion
rather than a synthetic one. The rest is recruitment, and the phase cannot
start without it.

### Phase 5: one pilot jurisdiction's parcel-aware ADU readiness packet

**Blocked on a jurisdiction sponsor.** `AGENTS.md` priority 2, and the single largest capability gap: "Application
completeness" is the one row in the capability matrix labelled bare `Planned`.

`docs/PRODUCT-CONTEXT.md` specifies the target output in detail: retrieved and
applicant-asserted parcel facts labelled by source, a requirement manifest
separating required from conditional from not applicable, findings labelled
present, missing, conflicting, or needs staff review with document and page
evidence, a cited remedy for each incomplete item, the relevant clocks, and an
exportable evidence manifest carrying source versions, hashes, verification
level, and the rules used.

The Woodland slice is a future-state simulation because the official program
page says the preapproved plan list is coming soon. This phase needs a
jurisdiction that sponsors it, an active permit subtype, an authoritative
local source package, and staff willing to review disagreements. It cannot be
started from this side.

### Phase 6: re-verification and local-rule authoring workbench

**Blocked on named human owners and a partner decision.** `AGENTS.md`
priority 3. The strict local-source intake validator exists and
tops out at `prepared_for_review` by design. The worklist, the decision
ledger, the assignment ledger, and the three release-receipt schemas exist and
are all `not_run`.

The missing piece is the workflow that turns a jurisdiction-owned,
fingerprint-bound intake into a separately reviewed and published local
record, and the timed rehearsal that measures detection to republication with
named human owners. `docs/BETA-ROADMAP.md` requires the prospective partner,
not the builder, to judge whether that maintenance burden is acceptable.

---

## Year 3: what the pilot has to prove first

### Phase 7a: held-out scanner evaluation

**Blocked on independent reviewers and freeze custody.** `AGENTS.md`
priority 4, first half. Fully specified and entirely blocked
externally: it needs independently collected official passages, two genuinely
independent qualified reviewers with a retained adjudication record, and a
custodian to freeze the inputs. Revealing the key retires that corpus, so it
can be run once and must be run properly. No amount of engineering supplies
any of those four things.

### Phase 7b: comparable-jurisdiction precedent

**Built.** `AGENTS.md` priority 4, second half, and the only part of year 3 that is not
blocked. The committed HCD accountability dataset already maps 1,314 letters
across 470 of the 541 registry entries, and 205 jurisdictions have received a
repeal-request technical assistance letter. That is a priority list derived
entirely from data already in the repository, with nothing to fetch.

It ships as a read-only CLI rather than a page.
`docs/PRODUCT-CONTEXT.md` says not to add demo modules until the applicant
journey reads as one coherent flow, and whether it does is the owner's
judgement, not this plan's. A CLI adds no step to the applicant journey and
leaves that judgement where it belongs.

### Phase 8: bounded Scenario B comment resolution

**Blocked by a recorded deferral whose precondition needs phases 5 and 6.**
`AGENTS.md` priority 5, and the last thing on the list on purpose.
`docs/BETA-ROADMAP.md` defers it, along with new-law discovery, SB 35, AB 2011,
accounts, uploads, telemetry, model calls, and permitting-system integrations,
behind one condition: the beta must first prove its maintenance and governance
loop. A comment-resolution matrix that tracks each public or synthetic comment
as addressed, partial, conflicting, or unresolved with response evidence is
the bounded version, and full plan check remains a non-goal.

---

## Continuous, in every phase

- Any change to a fail-closed evidence boundary, a runtime model path, a
  durable applicant-data flow, or the release posture gets an ADR first.
- A capability change updates the matrix, the README, the design notes, the
  demo script, and the accessibility notes together.
- New behavior gets positive, negative, boundary, ambiguous, and
  wrong-jurisdiction cases, and a new test has to be shown failing against the
  state before the change.

## Deliberately not in this plan

Each of these is a decision already recorded, not a gap waiting to be found.

| Not planned | Where it was decided |
|---|---|
| Autonomous legal interpretation, full building-code or engineering plan review, a rip-and-replace permitting platform | `AGENTS.md` priority order; `docs/PRODUCT-CONTEXT.md` "What to remove or defer" |
| Accounts, uploads, application-managed applicant storage, browser persistence, application telemetry, permitting-system writeback | ADR 0002 and the beta operations runbook; each needs a new ADR before implementation |
| More demo modules | `docs/PRODUCT-CONTEXT.md`: not until the applicant journey reads as one coherent flow |
| SB 35, AB 2011, and additional domains | `docs/BETA-ROADMAP.md` "Later": only after the beta proves its maintenance and governance loop, and then one at a time with their own source owners |
| New-law discovery | Same deferral |
| Open-ended question answering outside a matched result | `docs/DESIGN.md`: anchoring to a matched result is what keeps the citation check exact |
| A second packet evaluator in the browser, or app-side file generation | `docs/DESIGN.md`; the browser renders a Python-generated result and delegates printing |
| AI writing into `data/rules/` | ADR 0004; drafts land in Git-ignored `ai-drafts/` and a person authors any real rule |
| Adopting the successor California Design System at runtime, or using State branding | `docs/DESIGN-SYSTEM.md`: pre-Alpha, no unambiguous redistribution license, and copying an official header would blur the trust boundary |
| Fetching from the two large municipal-code hosts | `docs/findings/2026-08-15-multi-jurisdiction-adu-ordinance-scan.md`: both publish a `Content-Signal` header declining AI training, and whether this use is compatible is a human policy call, not a scanner decision |
| Broadening the evidence export profile to reviewer, participant, or applicant records | `docs/EXPORT-RESTORE.md`; any such record needs a separately reviewed profile version |
| Any validator that can promote its own state | Recorded across the beta gate, release receipts, onboarding intake, and assignment ledger; a schema with no passing state is the point |
| Working around the fork-blocked standards check, or minting a credential for it | Not a decision in the docs; recorded here because it is the obvious wrong fix |

## Planned versus built

Each built phase is a separate pull request, so each can be reviewed and
merged on its own. Every blocked phase names the specific thing that blocks it
and what would unblock it. None of them is stubbed, and none carries a
placeholder waiting to be filled in: an empty scaffold that looks finished is
worse than an honest gap.

| Phase | Status | What blocks it, and what would unblock it |
|---|---|---|
| 1. Source semantics in derived determinations | **Built** (PR #102) | Nothing. Three sibling transit corrections in `docs/PRODUCT-CONTEXT.md` risk 5 remain open and need a routing dependency or a feed-currency model. |
| 2. Gate scope equals its wording | **Built except the standards pin** (PR #103) | The pin needs `portfolio-standards` PR #97 to merge and a tag to be cut. `v2.0.0` keys this repository under its old name and its checker resolves by checkout basename, so pinning to the tag would fail a required check on an unchanged repository. That is a merge decision in another repository. No `.standards-version` was written, because it could only name an unmerged branch commit and DOC-01 asks for a released tag. |
| 3. Currency automation that converges | **Built** (PR #104) | Nothing. |
| 4. First promotion past `machine_linked` | **Blocked** | A named reviewer who is a currently attested member of the `rule-content-reviewer` role, with a dated conflict-of-interest attestation. The ledger, the dual fingerprint binding, the five demotion triggers, and the roster gate are all built and tested. The roster has zero members by design and cannot be filled from inside the repository: inventing a reviewer is the one thing this project must never do. Unblocked by one person agreeing to review one rule and being recorded in `reviewer-roster.json`. |
| 5. Pilot parcel-aware readiness packet | **Blocked** | A jurisdiction sponsor, an active permit subtype, an authoritative local source package, and staff willing to review disagreements. Woodland is a future-state simulation because the official program page says the preapproved plan list is coming soon. Unblocked by a jurisdiction saying yes. |
| 6. Re-verification and authoring workbench | **Blocked** | Named human owners for the assignments, and a partner decision on whether the maintenance burden is acceptable, which `docs/BETA-ROADMAP.md` assigns to the partner rather than the builder. The intake validator, worklist, decision ledger, assignment ledger, and three release-receipt schemas are all built and `not_run`. Unblocked by the same partner phase 5 needs. |
| 7a. Held-out scanner evaluation | **Blocked** | Independently collected official passages, two genuinely independent qualified reviewers with a retained adjudication record, and a custodian to freeze the inputs. The contract, evaluator, and CLI are built and `not_run`. Revealing the key retires the corpus, so it runs once and must run properly. Unblocked by recruiting two reviewers and a custodian. |
| 7b. Comparable-jurisdiction precedent | **Built** (PR #105) | Nothing. |
| 8. Bounded Scenario B | **Blocked** | `docs/BETA-ROADMAP.md` defers it until the beta proves its maintenance and governance loop, and the beta is blocked on phases 5 and 6. Building it now would contradict a recorded decision rather than close a gap. Unblocked by the pilot running. |

One further thing stays reported rather than fixed, and belongs in this list
because it is the clearest example of the rule: rule
`davis-local-adu-process` cites `davis-adu-handout-2026`, whose URL returns
HTTP 404. It cannot be repointed, because `documents.cityofdavis.org` 404s and
`www.cityofdavis.org` answers 403 to a non-browser client, so no replacement
address can be retrieved. Guessing one is exactly what this repository
forbids. ADR 0005 records the mechanism that reports it honestly, and the
citation stays as it is until someone can retrieve the document's new home.

## What phase 1 delivered

Issue #44, closed. `src/permit_pathways/transit.py` now reads the
`hqta_details` column it was parsing and discarding.

- `HQStop.is_planned` and `HQStop.is_existing_major` expose the distinction the
  dataset publishes.
- A planned row inside the half mile produces no candidate for either
  standard, and is reported by count, agency, type, and distance with the two
  statutory definitions and a question for the transit agency.
- Every dataset-derived reason string names both `hqta_type` and
  `hqta_details`.
- `load_hq_stops` requires `hqta_details` to be text and raises otherwise, and
  the de-duplication key includes it, which recovers 898 rows that were being
  collapsed.
- Eight regression tests, each shown failing against the previous state.
- Recorded as
  `docs/adr/0006-planned-transit-stops-are-not-existing-ones.md`.

The documented Davis example now names the operating Capitol Corridor rail
platform at 0.36 mi instead of a planned Yolo TD stop at 0.12 mi. The verdict
did not change. The reason given for it is now true.

Capability status is unchanged: transit proximity stays Prototype and stays
outside applicant-facing eligibility use.
