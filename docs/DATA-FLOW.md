# Current prototype data flow

Status: 2026-07-30. This describes the executable repository and public demo,
not a production deployment or a compliance assessment.

## Boundary summary

The public static site has no accounts, uploads, telemetry, applicant-data
store, external model call, parcel connection, or permitting-system
integration. The applicant routing form keeps submitted facts only in current
page memory. The packet-presence page uses a committed synthetic record and
does not accept applicant input.

The Python reference server can receive a form submission to render one
response, but it does not persist that submission. A production deployment
would require a separate data inventory, purpose and authority analysis,
access controls, retention and deletion rules, public-records workflow,
security review, and jurisdiction approval.

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
    +--> Generated evidence manifest
             |
             v
Static build bundle
             |
             v
Browser validates and renders the generated result
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
the same readiness payload in `data/demo-data.js`.

`prepare.html` loads the static bundle. `assets/demo.js` validates identifiers,
dates, counts, source bindings, remedy coverage, and review metadata before
rendering the result. It also checks the recorded source-review window. It
does not recalculate packet findings in JavaScript.

The browser does not send the synthetic facts to a server or model. It does
not use local storage, session storage, cookies, or an upload control. A user
may choose to follow the official checklist or parcel-metadata link.

## AI boundary

The repository records that AI assisted the checklist-to-requirement mapping
and the plain-language action drafts before runtime. Those artifacts are
portable files, are bound to workflow and requirement fingerprints, and
remain review-pending. They have not been approved by a named human, planner,
counsel, applicant, Woodland staff member, or another jurisdiction.
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
does not import the remedy sidecar. The browser rejects a generated readiness
record with invalid review metadata and withholds action wording when the
source state is not current.

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
