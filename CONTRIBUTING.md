# Contributing to Permit Bearings

## If you are not here to write code

The engineering is not what is blocking this project. Read the exit-gate table
in `docs/BETA-ROADMAP.md` and the dependency column keeps saying the same
thing: External jurisdiction. External reviewers. External recruitment.
External partner.

Two of those are things a stranger can start today:

- **You work for a California jurisdiction, or know one.** Issue #114 is one
  partner jurisdiction and one detached-ADU workflow, and twelve other roadmap
  issues wait behind it. It asks for a conversation, not a procurement: no
  money, no contract, no applicant data, no integration.
- **You have a screen reader and 20 minutes.** All 21 manual accessibility rows
  read `not_run`, and the screening form has never been driven by one.

[`docs/HELP-WANTED.md`](docs/HELP-WANTED.md) says what each asks, what it does
not ask, roughly what it costs, and - importantly - what a session report can
and cannot do to the manual record while the deployment lock is unfilled.

Read `AGENTS.md`, `docs/PRODUCT-CONTEXT.md`, `docs/DESIGN.md`, and
`PROVENANCE.md` before changing product behavior or public claims. The
repository's core rule is claim discipline: a candidate route is not an
eligibility finding, source linkage is not human approval, and a synthetic
presence screen is not packet completeness.

## Commercial solicitation

Issues here are not open to bids. They are design records — written so a decision is
reconstructable later — not scope documents for outside quoting, and unsolicited offers to
implement one for a fee will be declined.

Contributions through the normal fork-and-PR process are welcome, and `good first issue` is the
place to start.

## Verify a change

Use Python 3.12 and `uv`, then run:

```sh
make verify
```

That command installs the locked development environment and runs the same
format, lint, strict type, test, branch-coverage, dependency, SAST,
generated-bundle, browser-unit, and no-fetch verification gates used by CI.
The separate CI secret-scan job checks full repository history.

`make verify` needs **Node.js 24** as well as Python, and refuses to start
without it. Eight cross-runtime contract tests execute `assets/demo.js` under
Node, and the browser unit suite in `tests/browser/` runs the shipped browser
file directly. Those used to be skipped silently when Node was absent, so the
command could pass with the entire browser runtime untested. Use `make test`
for the Python-only subset when that is genuinely what you want.

Two coverage numbers are enforced, and they are not the same measurement:
85% branch coverage of the `permit_pathways` package, and 20% line / 17%
function coverage of `assets/demo.js`. The second is a ratchet on a file that
had no coverage gate before. Raise it when you add browser tests; do not
quote it as though it were the first.

Before opening a pull request:

- add tests for positive, negative, boundary, ambiguous, and
  wrong-jurisdiction behavior as relevant;
- rebuild `data/demo-data.js` after canonical data changes;
- update capability status and public claims when behavior changes;
- update `CHANGELOG.md` under `[Unreleased]`; and
- run `git diff --check`.

Do not include applicant PII, credentials, private permit files, or
model-provider payloads. Report vulnerabilities through `SECURITY.md`.
