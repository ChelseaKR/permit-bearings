# Woodland content-review protocol

Status: prepared, not executed
Protocol version: 1.0.0
Prepared: 2026-08-02

This protocol defines two independent reviews of the AI-assisted Woodland
checklist mapping and action drafts. No reviewer has been recruited or
qualified, no review has been run, and no mapping or action has received a
human, planner, counsel, or jurisdiction disposition.

The machine-readable review record is
`data/validation/woodland-content-review.json`. Every outcome in that record
is intentionally `null`; both reviewer slots are `not_run`, and the known
completed-reviewer count is zero. Preparing the record is not external
validation and does not change the existing
`prototype_review_pending` product status.

## Baseline provenance and artifact lock

`baseline_provenance` records where the blank review package came from. It is
not the execution lock and must not be rewritten when a later deployment is
frozen. The baseline binds the following content identifiers:

- baseline product commit:
  `18d6af3b72e83538c32fbad91e43a0c4636652a8`;
- workflow `woodland-preapproved-detached-adu` and mapping version `1.1.0`;
- workflow fingerprint
  `sha256:66013f9f75ba247e23ede5241639ee5f443d1b40205a1777565b13418c6b8df5`;
- action-draft version `1.0.0` and content fingerprint
  `sha256:3e49650e15f812f4ce0dfc13caa57b0ea9d20649a24b19b79ef4cca1be804787`;
- journey `woodland-preapproved-detached-adu-synthetic`, version `1.0.0`,
  fingerprint
  `sha256:6a7734b8bc920ec13898e2c8c753ce57d27652a5d37c8a41d433798318c4641a`;
- City of Woodland checklist digest
  `59ebf082a59ff257f104a13f75d63faa869565bfdecc33a6e1eba306b4796d62`;
  and
- Yolo County parcel-layer metadata digest
  `5f99beaf208dc10d8794df0ce1cd3d66f7414ac062d81cbdc018403ef01badb5`.

The separate `artifact_lock` repeats those exact content, journey, and source
bindings for the version that may be executed. Its current status is
`pending`, and its execution commit, deployed URL, freeze date, and freeze
owner code are all `null`.

Before either reviewer begins, make one atomic lock transition:

1. verify that the proposed deployment still has every recorded workflow,
   action, journey, and source fingerprint;
2. change the lock status to `locked`;
3. record the full 40-character execution commit;
4. record the exact public HTTPS URL used by both reviewers;
5. record the ISO freeze date; and
6. record a non-identifying freeze-owner code.

The root state then becomes `locked_not_executed`; reviewer slots and all row,
cross-cutting, synthesis, and gate outcomes remain blank. Do not combine
reviews of different versions. If bound content changes after a reviewer
starts, close that run as superseded and create a fresh lock rather than
editing the reviewed snapshot.

## Evidence-state transitions

The validator accepts only these complete states:

| Root state | Artifact lock | Reviewer and outcome evidence |
|---|---|---|
| `prepared_not_executed` | `pending`; lock identity is entirely `null` | Reviewer slots are `not_run`; completed count is `0`; outcomes are `null`. |
| `locked_not_executed` | Fully `locked` with commit, URL, date, owner code, and exact bindings | Reviewer slots remain `not_run`; completed count is `0`; outcomes remain `null`. |
| `review_complete` | Fully `locked` | Both reviewer receipts, all 25 row decisions, all five cross-cutting decisions, every synthesis receipt, and the computed gate are complete. |

Partial locks, partial reviewer receipts, mixed-version commits, populated
outcomes in an unexecuted state, and hand-written gate promotions are invalid.
Reviewers may work on separate private copies, but the committed execution
record is added only when both independent passes and reconciliation are
complete.

## Reviewer roles

Two people review the same 25 rows independently:

1. **R1** must know the Woodland checklist or its permit-intake workflow.
2. **R2** may be a California ADU designer, permit professional, intake
   practitioner, or other professional with recent packet-preparation
   experience.

Participation by a government employee is individual unless written authority
says otherwise. It is not agency endorsement or jurisdiction approval. Record
the reviewer, relevant qualification, method, and date only with permission;
keep contact information, scheduling messages, and raw notes outside the
repository.

Do not show either reviewer the other person's decisions before both
independent passes are locked. A repository contributor who drafted the
mapping or this protocol cannot fill an external reviewer slot.

## Materials

Give each reviewer the same locked materials:

- `corpus/woodland/preapproved-adu-permit-checklist.pdf`;
- `corpus/yolo/public-parcels-layer.json` for the two field-binding checks;
- `data/readiness/workflows/woodland-preapproved-detached-adu.json`;
- `data/readiness/remedies/woodland-preapproved-detached-adu.json`;
- the deployed synthetic route-to-packet journey; and
- a copy of the blank 25-row matrix without the other reviewer's answers.

Use only public, synthetic, or properly redacted material. Do not introduce a
real address, APN, applicant packet, permit number, client file, or confidential
jurisdiction record.

## Independent review procedure

For every row, the reviewer must inspect the official source passage before
classifying either the mapping or the action draft.

1. Confirm the requirement ID and fingerprint belong to the locked workflow.
2. Compare the locator and excerpt with the official checklist page.
3. Evaluate the label, category, item type, parent relationship, and every
   applicability condition.
4. Evaluate the action separately. Confirm it preserves the source condition,
   gives only a preparation step or staff question, and does not imply that a
   document is correct, compliant, complete, accepted, or approved.
5. Mark whether the row contains a blocking content defect and record concise
   evidence for any proposed change, staff route, or suppression.
6. Complete the non-counted cross-cutting checks for the three-fact
   applicability gate, both parcel-field bindings, unknown-state behavior, and
   the prototype claim boundary.

After both independent passes are locked, compare the row dispositions,
calculate initial agreement, and reconcile every disagreement. Preserve the
initial decisions; do not overwrite them with the final disposition.

Each completed reviewer slot must name the reviewer, qualification summary,
method, review date, exact execution commit, and an independence attestation.
Each completed row decision must include a source-based evidence note. A
`changes_required` mapping must include the full proposed mapping, and a
`changes_required` action must include the proposed action text. Other
dispositions cannot carry a proposal.

## Answer key and scoring rules

The record's canonical snapshot is a **scoring key**, not a substantive claim
that the AI draft is correct. There is no human-reviewed answer key yet. The
official source and the review method determine the disposition.

A mapping is `supported` only when all of these are true:

- the source ID, locator, and excerpt identify the reviewed source passage;
- the label does not add or omit a consequential requirement;
- category, item type, and parent relationship preserve the checklist's
  structure;
- every conditional phrase is represented by the correct fact and value; and
- the mapping does not transform document presence into correctness,
  compliance, completeness, acceptance, approval, or legal sufficiency.

An action is `supported` only when all of these are true:

- it stays within the source-backed requirement;
- it preserves conditional or uncertain language;
- it asks staff when the source does not support an affirmative instruction;
- it does not imply eligibility, approval, compliance, completeness, or agency
  acceptance; and
- it remains a preparation aid rather than a legal or technical determination.

Use these mapping and action dispositions:

| Value | Meaning |
|---|---|
| `supported` | The locked draft meets the scoring rules without a content edit. |
| `changes_required` | The source supports the concept, but the mapping or action needs a bounded correction. |
| `blocked_by_source` | Available evidence cannot support a safe disposition. |
| `route_to_staff` | The applicant-facing result must remain an explicit staff question. |
| `suppress` | The mapping or action must not appear in applicant-facing guidance. |

Use `none` or `blocking` for an executed blocking-defect decision. Until a
review is executed, the entire decision object remains `null`.

A blocking content defect is any of the following:

- an unsupported requirement or consequential omission;
- an incorrect applicability condition;
- a source mismatch;
- an action that implies approval, compliance, completeness, acceptance, or
  legal sufficiency; or
- an unknown fact treated as favorable.

For each row, initial agreement is `true` only when both reviewers
independently choose the same mapping disposition **and** the same action
disposition. It is `false` when either differs. Two reviewers can agree that a
defect exists, so initial agreement is not itself an acceptance decision.

Final row dispositions are `retain`, `revise`, `route_to_staff`, or `suppress`.
The synthesis must also record whether a blocking defect remains and a
resolution receipt containing the method, known source IDs, resolver code,
date, and note. An unapplied `revise` disposition remains blocking and cannot
pass the frozen artifact. Cross-cutting checks use the same logic but are not
included in the 25-row agreement denominator.

## Thresholds

The content gate requires all of the following before applicant testing:

- two independent qualified reviewers complete every row and cross-cutting
  check;
- at least 22 of 25 rows receive initial reviewer agreement;
- every disagreement is resolved through better sourcing, a bounded revision,
  suppression, or explicit staff routing; and
- zero known blocking content defects remain in the frozen build.

The unexecuted gate records the administratively known completion counts as
zero and leaves outcome counts and booleans `null`. A completed gate is
derived from the recorded decisions: two reviewers, 25 rows, five
cross-cutting checks, initial agreements, disagreements, and remaining
blocking defects. It is `passed` only when at least 22 rows agree and no
blocking defect remains; otherwise it is `failed`. A blank gate must never be
described as failed or passed. Agreement below 22 of 25 does not authorize
averaging, informal adjudication, or combining a revised version with the
original review.

## Reconciliation and publication

For a revised row, record the exact changed field or action, source passage,
resolution method, responsible person, date, and new version-bound
fingerprint. For a staff-routed or suppressed row, preserve the reason. Re-run
the repository verification suite after any canonical content change.

Do not promote the aggregate workflow or remedy status from
`prototype_review_pending` unless the completed evidence names the reviewer,
method, date, exact reviewed version, and matching content fingerprint. Two
individual reviews do not become `jurisdiction_approved` without explicit
institutional authorization.

Permissible language before execution is limited to:

> A version-bound two-reviewer protocol and 25-row disposition matrix are
> prepared. Both reviews and every outcome remain pending.

Do not claim that the mappings were reviewed, validated, approved, accepted,
or shown accurate merely because this protocol and empty record exist.
