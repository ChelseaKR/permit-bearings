# Woodland flagship evidence gate

Status: prepared, not run
Record date: 2026-08-02
Canonical status record:
[`data/validation/woodland-flagship-gate.json`](../data/validation/woodland-flagship-gate.json)

No reviewer has completed a review. No participant has been recruited or
tested. No partner commitment, manual accessibility result, Spanish semantic
review, Spanish-language usability result, source-change rehearsal, adoption,
or permitting outcome is recorded. The files in this repository are
scaffolding for collecting evidence; their existence is not outcome evidence.

## Purpose and authority

This gate decides whether the bounded Woodland route-to-packet prototype has
earned a stronger portfolio claim. It does not turn a synthetic example into a
pilot, a real application, legal advice, a completeness certification, or a
jurisdiction-approved workflow.

The JSON record is the machine-readable source of truth for status, artifact
lock fields, aggregate recruitment counts, thresholds, and the final
recommendation. This document defines how to produce evidence that may update
that record. The participant script and scorecard are in
[`SHOWCASE-VALIDATION-PLAN.md`](SHOWCASE-VALIDATION-PLAN.md). The signoff-required
manual accessibility and language matrix is in
[`MANUAL-VALIDATION.md`](MANUAL-VALIDATION.md).

The four versioned activity ledgers are the
[`content-review ledger`](../data/validation/woodland-content-review.json),
[`participant-session ledger`](../data/validation/woodland-participant-sessions.json),
[`manual and language ledger`](../data/validation/woodland-manual-evidence.json),
and
[`source-change rehearsal ledger`](../data/validation/woodland-source-change-rehearsal.json).
The aggregate fields in the flagship gate must be recomputed from these
records; they are not independently authored evidence.

If prose and the JSON record disagree, use the more conservative status and
open a corrective pull request. Never raise a status because work was planned,
scheduled, discussed, or informally reviewed.

## Evidence states

- `not_run`: the activity has no complete evidence record.
- `pending`: a gate remains open; it does not mean outreach or work occurred.
- `complete`: every required field and linked receipt exists for one frozen
  artifact, and the activity's result is recorded whether favorable or not.
- `blocked`: the activity was attempted but could not be completed. Record the
  reason without converting it to a pass.

Only a later evidence pull request may move an activity out of `not_run` or
`pending`. That pull request must include the frozen commit, de-identified raw
counts, contrary evidence, and the receipt fields required below.

## Freeze one test artifact

All six participant scorecards must describe one commit, one deployed build,
one source snapshot, and one answer key. Before the first session:

1. Merge every intended content or interface change and wait for its deployed
   build.
2. Record the lock ID, full 40-character commit SHA, exact deployed URL,
   source snapshot ID and receipt, freeze date and owner code, and an opaque
   verification receipt.
3. Confirm the journey ID and version, screening-case fingerprint, journey and
   fact-envelope fingerprints, readiness workflow and packet fingerprints,
   and every source ID/hash against the canonical gate record.
4. Verify both sample paths in the lock: `check.html?sample=adu` and the exact
   versioned `prepare.html` journey URL.
5. Verify the answer key from the generated journey and readiness evidence.
   It must identify the candidate route, official citation and source status,
   the unknown applicability behavior, the three reported-missing items, the
   needs-confirmation items, the staff questions, and the presence boundary.
6. Complete an internal dry run from `index.html` without a product tour. Its
   receipt must repeat the lock ID, commit SHA, exact deployed URL, source
   snapshot ID, and source-snapshot receipt ID, and record a tester code,
   run date, pass/fail result, and opaque evidence receipt ID. The run date
   cannot precede the freeze date.
7. Set the artifact lock to complete only after every field agrees. Do not
   freeze a working tree, pull-request preview, moving branch name, or local
   server whose content differs from the deployed commit.

If a blocking content defect or dangerous over-trust requires a change after
the first session, that cohort cannot pass. Close it as an earlier-version
record, deploy the fix, create a new lock, and use a fresh cohort. Do not mix
denominators, timings, or task results across versions.

## Independent content-authority review

Complete two independent reviews before applicant testing:

1. One reviewer must know Woodland's selected checklist or intake workflow.
2. The second reviewer may be a broader California ADU practitioner with
   recent packet experience.

Record a broad qualification summary and whether each person participated as
an individual or with explicit institutional authorization. Individual
participation never establishes agency approval. Keep identity and contact
records outside the repository unless the person has explicitly authorized a
public, named, version-bound review receipt.

Each reviewer independently classifies all 25 requirement mappings and their
action drafts before seeing the other review. For each row, check:

- the requirement ID and source locator identify the cited checklist item;
- the excerpt and conditional fact preserve the source meaning;
- the mapping neither adds an unsupported requirement nor omits one;
- the action stays within packet preparation and does not imply approval,
  compliance, completeness, or acceptance; and
- uncertainty is suppressed or converted to a direct staff question.

Allowed pre-adjudication dispositions are `supported`, `changes_required`,
`suppress`, `route_to_staff`, and `blocked_by_source`. Initial agreement means
the two reviewers chose the same mapping and action disposition before any
discussion. At least 22 of 25 rows must initially agree. Every disagreement
must then be resolved through better sourcing, suppression, or explicit staff
routing.

A blocking content defect is an unsupported requirement or omission, an
incorrect applicability condition, a source mismatch, an action that implies
approval or compliance, or an unknown treated favorably. Zero known blocking
defects may remain visible before participant testing.

Completing a review matrix does not silently promote application data to
`human_reviewed` or `jurisdiction_approved`. Any promotion requires a separate
content pull request containing the exact reviewed versions, reviewer, method,
date, content fingerprint, and authorization scope required by the production
schema.

## Recruitment and privacy boundary

Recruitment has not started. The canonical ledger therefore contains zeroes,
not placeholder participants or partners.

Those zeroes are administrative counts of recorded completed activity. The
specialized review matrix keeps unmeasured agreement, defect, disposition, and
eligibility results as `null`; neither representation is a failure or a pass.

Keep the following outside the public repository:

- names, handles, email addresses, phone numbers, and calendar invitations;
- employers, jurisdictions, client relationships, and scheduling records;
- real addresses, assessor parcel numbers, permit or application numbers,
  drawings, packets, screenshots, or project files;
- raw notes, recordings, transcripts, direct messages, and private partner
  correspondence; and
- any link or locator that reveals a mailbox, calendar, private document, or
  participant identity.

The repository may retain participant and reviewer codes, broad role or
qualification categories, aggregate funnel counts, de-identified structured
observations, and opaque private-receipt IDs. Store the mapping between a code
and a person only in separately controlled material outside the repository.

Use synthetic facts and files only. Do not add telemetry, accounts, uploads,
external model calls, or a participant-data store. If accidental personal,
confidential, or live-project information is disclosed, stop the disclosure,
exclude it from the record, and remove it before any analysis or commit.

Update aggregate funnel counts for each group:

- reviewers: contacted, screened, qualified, scheduled, completed, withdrawn,
  and excluded;
- participants: contacted, screened, qualified, scheduled, completed,
  withdrawn, excluded, and technically interrupted; and
- partners: contacted, discovery conversations completed, and qualifying
  written next steps.

Counts describe the funnel. They do not establish that a person met a task or
that a partner commitment qualified.

## Participant evidence

Run exactly six moderated, approximately 35-minute sessions under
[`SHOWCASE-VALIDATION-PLAN.md`](SHOWCASE-VALIDATION-PLAN.md). At least three
participants must be homeowners or small property owners. Among those primary
beneficiaries, at least two must have recently attempted an ADU or analogous
small-jurisdiction residential packet and at least one must have considered or
used a preapproved plan. Include at least two practitioners with recent ADU
packet experience and at least one participant with experience in a smaller
jurisdiction. Categories may overlap, but show the raw counts.

The canonical scorecards are the six slots `P01` through `P06` in
[`woodland-participant-sessions.json`](../data/validation/woodland-participant-sessions.json).
They are reserved for the six completed sessions in the final same-version
denominator. Screening failures, exclusions, withdrawals, and technical
interruptions remain aggregate recruitment counts and never occupy a
scorecard slot.

Begin with a critical-incident interview about the last analogous attempt,
then start tasks at the landing page without a tour or direct task URL. Record
the specific trigger, consequence, workaround, recurrence category, task
timings, assistance, errors, confidence, and contrary evidence in the
de-identified scorecard. Do not solicit a real parcel or packet.

The canonical thresholds require:

- at least three participants, including at least two primary beneficiaries,
  to describe a specific recent pain, delay, or costly workaround;
- at least one domain participant to report that the problem recurs at least
  monthly;
- at least five of six to describe the route as candidate guidance;
- at least five of six to locate source status or a citation and correctly
  interpret unknown-fact escalation;
- at least five of six to identify the packet gaps and correct next actions;
- a routing-task median of at most five minutes and a packet-task median of at
  most six minutes;
- no navigation blocker repeated in two or more sessions; and
- zero confident critical errors.

A confident critical error occurs when a participant finishes believing that
the candidate route is approval or final eligibility, or that reported-present
means compliant or accepted, and either rates that interpretation 4 or 5 out
of 5 or repeats it after a neutral clarification prompt. Any such error means
that version cannot pass.

Report raw counts, denominators, assistance, and contrary evidence. These six
sessions cannot establish legal accuracy, jurisdiction acceptance,
accessibility conformance, translation quality, improved completeness, staff
time savings, or a real permitting outcome.

Each complete scorecard must bind the artifact lock ID, commit, deployed URL,
source snapshot, artifact verification date and verifier code, and artifact
verification receipt. It must also carry opaque screening, consent,
privacy-review, and scorecard-integrity receipts. Keep the underlying private
records outside the repository. Artifact verification cannot predate the
freeze, and the session cannot predate artifact verification. Task-result and
correctness fields must agree with the scoring definitions: `not_observed`
cannot carry a positive correctness result. The critical-error flag is derived
from the two final beliefs, confidence, and whether the misunderstanding was
repeated after the neutral prompt; it cannot be hand-lowered. Recompute the
participant aggregate from the six rows; never hand-edit counts, medians, or
same-version status into the flagship gate.

## Partner gate and private receipt

The partner gate is pending. A credible partner must have a role that can
deliver the proposed next step. One written commitment qualifies only when it
includes an owner role and date and does one of the following:

- commits to recruit bounded pilot users;
- commits to provide an official public source package; or
- schedules a bounded-pilot scoping or decision session.

Praise, a demo invitation, an introduction, routine reviewer follow-up,
"keep me posted," or an ownerless and undated expression of interest does not
qualify. A statement by an individual staff member is not institutional
authorization unless explicit authorization is recorded.

Keep the message, name, contact details, and organization-specific private
material outside the repository. The public ledger may record only a partner
category, qualifying next-step type, owner role, due date, authorization
scope, and an opaque private-evidence receipt ID. The receipt ID must resolve
in the separately controlled evidence store; it must not be a public URL or
mailbox identifier.

## Source-change and re-review rehearsal

The canonical
[`woodland-source-change-rehearsal.json`](../data/validation/woodland-source-change-rehearsal.json)
record is not run. Exercise one controlled source change against the frozen
build without representing a simulated change as a change in law. Record:

1. the frozen source ID, prior hash, commit, and start time;
2. detection and the distinction between `changed` and `unverifiable`;
3. the exact affected requirement, action, test, and user-facing output set;
4. at least one unaffected control;
5. each human disposition and any update or suppression;
6. the approval method and human owner role;
7. the republished commit, URL, source hash, and verification result; and
8. elapsed time, active maintainer time, active reviewer time, and defects
   found.

The stages are detection, affected/unaffected identification, review,
update-or-suppress, approval, and republication. Every stage remains
`not_run` until its start and completion timestamps, actor code, method,
observed result, evidence receipt, and review receipt exist. The approval and
republication record additionally requires approval, republished-commit,
deployed-URL, source-hash, and verification receipts. A fetch failure is an
`unverifiable` state, not proof that the source changed.

Detection, impact identification, update/suppression, and republication are
maintainer stages; review and approval are reviewer stages. The observed
requirement, action, record, and unaffected-control lists must be exact and
duplicate-free. Requirement dispositions are limited to `retain`, `revise`,
`route_to_staff`, and `suppress`. A proceed-qualifying rehearsal must finish
with zero blocking defects; a blocking defect requires correction, a new
artifact lock, and a fresh clean rehearsal. Elapsed and active-role minutes
must equal the timestamp-derived durations rather than an independently typed
estimate.

Completing the rehearsal measures maintenance burden. It does not establish
that the burden is acceptable. A prospective partner must make that decision,
and the final record must name the human owner role expected to carry it. The
separate `partner_burden_decision` record remains pending until it contains the
partner role, decision date, opaque private receipt, and an independent receipt
verification. The rehearsal aggregate derives its burden fields from that
record; it cannot approve its own burden. The burden decision must follow the
completed rehearsal, and receipt verification must follow the decision.
Elapsed, active maintainer, and active reviewer minutes and the aggregate
rehearsal result are derived from the stage, execution, observed-impact, and
publication receipts rather than typed directly into the gate.

## Manual access and Spanish evidence

Three independent gates in
[`woodland-manual-evidence.json`](../data/validation/woodland-manual-evidence.json)
remain `not_run`:

1. manual access: all 21 `manual_checks` rows other than
   `ES-USABILITY-JOURNEY` must pass;
2. Spanish semantics: all 19 `spanish_semantic_reviews` rows must be approved;
   and
3. Spanish-language usability: the separate `ES-USABILITY-JOURNEY` check must
   pass.

Automated tests, Lighthouse, schema checks, an informal spot check, or a pass
in one of these gates cannot convert another gate to pass. Use the exact frozen
commit and journey URLs in `MANUAL-VALIDATION.md`. Spanish interface
localization is not reviewed source-derived guidance. Keep English
legal/content review separate.

## Decision rules

The final recommendation remains pending until the evidence record is
complete. Use one of four recommendations:

### Proceed

Use `proceed` only if every P0 boundary holds, both expert reviews clear the
content gate, six participants test one frozen version and clear every problem,
task, timing, navigation, and safety threshold, all 21 manual-access checks
pass, all 19 Spanish semantic rows are approved, `ES-USABILITY-JOURNEY`
passes, the source-change rehearsal is verified and has a human owner, its
burden is accepted by the prospective partner, and one credible partner
supplies a qualifying written next step with an owner and date. Every
supporting receipt must be present and tied to the same frozen artifact.
No execution start or evidence date may predate the freeze. The final
evaluation must be on or after the latest supporting terminal date, including
every content-row and cross-cutting resolution, manual signoff, session end,
rehearsal completion, and receipt verification; the signed decision must be on
or after that evaluation.

### Extend

Use `extend` when the wedge remains plausible but a blocking fix, cohort miss,
incomplete review, access defect, missing receipt, or recruitment shortfall
requires more evidence. Freeze a new build and use a fresh cohort after any
blocking product change.

### Pivot

Use `pivot` when evidence supports a narrower or different job. Examples are
packet preparation without route matching, a staff-facing source workbench,
or a replacement jurisdiction with a named sponsor and authoritative source
package. Do not carry Woodland-specific evidence into a new wedge without an
explicit boundary.

### Stop

Use `stop` when no qualified content reviewer or credible partner path exists,
authoritative sources cannot resolve a blocking defect, dangerous over-trust
persists, three or fewer participants can complete a core task, value requires
production PII or legal determinations, or maintenance has no human owner.

Showcase selection or nonselection is not a gate result.

## Claim ladder

Until a later evidence pull request clears the gate, the bounded public claim
is:

> The evidence protocol is prepared. Expert review, participant sessions,
> manual accessibility checks, Spanish semantic review, Spanish-language
> usability, the partner gate, and the source-change rehearsal have not been
> completed.

Do not substitute "validated," "pilot," "applicant-ready," "human-reviewed,"
"jurisdiction-approved," "adopted," or a permitting-outcome claim for that
statement. After evidence exists, report the exact tested commit, dates,
method, participant profiles, raw counts and denominators, assistance,
contrary evidence, reviewer scope, partner next step, and unresolved limits.
