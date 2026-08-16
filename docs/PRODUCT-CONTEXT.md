# Product context and opportunity map

Status: 2026-08-09. This is the canonical product and claim context for the
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

The current bounded overlay makes a fetched changed source stale only its
directly dependent rules and Golden cases, then blocks applicant outputs whose
route, checklist, or parcel-metadata bindings include that source. A complete
operational queue should extend that trace to packet fields, named owners,
review decisions, jurisdictions, and publication history. This makes Scenario
C the trust mechanism under a focused Scenario A product rather than a
disconnected supplementary feature.

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
| Browser result packet | Implemented surface for prototype data | After submission, `check.html` shows an always-visible decision boundary and count, then places the visually primary candidate route before supporting records. Every rule's longer explanation, next-step, and evidence body starts closed while its consequence, citation, and source-status label remain visible. Temporary answers used and the statewide staff handoff follow in closed native disclosures. The note distinguishes candidate, unresolved-fact, no-route-in-the-bounded-corpus, and source-review-hold states; it names what remains unconfirmed and directs jurisdiction-specific questions to staff. Candidate cards retain their exact route-record identity while using a non-approval heading. The submitted facts exist only in current page memory, and an ordinary answer edit clears the old result and disclosure state until resubmission. This is not a persisted applicant record, an exportable evidence manifest, a parcel verification, or a completeness assessment. |
| Statewide Coverage Navigator | Implemented surface for prototype data | When a recognized city or county is selected, `check.html` offers a closed native disclosure containing the generated profile from `data/jurisdictions/generated/coverage-index.json`. The summary names the jurisdiction and bounded statewide/local record counts; the body separates the bounded statewide candidate-rule inventory, limited local-layer status, and dated public HCD Housing Accountability Unit record history, then lists an onboarding checklist for a maintainer considering a local layer. It uses only committed registry, rule, and HCD-history data; it makes no live request and stores no applicant fact. A changed dependency in the adopted source-state receipt puts the affected statewide inventory or local source record on a visible source-review hold; an unreachable source remains a distinct warning and does not create a hold. `Not encoded` means no jurisdiction-specific rule, form, fee, or complete checklist is represented in this repository—not that local requirements do not exist. No linked HCD record means none was linked in the dated dataset—not compliance, no HCD activity, or complete coverage. Linked HCD correspondence is historical reference material, not a current local-ordinance, compliance, eligibility, or approval finding. |
| Local-source onboarding intake | Implemented tooling; committed template is `not_run` | `data/onboarding/local-source-intake-template.json`, `local_source_onboarding.py`, and its read-only CLI define a portable intake for a future jurisdiction-owned local layer. The strict schema covers the five required source roles (operative ordinance, form, checklist, fees, and process), official-source IDs/HTTPS URLs/content fingerprints/check dates, exact operative passages with enactment/effective/check-date bindings, project and parcel scope, candidate exceptions, unresolved conflicts, open questions, and accountable owner-role IDs/re-verification cadence. Operative-passage sources must exactly equal the declared ordinance-role source set. Bounded UTF-8 JSON parsing rejects duplicate keys, non-finite values, excessive nesting, noncanonical metadata, and malformed/control-bearing URLs. Historical CLI replay is labeled and emits its validation and earliest recheck dates without reporting current readiness. The committed template contains no jurisdiction, source, passage, owner, cadence, review, or approval evidence. A copied record can reach only `prepared_for_review`; the validator has no reviewed, approved, encoded, or published state and cannot affect matching. It does not authenticate an official publisher, establish which law is operative, create a local rule, prove comprehensive coverage, or supply a real local layer. The empty template is outside export profiles v1 and v2; a filled partner intake requires separate data classification and export scope. |
| Statewide orientation handoff | Implemented surface for prototype data | For every recognized registry entry, `check.html` derives a bilingual print-focused receipt from the current in-memory submission and matched statewide rules. It carries the selected jurisdiction and facts, candidate-route sources and currency status, the presence or absence of a bounded local record, and direct questions for local staff. Browser checks exercise an ordinary city, a county, post-2020 Mountain House, and Davis's limited local layer. The receipt is orientation only: it is not stored, does not make the future-state Woodland packet simulation statewide, and does not establish comprehensive local coverage, parcel verification, completeness, eligibility, or approval. |
| Plain-language decision records | Prototype | `data/explanations/plain-language.json` contains a versioned English and Spanish draft for all 19 current statewide/local rule records. Results group routes, standards, and local information records and separate meaning, scannable deadline/threshold highlights where needed, suggested first steps, direct staff questions, and cited evidence. Copy is AI-assisted and review-pending; it has no legal, jurisdiction, comprehension, or semantic-parity review and cannot affect deterministic matching. Source-date, citation-fingerprint, or full-rule-fingerprint drift invalidates display copy; completed reviews must name the reviewed explanation version; and stale/unverified records withhold action copy, interpretive notes, and generic document hints. `tests/test_explanations.py` checks these contracts and selected semantic/jargon boundaries, not overall accuracy or comprehension. |
| Local jurisdiction records | Prototype | Davis and Woodland records exist. The Davis record is bound to a January 2026 City handout and an October 2025 HCD technical-assistance letter; it verifies only the City's published processing categories, preserves HCD's unresolved ordinance-status warning, and does not determine which category lawfully applies. Neither record is comprehensive local-code coverage. |
| Bounded packet-presence evaluation | Prototype: source-bound future-state simulation | `readiness.py` and `readiness_cli.py` compare explicit facts and inventory statuses with 25 source-bound requirements from one City of Woodland preapproved detached ADU checklist, source checked 2026-07-29. The checklist is not represented as inherently dated. The City's official program page, checked 2026-08-09, says **“Preapproved ADU List: Coming soon!”** and no listed City plan was identified. The generated public sample is therefore a future-state simulation, not a currently usable preapproved-plan or applicant-ready workflow. Two fabricated fact values are bound to the `CITY` and `LU_Descr` fields in Yolo County public parcel-layer metadata; the evaluator performs no address/APN or live parcel query. It produces per-item findings, staff questions, fingerprints, source bindings, a source-status date and review deadline, and a machine-readable evidence manifest; unknown conditions and changed or stale checklist or parcel-schema sources fail closed. With an exact versioned simulation entry, `prepare.html` renders the Python-generated result rather than reimplementing the evaluator. AI-assisted checklist mapping and action copy remain review-pending and cannot affect deterministic evaluation. Mapping metadata binds exact input-source fingerprints and explicitly records that provider, model, and a reproducible run record are unavailable. No runtime model or applicant-data storage is used. No applicant, planner, or jurisdiction has validated the workflow or output. |
| Woodland program-availability boundary | Implemented surface for prototype data | `data/availability/woodland-preapproved-adu-program.json` strictly binds the simulation to the official program URL, check date, exact excerpt fingerprint, `plans_not_listed` status, future-state boundary, and recheck deadline. `program_availability.py` validates that record under the entry's explicit Woodland policy without participating in rule matching or readiness evaluation. A separately fixed generic test policy requires an exact negative excerpt, a source ID derived from the program ID, a canonical HTTPS URL whose path is that program ID, and the matching fingerprint; no second workflow is published. Bundle format 6 carries the selected default record to the browser, dispatches the registry-declared policy, and blocks a route-to-packet handoff when the record is missing, malformed, contradictory, or expired. A valid record permits only the labeled simulation; it cannot establish that a plan is available or that the workflow applies to a real project. |
| Versioned Woodland journey contract | Implemented surface for prototype data | `data/journeys/woodland-preapproved-detached-adu.json` references one golden screening case and candidate route, the bounded readiness workflow and synthetic packet, and its applicant-editable applicability fact. `journey.py` resolves those references only when the complete fixture, scope, applicability, fingerprints, and recorded review windows agree. The browser repeats those contract, current-source, and program-availability checks. Only the active, unedited canonical sample can offer the future-state simulation handoff, and no applicability answer is preselected: a matching **Yes** exposes the versioned packet URL; **No** or **I'm not sure** withholds it. The URL contains only the public journey ID and version and uses no browser storage. This remains a replayable made-up example, not a currently listed City plan, live parcel journey, applicant-ready workflow, eligibility finding, completeness assessment, authorization, persisted applicant record, or externally validated workflow. |
| Portable workflow registry boundary | Implemented infrastructure; one prototype entry | `data/workflows/registry.json` selects repository-relative readiness workflow, packet, remedy, journey, program-availability policy, and generated-output paths by stable ID. Canonical inputs are raw-byte pinned; generated destinations are path-bound rather than described as byte-pinned inputs. The Python loader rejects unknown or duplicate JSON keys, non-finite, recursive, or oversized records, non-integer schema versions, duplicate/case-colliding IDs or paths, linked files, unregistered canonical JSON, traversal/absolute/wrong-directory and cross-platform-unsafe paths, fingerprint drift, and declared IDs that disagree with their artifacts. The browser cannot inventory repository directories; bundle format 6 instead embeds the exact raw registry, verifies its generation-receipt hash and parsed equality, validates portable unique paths and every registered input pin, then selects the registry-declared browser default and dispatches its availability policy through the singular readiness object and one-journey array. Tests construct a second distinct generic prototype entry, select it as the browser default, validate its exact generic availability record, and prove build and review-queue traversal; the committed registry still contains only the bounded Woodland future-state simulation. This is not evidence of multiple active, reviewed, applicant-ready, or jurisdiction-approved workflows. |
| Printable synthetic journey summary | Implemented surface for prototype data | After the exact entry, integrity, and program-availability checks pass, `prepare.html` derives a print-focused summary from the already-normalized journey and readiness records: candidate route, labeled made-up facts, the three reported-missing preparation actions, three staff questions, route/checklist/parcel-metadata evidence, prototype boundary, and journey ID/version. The action block remains labeled AI-assisted, review-pending, and not human-reviewed. Direct, invalid, or expired-availability entry withholds the summary. The button delegates Print or Save as PDF to the browser; the app does not create, upload, store, or retrieve an export. This is a portable future-state simulation of one public synthetic fixture, not an applicant case, currently available City plan, official checklist, completeness finding, authorization, or jurisdiction-approved packet. |
| Flagship external-evidence gate | Prepared, not executed | Five machine-readable records bind the aggregate gate, future two-reviewer 25-item content review, six same-version applicant/practitioner sessions, manual access and Spanish checks, timed maintenance rehearsal, and partner gate to the exact synthetic Woodland journey, workflow, packet, source hashes, thresholds, and freeze fields. The public evidence page reports every current external outcome as `not_run` or pending. Tests derive the aggregate state from the specialized ledgers and reject unsupported completion or `proceed` states. This scaffolding is not a review, participant finding, accessibility signoff, translation approval, completed rehearsal, partner commitment, pilot, or external validation result. |
| Application completeness | Planned | The bounded readiness slice checks reported presence in one made-up inventory. It does not query or verify a live parcel, inspect files, test document contents or consistency, determine legal sufficiency, certify completeness, limit staff requests, or predict approval. There is no parcel-specific document ingestion, cross-document validation, or externally reviewed remedy engine. |
| Golden regression harness | Prototype | 29 structured intake-to-expected-rule-ID fixtures. Each fixture also declares sorted, validated `rule_dependency_ids`, so source impact includes positive matches and expected-empty negative or ambiguous cases that exercise the affected rule. This remains a developer-curated structured regression set; it does not evaluate natural-language answers, citation fidelity, remedies, supporting passages, or held-out accuracy. |
| Source currency monitoring | Prototype | Nineteen HCD, statute, and selected local-source URLs are hash-watched. Each run classifies every watched source as unchanged, changed (fetched, hash moved), or unverifiable (fetch failed after three backed-off retries); a fetch failure never counts as a change and never marks a rule stale. The scheduled workflow preserves the watched command's exit status through `tee`, distinguishes exit `1` (review needed) from exit `2` (could not check), and retains a machine-readable **proposed** receipt as an artifact. It never overwrites the public snapshot. The current Davis handout and HCD letter are watched; the blocked municipal-code host remains an unwatched reference and new statutes are not discovered. |
| Adopted source-state and impact overlay | Prototype | `data/source-status/current.json` records one completed watch run, all 19 observations, the source-registry digest, exact run/commit receipt, and exact affected/unaffected rule and Golden IDs. Bundle format 6 accepts only a strict `reviewed` receipt and carries the overlay separately from rule verification and Woodland program availability. The browser applies changed IDs to statewide result cards, orientation receipts, and the Statewide Coverage Navigator's statewide/local inventory holds. A changed candidate-route source blocks the Woodland handoff; a changed checklist or parcel binding withholds the Woodland packet and print summary; unrelated changes do not. Unverifiable sources warn without staling. In this schema, `reviewed` means deliberately selected during repository maintenance for publication—not named-human, legal, counsel, jurisdiction, or content approval. Automatic adoption, a named reviewer record, staffed ownership, and publication approval remain planned. The § 66321 control is a separate temporary rehearsal. |
| Source-change re-verification worklist | Prototype | `review_queue.py` and `review_queue_cli.py` turn a validated proposed or reviewed source-state receipt into a deterministic schema-v2 worklist. Explicit changed source IDs create fingerprint-bound source, rule, Golden replay, readiness requirement, source-backed fact/field, linked remedy, packet, and configured journey-handoff tasks; an unverifiable source remains a warning and creates none. For the current bounded context, tests prove that a checklist change reaches exactly 25 requirements, 25 remedies, the packet, and the journey, while the parcel schema reaches only its two bound fields, packet, and journey. A separate complete decision ledger supports opaque owner codes and evidence-bound dispositions but cannot clear a source hold, change matching, promote verification, or republish. When an exit-1 watcher receipt contains changed source IDs, the workflow retains the proposed receipt, worklist, and blank decision template as a 30-day artifact. Stale-rule-only or Golden-regression-only runs still open the currency-review issue without producing a false-clear source package. The adopted current receipt produces a clear queue. This is prepared operational tooling, not evidence that a source changed, a person was assigned, review was completed, a replacement was approved, or maintenance burden is acceptable. |
| Source-change release receipts | Prepared tooling; no release executed | `source_release.py` and `source_release_cli.py` strictly separate approval, publication, and rollback evidence. A prepared set binds the exact changed-source snapshot, worklist, and decision-ledger fingerprints but remains `not_run`. A schema-complete approval requires every exact work item to be resolved and evidence-bound plus one explicit digest-bound resolution for each changed source; generic work-item dispositions cannot adopt source state. Publication and rollback additionally bind the exact preceding receipt, enforce UTC timestamp chronology, and derive hold state from source snapshots re-derived against explicit source/rule/Golden inputs. Decision-ledger dates prove calendar-date ordering only, not intraday order. Open-once bounded receipt parsing rejects duplicate fields, non-finite values, malformed URLs, non-UTF-8 data, symlinks, and non-file or oversized input. Source/rule/Golden inputs are raw-fingerprinted before and after derivation to detect concurrent drift, without claiming an immutable or adversarial filesystem snapshot. Preparation exclusively creates a new directory, durably writes each receipt, and writes the completion marker last; unmarked packages are incomplete. Fixed non-mutating effects and adversarial tests prevent a decision ledger, status-only edit, forged summary, or caller-constructed upstream receipt from clearing a hold, adopting state, publishing, or proving rollback. The CLI exposes approval outcome and hold state and does not treat a rejection or retained hold as publishable success. The validator does not authenticate Git, a live deployment, reviewer authority, or opaque external receipt IDs. Schema-v1 template fingerprints are immutable in the validator and pinned by tests; semantic changes require a new schema version. The three committed templates keep every evidence field null and remain `not_run`, contain no people or approvals, and are outside evidence export profiles v1 and v2. No controlled rehearsal, assignment, disposition, authorization, publication, deployment verification, rollback, or burden finding has occurred. |
| Rule verification levels | Implemented evidence surface; no promoted rules | Schema version 2 in `src/permit_pathways/rule_verification.py` and `data/validation/rule-verification.json` adds explicit `machine_linked`/`human_reviewed`/`jurisdiction_approved` levels on top of the bare `verified_on` date. A promoted level must bind to both the exact citation fingerprint and the exact full-rule fingerprint. Citation drift, full-rule drift, a changed source dependency, source age, or review age demotes the effective claim to `machine_linked`. Tests exercise schema validation, promotion, drift, source-change, source-age, and review-age demotion on synthetic promotions because no real promotion exists. The ledger never changes which rules match an intake. The harness reports `automated source/regression checks: pass` only for its bounded automation and prints effective-level counts. Bundle format 6 exposes the same coverage on the public evidence page: all 19 rules are `machine_linked`, with zero named human reviews and zero jurisdiction approvals. |
| Ordinance conformance scanner | Prototype | Presence-based review flags with an HCD-derived regression fixture containing six quoted Santa Clara provisions, one negative control, and one committed San Diego scan. This is not a compliance test or measured statewide accuracy. |
| Held-out conformance evaluation | Planned execution; implemented strict evaluator scaffold and CLI | `conformance_evaluation.py` validates the committed `not_run` plan plus future frozen-case, blind-prediction, answer-key, and result schemas; the key must carry two distinct declared blind reviewer records and an adjudication record, which does not prove real independence or qualifications. The interface can generate blind predictions, score raw pairs, write an exclusive result while returning the whole-artifact SHA-256, and reload a result to recompute and validate its pairs, partitions, counts, chronology, lifecycle, and digest bindings. The CLI exposes `validate-plan`, a blind `predict` command with no answer-key argument, `score`, which requires frozen predictions and the declared reviewer/adjudication key, and `validate-result`, which requires all frozen inputs plus the result; invalid input/output returns exit 2 and existing outputs are not overwritten. The manifest pins the current scanner and all nine check IDs and defines a future `(case_id, check_id)` evaluation with `should_flag`, `should_stay_quiet`, and separately counted `reference_abstain` judgments. Flag and quiet mean only that an exact passage enters or stays out of one exact check's review queue; quiet is not a conformance judgment. The contract requires the full case-by-active-check Cartesian product and, per active check, one targeted official flag pair and one preselected candidate near-miss quiet pair; each case has exactly one target check, incidental findings do not count toward minima, and synthetic controls remain separate. Raw counts must be recomputable overall, per check, and by official/synthetic stratum. Development-influencing sources are bound to canonical URLs and retained digests where available. The case-set schema requires a custodian attestation that materially overlapping passages were excluded, while the manifest fixes the exclusion disposition; the interface does not detect semantic overlap. The scanner output is binary, so machine abstention is fixed at zero and execution errors must fail. The case-set, declared reviewer/adjudication-key, blind-prediction, result-path, evaluator-hash, and freeze/prediction/scoring commit/date fields are null; no out-of-band result-artifact digest exists. Future receipts bind the manifest and input digests directly and record commit SHAs but do not retrieve or authenticate Git objects. The manifest records the official-passage, genuinely independent qualified-review/adjudication, semantic near-duplicate-review, and freeze-custody blockers. A future run must preserve freeze/prediction/unblind/scoring order and retire the corpus after the key is revealed. No evaluation observation exists, so there is no precision, recall, accuracy, compliance, or statewide-coverage claim. |
| Review clocks | Prototype | The optional deadline tool starts in a closed native disclosure; a qualifying ADU route link opens it. The 15-business-day date is withheld unless an agency closure calendar is supplied. The separate 60-day illustration appears only when the applicant explicitly confirms both a complete-on-receipt application and an existing primary dwelling. Cure/completion events, tolling, resubmissions, and agency closures are not modeled in the public demo, so neither output is a production deadline determination. |
| Transit proximity | Prototype | GTFS and statewide high-quality-transit data support screening in a CLI. Peak-window edge gaps and ferry-to-bus/rail connections are covered by regression tests. Service effective dates/exceptions, planned-facility filtering, multi-operator completeness, walking-network confirmation, and parcel integration still require correction before applicant-facing eligibility use. |
| Jurisdiction/HCD-letter registry | Implemented dataset | 541 entries: 483 incorporated cities and 58 counties. The 2020 Census source is supplemented with official Mountain House incorporation evidence; an ongoing incorporation/dissolution refresh is still needed. `jurisdictions.py` compiles the registry, scoped rule records, and the dated public HCD-letter snapshot into a portable coverage index. Statewide baseline availability does not mean local codes are encoded, and HCD history is not a local compliance disposition. |
| Static browser delivery | Implemented surface for prototype data | Five task-focused pages use relative links and can run directly from disk or over HTTP. Two project-specific machine-generated, locally served, compressed WebP illustrations anchor the landing and project-check introductions; both are decorative, carry empty alternative text, and add no eligibility, approval, or evidence meaning. The project-check illustration is hidden at the single-column breakpoint so the form remains primary. The applicant-first landing page loads no data JavaScript; the applicant, packet, review, and evidence pages load the generated `data/demo-data.js` bundle before shared page-gated application code. Canonical JSON remains authoritative; static tests and the build check fail when the bundle, generated jurisdiction-coverage index, generated readiness evidence, generated journey envelope, program-availability record, or rule-verification ledger drifts. The coverage profile appears only after a recognized selection and uses no applicant-data store; the statewide receipt is rendered only from current page memory; the route-to-packet URL accepts exactly a journey ID and version and carries no project facts. |
| Deployment smoke contract | Implemented tooling | `deployment_smoke.py` performs a read-only HTTPS check of all five public routes, stable page markers, and the generated coverage-index schema/count contract. Its default production assertions are 541 profiles and 17 statewide candidate-rule IDs; both are overrideable when the canonical corpus intentionally changes. Offline tests cover transport, unsafe URL, missing marker, malformed JSON, and count-drift failures. A pass proves route availability and artifact shape only—not source currency, functional task success, legal accuracy, accessibility, beta readiness, or rollback. |
| No-storage beta operating package | Implemented planning validator; proposed and not approved | ADR 0002, `docs/BETA-OPERATIONS-RUNBOOK.md`, `data/validation/beta-operations-readiness.json`, and `beta_operations.py` define a pilot-neutral public/static boundary and 17 operations, privacy, security, records, access, release, rollback, accessibility, language, and support controls. The strict CLI accepts only `prepared_not_approved`: service-collected fields and purposes stay empty; the exact current-page fact inventory is pinned; all nine role approvals, future-beta deployment fields, records rehearsals, partner decisions, and execution receipts stay null/`not_run`; the ADR/runbook raw-byte SHA-256 bindings must match; and all other evidence paths must exist. Host/DNS/CDN and external operational systems may process metadata outside application code and remain unreviewed. A valid schema is not a deployment, rehearsal, partner decision, compliance finding, privacy/security approval, or tested-beta result. Future execution/approval requires a separately reviewed schema. |
| Public/synthetic evidence export and restore | Implemented tooling for prototype data | `evidence_export.py`, its CLI, and the versioned profiles build one Git-HEAD-bound canonical ZIP; verify raw hashes and a tree fingerprint; recheck normalized source-content hashes; preserve licensing/provenance and official-source gaps; enforce pinned pending/`not_run` validation-state assertions; replay canonical loaders; and restore inertly into a new directory. The frozen schema-v1 compatibility profile remains exactly 58 files and omits the later registry. The current schema-v2 profile has 59 files, adds the registry as its sole substantive membership delta, and verifies closure over every registered workflow input and output; replacing the versioned profile self-member accounts for the other path-set difference. Adversarial tests cover malformed profiles/manifests, missing registry closure, unsafe or colliding members, compression/encryption/metadata drift, prefix/trailer smuggling, tampering, size limits, selected-file drift, destination refusal, cleanup, and deterministic bytes. The pinned allowlists exclude known sensitive material and reject unlisted paths or asserted-state drift; they are not privacy classifiers. The later held-out evaluation planning artifact, beta-operations package, and any future cases, answer key, execution receipt, approval, or result are outside profiles v1 and v2 and require a separately reviewed profile version. This is a prototype-scope evidence handoff, not applicant-data export, contractual ownership/offboarding, partner acceptance, authenticity/signing, backup/disaster recovery, CPRA search/export, completed review, or beta evidence. |
| Shareable hypothetical ADU sample | Implemented surface for prototype data | `check.html?sample=adu` resolves the existing `woodland-new-detached-adu-local-layer` golden fixture, fills the normal intake, and submits through the same validation and matcher path as manual answers. The result cover sheet labels the facts as made up. While that sample remains active and unedited, a valid current availability record and an explicit applicability answer can expose or withhold the versioned future-state packet simulation. Editing a prefilled fact removes the sample URL state and clears the old result before recalculation. It is not a currently available City plan, real parcel, applicant-ready workflow, applicant record, pilot, or external validation result. |
| English/Spanish experience | Prototype | Intake, interface controls, applicant-facing result titles, and plain-language result explanations have English/Spanish variants. `scripts/check_applicant_copy.mjs` strictly checks catalog key order, nested shapes, stable option identifiers, formatter arity, static and formatter placeholders, nonblank singular/plural outputs, and a copy-leaf pseudo-expansion transform. It does not generate or render a complete pseudolocale catalog or review meaning. Spanish explanation copy remains an unreviewed machine draft; canonical pathway labels, rule notes, document hints, source excerpts, and much dashboard content remain English; no semantic-parity review has been completed. |
| Accessibility | Prototype | Static/code audit targets WCAG 2.2 AAA. Forty-five automated browser checks cover all five initial pages, 320px and 390px reflow without document overflow, compact mobile navigation, populated route-first results, collapsed/expanded support disclosures, representative statewide-handoff profiles, labeled mobile evidence records, valid/invalid journey-summary disclosure, and isolated no-overflow print-media states. Result states expose a semantic decision-boundary note with labeled definition-list rows for what the result shows, what remains unconfirmed, and the next staff step; browser contracts cover candidate, unresolved-fact, no-route, and source-review-hold copy. The Statewide Coverage Navigator has native outer/nested disclosure, list, and note semantics, a 64px outer and 44px HCD-disclosure target, and HCD links with programmatic jurisdiction/date/authority context. Its browser checks cover keyboard expansion, zero-HCD, linked-HCD, limited-local-layer, `Not encoded`, changed-statewide, and changed-local profiles; they include axe scans, storage boundaries, and no-overflow assertions. It is not human assistive-technology or physical-device evidence. `docs/MANUAL-VALIDATION.md` defines the signoff-required human test matrix, but physical-device, virtual-keyboard, screen-reader, keyboard, zoom, forced-colors, printed-output, and Spanish-pronunciation rows remain `not_run`. |
| Free-text grounded Q&A | Planned | Described as an architectural direction; no executable question-answering surface exists. |
| Scenario B staff workflows | Not targeted in v1 | No live status integration, report/letter drafting, plan check, or comment-resolution workflow exists. |
| Applicant-data privacy | Implemented for the no-storage demo; proposed beta operating controls not approved | The current browser/server demo does not persist submissions. The proposed beta package pins an empty service field/purpose inventory, exact current-page fields, no applicant-answer network submission, and role-based retention, deletion, CPRA routing, incident, support, release, and rollback procedures. It also states that a static host and external operational systems may separately process metadata. Every deployment inventory, rehearsal, approval, and partner decision is still null/`not_run`. The evidence ZIP's pinned profile excludes known sensitive material and is neither a privacy classifier nor a sensitive-record export. No CPRA, Information Practices Act, SAM, SIMM, privacy, or security compliance claim is made. |

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
   only selected known sources; the generated statewide profile is a dated
   summary of those committed inputs, not a local-material search. Neither
   surface discovers newly enacted law or new local materials.
2. **Adoption and accountable review still require people.** A completed
   watch can emit a proposed receipt, and one repository-adopted snapshot now
   reaches statewide results and the bounded Woodland route/checklist/parcel
   bindings. A schema-v2 worklist derives exact source, rule, Golden,
   requirement, source-backed field, remedy, packet, and journey tasks and can
   create a separate blank decision ledger. The workflow does not automatically
   adopt a proposal, select an authorized reviewer, fill assignments or
   dispositions, approve replacements, or publish them. A completed ledger
   cannot perform any of those actions.
3. **Verification strength remains unproven beyond machine linking.** Explanation records bind
   to digests of selected citation fields and the full normalized rule record;
   completed review claims require reviewer, method, date, and reviewed
   version. A parallel `machine_linked`/`human_reviewed`/`jurisdiction_approved`
   schema-v2 ledger now exists for rules themselves
   (`rule_verification.py`). Promotion binds both citation and full-rule
   fingerprints; source change, source age, review age, or fingerprint drift
   demotes the effective claim. Every current rule is still only
   `machine_linked` — the ledger has no real promoted entry or independent
   signature. The harness CLI and public evidence page expose this coverage;
   neither is evidence of a completed human review.
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
   official preapproved-plan checklist, but the official program page checked
   2026-08-09 says **“Preapproved ADU List: Coming soon!”** The sample is a
   source-bound future-state simulation, not a currently usable plan or
   applicant-ready workflow; its mapping and action copy remain review-pending
   and are not comprehensive local-code coverage. The generic local-source
   onboarding contract can inventory a future source package and fail closed
   on missing bindings, but its committed template is `not_run`; it supplies
   no local source authority, human review, jurisdiction approval, rule
   authoring, or publication evidence.
7. **Browser and Python behavior can drift.** Screening, staleness, scanning,
   and clocks are duplicated without cross-runtime contract tests. The
   readiness page avoids a second evaluator by rendering a result generated by
   the Python implementation. Python and browser code now share one strict
   registry selection and reject registry ID/path/fingerprint drift, while the
   browser validates and consumes the generated Woodland journey contract for
   one synthetic route-to-packet transition. This bounds artifact selection
   and this one case but does not remove the need for
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

The bounded Woodland slice is a first executable, source-bound future-state
simulation. The official program page currently says its plan list is coming
soon, so this slice is not available to a real applicant. It provides one
25-item requirement manifest, one synthetic inventory, explicit
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
case. A strict, date-bound program-availability record additionally blocks the
browser handoff when official-page evidence is missing, malformed, or expired;
passing that check permits only the labeled future-state simulation.

The current browser routing result remains a transient presentation of
applicant-supplied facts and matched prototype records. The linked packet page
replays a generated synthetic record and demonstrates parcel-field provenance
with fabricated values. On the exact valid entry it can also present those
integrity-checked route and packet records as a print-focused synthetic
summary. Browser Print/Save may create a user-controlled artifact, but the app
does not store or retrieve it. Neither surface implements live parcel retrieval
or the planned document-aware, persisted permit-readiness packet for a real
application.

### Statewide orientation without local-coverage overclaim

The Statewide Coverage Navigator is the thin statewide layer to build before
attempting to encode every jurisdiction's ordinance. At a recognized registry
selection, it makes the data boundary visible before a project answer is
interpreted: the bounded statewide ADU/JADU/SB 9 inventory can be screened;
the repository either has a limited jurisdiction-scoped record or does not;
and a dated public HCD record may or may not be linked to that jurisdiction.
It then displays a local-onboarding checklist—operative source passages and
effective dates; current forms, checklists, fees, and process pages; official
URLs/check dates/content fingerprints; project and parcel scope, exceptions,
and unresolved questions; plus review ownership and a re-verification
cadence.

This is an implemented discovery and handoff surface, not statewide local-code
coverage. It does not scrape a jurisdiction site, contact a jurisdiction,
refresh the HCD dataset at runtime, establish an operative ordinance, infer
that unlinked history is absent, decide project eligibility, or create a
local rule from a source URL. It gives a lower-capacity jurisdiction a clear
starting artifact while reserving the deeper applicant journey for a
jurisdiction-owned, reviewed local layer.

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
| P0 | Retarget the bounded ADU packet-presence slice to an active, reviewed pilot workflow | Woodland's official page currently lists no preapproved plans, so the current slice is useful only as a source-bound future-state simulation. | With a willing jurisdiction and an active permit subtype, compare results on a small set of public, synthetic, or redacted packets with staff-authored completeness notices. |
| P0 | Execute source-state operations with accountable ownership | The reviewed publication overlay and schema-v2 worklist now propagate exact rule/Golden, requirement, source-backed field, remedy, packet, and configured journey effects. The current queue is clear and no human maintenance activity is evidenced. | Adopt a proposed historical/simulated revision through the separate publication process, complete the fingerprint-bound assignments and dispositions with named authorized roles, and measure detection-to-republication time. |
| P0 | Verification levels and evaluator provenance | Makes “verified” meaningful to staff and counsel. | Schema-v2 machine-linked, human-reviewed, and jurisdiction-approved states exist for the full 19-rule set with tested full-rule/citation binding and source-change/source-age/review-age demotion (`rule_verification.py`); every rule is still only `machine_linked`. Next: recruit a named reviewer to review and promote one rule; the public evidence page already exposes aggregate coverage. |
| P1 | Parcel fact retrieval for one jurisdiction | Replaces high-risk self-attestation for zoning, hazards, historic status, and transit with sourced facts. | Run a known parcel set and have staff review disagreements and unknowns. |
| P1 | Local-rule authoring and re-verification workbench | The Statewide Coverage Navigator exposes the onboarding boundary, and a strict portable intake now validates a future unreviewed source package without pretending that it creates a local layer. A workbench can later turn jurisdiction-owned, fingerprint-bound inputs into separately reviewed and published records. | Have a reviewer approve/reject AI-proposed rules beside exact source passages; measure time and disagreement. |
| P1 | Held-out conformance evaluation | Could measure review-queue behavior beyond the fixture that shaped the scanner; no held-out result exists yet. | Use the implemented `not_run` contract to freeze independently sourced passages and a two-reviewer answer key, then report only the six raw confusion/abstention counts by check. |
| P1 | Comparable-jurisdiction precedent explorer | Converts the existing HCD-letter dataset into a useful Scenario C workflow. | Ask staff to resolve a known issue using cited, issue-matched examples and compare time to their normal search. |
| P2 | Review-comment resolution matrix | Extends the evidence model into Scenario B without attempting full plan check. | Track each public/synthetic comment as addressed, partial, conflicting, or unresolved with response evidence. |
| P2 | Read-only status adapter and cited staff drafts | Reduces calls and transcription while preserving existing systems and staff sign-off. | Map one jurisdiction export/API to a small common event model and generate a clearly marked draft from locked facts. |
| Later | SB 35, AB 2011, and additional domains | Broadens routing after the pilot proves the schema and maintenance loop. | Add one domain only with official sources, negative/boundary fixtures, local interaction tests, and an owner for updates. |

### What to remove or defer

- Do not lead with the registry count without immediately distinguishing the
  statewide candidate-rule set from the two incomplete local metadata records.
- Do not turn a linked HCD letter, or the absence of one in the dated snapshot,
  into a compliance, enforcement, or local-coverage conclusion.
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

`docs/DATA-FLOW.md` records the current no-storage synthetic-demo boundary and
the proposed no-application-storage beta operating flow. ADR 0002, the beta
operations runbook, and a strict prepared/not-approved ledger now cover the
deployment inventory, retention/deletion, CPRA routing, access, incident,
support, release, and rollback plan. The actual host/subprocessor inventory,
cost envelope, threat/control review, records rehearsal, human accessibility
record, and every role approval remain external work. These are
deployment-specific controls, not blanket legal compliance.

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

A credible showcase can demonstrate the synthetic routing and source-bound
future-state Woodland packet records as bounded prototypes, including the
official-page availability hold, their unsupported/abstention paths, and
source bindings. A stronger pilot would add one active jurisdiction workflow,
one sourced parcel journey, real or properly redacted file evidence, reviewed
requirements and remedies, and execute the exact affected-output worklist
through review, approval, republication, and rollback after a controlled
source revision. Every narrated claim should be reproducible from the
repository, and every simulation, sample, untranslated surface, unreviewed
draft, and unverified rule should be visible as such. This aligns with the
showcase's Scenario A and Scenario C goals without claiming that the current
Woodland plan program is live.
