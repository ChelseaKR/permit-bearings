# Current prototype data flow

Status: 2026-08-03. This describes the executable repository and public demo,
not a production deployment or a compliance assessment.

## Boundary summary

The public static site has no accounts, uploads, telemetry, applicant-data
store, external model call, parcel connection, or permitting-system
integration. The applicant routing form keeps submitted facts only in current
page memory. The route-to-packet link contains only a public journey ID and
version; it carries no project facts. The packet-presence page uses a
committed synthetic record and does not accept applicant input.

The Python reference server can receive a form submission to render one
response, but it does not persist that submission. A production deployment
would require a separate data inventory, purpose and authority analysis,
access controls, retention and deletion rules, public-records workflow,
security review, and jurisdiction approval.

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
    +--> automation never edits the public snapshot
    |
    v
Deliberate repository adoption as data/source-status/current.json
    |
    v
Strict loader re-binds source registry and re-derives
affected/unaffected rule and Golden-case IDs
    |
    v
Bundle format 3 embeds historical records + current overlay separately
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
workflow emits only `proposed` artifacts. New-law discovery, automatic
adoption/publication, packet-field assignment records, and staffed review
ownership remain outside this flow.

The source-state record is an overlay. It does not rewrite the historical rule,
Golden, journey, readiness, or evidence-manifest records. The browser derives
the Woodland route/checklist/parcel effects from those records' existing
source bindings.

## Bounded readiness path

```text
Official City checklist + public parcel-layer metadata retained
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
    |
    v
Browser validates the journey, linked route/readiness evidence,
fingerprints, current source-review windows, and exact changed-source bindings
    |
    +--> Active, unedited canonical sample + explicit Yes
    |        |
    |        +--> prepare.html?journey=<public-id>&version=<version>
    |                 |
    |                 +--> Exact current entry: render generated result
    |                 |        |
    |                 |        +--> Derive print-focused journey summary
    |                 |                 |
    |                 |                 +--> Browser Print / Save as PDF
    |                 |                      (no app-side export or storage)
    |                 +--> Direct, malformed, mismatched, or stale: hold
    |                      findings and print summary
    |
    +--> Edited/different sample, No, or I'm not sure: no packet link
```

### Source acquisition

The City of Woodland checklist is a public source retained at
`corpus/woodland/preapproved-adu-permit-checklist.pdf`. Its official URL,
retrieval date, and digest are recorded in `data/sources.json`.
The Yolo County public parcel feature-layer metadata is retained at
`corpus/yolo/public-parcels-layer.json` with the same URL/date/digest controls.
The latter describes available fields; it is not a downloaded parcel record.
Source retrieval and source-watcher execution are repository maintenance
operations, not browser requests made on behalf of an applicant.

### Canonical readiness inputs

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

`src/permit_pathways/readiness_cli.py` reads local paths and prints the
evidence manifest to standard output. It checks source currency against the
current UTC date unless a person explicitly requests a historical `--as-of`
replay. The CLI itself does not store the result. A person who redirects that
output creates a local file outside the CLI's storage behavior.

### Build and browser rendering

`scripts/build_demo_bundle.py` runs the Python evaluator against the canonical
synthetic sample. It writes the derived evidence record to
`data/readiness/generated/woodland-preapproved-adu-evidence.json` and embeds
the same readiness payload in `data/demo-data.js`. The build also resolves the
canonical journey definition, writes
`data/journeys/generated/woodland-preapproved-detached-adu.json`, and embeds
that same envelope in the bundle. It also strictly loads the repository-adopted
`data/source-status/current.json`, requires its publication receipt to be
`reviewed`, re-derives its dependency impacts, and embeds it as a separate
overlay. The bundle's generated-input manifest includes the snapshot digest.

`check.html` consumes the journey envelope only for the active, unedited
`sample=adu` fixture after the normal deterministic screening result exactly
matches the bound golden case and candidate route. `assets/demo.js` checks the
journey schema and identity; the linked golden intake, route, and readiness
records; the shared applicability provenance; every recorded fingerprint; and
the route and readiness source-review windows against the current date. It
also overlays the adopted changed-source IDs. A changed candidate-route source
blocks the handoff; a changed checklist or parcel-metadata source blocks the
packet; unrelated changes do not. An unverifiable fetch is not included in the
changed set and therefore does not create unsupported staleness. The
remaining editable applicability fact has no default. **Yes** exposes the
packet link; **No** withholds it as not applicable; and **I'm not sure**
withholds it and shows the exact staff question.

The handoff URL has exactly two fields: the public `journey` ID and its
`version`. It does not move project facts from `check.html` to `prepare.html`
or claim authorization. `prepare.html` validates those two fields and repeats
the journey and source-currency checks. A missing, duplicated, extra,
malformed, mismatched, or stale entry withholds the packet cover and findings.
A valid entry renders the Python-generated result; JavaScript does not
recalculate packet findings.

Only after that same exact entry and integrity path succeeds, the browser
derives a print-focused summary from the normalized journey and readiness
objects already in memory. It includes the candidate route, labeled synthetic
facts, the three reported-missing preparation actions, direct staff questions,
route/checklist/parcel-metadata evidence, boundary text, and the journey
ID/version. The action block preserves its AI-assisted, review-pending, and
not-human-reviewed status. It does not fetch new data or recalculate either the
route or packet result. The print button invokes `window.print()`; the browser, not the
application, controls printing or Save as PDF. Print media hides the remaining
site and detailed packet surfaces. Invalid or direct entry never reveals this
summary.

The browser does not send the synthetic facts to a server or model. It does
not use local storage, session storage, cookies, or an upload control. A user
may choose to follow the official checklist or parcel-metadata link. The
handoff is therefore replay of one public made-up record, not continuity for
a real applicant case. Choosing browser Print or Save as PDF can create a
user-controlled artifact outside the app; the app does not create, name,
upload, retain, or later retrieve it.

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
- the public browser.

AI-assisted copy cannot create or change a readiness finding. The evaluator
does not import the remedy sidecar. The browser recomputes its content
fingerprint, rejects invalid review metadata, and withholds action wording
when the source state is not current.

## What the generated record does not establish

The evidence manifest records that one versioned program evaluated one
synthetic inventory against one source-bound manifest. It does not establish
that:

- the checklist is a complete statement of Woodland requirements;
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
external models, parcel services, or permitting-system data would create a
different data flow and require deployment-specific documentation and review.
