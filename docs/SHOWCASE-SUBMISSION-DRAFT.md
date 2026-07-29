# AI Permitting Innovation Showcase submission draft

Status: working draft, not submitted.

This draft is written for the official application preview dated July 2026.
Confirm the fields and limits in Authorium before pasting. Do not include
confidential, proprietary, or trade-secret material.

Current gap status and evidence are tracked in
[SHOWCASE-REMEDIATION-PLAN.md](SHOWCASE-REMEDIATION-PLAN.md).

- Submission window closes August 11, 2026 at 5:00 p.m. Pacific.
- Primary scenario: Scenario 1, guiding applicants to a complete and
  well-routed application.
- Additional scenarios: none.
- Maturity: tested prototype.
- Official program page:
  <https://innovation.ca.gov/our-work/innovation-showcase/>
- Official application preview:
  <https://innovation.ca.gov/img/wordpress/2026/07/ai-permitting-vendor-application-form.pdf>

## Section 1: Who you are

Company name: `[LEGAL ENTITY OR INDIVIDUAL APPLICANT NAME]`

Website: `https://chelseakr.github.io/permit-pathways/`

Contact name: `[NAME]`

Contact email: `[EMAIL]`

Procurement vehicle: `[SLP / CMAS / OTHER / NONE YET]`

Applying as a team: `[YES / NO]`

### Company description

Limit: 50 words. Draft count: 43 words by whitespace.

> Permit Bearings is a tested permitting prototype combining
> deterministic pathway screening and one bounded packet-presence sample with
> source-linked, AI-assisted draft guidance. It helps applicants identify
> ADU, JADU, and SB 9 routes, inspect evidence, and recognize
> questions without replacing staff judgment or approval authority.

If applying as a team, add only verified team members and describe the actual
working relationship. Otherwise skip the team fields.

### Qualifications draft

**User confirmation required before submission.** This draft is based only on
the applicant's self-published [chelseakr.com](https://chelseakr.com/) site. It
has not been independently verified and does not establish that any current or
former employer is participating in, endorsing, or responsible for Permit
Bearings.

Draft text:

Chelsea Kelly-Reif's public site describes a decade building public-interest
technology in California state government and as a government delivery
partner. It describes engineering leadership for statewide workforce, health,
energy, utilities, licensing, and social-services systems, including secure
and accessible resident-facing services. The site also describes hands-on
architecture, Python and JavaScript development, cloud delivery, continuous
integration, applied AI, data interoperability, security, and accessibility
experience. Permit Bearings is identified separately in this repository as a
personal project.

Before using this paragraph, the user must confirm the current title, dates,
project descriptions, legal applicant name, relationship to the personal
project, and permission to reference employer or client work. The program page
says qualifications are required, although the application preview has no
separately labeled qualifications field. Confirm placement in Authorium.

## Section 2: Which challenges you address

Primary scenario: `Scenario 1: Guiding applicants to a complete and well-routed application`

Additional scenarios: none.

Scenario 3 is an assurance layer beneath the applicant experience, but the
current prototype does not yet provide the searchable, jurisdiction-specific
law resource described by the full Scenario 3 prompt. Do not select it as an
additional scenario for this submission.

## Section 3: Solution detail

### Solution description

Limit: 200 words. Draft count: 189 words by whitespace.

> An applicant starts with a jurisdiction, project type, and
> applicant-supplied facts. Permit Bearings applies deterministic California
> housing rules and returns candidate routes, standards, local information
> records, source status, citations, and questions for staff.
>
> An unknown fact produces direct questions without a favorable assumption. If
> complete facts match no encoded route, the product abstains and routes to
> staff. If evidence is stale, unverified, or fails a fingerprint check, the
> matched rule and available evidence remain visible, but action copy and
> document hints are withheld.
>
> A separate deterministic sample compares one made-up Woodland preapproved ADU
> inventory with 25 requirements mapped from one official City checklist. It
> labels items present, missing, needing staff review, not applicable, or not
> evaluated and emits a source-bound evidence manifest. "Present" means only
> that the synthetic inventory reports the item present. The prototype does not
> inspect files, verify parcel facts, determine legal sufficiency, certify
> completeness, or limit what staff may request.
>
> This bounded flow is a testable example, not a real applicant record, pilot,
> or external validation result. No effect on time, rework, submission quality,
> or staff effort has been measured with external applicants or jurisdiction
> staff.

### AI technical workflow

Limit: 150 words. Draft count: 145 words by whitespace.

> During development, AI assisted with mapping one official checklist into
> structured requirements and drafting versioned remedy actions. The mapping
> and remedies are review-pending. Mapping errors can affect deterministic
> findings, so no human, counsel, or jurisdiction approval is claimed.
> Mapping metadata records source fingerprints; provider, model, and run
> record were not recorded.
> Runtime calls no model. It reads facts and inventory states,
> applies conditions, and produces packet-presence findings.
>
> Remedy text is display-only and cannot change a finding. It is stored
> with version, AI-assisted authorship, pending review status,
> workflow fingerprint, and requirement fingerprints. Source or requirement
> drift blocks use.
>
> AI also drafted route explanations and Spanish translations before runtime.
> They remain versioned and review-pending, and Spanish remains a
> machine draft. No applicant input is sent to a model. A completed review
> would require a named reviewer, method, date, exact version, and recorded
> disposition before release or reliance.

### Maturity

Select: `Tested prototype`

Limit: 100 words. Draft count: 89 words by whitespace.

> Tested prototype. The deterministic matcher replays 29 golden
> fixtures covering positive, negative, boundary, ambiguous, and
> wrong-jurisdiction cases. Automated tests check rule and explanation linkage,
> duplicate or orphan records, fingerprint drift, stale-source behavior,
> browser bundle parity, clock conditions, and selected plain-language
> boundaries. The readiness CLI produces a reproducible source-bound manifest
> for one synthetic inventory and one City checklist. "Present" does not mean
> inspected or complete. No applicant, planner, counsel, translator, or
> jurisdiction has validated usability, mapping fidelity, legal fidelity,
> outcomes, or Spanish semantic parity in any independent study or review.

## Section 4: Deployment in a California jurisdiction

Reference case: a small California jurisdiction with limited technical staff,
starting with one new detached ADU workflow.

### Time to first usable result

#### Measured prototype automation

These measurements describe an already configured public prototype repository,
not deployment in a jurisdiction. On the three latest successful `main` runs
observed July 29, 2026:

| Measurement | Observed elapsed times | Evidence |
|---|---|---|
| CI | 13, 16, and 15 seconds | [30410892005](https://github.com/ChelseaKR/permit-pathways/actions/runs/30410892005), [30428315210](https://github.com/ChelseaKR/permit-pathways/actions/runs/30428315210), [30478495913](https://github.com/ChelseaKR/permit-pathways/actions/runs/30478495913) |
| GitHub Pages build and deployment | 39, 42, and 47 seconds | [30410891433](https://github.com/ChelseaKR/permit-pathways/actions/runs/30410891433), [30428314821](https://github.com/ChelseaKR/permit-pathways/actions/runs/30428314821), [30478494564](https://github.com/ChelseaKR/permit-pathways/actions/runs/30478494564) |

Elapsed time is calculated from GitHub's `startedAt` to `updatedAt` values.
These runs precede the current unmerged readiness implementation. They do not
measure jurisdiction configuration, source review, integration, production
authorization, support, or time to a usable permitting result.

#### Production planning estimate

Status: unvalidated estimate, decision required before submission.

Proposed estimate: `8 to 12 weeks for one bounded ADU workflow`

This is a planning hypothesis, not a prior deployment result or quote. The
[pilot brief](SHOWCASE-PILOT-BRIEF.md) assumes one English-language workflow,
applicant-supplied parcel facts, a complete source package at kickoff,
synthetic test projects, file-based review, timely staff decisions, and no
production integration, accounts, uploads, or security authorization. The
delivery team and capacity are not identified. Do not use this estimate until
that team validates it.

#### Cost

Status: unknown.

No production implementation, hosting, integration, support, or maintenance
cost has been estimated. The speed of the current static CI and Pages pipeline
is not production cost evidence.

### Work required from jurisdiction staff

Limit: 100 words. Draft count: 89 words by whitespace.

> For a pilot, staff would select one ADU workflow and
> provide ordinance, forms, checklist, procedures, closure calendar, and
> authoritative source list. A planning or
> building expert would review encoded criteria, explanations,
> uncertainty routing, and synthetic cases. Counsel and language
> reviewers would participate according to local policy. Information technology
> staff would assess read-only data options, access boundaries, export needs,
> and deployment controls. Ongoing work would include reviewing source alerts
> and approving or rejecting revisions. The prototype has no administrative
> workbench, so pilot authoring and review would be collaborative and
> file-based.

### Source data and integrations

Limit: 100 words. Draft count: 86 words by whitespace.

> The prototype uses HCD guidance, selected municipal sources, structured JSON,
> transit datasets, and applicant facts. One synthetic packet-presence sample
> uses a City checklist,
> an explicit made-up inventory, and a generated evidence manifest. The public
> applicant flow has no live parcel, permitting, document-management, identity,
> upload, or model integration. A parcel, zoning, GIS, or permitting connection
> would be assessed separately and is excluded from the estimate. Portable
> source, rule, workflow, inventory, remedy, and evidence files can be inspected
> without vendor-only tooling; operational ownership and export terms require
> agreement.

### Known exceptions

Limit: 100 words. Draft count: 88 words by whitespace.

> The readiness sample checks reported presence against one City checklist. It
> does not inspect files, verify parcel facts, assess document
> contents, determine legal sufficiency, validate cross-document consistency,
> certify completeness, or provide reviewed remedies. Its mapping and
> AI-assisted remedy draft await named review. The prototype does not
> encode comprehensive local codes, SB 35, or AB 2011. Monitoring covers
> URLs and does not discover new laws or persist production change
> state. No participant or jurisdiction has validated outputs.
> Privacy, security, records, integration, support, time,
> and cost all remain deployment work.

### Large jurisdiction experience

Leave blank unless verifiable experience can be added.

## Section 5: Supporting materials

The form permits up to two annotated screenshots and an optional public video
of no more than 120 seconds.

Recommended screenshot set:

1. Open `check.html?sample=adu`. Annotate the hypothetical Woodland input and
   the sample disclosure. Caption: "Made-up applicant facts are passed through
   the same deterministic screening path used by manual input."
2. Capture one resulting route with its plain-language consequence, source
   status, citation, and evidence disclosure visible. Caption: "The result
   separates review-pending explanation copy from the official source record."

If a readable packet-presence view is published and verified before
submission, consider replacing the second screenshot with that view. Its
caption must say that the inventory is synthetic, "present" is not file
inspection, and the result is not a completeness determination.

Recommended video outline, 90 seconds:

1. State the user and scope.
2. Open the hypothetical ADU sample.
3. Show the candidate route, staff questions, and evidence disclosure.
4. If the packet-presence view is ready, show one missing item, one staff
   question, and its source-bound evidence. State the presence-only boundary.
5. Change one material route fact to “I'm not sure,” resubmit, and show direct
   staff questions instead of an assumed favorable answer.
6. End on no external validation, unknown production cost, and the bounded
   pilot hypothesis.

## Final checks before submission

- Replace every bracketed placeholder.
- Confirm the qualifications draft, applicant authority, and where Authorium
  asks for qualifications.
- Decide whether a delivery team can support the proposed 8 to 12 week
  unvalidated planning estimate.
- Leave production cost unknown unless a supportable estimate is supplied.
- Attend or review notes from the July 30 Vendor Information Forum.
- Verify live Authorium fields and word counters.
- Open every supporting link without authentication.
- Confirm screenshots show the sample disclosure and no personal information.
- Do not claim a pilot, production deployment, applicant validation, staff
  validation, legal review, translation review, measured time savings, or
  packet-level completeness. Describe the readiness feature only as a
  deterministic presence check over one synthetic inventory and one checklist.
- Save a draft in Authorium before final submission.
