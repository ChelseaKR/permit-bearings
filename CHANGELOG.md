# Changelog

All notable changes to this project are recorded here. The project has not
published a versioned release.

## [Unreleased]

### Fixed

- The source-currency watcher no longer reports a source it could not
  download as a source that changed. Each watched source is now classified as
  `unchanged`, `changed` (fetched, hash moved), or `unverifiable` (fetch
  failed: network error, non-2xx, timeout, or bot/WAF block). An unverifiable
  source keeps its recorded hash and last successful verification date and
  marks no rule stale, so a blocked or rate-limited scheduled runner can no
  longer flip every dependent rule to "stale". Fetches now retry three times
  with exponential backoff, one dead source cannot abort the run, and the
  harness exits `2` for "could not check" as distinct from `1` for "review
  needed". No rule content, source hash, or demo-visible output changed.

### Changed

- Added a durable, repository-adopted source-state overlay. The watcher can
  emit a proposed completed-run receipt with observed digests; the scheduled
  workflow retains that JSON for human adoption but never overwrites public
  state. A strict loader and bundle-format-3 browser contract bind the source
  registry and run receipt, re-derive exact affected/unaffected rule and
  Golden-case IDs, and fail closed on drift. Changed dependencies stale exact
  statewide records and block only bound Woodland route/checklist/parcel
  surfaces; unrelated records remain available, while unverifiable fetches
  warn without staling. The public evidence page distinguishes the committed
  snapshot from the temporary § 66321 rehearsal. Automatic adoption, a named
  reviewer record, staffed disposition workflow, packet-field queue records,
  new-law discovery, and substantive approval remain planned.
- Refreshed the public HCD Housing Accountability Unit letter corpus from
  1,309 to 1,314 records on 2026-08-03. All 1,314 rows map cleanly to the
  statewide jurisdiction registry or the two statewide records; Grover Beach
  now has letter history in the applicant-facing jurisdiction context.
- Added a bilingual, print-focused statewide orientation handoff for all 541
  recognized California cities and counties. It carries the selected facts,
  candidate-route sources and currency, local-coverage boundary, and questions
  for staff without storing applicant input. Automated browser coverage spans
  an ordinary city, a county, post-2020 Mountain House, and Davis's bounded
  local layer. The deeper 25-item packet remains explicitly Woodland-only.
- Reworked phone-width navigation into a native section disclosure, tightened
  narrow-screen spacing, expanded primary task actions, and restyled evidence
  tables as labeled records without changing their table semantics. Automated
  browser coverage now includes 320px and 390px reflow, a populated applicant
  result, and the mobile evidence state.
- Added a local SVG favicon and expanded the Lighthouse mobile budget gate to
  the populated applicant sample; all six audited states currently score 1.00
  for accessibility, best practices, performance, and SEO.
- Added a source-shaped Woodland parcel-evidence fixture: two fabricated
  values bind to exact fields in dated Yolo County public parcel-layer
  metadata, flow into the evidence manifest and packet UI, and fail closed
  when the checklist or parcel-schema source changes or ages out. No live
  parcel is queried or represented as verified.
- Hardened GitHub Actions with least-privilege permissions, concurrency
  controls, immutable action pins, and full-history secret scanning.
- Added a locked Python 3.12 development environment and matching local/CI
  lint, strict type, branch-coverage, dependency, SAST, and data-integrity
  verification.
- Added event-armed CodeQL, workflow-security, Scorecard, and dependency-update
  automation with least-privilege tokens and immutable action pins.
- Added automated axe WCAG checks across every public page and Lighthouse
  accessibility, performance, best-practices, and SEO budgets.
- Decomposed the fail-closed rule, explanation, source, transit, and readiness
  loaders/evaluators into bounded validators and retired the `WVR-007`
  complexity waiver; Ruff now enforces complexity 10 across the Python
  codebase.
- Bound the Davis local record to current official City guidance, preserved
  HCD's unresolved ordinance-status warning as separate evidence, and limited
  public copy to the City's published processing categories rather than
  implying locally encoded eligibility rules.
- Added a versioned human accessibility and Spanish semantic-parity test
  matrix with explicit evidence fields and `not_run` defaults; creating the
  record does not promote any manual-review or conformance claim.
- Added a pinned, read-only private standards consumer gate and a reviewable
  protected-main ruleset profile.
- Pinned the consumer to the standards fix that enforces live hosted policy
  and publication checks in single-repository network mode.
- Stabilized the unchanged Lighthouse 0.90 performance budget by confirming a
  low first sample twice and evaluating the three-sample median.
- Updated pinned checkout, Python, uv, and CodeQL actions; CodeQL initialization
  and analysis now use the same action version.
