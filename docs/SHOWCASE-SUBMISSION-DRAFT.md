# AI Permitting Innovation Showcase submission draft

Status: working draft, not submitted.

This draft is written for the official application preview dated July 2026.
Confirm the fields and limits in Authorium before pasting. Do not include
confidential, proprietary, or trade-secret material.

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

> Permit Bearings is a tested California permitting prototype
> combining deterministic pathway screening with source-linked, AI-assisted
> explanations. It helps applicants identify ADU, JADU, and SB 9 routes,
> inspect evidence, and recognize open questions without replacing staff
> judgment, legal review, permitting systems, or
> approval authority.

If applying as a team, add only verified team members and describe the actual
working relationship. Otherwise skip the team fields.

Qualifications evidence: `[VERIFIED EXPERIENCE, ROLE, AND RELEVANT DELIVERY OR
TECHNICAL QUALIFICATIONS]`

The program page says qualifications are required, although the application
preview has no separately labeled qualifications field. Confirm placement at
the Vendor Information Forum or in Authorium. Add only experience that can be
verified.

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

> An applicant with an ADU starts with a jurisdiction, project type,
> and applicant-supplied facts about the lot and existing dwelling. Permit
> Bearings applies deterministic California housing rules and returns candidate
> routes, standards, and process records. Every match shows source status and a
> citation. When copy is valid and evidence current, it also shows an
> explanation, excerpt, starting steps,
> and questions for staff.
>
> An unknown fact produces direct questions without a favorable assumption. If
> complete facts match no encoded route, the product abstains and routes to
> staff. If evidence is stale, unverified, or fails a fingerprint check, the
> matched rule and evidence remain
> visible, but action copy and document hints are withheld.
>
> The prototype covers statewide ADU, JADU, and SB 9 screening plus two bounded
> local records. It does not determine final eligibility, retrieve
> authoritative parcel facts, or evaluate packet completeness.
>
> For a homeowner or small builder, the value is a cited candidate route and
> focused open questions instead of reconstructing state law alone. This may
> reduce repetitive routing questions and work on a mismatched pathway. No
> effect on time or rework has been measured with applicants or jurisdiction
> staff.

### AI technical workflow

Limit: 150 words. Draft count: 137 words by whitespace.

> Before runtime, AI drafts English explanations and Spanish translations from
> a rule record and linked official citation. No applicant input is sent to a
> model. Runtime matching uses deterministic criteria.
>
> Each explanation is stored separately with stable rule ID, version,
> authorship status, source-check date, citation fingerprint, and full-rule
> fingerprint. Source-date or rule-content drift invalidates explanation. Stale
> or unverified evidence suppresses action copy.
>
> To promote a draft, the file-based review procedure would require a reviewer
> to check citation and excerpt against the underlying rule, then correct or
> reject the record. Review status changes only when reviewer, method, date,
> and reviewed version are recorded. This procedure has not been exercised
> with a named reviewer. English and Spanish remain labeled AI-assisted and
> review-pending, and Spanish remains a machine draft. AI is bounded to
> explanation; deterministic screening remains reproducible and testable.

### Maturity

Select: `Tested prototype`

Limit: 100 words. Draft count: 89 words by whitespace.

> Tested prototype. The deterministic matcher replays 29 golden
> fixtures covering positive, negative, boundary, ambiguous, and
> wrong-jurisdiction cases. Automated tests check rule and explanation linkage,
> duplicate or orphan records, fingerprint drift, stale-source behavior,
> browser bundle parity, clock conditions, and selected plain-language
> boundaries. Retained HCD and statutory materials include citations and source
> metadata. The public demo stores no applicant input. Assumed source changes
> mark dependent rules stale, suppress guidance, and leave unrelated controls
> available. No
> applicant, planner, counsel, translator, or jurisdiction has validated
> usability, legal fidelity, outcomes, or Spanish semantic parity.

## Section 4: Deployment in a California jurisdiction

Reference case: a small California jurisdiction with limited technical staff,
starting with one new detached ADU workflow.

### Time to first usable result

Decision needed before submission.

Proposed planning estimate: `8 to 12 weeks for one bounded ADU workflow`

This is an estimate, not a result from a prior deployment. Confirm that the
scope and estimate in
[SHOWCASE-PILOT-BRIEF.md](SHOWCASE-PILOT-BRIEF.md) are acceptable before using
it.

Estimate assumptions: one English-language ADU workflow, applicant-supplied
parcel facts, public and jurisdiction-provided sources available at kickoff,
synthetic test projects, file-based review, timely staff decisions, and no
production integration, accounts, uploads, or security authorization. The
delivery team and its capacity are not yet identified. Do not use the estimate
until that team confirms it.

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

> The prototype uses official state statutes, HCD guidance, selected municipal
> sources, structured JSON, a jurisdiction registry, transit datasets, and
> applicant facts. The public applicant flow has no live parcel, permitting,
> document management, identity, or model integration. The proposed first
> result uses applicant-supplied parcel facts and the jurisdiction's ordinance,
> forms, checklist, procedures, and calendar. A parcel, zoning, or GIS
> connection would be assessed separately and is excluded from the estimate.
> Portable rule and review files can be inspected without vendor-only tooling;
> ownership and export terms require agreement.

### Known exceptions

Limit: 100 words. Draft count: 88 words by whitespace.

> The prototype does not retrieve parcel facts, assess documents, determine
> packet completeness, validate cross-document consistency, or provide
> remedies. It
> encodes statewide ADU, JADU, and SB 9 rules, not SB 35, AB 2011, or
> comprehensive local codes. Monitoring covers selected URLs; it does not
> discover new laws or persist change state into applicant results. No
> jurisdiction, counsel, applicant, accessibility tester, or translator has
> reviewed outputs. Spanish explanations are machine drafts. Production
> privacy, security, retention, CPRA retrieval, integration, support, and cost
> remain deployment work. The demo stores no applicant input.

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

Recommended video outline, 90 seconds:

1. State the user and scope.
2. Open the hypothetical ADU sample.
3. Show the candidate route, staff questions, and evidence disclosure.
4. Change one material fact to “I'm not sure,” resubmit, and show direct staff
   questions instead of an assumed favorable answer.
5. End on current limitations and the one-workflow pilot proposal.

## Final checks before submission

- Replace every bracketed placeholder.
- Add only verifiable qualifications and confirm where Authorium asks for
  them.
- Decide whether the proposed 8 to 12 week planning estimate is defensible.
- Attend or review notes from the July 30 Vendor Information Forum.
- Verify live Authorium fields and word counters.
- Open every supporting link without authentication.
- Confirm screenshots show the sample disclosure and no personal information.
- Do not claim a pilot, production deployment, applicant validation, staff
  validation, legal review, translation review, measured time savings, or
  packet-level completeness.
- Save a draft in Authorium before final submission.
