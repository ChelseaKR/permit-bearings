# California Web Standards alignment

Reviewed 2026-07-28.

Permit Bearings is not an official State of California website. It uses the
published California Design System as an open-source foundation and follows
California Web Standards design principles without copying the official-site
banner, wordmark, or agency identity.

## Adopted foundation

`assets/site.css` defines the published `cagov` theme token names and values
locally, then maps product-level aliases to those tokens. The adopted
foundation includes:

- `primary`, `accent1`, `accent2`, `gray`, `success`, `danger`, `warning`, and
  `info` color scales;
- `cagov-primary`, `cagov-primary-dark`, `cagov-secondary`, and
  `cagov-highlight`;
- Public Sans-first interface typography, an 18px base size, and the published
  type and line-height scale;
- the 1,176px large shell and 876px reading width; and
- the published spacing steps.

The site keeps the implementation dependency-free. It does not install the
[next California Design System
package](https://github.com/Office-of-Digital-Services/California-Design-System),
whose repository currently labels the package pre-alpha and not stable for
production use. This choice preserves the static demo while keeping the
token contract visible and testable.

## Interaction and content patterns

The implementation applies the California Web Standards principles directly:

- **Design for people’s needs:** the landing page routes applicants, review
  staff, and assurance reviewers to separate tasks.
- **Make complexity simple:** each tool page has one primary job, a short
  boundary statement, and plain labels instead of a conversational shell.
- **Prioritize accessibility:** native controls, skip links, active-page
  semantics, 44–48px targets, a dual-color focus indicator, reduced-motion
  handling, forced-colors support, and labeled scroll regions are built in.
- **Be concise:** the landing page explains scope before detail and limits the
  main task index to three links.
- **Design with data:** rule-source status and dependency effects come from the
  same generated data bundle used by the tools.
- **Optimize performance:** the landing page loads one local stylesheet and no
  application or data JavaScript. Interactive pages share one page-gated
  script and one generated data bundle.
- **Open by default:** important claims link to source evidence, and the
  repository exposes the rule, source, fixture, and explanation artifacts.

## Product-specific presentation

The landing page follows a public-service start-page pattern. It gives the
applicant check one primary action, keeps staff tools secondary, and shows the
contents of a result as a plain definition list. The presentation avoids a
marketing hero, decorative cards, product illustrations, and conversational
interface patterns. Its colors, typography, focus behavior, and responsive
layout use the adopted tokens.

The review-clock utility uses a narrow, single-column service form. Its action
follows the facts needed for the result, and its separate timing outcomes use a
stacked definition list instead of a dashboard card or comparison table.

## Conformance boundary

This is an alignment record, not a claim of certification. Automated and
static checks do not replace a human accessibility review, usability testing,
content review, or approval by California’s Office of Digital Services.
Remaining human checks are tracked in `docs/ACCESSIBILITY.md`.
