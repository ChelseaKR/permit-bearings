# Showcase formative validation plan

Status: planned formative research. No participants have been recruited, no
sessions have been conducted, and no findings or outcomes are claimed.

This plan covers two small, moderated usability studies to inform the Intent to
Showcase submission. Each session is 25 minutes. These studies are not a
jurisdiction pilot, legal review, accessibility audit, translation review, or
measurement of permitting outcomes.

## Objectives

The studies will examine whether people can:

1. recognize that the applicant result is a candidate route, not an approval,
   final eligibility finding, legal opinion, or complete local checklist;
2. identify which made-up facts produced a result and what happens when a
   material fact is unknown;
3. locate the source status, citation, evidence disclosure, suggested starting
   steps, and questions for staff;
4. distinguish a packet item's presence from its consistency, legal
   sufficiency, or agency acceptance;
5. find an item labeled "Reported missing," an item labeled "Needs
   confirmation," and the stated next action in the synthetic
   packet-readiness sample; and
6. complete these tasks without avoidable navigation, terminology, or
   comprehension errors.

Staff sessions will also collect bounded observations about whether the
presentation could support an intake or routing conversation. Applicant and
designer sessions will collect bounded observations about whether the
presentation helps a person understand what to verify and what to prepare
next.

The studies will not determine whether encoded rules are legally correct,
whether a jurisdiction accepts an interpretation, whether a real application
is complete, or whether the product reduces delay, rework, or staff effort.

## Study design

| Study | Participants | Method | Session length |
| --- | --- | --- | --- |
| Staff usability study | 3 to 5 California planning, building, permit intake, or permit-program staff | Moderated remote session with screen sharing | 25 minutes |
| Applicant and designer usability study | 3 to 5 California ADU applicants, prospective applicants, designers, or permit professionals | Moderated remote session with screen sharing | 25 minutes |

The target is formative coverage, not statistical representation. Report the
number recruited, scheduled, completed, withdrawn, and excluded for each
cohort. Keep the cohorts separate during analysis.

## Participant criteria

### Staff study

Include an adult who:

- currently works, or worked within the last three years, in California local
  planning, building, permit intake, or an ADU permit program;
- has handled or observed applicant routing, application intake, or
  completeness questions; and
- can use a desktop or laptop browser while sharing the prototype screen.

Exclude a person who:

- contributed to this repository, its design, or its research plan;
- does not have California planning, building, or permit-intake experience;
- is participating as an official spokesperson without authorization;
- wants the session to review a live application or provide legal advice; or
- cannot give informed, voluntary consent.

Recruit across more than one role or jurisdiction type when practical. Do not
describe this convenience sample as representative of California staff.

### Applicant and designer study

Include an adult who:

- has considered, prepared, designed, or submitted a California ADU project
  within the last three years; or
- professionally helps California homeowners prepare ADU applications; and
- can use a desktop or laptop browser while sharing the prototype screen.

Exclude a person who:

- contributed to this repository, its design, or its research plan;
- has no California ADU experience or near-term intent;
- wants advice about a live parcel, dispute, application, or deadline;
- plans to enter or share a real address, assessor parcel number, application
  number, drawing, permit file, or other project record; or
- cannot give informed, voluntary consent.

Recruit a mix of homeowners and design or permit professionals when practical.
Report the mix exactly. Do not combine professional and homeowner observations
without showing the separate counts.

## No-PII and study-data rules

- Use only the repository's labeled hypothetical ADU sample and the prepared
  synthetic packet-readiness sample.
- Do not ask for or enter names, addresses, assessor parcel numbers, permit
  numbers, application files, employer names, jurisdiction names, or contact
  details in the prototype or study notes.
- Use participant codes `S01` to `S05` for staff and `A01` to `A05` for
  applicants and designers.
- Keep scheduling contact information outside the repository. Do not copy
  direct messages, email addresses, calendar invitations, or recruitment
  lists into committed research artifacts.
- Do not record audio, video, or the participant's screen for these studies.
  The moderator may take structured notes after obtaining consent.
- Paraphrase by default. Record a short de-identified quotation only when the
  participant separately consents to quotation.
- Do not commit participant names, contact information, employers,
  jurisdictions, raw recordings, or unredacted screenshots.
- If a participant begins to disclose personal, confidential, or live project
  information, stop the disclosure, remind them to use only the synthetic
  material, and omit the information from notes. If it was captured, remove it
  before analysis or sharing.
- The public prototype has no applicant-data store. Do not add telemetry,
  accounts, uploads, or external model calls for this research.

## Materials and artifact lock

Before the first session:

1. record the exact 40-character product commit used in every session;
2. verify the hypothetical sample at `check.html?sample=adu`;
3. record the exact URL or local path for the packet-readiness sample;
4. verify that both samples are made up and visibly labeled as such;
5. prepare a packet-readiness answer key containing at least one `present`
   item, one `missing` item, and one `needs_staff_review` item, and verify that
   the public page labels the latter two "Reported missing" and "Needs
   confirmation";
6. verify that the packet sample separates presence from consistency,
   compliance, and agency acceptance;
7. verify that citations and source status remain visible or discoverable;
8. disable or avoid any tool that could collect participant input; and
9. complete one internal dry run against the timing and task-success rubric.

Do not improvise a packet assessment from a real application. If the synthetic
packet-readiness sample is not executable at the locked commit, omit that task,
record the protocol deviation, and do not claim packet-readiness usability
evidence.

## Staff usability study, 25 minutes

### Session sequence

| Time | Activity |
| --- | --- |
| 0:00 to 3:00 | Welcome, scope, consent, and no-PII reminder |
| 3:00 to 5:00 | Role context using broad categories only |
| 5:00 to 13:00 | Task S1, candidate-route and uncertainty flow |
| 13:00 to 21:00 | Task S2, synthetic packet-readiness flow |
| 21:00 to 24:00 | Confidence ratings and staff-specific follow-up |
| 24:00 to 25:00 | Final comment and close |

### Context questions

Ask only:

1. "Which broad role best describes your work: planning, building, permit
   intake, program management, or another related role?"
2. "How often do you encounter ADU routing or application-completeness
   questions: rarely, monthly, weekly, or most workdays?"

Do not ask for the employer, jurisdiction, or a real case.

### Task S1: interpret a candidate route

Read this task exactly:

> Open the hypothetical detached ADU sample. Using only what is on the page,
> tell me what the product says this made-up project may be able to do and what
> it does not decide. Show me two facts used for the result, the source status,
> and one official citation. Then edit the answer to "What dwelling exists on
> the lot now, or is proposed?" to "I'm not sure," submit the answers again,
> and explain what changed.

Do not explain the interface before the participant attempts the task.

Full task success requires the participant to:

- describe the route as a candidate or possible route, not an approval;
- identify that the facts are hypothetical and applicant-supplied;
- find two answers used for the result;
- find a source-status label and an official citation; and
- observe that the unknown material fact produces a staff question or
  abstention instead of a favorable route.

### Task S2: interpret packet readiness

Read this task exactly:

> Open the synthetic packet-readiness sample. Identify one item marked
> "Reported missing," one item marked "Needs confirmation," and the next
> action shown for each. Find the evidence or source for one requirement.
> Finally, tell me whether an item marked "Reported present" means that the
> document is correct,
> compliant, or accepted by the agency.

Full task success requires the participant to:

- locate the requested "Reported missing" and "Needs confirmation" states;
- identify the displayed next action for both;
- find requirement evidence or a citation; and
- state that "Reported present" does not establish consistency, compliance, legal
  sufficiency, or agency acceptance.

### Staff follow-up

Ask:

1. "What, if anything, could cause staff or an applicant to overread this
   result?"
2. "Which label or next action would you change first for an intake
   conversation?"
3. "What information would staff still need before relying on this in a real
   workflow?"

Record these as participant observations, not jurisdiction requirements or
institutional approval.

## Applicant and designer usability study, 25 minutes

### Session sequence

| Time | Activity |
| --- | --- |
| 0:00 to 3:00 | Welcome, scope, consent, and no-PII reminder |
| 3:00 to 5:00 | ADU experience context using broad categories only |
| 5:00 to 13:00 | Task A1, understand the route and open questions |
| 13:00 to 21:00 | Task A2, act on synthetic packet findings |
| 21:00 to 24:00 | Confidence ratings and applicant-specific follow-up |
| 24:00 to 25:00 | Final comment and close |

### Context questions

Ask only:

1. "Which broad description fits you best: homeowner considering an ADU,
   homeowner who prepared or submitted one, designer, or permit
   professional?"
2. "Before today, how familiar were you with California ADU permitting: not at
   all, a little, somewhat, or very?"

Do not ask for a property address, jurisdiction, client, or real application.

### Task A1: find a route and know what to verify

Read this task exactly:

> Imagine the made-up facts in the hypothetical detached ADU sample describe
> your project. In your own words, tell me what route the page found, whether
> that means the project is approved or eligible, and what you would do next.
> Show me where you would check the source. Then edit the answer to "What
> dwelling exists on the lot now, or is proposed?" to "I'm not sure," submit
> again, and tell me what you would ask local staff.

Full task success requires the participant to:

- identify the candidate route without describing it as approval or final
  eligibility;
- find a suggested next step and the source or evidence disclosure;
- change the material fact and resubmit; and
- identify the resulting direct question or need to confirm the fact with
  staff.

### Task A2: decide what to prepare next

Read this task exactly:

> Open the synthetic packet-readiness sample. Tell me which material you would
> work on first and why. Find one item labeled "Needs confirmation" and
> explain the question you would bring to staff. Then tell me whether this
> page says the sample packet is complete, compliant, or ready for agency
> acceptance.

Full task success requires the participant to:

- choose a displayed "Reported missing" item and connect it to its stated
  remedy;
- identify a "Needs confirmation" item and its direct question;
- avoid treating "Reported present" as proof of correctness or compliance;
  and
- avoid describing the sample as an agency-approved completeness finding.

### Applicant and designer follow-up

Ask:

1. "Which phrase, status, or instruction was hardest to understand?"
2. "What would you expect to happen after this screen?"
3. "What information would you still need from local staff?"

Record professional participants' suggestions as opinions based on their
experience, not as controlling requirements.

## Moderator consent and observation script

### Opening and consent

Read this script:

> Thank you for joining. I am evaluating a prototype, not you. This session
> will take about 25 minutes and uses only made-up ADU information. The
> prototype provides candidate information and is not legal advice, an
> approval, or a complete local checklist.
>
> Please do not share any real address, parcel number, application number,
> drawing, client information, employer, jurisdiction, or confidential work
> material. I will take structured notes using a participant code. I will not
> make an audio or video recording. Participation is voluntary. You may skip a
> question or stop at any time.
>
> De-identified observations may be summarized in product documentation or an
> Intent to Showcase submission. Your name, contact information, employer, and
> jurisdiction will not be included. Do you consent to participate and to
> de-identified note taking?

Record `yes` or `no`. End the session if the answer is not `yes`.

Then ask:

> May I include a short, de-identified quotation from you if one is useful?
> Saying no will not affect your participation.

Record quote consent separately. Do not treat general participation consent as
quote consent.

### Think-aloud instruction

Read:

> As you work, please say what you are looking for, what you expect to happen,
> and what you think the page means. I may remind you to keep talking, but I
> will not teach you how to complete the task until the task ends.

### Neutral observation prompts

Use only when needed:

- "What are you looking for now?"
- "What do you expect that control to do?"
- "What does that phrase mean to you?"
- "What makes you say that?"
- "What would you do next?"

Do not say where an answer is, praise a choice, correct an interpretation
during the timed task, or ask a leading question. After time is stopped, the
moderator may explain a safety-critical misunderstanding and record that the
explanation occurred.

### Closing

Read:

> That completes the study. This was formative feedback on a tested prototype,
> not a review of a real project or a request for agency endorsement. Please do
> not rely on anything shown today for a real application. Is there one final
> observation you want included?

## Measures and scoring

Record measures per task, not only per participant.

### Task success

Use this scale:

- `independent success`: all required success criteria completed without a
  directional hint;
- `assisted success`: all required criteria completed after one neutral
  reminder or one directional hint;
- `partial`: at least one required criterion completed, but one or more
  critical criteria missed;
- `not completed`: no critical criterion completed, the participant gives up,
  or the time cap is reached; and
- `not observed`: task omitted because of a technical or protocol problem.

A neutral think-aloud reminder is not assistance. A statement that identifies
the control, section, or answer is assistance and must be recorded.

### Time on task

- Start when the moderator finishes reading the task.
- Stop when the participant states they are done or the eight-minute task
  window ends.
- Record minutes and seconds.
- Keep setup, consent, follow-up questions, and moderator explanation outside
  task time.
- Report the median and range only when at least three people completed the
  same task in a cohort. Always show the denominator.

### Errors

Record each observed error once per task using these codes:

| Code | Observed error |
| --- | --- |
| `CANDIDATE_AS_APPROVAL` | Treats a candidate route as approval or final eligibility |
| `HYPOTHETICAL_AS_REAL` | Treats made-up or applicant-supplied facts as verified parcel facts |
| `SOURCE_STATUS_MISREAD` | Treats stale, unverified, or review-pending material as reviewed current guidance |
| `UNKNOWN_ASSUMED_FAVORABLE` | Expects an unknown material fact to preserve a favorable route |
| `EVIDENCE_NOT_FOUND` | Cannot locate source status, citation, or evidence |
| `PRESENT_AS_COMPLIANT` | Treats document presence as proof of consistency, compliance, or acceptance |
| `STAFF_REVIEW_MISSED` | Misses or resolves an item that the sample routes to staff |
| `NEXT_ACTION_NOT_FOUND` | Cannot identify the displayed remedy or next action |
| `NAVIGATION_ERROR` | Takes an unintended path and cannot recover without assistance |
| `TECHNICAL_ERROR` | Browser, connection, or prototype failure prevents observation |

Record what happened before assigning a code. Do not infer an error solely
from silence.

### Confidence

After each task, ask:

> On a scale from 1 to 5, how confident are you that you understood what the
> page says and what you would do next? One means not confident and five means
> very confident. What is the main reason for your rating?

Confidence is self-report, not evidence of correctness. Report confidence
beside observed task success and errors, never as a substitute for them.

## Session evidence template

Create one de-identified record per completed or attempted session:

```markdown
# Session [S01 or A01]

- Cohort: [staff | applicant/designer]
- Participant role category: [broad category only]
- California ADU exposure: [frequency or familiarity category]
- Session date: [YYYY-MM-DD]
- Time zone: [time zone]
- Product commit: [full 40-character SHA]
- Hypothetical sample location: [URL or path]
- Packet-readiness sample location: [URL or path]
- Method: [moderated remote screen share]
- Browser and device category: [no unique device identifiers]
- Moderator: [researcher name or project role]
- Note taker: [researcher name, project role, or none]
- Participation and note consent: [yes | no]
- De-identified quote consent: [yes | no]
- Recording: none
- Protocol deviations: [none or description]

## Task S1 or A1

- Start and stop time:
- Task duration:
- Success: [independent | assisted | partial | not completed | not observed]
- Assistance given:
- Errors:
- Confidence rating and reason:
- Observations in sequence:

## Task S2 or A2

- Start and stop time:
- Task duration:
- Success: [independent | assisted | partial | not completed | not observed]
- Assistance given:
- Errors:
- Confidence rating and reason:
- Observations in sequence:

## Follow-up

- Participant statements:
- De-identified quotation, only if separately permitted:
- Moderator observations:
- Researcher interpretation, labeled as interpretation:
- Safety-critical misunderstanding explained after timing:
- Technical issue:

## Findings

- Supported finding:
- Contrary or ambiguous evidence:
- Recommended product or copy change:
- Evidence needed before making a broader claim:
```

Do not put recruitment contact information in a session record. Store only
records that have been checked for accidental personal or confidential
information.

## Synthesis and claim rules

1. Preserve separate staff and applicant or designer results.
2. Show raw counts and denominators, such as "3 of 4 completed the task
   independently." Do not use a percentage without the count.
3. If fewer than three sessions are completed in a cohort, report individual
   formative observations and do not aggregate that cohort.
4. Separate observed behavior, participant statement, and researcher
   interpretation in every finding.
5. Retain disconfirming and ambiguous observations. Do not discard them to
   create a favorable narrative.
6. Report the tested commit, task, sample, method, dates, and participant
   profile with every synthesis.
7. Treat staff participation as individual research, not institutional
   endorsement, legal review, jurisdiction approval, or acceptance of an
   interpretation.
8. Treat applicant and designer participation as usability observation, not
   proof that the product improves real application outcomes.
9. Do not describe either study as a pilot, validation by a jurisdiction,
   representative research, or a generalized California outcome.
10. Do not claim reduced permit time, reduced rework, improved completeness,
    staff time savings, legal accuracy, accessibility conformance, or
    translation quality from these sessions.
11. Use "observed in this small formative study" rather than "proved,"
    "validated," "users want," or "California staff agree."
12. A professional participant's opinion does not change a published rule,
    source status, or explanation review status. Rule or copy changes must
    follow the repository's normal evidence and review controls.
13. A usability success does not establish legal fidelity. A confidence score
    does not establish task accuracy.
14. If the product changes after a session, identify which findings apply only
    to the earlier commit. Do not represent an untested revision as observed.
15. Use quotations only with separate quote consent and after removing details
    that could identify the participant or organization.

A permissible submission statement would be:

> In [count] moderated formative sessions conducted from [dates] against
> commit [SHA], [count] of [denominator] participants in the [cohort] cohort
> completed [named task] independently. These observations concern the tested
> synthetic workflow only. They are not a jurisdiction pilot, legal review, or
> evidence of permitting outcomes.

Use that statement only after replacing every bracket with recorded evidence.

## Recruitment copy

Do not post recruitment copy until the study artifacts, consent procedure, and
available session times are confirmed.

### LinkedIn, staff

> I am recruiting 3 to 5 current or recent California planning, building, or
> permit-intake staff for a 25-minute remote usability study of Permit
> Bearings, a tested ADU permitting prototype. Sessions use only made-up
> project information. I will not ask for an agency endorsement, a real case,
> confidential material, or legal advice. The study is planned for August 3
> through August 6. If your work includes ADU routing or application intake
> and you are interested, please send me a direct message. Participation is
> individual and will not be presented as your jurisdiction's approval.

### LinkedIn, applicants and designers

> I am recruiting 3 to 5 adults who have considered, designed, prepared, or
> submitted a California ADU project within the last three years for a
> 25-minute remote usability study of Permit Bearings. The study uses a
> made-up project and synthetic packet, not your address, drawings, or permit
> file. It does not provide legal or project advice. Sessions are planned for
> August 3 through August 6. Homeowners, designers, and permit professionals
> may send me a direct message if interested.

### Bluesky, staff

> California planning, building, or permit-intake staff: seeking 3 to 5 people
> for a 25-minute remote ADU prototype usability study, Aug. 3 to 6. Synthetic
> facts only. No real cases, confidential material, legal advice, agency
> endorsement, or jurisdiction approval. Reply or DM if interested.

### Bluesky, applicants and designers

> California ADU applicants, designers, and permit professionals: seeking 3 to
> 5 people for a 25-minute remote prototype usability study, Aug. 3 to 6.
> Made-up project and packet only. No address, drawings, permit file, or legal
> advice. Reply or DM if interested.

## Schedule through August 9, 2026

| Date | Activity and exit condition |
| --- | --- |
| July 29 | Finalize this protocol, participant criteria, consent script, task rubric, and session evidence template. |
| July 30 | Verify both synthetic samples, complete an internal dry run, confirm available session times, and publish recruitment copy. |
| July 31 to August 2 | Screen against inclusion and exclusion criteria, schedule participants and backups, assign participant codes, and keep contact details outside the repository. |
| August 3 | Lock and record the tested product commit and sample locations. Repeat the dry run after the lock. Begin staff sessions. |
| August 3 to August 5 | Conduct 3 to 5 staff sessions. Check each session record for completeness and accidental PII on the same day. |
| August 4 to August 6 | Conduct 3 to 5 applicant and designer sessions. Check each session record for completeness and accidental PII on the same day. |
| August 6 | Close data collection. Record recruited, scheduled, completed, withdrawn, excluded, and technically interrupted counts for each cohort. |
| August 7 | Score tasks, verify timings and error codes, separate observations from interpretations, and retain contrary evidence. |
| August 8 | Synthesize each cohort separately. Draft bounded findings with raw counts, tested commit, dates, and method. Classify changes by impact and effort. |
| August 9 | Complete a claim review. Remove unsupported generalizations, verify that no study is called a pilot or jurisdiction validation, and freeze any submission language supported by the recorded evidence. |

If recruitment or sample readiness misses this schedule, report the shortfall.
Do not fabricate a participant, session, result, quotation, task count, or
outcome to fill the gap.
