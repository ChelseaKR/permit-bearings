# Accessibility audit — static pass, updated 2026-07-27

Scope: the public demo page (`index.html`). **Target: WCAG 2.2 Level AAA.**
Styling uses the open-source **California Design System** ("cagov" theme
tokens from `@cagov/ds-base-css`, Public Sans type); token steps were chosen
to meet AAA contrast on these surfaces, and the dark theme derives from the
same hues (CDS ships light-only). No state branding, logo, or header is
used — the design system is open source and its use does not imply
affiliation.

This is a static (code-level) audit with computed contrast; items under
"Remaining" require a human with assistive technology.

## Checked and passing

**Semantics & structure.** Single `<main>`; one `<h1>`; sectioned `<h2>`s;
`<th>` header rows; all interactive elements are native controls, so
keyboard operability and focus order come from the platform.

**Focus appearance (2.4.13, AAA-new).** Global `:focus-visible` indicator:
3px solid accent outline with 2px offset — ≥2px perimeter, ≥3:1 against
adjacent colors in both themes (10.6:1 light / 10.3:1 dark vs page).

**Target size (2.5.5 AAA / 2.5.8 AA).** Buttons, selects, inputs, and
textareas have `min-height: 44px`; checkbox/radio rows get ≥44px hit areas
via label padding. Inline text links fall under the in-text exception.

**Motion (2.3.3).** The only animation (smooth scroll to results) is
disabled under `prefers-reduced-motion: reduce`.

**Labels & names.** Visible `<label>` wrappers for radios/checkboxes;
`aria-label` on the jurisdiction combobox, ordinance textarea, and date
input; the trust meter has `role="img"` with a descriptive label.

**Dynamic updates.** Results, scan findings, clock output, and jurisdiction
status carry `aria-live="polite"`.

**Link purpose (2.4.9 AAA).** Every link's text alone states its target
("view scan findings (JSON)", full source citations, named statutes).

**Language.** `<html lang>` tracks the EN/ES toggle.

**Not color-alone.** Statuses are icon + word badges; hue never carries
meaning by itself.

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

## Remaining (human/AT pass — not done)

- Screen-reader walkthrough (VoiceOver/NVDA): reading order, datalist
  combobox behavior, live-region verbosity.
- 200% zoom and 320px reflow visual check on real devices.
- `forced-colors` / high-contrast mode spot check.
- Spanish screen-reader pronunciation check.
- Keyboard-only end-to-end run of all four flows.
- AAA content-level judgments (3.1.5 reading level — plain language and a
  full Spanish interface are design goals, but no formal readability
  assessment has been done).
