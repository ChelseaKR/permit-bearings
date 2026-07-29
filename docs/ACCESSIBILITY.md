# Accessibility audit: static pass, updated 2026-07-28

Scope: the four-page public static site (`index.html`, `check.html`,
`review.html`, and `evidence.html`) and the separate applicant flow in
`demo/app.py`. **Target: WCAG 2.2 Level AAA.**
The static site implements the published California Design System `cagov`
tokens locally: Public Sans-first typography, 18px body copy, 1.75 line
height, state color/status tokens, spacing steps, and the 1,176px shell /
876px reading widths. No State logo, official-site banner, branding, or
affiliation is claimed. See `docs/DESIGN-SYSTEM.md`.

This is a static (code-level) audit with computed contrast; items under
"Remaining" require a human with assistive technology.

## Checked and passing

**Semantics & structure.** Each page has a skip link, one `<main>`, one
`<h1>`, a labeled primary navigation, and `aria-current` on the active page.
Sections use `<h2>`s;
grouped result headings; each decision record is an `<article>` labeled by
its unique title; evidence uses native `<details>/<summary>`; `<th>` header
rows. Multiple deadlines or thresholds use a semantic heading and list rather
than visual-only layout. All interactive elements are native controls, so
keyboard operability and focus order come from the platform.

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

**Dynamic updates.** A visually hidden, concise result-count status,
scan findings, clock output, and jurisdiction status carry
`aria-live="polite"`. The full result-card collection is not a live region,
which avoids announcing every source excerpt when several records match. The
zero-result status includes the full staff-review routing message instead of
announcing only a count. The amendment rehearsal announces how many matching
guidance records were withheld or restored, then moves focus to the newly
available reset/rehearse control. After screening, keyboard focus moves to
the result heading; scanner and clock live regions announce a concise summary
instead of their full result tables or cards.

The shareable ADU sample is introduced by descriptive link text and followed
by a visible disclosure that identifies the facts as hypothetical. It fills
the same native form controls and invokes the same form submission path as
manual answers, so the existing result-status announcement applies. For the
automatically submitted sample, focus moves to the disclosure instead of
skipping past it to the results. A plainly labeled link clears the sample.
Editing a sample fact relabels the disclosure, removes the sample URL
parameter, and clears the old results until the edited form is submitted.

**Data-loading state.** Data-dependent pathway, scanner, and trust-rehearsal
buttons use the native `disabled` state until their datasets are ready. A
load failure places a visible explanation in the results area and a short
message in the result status region instead of leaving empty controls that
appear operable.

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
rendered result set when English/Spanish interface copy is toggled. Source
material that remains English carries `lang="en"`. The Python reference demo's
language link is labeled as starting over because that server-rendered surface
does not preserve form state. Both surfaces state that language selection
covers the applicant form and results, while the staff-facing trust,
ordinance, and clock tools remain English.

## Remaining (human/AT pass not done)

- Screen-reader walkthrough (VoiceOver/NVDA): reading order, datalist
  combobox behavior, live-region verbosity.
- 200% zoom and 320px reflow visual check on real devices.
- `forced-colors` / high-contrast mode spot check.
- Spanish screen-reader pronunciation check.
- Mixed-language audit: translated intake/result labels and Spanish
  plain-language drafts carry explicit `lang` metadata. Pathway titles,
  source-derived notes/excerpts, and document hints are marked English. The
  Spanish drafts have not had human or semantic-parity review, and the
  source-linked letter metadata, scanner, clocks, dashboard, and sources
  remain partly or wholly English.
- Keyboard-only end-to-end run of all four flows.
- AAA content-level judgments (3.1.5 reading level): the new plain-language
  layer is structurally simpler, but no formal readability or comprehension
  assessment has been done).
