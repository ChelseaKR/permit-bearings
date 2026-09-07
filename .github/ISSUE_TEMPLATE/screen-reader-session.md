---
name: Report a screen-reader, keyboard, or print session
about: You walked part of the prototype with assistive technology and can say what happened
title: "[a11y session] <page> · <your screen reader + browser>"
labels: ["accessibility", "help wanted"]
---

<!--
docs/MANUAL-VALIDATION.md holds a prepared matrix of 21 version-bound human
checks: keyboard, VoiceOver/Safari, NVDA, physical iOS and Android, zoom and
reflow, forced colors, three print browsers, and a PDF assistive-technology
review. Every human row reads `not_run`. Automated axe, Lighthouse, reflow and
print-media checks are separate evidence and cannot promote any of those rows.

You do not need to be an accessibility expert. You need a screen reader you
already use, or a keyboard, or a printer.

READ THIS BEFORE YOU SPEND TIME, because it is the honest part:

  A session report from you is genuinely useful and will be read and acted on.
  It will NOT, on its own, move a row in docs/MANUAL-VALIDATION.md from
  `not_run` to `pass`. That record is bound to an exact deployed commit and
  deployed URL, and both are still `null` because no run has been executed
  against a frozen deployment. Until the maintainer fills that lock, your
  session is evidence and a source of filed defects rather than a completed
  matrix row.

  That is not a reason to skip it. Defects found now are cheaper than defects
  found during a partner's beta. But nobody should discover after an afternoon
  that their work could not be recorded where they expected.

ONE PAGE IS A WHOLE CONTRIBUTION. Try the live prototype at
https://chelseakr.github.io/permit-bearings/ and walk one thing: the landing
page, the screening form on check.html, the packet view on prepare.html, the
evidence page, or the printed output. 15 to 40 minutes each. The screening
form is the interesting one, because it is where an applicant answers
questions and gets a result.
-->

## What you walked

- **Page (paste the URL):**
- **Language:** <!-- en / es. Spanish is explicitly review-pending and outside any beta claim; a session on it is still useful. -->
- **How long it took you:**

## Your setup

A screen reader and a browser fail as a pair, not separately, so both versions
matter. So does the device, for the reflow and touch questions.

- **Screen reader + version:** <!-- e.g. VoiceOver on macOS 15.3, NVDA 2024.4, TalkBack 15 -->
- **Browser + version:**
- **Operating system + version, and physical device if it was a phone:**
- **Keyboard only, screen reader, print, or forced colors:**
- **If you tested reflow:** viewport or zoom level

## What happened

<!--
Describe what you did and what you heard or saw, in order. Quote what was
announced where you can, including the parts that were wrong.

Please do NOT tell us whether the page conforms to anything. That judgement
belongs to the record and to whoever signs it, and a report that leads with
"looks fine" is a report that gets nodded through. Say what happened.
-->

## Where it stopped, or got hard

- [ ] I completed the task
- [ ] I completed it, but it was harder than it should have been
- [ ] I could not complete it
- [ ] I could not tell whether it worked

<!--
"I could not tell" is a real answer and it is wanted as itself. The record's
own rule is that `not_run` stays until every required field exists, and that a
`pass` is never used for a partial workflow, an automated result, an informal
spot check, or a visual inspection standing in for assistive-technology
review. The same honesty applies to your report.
-->

## If you used the screening form

This is the part an applicant actually uses, so these are the questions worth
answering if you got to them:

1. Could you complete the screening with the keyboard alone, and did you always
   know which question you were on?
2. When a result came back, were the **unknowns and the questions for staff**
   announced as clearly as the answers were? This tool's whole posture is that
   it does not determine eligibility and routes unresolved questions to staff;
   if that framing is audible only to a sighted reader, that is a serious
   finding.
3. Did anything read as more certain than it is? The explanations are
   AI-assisted and review-pending drafts and are labelled as such.

## How you want to be credited

- **Name, handle, or organisation to record:**
- [ ] Record me by name
- [ ] Record a handle or an organisation instead
- [ ] Do not record me

<!-- Nobody will push you to be named. See docs/HELP-WANTED.md for the open
question about what a credit line should be allowed to say. -->

## Did you walk another project in the same sitting?

A session report is portable. Several projects in this portfolio are each
blocked on a manual screen-reader and keyboard pass and none has ever had one:

- permit-bearings (this repo), the manual rows in `docs/MANUAL-VALIDATION.md`
- homeroom #6
- tods-validate #74 and #184
- ctdl-validate #54
- fare-policy-assistant #201
- gauntlet #35

File the detail wherever you did the most, and link that issue from the others.

- **Other session reports:**
