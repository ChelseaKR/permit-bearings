# Responsible-Tech audits — Permit Bearings

Project-specific findings under the portfolio Responsible-Tech Framework.
Numeric thresholds remain owned by `~/portfolio/STANDARDS`.

## Applicability

- A Ethics: applies; permitting guidance can impose cost, delay, or false
  confidence.
- B Bias: applies; encoded coverage and unresolved facts can distribute benefit
  unevenly across jurisdictions and applicants.
- C Privacy/DPIA: applies to the public intake boundary, although the current
  demo keeps facts in page/request memory and stores none.
- D Transparency: applies; source, currency, prototype status, and unknowns are
  core product behavior.
- E Accessibility: applies to all five static pages and the Python-rendered
  reference surface.
- F Security: applies to evidence integrity, browser rendering, remote source
  retrieval, and CI.
- AI Evaluation: applies narrowly to AI-assisted explanation, remedy, mapping,
  and translation artifacts; no model runs in the product.
- Internationalization: applies to the applicant-facing English/Spanish
  surface.

## Findings

### Ethics and bias

The highest-impact failure is an applicant treating a candidate route or
presence result as approval, legal advice, or completeness. The interface and
tests preserve those boundaries. Coverage remains structurally uneven:
statewide rules are broader than the two bounded local records, and only one
local packet workflow is encoded. A registry entry must never be presented as
local-law coverage.

Review gate: new jurisdictions, rules, remedies, or applicant claims require
source evidence, explicit status, negative and ambiguous fixtures, and review
of who remains unsupported.

### Privacy

The static page keeps submitted facts only in memory. The reference server
does not persist requests. There are no accounts, uploads, telemetry, cookies,
external model calls, or applicant records. The committed packet is synthetic.

Residual risk remains because applicants can type sensitive project facts into
a prototype and a future host can add logging outside this repository.
Deployment must document fields, purpose, subprocessors, access, retention,
deletion, public-records handling, and operator logging before real use.

### Transparency

Rules expose citations, source status, excerpts when available, scope, and
candidate labels. AI-assisted copy lives outside matching data with independent
review metadata and fingerprint bindings. Missing or invalid explanation data
degrades to evidence-only output.

No current explanation, remedy, mapping, or Spanish draft is represented as
human-, counsel-, or jurisdiction-reviewed. The source watcher is a rehearsal
and alert path, not a durable re-verification queue.

### Accessibility

The target and current static evidence are recorded in
`docs/ACCESSIBILITY.md`. Automated unit/static checks and limited viewport
inspection exist, but the portfolio axe, pa11y, and Lighthouse auto-gates are
not wired. Keyboard-only, forced-colors, VoiceOver, NVDA, and Spanish
pronunciation review remain open. No WCAG conformance or human-testing claim
is made.

### Security

The current model and residual risks are in `docs/THREAT-MODEL.md`.
SHA-pinned Actions, least-privilege workflow tokens, locked Python tools,
Bandit, pip-audit, and Gitleaks are now enforced. CodeQL/advanced SAST, live
branch-ruleset verification, standards-consumer CI, SBOM, and deployment CSP
evidence remain open.

## Gate checklist

| Control | Gate | Current evidence |
|---|---|---|
| Matching is independent of explanation copy | AUTO | Trust-contract and explanation tests |
| Source/explanation drift fails closed | AUTO | Fingerprint, stale-source, and fallback tests |
| Generated bundle matches canonical inputs | AUTO | `scripts/build_demo_bundle.py --check` |
| Core strict typing | AUTO | `mypy --strict src` |
| Branch coverage | AUTO | 80% interim gate; 85% portfolio floor remains open |
| Dependency/SAST/secret checks | AUTO | pip-audit, Bandit, Gitleaks |
| Human legal/content review | REVIEW | Open; metadata remains review-pending |
| Translation semantic parity | REVIEW | Open; machine draft label remains visible |
| Human assistive-technology review | REVIEW | Open in `docs/ACCESSIBILITY.md` |
| Pilot privacy and records review | REVIEW | N/A to no-storage demo; required before pilot data |

Status: prototype. Last reviewed 2026-07-29; recheck quarterly and on every
release or material boundary change.
