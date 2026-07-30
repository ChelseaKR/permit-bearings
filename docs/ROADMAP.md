# Engineering roadmap and metrics ledger

Last reviewed 2026-07-29. Product priorities remain canonical in
`docs/PRODUCT-CONTEXT.md`; this file records portfolio-standards adoption and
measurable engineering gaps.

## Metrics ledger

| Attribute | Current value | Gate / disposition |
|---|---|---|
| Python | `>=3.12`, pinned by `.python-version` | AUTO |
| Ruff | `>=0.15`, canonical rules, complexity ceiling 10 | AUTO, with 10 named legacy function exceptions tracked below |
| Strict typing | 0 errors across `src/` | AUTO |
| Branch coverage | 81% measured on 2026-07-29 | AUTO at 80% interim; 85% target open |
| Golden screening cases | 29 structured fixtures | AUTO; not natural-language evaluation |
| Bundle parity | Canonical JSON equals generated static bundle | AUTO |
| Source currency | 17 watched sources; weekly alert workflow | AUTO alert; human queue remains open |
| Accessibility automation | Static regression checks only | GAP: axe, pa11y, Lighthouse not wired |
| Human accessibility | No completed VoiceOver/NVDA walkthrough | REVIEW open |
| Translation parity | Spanish machine drafts, no named semantic review | REVIEW open |
| Data classification | L1 public sources plus synthetic fixtures | REVIEW current; per-source card expansion open |
| Runtime data retention | None in public demo | REVIEW on any boundary change |
| Release pipeline | N/A: no versioned artifact | Accepted ADR 0001 |
| Observability | Tier B static surface plus Tier C local reference server | N/A for service SLOs; deployment monitoring open |
| Performance | No committed Lighthouse baseline | GAP: frontend performance gate open |
| AI development measurement | No runtime model; AI-assisted artifacts disclosed | REVIEW; local-only tool metrics not yet recorded |

## Remediation order

1. Register `permit-pathways` in the portfolio applicability manifest and add
   the pinned standards-consumer workflow without disturbing the standards
   repository's existing uncommitted work.
2. Raise branch coverage from 81% to the 85% application floor, emphasizing
   stale/invalid/unknown evidence paths.
3. Refactor or formally waive the ten schema/evaluator functions currently
   above cyclomatic complexity 10; current `noqa` annotations are visible
   debt, not proof that the ceiling is met.
4. Add blocking axe, pa11y, and Lighthouse checks over all five pages, plus a
   committed performance baseline.
5. Complete keyboard, forced-colors, VoiceOver, NVDA, and native Spanish
   review with dated human artifacts.
6. Expand the public-source data card into one card per distinct ingest source
   and add automated enumeration against `data/sources.json`.
7. Verify live branch ruleset status and add the remaining portfolio security
   workflows (CodeQL Actions/Python, Scorecard, and standards freshness).

No item above changes the product priority order in `AGENTS.md`.
