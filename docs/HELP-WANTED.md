# Help wanted: what this project cannot build its way out of

Permit Bearings is a prototype decision-support tool for California ADU, JADU,
and SB 9 projects. Structured applicant facts produce candidate routes, relevant
standards, cited official sources, and questions for local staff. The matcher is
deterministic. Live at <https://chelseakr.github.io/permit-bearings/>.

The engineering is not what is blocking it.

## What is not done, and why no amount of code closes it

Read the exit-gate table in [`docs/BETA-ROADMAP.md`](BETA-ROADMAP.md) and the
same phrase keeps appearing in the dependency column: **External jurisdiction.
External reviewers. External recruitment. External partner.**

| Gate | Current state |
|---|---|
| Active scope | No active pilot workflow or sponsor is recorded |
| Content authority | Two reviewer slots `not_run`; no completed content-review claim |
| Review levels | All 19 rules are effectively `machine_linked` |
| Applicant evidence | Six scorecards prepared, `not_run` |
| Problem evidence | No participant evidence exists |
| Human access | All 21 manual rows `not_run` |
| Language | Nineteen semantic-review rows `not_run` |
| Partner and decision | Pending |

Every one of those is prepared. The matrices exist, the validators exist, the
fixtures exist, the record refuses to lie about any of them. What does not exist
is people.

The Woodland flagship is the clearest case. The City's own program page,
checked 2026-09-10, says *"Preapproved ADU List: Coming soon!"* No listed City
plan was identified, so the flagship is a **source-bound future-state
simulation**, not a usable workflow. That is stated on the page, in the README,
and in the evidence ledger. It is not a bug to be fixed in code.

## The one that unblocks twelve others

[**#114**](https://github.com/ChelseaKR/permit-bearings/issues/114): select a
partner jurisdiction and one detached-ADU workflow. Issues #115 through #126
wait behind it.

Step 1 of the roadmap's "Next" phase is two things:

1. the authoritative local source package for one detached-ADU workflow: the
   ordinance, forms, checklist, procedure and agency calendar as that
   jurisdiction actually publishes them;
2. **a named conflict-resolution authority** - because a source package with no
   named authority to settle a conflict cannot produce a defensible answer when
   two documents disagree.

**What this asks for is a conversation, not a procurement.** No money, no
contract, no applicant data, no integration with a permitting system, no
endorsement. The first beta stays public, synthetic or redacted, with no
accounts, uploads, applicant store, telemetry or write-back. `stop` is a real
supported outcome at the end and the roadmap names it as one.

**What one hour buys here:** if you work for a California jurisdiction, or with
one, or you can introduce someone who does, an hour of your time is the
difference between a prototype and a tested beta.
[Open the partner
template](https://github.com/ChelseaKR/permit-bearings/issues/new?template=partner-jurisdiction.md).
An introduction is a complete contribution.

## The one anybody with a screen reader can start today

[`docs/MANUAL-VALIDATION.md`](MANUAL-VALIDATION.md) prepares 21 human checks:
keyboard, VoiceOver/Safari, NVDA, physical iOS and Android, zoom and reflow,
forced colors, three print browsers, and a PDF assistive-technology review.
Every human row reads `not_run`. Automated axe, Lighthouse, reflow and
print-media checks run and are real, and the record is explicit that they
**cannot promote any of those rows**.

**Here is the honest part, and please read it before spending an afternoon.**

A session report from you is genuinely useful and will be read and acted on. It
will **not**, on its own, move a row from `not_run` to `pass`. That record is
bound to an exact deployed commit and deployed URL, and both are still `null`
because no run has been executed against a frozen deployment. Until the
maintainer fills that lock, your session is evidence and a source of filed
defects, not a completed matrix row.

That is not a reason to skip it: a defect found now is far cheaper than the
same defect found during a partner's beta, and the screening form has never
been driven by a screen reader at all. But nobody should discover after the
fact that their work could not be recorded where they expected it to be.

**What one hour buys:** one page walked. The landing page, the screening form
on `check.html`, the packet view on `prepare.html`, the evidence page, or the
printed output. 15 to 40 minutes each. The screening form is the one worth
doing first, because it is where an applicant answers questions and gets a
result, and because of this question:

> When a result comes back, are the **unknowns and the questions for staff**
> announced as clearly as the answers are?

This tool's entire posture is that it does not determine eligibility and routes
unresolved questions to staff. If that framing is visible only to a sighted
reader, the tool is quietly more confident in a screen reader than it is on
screen, and that is a serious finding.

[Open the session
template](https://github.com/ChelseaKR/permit-bearings/issues/new?template=screen-reader-session.md).

## What you get

- **Your name, handle, or organisation recorded** against what you did, at your
  choice. Both templates offer an anonymous option.
- **A dated, citable artifact.** This repository has a `CITATION.cff` and the
  evidence records are committed files at a commit. Manual accessibility work
  and content review usually vanish into private audit documents; here they are
  public and linkable.
- **Findings filed as issues** with your report linked, so what you found has a
  life after the sitting.
- For a partner jurisdiction: a jurisdiction-owned export of sources, rules,
  requirements, review receipts, fixtures and checksums that opens and restores
  without vendor-only tooling.

## A question this project has not answered

Being credited means being named in a public file, and for some people that is
not free. Neither template forces it, and neither invents a policy about what a
credit line may say instead of a legal name. That is the maintainer's call, and
possibly counsel's.

Sibling projects in this portfolio have answered it in opposite directions:
contextsafe's hazard register accepts pseudonymity and publishes no roster
without individual written consent, while trans-docs-navigator requires a named
verifier on a public roster and serves an audience for whom being named carries
real risk. Those cannot both be the right default everywhere, and it should not
be settled in an issue thread.

## Reusing one session across several projects

Several projects in this portfolio are each blocked on a manual screen-reader
and keyboard pass and none has ever had one. One sitting answers the same
question for several, and the report is portable:

- permit-bearings, the manual rows in `docs/MANUAL-VALIDATION.md`
- homeroom, [#6](https://github.com/ChelseaKR/homeroom/issues/6)
- tods-validate, [#74](https://github.com/ChelseaKR/tods-validate/issues/74)
  and [#184](https://github.com/ChelseaKR/tods-validate/issues/184)
- ctdl-validate, [#54](https://github.com/ChelseaKR/ctdl-validate/issues/54)
- fare-policy-assistant,
  [#201](https://github.com/ChelseaKR/fare-policy-assistant/issues/201)
- gauntlet, [#35](https://github.com/ChelseaKR/gauntlet/issues/35)

File the detail wherever you did the most work and link that issue from the
others. Nobody should have to type a session report twice.
