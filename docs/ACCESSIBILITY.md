# Accessibility audit — static pass, 2026-07-27

Scope: the public demo page (`index.html`). Target: WCAG 2.1 AA. This is a
static (code-level) audit with computed contrast; the items under "Remaining"
require a human with assistive technology and have not been done.

## Checked and passing

**Semantics & structure.** Single `<main>` landmark; one `<h1>`; sections
with `<h2>` headings; data tables use `<th>` header rows; all interactive
elements are native controls (`button`, `input`, `select`, `textarea`,
`a`) — no div-buttons, so keyboard operability and focus come from the
platform. Default focus outlines are not suppressed anywhere.

**Labels.** Every form control has a programmatic name: visible `<label>`
wrappers for radios/checkboxes; `aria-label` on the jurisdiction combobox,
ordinance textarea, and date input (their `<legend>`/heading context is not
programmatically associated, so the explicit name is required). The trust
meter has `role="img"` with a descriptive `aria-label`.

**Dynamic updates.** Results, scan findings, clock output, and the
jurisdiction status line carry `aria-live="polite"` so screen-reader users
hear updates without losing focus.

**Language.** `<html lang>` reflects the active language and is updated by
the EN/ES toggle; the toggle is a real link with `role="button"` semantics
via activation handling.

**Not color-alone.** Every status is a badge with an icon glyph (✓ ⚠ ✕) and
a text word; verified/stale/unverified never rely on hue only.

**Contrast (computed, WCAG relative-luminance method).** All text pairs meet
≥ 4.5:1 in both themes after the 2026-07-27 fixes:

| Pair | Light | Dark |
|---|---|---|
| Body ink / page | 18.7 | 19.4 |
| Secondary ink / page | 7.5 | 10.9 |
| Muted ink / page | 5.0 (was 3.4, darkened) | 5.4 |
| Links & buttons (accent) | 6.3 (was 4.2, darkened) | 5.3 |
| Badge "ok" text/bg | 6.8 (was 3.0, → success-text token) | 8.2 (→ #4ade80) |
| Badge "warn" text/bg | 6.4 | 8.0 |
| Badge "bad" text/bg | 7.0 (was 4.1, → #991b1b) | 6.1 (→ #f87171) |

Status *fill* colors on the meter remain the reserved status palette; the
adjacent count badges carry the text.

**Reflow.** Layout is a single column with `max-width`; tables are the only
wide content and scroll within the viewport at 320 px width.

## Remaining (human/AT pass — not yet done)

- Screen-reader walkthrough (VoiceOver/NVDA): reading order, datalist
  combobox behavior across browsers, live-region verbosity.
- 200% zoom and 320 px reflow visual check on real devices.
- `forced-colors` / Windows High Contrast mode spot check.
- Spanish-language screen-reader pronunciation check.
- Keyboard-only end-to-end run of all four flows.
