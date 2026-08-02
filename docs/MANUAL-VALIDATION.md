# Manual accessibility, print, and language validation record

Status: prepared, not executed  
Record version: 1.0.0
Prepared: 2026-08-02

The canonical machine-checkable record is
[`data/validation/woodland-manual-evidence.json`](../data/validation/woodland-manual-evidence.json).
It defines the human checks required before Permit Bearings can describe the
public synthetic Woodland route-to-packet journey, its printed artifact, or
its Spanish guidance as applicant-ready.

This record does **not** report a completed accessibility audit, WCAG
conformance determination, physical-device test, printed-output review,
accessible-PDF result, Spanish semantic-parity review, applicant study, legal
review, or jurisdiction approval. Every human result remains `not_run`.
Automated axe, Lighthouse, reflow, print-media, schema, fingerprint, and
regression checks are separate evidence and cannot promote a row in this
record.

## Exact synthetic artifact under review

The prepared matrix is bound to one public synthetic fixture. The execution
lock remains unfilled until a human run records both the exact deployed commit
and deployed URL.

| Lock | Prepared value |
|---|---|
| Sample entry | `check.html?sample=adu` |
| Valid packet entry | `prepare.html?journey=woodland-preapproved-detached-adu-synthetic&version=1.0.0` |
| Journey ID / version | `woodland-preapproved-detached-adu-synthetic` / `1.0.0` |
| Journey fingerprint | `sha256:6a7734b8bc920ec13898e2c8c753ce57d27652a5d37c8a41d433798318c4641a` |
| Screening-case fingerprint | `sha256:3171705791a2520132e727c9d39d6f0bc710d7114e6408c0bfd2af6ebb3d754b` |
| Fact-envelope fingerprint | `sha256:18c9bf3bdf525776352301b3150185fce8cdb0882b621d61f92eabcc25036847` |
| Workflow fingerprint | `sha256:66013f9f75ba247e23ede5241639ee5f443d1b40205a1777565b13418c6b8df5` |
| Packet fingerprint | `sha256:dd9ed173d0e87e44b713d9133232d5ec8c200826d4264e25e5e7ba4e99c6364e` |
| Tested commit | `null` — no run has been executed |
| Deployed URL | `null` — no run has been executed |

The valid packet URL has exactly the `journey` and `version` parameters.
Direct, missing, duplicate, extra-parameter, mismatched-version, and stale
entries are withheld states, not substitutes for testing the valid journey.
Do not combine, average, or carry forward results from different commits,
journey versions, or fingerprints. A changed lock requires a new run.

## Evidence and transition rules

Use `not_run` until every required field exists. Do not use `pass` for a
partial workflow, an automated result, an informal spot check, a visual PDF
inspection standing in for assistive-technology review, or a fixed defect that
has not been retested against the same locked artifact.

For an executed manual check, record:

- the exact 40-character deployed commit and HTTPS deployment URL;
- check ID, result (`pass`, `fail`, or `blocked`), start and completion time;
- a consented public tester identifier and broad role;
- operating system and version, device, browser and version;
- assistive technology, input method, display setting, print driver, PDF
  viewer, or language-review method;
- the exact successful, error, unknown, and withheld task paths used;
- observations and reproduction steps;
- redacted evidence references;
- defect and retest references when applicable;
- tester attestation and a consented public identifier for the independent
  acceptance reviewer; and
- signoff disposition and dates.

A `not_run` row must retain `execution`, `reviewer`, `evidence`, and `signoff`
as `null`. A non-`not_run` row is invalid unless the artifact lock is
`executed` and contains the exact commit and deployment, and the row contains
a complete execution record, evidence, reviewer, and signoff. `in_progress`
means at least one but not all required manual and Spanish rows has a signed
result. `complete` means every required row has a signed non-`not_run` result,
including unfavorable `fail`, `blocked`, `changes_required`, or
`blocked_by_source` outcomes; it does not mean every check passed. Failed and
blocked checks remain visible and cannot be converted to passes by changing
prose.

## Human task matrix

Keyboard and screen-reader runs include successful, error, unknown-input, and
withheld paths. The journey rows start at the made-up sample, exercise the
unselected applicability gate, and follow the exact versioned packet handoff.

| Check ID | Human method and required surface | Current result |
|---|---|---|
| KB-INDEX | Keyboard-only skip-link, navigation, focus-order, and visible-focus run on `index.html`. | `not_run` |
| KB-JOURNEY | Keyboard-only full route, Yes/No/unknown gate, exact handoff, summary, print control, packet, source, manifest, edit, clear, error, and recovery run. | `not_run` |
| KB-REVIEW | Keyboard-only ordinance input, result, empty-state recovery, focus-order, and visible-focus run. | `not_run` |
| KB-EVIDENCE | Keyboard-only source-change rehearsal, reset, affected link, focus, and status-announcement run. | `not_run` |
| SR-JOURNEY-VOICEOVER-SAFARI | Full journey with VoiceOver/Safari, including names, roles, states, live regions, reading order, summary, packet, sources, disclosures, and manifest. | `not_run` |
| SR-JOURNEY-NVDA | Full journey with NVDA and Firefox or Chrome, covering the same successful and withheld states independently. | `not_run` |
| SR-TOOLS | VoiceOver and NVDA review of live-region timing and non-color status for `review.html` and `evidence.html`. | `not_run` |
| REFLOW-JOURNEY | Full populated journey at 200% and 400% browser zoom and a 320 CSS-pixel viewport, including long IDs, fingerprints, and URLs. | `not_run` |
| REFLOW-OTHER-PAGES | `index.html`, `review.html`, and `evidence.html` at 200%, 400%, and 320 CSS pixels. | `not_run` |
| MOBILE-JOURNEY-IOS | Full journey on a physical iPhone with Safari and the virtual keyboard at recorded narrow and common widths. | `not_run` |
| MOBILE-JOURNEY-ANDROID | Full journey on a physical Android phone with Chrome and the virtual keyboard at recorded narrow and common widths. | `not_run` |
| TEXT-SPACING-ALL | WCAG text-spacing overrides on initial and populated states of all five pages. | `not_run` |
| FORCED-COLORS-JOURNEY | Full journey in Windows forced-colors or a recorded comparable high-contrast mode; verify focus, controls, borders, links, and every status distinction. | `not_run` |
| FORCED-COLORS-OTHER-PAGES | High-contrast run of `index.html`, `review.html`, and `evidence.html`. | `not_run` |
| MOTION | Reduced-motion run of applicant-result navigation and the source-change rehearsal. | `not_run` |
| PRINT-JOURNEY-CHROME | Chrome Print and Save as PDF; inspect isolation, content, links, grayscale, wrapping, pagination, and reading order. | `not_run` |
| PRINT-JOURNEY-SAFARI | Safari Print and Save as PDF; repeat the complete visual and functional printed-output review. | `not_run` |
| PRINT-JOURNEY-FIREFOX | Firefox Print and Save as PDF; repeat the complete visual and functional printed-output review. | `not_run` |
| PDF-AT-JOURNEY | Inspect a saved artifact with a recorded PDF viewer and screen reader for title, tags, structure, order, links, selectable text, IDs, status, and boundary. | `not_run` |
| ES-USABILITY-JOURNEY | Moderated Spanish-language comprehension run against the exact journey version: candidate-not-approval meaning, source status, unknown escalation, explicit English handoff, packet action, staff question, and synthetic boundary. | `not_run` |
| ES-HANDOFF | Verify Spanish state preservation, English source boundaries, explicit English packet label, Yes/No/unknown behavior, exact two-parameter link, and English destination. | `not_run` |
| ES-PRONUNCIATION | Verify Spanish pronunciation and understandable voice changes across English source text and the English packet destination with a Spanish-capable screen-reader voice. | `not_run` |

The three print rows concern visual and functional printed output. They do not
establish an accessible PDF. `PDF-AT-JOURNEY` remains independently
`not_run`; if a browser-generated PDF is untagged or has unusable reading
order, record `fail` or `blocked`, not a visual pass.

## Execution record template

Copy this structure for each run. Do not fill it with inferred, automated, or
undated evidence.

```text
Check ID:
Result: not_run | pass | fail | blocked
Tested commit: [full 40-character SHA]
Deployed URL: [HTTPS URL]
Journey ID and version:
Journey, screening-case, fact-envelope, workflow, and packet fingerprints:
Consented public tester identifier and broad role:
Started at / completed at:
OS/device:
Browser:
Assistive technology, setting, print driver, or PDF viewer:
Task paths:
Observations and reproduction steps:
Redacted evidence references:
Defect/follow-up:
Retest record:
Privacy/redaction confirmation:
Tester attestation date:
Consented public acceptance-reviewer identifier and review date:
Signoff disposition: accepted_for_tested_artifact | rejected | exception_pending
```

## Privacy handling

Use only the repository's public made-up route, generated synthetic packet,
properly redacted defect evidence, and consented public tester or reviewer
identifiers with broad non-identifying role or qualification summaries. Do not
retain private names or attribution details without explicit public-use
consent. Never retain email addresses, phone numbers, handles, scheduling
records, identity-linking details, unauthorized employer or jurisdiction
names, real addresses, APNs, application numbers, drawings, permit files,
client information, credentials, browser profiles, or unredacted screenshots.
Do not record audio, video, or screens. Contact and identity-linking material
stays outside the repository.

Before committing any executed record, a second person must confirm that the
record and linked evidence contain no applicant, private participant,
unauthorized employer or jurisdiction, contact, identity-linking, or
credential data and that each public tester or reviewer identifier has
explicit attribution consent. Until that confirmation is recorded, privacy
status, reviewer, evidence, and signoff remain `not_run` or `null`.

## Spanish-language usability check

`ES-USABILITY-JOURNEY` is a distinct version-bound human task run. It asks a
fluent Spanish-speaking participant to interpret the candidate-route boundary,
source status, unknown escalation, explicit English packet transition, one
packet action, one staff question, and the synthetic not-a-decision boundary
without a product tour. Its outcome is usability evidence only. It cannot
promote a translation, establish semantic fidelity or accessibility, or stand
in for any of the 19 rule-by-rule reviews below.

## Spanish semantic-parity protocol

Interface localization and source-derived guidance are independent review
surfaces. A fluent or qualified reviewer must compare the exact Spanish copy
with its English copy and cited source evidence. Each row is bound to the
version, citation fingerprint, full-rule fingerprint, and computed English
and Spanish localized-content fingerprints stored in the canonical JSON.

The review must separately examine:

- applicant consequence and uncertainty;
- every number, deadline, threshold, and condition;
- negative and exception language;
- legal terms that remain untranslated or are defined differently;
- questions, next actions, and escalation instructions; and
- identical handling of stale or unverified evidence.

| Source rule ID | Explanation version | Current result |
|---|---:|---|
| `adu-ministerial-review` | `1.1.0` | `not_run` |
| `adu-protected-minimum` | `1.1.0` | `not_run` |
| `adu-height-standards` | `1.1.0` | `not_run` |
| `jadu-standards` | `1.1.0` | `not_run` |
| `jadu-ministerial-review` | `1.0.0` | `not_run` |
| `sb9-two-unit-ministerial` | `1.2.0` | `not_run` |
| `sb9-urban-lot-split` | `1.2.0` | `not_run` |
| `adu-size-allowances` | `1.2.0` | `not_run` |
| `adu-parking-limits` | `1.1.0` | `not_run` |
| `adu-no-owner-occupancy-rental` | `1.1.0` | `not_run` |
| `adu-conversion-exemptions` | `1.1.0` | `not_run` |
| `adu-unpermitted-legalization` | `1.1.0` | `not_run` |
| `jadu-unpermitted-legalization` | `1.0.0` | `not_run` |
| `adu-multifamily-66323` | `1.1.0` | `not_run` |
| `adu-multifamily-proposed-66323` | `1.0.0` | `not_run` |
| `sb9-adu-interaction` | `1.1.0` | `not_run` |
| `sb9-lot-split-adu-interaction` | `1.0.0` | `not_run` |
| `davis-local-adu-process` | `1.2.0` | `not_run` |
| `woodland-adu-ordinance-2026` | `1.2.0` | `not_run` |

Allowed review dispositions are `approved`, `changes_required`, and
`blocked_by_source`. Any executed disposition requires a consented public
reviewer identifier, relevant language/domain qualification, method, date,
redacted evidence, and signoff against the exact lock. `approved` is invalid
unless the matching Spanish explanation record is promoted with the same
reviewer identifier, date, version, method, and Spanish content fingerprint.
Conversely, `changes_required` or `blocked_by_source` is invalid if the
matching translation has already been promoted to `human_reviewed` or
`jurisdiction_approved`. English content or legal approval remains independent
and cannot be inferred from Spanish approval.

## Exit criteria

The relevant acceptance claim remains open until:

1. each required matrix row has a signed result for the exact accepted commit,
   deployment, journey version, and fingerprints;
2. every failed or blocked result is fixed and retested or remains explicitly
   open without an applicant-ready or conformance claim;
3. screen-reader coverage includes both VoiceOver/Safari and NVDA with a
   recorded browser;
4. Chrome, Safari, and Firefox printed-output rows and the independent PDF/AT
   row are resolved without conflating their evidence;
5. the distinct Spanish-language usability row has a signed result for the
   same locked artifact;
6. Spanish source-derived guidance has rule-by-rule semantic-parity evidence
   bound to the exact 19 records; and
7. the README, product context, accessibility record, i18n record, capability
   matrix, and public labels accurately distinguish completed and open work.
