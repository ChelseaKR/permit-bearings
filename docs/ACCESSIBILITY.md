# Accessibility audit — static pass, updated 2026-07-28

Scope: the public demo page (`index.html`). **Target: WCAG 2.2 Level AAA.**
Styling uses the open-source **California Design System** ("cagov" theme
tokens from `@cagov/ds-base-css`, with a system UI type stack); token steps were chosen
to meet AAA contrast on these surfaces, and the dark theme derives from the
same hues (CDS ships light-only). No state branding, logo, or header is
used — the design system is open source and its use does not imply
affiliation.

This is a static (code-level) audit with computed contrast; items under
"Remaining" require a human with assistive technology.

## Checked and passing

**Semantics & structure.** Single `<main>`; one `<h1>`; sectioned `<h2>`s;
grouped result headings; each decision record is an `<article>` labeled by
its unique title; evidence uses native `<details>/<summary>`; `<th>` header
rows. Multiple deadlines or thresholds use a semantic heading and list rather
than visual-only layout. All interactive elements are native controls, so
keyboard operability and focus order come from the platform.

**Focus appearance (2.4.13, AAA-new).** Global `:focus-visible` indicator:
3px solid accent outline with 2px offset — ≥2px perimeter, ≥3:1 against
adjacent colors in both themes (10.6:1 light / 10.3:1 dark vs page).

**Target size (2.5.5 AAA / 2.5.8 AA).** Buttons, selects, inputs, and
textareas have `min-height: 44px`; checkbox/radio rows get ≥44px hit areas
via label padding. Result evidence summaries also have a 44px minimum target.
Inline text links fall under the in-text exception.

**Motion (2.3.3).** The only animation (smooth scroll to results) is
disabled under `prefers-reduced-motion: reduce`.

**Labels & names.** Visible `<label>` wrappers for radios/checkboxes;
`aria-label` on the jurisdiction combobox, ordinance textarea, and date
input; the trust meter has `role="img"` with a descriptive label.

**Dynamic updates.** A visually hidden, concise result-count status,
scan findings, clock output, and jurisdiction status carry
`aria-live="polite"`. The full result-card collection is not a live region,
which avoids announcing every source excerpt when several records match. The
zero-result status includes the full staff-review routing message instead of
announcing only a count. The amendment rehearsal announces how many matching
guidance records were withheld or restored, then moves focus to the newly
available reset/rehearse control.

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

**Contrast — 1.4.6 Enhanced (7:1 normal text), computed both themes:**

| Pair | Light | Dark |
|---|---|---|
| Body ink / page | 18.7 | 19.4 |
| Secondary ink / page | 7.5 | 10.9 |
| Muted ink / page·surface | 7.1 / 7.3 | 8.2 / 7.3 |
| Links & accent (CDS primary-900 / primary-300) | 10.6 | 10.3 / 9.2 |
| Button text on accent | 11.2 | 10.3 |
| Badge ok text/bg | 8.0 | 8.2 |
| Badge warn text/bg (CDS accent2-900/accent2-100) | 9.6 | 8.0 |
| Badge bad text/bg | 7.8 | 8.9 |

Status *fill* colors (meter segments) are graphical objects (1.4.11, 3:1
with text badges adjacent); ok/bad badge pairs are supplemental to CDS,
which defines no status green/red in its theme tokens.

**Visual presentation (1.4.8, partial).** Line height 1.55; single column
capped near 80 characters; no justified text; wide tables scroll in their
own container (no page horizontal scroll at 320px). User-selectable
colors/spacing beyond browser and OS mechanisms are not provided.

**Language switching.** The static showcase preserves the current intake and
rendered result set when English/Spanish interface copy is toggled. Source
material that remains English carries `lang="en"`. The Python reference demo's
language link is labeled as starting over because that server-rendered surface
does not preserve form state.

## Remaining (human/AT pass — not done)

- Screen-reader walkthrough (VoiceOver/NVDA): reading order, datalist
  combobox behavior, live-region verbosity.
- 200% zoom and 320px reflow visual check on real devices.
- `forced-colors` / high-contrast mode spot check.
- Spanish screen-reader pronunciation check.
- Mixed-language audit: translated intake/result labels and Spanish
  plain-language drafts carry explicit `lang` metadata. Pathway titles,
  source-derived notes/excerpts, and document hints are marked English. The
  Spanish drafts have not had human or semantic-parity review, and the
  jurisdiction-status details, scanner, clocks, dashboard, and sources remain
  partly or wholly English.
- Keyboard-only end-to-end run of all four flows.
- AAA content-level judgments (3.1.5 reading level — the new plain-language
  layer is structurally simpler, but no formal readability or comprehension
  assessment has been done).
