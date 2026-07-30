# Contributing to Permit Bearings

Read `AGENTS.md`, `docs/PRODUCT-CONTEXT.md`, `docs/DESIGN.md`, and
`PROVENANCE.md` before changing product behavior or public claims. The
repository's core rule is claim discipline: a candidate route is not an
eligibility finding, source linkage is not human approval, and a synthetic
presence screen is not packet completeness.

## Verify a change

Use Python 3.12 and `uv`, then run:

```sh
make verify
```

That command installs the locked development environment and runs the same
format, lint, strict type, test, coverage, dependency, SAST, generated-bundle,
and no-fetch verification gates used by CI. The separate CI secret-scan job
checks full repository history.

Before opening a pull request:

- add tests for positive, negative, boundary, ambiguous, and
  wrong-jurisdiction behavior as relevant;
- rebuild `data/demo-data.js` after canonical data changes;
- update capability status and public claims when behavior changes;
- update `CHANGELOG.md` under `[Unreleased]`; and
- run `git diff --check`.

Do not include applicant PII, credentials, private permit files, or
model-provider payloads. Report vulnerabilities through `SECURITY.md`.
