# Manual accessibility and language validation record

Status: prepared, not executed  
Record version: 1.0  
Prepared: 2026-07-30

This record defines the human checks required before Permit Bearings can
describe its public interface or Spanish guidance as applicant-ready. It does
not record a completed accessibility audit, WCAG conformance determination,
Spanish semantic-parity review, or legal review.

Automated axe, Lighthouse, schema, and regression results remain separate
evidence. A person must perform and sign each check below. Failed and blocked
checks remain visible; they are not converted to passes by changing interface
copy.

## Evidence rules

For every executed check, record:

- check ID and page or content version;
- result: `pass`, `fail`, or `blocked`;
- tester or reviewer name;
- test date;
- operating system and version;
- browser and version;
- assistive technology, input method, display setting, or language-review
  method;
- concise observations and reproduction steps;
- linked defect or follow-up when the result is not `pass`.

Use `not_run` until all required evidence exists. Do not use `pass` for a
partial workflow, an automated result, or an informal spot check.

## Public-page task matrix

| Check ID | Page | Required human task | Current result |
|---|---|---|---|
| KB-INDEX | `index.html` | Use the skip link and primary navigation without a pointer; verify visible focus and logical order. | `not_run` |
| KB-CHECK | `check.html?sample=adu` | Complete, edit, clear, and resubmit the sample using only the keyboard; operate every disclosure and follow every result jump link. | `not_run` |
| KB-PREPARE | `prepare.html` | Reach the packet summary, source record, missing items, staff questions, disclosures, and manifest link using only the keyboard. | `not_run` |
| KB-REVIEW | `review.html` | Enter ordinance text, run the screen, reach the result summary and findings, and recover from an empty submission using only the keyboard. | `not_run` |
| KB-EVIDENCE | `evidence.html` | Run and reset the source-change rehearsal, follow the affected-result link, and verify focus placement and status announcements. | `not_run` |
| SR-CHECK | `check.html?sample=adu` | With VoiceOver/Safari and separately NVDA/Firefox or NVDA/Chrome, verify landmarks, headings, field names, conditional questions, errors, answers-used summary, result groups, source status, and disclosure reading order. | `not_run` |
| SR-PREPARE | `prepare.html` | Verify loading status, packet summary, finding counts, missing and unresolved items, source evidence, disclosure names, and manifest-link purpose with a screen reader. | `not_run` |
| SR-TOOLS | `review.html` and `evidence.html` | Verify live-region timing and verbosity for scan results and the source-change rehearsal; confirm that changed status is not conveyed by color alone. | `not_run` |
| REFLOW-ALL | All five pages | Test browser zoom at 200% and 400%, then a 320 CSS-pixel viewport; verify no loss of content or function and no document-level horizontal scrolling. | `not_run` |
| TOUCH-IOS | `index.html`, `check.html?sample=adu`, and `evidence.html` | On a physical iPhone using Safari, open and close the section menu, complete and edit the sample with the virtual keyboard, operate disclosures, and scan the labeled evidence records at 320px-equivalent and 390px-equivalent widths. | `not_run` |
| TOUCH-ANDROID | `index.html`, `check.html?sample=adu`, and `evidence.html` | On a physical Android phone using Chrome, open and close the section menu, complete and edit the sample with the virtual keyboard, operate disclosures, and scan the labeled evidence records at a narrow and a common phone width. | `not_run` |
| TEXT-SPACING | All five pages | Apply WCAG text-spacing overrides and verify that text is not clipped, overlapped, or made inoperable. | `not_run` |
| CONTRAST-MODE | All five pages | Test forced-colors or a comparable high-contrast mode; verify focus, controls, links, disclosures, and status distinctions. | `not_run` |
| MOTION | `check.html` and `evidence.html` | Enable reduced motion and verify that navigation and result updates remain understandable without smooth scrolling. | `not_run` |
| ES-PRONUNCIATION | `check.html` | With the page in Spanish, verify language switching, pronunciation, English-source `lang` boundaries, and understandable mixed-language transitions with a Spanish-capable screen reader voice. | `not_run` |

Keyboard and screen-reader runs must include both successful and error or
unknown-input paths. Record defects independently from this table; the table
records the result of the tested version, not the eventual intention to fix
it.

## Run record template

Copy this block once for each executed check:

```text
Check ID:
Result: not_run | pass | fail | blocked
Tester:
Date:
Commit or deployed URL:
OS/device:
Browser:
Assistive technology or setting:
Task path:
Observations:
Defect/follow-up:
Retest record:
```

## Spanish semantic-parity review

Interface localization and source-derived guidance are separate review
surfaces. A fluent or qualified reviewer must compare each Spanish
explanation with its English explanation and cited source evidence.

For every reviewed rule, record:

- stable `source_rule_id`;
- explanation `version`;
- English localized-content fingerprint;
- Spanish localized-content fingerprint;
- citation fingerprint and full-rule fingerprint;
- reviewer name and relevant language/domain qualification;
- review method and date;
- disposition: `approved`, `changes_required`, or `blocked_by_source`;
- each meaning, threshold, exception, legal-term, and next-action difference.

The review is incomplete if it checks only fluency or interface labels. It
must separately examine:

- applicant consequence and uncertainty;
- every number, deadline, threshold, and condition;
- negative and exception language;
- legal terms that remain untranslated or are defined differently;
- questions and escalation instructions;
- whether stale or unverified evidence is handled identically.

Only after that review may the exact Spanish record move from
`machine_draft` to a completed review status. The record must contain the
reviewer, method, date, reviewed version, and matching content fingerprint.
English content/legal review remains independent and must not be inferred
from Spanish approval.

## Exit criteria

Human validation is complete only when:

1. every matrix row has a signed `pass` record for the commit or deployment
   being accepted;
2. every failed or blocked result has been fixed and retested, or remains
   explicitly open without an applicant-ready claim;
3. screen-reader coverage includes VoiceOver/Safari and one NVDA/browser
   combination;
4. Spanish source-derived guidance has rule-by-rule semantic-parity evidence
   bound to exact versions and fingerprints; and
5. `docs/ACCESSIBILITY.md`, `docs/I18N.md`, the capability matrix, README, and
   public labels accurately reflect the completed and still-open work.
