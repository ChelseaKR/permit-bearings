# Accessibility audit: static and automated browser pass, updated 2026-08-03

Scope: the five-page public static site (`index.html`, `check.html`,
`prepare.html`, `review.html`, and `evidence.html`) and the separate applicant
flow in `demo/app.py`. **Target: WCAG 2.2 Level AAA.**
The static site implements the published California Design System `cagov`
tokens locally: Public Sans-first typography, 18px body copy, 1.75 line
height, state color/status tokens, spacing steps, and the 1,176px shell /
876px reading widths. No State logo, official-site banner, branding, or
affiliation is claimed. See `docs/DESIGN-SYSTEM.md`.

This audit combines static and code-level checks, computed contrast, automated
axe scans of all five public pages, Lighthouse category budgets, automated
320px/390px reflow checks, populated-state checks, and limited local browser
inspection. Automation found and remediated invalid ARIA labeling on packet
status text and the ordinance results region. It is not a completed manual,
physical-device, or assistive-technology review.
Items under "Remaining" require a person using the named browsers, input
methods, or assistive technology. The executable task matrix and signed-result
requirements are defined in `docs/MANUAL-VALIDATION.md`; every row is
currently `not_run`. The corresponding machine-readable execution fields and
version locks are in `data/validation/woodland-manual-evidence.json`; creating
that ledger does not count as a human check.

## Static and code checks recorded

**Semantics & structure.** Each page has a skip link, one `<main>`, one
`<h1>`, a labeled viewport-appropriate primary navigation, and `aria-current`
on the active page. The phone navigation is a native disclosure with a 48px
summary target; the full navigation remains the desktop/tablet surface.
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

The exact valid journey entry adds one labeled evidence-summary section. Its
public ID/version and facts use definition lists, preparation actions use an
ordered list, direct staff questions use an unordered list, and source records
retain descriptive links and visible status text. A native button opens the
browser print dialog. The entire section, including that control, remains
hidden on direct or invalid packet entry. These structures are covered by
static and browser checks; their screen-reader reading order and printed-page
usability have not been manually reviewed.

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

On 2026-08-03, axe-core 4.12.1 reported no WCAG 2.0/2.1/2.2 A, AA, or tagged
AAA violations on `index.html`, `check.html`, `prepare.html`, `review.html`,
or `evidence.html` in a Playwright-managed Chromium build. Thirty-four browser
checks also exercise each page at 320px and 390px, open the compact navigation,
check document-level overflow, scan a populated applicant result, verify that
mobile evidence tables render as labeled records, and cover valid/invalid
journey-summary disclosure. The evidence-page checks now cover the adopted
all-unchanged source receipt, an internally consistent changed receipt with
its derived review queue, and an unverifiable receipt that warns without
staling a dependent. A print-media check isolates the summary from the
site and detailed packet surfaces and checks horizontal overflow at an
816-by-1056 CSS-pixel viewport. Lighthouse 13.4.1 audits all five initial pages
plus the populated applicant sample and exact valid journey entry using its
mobile profile. On 2026-08-03, all seven states met 1.00 accessibility and best
practices, at least 0.99 performance, and at least 0.90 SEO. CI repeats both
suites on pull requests, default-branch pushes, and weekly. A first performance
sample below the 0.90 budget triggers two confirmation samples and evaluates
their median; the budget itself is unchanged.

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

Every resolved jurisdiction result also includes an orientation receipt built
with native headings, definition lists, and lists. Its print action calls the
browser's print dialog, and print media isolates the receipt from navigation,
intake, detailed result cards, and controls. Automated coverage checks the
receipt's reflow and print overflow across representative city, county,
incorporation-update, and bounded-local-layer profiles. Printed-output reading
order and assistive-technology behavior remain manual checks.

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
content is capped at the published 876px width; no text is justified. At phone
widths, wide evidence tables become labeled records and the automated 320px
and 390px checks find no document-level horizontal scroll. User-selectable
colors/spacing beyond browser and OS mechanisms are not provided.

**Print presentation (automated emulation only).** Readiness-page print CSS
withholds the site header/footer, task hero, detailed packet surfaces, and
print control while keeping the evidence summary. It uses print-sized type,
visible black borders/status text, overflow wrapping for IDs and URLs, and
break avoidance on bounded records. The automated check uses Chromium print
media; it does not inspect a generated PDF, paper output, pagination across
printer drivers, or assistive reading of a saved file.

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
- 200% and 400% zoom checks on real devices. Automated Chromium reflow passes
  at 320px and 390px, but that is not a physical-device, browser-zoom, or
  virtual-keyboard test.
- Physical iPhone/Safari and Android/Chrome task runs, including the compact
  section menu, form editing with the virtual keyboard, disclosures, and
  labeled evidence records.
- Browser Print and Save-as-PDF review in Safari, Chrome, and Firefox,
  including pagination, link destinations, long-value wrapping, grayscale,
  and reading order in the resulting artifact.
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
