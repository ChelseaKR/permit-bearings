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

## Renew a program-availability reading

A record under `data/availability/` states that a person opened a
jurisdiction's page on `checked_on` and read what its `excerpt` says.
`recheck_due_on` is when that reading stops counting. Once it passes, the beta
gate appends the blocker `reference_program_availability`, the packet journey
renders its hold branch instead of the applicability radio group, and the
flagship packet is locked. That is the designed behaviour: the product fails
closed rather than publishing a reading nobody has confirmed. It also means
`main` goes red on a calendar boundary with no commit behind it, which is what
happened on 2026-09-09 (#164).

**It is renewed by a person, not by a fetch.** `monitoring_status` is
`manual_date_bound`. Writing a later `checked_on` without opening the page
publishes an attestation nobody made, which is the one thing this record exists
to prevent. Do not move the date to make a check pass.

Advance notice: the weekly `Source currency watch` prints
`program_availability_due=N program_availability_records=M` on its
`currency signals:` line and annotates the run when a reading lapses before the
next scheduled run. The lead time is derived from that workflow's own cron, so
changing the schedule widens the notice with it.

Steps, in order:

1. Open the `source.url` recorded in the availability record and read the page.
2. If the wording has changed, `excerpt` and `excerpt_sha256` change with it
   (`excerpt_sha256` is `sha256:` plus the digest of the normalised excerpt --
   `permit_pathways.program_availability.excerpt_fingerprint`). If the program
   *status* has changed, this is no longer a date renewal: route it to
   `content_source_owner` before editing anything.
3. Update `data/availability/<record>.json`: `checked_on` to the date you read
   the page, `recheck_due_on` no more than `MAX_RECHECK_INTERVAL_DAYS` (31)
   after it.
4. Update `answer_key.program_availability` in
   `data/validation/woodland-flagship-gate.json` to match. These two files must
   move together, and the beta gate compares them field for field
   (`external gate.answer_key.program_availability`), so a half-renewal fails
   loudly rather than half-applying.
5. Rebuild the generated browser bundle: `python scripts/build_demo_bundle.py`.
   `make bundle-check` runs the `--check` form and fails until you do.
6. Re-pin the digests taken over the record's own bytes, which `recompute` does
   not write: `artifacts.program_availability.sha256` in
   `data/workflows/registry.json`. Leave it stale and step 7 refuses with
   `registered fingerprint does not match` rather than half-applying.
7. Recompute the prepared gate:
   `python -m permit_pathways.beta_gate_cli recompute --write`. It writes the
   v2 export profile's digests and the record's own pins, and **refuses**
   `_EXPORT_PROFILE_V2_SHA256` in `src/permit_pathways/beta_gate.py` — that one
   is the tamper-evidence anchor over the profile, so it prints the value and a
   person writes it. Edit it, then run `recompute` again until it reports that
   every pin already matches the tree. `_NOT_RUN_ARTIFACT_SHA256` beside it is
   an immutable not-run ledger that `recompute` never touches at all: its
   `external_evidence_gate` entry is the digest of
   `data/validation/woodland-flagship-gate.json`, so step 4 moves it and only a
   hand edit puts it back.
8. The prose that states when the page was checked moves with it. `grep -rn`
   the old date and read each hit: several documents carry the same date string
   for a different reason (`docs/ACCESSIBILITY.md`'s own audit and axe-run
   dates, `TEMPLATE_PUBLISHED_ON` in `local_source_onboarding.py`), and those
   do not move.
9. Run `make verify`, then `npm run test:a11y`. No test clock has to move with
   the record: `tests/attestation_clock.py` derives the suite's frozen dates
   from the record, and the packet-page specs run against a fixture anchored to
   the run's own UTC date, with the committed record's currency asserted by one
   test that names the file. Before that was true the renewal described here
   reported **71 failures and 27 errors**, all of them about the fixtures
   rather than about the page, and the thirty-day recheck had never once been
   satisfiable.

This lives here rather than in `docs/BETA-OPERATIONS-RUNBOOK.md`, which would
be the obvious home, because that document's bytes are bound by
`data/validation/beta-operations-readiness.json` and `beta_gate_cli recompute`
**refuses** to re-pin them: `document_bindings[1].sha256: bound document bytes
changed`. Editing the runbook is an attested act, not an editorial one.
