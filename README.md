# Permit Bearings

**Check a California ADU, JADU, or SB 9 project. See the sources behind the
result. Take unresolved questions to staff.**

Permit Bearings is a prototype decision-support tool for California ADU, JADU,
and SB 9 projects. Structured applicant facts produce candidate routes,
relevant standards, cited official sources, and questions for local staff. The
matcher is deterministic. Separate English and Spanish explanations are
AI-assisted, review-pending drafts.

## Quickstart

Open `index.html` directly, or run
`python3 -m http.server 8765` and visit `http://localhost:8765/`. The landing,
applicant guide, packet sample, ordinance screen, and evidence page use
relative links and work without network requests. Only the four data-driven
pages load the generated `data/demo-data.js` bundle.

A separate bounded sample compares a made-up Woodland packet inventory with
25 source-bound items from one City preapproved ADU checklist. The City's
[official program page](https://www.cityofwoodland.gov/1616/Preapproved-ADU-Plan-Program),
checked 2026-08-09, says **“Preapproved ADU List: Coming soon!”** No listed
City plan was identified. The flagship is therefore a **source-bound
future-state simulation**, not a currently usable preapproved-plan workflow
or applicant-ready service. Two fabricated parcel values are bound to the
`CITY` and `LU_Descr` fields exposed by Yolo County's public parcel-layer
metadata; no address, APN, or live parcel is queried. The sample does not open
files, verify parcel facts, reproduce a complete local checklist, determine
final eligibility, certify submission completeness, or approve permits.

At build time, a versioned synthetic journey definition binds the existing
Woodland golden routing fixture to that readiness workflow and packet. The
generated, fingerprinted envelope is also the browser's fail-closed handoff
contract for these prototype inputs. A strict portable registry at
`data/workflows/registry.json` selects the workflow, packet, remedy, journey,
availability, and generated-output paths. It raw-byte-pins every canonical
input; generated destinations are path-bound and rebuilt before use. Build and
CLI code resolve those paths through stable IDs and explicit availability policies.
The Python boundary rejects ambiguous or oversized JSON, linked files,
cross-platform-unsafe paths, duplicate IDs, orphan files, shared paths,
fingerprint drift, and mismatched IDs. Bundle format 6 separately hashes the
exact raw registry against its generation receipt and validates every input
pin in the browser; browser code cannot inventory files absent from a bundle.
The registry contains one prototype workflow and names that same entry as the one
browser default; it is infrastructure for adding a reviewed workflow, not
evidence that multiple workflows are active. A separate strict availability record at
`data/availability/woodland-preapproved-adu-program.json` binds that contract
to the official program-page evidence and a date-bound recheck. The browser
blocks the handoff when that record is missing, malformed, or expired. Within
that simulation boundary, only the active, unedited made-up Woodland sample
can offer the packet step. The applicant must explicitly answer its remaining
workflow-applicability question; no answer is selected by default. A matching
**Yes** opens the versioned packet example, while **No** or **I'm not sure**
withholds it and preserves the relevant boundary or staff question. **Yes**
does not establish that a City plan is available.

On an exact, integrity-checked future-state simulation entry whose
availability record is still within its recheck period, the browser also
composes a print-focused summary from that envelope: the candidate route,
made-up facts, the three reported-missing preparation actions, staff
questions, source evidence, the prototype boundary, and the public journey
ID/version. The button opens the browser's print dialog, where a person may
choose Print or Save as PDF. The app does not create, upload, or store a file,
and direct, invalid, or unavailable packet entry withholds the summary with
the underlying findings.

**Live demo:** https://chelseakr.github.io/permit-pathways/

**External evidence gate:** prepared, not run. The repository now binds future
content review, same-version sessions, manual access/language checks, a timed
maintenance rehearsal, and a qualifying partner step to explicit ledgers and
thresholds. No reviewer outcome, participant result, accessibility signoff,
Spanish semantic approval, completed rehearsal, or partner commitment is
claimed. Inspect the current status on the live **Sources & limits** page or in
[`data/validation/woodland-flagship-gate.json`](data/validation/woodland-flagship-gate.json).

**Beta operations package:** **PREPARED / NOT APPROVED**. A proposed ADR,
role-based runbook, portable control ledger, and strict validator now define a
pilot-neutral public/static boundary with no accounts, uploads,
application-managed applicant storage, browser persistence, application
telemetry, runtime external model calls, or permitting-system writeback. Every
deployment field, human approval, records rehearsal, and partner decision is
still null/`not_run`. Static hosts and operational systems may separately
process request or operational metadata and require deployment-specific
review. See
[`docs/BETA-OPERATIONS-RUNBOOK.md`](docs/BETA-OPERATIONS-RUNBOOK.md).

**Made-up Woodland future-state route-to-packet simulation** (answer the
applicability question to continue only if the availability record passes):
https://chelseakr.github.io/permit-pathways/check.html?sample=adu

See [docs/PRODUCT-CONTEXT.md](docs/PRODUCT-CONTEXT.md) for the capability
truth, challenge fit, and prioritized opportunity map. Repository-specific
contributor and agent guardrails live in [AGENTS.md](AGENTS.md). The visual
and interaction alignment with California Web Standards is recorded in
[docs/DESIGN-SYSTEM.md](docs/DESIGN-SYSTEM.md).
Two project-specific machine-generated editorial illustrations use the same California token palette on
the landing and project-check introductions. They are local, compressed WebP
assets with empty alternative text because they repeat nearby orientation
copy; they do not depict or imply a permit decision.
The measurable path from this automated-tested prototype to one bounded,
active-jurisdiction beta is in [docs/BETA-ROADMAP.md](docs/BETA-ROADMAP.md).
The execution, privacy, scoring, and claim rules for the external evidence
gate are in [docs/VALIDATION-EVIDENCE.md](docs/VALIDATION-EVIDENCE.md).
The proposed no-application-storage operating procedure and its pending
decision boundary are in
[docs/BETA-OPERATIONS-RUNBOOK.md](docs/BETA-OPERATIONS-RUNBOOK.md) and
[ADR 0002](docs/adr/0002-retain-no-storage-beta-boundary.md).

## Run it

The verification commands require Python 3.12, `uv`, and Node.js 24. Browser
checks additionally install the locked npm dependencies and Playwright's
Chromium build.

```sh
make verify                                        # locked Python quality/security/data gates
npm ci && npx playwright install chromium          # one-time browser test setup
npm run test:a11y                                  # axe, reflow, and journey-state checks
npm run test:perf                                  # Lighthouse category budgets
PYTHONPATH=src python3 -m permit_pathways.transit --gtfs corpus/gtfs/unitrans.zip --lat 38.5449 --lon -121.7442
PYTHONPATH=src python3 -m permit_pathways.conformance <ordinance.txt>  # scan
PYTHONPATH=src python3 -m permit_pathways.conformance_evaluation_cli validate-plan
PYTHONPATH=src python3 -m permit_pathways.harness   # verification report
PYTHONPATH=src python3 -m permit_pathways.harness --fetch            # live source diff
PYTHONPATH=src python3 -m permit_pathways.harness --fetch \
  --snapshot-out source-state-proposed.json \
  --snapshot-id source-watch-local-1 \
  --checked-at 2026-08-03T17:08:28Z \
  --receipt-method local_source_currency_watch \
  --run-url https://github.com/ChelseaKR/permit-pathways \
  --commit-sha 8d841409dc5fd16fe56b52a8b57c826c07f176a6
PYTHONPATH=src python3 -m permit_pathways.harness --assume-changed ca-gov-66321
PYTHONPATH=src python3 -m permit_pathways.readiness_cli \
  --workflow-id woodland-preapproved-detached-adu --as-of 2026-07-30
PYTHONPATH=src python3 -m permit_pathways.review_queue_cli  # read-only source-change worklist
PYTHONPATH=src python3 -m permit_pathways.local_source_onboarding_cli \
  validate                                      # validates the empty not_run template
PYTHONPATH=src python3 -m permit_pathways.deployment_smoke # live static-route/artifact smoke check
PYTHONPATH=src python3 -m permit_pathways.beta_operations  # validates PREPARED / NOT APPROVED only
PYTHONPATH=src python3 -m permit_pathways.evidence_export_cli build \
  --output /tmp/permit-bearings-evidence.zip \
  --freeze-id public-synthetic-evidence-2026-08-09 \
  --frozen-on 2026-08-09                       # committed public/synthetic data only
make evidence-export-check                     # disposable build/verify/restore round trip
node scripts/check_applicant_copy.mjs           # structural locale/pseudolocale contract
python3 -m http.server 8765                         # full static showcase
PYTHONPATH=src python3 demo/app.py 8766             # Python reference demo
# The Python server exposes the landing at /index.html and tools at
# /check.html, /prepare.html, /review.html, and /evidence.html.
python3 scripts/build_demo_bundle.py                # after canonical JSON changes
```

The review-worklist CLI returns `0` for a valid clear queue, `1` for a valid
queue with human work remaining, and `2` for invalid input or output. Neither
its worklist nor its separate decision ledger changes the adopted source state
or publishes anything. The deployment-smoke command returns only an
availability/artifact-shape result.

The beta-operations validator returns `0` only when the exact pilot-neutral
planning package remains `prepared_not_approved`, every deployment and
records-execution field remains null/`not_run`, all nine role approvals remain
null/`not_run`, all 17 controls match the pinned contract, and the ADR/runbook
raw-byte SHA-256 bindings still match. Exit `0` is schema evidence only; it
cannot approve a beta,
deployment, partner decision, privacy/security posture, records workflow, or
legal compliance. A later execution or approval requires a separately
reviewed schema.

The evidence-export `build` command returns `0` only after its selected files
are verified against Git `HEAD`, packaged in the single canonical ZIP
representation, and checked against the pinned public/synthetic profile.
Archive-only `verify` and `restore` validate the recorded commit identifier,
profile, hashes, bytes, and canonical structure; they do not retrieve or
authenticate the originating Git commit. Both are inert and do not adopt,
approve, or publish records. The exact format, operator commands, privacy
boundary, and limitations are in
[docs/EXPORT-RESTORE.md](docs/EXPORT-RESTORE.md).

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
| Observability | N/A — the deployed artifact is a static, no-account, no-telemetry showcase rather than a long-running production service. The proposed no-storage beta runbook still requires host request-metadata and operational-system review because those records sit outside application telemetry. Storage, telemetry, uploads, or external model calls would trigger a new architecture and operational review. |
| Accessibility | Axe runs on all five public pages plus populated candidate-route and valid packet states; Lighthouse covers seven public page states. Browser tests also check 320px and 390px reflow, compact mobile navigation, the Spanish handoff language boundary, labeled mobile evidence records, document-level overflow, and the print summary's isolated print-media layout. The versioned human test matrix in `docs/MANUAL-VALIDATION.md` keeps physical-device, virtual-keyboard, keyboard, screen-reader, zoom, forced-colors, printed-output, and Spanish semantic review explicitly `not_run` until signed evidence exists. |
| Internationalization | Applies. `make verify` enforces English/Spanish catalog shape, stable option identifiers, formatter arity, static and formatter placeholders, nonblank singular/plural output, and a copy-leaf pseudo-expansion transform. This is structural automation only: it does not generate or render a complete pseudolocale catalog, and mixed-language acceptance and native Spanish semantic review remain pre-pilot work in `docs/I18N.md`. |
| AI Evaluation | Applies to the offline AI-assisted rule/explanation workflow. Deterministic matching has model-independent fixtures; natural-language legal fidelity, applicant comprehension, and Spanish semantic parity remain unreviewed and are not inferred from those tests. |
| Documentation | Capability status and public claims are maintained in the README, product context, design, demo script, accessibility notes, and ADR log. |
| Quality & Metrics | Automated evidence includes public Python tests with branch-aware coverage, 29/29 Golden cases, browser checks, and seven Lighthouse page states, plus dependency audits, source-currency output, the exact re-verification worklist, the deployment-smoke contract, the applicant-copy structural contract, local illustration path/format/size/accessibility checks, the strict workflow-registry boundary, the deterministic evidence-export round trip, adversarial no-storage operations-package checks, and the local-source onboarding contract. Browser contracts cover canonical, changed, unrelated, and unverifiable adopted source-state receipts; duplicate-ID, portable-path, raw-registry, and input-fingerprint workflow-registry states; and distinct statewide-coverage, decision-boundary, route-first, collapsed/expanded support, keyboard, reflow, illustration-decoding/tablet-hierarchy, and multi-route accessible-name states. Python registry tests separately inventory canonical directories and reject orphan or linked files. Exact current counts and coverage come from CI rather than this prose. The harness reports `automated source/regression checks: pass`; this means those bounded checks passed, not that the law, interpretations, workflow, operating package, local-source intake, or deployment are approved. The public evidence page exposes the rule-review level: all 19 rules are `machine_linked`, with zero named human reviews or jurisdiction approvals. |
| Versioned release | N/A — this remains a branch-deployed showcase with no published package, container, action, or signed release. The trigger for replacing this N/A is recorded in `docs/adr/0001-no-versioned-release.md`. |

## How the project check works

1. The applicant selects a jurisdiction and supplies structured project facts.
   When the selection matches the registry, the browser also offers a closed
   native disclosure for that jurisdiction's generated statewide coverage
   profile. It separates the bounded
   statewide candidate-rule inventory from any limited local record, shows the
   dated public HCD history linked in the committed dataset, and lists a
   local-onboarding checklist for a maintainer considering a local layer.
   If a changed source dependency affects the statewide or local inventory,
   that part of the profile is visibly held for source review; an
   unverifiable source remains a warning rather than a change finding.
   The profile is a static orientation aid: it does not look up a parcel,
   retrieve current local materials, determine compliance, or make an approval
   finding.
2. Deterministic criteria match those facts to the bounded rule set. No live
   model and no free-text answer determine eligibility.
3. The browser puts the candidate route before supporting records, then places
   the temporary answers-used receipt and statewide staff handoff in closed
   native disclosures. It also summarizes matching records by group and
   provides jump links. The answers receipt exists only in the current page;
   it is not a stored or exportable applicant record.
4. Result cards keep their consequence, citation, and source-status label
   visible while every longer explanation, next-step, and evidence body starts
   closed. The configured candidate route receives the strongest visual
   treatment; this is hierarchy, not a ranking, recommendation, final route,
   or eligibility finding.
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
10. Every recognized city or county receives a bilingual, print-focused
    orientation receipt from the current in-memory result. It preserves the
    selected facts, candidate routes and source status, labels whether a
    bounded local record exists, and supplies questions for local staff. The
    browser handles Print or Save as PDF; the app does not upload or store the
    receipt. It is not a complete local checklist, parcel verification,
    eligibility or completeness finding, or approval prediction.
11. For the active, unedited made-up Woodland sample only, the browser checks
    the generated journey, route, readiness, fingerprint, source-review, and
    strict program-availability contracts. A missing, malformed, or expired
    availability record blocks the handoff. If those checks pass, it asks one
    explicit applicability question. Nothing is preselected: **Yes** exposes
    a future-state packet simulation link, **No** records that the bounded
    workflow does not apply, and **I'm not sure** shows the exact staff
    question. The link contains only the public journey ID and version, not
    project facts, and does not represent a currently listed City plan.

The current app covers statewide ADU, JADU, and SB 9 screening; a generated
coverage profile and bounded orientation handoff are available for all 541
registry entries, while only two jurisdictions have local rule records.
Parcel retrieval, application-file inspection, packet-level completeness,
reviewed remedies, SB 35, AB 2011, reviewed translation, and comprehensive
local rules are planned rather than implemented. The temporary result packet
and coverage profile do not change those boundaries.

## How the bounded packet sample works

1. `data/workflows/registry.json` is the strict path and fingerprint boundary.
   It currently registers exactly one prototype entry and selects it as the
   browser default. Registration does not make the workflow active,
   applicant-ready, reviewed, or jurisdiction-approved.
2. `data/readiness/workflows/woodland-preapproved-detached-adu.json` encodes
   25 requirements from one City of Woodland checklist, source checked
   2026-07-29, for a simulated project that would use a City preapproved
   detached ADU plan. The checklist itself is not presented as inherently
   dated. The official program page was separately checked 2026-08-09 and
   says **“Preapproved ADU List: Coming soon!”**; the sample is not evidence
   that a plan is currently available.
3. `data/readiness/samples/woodland-preapproved-adu.json` supplies one made-up
   project and an explicit inventory status for every requirement. Two
   concrete parcel-fact fixtures are tied to exact fields in the recorded Yolo
   County parcel-layer metadata; the values themselves are fabricated and the
   evaluator does not query a live parcel or inspect a plan, form, or file.
4. `src/permit_pathways/readiness.py` deterministically applies the workflow
   conditions. Missing items remain gaps, unknown facts become staff
   questions, and a changed or stale checklist or parcel-schema source
   prevents a favorable packet summary.
5. `python3 -m permit_pathways.readiness_cli` selects the registered workflow
   by stable ID and prints the machine-readable
   evidence manifest. By default, source age is checked against the current
   UTC date; historical replay requires an explicit `--as-of` date. The build
   uses the same Python evaluator with the sample's recorded date to generate
   `data/readiness/generated/woodland-preapproved-adu-evidence.json` and the
   static bundle.
6. `data/availability/woodland-preapproved-adu-program.json` strictly binds
   the future-state simulation to the official program page, its checked date,
   excerpt fingerprint, status, boundary, and recheck deadline. The browser
   withholds the route-to-packet handoff when this record is missing,
   malformed, or expired; it cannot create a match or establish real-world
   applicability.
7. `data/journeys/woodland-preapproved-detached-adu.json` references the
   golden screening case, candidate route, readiness workflow, packet, and
   applicant-editable applicability fact. `src/permit_pathways/journey.py`
   fails closed unless those records agree, then the build writes
   `data/journeys/generated/woodland-preapproved-detached-adu.json` and embeds
   the same envelope in the static bundle. The envelope emits per-fact
   provenance and the candidate route's recorded source-status date and
   review deadline. The browser independently checks the envelope, its linked
   route and readiness evidence, their fingerprints, current source-review
   windows, and program availability before offering a simulation handoff from
   the canonical sample.
8. The handoff URL contains exactly `journey=<public-id>&version=<version>`.
   It carries no project facts and uses no local storage, session storage, or
   cookies. `prepare.html` withholds packet findings on direct, malformed,
   duplicated, mismatched, stale, or expired-availability entry; a valid
   simulation entry replays and renders the generated Python result. It does
   not contain a second packet evaluator.
9. For that exact valid simulation entry, the page derives a print-focused
   journey summary from the same integrity-checked records. It combines the
   candidate route,
   labeled synthetic facts, exactly three reported-missing preparation
   actions, three staff questions, route/checklist/parcel-metadata evidence,
   the prototype boundary, and journey ID/version. The print control calls the
   browser's native print dialog; the app stores no export. The action block
   remains labeled AI-assisted, review-pending, and not human-reviewed.
   Invalid or direct entry leaves the summary hidden.
10. The checklist mapping and plain-language action copy are AI-assisted
   drafts. They are versioned, fingerprint-bound, and marked
   `prototype_review_pending`; no named human, planner, or Woodland reviewer
   has approved them. A generated content fingerprint detects action-copy
   drift; it is an integrity check, not evidence of human review. Mapping
   metadata binds the exact checklist and
   parcel-schema source digests and records that provider, model, and a
   reproducible run record are unknown or were not retained.
11. No model runs in the CLI, build evaluator, or public browser. The public
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
dependency IDs to mark affected rules stale. A completed watcher run can emit
a machine-readable **proposed** snapshot. The scheduled workflow retains that
proposal as an artifact but never rewrites public state. A repository
maintainer must deliberately adopt a completed-run receipt in
`data/source-status/current.json`; the bundle accepts only a strict
`reviewed` receipt and fails closed when its source-registry digest,
observations, or derived rule/Golden impacts drift.

For this receipt, `reviewed` means selected for publication after checking the
run binding. It is not legal, jurisdiction, counsel, or substantive content
approval, and it does not identify a human reviewer. Bundle format 6 carries
the adopted overlay, strict program-availability record, and rule-verification
ledger into the browser. A fetched changed source stales only
exact dependent statewide records and blocks a Woodland route or packet only
when that source is bound to the route, checklist, or parcel metadata. An
unverifiable fetch remains a visible warning and stales nothing. The separate
§ 66321 control is still a temporary rehearsal layered over this committed
state. New-law discovery, automatic adoption, staffed review assignment,
approval history, and automatic publication remain planned.

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

The held-out evaluation contract is implemented as a validated
`status: not_run` planning manifest in
`data/conformance/evaluations/heldout-v1/manifest.json`; the evaluation itself
is still planned. The strict Python interface in
`src/permit_pathways/conformance_evaluation.py` validates the plan, frozen case
set, a key carrying two declared blind reviewer records and adjudication, and
blind predictions; it can
generate blind predictions, score raw pairs, and write a result exclusively
while returning its out-of-band SHA-256. No cases, key, predictions, result,
or run receipt exists. The CLI exposes `validate-plan`; blind `predict` accepts
frozen cases, an output path, timestamp, and declared commit SHA but
intentionally has no answer-key argument. `score` requires the frozen cases,
blind prediction receipt, and key carrying the declared reviewer/adjudication
records. `validate-result` reloads those frozen inputs and the result, then
recomputes the bounded pair outcomes and raw partitions before accepting the
receipt.
Both write paths refuse to overwrite an existing output, return the
whole-artifact SHA-256, and use exit 2 for invalid input or output. The plan
pins the current scanner and nine-check registry, defines the scoring unit as
one `(case_id, check_id)` pair, and permits only
`should_flag`, `should_stay_quiet`, or separately counted
`reference_abstain` reference judgments. Flag and quiet mean only that the
exact passage should enter or stay out of that exact check's review queue;
quiet does not mean conformant. Per active check, the future official corpus
must contain at least one targeted flag pair and one preselected candidate
near-miss quiet pair; incidental findings cannot satisfy that coverage, and
synthetic controls stay separately denominated. Development-source exclusions
carry canonical URLs and retained digests when available. The case-set schema
requires a custodian's near-duplicate-review attestation, while the manifest
fixes the exclusion disposition; semantic overlap review remains external.
Scoring must cover the full case-by-active-check Cartesian
product so unexpected cross-check flags cannot be omitted. Targeted coverage
uses one target check per case; multi-target cases are unsupported in v1. The
six raw counts must remain recomputable overall, per check, and separately for
official and synthetic strata from pair-level observations.
The case set, answer key, blind predictions, result path, evaluator hash, and
all freeze, prediction, and scoring receipts remain null until
official passages are independently collected, fingerprinted, reviewed,
adjudicated, and frozen. A future receipt must record freeze, blind prediction,
answer-key unblinding, and scoring in that order. Unblinding retires that
corpus for future scanner versions; any post-run tuning needs a newly selected
corpus. The binary scanner has no machine-abstention output; an execution error
must fail rather than become an abstention. A future result must bind every
input digest internally; its whole-artifact SHA-256 is recorded out of band
because the result cannot contain its own byte hash. The result binds the
manifest digest directly. Receipt commit SHAs are
recorded bindings; this interface does not retrieve or authenticate Git
objects. Until that external work and a bound run exist, there are no held-out
precision, recall, accuracy, or statewide-coverage results to report.

Conceived 2026-07-27 for the California AI Permitting Innovation Showcase
(ODI / GovOps / CHHA / GO-Biz). See [PROVENANCE.md](PROVENANCE.md).

## Showcase scenario mapping

| Scenario | Coverage |
|---|---|
| Scenario 1 (A): guiding applicants to a complete, well-routed application | Primary prototype. Candidate ADU, JADU, and SB 9 routing, a temporary grouped result packet, citations, uncertainty routing, and one generated synthetic Woodland packet-presence future-state simulation are implemented. The official program page currently says its preapproved plan list is coming soon, so this is not an applicant-ready workflow. The sample uses 25 source-bound checklist requirements, two fabricated values tied to official parcel-layer fields, and review-pending AI-assisted action drafts. Live parcel retrieval, file inspection, parcel-specific packet completeness, reviewed remedies, and reviewed translation are planned. |
| Scenario 2 (B): supporting internal review | Not targeted in v1. |
| Scenario 3 (C): keeping current with housing law | Prototype assurance layer beneath Scenario 1. Selected-source checking, proposed run receipts, deliberate snapshot adoption, exact rule/Golden and bounded packet-context worklists, applicant-output invalidation, separate fingerprint-bound decision templates, and an HCD-letter dataset are implemented in bounded form. Search, new-law discovery, automatic adoption/publication, completed staffed assignments, comparable-jurisdiction research, and substantive approval history are planned. |

## Design commitments (from the challenge statement's cross-cutting requirements)

- Decision support, never a legal agent; abstention over confabulation.
- Rules, sources, cases, and review artifacts use portable files. A pinned,
  deterministic ZIP can export and restore-verify either the frozen 58-file
  schema-v1 compatibility set or the current 59-file, registry-aware schema-v2
  public and synthetic evidence set without vendor-only storage. The held-out
  evaluation planning artifact, beta-operations ADR/runbook/ledger/tooling,
  and any future cases, answer key, execution receipt, approval, or result are
  outside export profiles v1 and v2 and require a separately reviewed future
  profile version. This is not a production applicant-data export,
  contractual ownership/offboarding,
  partner acceptance, backup, or CPRA workflow. This prototype has no
  accounts, uploads, or applicant-data store.
- A proposed beta operations package documents the current
  no-application-storage boundary, deployment inventory, retention/deletion,
  CPRA routing, incident, support, release, and rollback procedures. Every
  deployment-specific approval and rehearsal remains null/`not_run`; it does
  not establish CPRA, Information Practices Act, SAM, or SIMM compliance. Any
  applicant-data flow would require a superseding architecture and review.
- Dependency-light and designed to sit alongside existing permitting systems.
  Pilot integration, staffing, hosting, and cost evidence remain planned.
- WCAG 2.2 AAA target with a static computed-contrast audit
  (`docs/ACCESSIBILITY.md`); required human/assistive-technology checks remain
  open. English/Spanish intake, interface controls, and plain-language result
  drafts are prototyped. Spanish drafts have no human or semantic-parity
  review. Applicant-facing result titles are localized drafts; canonical
  source citations, excerpts, and generic document hints remain English.
  All five public pages load a locally maintained California Design System
  version-0 preview compatibility layer before product styles. It applies
  selected semantic `ca-*` structures, published California tokens, and local
  Public Sans webfonts while keeping decision/evidence records and the service
  header product-specific. The successor system is pre-Alpha with no
  production-supported release, so commit `f8775cf` is a design reference
  only: no successor package, source, or compiled bundle is vendored. This is
  component alignment, not conformance, certification, State branding,
  affiliation, or endorsement. The optional Python-rendered reference flow
  loads the same two style assets and uses the same component hooks instead of
  maintaining a separate visual system. See `docs/DESIGN-SYSTEM.md`.

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

A separate rule-verification ledger, now schema version 2
(`src/permit_pathways/rule_verification.py`,
`data/validation/rule-verification.json`) adds an explicit `machine_linked` /
`human_reviewed` / `jurisdiction_approved` level on top of the bare
`verified_on` date. Every current rule is recorded `machine_linked`; a
promoted level must bind both the exact citation fingerprint and the exact
full-rule fingerprint. A changed dependency, aged source evidence, aged
review, or fingerprint drift demotes the effective claim to `machine_linked`
rather than keeping a stronger claim alive. No rule has an actual named
reviewer or jurisdiction sign-off yet. `python -m permit_pathways.harness`
prints `automated source/regression checks: pass` when its bounded checks pass
and reports the effective level counts. The public evidence page exposes the
same coverage: all 19 current rules are `machine_linked`, with zero named
reviews and zero jurisdiction approvals. Neither surface can change which
rules match an intake or promote a claim.

The separate Woodland readiness workflow is also machine-assisted and is
explicitly a future-state simulation because the official program page says
no preapproved plan list is available yet. Its 25
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

**Statewide Coverage Navigator:** selecting a recognized registry entry shows
a generated profile from
[`data/jurisdictions/generated/coverage-index.json`](data/jurisdictions/generated/coverage-index.json).
It keeps three facts separate: the same bounded statewide candidate-rule set
is available for every registry entry; only the limited local records already
encoded in the repository are local coverage; and the linked public HCD
Housing Accountability Unit history is a dated dataset reference, not a
current compliance result. A profile with no local record means Permit
Bearings has not encoded one — it does not mean local requirements do not
exist. A profile with no linked HCD record means none was linked in the
committed dataset — it does not prove no HCD activity, compliance, or complete
coverage. The profile also lists a local-onboarding checklist for a maintainer
considering a local layer: operative ordinance sections and effective dates;
current forms, checklists, fees, and process pages; official URLs with
source-check dates and content fingerprints; project/parcel scope, exceptions,
and unresolved questions; plus accountable owner-role IDs and a re-verification
cadence. A source link alone never creates a local rule.

That checklist now has a separate, machine-testable offline intake contract at
[`data/onboarding/local-source-intake-template.json`](data/onboarding/local-source-intake-template.json).
The read-only validator accepts an empty `not_run` template, an in-progress
collection, or a complete `prepared_for_review` package. It strictly binds the
five source roles, source IDs/HTTPS URLs/fingerprints/check dates, operative
passage text and enactment/effective/check dates, project/parcel scope,
candidate exceptions, unresolved conflicts, open questions, and planned
accountable owner-role IDs/cadence. It binds every operative passage to the
declared ordinance role, rejects noncanonical metadata and malformed URLs,
and limits UTF-8 JSON input to 1 MiB. Historical CLI replay never reports
current readiness and emits its validation date and earliest recheck date. It
never accepts a reviewed, approved, encoded, or published
state, cannot change matching, and does not authenticate a publisher or create
a real local layer. The committed template contains no jurisdiction or source
data and all owner, cadence, review, and approval fields remain null/`not_run`.
It is outside evidence export profile v1; a filled partner copy needs a
separate data-classification and export decision.

A changed dependency in the adopted source-state receipt visibly places its
affected statewide inventory and any affected local source record on a
source-review hold. The raw citation remains available as evidence, but the
profile does not describe that inventory as ready to screen or use for
coverage until it is re-verified. An unreachable source remains a distinct
warning and does not create that hold.

The rule base currently covers, statewide: ADU ministerial review and the
15-business-day/60-day clocks, protected minimum unit, size allowances,
height allowances, parking limits and exemptions, the owner-occupancy
prohibition, conversion exemptions, pre-2020 unpermitted-unit legalization,
multifamily-lot 66323 allowances, JADU standards, SB 9 two-unit developments,
SB 9 urban lot splits, and the SB 9 × ADU unit-count interaction, plus
bounded local metadata records for the Cities of Davis and Woodland. A weekly
GitHub Action re-fetches selected statewide sources and classifies each as
unchanged, changed, or unverifiable. It opens a review issue when a fetched
source's content hash moved, a rule aged out, or a Golden scenario regressed;
a source it could not download is recorded as unverifiable with its last
successful verification date and marks no rule stale. Two
selected Woodland workflow
sources, the January 2026 Davis ADU handout, and HCD's October 2025 Davis
technical-assistance letter are recorded and watched. The Davis record reports
only the City's published processing categories; it preserves HCD's unresolved
ordinance-status warning and does not determine which category lawfully
applies. Comprehensive local-source and newly enacted-law discovery are not
implemented. Each scheduled run also retains a proposed source-state receipt.
The public build uses only the separately adopted receipt; it is a dated
snapshot, not a live per-page check or an automatic legal update.
When a review-needed watcher receipt includes at least one fetched source whose
content changed, the same job also retains a 30-day `source-review-package`
artifact containing the proposed receipt, an exact schema-v2 worklist, and a
blank fingerprint-bound decision template. Stale-rule-only and Golden-
regression-only runs still open the currency-review issue, but do not produce a
misleading source-change package. Changed checklist, parcel-field, rule,
Golden-case, remedy, packet, and configured journey effects follow explicit
IDs. Golden fixtures carry explicit `rule_dependency_ids`, including negative
and ambiguous expected-empty cases. Unverifiable sources create no work. The
artifact does not select an owner, complete review, adopt the proposal, clear
a hold, promote verification, or publish a replacement.

The full static showcase has five task-focused pages: an applicant-first
landing page; an English/Spanish applicant guide with review clocks; the
gated generated synthetic packet-presence sample; a bounded ordinance screen;
and an evidence-and-updates page. Project-specific local illustrations give the
landing and project-check introductions a visual anchor without adding a new
step or evidentiary claim; the project-check illustration is removed at
narrower breakpoints so the form stays primary. On a recognized jurisdiction selection, the
applicant guide offers the Statewide Coverage Navigator in a closed native
disclosure: a static profile of the bounded statewide inventory,
limited-local-layer status, dated public HCD history, and local-onboarding
requirements. A submitted result renders a dynamic grouped summary with jump
links, an always-visible decision boundary, and the visually primary candidate
route before supporting records. Every longer rule body starts closed; the
temporary answers-used receipt and statewide handoff follow in closed native
disclosures.
The boundary distinguishes candidate, unresolved-fact, no-route-in-the-bounded
corpus, and source-review-hold states; every candidate card also retains the
exact route-record name. Citations and source-status badges stay visible
outside the disclosures. Ordinary answer edits clear the old result until the
applicant submits again. Every recognized jurisdiction also receives a
bilingual print-focused orientation receipt derived from the current page:
facts used, candidate-route sources and currency, local-coverage status, and
questions for staff. Printing or saving is browser-owned and the app stores no
receipt. The applicant guide also includes plain-language
explanation drafts and an abstention path ("needs staff review") when no
encoded state pathway matches. Spanish explanation copy is an unreviewed
machine draft; applicant-facing titles are localized drafts while canonical
pathway labels, excerpts, citations, and document hints remain English when
shown. Stale and unverified records suppress action copy, interpretive notes,
and document hints. For the canonical active, unedited Woodland sample, an
explicit applicability answer can open the versioned packet step; all other
entry states fail closed. The packet page renders a Python-generated result
and links its evidence manifest. The same exact valid entry presents a
print-focused summary of the integrity-checked route, made-up facts, first
three preparation actions, staff questions, evidence sources, boundary, and
journey ID/version; its button delegates Print or Save as PDF to the browser
without creating an app-side export. The evidence page includes a clearly
labeled one-click rehearsal of an amendment to Gov. Code § 66321; matching
applicant records can be opened in the stale state, but the rehearsal is not
persisted production state. The smaller Python reference demo renders the same
explanation sidecar and keeps a separate `/trust` route.

## Layout

- `src/permit_pathways/screening.py`: deterministic pathway-screening engine
- `src/permit_pathways/explanations.py`: versioned explanation validation
- `src/permit_pathways/readiness.py`: deterministic bounded packet-presence
  evaluator and evidence-manifest generator
- `src/permit_pathways/readiness_cli.py`: packet-presence CLI
- `src/permit_pathways/journey.py`: strict versioned route-to-packet contract
  resolver for the synthetic Woodland fixture
- `src/permit_pathways/workflow_registry.py`: strict portable workflow,
  packet, journey, availability, and generated-output path registry with
  canonical-input raw-byte pins and complete artifact inventory checks
- `src/permit_pathways/program_availability.py`: strict, date-bound Woodland
  policy plus a conservative generic prototype policy whose exact negative
  excerpt, source/program IDs, canonical HTTPS program path, and fingerprint
  must agree; both are isolated from screening/readiness
- `src/permit_pathways/source_state.py`: strict watcher-receipt validation and
  exact rule/Golden dependency impact
- `src/permit_pathways/review_queue.py` and `review_queue_cli.py`: portable,
  fingerprint-bound source-change worklists and separate human decision
  ledgers that cannot clear holds or republish output
- `src/permit_pathways/local_source_onboarding.py` and
  `local_source_onboarding_cli.py`: strict read-only validation for a portable
  local-source intake whose maximum state is `prepared_for_review`
- `src/permit_pathways/deployment_smoke.py`: read-only public-route and
  generated-coverage-index deployment check
- `src/permit_pathways/conformance_evaluation.py`: strict `not_run` manifest
  validation and future frozen-case, blind-prediction, adjudication, and raw
  scoring contracts for the presence-based scanner
- `src/permit_pathways/conformance_evaluation_cli.py`: `validate-plan`, blind
  `predict`, declared-reviewer-key `score`, and recomputing `validate-result`
  commands with exclusive prediction/result writes
- `src/permit_pathways/evidence_export.py` and `evidence_export_cli.py`:
  deterministic, Git-bound public/synthetic evidence packaging, verification,
  and inert restore
- `src/permit_pathways/beta_operations.py`: strict validator/CLI for the
  pilot-neutral `prepared_not_approved` operating ledger; it rejects filled
  deployment, approval, rehearsal, and receipt fields
- `src/permit_pathways/rule_verification.py`: schema-v2
  machine-linked/human-reviewed/jurisdiction-approved claim evaluation for
  rule citations and full-rule records
- `src/permit_pathways/harness/`: verification runner and CLI
- `data/rules/`: the cited rule base; `data/golden/`: Golden cases with
  explicit positive and negative rule-dependency IDs
- `data/conformance/evaluations/heldout-v1/manifest.json`: validated
  `not_run` contract for a future independently frozen scanner evaluation;
  no cases, answer key, blind predictions, execution, or result is recorded
- `data/explanations/plain-language.json`: English/Spanish explanation drafts
- `data/validation/rule-verification.json`: the rule verification-level
  ledger; every current entry is `machine_linked`
- `data/validation/beta-operations-readiness.json`: portable 17-control,
  nine-approval no-storage beta plan; all execution and approval evidence is
  null/`not_run`
- `data/onboarding/local-source-intake-template.json`: generic `not_run`
  local-source collection template with no jurisdiction, source, owner,
  review, or approval evidence
- `data/availability/woodland-preapproved-adu-program.json`: official-page
  evidence and recheck boundary for the future-state Woodland simulation
- `data/workflows/registry.json`: one registered prototype workflow and the
  explicit browser-default selection; it does not record multiple active
  workflows
- `data/readiness/`: the Woodland workflow, synthetic packet, review-pending
  remedies, and generated evidence manifest
- `data/journeys/`: the reference-only Woodland journey definition and its
  generated fingerprinted envelope
- `data/source-status/current.json`: repository-adopted completed-run receipt
  used as the public source-state overlay
- `data/export/public-synthetic-evidence-v1.json`: exact artifact membership,
  raw digest pins, public-state assertions, exclusions, and known absences for
  the frozen 58-file schema-v1 compatibility handoff
- `data/export/public-synthetic-evidence-v2.json`: current 59-file profile that
  adds registry-aware closure and advances the existing bundle pin to format 6
- `data/jurisdictions/generated/coverage-index.json`: generated statewide
  coverage profiles that keep the statewide inventory, limited local records,
  dated HCD history, and local-onboarding boundary distinct
- `data/demo-data.js`: generated offline bundle for the static showcase
- `index.html`, `check.html`, `prepare.html`, `review.html`,
  `evidence.html`: task-focused static pages; `assets/`: shared browser
  application and visual system
- `corpus/hcd/`: HCD source documents recorded by rule citations
- `demo/app.py`: stdlib reference demo and safe static-file server
- `scripts/build_demo_bundle.py`: rebuild/check the static data bundle
- `src/permit_pathways/jurisdictions.py`: validates and builds the portable
  jurisdiction-coverage index used by the browser profile
- `docs/DESIGN.md`: architecture and demo plan
- `docs/DATA-FLOW.md`: current build-time and browser data boundaries
- `docs/DESIGN-SYSTEM.md`: California Web Standards alignment and local
  extensions
- `docs/PRODUCT-CONTEXT.md`: capability truth and opportunity priorities
- `docs/BETA-ROADMAP.md`: evidence-gated path from tested prototype to one
  active-jurisdiction limited beta
- `docs/BETA-OPERATIONS-RUNBOOK.md` and `docs/adr/0002-retain-no-storage-beta-boundary.md`:
  proposed operating boundary, roles, release/incident/records procedures,
  alternatives, and pending decisions
- `docs/EXPORT-RESTORE.md`: package contract, commands, integrity model,
  privacy boundary, and maintenance rules
- `docs/SHOWCASE-REMEDIATION-PLAN.md`: capability status, evidence, and known
  limitations
- `docs/SHOWCASE-PILOT-BRIEF.md`: bounded small-jurisdiction deployment
  hypothesis
- `AGENTS.md`: evidence, scope, privacy, and quality guardrails
- `LICENSE` and `THIRD_PARTY_NOTICES.md`: original-project license and
  attribution or separate terms for bundled source material

## Support

This is independent, unpaid work. If it has been useful to you, you can
<a href='https://ko-fi.com/T6T6GMYTU' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi6.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>
