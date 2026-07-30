# Threat model

STRIDE-style review of the static showcase, Python reference server, source
watcher, generated-data build, and CI supply chain.

## Assets and trust boundaries

The protected assets are deterministic match integrity, citation and source
currency, fail-closed explanation display, synthetic-sample labeling, and the
absence of applicant persistence. Trust boundaries are canonical JSON and
retained public sources, remote source retrieval by the scheduled watcher,
browser rendering from the generated bundle, HTTP form input to the reference
server, and GitHub Actions dependencies.

## Threats and controls

| Threat | Current control | Residual status |
|---|---|---|
| Model prose creates or changes a route | Matching does not import explanation data; parity and trust-contract tests | Low for the encoded path |
| Stale or mismatched evidence yields action copy | Source dates and fingerprints fail closed while preserving the deterministic match | Low; source discovery remains incomplete |
| Crafted intake or source data injects browser markup | Structured validation and escaping helpers; static tests exercise unsafe strings | Medium; automated browser SAST and CSP deployment review remain open |
| Watcher fetches an unsafe scheme or credentialed URL | Registry loader accepts only credential-free HTTPS URLs before retrieval | Low |
| Real applicant data enters the public demo | No upload, storage, telemetry, account, or model-call surface; synthetic packet is visibly labeled | Medium because users can still type facts into page memory |
| Generated bundle drifts from canonical JSON | Deterministic build check compares committed output with canonical inputs | Low |
| Compromised CI dependency executes mutable code | Actions are SHA-pinned, permissions scoped, checkout credentials not persisted, lockfile committed | Medium pending standards CI and branch-ruleset verification |
| Secret reaches repository history | Local pre-commit hook and automatic full-history Gitleaks job | Medium; hook installation is voluntary |

## Abuse and failure cases

- A user supplies HTML-like text in a form. It must be escaped before any
  `innerHTML` sink; tests must fail if executable markup appears.
- A source changes or becomes unreachable. Dependent guidance becomes stale
  and action-oriented copy is withheld rather than guessed.
- A contributor edits `data/demo-data.js` directly. The build drift check
  fails because generated output no longer matches canonical JSON.
- A deployer adds storage or telemetry without updating the data flow. That is
  a boundary change requiring a new DPIA, retention plan, and ADR before use.

Status: prototype review. Last reviewed 2026-07-29; recheck on every trust
boundary, deployment, source-ingest, or data-flow change.
