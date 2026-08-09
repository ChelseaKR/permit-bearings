# Woodland flagship formative evidence protocol

Status: prepared, not started
Protocol version: 2.0.0
Prepared: 2026-08-02

No expert review, recruitment, participant session, partner commitment,
manual accessibility check, Spanish semantic review, Spanish-language
usability check, source-change rehearsal, or permitting outcome is claimed.
Aggregate counts and activity states remain zero, `not_run`, or `pending` in
the canonical
[`woodland-flagship-gate.json`](../data/validation/woodland-flagship-gate.json).

This protocol covers two independent content-authority reviews and exactly six
moderated sessions on one frozen version of the synthetic Woodland
route-to-packet journey. It is formative research, not a jurisdiction pilot,
legal review, accessibility audit, translation review, representative sample,
or measurement of permitting outcomes.

Operational evidence, privacy, partner, maintenance-rehearsal, and decision
rules are defined in [`VALIDATION-EVIDENCE.md`](VALIDATION-EVIDENCE.md).

The canonical activity ledgers are:

- [`woodland-content-review.json`](../data/validation/woodland-content-review.json)
  for the two independent content-authority reviews;
- [`woodland-participant-sessions.json`](../data/validation/woodland-participant-sessions.json)
  for exactly six completed, de-identified, same-version scorecards;
- [`woodland-manual-evidence.json`](../data/validation/woodland-manual-evidence.json)
  for manual access, Spanish semantic review, and Spanish-language usability;
  and
- [`woodland-source-change-rehearsal.json`](../data/validation/woodland-source-change-rehearsal.json)
  for the controlled source-change and re-review rehearsal.

Gate aggregates are derived from those ledgers. Do not edit an aggregate to
manufacture a passing result.

## Questions this protocol can answer

The work examines whether:

1. two qualified reviewers agree that each of the 25 bounded checklist
   mappings and its action draft is supported, safely worded, or routed to
   staff;
2. relevant people independently describe a recent analogous permitting pain,
   consequence, and workaround;
3. a participant can explain the displayed route as candidate guidance rather
   than approval or final eligibility;
4. a participant can locate material facts, source status, and an official
   citation;
5. choosing "I'm not sure" for the City-preapproved-plan applicability fact
   visibly withholds the packet transition and creates a staff question;
6. a participant can restore the synthetic fact, carry the same versioned
   journey into packet preparation, and identify the first three actions;
7. a participant can distinguish reported presence from correctness,
   compliance, completeness, acceptance, or approval; and
8. the selected workflow avoids repeated navigation blockers and confident
   critical over-trust.

The work cannot determine whether an encoded rule is legally correct, whether
Woodland accepts an interpretation, whether a real application is complete,
whether the interface conforms to WCAG, whether Spanish guidance is
semantically equivalent, or whether the product changes permit time, staff
effort, correction cycles, or housing production.

## Evidence design

| Activity | Target | Method | Current state |
|---|---:|---|---|
| Content-authority review | 2 reviewers | Independent classification of all 25 mappings and action drafts, followed by sourced adjudication | `not_run` |
| Applicant/practitioner sessions | Exactly 6 | Moderated remote session using one frozen deployed commit and synthetic facts only | `not_run` |
| Partner gate | 1 qualifying written next step | Private receipt with a concrete next step, owner role, and date | `pending` |
| Source-change/re-review rehearsal | 1 | Timed controlled rehearsal from detection through republication | `not_run` |
| Manual accessibility and language work | See signoff-required matrix | Version-bound human checks, kept separate from usability | `not_run` |

Do not combine these activities into one favorable label. Usability cannot
substitute for content authority, partner evidence, accessibility, language
review, or maintenance ownership.

## Freeze before external work

Before either reviewer receives material and before the first participant
session:

1. Record the artifact lock ID, one full 40-character commit SHA, its exact
   deployed URL, freeze date, source snapshot ID, source-snapshot receipt ID,
   verifier code, and verification receipt.
2. Verify the journey ID/version and every journey, fact-envelope, screening,
   readiness-workflow, and readiness-packet fingerprint in the canonical gate
   record.
3. Record the exact source IDs and hashes for Gov. Code section 66317, the HCD
   ADU Handbook, the City checklist, and Yolo parcel-layer metadata.
4. Verify `index.html`, `check.html?sample=adu`, and the exact versioned packet
   URL recorded in the gate.
5. Verify the versioned answer key against the generated journey and readiness
   evidence.
6. Complete one internal dry run from the landing page without a product tour.
   Bind its receipt to the lock ID, commit, exact deployed URL, source snapshot
   ID, and source-snapshot receipt; record a passing result on or after the
   freeze date.
7. Confirm that no telemetry, account, upload, external model call, or
   participant-data store is active.

Do not test a moving branch, local working tree, pull-request preview, or a
deployment that differs from the locked SHA. If a blocking content defect or
dangerous over-trust requires a change, close that cohort against the old
version, freeze the new deployment, and recruit a fresh cohort. Never combine
task results or timings across versions.

## Two independent expert reviews

### Reviewer criteria

- Reviewer 1 must know Woodland's selected checklist or intake workflow.
- Reviewer 2 may be a California ADU architect, residential designer, permit
  expeditor, contractor, housing navigator, or comparable professional with
  recent packet experience.
- A reviewer must not have authored the mapping, actions, or this protocol.
- Participation is individual unless formal institutional authorization is
  separately recorded. Individual review is not agency approval.

### Review procedure

Give each reviewer an isolated copy containing the same frozen source package,
25 requirement rows, action drafts, and disposition definitions. Do not show
one reviewer the other's answers before both independent records are locked.

For every row, independently classify the mapping and action as `supported`,
`changes_required`, `suppress`, `route_to_staff`, or `blocked_by_source`. Record a
short sourced rationale for any result other than `supported`.

Initial agreement requires the same mapping and action disposition before
adjudication. The content gate requires at least 22 of 25 rows to agree
initially. Every disagreement must be resolved through better sourcing,
suppression, or explicit staff routing. Zero known blocking content defects
may remain visible before participant testing.

A blocking content defect is:

- an unsupported requirement or omission;
- an incorrect applicability condition;
- a source, locator, excerpt, or fingerprint mismatch;
- an action that implies approval, compliance, completeness, or acceptance;
  or
- an unknown treated favorably.

The review does not promote production data automatically. A later content
pull request must bind any completed review claim to its exact reviewer,
method, date, version, fingerprints, and authorization scope.

## Participant cohort

Run exactly six sessions. Categories may overlap, but report every raw count.
The completed cohort must include:

- at least 3 homeowners or small property owners;
- among those primary beneficiaries, at least 2 who recently attempted an ADU
  or analogous small-jurisdiction residential packet;
- among those primary beneficiaries, at least 1 who considered or used a
  preapproved plan;
- at least 2 practitioners with recent ADU packet experience; and
- at least 1 participant with experience in a smaller jurisdiction.

Include an adult who can give informed voluntary consent, can use a desktop or
laptop browser for the remote session, and meets at least one cohort category.
Exclude a person who contributed to the repository or protocol, wants advice
about a live case, intends to disclose a real parcel or packet, or cannot give
consent.

Do not describe this maximum-six convenience cohort as representative of
California applicants, practitioners, or staff.

## Privacy and study-data rules

- Use participant codes `P01` through `P06` only.
- Use the repository's made-up Woodland journey and synthetic packet only.
- Do not ask for a name, employer, jurisdiction, address, assessor parcel
  number, permit number, application number, client, drawing, packet, or real
  project detail.
- Keep contact, screening, scheduling, consent administration, code-to-person
  mapping, and private correspondence outside the repository.
- Do not record audio, video, screen content, or a transcript.
- Keep only de-identified structured scorecards and aggregate funnel counts in
  the repository. Paraphrase; do not store quotations in the public record.
- If personal, confidential, or live-project information is disclosed, stop
  it, remind the participant of the boundary, and remove it before analysis or
  commit.
- Do not add telemetry, accounts, uploads, external model calls, or persistent
  browser storage for the study.

## Session sequence, approximately 35 minutes

| Time | Activity |
|---|---|
| 0:00 to 3:00 | Scope, consent, synthetic-only and no-PII reminder |
| 3:00 to 13:00 | Critical-incident interview about the last analogous attempt |
| 13:00 to 20:00 | Task 1: candidate route, evidence, and unknown applicability |
| 20:00 to 28:00 | Task 2: packet preparation and portable summary |
| 28:00 to 33:00 | Confidence, comprehension, and next-action follow-up |
| 33:00 to 35:00 | Debrief, safety correction if needed, and close |

The task windows are observation caps, not passing-time thresholds. The gate
uses a median of at most five minutes for routing and at most six minutes for
packet preparation.

## Opening and consent script

Read:

> Thank you for joining. I am evaluating a prototype, not you. This session
> takes about 35 minutes and uses only made-up ADU information. The prototype
> shows candidate guidance. It is not legal advice, approval, final
> eligibility, or a complete local checklist.
>
> Please do not share a name, employer, jurisdiction, real address, parcel or
> application number, drawing, packet, client information, or confidential
> material. I will take a structured, de-identified scorecard under a
> participant code. I will not record audio, video, or your screen. You may
> skip a question or stop at any time.
>
> De-identified observations and aggregate counts may be published with the
> tested commit and method. Do you consent to participate and to this
> structured note taking?

Record `yes` or `no` outside the public scorecard. End the session if the
answer is not `yes`.

Then read:

> As you work, say what you are looking for, what you expect to happen, and
> what you think the page means. I may remind you to keep talking, but I will
> not show you how to complete a task until its timer ends.

## Critical-incident interview, 10 minutes

Ask about the participant's last analogous attempt without requesting a place,
parcel, organization, client, or case identifier:

1. "What were you trying to prepare or understand?"
2. "What specific event or question made the process difficult?"
3. "What happened because of that difficulty?"
4. "What workaround did you use, and who or what helped?"
5. "How often do you encounter something similar: once, less than monthly,
   monthly, weekly, or more often?"

Record only broad, de-identified categories for trigger, consequence,
workaround, and recurrence. A general opinion that permitting is hard does not
meet the problem-evidence threshold. The record needs a specific recent
trigger, consequence, and workaround.

## Task 1: candidate route and honest unknown

Start the timer, then read:

> Starting from this landing page, use the made-up Woodland example. Explain
> the candidate route in your own words and what it does not decide. Show two
> material facts, the source status, and one official citation. At the packet
> applicability question, choose "I'm not sure." Explain what happened, why
> packet preparation is blocked, and what you would ask staff. Then restore
> the made-up answer to "Yes" and continue into packet preparation.

Do not provide a direct task URL or interface tour. Full success requires the
participant to:

- reach the example from `index.html`;
- describe the route as candidate guidance, not approval or final eligibility;
- identify two facts as made up or applicant-asserted rather than verified
  parcel facts;
- find source status and the Gov. Code section 66317 citation;
- choose `unknown` for `uses_city_preapproved_plan`;
- recognize that the packet handoff is withheld and repeat or paraphrase the
  staff question; and
- restore `yes` and follow the exact versioned handoff.

Stop timing when the participant reaches packet preparation and states why the
transition is available.

## Task 2: packet preparation and carry-forward

Start the timer, then read:

> In this synthetic packet result, find one item marked "Reported missing" and
> its next action. Find one item marked "Needs confirmation" and the question
> you would take to staff. Locate the evidence for one requirement. Identify
> the first three preparation actions, then show how you would carry the
> summary forward. Finally, tell me whether "Reported present" means correct,
> compliant, complete, accepted, or approved.

Full success requires the participant to:

- identify a displayed missing item and its source-backed action;
- identify a needs-confirmation item and a direct staff question;
- locate the City checklist evidence and its source status;
- identify the three reported-missing preparation actions;
- locate the print/save control and recognize that the app does not store the
  resulting artifact; and
- state that reported presence establishes none of correctness, compliance,
  completeness, acceptance, or approval.

The participant need not create a local PDF. Stop timing after the final
presence-boundary explanation.

## Neutral prompts and assistance

Allowed neutral prompts are:

- "What are you looking for now?"
- "What do you expect that control to do?"
- "What does that phrase mean to you?"
- "What makes you say that?"
- "What would you do next?"

A think-aloud reminder is not assistance. A statement identifying a control,
section, answer, or route is directional assistance and must be recorded. Do
not correct an interpretation during timing. After timing ends, correct any
safety-critical misunderstanding and record that the correction occurred.

## Scoring

### Task result

- `independent`: every critical criterion completed without a directional
  hint;
- `assisted`: every critical criterion completed after directional help;
- `partial`: at least one critical criterion completed but one or more missed;
- `not_completed`: no critical criterion completed, the participant stops, or
  the observation cap is reached; and
- `not_observed`: a protocol or technical problem prevents the task.

### Timing

Start when the moderator finishes the task prompt. Stop at the task-specific
endpoint. Record seconds. Keep setup, consent, critical-incident questions,
follow-up, and moderator explanations outside the task time. Report median,
range, and denominator for the six same-version sessions.

### Error codes

| Code | Observed error |
|---|---|
| `CANDIDATE_AS_APPROVAL` | Treats candidate guidance as approval or final eligibility |
| `HYPOTHETICAL_AS_REAL` | Treats made-up facts as verified parcel facts |
| `SOURCE_STATUS_MISREAD` | Treats dated, stale, unverified, or review-pending evidence as human-approved guidance |
| `UNKNOWN_ASSUMED_FAVORABLE` | Expects an unknown applicability fact to preserve the packet handoff |
| `EVIDENCE_NOT_FOUND` | Cannot locate source status, citation, or requirement evidence |
| `PRESENT_AS_COMPLIANT` | Treats reported presence as correctness, compliance, completeness, acceptance, or approval |
| `STAFF_REVIEW_MISSED` | Resolves or overlooks an item routed to staff |
| `NEXT_ACTION_NOT_FOUND` | Cannot identify the displayed next action |
| `NAVIGATION_BLOCKER` | Cannot reach or continue the journey without directional help |
| `TECHNICAL_ERROR` | Browser, connection, or prototype failure prevents observation |

Record observed behavior before assigning a code. Silence alone is not an
error.

### Confidence and critical error

After each task ask:

> On a scale from 1 to 5, how confident are you that you understood what the
> page says and what you would do next? What is the main reason?

Confidence is self-report, not correctness. A confident critical error exists
when a participant finishes believing that a candidate route is approval or
final eligibility, or that reported presence means compliant or accepted, and
either rates that interpretation 4 or 5 or repeats it after the neutral prompt
"What makes you say that?" Any confident critical error fails that version.

## De-identified scorecard template

The participant ledger reserves `P01` through `P06` only for the final six
completed sessions that make up the same-version denominator. A withdrawal,
exclusion, failed screening, or technical interruption remains in the
aggregate recruitment funnel and does not fill or partially fill a scorecard
slot. Keep the slot `not_run` until one complete, de-identified record and all
required receipts exist. Check every record for accidental PII before commit.

```text
Participant code: P01 | P02 | P03 | P04 | P05 | P06
Scorecard status: not_run | complete
Broad cohort categories:
Primary beneficiary: yes | no
Recent analogous packet attempt: yes | no
Preapproved-plan exposure: yes | no
Practitioner with recent ADU packet experience: yes | no
Smaller-jurisdiction experience: yes | no
Session date:
Artifact lock ID: woodland-route-to-packet-frozen-artifact-1
Frozen commit SHA:
Deployed landing URL:
Journey ID and version:
Source snapshot ID:
Artifact verified on and by code:
Artifact-verification receipt ID:
Protocol version: 2.0.0
Answer-key version: 1.2.0
Browser and device category:
Moderator code:
Recording: none
Protocol deviations:
Private screening receipt ID:
Private consent receipt ID:
Privacy-review receipt ID:
Scorecard integrity SHA-256:

Critical incident
Trigger category:
Consequence category:
Workaround category:
Recurrence: once | less_than_monthly | monthly | weekly | more_often
Specific recent pain threshold met: yes | no | not_observed

Task 1
Duration seconds:
Result: independent | assisted | partial | not_completed | not_observed
Directional assistance:
Error codes:
Candidate-guidance interpretation correct: yes | no | not_observed
Source and unknown escalation correct: yes | no | not_observed
Confidence and reason, de-identified:
Observed behavior in sequence, de-identified:

Task 2
Duration seconds:
Result: independent | assisted | partial | not_completed | not_observed
Directional assistance:
Error codes:
Packet and next-action interpretation correct: yes | no | not_observed
Presence boundary correct: yes | no | not_observed
Confidence and reason, de-identified:
Observed behavior in sequence, de-identified:

Final safety read-back
Candidate route treated as approval or final eligibility: yes | no
Reported presence treated as compliant or accepted: yes | no
Misunderstanding repeated after the neutral prompt: yes | no
Confident critical error: yes | no
Safety correction after timing:

Synthesis fields
Supported observation:
Contrary or ambiguous observation:
Recommended change:
Evidence needed before broader claim:
```

Do not enter a name, contact detail, employer, jurisdiction, property, client,
real case, quotation, raw transcript, or private correspondence in this record.
The three private receipt IDs are opaque references to separately controlled
records; they must not contain contact details, mailbox identifiers, or URLs.
Recompute the participant aggregate from the six scorecard rows. Never enter
task counts, medians, or a same-version result directly into the gate.

## Passing thresholds

Report raw counts and denominators; do not imply statistical significance.

### Content authority

- 2 independent reviewers each classify all 25 rows.
- At least 22 of 25 rows receive initial agreement.
- Every disagreement is sourced, suppressed, or routed to staff.
- Zero known blocking content defects remain visible.

### Problem evidence

- At least 3 participants, including at least 2 primary beneficiaries,
  independently describe a specific recent pain, consequence, and workaround.
- At least 1 domain participant reports monthly or more frequent recurrence.

### Trust and tasks

- At least 5 of 6 correctly describe the route as candidate guidance.
- At least 5 of 6 locate source status or a citation and correctly interpret
  unknown-fact escalation.
- At least 5 of 6 identify the packet gap and correct next actions.
- Median route time is at most 300 seconds.
- Median packet time is at most 360 seconds.
- A navigation blocker occurs in at most 1 session.
- Zero confident critical errors occur.

### Pilotability and maintainability

- At least 1 credible partner supplies a qualifying written next step with an
  owner role and date.
- 1 source-change/re-review rehearsal completes all stages and records a human
  owner, elapsed time, active maintainer/reviewer time, and defects.
- The prospective partner, not the researcher, decides whether maintenance
  burden is acceptable.
- All 21 manual-access checks pass on the frozen artifact.
- All 19 Spanish semantic-review rows are approved on that artifact.
- The separate `ES-USABILITY-JOURNEY` Spanish-language usability check passes.

Usability alone is not a pass.

## Synthesis and claim rules

1. Verify each scorecard against the frozen SHA, source snapshot, protocol, and
   answer key before aggregation. Artifact verification and the session must
   occur on or after the freeze, in that order.
2. Show counts and denominators, assistance, range and median timing, contrary
   evidence, technical interruptions, withdrawals, and exclusions.
3. Preserve primary-beneficiary and practitioner counts rather than collapsing
   them into a generic user label.
4. Separate observed behavior, participant statement, and researcher
   interpretation.
5. Do not discard disconfirming evidence or a failed task to make the gate
   appear favorable. Derive correctness from the recorded task result and
   derive the confident-critical-error flag from final beliefs, confidence,
   and repetition after the neutral prompt.
6. A participant opinion does not change a source, rule, mapping, action, or
   review status.
7. A staff participant is not a jurisdiction endorsement.
8. Do not claim reduced time, rework, staff burden, improved completeness,
   legal accuracy, accessibility, language quality, adoption, or a housing
   outcome from these sessions.
9. If the product changes, close the old cohort and test the revised commit
   with a fresh cohort. Do not aggregate versions.

Before evidence exists, the only permissible status statement is:

> The evidence protocol is prepared. Expert review, participant sessions,
> manual accessibility checks, Spanish semantic review, Spanish-language
> usability, the partner gate, and the source-change rehearsal have not been
> completed.

## Proceed, extend, pivot, or stop

- `proceed`: every P0, content, cohort, problem, trust/task, timing, safety,
  partner, 21-check manual-access, 19-row Spanish semantic-review, separate
  `ES-USABILITY-JOURNEY`, rehearsal, and maintenance-owner condition passes on
  the frozen artifact with required receipts.
- `extend`: a fix, recruitment shortfall, incomplete gate, or missing receipt
  warrants more evidence; a blocking product fix requires a new lock and fresh
  cohort.
- `pivot`: evidence supports a narrower applicant job, a staff-facing source
  workbench, or a different jurisdiction with a sponsor and authoritative
  source package.
- `stop`: no qualified reviewer or partner path exists, a blocking source issue
  cannot be resolved, dangerous over-trust persists, three or fewer complete a
  core task, the value depends on production PII or legal determinations, or
  maintenance has no human owner.

Showcase selection or nonselection does not change this decision.
