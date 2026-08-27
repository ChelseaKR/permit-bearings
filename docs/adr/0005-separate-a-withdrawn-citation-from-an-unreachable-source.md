# Separate a withdrawn citation from an unreachable source

- Status: Accepted
- Date: 2026-08-27
- Decider: Chelsea Kelly-Reif

## Context

`AGENTS.md` already draws one line the watcher enforces: a source that was
fetched and whose hash moved is *changed*, and a source the fetch could not
reach is *unverifiable*. Only the first stales dependent rules. The second is
"evidence about the network, not about the law".

Running `python -m permit_pathways.harness --fetch` on 2026-08-27 showed that
one line is not enough. Thirteen watched sources came back unverifiable in a
single run, and they were two entirely different findings wearing one label:

- Twelve leginfo statute pages failed with
  `[SSL: CERTIFICATE_VERIFY_FAILED] ... unable to get local issuer certificate`.
  That is the local machine's trust store. It says nothing about the statutes.
- `davis-adu-handout-2026` failed with `HTTP 404 Not Found`. The server
  answered, and its answer was that no document is published at that address.

The consequences differ completely. The first is a fact about one run and
resolves itself. The second is permanent until a person finds the document's
new home, and it is visible to applicants: `data/rules/davis.json` carries
that exact URL as rule `davis-local-adu-process`'s own `citation.url`, and
that rule matches every Davis ADU or JADU screen. The static result card
rendered it as a live link beside a "Source evidence on file" badge, so the
one promise on the front of the README, "See the sources behind the result",
resolved to a 404 page for the flagship comparison jurisdiction. Issues #91
and #96 are two independent reports of this, one from an outside harness.

Reporting them together also blocks the obvious fix. Surfacing raw
`unverifiable` on the applicant-facing card would, on the run above, have
warned about twelve statutes because of a certificate on one laptop. That is
the same false alarm the `changed`/`unverifiable` split exists to prevent,
one level down.

## Decision

Every unverifiable observation carries a `kind`.

- `transport` — no authoritative answer arrived: DNS, TLS, timeout, reset,
  5xx, throttling, a 403 refusal, a WAF block. Unchanged behaviour. Reported
  as a run fact, marks nothing, and keeps the retry budget.
- `not_found` — the server answered HTTP 404 or 410 about that exact address.
  Retries stop after the first attempt, because asking again cannot change an
  answer. Reported as its own finding, in the run summary, in the harness
  report derived from the adopted receipt, and on the evidence page.

A `not_found` source still never stales a rule, never changes a match, never
suppresses an excerpt, a note, or action copy, and never changes an exit code.
The one thing it changes is the link: a rule whose own `citation.url` resolves
to a `not_found` source is rendered with its citation as text rather than as
an anchor, beside a sentence saying the official link did not open, that the
quoted text comes from the copy this project retained, and that the current
document should be requested from staff. `assets/demo.js` and `demo/app.py`
both do this, and a test asserts they agree.

The kind is required exactly on an unverifiable observation and forbidden
elsewhere, so `data/source-status/current.json` — which records no
unverifiable observation — is byte-identical and keeps its fingerprint. An
unverifiable observation without a valid kind is rejected by both the Python
loader and the browser validator: a failure the reader cannot describe
honestly is not one to render.

## Alternatives considered

- **Repoint the citation URL.** Issue #96's suggested fix, and the right one
  once the document's new address is known. It was not available here: the
  City of Davis site answers `403` to a non-browser client, so no replacement
  URL could be verified, and inventing one is exactly what this repository
  must not do. Recording what was observed is the honest move, and the
  mechanism is needed regardless because the next dead link is a matter of
  time.
- **Treat a 404 as `changed`.** It is not. The retained copy and its recorded
  hash still stand, no new text was read, and staling nineteen rules because a
  city reorganised a website would be a false claim about the law.
- **Fail the build on a withdrawn citation.** Rejected. The maintainer may
  not be able to fix it in the same run, as this change's own author could
  not. It is reported loudly instead. What does fail closed is the schema: an
  unverifiable row with no kind, or a kind on a fetched row.
- **Widen the finding to any rule that depends on a withdrawn source.** Not
  done. The applicant-facing promise is about the single link the result card
  prints, so the derivation is bound to `citation.url`.

## Consequences

The distinction is dormant on the committed receipt, which records every
source as `unchanged`. It becomes visible the first time a maintainer adopts
a watch receipt taken while a cited address is gone. Until then the harness
says so in as many words rather than staying silent.

Deciding what a 403 means is deferred. Today it is `transport`, because a
refusal to answer is not an answer about the document. If a publisher starts
returning 403 for withdrawn material, that is a new decision, not a quiet
widening of `not_found`.
