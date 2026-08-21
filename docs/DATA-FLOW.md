# Current prototype data flow

Status: 2026-08-21. This describes the executable repository and public demo,
not a production deployment or a compliance assessment.

## Boundary summary

The public static site has no accounts, uploads, telemetry, applicant-data
store, parcel connection, or permitting-system integration, and makes no
model call on its own. ADR 0004 directs a separate optional AI service; its
data flow is recorded in "Optional runtime AI service path" below. The applicant routing form keeps submitted facts only in current
page memory. The route-to-packet link contains only a public journey ID and
version; it carries no project facts. The packet-presence page uses a
committed synthetic record and does not accept applicant input.

The Python reference server can receive a form submission to render one
response, but it does not persist that submission. A production deployment
would require a separate data inventory, purpose and authority analysis,
access controls, retention and deletion rules, public-records workflow,
security review, and jurisdiction approval.

## Proposed limited-beta operating flow (prepared, not approved)

ADR 0002 proposes retaining the no-application-storage boundary for a first
limited beta. The proposal, runbook, and portable control ledger are
machine-testable planning artifacts; they do not represent a beta deployment,
host review, rehearsal, approval, or partner decision.

```text
Public static HTML/CSS/JS + committed public/synthetic data
    |
    v
Selected HTTPS host, DNS, and optional CDN
    |   deployment provider/request-metadata/subprocessor review: not_run
    v
Applicant browser
    |
    +--> exact structured facts held in current page memory
    |       purpose: deterministic candidate guidance, source status,
    |       unresolved questions, and temporary print-oriented outputs
    |       application network submission: none
    |       cookie/local/session storage: none
    |
    +--> static repository data requests; no applicant answers attached
    |
    +--> optional official-source links cross into the linked site's boundary
    |
    +--> optional Browser Print / Save as PDF
            user-controlled local artifact; no app retrieval/deletion path

Application service applicant record store: none
Application telemetry/runtime external model/writeback: none

Separate operational systems may create records:
repository/release + host/security + support + incident + partner review
    |
    +--> deployment-specific access/retention/deletion: not_run
    +--> CPRA search/export and legal-hold routing: not_run
    +--> privacy/security/records/partner approvals: not_run
```

The service-collected applicant field and purpose inventories are both empty.
The browser-memory inventory is exact and limited to the structured names
validated in `data/validation/beta-operations-readiness.json`: project type,
recognized jurisdiction name/slug, the encoded ADU/JADU/SB 9 screening facts,
and the bounded synthetic-journey applicability answer. The packet page
accepts no applicant field or document; it replays committed synthetic data.
Adding an address, APN, contact, permit number, upload, free text, identity,
persistence, telemetry, runtime network/model request, or writeback changes
this flow and requires a new ADR and approvals before implementation.

“No storage” means no application-managed applicant record and no
applicant-answer submission. It is not a claim that the network or host has no
logs. The selected static host, DNS/CDN, linked official sites, repository,
support system, incident system, and partner-controlled evaluation materials
may process request or operational metadata under separate terms. Their
actual fields, purposes, access, subprocessors, location, retention, deletion,
export, and offboarding boundary remain unknown until deployment review.

`src/permit_pathways/beta_operations.py` accepts only the fixed
`prepared_not_approved` planning state: 17 exact controls are prepared, while
all nine role approvals, future-beta deployment identifiers, host/subprocessor
details, records rehearsals, decisions, and execution receipts remain
null/`not_run`. It validates that pending contract; it does not inspect a host,
execute the runbook, approve a system, or establish CPRA, Information
Practices Act, SAM, or SIMM compliance. A later execution or approval record
requires a separately reviewed schema.

The role-based operational procedure in `docs/BETA-OPERATIONS-RUNBOOK.md`
keeps retention/deletion, CPRA routing, incident triage, support, release,
rollback, and escalation explicit. It also states that a records owner—not the
application—must search authorized repository, deployment, source/review,
support, and incident systems. The absence of an application applicant store
must not be converted into a legal conclusion that no responsive record
exists.

## Statewide jurisdiction-coverage path

```text
Portable California jurisdiction registry
+ bounded statewide/local rule records
+ dated public HCD Housing Accountability Unit history
    |
    v
Strict coverage-index builder in jurisdictions.py
    |
    v
data/jurisdictions/generated/coverage-index.json
    |
    v
Static bundle key: coverage_index
    |
    v
Recognized jurisdiction selection in check.html
    |
    +--> bounded statewide candidate-rule inventory
    +--> limited local-layer status or not encoded
    +--> dated linked HCD-history reference or no linked record in snapshot
    +--> local-onboarding checklist
```

The builder joins committed repository inputs; neither it nor the browser
scrapes a jurisdiction site, calls an HCD service, retrieves a parcel, or
stores an applicant selection. A profile's statewide inventory is the same
bounded ADU/JADU/SB 9 candidate-rule set already screenable for every registry
entry. Its local status says only what the repository encodes: `not encoded`
does not mean a jurisdiction has no requirements, and a limited record is not
a complete code, forms set, fee schedule, checklist, or project finding.

Coverage-index schema version 1 deliberately contains only the 17 statewide
rule IDs, each registry slug's `local_rule_ids` and `hcd_record_count`, and
the HCD dataset's source/date/count metadata. It does not duplicate,
classify, or interpret HCD rows; the linked public correspondence remains in
`data/jurisdictions/hcd-letters.json`. The build rejects a local rule scope
that has no registry entry, an HCD slug that has no registry entry, or a
declared HCD total that does not match the contained rows.

HCD correspondence in a profile is a date-stamped reference from the committed
public dataset. It may include inquiries, technical assistance, findings, or
other correspondence, but it cannot establish the current ordinance, a
compliance status, a permit outcome, or what applies to a project. Likewise,
the absence of a linked record in the snapshot does not prove no HCD activity,
compliance, or complete data coverage. The local-onboarding checklist identifies
the evidence a maintainer should assemble before a deeper layer can exist:
operative provisions/effective dates; current forms, checklist, fees, and
process pages; official URLs, source-check dates, and content fingerprints;
project/parcel scope, exceptions, and unresolved questions; and a named review
owner/re-verification cadence. A URL by itself cannot create a local rule.

## Source-state receipt path

```text
19 watched source records with retained digest/date
    |
    v
Scheduled or local watcher re-fetch
    |
    +--> unchanged: observed digest equals recorded digest
    +--> changed: fetched digest differs
    +--> unverifiable: fetch failed; no change inference
    |
    v
Proposed JSON receipt + exact run URL/commit
    |
    +--> scheduled workflow retains artifact for 30 days
    +--> receipt with changed source IDs derives exact worklist + blank
    |    decision template and retains the three-file package for 30 days
    +--> optional release-receipt preparation binds that exact source-state,
    |    worklist, and decision-ledger fingerprint; every stage remains not_run
    +--> stale-only or Golden-regression-only run opens an issue without a
    |    misleading source-change package
    +--> automation never edits the public snapshot
    |
    v
Deliberate repository adoption as data/source-status/current.json
    |
    v
Strict loader re-binds source registry and re-derives
affected/unaffected rule and Golden-case IDs; Golden fixtures use explicit
rule dependencies for positive, negative, and ambiguous cases
    |
    v
Generated static bundle: historical records, current overlay, rule-review
coverage, program availability, and the separate coverage index
    |
    +--> changed dependency: stale exact rule/output or block bound handoff
    +--> unverifiable dependency: visible warning, no automatic staleness
    +--> unrelated dependency: explicit unaffected control remains available
```

The receipt status `reviewed` means a repository maintainer deliberately
selected a completed-run receipt for publication. It does not record a named
human reviewer or imply legal, jurisdiction, counsel, or substantive content
approval. `src/permit_pathways/source_state.py` requires one observation per
watched source, binds the current `data/sources.json` digest, checks the exact
run receipt fields, and re-derives direct rule/Golden impact. The scheduled
workflow emits only `proposed` artifacts. When that workflow reports review
needed, `src/permit_pathways/review_queue.py` also derives a portable worklist
and blank decision template. The worklist reaches exact changed source, rule,
Golden, readiness requirement, source-backed field, linked remedy, packet, and
configured journey nodes from explicit IDs and fingerprints; an unverifiable
source creates none. New-law discovery, automatic adoption/publication,
authorized owner selection, filled dispositions, and approval remain outside
the automated flow. `src/permit_pathways/source_release.py` adds strict,
read-only evidence contracts for those later boundaries: a completed approval
requires every exact work item to have a resolved evidence-bound disposition;
publication then binds that exact approval and a separately validated
`reviewed` publication source-state snapshot; rollback binds that exact
publication and a separately validated restored snapshot. The validator
derives whether the target hold remains from those supplied source-state
records. It does not edit `current.json`, adopt state, run Git, deploy, or
restore anything. It also does not authenticate Git objects, reviewer
authority, a live deployment, or opaque external receipt IDs. The committed
receipt templates keep every evidence field null and remain `not_run`, so no
rehearsal or human action is recorded.

The source-state record is an overlay. It does not rewrite the historical rule,
Golden, journey, readiness, or evidence-manifest records. The browser derives
the Woodland route/checklist/parcel effects from those records' existing
source bindings.

## Rule-verification claim path

```text
Rule record + citation + explicit source dependencies
    |
    v
Schema-v2 rule-verification entry
    |
    +--> machine_linked: no promotion claim
    |
    +--> promoted claim requires named review metadata,
         exact citation fingerprint, and exact full-rule fingerprint
             |
             v
Effective-status evaluation
    |
    +--> fingerprint drift: demote to machine_linked
    +--> changed source dependency: demote to machine_linked
    +--> source age or review age: demote to machine_linked
    +--> all bindings current: retain recorded effective level
             |
             v
Harness summary + bundle-format-6 evidence-page disclosure
```

`data/validation/rule-verification.json` cannot change deterministic rule
matching. It describes only the strength of the review claim in force.
`src/permit_pathways/rule_verification.py` binds any promotion to both the
normalized citation and full normalized rule record, then applies source-change,
source-age, and review-age demotion. The harness phrase
`automated source/regression checks: pass` reports bounded automation only.
The public evidence page exposes the current effective counts: all 19 rules
are `machine_linked`, with zero named human reviews and zero jurisdiction
approvals.

## Bounded readiness path

```text
Official City checklist (source checked 2026-07-29)
+ public parcel-layer metadata retained
    |
    v
Source registry entry with URL, check date, and digest
    |
    +--> 25-item workflow mapping, AI-assisted and review-pending
    |
    +--> Plain-language action sidecar, AI-assisted and review-pending
    |
    +--> Made-up project facts and explicit packet inventory
          |
          +--> Two fabricated parcel values bound to exact metadata fields
             |
             v
Deterministic Python evaluator
    |
    +--> Per-item findings and staff questions
    |
    +--> Source, workflow, requirement, and packet fingerprints
    |
    +--> Generated evidence manifest -------------------------+
                                                               |
Golden Woodland routing fixture + candidate rule current on recorded date --+
                                                               |
                                                               v
Versioned journey resolver
    |
    +--> Exact scope, applicability, and reference checks
    |
    +--> Route, fact-envelope, workflow, packet, and journey fingerprints
    |
    +--> Generated synthetic journey envelope
             |
             v
Static build bundle
    |
    +--> Includes strict repository-adopted source-state overlay
    +--> Includes strict rule-verification ledger
    +--> Includes strict, date-bound program-availability record <---------+
    |                                                                    |
    |     Official Woodland program page checked 2026-08-09              |
    |         |                                                          |
    |         +--> “Preapproved ADU List: Coming soon!”                  |
    |                     |                                              |
    |                     +--> plans_not_listed / future-state boundary --+
    |
    v
Browser validates the journey, linked route/readiness evidence,
fingerprints, current source-review windows, exact changed-source bindings,
and program availability
    |
    +--> Missing, malformed, or expired availability record: hold
    |
    +--> Current availability record + active, unedited canonical sample
         + explicit Yes
    |        |
    |        +--> prepare.html?journey=<public-id>&version=<version>
    |                 |
    |                 +--> Exact valid simulation entry: render generated result
    |                 |        |
    |                 |        +--> Derive print-focused journey summary
    |                 |                 |
    |                 |                 +--> Browser Print / Save as PDF
    |                 |                      (no app-side export or storage)
    |                 +--> Direct, malformed, mismatched, stale, or
    |                      availability-blocked: hold
    |                      findings and print summary
    |
    +--> Edited/different sample, No, or I'm not sure: no packet link
```

This path exposes a **source-bound future-state simulation**, not a currently
usable City preapproved plan or applicant-ready workflow. A current
availability record authorizes only display of that bounded simulation; it
cannot create a screening match, make the readiness workflow applicable, or
establish that a plan exists.

### Source acquisition

The City of Woodland checklist is a public source retained at
`corpus/woodland/preapproved-adu-permit-checklist.pdf`. Its official URL,
source-check date of 2026-07-29, and digest are recorded in
`data/sources.json`; the document is not described as inherently dated.
The Yolo County public parcel feature-layer metadata is retained at
`corpus/yolo/public-parcels-layer.json` with the same URL/date/digest controls.
The latter describes available fields; it is not a downloaded parcel record.
Source retrieval and source-watcher execution are repository maintenance
operations, not browser requests made on behalf of an applicant.

Program availability is separate from the checklist. The official
[Woodland Preapproved ADU Plan Program page](https://www.cityofwoodland.gov/1616/Preapproved-ADU-Plan-Program)
was checked 2026-08-09 and says **“Preapproved ADU List: Coming soon!”** That
manual, date-bound observation is recorded in
`data/availability/woodland-preapproved-adu-program.json` with its excerpt
fingerprint and recheck deadline. It is not inferred from the checklist and is
not represented as a watched-source proof that a plan is available.

### Canonical readiness inputs

- `data/workflows/registry.json` declares the repository-relative workflow,
  packet, remedy, journey, availability-policy, and generated-output paths.
  Every canonical input is raw-byte pinned. The strict Python loader rejects
  duplicate JSON keys, non-finite or oversized records, symlinks/hard links,
  cross-platform-unsafe names, duplicate or orphan IDs/files, shared paths,
  traversal, wrong-directory paths, fingerprint drift, and IDs that disagree
  with their referenced records. It currently contains one prototype entry
  and selects that same Woodland entry as the browser default; a synthetic
  two-entry test does not represent multiple active workflows.
- `data/availability/woodland-preapproved-adu-program.json` contains the
  official program-page binding, `plans_not_listed` status, future-state
  simulation boundary, and manual recheck deadline. Its strict schema is
  isolated from rule matching and readiness evaluation.
- `data/readiness/workflows/woodland-preapproved-detached-adu.json` contains
  the bounded workflow, nine tri-state facts, 25 requirements, source
  locators, excerpts, conditions, and bindings to the recorded checklist and
  parcel-layer metadata. Two fact definitions name exact parcel-layer fields.
- `data/readiness/samples/woodland-preapproved-adu.json` contains one labeled
  synthetic packet. Seven facts are marked
  `synthetic_applicant_assertion`; two concrete fabricated values use
  `synthetic_public_record_fixture` and carry the exact source ID, field, and
  recorded date. Every requirement has an explicit inventory status.
- `data/readiness/remedies/woodland-preapproved-detached-adu.json` contains
  versioned AI-assisted action drafts. The current status is
  `prototype_review_pending`, with no reviewer or completed-review claim.

The sample contains no real applicant, address, assessor parcel number,
permit number, contact information, plan, or application file.

### Canonical journey binding

`data/journeys/woodland-preapproved-detached-adu.json` is a reference-only,
versioned definition for one synthetic journey. It names the existing golden
screening case, one candidate-route rule, the readiness workflow and packet,
and designates one applicability fact as applicant-editable. It does not
duplicate the intake, rule, workflow, packet, or evaluator output.

`src/permit_pathways/journey.py` resolves those references at build time. It
requires the candidate route to match the complete golden case and to be
inside its source-review window on the sample's recorded evaluation date,
requires the screening and readiness scopes to agree, and requires the
canonical readiness applicability status to be `applies`. It emits the
resolved route evidence with that as-of date and review deadline, the shared
synthetic fact envelope with per-fact provenance, applicability facts, the
full readiness evidence manifest, and fingerprints for the route, screening
case, fact envelope, workflow, packet, and complete journey. A mismatch stops
generation. Browser code must still compare the recorded review deadlines
with the current date before presenting an affirmative handoff. It does so at
runtime together with the route, readiness, fact-envelope, and journey
fingerprint checks described below.

The journey resolver does not use program availability to manufacture a route
or readiness result. `src/permit_pathways/program_availability.py` validates
that independent record at build time, and browser entry validation enforces
its recheck date. Missing, malformed, or expired program evidence blocks the
future-state display even when the synthetic journey itself remains internally
consistent.

### Deterministic evaluation and CLI

`src/permit_pathways/readiness.py` loads and strictly validates the workflow,
packet, source binding, and remedy metadata. The evaluator compares explicit
facts and inventory statuses. Source-shaped parcel fixtures must match the
workflow's source ID, field name, and recorded date and cannot be used in a
packet labeled non-synthetic. The evaluator does not import the remedy
sidecar, call a model, inspect files, retrieve a parcel, or infer missing
facts.

Unknown conditions remain staff questions. A changed or stale source prevents
the evaluator from publishing a favorable packet summary. The result uses
`no_known_gaps_in_bounded_manifest` when every applicable item is reported
present; it never calls the packet complete.

`src/permit_pathways/readiness_cli.py` selects a registry entry by stable
workflow ID and prints the evidence manifest to standard output. Its legacy
path options are exact assertions against that entry, not an unregistered path
bypass. It checks source currency against the current UTC date unless a person
explicitly requests a historical `--as-of` replay. The CLI itself does not
store the result. A person who redirects that output creates a local file
outside the CLI's storage behavior. `review_queue_cli.py` builds contexts for
every registered workflow by default and can narrow to one registered ID; it
cannot infer or activate an unregistered workflow. `source_release_cli.py`
uses the same context loader but always binds every registered workflow; it
cannot create a repository-wide release receipt from a single selected entry.

### Build and browser rendering

`src/permit_pathways/jurisdictions.py` validates the registry shape, scoped
rules, and HCD-history input while building
`data/jurisdictions/generated/coverage-index.json`. The result is a portable
read-only index, not a source of deterministic matching logic. The static
builder embeds it under `coverage_index`; `check.html` only renders a profile
when the currently selected jurisdiction resolves to that registry index.
Changing or clearing the selection hides the profile. No profile data is
included in the route-to-packet URL.

`scripts/build_demo_bundle.py` loads and validates every registry entry, then
runs the Python evaluator against each configured canonical synthetic sample.
It writes each derived evidence record to that entry's registered output path;
for the current sole entry this is
`data/readiness/generated/woodland-preapproved-adu-evidence.json` and embeds
the same readiness payload in `data/demo-data.js`. The build also resolves each
registered journey definition; for the current entry it writes
`data/journeys/generated/woodland-preapproved-detached-adu.json`, and embeds
that same envelope in the bundle. Under the bundle-format-6 browser contract,
only the explicit `browser_default_workflow_id` is aliased to the
singular readiness object, program-availability object, and one-element
journey array. Registration alone does not expose another browser workflow.
The build also strictly loads the repository-adopted
`data/source-status/current.json`, requires its publication receipt to be
`reviewed`, re-derives its dependency impacts, and embeds it as a separate
overlay. The build strictly loads schema-v2 rule-verification data and the
date-bound Woodland program-availability record as separate inputs. Bundle
format 6 exposes those claims, the strict workflow registry, its exact raw
text, and the separate jurisdiction-coverage index. The generated-input
manifest binds the raw registry and every registered canonical input.

`assets/demo.js` first hashes the embedded raw registry against the bundle
receipt, confirms its parsed form matches the embedded registry object, then
validates exact shape, stable IDs, unique portable paths, availability policy,
and every registered input fingerprint. The browser cannot enumerate the
repository, so orphan-file detection belongs to the Python loader/build.
It derives the availability and generated-evidence paths from the one browser
default and verifies that the readiness, packet, journey, availability, and
jurisdiction IDs agree. Invalid registry data fails closed; an invalid
workflow-specific artifact continues to withhold only its deeper surface when
the base screening data remains valid.

`check.html` consumes the journey envelope only for the active, unedited
`sample=adu` fixture after the normal deterministic screening result exactly
matches the bound golden case and candidate route. `assets/demo.js` checks the
journey schema and identity; the linked golden intake, route, and readiness
records; the shared applicability provenance; every recorded fingerprint; and
the route and readiness source-review windows against the current date. It
also overlays the adopted changed-source IDs and validates the separate
program-availability schema and recheck deadline. A changed candidate-route
source blocks the handoff; a changed checklist or parcel-metadata source
blocks the packet; unrelated changes do not. A missing, malformed, or expired
availability record independently blocks the future-state handoff. An
unverifiable fetch is not included in the changed set and therefore does not
create unsupported staleness. The remaining editable applicability fact has
no default. **Yes** exposes the packet simulation link only after these
checks; **No** withholds it as not applicable; and **I'm not sure** withholds
it and shows the exact staff question. **Yes** does not establish that a City
plan is available.

The handoff URL has exactly two fields: the public `journey` ID and its
`version`. It does not move project facts from `check.html` to `prepare.html`
or claim authorization. `prepare.html` validates those two fields and repeats
the journey, source-currency, and availability checks. A missing, duplicated,
extra, malformed, mismatched, stale, or expired-availability entry withholds
the packet cover and findings. A valid simulation entry renders the
Python-generated result; JavaScript does not recalculate packet findings.

Only after that same exact entry, integrity, source-currency, and availability
path succeeds, the browser
derives a print-focused summary from the normalized journey and readiness
objects already in memory. It includes the candidate route, labeled synthetic
facts, the three reported-missing preparation actions, direct staff questions,
route/checklist/parcel-metadata evidence, boundary text, and the journey
ID/version. The action block preserves its AI-assisted, review-pending, and
not-human-reviewed status. It does not fetch new data or recalculate either the
route or packet result. The print button invokes `window.print()`; the browser, not the
application, controls printing or Save as PDF. Print media hides the remaining
site and detailed packet surfaces. Invalid, direct, or availability-blocked
entry never reveals this summary.

The browser does not send the synthetic facts to a server or model. It does
not use local storage, session storage, cookies, or an upload control. A user
may choose to follow the official checklist or parcel-metadata link. The
handoff is therefore replay of one public made-up future-state record, not
continuity for a real applicant case or a currently usable City plan. Choosing
browser Print or Save as PDF can create a
user-controlled artifact outside the app; the app does not create, name,
upload, retain, or later retrieve it.

## Public/synthetic evidence export path

The evidence exporter is an offline repository-maintenance command, not a
browser or applicant flow. Its versioned path is:

```text
Selected profile + pending/not_run state assertions
    |
    +--> v1: frozen 58-file compatibility identity
    +--> v2: 59 files; registry-aware closure and format-6 bundle pin
    |
    +--> verify every selected byte against Git HEAD and its profile digest
    +--> recheck normalized official-source digests separately from raw bytes
    |
    v
Canonical manifest: commit/freeze, roles, byte counts, raw hashes, tree hash,
claim boundary, exclusions, known absences, and sources without retained copies
    |
    v
Single deterministic ZIP_STORED representation outside the repository
    |
    +--> verify exact member set, paths, metadata, limits, hashes, and bytes
    +--> reject prefixes, trailers, compression, encryption, and tampering
    |
    v
Private sibling staging directory -> canonical loader replay -> exclusive
destination publication only after every check passes
```

The selected evidence includes public source copies and portable prototype
records; it does not include browser answers, applicant files, accounts,
uploads, identity mappings, credentials, private receipts, portal/submission
material, or unlisted working-tree files. Mutable validation ledgers may be
included only while their profile-pinned bytes and public-state assertions
remain pending, prepared, or `not_run`.

Restore is inert. It does not change the adopted source snapshot, clear a
source-review hold, promote a verification level, update the originating
repository, or publish guidance. The archive and tree hashes are integrity and
reproducibility records, not signatures, copyright ownership, partner
acceptance, a backup, or a CPRA/sensitive-data export. The exact operational
contract is in [`EXPORT-RESTORE.md`](EXPORT-RESTORE.md).

The later held-out evaluation contract, the source-change release-receipt
templates and tooling, and the beta-operations ADR, runbook, ledger, validator,
and tests are outside both the pinned 58-file export
profile v1 and the registry-aware 59-file profile v2. Their presence in the
repository does not make either fixed package incomplete. A reviewed future
profile version must classify and add them before an evidence handoff can
claim to include them.

## AI boundary

The repository records that AI assisted the checklist-to-requirement mapping
and the plain-language action drafts before runtime. Those artifacts are
portable files, are bound to workflow and requirement fingerprints, and
the generated remedy record carries a recomputed content fingerprint. They
remain review-pending. The fingerprint detects copy drift; it does not record
review or approval by a named human, planner, counsel, applicant, Woodland
staff member, or another jurisdiction.
The mapping record includes exact input-source fingerprints and explicitly
states that provider, model, and a reproducible run record are unknown or not
retained.

No model runs in:

- the deterministic readiness evaluator;
- the readiness CLI;
- the static bundle build;
- the applicant routing matcher; or
- the public browser when the optional AI service is absent or not used.

When the optional AI service directed by ADR 0004 is running and the
applicant uses it, a model runs outside the browser, in that service's
provider call. That path is described next; it still never runs a model inside
the matcher, the evaluator, or the build.

## Optional runtime AI service path (ADR 0004; planned, not yet in this repository)

`AGENTS.md` requires this inventory before an external model call is added.
It describes the service as designed; when the implementation lands, the
capability matrix will say what of it exists.

```text
Applicant browser (check.html)
    |
    |  only when the applicant opens the AI intake control or presses the
    |  "explain" control, and only if the service answered a health probe;
    |  otherwise the page is the static experience above and makes no request
    v
Permit Bearings AI service (permit_pathways.ai; local by default,
host to be decided)
    |   request body held in process memory for one request
    |   applicant content written to disk or logs: none
    |   applicant record store: none
    |   rate limiting / abuse controls: deployment-specific, not_run
    v
Model provider (Anthropic API, or Amazon Bedrock via the same SDK)
    |   subprocessor; retention per the provider's terms for the deployment's
    |   account — to be recorded before any hosted deployment: not_run
    v
Service: deterministic checks on the model output
    - extracted facts: allowed-value check; supporting quote must occur in
      the applicant's text, else the field becomes `unknown`
    - explanation: every cited quote must occur in the extracted corpus text
      for the named source; unverifiable claims withheld and counted
    - staff questions: labeled drafts
    v
Browser: drafted facts shown in the editable form for confirmation; labeled
AI-generated explanation with its verified citations; withheld-claim count
```

Collected fields and purpose:

| Field | Sent to | Purpose | Retained by the service |
|---|---|---|---|
| Free-text project description (EN/ES) | service → provider | draft the structured facts the applicant then confirms | no |
| Confirmed structured facts (the existing 19 names) and jurisdiction slug | service → matcher (local) and → provider | re-run the deterministic matcher; ground the explanation and staff questions | no |
| Interface language | service → provider | choose the output language | no |
| Matched rule IDs computed by the browser | service | parity check against the Python matcher; a mismatch refuses the request | no |

Not collected: name, address, APN, contact details, files, account, or
browser identifiers. The free-text field is the one place an applicant could
volunteer personal information; the interface tells them not to and the
service does not retain it, but a provider receives whatever was typed.

Data flow and subprocessors: browser → service → one model provider. The
provider, region, account, and retention terms are deployment facts and are
`not_run` until a deployment records them.

Access controls and security boundary: the service binds to localhost by
default and allows only configured origins; the provider credential is read
from the environment and never written. A hosted deployment needs transport
security, origin policy, request-size limits, rate limiting, abuse handling,
and a cost ceiling, all of which are pending decisions.

Retention and deletion: the service retains nothing, so there is nothing to
delete on the application side. Provider-side retention is governed by the
provider's terms and must be documented per deployment.

Jurisdiction ownership and export: no applicant record exists to own or
export. Prompts, the evaluation set, and the corpus index are repository
files.

CPRA and records: a hosted service creates request metadata at the host and
the provider. Whether any of it is a public record in a given deployment is a
deployment-specific determination; nothing here asserts one.

Deployment-specific review needs: host and subprocessor inventory, privacy
review of the free-text field, threat model, cost envelope, operations
package, and the approvals ADR 0002 lists — none has been started.

AI-assisted copy cannot create or change a readiness finding. The evaluator
does not import the remedy sidecar. The browser recomputes its content
fingerprint, rejects invalid review metadata, and withholds action wording
when the source state is not current.

## What the generated record does not establish

The evidence manifest records that one versioned program evaluated one
synthetic inventory against one source-bound manifest. It does not establish
that:

- the checklist is a complete statement of Woodland requirements;
- a Woodland preapproved plan is currently listed or usable;
- the simulated workflow is applicant-ready or applies to a real project;
- any reported-present file contains the required information;
- the fabricated parcel values describe any real parcel or that parcel or
  zoning facts are correct;
- documents are internally consistent or legally sufficient;
- an application is complete;
- staff may not request other material;
- the project is eligible or compliant;
- a permit will be approved; or
- applicants, planners, counsel, or a jurisdiction have validated the
  workflow.

Any future use of real applicant facts, document files, accounts, telemetry,
parcel services, or permitting-system data would create a different data flow
and require deployment-specific documentation and review. The optional AI
service path above is the one such flow this repository has designed; its
hosted deployment is still subject to that review.
