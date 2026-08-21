# Changelog

All notable changes to this project are recorded here. The project has not
published a versioned release.

## [Unreleased]

### Added

- The optional runtime AI service directed by ADR 0004, as the new
  `permit_pathways.ai` package behind the `ai` extra (`uv sync --extra ai`;
  `make serve-ai`). `facts.py` pins the intake vocabulary to the matcher's
  own 19 fact names and allowed values and is tested against the rule
  criteria, the browser form, and the beta-operations field pin. `corpus.py`
  indexes every text document `data/sources.json` binds to `corpus/` (12
  leginfo statutes as HTML, the HCD handbook and SB 9 fact sheet as PDF via
  pypdf, the Davis and Woodland PDFs, the CEQA notice) into passages and
  verifies a quoted string against the whole extracted document after
  typography, case, and whitespace folding, with a minimum length so a
  trivial phrase cannot pass as a citation. `intake.py` asks the model for
  the matcher's facts and nothing else, then re-checks every value against
  the allowed list and every supporting quote against the applicant's text,
  downgrading anything unsupported to `unknown`; the jurisdiction name is
  resolved deterministically against the registry. `explain.py` re-runs the
  Python matcher, refuses a caller-asserted rule set that differs, offers the
  model passages only from the matched rules' `source_dependencies`, and
  withholds any claim whose citation does not verify, reporting the withheld
  count. `staff_questions.py` drafts labeled questions tied to unresolved
  facts and matched rules, dropping pointers that do not resolve.
  `provider.py` reaches the Anthropic API or Amazon Bedrock through the
  public `anthropic` SDK only, default model `claude-sonnet-5`, credential
  from the environment only. `service.py` is the FastAPI app (`/health`,
  `/intake/extract`, `/explain`, `/staff-questions`) bound to localhost with
  an origin allowlist; it stores and logs no applicant content. Tests run
  against a scripted provider and make no network call. A data finding from
  building the verifier: 12 of the 19 committed rule excerpts contain
  editorial elisions (`[...]`, `[must]`) and are not verbatim source text;
  the grounding step locates them fragment by fragment, and 16 of 19 resolve.

### Changed

- Recorded an owner-directed change of direction in
  `docs/adr/0004-runtime-ai-at-the-edges.md`: Permit Bearings will add AI to
  the applicant's path — natural-language intake that drafts the structured
  facts for the applicant to confirm, a grounded plain-language explanation
  whose every claim must cite a passage verified against the committed
  corpus, and tailored staff questions — as a separate optional service,
  while the deterministic matcher stays unchanged. The README, `SECURITY.md`,
  `docs/DATA-FLOW.md`, `docs/PRODUCT-CONTEXT.md`, `docs/DESIGN.md`, and
  `AGENTS.md` no longer state "no runtime external model calls" as a
  repository guarantee; they state it for the static site only and point at
  the ADR. `docs/DATA-FLOW.md` gains the collected-field, subprocessor,
  access, retention, ownership, records, and review inventory that
  `AGENTS.md` requires before an external model call is added. The
  capability matrix lists the four runtime-AI capabilities as `Planned`;
  nothing in this change executes a model. ADR 0002 and the beta operations
  runbook are unchanged and still describe the static-only deployment, which
  remains the only shape with a prepared operations package.

### Fixed

- The required `standards` check passes again on a repository whose only
  change was its GitHub name. The repo was renamed from `permit-pathways` to
  `permit-bearings`; the pinned conformance checker resolved the private
  applicability entry by checkout basename, found nothing, defaulted the
  publication state to `restricted`, and scored a release-workflow control the
  entry marks N/A. `.github/workflows/standards.yml` now pins the head of
  portfolio-standards PR #97 (current main plus the key rename). That newer
  checker also enforces DOC-11, so the README's Standards Conformance table
  gained a `State and evidence` header, an explicit `Applies —` / `N/A —` state
  on every row, and rows for Performance, AI Development Measurement, Incident
  Response, and Data Governance that state what exists and what does not. The
  remaining items in issue #74 (tag pin, `.standards-version`) wait on that PR
  merging.

- The published San Diego ordinance scan now matches the checks that produced
  it. `data/conformance/results/san-diego.json` was generated on 2026-07-27
  and copied the `size-cap-conflict` check's `state_law` text; that check was
  rewritten on 2026-07-28 to add "these figures protect what local maximums
  must allow; they are not required minimum unit sizes", and the published
  file — which the browser links to directly — kept serving the superseded
  wording. The finding set was never wrong; the explanatory text was stale.
  `scripts/scan_ordinances.py --check` now re-derives every published result
  from the committed corpus, names the exact field that moved, and fails;
  `make bundle-check` runs it, so this class of drift breaks the build
  instead of being published. The result's disclaimer also now states that a
  scan is point-in-time and that no source-currency watch monitors the
  scanned ordinance for amendment. Regenerating the result also refreshed
  the generated demo bundle and, per the export maintenance rule, the two
  changed raw digests plus the bundle digest in the schema-v2 export
  profile; the frozen schema-v1 profile keeps its historical digests.
- The ordinance screen a visitor runs is now covered by the evidence the
  README cites for it. The HCD six-finding validation exercised the Python
  scanner; `review.html` runs a hand-ported JavaScript reimplementation that
  no test touched. A parity test now executes the shipped `scanOrdinance()`
  from `assets/demo.js` under Node against the same fixtures and requires
  identical check IDs, offsets and excerpt text, and a browser test asserts
  that the page renders those flags with the current `checks.json` wording.
  The comparison found one live divergence: the port collapsed excerpt
  whitespace without trimming, so an excerpt could be published with a
  leading or trailing space the validated scanner strips. The port now
  matches.
- The HCD HAU letters drift check now says what moved and stops filing a new
  issue every week for the same unresolved condition. It reported a
  difference between two row totals, which is not a count of letters: HCD
  edits published rows in place, so a run can add rows, remove rows and edit
  rows at once, and an edit that leaves the row count unchanged was reported
  as a bare "CHANGED". The check now reports rows added, rows removed, and
  which jurisdictions had rows on both sides (edited) versus only added
  (new). A dashboard that cannot be read now exits `2` as unverifiable with a
  workflow warning, matching the source-currency watcher's rule that a failed
  fetch is evidence about the network and never a change; previously it
  raised and the step was silent. The drift step now comments on the one open
  drift issue instead of opening another, and the fetch sends an identifying
  User-Agent.
- The reference server no longer disagreed with the browser about staleness.
  `demo/app.py` labelled a rule `verified` whenever its citation was inside
  the review window, ignoring changed sources entirely, while
  `assets/demo.js` and `permit_pathways.harness.runner` both treat a changed
  dependency as stale regardless of citation age. The server also contradicted
  itself: `/trust` routed through the harness and got it right, `/screen` did
  not. It now applies the same changed-source-first precedence and reads the
  same `data/source-status/current.json` the browser bundle ships.
- The 180-day source review window had four separate definitions. It now has
  one, `permit_pathways.dates.SOURCE_REVIEW_WINDOW_DAYS`, which the harness
  and readiness constants alias and the reference server renders.
  `tests/test_source_review_window.py` fails if any runtime drifts from it,
  including the browser constant that cannot import Python.

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

- Added the Statewide Coverage Navigator to the applicant guide. Selecting a
  recognized California city or county now renders a generated coverage profile
  from the committed registry, bounded rule records, and dated public HCD
  Housing Accountability Unit history. The profile keeps the statewide
  candidate-rule inventory, limited-local-layer status, and HCD history
  separate, shows an explicit `Not encoded` state where the repository has no
  jurisdiction-specific rule/form/fee/checklist layer, and lists the local
  source, scope, review-owner, and re-verification inputs a maintainer should
  assemble before adding a local layer. It makes no browser request or applicant-data
  store. HCD correspondence is historical reference material, not a current
  compliance or permit finding; no linked record in the dated snapshot does
  not establish no activity, compliance, or complete coverage.
- The navigator now consumes the adopted source-state overlay: a changed
  dependency visibly holds the affected statewide inventory or local source
  record for re-verification, while an unreachable source remains a separate
  warning. HCD disclosure targets now meet the 44px minimum and their links
  carry programmatic jurisdiction/date/authority context.
- Added a locally maintained California Design System version-0 preview
  compatibility layer across all five public static pages. The shared asset
  provides selected semantic `ca-*` structures for native actions and fields,
  boundary notices, bounded panels, responsive meshes, and semantic table
  treatments, plus one consistent skip-to-content pattern. Product styles now
  compose those structures while retaining local decision/evidence records,
  status chips, journey rail, print packet, and a service header that
  deliberately avoids State branding. Public Sans 400/600/700 is served
  locally from the archived `cagov/design-system` snapshot under the SIL Open
  Font License 1.1; the snapshot's design-system material is MIT-licensed.
  Successor-system commit `f8775cf` is a pinned reference
  only: that system is pre-Alpha with no production-supported release, and no
  current package, source, or bundle is copied because its licensing metadata
  is not unambiguous. This is component alignment, not conformance,
  certification, an official California website, or State endorsement. The
  optional Python-rendered reference flow now consumes the same shared assets
  and component hooks instead of maintaining a separate visual system.
- Added a read-only effective verification-level summary to
  `python -m permit_pathways.harness` (`rule_verification.level_coverage`):
  a one-line count of how many rules are effectively `machine_linked`,
  `human_reviewed`, or `jurisdiction_approved` today, including how many
  reverted closed because a review window elapsed. It loads the ledger
  tolerantly (`require_complete=False`, `strict=False`) so pointing `--rules`
  at a fixture the committed ledger was never meant to cover — as the
  harness's own tests already do — degrades to the `machine_linked` default
  rather than raising. This is visibility only: it cannot change which rules
  match an intake or promote, demote, or otherwise write to the ledger.
- Added a prepared, not-yet-adopted rule verification-level ledger
  (`src/permit_pathways/rule_verification.py`,
  `data/validation/rule-verification.json`) with explicit `machine_linked`,
  `human_reviewed`, and `jurisdiction_approved` states, as AGENTS.md's
  evidence rules describe. A promoted level binds to the rule's exact
  citation fingerprint and a 180-day review window; strict loading rejects
  duplicate, orphaned, unauthorized-metadata, pre-dated, and
  citation-drifted entries, and `effective_status` fails a claim closed back
  to `machine_linked` once its review window elapses. All 19 current rules
  are recorded `machine_linked`; none has an actual named reviewer or
  jurisdiction sign-off yet, and the ledger has no browser, CLI, or
  evidence-page surface yet. It never changes which rules match an intake.
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
