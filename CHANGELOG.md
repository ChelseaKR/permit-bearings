# Changelog

All notable changes to this project are recorded here. The project has not
published a versioned release.

## [Unreleased]

### Changed

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
- Rechecked the unverified Davis local record against currently discoverable
  City and code-host material, recorded the local/state currency conflict, and
  preserved the fail-closed unverified status pending a stable official
  artifact and review.
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
