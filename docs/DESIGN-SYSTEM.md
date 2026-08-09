# California Design System alignment

Reviewed 2026-08-09.

Permit Bearings is not an official State of California website. The five-page
public static site maintains a local **version-0 preview compatibility layer**
for selected California Design System component structures, tokens, and
interaction patterns. This is an implementation aid for the prototype, not a
claim of California Design System conformance, certification, production
support, State affiliation, or Office of Digital Services approval.

## Upstream status and reference boundary

The successor [California Design
System](https://github.com/Office-of-Digital-Services/California-Design-System)
describes itself as pre-Alpha and not ready for production use. It has no
production-supported release for this project to adopt. Permit Bearings uses
commit `f8775cfac090de08b9e0083eb3008bd585f33e91`, dated 2026-01-27, as a pinned
design reference so later upstream changes cannot silently alter this site's
contract.

The successor repository and package metadata do not currently present one
unambiguous redistribution license. No successor package, source file, or
compiled bundle is installed, copied, or served by this repository. The local
compatibility selectors and markup are project-maintained implementations
informed by the pinned public reference. `version-0` names this project's
preview contract; it is not an upstream version or maturity claim.

The earlier `cagov/design-system` repository remains the source for the
published `cagov` theme token values already adapted locally and the bundled
Public Sans webfonts. The design-system snapshot is MIT-licensed; the font
files retain the SIL Open Font License 1.1. Exact snapshot provenance and both
notices are recorded in `THIRD_PARTY_NOTICES.md` and `PROVENANCE.md`.

## Local implementation contract

Every public page loads `assets/california-design-system.css` before
`assets/site.css`. The first file contains the shared compatibility layer;
the second applies Permit Bearings composition, evidence, decision-support,
responsive, and print styles. Keeping those layers separate makes it possible
to test common component behavior without representing product-specific
patterns as California Design System components.

The optional server-rendered reference flow in `demo/app.py` loads those same
two assets and adds only scoped reference-flow composition. Its generated
forms, notices, cards, actions, tables, header, and bypass link carry the same
component hooks. It remains a reference implementation, not a sixth public
task page or a separate design-system claim.

The shared layer uses the successor system's semantic `ca-*` vocabulary where
the static HTML has a stable equivalent:

| Local structure | Use in Permit Bearings | Boundary |
|---|---|---|
| `#skip-to-content` | First-focusable bypass link on all five pages | Local static implementation; no upstream script |
| `.ca-button` | Primary and secondary actions, including page and form controls | Existing product classes remain as page-level modifiers |
| `<ca-field>` | Groups a label, help or status text, and its native input | Native inputs preserve browser form semantics |
| `<ca-shout>` | Important boundary, warning, or load-state notice | Status meaning also remains in visible text |
| `<ca-box>` | Bounded explanatory or task panel | Does not imply approval or a legal finding |
| `<ca-mesh>` | Responsive repeated-content layout | Layout semantics only; children retain their own headings and landmarks |
| `.ca-inner-border`, `.ca-outer-border`, `.ca-stripes` | Visual treatment on semantic data tables | Tables retain captions, row/column headers, and narrow-screen labels |

Native `<details>` disclosures remain native. The service header and footer,
decision and evidence records, status chips, journey rail, and printable
packet summary are Permit Bearings components. They are intentionally not
relabeled as upstream components.

## Tokens, typography, and accessibility extensions

The compatibility layer exposes the published California color, type,
spacing, and width vocabulary used by the product. Permit Bearings maps those
values to product-level aliases and may choose a darker token when needed for
its WCAG 2.2 AAA contrast target. Public Sans 400, 600, and 700 are served as
local WOFF2 assets; there is no runtime font or stylesheet request to a State
or third-party CDN.

Local behavior includes an always-visible dual-color focus indicator,
44–48px control targets, reduced-motion handling, forced-colors support,
responsive table records, and print isolation. These are project
accessibility decisions and test targets. They do not establish WCAG
conformance or upstream component approval; the remaining human and
assistive-technology checks are tracked in `docs/ACCESSIBILITY.md`.

## Product-specific presentation

The product keeps a task-oriented public-service structure rather than
imitating an agency website. The landing page gives the applicant check one
primary action and keeps staff and assurance tools secondary. The applicant
result presents submitted facts, grouped candidate records, citations, source
currency, and uncertainty routing as service records rather than a dashboard.
The evidence rail uses a gold structural rule to connect a decision-support
result with the source record that constrains it.
The result decision boundary composes the local `<ca-box>` hook with a native
`<aside role="note">` and definition list, using only the shared token aliases;
its candidate, unresolved, no-route, and source-review meanings remain in text
rather than depending on the colored border.

The header is a product-specific service header. It deliberately omits the
State logo, official-site banner, wordmark, and agency identity because this
personal prototype is not operated or endorsed by California. Copying an
official State header would make the trust boundary less clear, not more
aligned.

## Verification and change control

Static contract tests check that all five public pages load the compatibility
stylesheet before product styles, expose the same bypass-link structure, and
use the selected semantic structures for their applicable controls and
content. Browser accessibility, reflow, print, and performance checks exercise
the composed result. A future upstream change is reviewed deliberately against
the pinned snapshot; it is never inherited at runtime.

This record documents alignment only. Automated and static checks do not
replace usability testing, content review, legal review, human accessibility
testing, or approval by California's Office of Digital Services.
