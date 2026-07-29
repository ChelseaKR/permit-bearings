# Showcase remediation plan

Status: working plan for the Intent to Showcase submission. Updated
2026-07-29.

This plan tracks six gaps between the current prototype and a defensible
submission. It does not claim a pilot, external validation, legal review,
jurisdiction approval, production deployment, or measured permitting outcome.

## Status labels

- **Implemented:** executable code or a concrete artifact exists in the current
  repository working tree. This label does not mean merged, deployed, reviewed,
  or validated by an external person.
- **Next:** work to complete or verify before the Intent to Showcase
  submission.
- **Planned:** work proposed for a bounded pilot after submission.
- **Unknown:** an unresolved fact that must not be estimated or filled in
  without evidence.

## 1. Scenario 1 depth: a packet-presence proof

**Implemented**

- One deterministic workflow maps 25 requirements from the official City of
  Woodland Preapproved ADU Permit Application Checklist. See the
  [workflow manifest](../data/readiness/workflows/woodland-preapproved-detached-adu.json)
  and the [official checklist](https://www.cityofwoodland.gov/DocumentCenter/View/12372).
- One explicitly synthetic inventory exercises present, missing, unknown, and
  conditional states. See the
  [synthetic packet](../data/readiness/samples/woodland-preapproved-adu.json).
- The [packet-presence evaluator](../src/permit_pathways/readiness.py) applies
  fixed conditions, preserves unknowns as staff questions, validates the
  checklist source binding, and fails closed when the source is changed or
  stale.
- Runtime and CLI source checks use the current UTC date by default. Historical
  replay requires an explicit date, and the generated evidence manifest names
  both the date of its source-status finding and the next source-review
  deadline.
- The current generated sample reports 14 items present, 3 missing, 5 needing
  staff review, and 3 not applicable. Those are deterministic results for one
  made-up inventory, not observations from a real application. See the
  [generated evidence manifest](../data/readiness/generated/woodland-preapproved-adu-evidence.json).
- A readable static [packet sample page](../prepare.html) presents the generated
  findings, source status, evidence links, and AI boundary without recalculating
  the result in a model.
- [Readiness regression tests](../tests/test_readiness.py) cover expected
  findings, all-present, conditional, unknown, wrong-workflow, stale-source,
  malformed-data, source-binding, remedy-review, determinism, generated
  evidence, and CLI behavior.
- Local browser inspection covered the rendered landmarks, generated findings,
  source links, console output, computed contrast, and horizontal reflow at
  1280, 390, and 320 CSS pixels. This is not a manual keyboard or
  assistive-technology test.
- The result says only whether the inventory reports an item present. It does
  not inspect a file, verify parcel facts, determine legal sufficiency, certify
  completeness, or constrain what staff may request.

**Next**

- Repeat the repository and browser checks against the exact reviewed commit.
- Deploy the packet sample page and verify its public URL, source links, visible
  boundary, and responsive layout before creating a screenshot or video claim.
- Complete a manual keyboard walkthrough and a named screen-reader walkthrough
  before making accessibility-conformance claims beyond the documented static
  and automated checks.

**Planned**

- Replace the prototype mapping with one jurisdiction-reviewed requirement set
  for one agreed ADU workflow.
- Test synthetic or properly redacted packets against a staff-authored answer
  key while keeping presence separate from consistency and compliance.

**Unknown**

- Whether Woodland staff consider the mapped requirements complete or current
  for any real project.
- Whether a jurisdiction will sponsor the proposed workflow or provide
  reviewable packet examples.

## 2. Bounded AI contribution and review controls

**Implemented**

- AI assisted the initial checklist-to-requirement mapping and drafted remedy
  actions during development. Runtime evaluation does not call a model.
- The [workflow manifest](../data/readiness/workflows/woodland-preapproved-detached-adu.json)
  records mapping version, date, AI-assisted authorship, exact input-source
  fingerprints, and `prototype_review_pending` status. It also states that
  provider, model, and a reproducible run record were not recorded.
- The [remedy sidecar](../data/readiness/remedies/woodland-preapproved-detached-adu.json)
  is versioned, bound to workflow and requirement fingerprints, labeled
  `ai_assisted`, and marked `prototype_review_pending`.
- Remedy text is display-only. The deterministic evaluator does not import
  remedy text when it decides a presence status.
- Existing route explanations and Spanish translations are also versioned
  AI-assisted drafts with independent review status. See
  [the explanation sidecar](../data/explanations/plain-language.json).

**Next**

- Have a named subject-matter reviewer compare every mapped requirement,
  condition, locator, excerpt, and remedy against the official checklist.
- Record corrections and the exact reviewed versions. Do not promote the
  status through prose alone.

**Planned**

- Add a human approval workflow for proposed requirement, remedy, and source
  changes.
- Evaluate bounded AI extraction and drafting against held-out source passages
  with evidence-level error reporting.

**Unknown**

- Who is authorized to review the mapping and remedy language for a pilot.
- Whether any future deployment would permit runtime model calls. The current
  prototype makes none.

## 3. External validation and outcome evidence

**Implemented**

- A concrete [formative validation plan](SHOWCASE-VALIDATION-PLAN.md) defines
  separate staff and applicant or designer sessions, synthetic-only materials,
  task-success criteria, safety boundaries, and a no-PII protocol.

**Next**

- Recruit participants who meet the stated criteria, lock the tested commit,
  conduct the sessions, and report completions, failures, misunderstandings,
  and contrary evidence.
- Keep usability observations separate from legal fidelity, accessibility,
  translation, and permitting outcomes.

**Planned**

- During a pilot, compare the bounded workflow with staff-authored completeness
  notices or answer keys and agree on outcome measures before testing.

**Unknown**

- Participant availability, findings, task-success rates, and whether staff or
  applicants find the prototype useful.
- Any effect on submission quality, review time, correction cycles, staff
  effort, or permitting duration.

No external participant has validated the prototype as of 2026-07-29.

## 4. Applicant qualifications and delivery authority

**Implemented**

- The applicant's self-published site describes a decade of public-interest
  technology work, California state-system experience, public-sector delivery,
  applied AI, accessibility, security, cloud, and engineering leadership. See
  [chelseakr.com](https://chelseakr.com/).
- [PROVENANCE.md](../PROVENANCE.md) identifies this repository as a personal
  project created on personal equipment and accounts.

**Next**

- The user must confirm the current title, dates, project descriptions, scale
  statements, and permission to use employer or client references.
- Confirm the legal applicant name, relationship between the applicant and this
  personal project, procurement vehicle, delivery team, and whether the
  application is individual or organizational.

**Planned**

- Add only qualifications the user confirms and can support if the program
  requests evidence.

**Unknown**

- Legal applicant entity, procurement path, proposed team, delivery capacity,
  and authority to bind any current or former employer.

The qualifications draft in
[SHOWCASE-SUBMISSION-DRAFT.md](SHOWCASE-SUBMISSION-DRAFT.md) is based only on
the self-published site and is not independently verified.

## 5. Deployment time, operations, and cost

**Implemented**

- The three latest successful `main` CI runs observed on 2026-07-29 completed
  in 13, 16, and 15 seconds:
  [run 30410892005](https://github.com/ChelseaKR/permit-pathways/actions/runs/30410892005),
  [run 30428315210](https://github.com/ChelseaKR/permit-pathways/actions/runs/30428315210),
  and
  [run 30478495913](https://github.com/ChelseaKR/permit-pathways/actions/runs/30478495913).
- The matching GitHub Pages build and deployment runs completed in 39, 42, and
  47 seconds:
  [run 30410891433](https://github.com/ChelseaKR/permit-pathways/actions/runs/30410891433),
  [run 30428314821](https://github.com/ChelseaKR/permit-pathways/actions/runs/30428314821),
  and
  [run 30478494564](https://github.com/ChelseaKR/permit-pathways/actions/runs/30478494564).

These are elapsed workflow timings calculated from GitHub's `startedAt` and
`updatedAt` values. They measure validation and static publication in an
already configured prototype repository. They do not measure jurisdiction
configuration, source review, integration, security authorization, production
deployment, support, or time to a usable permitting result. The runs also
precede the current unmerged readiness implementation.

**Next**

- Repeat the measurement on the exact submission commit and retain the run
  links.
- Ask a proposed delivery team to validate scope, staffing, dependencies, and
  assumptions before using a jurisdiction timeline.

**Planned**

- The current [pilot brief](SHOWCASE-PILOT-BRIEF.md) proposes 8 to 12 weeks for
  one bounded English-language ADU workflow under stated assumptions. This is
  an unvalidated planning estimate, not a prior result or quote.

**Unknown**

- Production hosting, implementation, integration, support, maintenance, and
  total cost.
- Delivery team capacity, jurisdiction review time, procurement path, and
  deployment-specific security or privacy work.

Do not infer production time or cost from the prototype CI or Pages timings.

## 6. Submission proof and supporting materials

**Implemented**

- The [public prototype](https://chelseakr.github.io/permit-pathways/) and
  [hypothetical ADU route sample](https://chelseakr.github.io/permit-pathways/check.html?sample=adu)
  are available without sign-in.
- A readable [packet sample page](../prepare.html) exists in the current working
  tree but is not part of the published `main` evidence until the exact commit
  is merged and deployed.
- The [submission draft](SHOWCASE-SUBMISSION-DRAFT.md) records current field
  assumptions, boundaries, and unresolved placeholders.

**Next**

- Verify the live Authorium fields, word limits, qualification placement, and
  supporting-material rules.
- Prepare no more than two annotated screenshots and a public video no longer
  than 120 seconds using the exact submission commit.
- Publish and verify the packet-presence page before using it as submission
  evidence.
- Attend or review the July 30 Vendor Information Forum and record any change
  to the submission interpretation.

**Planned**

- Rehearse the full submission narrative with a strict distinction between
  implemented prototype behavior, validation work, and pilot hypotheses.

**Unknown**

- Whether the live portal differs from the application preview.
- Whether a packet-presence public view, final screenshots, video, and confirmed
  qualifications will be ready before submission.

## Submission gate

Do not submit until:

1. every placeholder in the application draft is resolved;
2. the exact commit is tested, published, and linked;
3. qualifications and applicant authority are confirmed by the user;
4. the readiness sample is described only as deterministic packet presence;
5. external validation is either reported with its method and results or
   explicitly reported as not completed;
6. the production timeline is labeled an unvalidated estimate and cost remains
   unknown unless a delivery team supplies a supportable figure; and
7. screenshots and video show only synthetic facts and current capability
   boundaries.
