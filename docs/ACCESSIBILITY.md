# Accessibility audit: static and automated browser pass, updated 2026-07-30

Scope: the five-page public static site (`index.html`, `check.html`,
`prepare.html`, `review.html`, and `evidence.html`) and the separate applicant
flow in `demo/app.py`. **Target: WCAG 2.2 Level AAA.**
The static site implements the published California Design System `cagov`
tokens locally: Public Sans-first typography, 18px body copy, 1.75 line
height, state color/status tokens, spacing steps, and the 1,176px shell /
876px reading widths. No State logo, official-site banner, branding, or
affiliation is claimed. See `docs/DESIGN-SYSTEM.md`.

This audit combines static and code-level checks, computed contrast, automated
axe scans of all five public pages, Lighthouse category budgets, and one
limited local browser inspection of the packet sample. Automation found and
remediated invalid ARIA labeling on packet status text and the ordinance
results region. It is not a completed manual or assistive-technology review.
Items under "Remaining" require a person using the named browsers, input
methods, or assistive technology. The executable task matrix and signed-result
requirements are defined in `docs/MANUAL-VALIDATION.md`; every row is
currently `not_run`.

## Static and code checks recorded

**Semantics & structure.** Each page has a skip link, one `<main>`, one
`<h1>`, a labeled primary navigation, and `aria-current` on the active page.
Sections use `<h2>`s. The applicant result cover sheet uses a `<dl>`, its
group index is a labeled `<nav>`, and each nonempty group has a focusable
heading that serves as a jump-link target. Each decision record is an
`<article>` labeled by its unique title. One explicitly configured candidate
route uses an open native `<details>` element when it matches; compact
supporting records start closed. Citations and source-status text remain
outside those disclosures. Tables use `<th>` header rows. Multiple deadlines
or thresholds use a semantic heading and list rather than visual-only layout.
All interactive elements are native controls, so keyboard operability and
focus order come from the platform.

The packet sample has one labeled main region and one page heading. Its
made-up packet cover, finding counts, and source record use definition lists.
Missing and unresolved findings are labeled articles with headings and
visible text states. Reported-present, not-applicable, and not-evaluated
groups use native disclosures. The generated manifest and official checklist
use descriptive links. These observations come from markup, regression
checks, and limited visual inspection; browser reading order and
assistive-technology output remain pending.

## Limited local browser checks recorded

On 2026-07-29, the generated packet sample was inspected in the local in-app
browser at 1280, 390, and 320 CSS-pixel viewport widths. The page had no
horizontal document overflow at those widths, the generated output replaced
its busy state without a visible load error, and the expected headings and
visible trust labels rendered. Computed token contrast checks and spot checks
of link and disclosure target heights were also recorded. This inspection did
not establish keyboard operation, screen reader output, real-device zoom
behavior, or conformance for the other four static pages.

## Automated browser checks recorded

On 2026-07-29, axe-core 4.12.1 reported no WCAG 2.0/2.1/2.2 A, AA, or tagged
AAA violations on `index.html`, `check.html`, `prepare.html`, `review.html`,
or `evidence.html` in a Playwright-managed Chromium build. Lighthouse 13.4.1
reported accessibility 1.00, performance 1.00, SEO 1.00, and best-practices
0.96 for each page against a gzip-enabled local server that mirrors the
production static delivery behavior. CI repeats both checks on pull requests,
default-branch pushes, and weekly. A first performance sample below the 0.90
budget triggers two confirmation samples and evaluates their median; the
budget itself is unchanged.

These automated results cover only rules the tools can evaluate. They do not
establish WCAG conformance, substitute for the remaining keyboard and
screen-reader work, or promote the Spanish machine drafts to reviewed copy.

**Focus appearance (2.4.13, AAA-new).** Global `:focus-visible` uses a 3px
`accent2-300` ring with a 2px offset and a 5px `primary-900` outer ring.
The inner gold is 5.87:1 against the primary surface and the outer blue is
10.68:1 against the page. Two colors keep the indicator visible across white,
gold, and blue components.

**Target size (2.5.5 AAA / 2.5.8 AA).** Buttons, selects, inputs, and
textareas have `min-height: 44px`; checkbox/radio rows get ≥44px hit areas
via label padding. Result evidence summaries also have a 44px minimum target.
Inline text links fall under the in-text exception.

**Motion (2.3.3).** The only animation (smooth scroll to results) is
disabled under `prefers-reduced-motion: reduce`.

**Labels & names.** Visible `<legend>` and `<label>` text for conditional
radio groups; the jurisdiction combobox is named by its visible legend and
described by help and status text. The ordinance textarea and date input have
explicit accessible names; the trust meter has `role="img"` with a
descriptive label. Required applicant facts use explicit Yes / No / “I'm not
sure” choices instead of favorable checkbox defaults.

**Dynamic updates.** A visually hidden status announces the grouped result
summary and boundary text without turning the full result collection into a
live region. This avoids announcing every source excerpt when several records
match. Scan findings, clock output, and jurisdiction status also use
`aria-live="polite"`. The zero-result status includes the full staff-review
routing message instead of announcing only a count. The amendment rehearsal
announces how many matching guidance records were withheld or restored, then
moves focus to the newly available reset/rehearse control. After screening,
keyboard focus moves to the result heading; scanner and clock live regions
announce a concise summary instead of their full result tables or cards.

The packet page marks its generated output `aria-live="polite"` and
`aria-busy="true"` until rendering completes. Static checks confirm those
attributes and the visible loading and error containers. Actual announcement
timing, verbosity, and focus behavior have not been checked with a browser or
screen reader.

The shareable ADU sample is introduced by descriptive link text and followed
by a visible disclosure that identifies the facts as hypothetical. It fills
the same native form controls and invokes the same form submission path as
manual answers, so the existing result-status announcement applies. For the
automatically submitted sample, focus moves to the disclosure instead of
skipping past it to the results. A plainly labeled link clears the sample.
Editing a sample fact relabels the disclosure, removes the sample URL
parameter, and clears the old results until the edited form is submitted.
The same invalidation rule applies to ordinary applicant answers: changing the
jurisdiction or a named project fact removes the rendered result, temporary
answers-used cover sheet, and remembered disclosure state. This prevents a
result from remaining visible beside facts that no longer produced it.

**Data-loading state.** Data-dependent pathway, scanner, and trust-rehearsal
buttons use the native `disabled` state until their datasets are ready. A
load failure places a visible explanation in the relevant results area and a
short message in the result status region instead of leaving empty controls
that appear operable. The packet page also clears its busy state and presents
a visible load error. These behaviors are covered by code inspection and
static tests, not a manual browser failure rehearsal.

**Link purpose (2.4.9 AAA).** Every link's text alone states its target
("view scan findings (JSON)", full source citations, named statutes).

**Not color-alone.** Statuses are icon + word badges; decorative badge glyphs
are hidden from assistive technology, and hue never carries meaning by itself.
The current-source badge is deliberately neutral rather than approval-green.

**Contrast: 1.4.6 Enhanced (7:1 normal text), computed from the adopted
tokens:**

| Pair | Ratio |
|---|---:|
| Black body ink / gray-50 page | 20.12:1 |
| Gray-800 secondary ink / gray-50 page | 8.44:1 |
| Primary-900 link / gray-50 page | 10.68:1 |
| White button text / primary-900 | 11.15:1 |
| Success-900 / success-100 badge | 9.58:1 |
| Warning-900 / accent2-100 badge | 9.57:1 |
| Danger-900 / danger-100 badge | 9.56:1 |

Status meter fills are graphical objects with adjacent text labels; meaning
does not depend on color. The gray-700 form-control boundary is 6.39:1
against its white surface.

**Visual presentation (1.4.8, partial).** Base line height is 1.75; reading
content is capped at the published 876px width; no text is justified; wide
tables scroll in their own labeled region (no page horizontal scroll at
320px). User-selectable colors/spacing beyond browser and OS mechanisms are
not provided.

**Language switching.** The applicant page preserves the current intake and
rendered result set, temporary cover sheet, and disclosure state when
English/Spanish interface copy is toggled. Stable rule anchors do not change
with the language. Source material that remains English carries `lang="en"`.
The Python reference demo's language link is labeled as starting over because
that server-rendered surface does not preserve form state. Both surfaces state
that language selection covers the applicant form and results, while the
staff-facing trust, ordinance, and clock tools remain English.

## Remaining (human/AT pass not done)

- Execute and sign every row in `docs/MANUAL-VALIDATION.md`. Preparing that
  record did not complete any human or assistive-technology test.
- Screen-reader walkthrough (VoiceOver/NVDA): reading order, datalist
  combobox behavior, packet-result reading order, and live-region verbosity.
- 200% zoom and 320px reflow visual check on real devices. The packet page
  passed a local 320 CSS-pixel viewport check, which is not a real-device or
  browser-zoom test.
- `forced-colors` / high-contrast mode spot check.
- Spanish screen-reader pronunciation check.
- Mixed-language audit: translated intake/result labels and Spanish
  plain-language drafts carry explicit `lang` metadata. Pathway titles,
  source-derived notes/excerpts, and document hints are marked English. The
  Spanish drafts have not had human or semantic-parity review, and the
  source-linked letter metadata, scanner, clocks, dashboard, and sources
  remain partly or wholly English.
- Keyboard-only end-to-end run of all five static flows.
- AAA content-level judgments (3.1.5 reading level): the new plain-language
  layer is structurally simpler, but no formal readability or comprehension
  assessment has been done).
