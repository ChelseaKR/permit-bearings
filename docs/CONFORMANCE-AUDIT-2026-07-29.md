# Portfolio standards conformance audit — 2026-07-29

Scope: `permit-pathways` against the current local
`~/portfolio/STANDARDS` checkout. This is a dated engineering audit, not a
legal, accessibility, security, or regulatory certification.

## Outcome

The standards Tier-1 file-based checker improved from **6/30** to **31/31**
after remediation. That score means its deterministic presence and
configuration checks pass; it does not close the review gates below.

The separate honesty-gates checker improved from **1/9** to **8/9**. Its sole
remaining notice is the absence of a hardened signed-tag release workflow.
That is intentionally N/A under accepted ADR 0001 because this repository does
not publish a versioned artifact. The portfolio checker recognizes this
reasoned N/A; the standalone honesty checker does not inspect that ADR.

## Verification evidence

| Check | Result |
|---|---|
| `make verify` | Pass |
| Tests | 160 passed on Python 3.12.13 |
| Branch coverage | 81.14%; interim gate 80%, portfolio target 85% |
| Ruff | Pass with canonical rule families and ten named complexity exceptions |
| Mypy | Strict mode, 0 errors across 14 source files |
| Bandit | Pass; one justified B310 suppression after HTTPS registry validation |
| Runtime dependency audit | Pass; package has zero runtime dependencies |
| Generated bundle check | Pass |
| No-fetch verification harness | Pass |
| Actions pinning | 6/6 external action references pinned to full commit SHA |
| Workflow token permissions | 2/2 workflows explicitly scoped |
| Live GitHub rulesets | None |
| Classic protection on `main` | None; GitHub returned “Branch not protected” |
| Repository visibility | Public; default branch `main` |

## Remediated in this pass

- moved the declared Python floor to 3.12 and committed `.python-version`;
- adopted Hatchling, PEP 735 development dependencies, and `uv.lock`;
- added canonical ruff, strict mypy, pytest, coverage, Bandit, and pip-audit
  configuration;
- corrected 26 strict-type errors in the shipped package and made formatting
  and linting clean;
- added a root `make verify` and made CI call it;
- pinned every GitHub Action, removed persisted checkout credentials, scoped
  workflow permissions, and added CI concurrency;
- added automatic full-history Gitleaks scanning;
- added `SECURITY.md`, `CONTRIBUTING.md`, `CODEOWNERS`, `CHANGELOG.md`,
  `CITATION.cff`, pre-commit hooks, ADRs, a threat model, a responsible-tech
  audit, an i18n declaration, a data card, and a metrics ledger; and
- added an accurate README standards table that distinguishes implemented
  gates, reasoned N/A, and open work.

## Open findings

### P0 — central scope and publication decision are missing

`permit-pathways` has no entry in `STANDARDS/applicability.yml`. The checker
therefore reports “unscoped” and scores every control instead of applying an
owner-approved archetype, tier, publication state, flags, and reasoned N/A
decisions. The repository is publicly visible, so the portfolio publication
gate cannot confirm that public visibility was cleared.

Disposition: blocked on an owner-level central standards change. The
`STANDARDS` worktree already contained unrelated uncommitted changes,
including `applicability.yml`, before this audit; this pass did not overwrite
or mix with them.

### P0 — `main` is unprotected

Live GitHub inspection returned no repository rulesets and no classic branch
protection for `main`. Force-push/deletion prevention and required checks are
therefore not enforced by repository policy.

Disposition: open external control. Create the solo-maintainer ruleset profile
only after the exact required check names are confirmed from a successful CI
run. This audit did not change live repository settings.

### P1 — standards consumer workflow is not installed

The repo does not fetch a pinned `portfolio-standards` release in CI, so
standards freshness and central applicability drift are not checked on pull
requests. Installing the canonical workflow also requires the repository's
read-only `STANDARDS_DEPLOY_KEY` secret and central consumer registration.

Disposition: open with the P0 central registration work.

### P1 — quality floors are not fully met

Measured branch coverage is 81.14%, below the portfolio's 85% application
floor. The 80% gate is intentionally labeled interim. Ten validation/evaluation
functions exceed cyclomatic complexity 10 and carry narrow `noqa: C901`
annotations. The checker confirms that a ceiling is configured; it does not
prove those exceptions satisfy the standard.

Disposition: add tests for invalid, stale, unknown, and fallback branches;
then refactor or formally waive the named complex functions. Do not raise the
coverage number without measured evidence.

### P1 — accessibility auto- and review-gates remain open

Static regression tests and limited viewport/contrast evidence exist, but
blocking axe, pa11y, and Lighthouse checks are not wired. Keyboard-only,
forced-colors, VoiceOver, NVDA, and Spanish pronunciation reviews have not
been completed.

Disposition: open. No WCAG conformance or human assistive-technology testing
claim may be made.

### P1 — Spanish semantic acceptance remains open

The civic-facing bilingual surface has no standards-backed catalog parity
gate or named human semantic review. Spanish explanations remain machine
drafts, and source-derived content is partly English.

Disposition: pre-pilot blocker for applicant-ready Spanish guidance.

### P2 — performance, data-card breadth, and security depth remain open

There is no committed Lighthouse performance baseline or >10% regression
gate. Public-source lineage is strong in `data/sources.json`, but the new data
card consolidates many distinct publishers rather than providing one card per
ingest source. CodeQL, Scorecard, workflow SAST, and live ruleset evidence are
not yet present.

Disposition: sequence after central registration, branch protection,
coverage/complexity, and accessibility.

## Claim boundary

Passing Tier-1 checks means the configured files and gates were mechanically
found. It does not mean all portfolio standards conform, that GitHub policy is
effective, that human review occurred, or that the permitting prototype is
approved for real applicant use.
