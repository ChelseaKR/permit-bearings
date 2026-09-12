# Changelog

All notable changes to this project are recorded here. The project has not
published a versioned release.

## [Unreleased]

### Changed

- **The City of Woodland program page was re-checked on 2026-09-10, and the
  suite can now accept a re-check.** The page has gained real program content
  — the City is accepting designer submissions, with steps, a permit
  checklist and fee rules — but under the **Preapproved ADU List** heading it
  still reads *“Coming soon!”*. The recorded excerpt is unchanged and its
  `sha256` still matches byte for byte, so `status: plans_not_listed` and
  `mode: future_state_simulation` remain accurate and only `checked_on` and
  `recheck_due_on` move.
  - **The thirty-day recheck control had never once been satisfiable.** Test
    files pinned a literal “today”, every one of them earlier than any date a
    real renewal could carry, and `load_program_availability` refuses a record
    whose `checked_on` is in its future. Moving the two dates on their own
    turned **71 tests red with 27 errors**, against 1 failure on `main`, and
    dropped coverage below its floor. A record that expires every thirty days
    by design could not be renewed.
  - `tests/attestation_clock.py` reads the attested dates out of the record,
    and five suites now freeze their clocks from it: program availability, the
    beta gate, the evidence export and its signatures, and the browser journey
    contract. Renewing the attestation is a data edit again.
  - **No gate was relaxed, and two controls say so.** The committed record
    still blocks the beta gate on the first day past its recheck deadline and
    not on the day before it; a check date in the gate's own future is still
    refused; and the browser contract still withholds the packet handoff one
    day past the deadline. The excerpt fingerprint is compared unchanged.
  - **`make evidence-export-check` froze its disposable archive on a literal
    `2026-08-09`.** The restore replays every record against the manifest's own
    `frozen_on`, so that literal became earlier than the evidence the archive
    carries the moment the page was re-checked, and the round trip would have
    failed for a reason that has nothing to do with the export. It now freezes
    on the run's own UTC date, read once so both builds inside the target
    agree across a midnight boundary. The two documented example commands were
    carrying the same literal and are fixed with it.
  - **The record's bytes are pinned in four other artifacts and mirrored in a
    fifth**, so the renewal carries that closure: `data/workflows/registry.json`,
    the regenerated `data/demo-data.js`, the v2 export profile, the
    `program_availability` block of `data/validation/woodland-flagship-gate.json`,
    and, downstream of those, `data/validation/pilot-beta-gate.json` and
    `_EXPORT_PROFILE_V2_SHA256` in `src/permit_pathways/beta_gate.py`
    (`beta_gate_cli recompute --write` derives the last two). The frozen v1
    export profile keeps its historical digests, as its own identity test
    requires. **Thirteen prose sentences** across the README, `PROVENANCE.md`
    and six documents state when the page was checked and move with it;
    `docs/ACCESSIBILITY.md`'s own audit and axe-run dates and
    `TEMPLATE_PUBLISHED_ON` share the date string, mean something else, and do
    not move.

### Added

- **A watch over the seven scanned ordinances, and a gate over the bytes they
  were scanned from.** Every published conformance result names a real
  California city and says its ordinance carries specific defects, on the
  strength of text retrieved once in July and August. Nothing monitored those
  sources afterwards, and the results said so in their own disclaimer (part of
  issue #136).
  - `corpus/ordinances/SOURCES.json` entries gain a `watch` block: the SHA-256
    of the committed text, and the chapter or section designation the document
    must carry. Neither existed before. The digests recorded in the `note`
    prose are **truncated hashes of the retrieved pages**, and this repository
    does not keep those bytes, so no reader could ever check one against
    anything here; the new digest is over the text the scanner actually reads.
  - `scripts/scan_ordinances.py --check`, already in `make bundle-check`, now
    also holds every committed text to that digest. It re-derived the results
    *from* the corpus before, which proves the results match the corpus and
    cannot notice the corpus itself moving: an edit no check matches changed
    nothing it compared.
  - `scripts/watch_ordinances.py` re-reads all seven and reports each as
    unchanged, changed, or unverifiable by kind, on the weekly
    `Source currency watch` schedule.
  - **The comparison is findings, not content hashes, and that is measured
    rather than assumed.** Re-extracting all seven with this repository's own
    extractor reproduced the committed text **byte-for-byte zero times out of
    seven** — publishers reflow markup, and a PDF extractor is not the one that
    produced the committed conversion. A digest watch would have called every
    source changed on its first run, which is how a watch gets switched off in
    its first week. The findings rule reported **five unchanged and two
    changed** on the same bytes.
  - **A `200` is not evidence that the page is the document.** One of the seven
    publisher URLs now answers `200` with a code-migration notice, and scanning
    that notice yields **zero findings** — a clean bill of health for a city
    whose ordinance nobody read. A page that does not carry its declared
    identifier is `unverifiable/not_the_document`, never `changed`.
  - **The watch proposes; it never adopts.** Re-scanning republishes a
    statement about a named city. The workflow files one undated, labelled
    issue saying what moved and leaves the re-scan to a person.
  - `data/export/public-synthetic-evidence-v2.json` and
    `_EXPORT_PROFILE_V2_SHA256` re-pinned for the one changed file, through
    `beta_gate_cli recompute`'s maintainer-attestation path: the profile diff
    is a single entry (`corpus/ordinances/SOURCES.json`), and the new constant
    was confirmed against `shasum -a 256` independently of the tool.

- **An evaluation set for `/ask`, and the scorer that reads it.** The
  capability table said "no evaluation set covers `/ask` yet" while the other
  two runtime endpoints had committed cases and recorded numbers, so the most
  consequential surface — the one that answers a question in prose — was
  measured by two anecdotes in the README (issue #139).
  - `evals/ai/ask-cases.json`: **44 questions over the same eight
    confirmed-fact intakes** as the grounding suite, 28 English and 16
    Spanish, every label present in both languages. Each is
    `answerable_from_passages` (23), `should_abstain` (10), or
    `should_refuse_scope` (11).
  - `permit_pathways.ai.eval ask` scores `claims_shown`, `claims_withheld`,
    `abstained_when_expected`, `answered_when_should_abstain`,
    `scope_refusals` and `answered_out_of_scope`. `make ai-eval` runs it.
  - **`abstained_when_expected` means deferred to staff, not silent.** The
    live behaviour already seen for a fee question was a *cited* statement
    that the sources set no fee plus a staff question. That is a better answer
    than silence, and scoring it as a failure to abstain would push the model
    towards saying nothing. The defect counted instead is claims shown with
    nothing flagged for a person.
  - **Out-of-scope questions are zero tolerance and counted, not rated.** A
    claim shown for "what is my property worth?" is an answer assembled from
    passages retrieved for a different question, and one is one too many.
  - **An answerable case must record the passages that would settle it**, and
    the loader refuses one that does not: a case with nothing recorded would
    score whatever the model did and call it right. A separate test asserts
    every recorded settling passage is one the retrieval actually offers for
    that question — otherwise the metric would measure the retrieval's silence
    while reading as a statement about the model.
  - **The `not_run` contract is now enforced, not merely declared.** A record
    with `status: not_run` may carry no numeric summary and no cases. The
    status string was previously the only thing checked, so a placeholder
    could have published a summary full of figures — the portfolio's
    "absence rendered as a value" shape, one level up from the data.
  - **No `ask` result is committed.** The numbers need one live run on a
    configured provider, and a file naming a model nothing has answered is
    exactly what that contract refuses. The README and the capability row both
    say so rather than implying the suite has been run.

- **A local-inference provider, so the applicant's own words can stay on the
  operator's host.** `PERMIT_AI_PROVIDER=local` points the same runtime AI
  service at an OpenAI-compatible chat-completions endpoint on localhost or
  the jurisdiction's own network (`PERMIT_AI_LOCAL_URL`, a required
  `PERMIT_AI_MODEL`, an optional `PERMIT_AI_LOCAL_API_KEY`), over plain HTTP
  from the standard library. No second SDK, no streaming, no bundled weights
  or runtime, and the Lambda deployment is unchanged (issue #138).
  - **It removes a subprocessor, not a control.** Every guard the AI layer
    rests on — allowed-value checks, verbatim quote binding, corpus
    verification, withheld counts — runs in this service on the model's
    output, above the provider interface, so it applies identically whichever
    endpoint answered. A test runs the same fixed response through the
    scripted provider and through a stub local endpoint and asserts the
    extracted structure is equal except for the provider name, model, and
    token usage; another asserts that a quote the applicant never wrote is
    downgraded to `unknown` on the local path exactly as on the hosted one.
  - `/health` now reports `provider_kind`, `hosted` or `local`, so a page can
    label where the text goes without keeping a list of provider names in
    step with this module.
  - **No default model name, on purpose.** Every self-hosted runtime serves
    something different, and a guessed default would reach the endpoint as a
    request for a model it does not have — an error about the wrong thing, at
    the first applicant request rather than at startup. `PERMIT_AI_LOCAL_URL`
    is likewise validated at startup: HTTP(S) only, no inline credentials, no
    fragment.
  - An unreachable endpoint, an HTTP error, a truncated answer, a
    content-filter stop, an empty completion and an HTML error page served
    with HTTP 200 all raise `ProviderError`, which every endpoint already
    turns into a 503, so the page stays static rather than showing a partial
    answer. A `usage` block the runtime omitted counts as zero rather than
    being invented; the budget counts requests, not tokens, so a missing
    count cannot buy anyone a larger allowance.
  - The committed-results contract now accepts `local` beside the two hosted
    providers. Leaving it out would have made that contract reject the first
    honest local result, which is the opposite of what it is for; it stays an
    allowlist, so a result naming a provider this package cannot build is
    still refused.
  - `make ai-eval` runs both suites against `local`, and the output filename
    now survives a model name containing `:` or `/`. **No local result is
    committed**: running one needs a host with the runtime and the weights,
    and a result naming a model nothing has answered is the placeholder this
    directory's contract test exists to refuse. What a smaller open-weight
    model costs in abstention and citation resolution is a measurement to
    take, not an assumption to publish.

- **Walking distance over an offline pedestrian network, reported beside the
  straight line.** Both transit standards are written in walking distance
  (§ 66322(a)(1): "within one-half mile walking distance of public transit")
  and `transit.py` measured a straight line, which the README described as
  able to eliminate a stop but not establish one. That asymmetry is
  systematic, not incidental: a stop across a freeway or a creek is a quarter
  mile as the crow flies and a mile and a half on foot, so the straight-line
  answer errs in the direction that matters (issue #134).
  - `permit_pathways.pedestrian` builds a walkable graph from an OSM XML
    extract (`.osm`, `.osm.gz`, `.osm.bz2`) or a pre-built graph (`.json`)
    and measures the shortest walk. `transit.py --pedestrian-network` reports
    it per stop, `--snap-max-meters` sets the snap limit. Nothing is fetched
    and no routing service is called.
  - **No third-party package, and therefore no optional extra.** The reader is
    the standard library's `iterparse` and the search is `heapq`, so there is
    nothing to install and nothing new in the lockfile. A test proves the
    default screening path never imports the module. PBF is deliberately
    unsupported and says so by name rather than failing on binary; `osmium cat`
    converts it in one command.
  - **The graph rules are written down, in ADR 0007**, not inferred at read
    time. `motorway`, `trunk`, `construction`, `proposed`, `raceway` and
    `bus_guideway` are never walkable *whatever else they are tagged* — a
    `foot=yes` on a motorway is a mapped shoulder, not a footpath — and
    `foot=no` or `access=private` removes an otherwise walkable way. Edges are
    undirected: `oneway` restricts vehicles.
  - **Three states carry no number, by name:** `not_in_extract`,
    `snap_too_far`, `disconnected`. None is ever filled in from the straight
    line, which is the substitution the check exists to prevent, and a clipped
    extract makes the last two common near its edge, so neither is treated as
    evidence against a stop.
  - **It changes no verdict.** Parking and height stay straight-line, because
    which distance a jurisdiction applies to a given screen is a legal
    judgement this tool does not make; the summary says so where it prints the
    numbers. Without the flag the run is straight-line only and prints no
    walking block at all.
  - Two committed OSM fixtures differ in exactly one tag — way 104 is a
    freeway ramp in one and a footbridge in the other — so the barrier case
    measures 300 m straight-line and 1,400 m walking, and removing the barrier
    makes them agree. A test asserts the two files differ *only* in that tag,
    so the comparison cannot quietly start proving something else. The
    extract's SHA-256 and bounds travel with every result.

- **A what-if explorer: which rules and routes change when one answer
  changes.** `permit_pathways.what_if` re-runs the deterministic matcher once
  per allowed value of one material fact at a time and reports the rule and
  route delta, reachable as
  `python -m permit_pathways.what_if --facts facts.json` and ported into
  `assets/demo.js` as `whatIfDeltas` (issue #130).
  - **Decision support without prediction.** Nothing says which answer is
    true, which is better, or what to do. Facts come in the form's order and
    values in the order the vocabulary declares them, so no branch is
    presented as preferable. Single-fact perturbation only: there is no search
    for a best path and no combination of two changes.
  - **Three states where a delta would be a lie, and what happens instead.**
    A branch that still leaves a material fact unanswered reports
    `needs_staff_review` and an empty `candidate_routes`, exactly as a real
    screening of that intake would — including the case where answering
    "unknown" matches the very same rules, so a reader of rule deltas alone
    would conclude that not answering costs nothing when it costs the route.
    A fact every rule reads the same way is reported as
    `no_rule_reads_this_differently` rather than dropped. And a fact read by a
    rule whose source the snapshot records as changed since it was last
    reviewed gets `null` deltas, never `[]`, plus the ids of the held rules:
    an empty delta reads as "changing this answer changes nothing", which is a
    finding about the rule set that a held rule set cannot support.
  - The hold is fail-closed on purpose. Every in-jurisdiction rule with a
    criterion on the fact counts, including one that cannot match this project
    type as encoded today, because a hold says the *encoding* may no longer
    match its source and narrowing the set would assume what the hold puts in
    doubt.
  - Its own `what_if_schema_version`, not the screening envelope's
    `schema_version`: they describe different documents, and moving the
    screening version would tell every screening consumer their contract had
    changed when it had not.
  - `tests/test_what_if_browser_parity.py` lifts the shipped port out of
    `assets/demo.js` and runs it under Node against all 29 Golden cases, twice
    each — once clean and once with a source on hold — and requires identical
    output, because `null` in one runtime and `[]` in the other render the
    same and mean opposite things. Expected Woodland deltas are hand-written
    in `tests/fixtures/what-if-woodland.json` rather than captured from a run.
  - **The disclosure on `check.html`.** `whatIfDisclosureMarkup` renders the
    explorer into a collapsed "See what would change if an answer were
    different" section under both result pages: the screened result and the
    staff-review result. It reuses the applicant-copy contract, so its
    seventeen strings exist in English and Spanish at key parity.
    - **Three states, three pieces of copy.** A fact on source hold renders
      the hold and *no branches at all*, because an empty delta drawn as a row
      is the claim a held rule set cannot support. A fact every rule reads the
      same way says so once, above the branches, instead of as a column of
      identical rows. And every branch states whether a path is shown for it
      even when its rules did not move: on the Woodland fixture, answering "I'm
      not sure" to the ADU-work question matches exactly the same rules as the
      real answer, so a disclosure showing only rule deltas would tell an
      applicant that not answering is free. It costs the route, and the page
      now says so on that row.
    - A rule is named by its own `pathway` record name, verbatim and marked
      `lang="en"`, the same way a result card names a route record. Interface
      copy is translated; a record name is not.
    - With no rule set loaded the disclosure renders nothing, rather than
      reporting that no rule has a condition on any question, which would be a
      finding about the rules and not about a failed load.
    - The branches explored are read from the English option identifiers, so
      the set of answers examined is identical in either display language.
    - `tests/browser/what-if-disclosure.test.mjs` covers it against the
      shipped file, asserting copy through the catalog rather than retyping
      it. The browser coverage floor moves 23% to 40% of functions, to what
      the suite now reaches.

- **The transit screen is calendar-aware.** `transit.py` takes `--as-of DATE`
  and measures peak headways only over the services `calendar.txt` and
  `calendar_dates.txt` say run on that date, after checking the date against
  the validity window `feed_info.txt` publishes. The result carries
  `service_date`, `service_ids_active`, `feed_valid_from`, `feed_valid_to`,
  `calendar_source`, and the service ids any exception added or removed
  (issue #132).
  - **What it stops.** The previous implementation read `calendar.txt` alone,
    kept whichever `service_id` had the most trips, and never opened
    `feed_info.txt` or `calendar_dates.txt`. A summer session, a holiday, and
    a feed that expired years ago all produced a headway, and which headway
    you got depended on which of the feed's service periods happened to be
    larger. That is a measurement standing in for one nobody made.
  - **Four states withhold instead of answering**, and each reports `unknown`
    rather than "no qualifying stop": `no_as_of`, `outside_feed_window`,
    `no_calendar`, and — the one negative a feed *can* support —
    `no_service_on_date`, which is the calendar saying nothing runs. There is
    deliberately no default to today, so a recorded run stays reproducible.
  - A candidate resting on the statewide Caltrans dataset is unaffected: that
    dataset carries its own currency and is not scoped by a local feed's
    calendar, so an unreadable feed suppresses nothing that never depended on
    it.
  - Every service active on the date is now measured, not just the busiest
    one, so a supplemental schedule sharing a weekday with a base schedule is
    no longer dropped whole.
  - `frequencies.txt` is still not expanded; a feed that ships one now says so
    instead of being measured around.
  - Over the committed Unitrans feed this is visible rather than theoretical:
    the feed declares itself valid 2026-07-20 to 2026-09-22 and ships two
    disjoint session calendars, so 2026-08-04 measures service `71` across
    sixteen routes and 2026-08-09 measures service `79` across two, while
    2026-09-07 — a Monday — runs `79` because `calendar_dates.txt` removes
    `71` and adds `79`. The repository's published finding is unchanged: no
    local bus stop meets the encoded ≤15/≤20-minute peak screens on any of
    those dates, and the Amtrak candidate still comes from the statewide
    dataset.

- **The evidence export can be signed, and an unsigned one says so.**
  `evidence_export_cli build --sign-key <key>` writes a detached OpenSSH
  signature to `<archive>.sig.json`; `verify` and `restore` take
  `--allowed-signers <file>` or `--use-repository-signers` (issue #137).
  - **The archive bytes are identical with and without signing.** The signed
    payload is a short canonical statement naming the archive's SHA-256
    together with the package id, freeze, commit and profile, so the ZIP format
    and the determinism gate are untouched and a signature cannot be moved to a
    different package.
  - **Absence is a state, never an inference.** An unsigned archive reports
    `absent`; a signature nobody asked to check reports `not_checked`. Neither
    is ever reported as `verified`, and an empty or comment-only signers file
    accepts nobody rather than reading as "cannot tell, so allow".
  - Three distinct exit codes, because the three findings call for different
    responses: `3` unsigned, `4` the bytes are not what was signed, `5` the
    signer is not listed. `ssh-keygen -Y verify` prints the same message for
    the last two, so listing is decided by parsing the signers file rather than
    by reading OpenSSH's wording.
  - When a signers file is supplied, **the signature is settled before the
    archive is opened**: one altered byte moves the digest the signature covers
    and is reported as a broken signature, not as a changed member. A refused
    `restore` therefore publishes nothing.
  - Without `--allowed-signers` nothing is gated, so every existing unsigned
    package and every prior `verify` invocation behaves exactly as before.
  - `make evidence-export-check` now round-trips both an unsigned and a signed
    build with a throwaway key, asserts the two archives are byte-identical,
    and asserts that the unsigned one fails an authenticity check.

- The source watch now reports, per rule, whether the text that rule quotes
  still occurs in a source whose content hash moved. A changed hash stales
  every dependent rule, which is correct and deliberately coarse: a footer
  edit on the HCD Handbook stales seventeen rules exactly as a rewritten
  height section would. The receipt and the harness now also answer the
  question a maintainer asks next — which of those rules lost the words it
  quotes — as `excerpt_survives`, `excerpt_lost`, or `not_checkable`.
  - **It un-stales nothing.** A rule whose excerpt survived is still on hold
    until a person re-verifies it: surrounding text can change what the same
    sentence means, and no string test sees that. Survival orders the
    worklist; it never shortens it. No exit code moves.
  - Matching is `ai.corpus.normalize_for_match`, the same normalization the
    AI layer's citation verifier uses, so "occurs verbatim" means one thing
    in this project rather than two. The document is read from the bytes the
    watch already fetched, so the check is not a second, differently-timed
    read of a moving target.
  - **A verdict is issued only where it is earned**, which over this corpus is
    the minority of cases. Depending on a source is not quoting it: thirteen
    of the fifteen rules that depend on the HCD ADU Handbook quote a statute
    and lean on the Handbook for context, so their text was never in that PDF.
    And this project's excerpts are curated citations rather than raw
    quotations — several carry editorial brackets condensing a list — so they
    do not occur verbatim even now. A rule is therefore given a verdict only
    when the changed document is the one it quotes *and* its excerpt occurs
    verbatim in the retained copy first. Everything else is `not_checkable`,
    carrying which of the two it was. Measured over the committed corpus that
    is 7 trackable and 37 not, with zero rules reported lost against a
    document that had not changed. Without those two rules the same corpus
    reported 36 losses against documents that had not changed at all, which
    is what the first real source change would have printed.
  - A source that could not be read reports `not_checkable` for every rule
    that cites it, carrying the reason, and may report nothing else. Both the
    Python loader and the browser bundle check refuse a receipt that claims
    `excerpt_survives` or `excerpt_lost` for an unverifiable source, and
    refuse the field entirely on an unchanged one: a verdict about words
    inside a document nobody opened is a claim that a check ran when it did
    not.
  - The field is additive and appears only where it was earned, so every
    receipt written before it existed stays byte-identical and keeps its
    fingerprint. The committed receipt is unchanged, and no digest it is
    pinned by moves.

- `beta_gate_cli recompute` re-derives the digests that ordinary maintenance
  moves, so re-pinning them stops being a hand-edit of a tamper-evidence
  chain. Two routine acts change bytes this repository pins by hash —
  refreshing the HCD accountability-letter snapshot (#63) and adopting a
  source-watch receipt (#140) — and both landed on the same four-step chain
  with no tooling: the v2 export profile's entry digests, the
  `_EXPORT_PROFILE_V2_SHA256` constant, the record's `artifact_bindings`
  digests, and the dependent `aggregate.artifact_set_fingerprint` and counts.
  Doing that by hand has already failed once, in #80: six binding digests were
  rewritten without recomputing the dependent fingerprint, and the record
  failed its own self-consistency check.
  - Every derived value comes back from `load_beta_gate` itself. `recompute`
    applies the digests it can read from bytes, lets the validator reject the
    aggregate, and takes the recomputed aggregate verbatim from the rejection,
    so it cannot re-pin to a value the validator would refuse.
  - It cannot promote anything. Schema v1's fixed aggregate — `not_run`, zero
    prepared gates, every stronger-claim boolean false — is what the validator
    recomputes, and a test asserts a re-pin reproduces it.
  - It refuses the immutable not-run planning ledgers outright rather than
    re-pinning them, naming the artifact, and writes nothing in that case.
    Their independent raw bytes are what stops a favourable nested result
    being rewritten together with its digest.
  - It reports `_EXPORT_PROFILE_V2_SHA256` rather than editing it. That
    constant is the anchor over the export profile and lives in Python source;
    moving it stays a maintainer attestation with a one-line diff. A refresh
    is therefore two passes with that attestation in between, which is why the
    command exits 1 rather than 0 while it is pending.
  - Export profile membership is never edited — an entry's `raw_sha256` is
    only ever updated in place — so this cannot add a file to the
    public/synthetic export or drop one from it. Adding or removing a member
    still requires a new, separately reviewed profile version.
  - It refuses to rewrite any file whose committed bytes it cannot reproduce
    exactly, so a re-pin can never also reformat the file being reviewed.

### Fixed

- **An expired attestation reported itself as six accessibility failures.**
  `data/availability/woodland-preapproved-adu-program.json` carries
  `recheck_due_on: 2026-09-08`, and the page resolves it against UTC today. At
  `2026-09-09T00:00:00Z` the record fell outside its window, the packet journey
  closed as designed, and `tests/accessibility.spec.js` reported **6 failures**
  on the same commit that had passed eleven hours earlier — every one of them
  `expect(locator).toBeVisible()` on `#journeyEntrySummary` or a sibling, none
  of them naming a date, a file or an attestation. The gate was working; its
  output sent a reader into the CSS.
  - **Measured, and it is what picked the repair:** of the six, **five assert
    nothing about the record** — the only two axe WCAG scans of the packet page
    (320px and 390px), print-media isolation, the Spanish `lang` handoff, and
    the evidence summary with its print action. So while the record is stale the
    packet page is scanned by axe **0 times out of 2** viewports. It was not
    only a mis-named failure; the accessibility gate had stopped examining.
  - Those five now run against a fixture whose attestation window is anchored to
    the run's own UTC date, so they measure accessibility. Only the two dates
    move, and only in memory: the excerpt, its `sha256`, the label and the URL
    stay the committed ones, so the page's own fingerprint check still runs.
  - The committed record's currency is asserted by one test, first in the file,
    which names the file, `checked_on`, `recheck_due_on`, today's UTC date, how
    many days past due it is, and that renewal means a person opening the City
    of Woodland page and attesting to what it says. **The date has not been
    moved** — that would publish an attestation nobody made — so `main` stays
    red until a human re-attests, now for one legible reason instead of six
    misleading ones.
  - It also refuses if `data/demo-data.js` no longer carries the record the JSON
    file holds, because a fixture derived from a stale bundle would vouch for a
    record the page does not serve.

- The committed source-state receipt reported a withdrawn address as verified.
  `davis-adu-handout-2026` answers `HTTP 404 Not Found` at its published
  address, but `data/source-status/current.json` still carried the last
  successful watch: `status: "unchanged"`, with `observed_sha256` holding the
  same digest as `recorded_sha256`, as though the document had been fetched
  and matched. A failed read was published as a successful verification, which
  is the one thing a currency receipt exists to rule out. The receipt from the
  run that actually observed the 404 is now the committed one, so the source
  reports `unverifiable` / `not_found` and appears in
  `unverifiable_source_ids`.
  - Nothing is marked stale by it. Per ADR 0005 an unverifiable source is not
    evidence that the law moved: the retained copy last confirmed 2026-07-30
    still stands, all 19 rules and 29 Golden cases stay unaffected, and the
    harness still exits 0. A withdrawn link is a publication fact, not a
    finding about the law, and it must not move an exit code.
  - The digests that depend on those bytes moved with it — the record's
    `artifact_bindings[source_state]`, the v2 export profile entry and its
    `_EXPORT_PROFILE_V2_SHA256` anchor, and the dependent
    `aggregate.artifact_set_fingerprint` and `unverifiable_source_count`.

- The harness stopped reporting a fetch it never made as a clean result. The
  machine-readable `currency signals:` line printed
  `changed_sources=0 ... unverifiable_sources=0` on every run, including the
  ordinary no-network run that `make bundle-check` and any local invocation
  perform. Those two counts are answers only a download can give, so `0` there
  was an absence rendered as a measurement — byte-identical to what a watch
  that ran and found every source current prints. Both now read `not_checked`
  unless `--fetch` was given.
  - `stale_rules` and `golden_regressions` are unchanged. They are derived
    from the committed rule and Golden records, which every run reads, so they
    are measured whether or not anything was fetched.
  - Exit codes are untouched. `unverifiable_sources` still counts only this
    run's fetch failures, so a withdrawn address recorded in the committed
    receipt still does not move the exit code.
  - The weekly workflow always runs with `--fetch` and so always saw real
    numbers, but its alert step read any non-`0` value as "this condition
    fired" and interpolated it into "N watched source(s) were fetched and
    their content hash moved". It now refuses a non-numeric signal value and
    fails the step rather than publishing a sentence built on a token. A
    report with no signal line at all still falls through to the existing
    "without a signal breakdown" wording.

- The two source watchers stopped announcing a repository that no longer
  exists. `scripts/pull_hau_letters.py` and
  `src/permit_pathways/harness/watch.py` sent
  `permit-pathways-hau-letters-watch/0.1` and
  `permit-pathways-currency-watch/0.1` as their outbound `User-Agent`, so the
  HCD and legislative servers this project polls have been logging a project
  name that only resolves through GitHub's rename redirect — and that redirect
  survives only while nobody else claims `ChelseaKR/permit-pathways`. Both now
  name `permit-bearings`. `CITATION.cff`'s `repository-code` and
  `[project.urls]` did the same to anyone citing or linking the work, and now
  point at the current URL directly.
  - This is the externally visible slice of #111 only. The distribution name,
    the `src/permit_pathways` import package and the deployed Lambda's build
    are deliberately untouched: moving those has to be sequenced with a
    rebuild and apply of `deploy/ai-service/`, which is not a repository-only
    change. #111 stays open for that.
  - A contract test asserts both user agents and both citation surfaces name
    the current repository, so the next straggler fails rather than shipping.

- Two date validators compared against the host machine's local calendar
  instead of UTC, so the same bytes passed or failed depending on where and
  when they were checked. `jurisdictions._required_recorded_date` (the
  `retrieved_on` guard on the HCD letter dataset, which is emitted straight
  into the browser bundle) and `conformance_evaluation.load_answer_key` (the
  `law_as_of` / `check_registry_as_of` future-date guard) both called
  `date.today()`. West of UTC that rejects a dataset stamped with the current
  UTC date — a `build_hcd_letters.py <today>` run during a Pacific evening
  fails `retrieved_on: cannot be in the future` locally while the identical
  file passes in CI. East of UTC it does the opposite and accepts a record
  dated a day into the future, which is precisely what the guard exists to
  stop. `assets/demo.js` has always compared these fields against `Date.UTC`,
  and `permit_pathways.dates.resolve_today` exists so the Python runtimes
  agree with it; these two callers had simply never been moved onto it.
  `build_coverage_index` now takes the same injectable `today` every other
  validator here does, and a test asserts no module under `src/` or
  `scripts/` reintroduces `date.today()`.
  - `scripts/readability_gate.py` stamped a regenerated baseline's
    `generated_on` from the local clock for the same reason; it now records
    the UTC date, so a committed baseline says the same thing wherever it was
    regenerated.

- The Bedrock provider default is a model this project's AWS account can
  actually invoke. `DEFAULT_BEDROCK_MODEL` was
  `global.anthropic.claude-sonnet-5`, and `InvokeModel` answers
  `403 anthropic.claude-sonnet-5 is not available for this account` for it
  (verified live 2026-09-02) while the entitlement API reports the model
  authorised — so availability had to be established by invoking it, not by
  asking. Anyone following the documented `PERMIT_AI_PROVIDER=bedrock`
  invocation without also setting `PERMIT_AI_MODEL` got a 403 from a service
  that was otherwise configured correctly, and Bedrock is the path every
  recorded run under `evals/ai/results/` actually used. The default is now
  `global.anthropic.claude-sonnet-4-6`.
  - `DEFAULT_ANTHROPIC_MODEL` stays `claude-sonnet-5`. The two defaults answer
    different questions — ADR 0004's settled choice for a deployer with
    ordinary API access, against what one AWS account is entitled to — so they
    differ on purpose, and the module docstring, ADR 0004, and
    `test_the_bedrock_default_is_a_model_this_account_can_invoke` all say so,
    to stop the next reader tidying the difference away.
  - That test pins both literals rather than comparing against the constants
    the way every other assertion in the file does, and additionally requires
    the Bedrock default to appear as the `run.model` of a committed live
    result, so the default can never name a model nothing has answered.

### Changed

- **The Python distribution is renamed `permit-pathways` -> `permit-bearings`,
  and so is everything outward-facing that still carried the old name.**
  `pyproject.toml`'s `name`, `uv.lock`, `package.json`/`package-lock.json`
  (`permit-bearings-quality`), the `SECURITY.md` report subject, the README's
  `--run-url` example, the "Source code" links on `index.html` and
  `evidence.html`, the historical Actions run links in
  `docs/SHOWCASE-REMEDIATION-PLAN.md`, and the temporary paths `make security`,
  `make evidence-export-check` and the Lighthouse budget script create. Neither
  name is claimed on PyPI, so this costs nothing today and stops being free the
  moment either is published.
  - **Three test-side validators were pinning the old GitHub Pages path**, which
    is the part that was not merely cosmetic. `tests/test_content_review_evidence.py`,
    `tests/test_flagship_evidence_ledgers.py` and `tests/test_manual_evidence.py`
    required a frozen `deployed_url` to start `https://chelseakr.github.io/permit-pathways/`.
    Every committed record has `deployed_url: null` today, so nothing was
    wrong yet — but the first real freeze, at the address the site actually
    serves from, would have been rejected by its own validator.
  - A new contract test enumerates the four places the old name survives on
    purpose — `CHANGELOG.md`, the 2026-08-15 scan finding's recorded
    `User-Agent`, and the two sentences explaining why the standards pin is a
    commit rather than a tag — and fails on any tracked file that reintroduces
    it elsewhere. Entries in this changelog keep the old name because several
    of them are about the rename.
  - **The import package is still `permit_pathways`, and that is now recorded
    rather than pending.** Three not-run planning ledgers name module paths
    inside it — `data/validation/beta-operations-readiness.json` lists
    `src/permit_pathways/beta_operations.py` as an evidence path,
    `data/conformance/evaluations/heldout-v1/manifest.json` pins the scanner
    and evaluator paths, and `data/validation/woodland-source-change-rehearsal.json`
    names `permit_pathways.readiness_cli`. Their raw bytes are pinned in
    `beta_gate._NOT_RUN_ARTIFACT_SHA256`, and `beta_gate_cli recompute`
    refuses to re-derive them outright, because that refusal is what stops a
    favourable nested result being rewritten together with its digest.
    Renaming the package therefore means editing three immutable ledgers and
    three pinned digests by hand. That is an attestation, not a refactor, and
    it is left to the maintainer.

- **The committed HCD Housing Accountability Unit letter dataset is re-read
  as of 2026-09-07.** The dashboard moved from 1,314 rows to 1,356: 231 rows
  added and 189 removed, across 19 jurisdictions whose rows are new and 141
  whose rows changed in place. A row total is not a letter count — HCD edits
  published rows — so the numbers are reported as rows, not as new letters
  (issue #63). The derived dataset now holds 1,356 records: 1,353 keyed to
  473 of the 541 registry entries, three statewide, zero unmatched. The
  jurisdictions with HCD letter history go from 470 to 473, and every prose
  count that quoted the old snapshot — `PROVENANCE.md`, `docs/EXPANSION-PLAN.md`,
  `docs/PRODUCT-CONTEXT.md`, the README's Scenario 3 row, and the
  `permit_pathways.precedent` docstring — moves with it. The 2026-08-15
  ordinance-scan finding keeps its own numbers: it is a dated record of what
  the scan was run against, not a live claim.
  - The regenerated demo bundle, coverage index and v2 export profile carry
    the new digests, and the export profile's tamper-evidence anchor
    (`_EXPORT_PROFILE_V2_SHA256`) is re-pinned by hand after reading the
    profile diff, which is exactly the five files this change touches that the
    profile covers.

- The README names the live demo above the fold. The URL first appeared at
  line 84, below the quickstart, the preapproved-plan availability boundary,
  the registry and bundle-integrity description, and the print-summary
  paragraph: eighty-three lines of accurate, deliberate prose about what this
  prototype does not claim, standing between a visitor and the working thing
  that prose describes. The link moves to line 12, directly after the
  description and before the runtime AI note. Nothing was cut — every
  boundary and limitation paragraph is byte-identical, and the demo URL still
  appears exactly once in the file.

- The intake prompt no longer teaches the model that "a second unit" means an
  ADU, and the runtime intake prompt is now `intake-v2`. Gauntlet reported
  `/intake/extract` returning `project_type=adu (extracted)` in both English
  and Spanish for an applicant who wrote "I want to add a second unit on my
  property in Davis. Not sure what the options are." (issue #90). The quote
  gate could not catch it: "add a second unit on my property" is a verbatim
  substring, so the value looked supported. The prompt was the source — the
  vocabulary block glossed `adu` as "backyard cottage, garage conversion,
  attached or detached second unit", listing the exact phrase an undecided
  applicant reaches for as a definition of one specific answer, while rule 3
  forbids inferring an unstated fact. "A second unit" is equally an ADU, a
  JADU, and an SB 9 two-unit project.
  - The `adu` gloss drops "second unit"; a new rule names the ambiguous
    phrases in both languages and says a quote can be verbatim and still not
    decide the question; a further rule says an applicant stating they do not
    know is the answer, scoped to the fact they were unsure about — someone
    undecided between converting the garage and building in the yard has
    still said the type, and only the form is unknown.
  - Measured on Bedrock `global.anthropic.claude-sonnet-4-6`, that input, ten
    trials per language: `intake-v1` filled a project type 7/20 (en 0/10,
    es 7/10); `intake-v2` 0/20 (en 0/10, es 0/10).
  - Two committed 40-case runs of `intake-v2` are recorded in
    `evals/ai/results/`. Project-type and jurisdiction accuracy stay 1.000 and
    `known_field_wrong` stays 0.000. The cost is a small, repeatable rise in
    abstention on facts the text does state: `known_field_missed` 0.024 at
    `intake-v1` against 0.047 and 0.035 at `intake-v2`, both extra misses
    being `sf_zone` on SB 9 lot-split cases. `filled_when_unknown`, the defect
    rate this design exists to hold down, is 0.035 against 0.035 and 0.043.
    Two runs of forty cases cannot separate that last figure from run-to-run
    variance and it is not claimed as an improvement.
- Every public page now carries a self-referencing `<link rel="canonical">`
  and a complete social card. `index.html` already had both; `check.html`,
  `prepare.html`, `review.html` and `evidence.html` had `og:title`,
  `og:description` and `og:type` and nothing to say which URL they described or
  which image to show, so a shared link to any of the four previewed as a bare
  URL with no card and no page identity. They now also carry `og:url`,
  `og:site_name`, `og:image` (with type, dimensions and alt text),
  `twitter:card`, `twitter:title`, `twitter:description`, `twitter:image` and
  `twitter:image:alt`, all absolute and all pointing at the page they sit on.
  No new applicant-facing copy was written: every string is the page's existing
  title or `og:description`, or the shared card and its alt text from
  `index.html`. `test_every_static_page_names_itself_and_not_the_shared_origin`
  extends the existing five-page static-markup checks rather than starting a
  parallel suite, and it holds the property that matters on this deployment:
  the site is served from `chelseakr.github.io`, an origin shared with five
  other unrelated projects, on a path rather than a domain, so a canonical of
  "/" is not this site's root but a different address that 404s and that all
  six sites would claim. Observed failing four ways, each naming the page:
  canonical deleted from `check.html`; `prepare.html` canonicalised to the bare
  origin; `twitter:card` deleted from `review.html`; `evidence.html`'s `og:url`
  pointed at `check.html`.

- The committed `protect-main` ruleset now records the repository owner's
  standing bypass, which the live ruleset has had all along.
  `.github/rulesets/main.json` declared `"bypass_actors": []` while live
  ruleset `20017370` carried `{"actor_id": 5, "actor_type": "RepositoryRole",
  "bypass_mode": "always"}` and reported `"current_user_can_bypass": "always"`.
  The committed file is the one somebody re-applies, which is what made the
  mismatch a hazard rather than a stale line: an agent once applied a ruleset
  with no bypass and locked the owner out of their own repository, and
  restoring access took a sweep across eighteen repositories. Re-applying this
  file as it stood would have reproduced that, and the empty list would have
  looked like the careful choice while doing it. The file changed to match
  reality; no live ruleset or repository setting was touched.
  - A new `.github/rulesets/README.md` records why the bypass exists, what it
    is not (a relaxed merge policy — every change still goes through a pull
    request with the eight required contexts green), and how to check
    `current_user_can_bypass` after re-applying the file.
  - `tests/test_repository_ruleset.py` holds the committed file and the live
    ruleset against that one actor independently rather than comparing the two
    to each other. Comparing them would report conformance on the day both
    were emptied together, which is the incident recurring with a green tick
    on it; that case is a test, and it must produce two findings rather than
    zero. A second bypass actor on either side is a finding too.

- The verification gate's scope now matches the claim it backs. `make verify`
  was presented as local-equivalent verification while every one of its
  checks was scoped to `src/`, leaving roughly 6,300 lines across
  `assets/demo.js`, `demo/app.py`, and `scripts/` outside lint, strict
  typing, Bandit, and any coverage floor, including the two files that carry
  duplicated rule logic (issue #73).
  - Ruff, strict mypy, and Bandit now cover `src`, `tests`, `scripts`, and
    `demo`. `demo/app.py` is fully annotated and passes strict mypy; the two
    `S310`/`B310` network findings in `scripts/pull_hau_letters.py` are
    waived inline, next to the call they excuse, with the invariant that
    makes them safe written out, rather than by a file-level entry.
  - `src/permit_pathways/py.typed` is added. The package was strictly typed
    and did not say so, so every script importing it was being checked
    against `Any`.
  - `tests/browser/` is a new Node unit suite that evaluates the shipped
    `assets/demo.js` in a `node:vm` context with a small DOM, rather than a
    copy of it. 65 tests cover the duplicated domains: all 29 golden cases
    replayed through the browser's own `screen()`, the criterion semantics,
    the 180-day staleness boundary, the ADR 0005 withdrawn-citation
    derivation, and the review clocks, whose 60-calendar-day answers are
    asserted against the dates `permit_pathways.clocks` produces. This is
    the cross-runtime screening contract `docs/PRODUCT-CONTEXT.md` records
    as known correctness risk 7.
  - `scripts/browser-coverage.mjs` reports real V8 coverage of
    `assets/demo.js` and enforces a floor, with no new dependency. It
    measures 20% of lines and 17% of functions. That floor is a ratchet on a
    file that had no coverage gate at all; it is not the Python package's
    85%, and the README now prints both numbers separately rather than one
    number that reads as covering the repository.
  - `make verify` requires Node and says why. Eight cross-runtime contract
    tests were guarded by `skipif(shutil.which("node") is None)`, so a local
    run could pass with the browser runtime entirely untested while CI
    called the same command "local-equivalent verification".
  - `zizmor` runs at `min-severity: low` instead of `high`, verified clean at
    low severity and low confidence first, so the change tightens the gate
    without leaving a backlog.
  - Not done, and why: the `Standards` pin still names a commit rather than a
    released tag. `portfolio-standards` v2.0.0 keys this repository as
    `permit-pathways`, its checker resolves the entry by checkout basename,
    and after the GitHub rename that entry no longer matches, so pinning to
    the tag would fall to the `restricted` publication default and fail a
    required check on an unchanged repository. The fix is `portfolio-standards`
    PR #97 merging and a tag being cut, which is a decision in another
    repository. No `.standards-version` file was added, because it could only
    name an unmerged branch commit and DOC-01 asks for a released tag.
    Recorded in the README's CI/CD row alongside the fact that a fork pull
    request can never pass this required check, because GitHub does not pass
    the deploy key to fork runs (issue #74).
### Fixed

- The weekly currency watch converges instead of accumulating. It filed a
  brand-new issue every Monday with the run date in the title and no
  deduplication of any kind, so a condition that stays unresolved became an
  unbounded pile; #63 and #65 are two weeks of the same one. Titles are now
  stable and dateless, both alerts search before they create and comment on
  the open issue instead, both carry a `currency` label, and each repeat
  comment says how many days the condition has been open. A green run closes
  the alert it opened, with a comment naming the run that cleared it, so the
  automation is a status signal rather than an append-only log. An
  unverifiable run neither opens nor closes anything: a source that could not
  be downloaded is evidence about the network, and nothing was learned about
  the law in that run. `python -m permit_pathways.harness` now prints one
  machine-readable `currency signals: changed_sources=N stale_rules=N
  golden_regressions=N unverifiable_sources=N` line on every run, including a
  clean one, so the issue names which of the three conditions behind exit 1
  fired rather than reporting that one of them did; a signal printed only on
  failure could not be used to detect recovery either. The workflow's own
  shell is executed against a fake `gh` in `tests/test_currency_workflow.py`,
  because string assertions prove a workflow says the right words and cannot
  prove it runs. Reported as issue #70.

- `scripts/scan_ordinances.py` no longer re-dates every published scan result
  on every run. It took one global `scanned_on` and stamped it on all eight
  files, including jurisdictions whose ordinance text had not been
  re-retrieved, so `scanned_on` recorded when the writer last ran rather than
  when that ordinance was scanned. Each result is now re-derived with its own
  recorded date first, and only the ones that come back different, or that
  have no published result yet, take the new date; `--redate-all` covers a
  deliberate re-retrieval of the whole corpus. Running the writer with a new
  date against the unchanged corpus now leaves all eight files byte-identical,
  which also stops it disturbing the two results pinned in the frozen
  schema-v1 export profile. Recorded as weakness 3 in
  `docs/findings/2026-08-15-multi-jurisdiction-adu-ordinance-scan.md`, where
  it is noted as untidy at seven jurisdictions and misleading at two hundred.

### Added

- `python -m permit_pathways.precedent`: read-only comparable-jurisdiction
  discovery over the HCD accountability letter snapshot already committed at
  `data/jurisdictions/hcd-letters.json`. Nothing is fetched. Three
  subcommands: `kinds` lists letter kinds with how many jurisdictions
  received each, `list --kind ... [--authority ...]` prints every letter of
  one kind, and `for <slug>` shows one jurisdiction's letters and then the
  other jurisdictions HCD wrote to about the same kind under the same
  authority. Grouping by (kind, authority) is what makes it precedent rather
  than a directory: two jurisdictions that both received an ADU-Law repeal
  request are comparable in a way that two entries on the same list are not.
  Of the 1,312 letters across 470 of the 541 registry entries, 205
  jurisdictions have received a repeal-request technical assistance letter,
  which `docs/findings/2026-08-15-multi-jurisdiction-adu-ordinance-scan.md`
  had already noted was a priority list sitting in committed data.
  Every rendering carries the boundary, and a test asserts it: HCD
  correspondence is documented precedent, not controlling authority for
  another jurisdiction and not a compliance finding, and a jurisdiction with
  no row is one this dated snapshot linked no letter to, which is not
  evidence of compliance or of no HCD activity. A capped listing always
  reports the full group size. It reads correspondence metadata rather than
  ordinance text, no watcher monitors an individual letter for later action,
  and it ships as a CLI rather than a page, because
  `docs/PRODUCT-CONTEXT.md` says not to add demo modules until the applicant
  journey reads as one coherent flow and whether it does is not this
  change's call to make. Addresses `AGENTS.md` priority 4,
  comparable-jurisdiction discovery.
### Fixed

- The transit screen read the Caltrans dataset's stop type and threw away the
  column that says whether the stop exists. `hqta_details` was parsed into
  `HQStop.details` and never read by anything in `src/`, `tests/`, `scripts/`,
  or `assets/`, and it is the only field separating a stop derived from
  published service from one a metropolitan planning organization submitted as
  planned in its adopted regional transportation plan. 3,120 of the 13,446
  distinct `major_stop_*` rows the loader returns from the committed snapshot
  are planned. On the exact command the README documents, the screen named a
  planned Yolo TD stop 0.12 mi away as the reason the § 66321(b)(4)(B) height
  allowance applied, in the present tense, while the operating Capitol
  Corridor and Amtrak rail platforms sat at 0.36 mi. `HQStop.is_planned` and
  `HQStop.is_existing_major` now expose the distinction; a planned row inside
  the half mile produces no candidate for either standard and establishes
  neither a § 21064.3 major transit stop nor public transit near the site; and
  every planned row inside the radius is reported by count, agency, type, and
  distance, with what Caltrans publishes about these rows, both statutory
  definitions, and a question for the transit agency. Reason strings now name
  `hqta_type` and `hqta_details` together. `load_hq_stops` requires
  `hqta_details` to be text and raises otherwise rather than defaulting to a
  value that reads as an operating facility, and the de-duplication key
  includes it, which recovers 898 rows that were collapsing into whichever row
  came first. The verdict on the documented example is unchanged; the stop it
  cites as the reason is now one that exists. Grounded in Cal-ITP's published
  methodology for the dataset, read 2026-08-27. Reported as issue #44 and
  recorded as
  `docs/adr/0006-planned-transit-stops-are-not-existing-ones.md`.

### Added

- `docs/EXPANSION-PLAN.md`: a two-to-three-year expansion plan ranked against
  `AGENTS.md`'s priority order and `docs/PRODUCT-CONTEXT.md`'s known
  correctness risks, separating the work that can be finished from inside the
  repository from the work that needs a named reviewer, a jurisdiction
  sponsor, or a partner decision. It changes no capability status.

- A watched source that could not be fetched is now recorded by kind, and a
  citation whose published address is gone stops being offered as a link.
  `permit_pathways.harness.watch` classifies an HTTP 404 or 410 as
  `not_found` (the server answered about that exact address) and every other
  failure as `transport` (no authoritative answer arrived); a `not_found`
  answer is not retried, because asking again cannot change it. The
  source-state receipt requires `unverifiable_kind` on exactly an
  unverifiable observation and rejects it anywhere else, so
  `data/source-status/current.json` is byte-identical and keeps its
  fingerprint. `source_state.withdrawn_citations` names each rule whose own
  `citation.url` resolves to a `not_found` source; `python -m
  permit_pathways.harness` reports that from the adopted receipt on every
  run. `assets/demo.js` and `demo/app.py` both render such a citation as
  text rather than an anchor, with a bilingual note saying the official link
  did not open, that the quoted text is from the retained copy, and that
  staff should be asked for the current document, and a test asserts the two
  runtimes agree. The evidence page labels "published link not found"
  separately from "could not re-fetch". Nothing here stales a rule, changes
  a match, suppresses an excerpt or action copy, or moves an exit code.
  Motivated by a live run on 2026-08-27 in which twelve leginfo sources
  failed on a local certificate store and `davis-adu-handout-2026` returned
  HTTP 404, both reported identically (issues #91 and #96). The Davis
  citation URL itself is unchanged: the City site answers 403 to a
  non-browser client, so no replacement address could be retrieved and
  guessing one is not available to this repository. Recorded as
  `docs/adr/0005-separate-a-withdrawn-citation-from-an-unreachable-source.md`.

### Changed

- The optional AI service is now hosted and reachable from the public page.
  `deploy/ai-service/` was applied on 2026-08-21: one arm64 Lambda behind a
  Function URL in `us-west-2`, DynamoDB daily cap of 100 model-backed
  requests, reserved concurrency 2, Bedrock `global.anthropic.claude-sonnet-4-6`.
  `check.html` lists the hosted origin as the second service candidate after
  localhost and allows it in `connect-src`; `demo/app.py` allows the same
  origin. Three deployment corrections were needed and are now in the
  Terraform: the build keeps `*.dist-info` metadata (the SDK reads package
  metadata at import), a public Function URL needs both `InvokeFunctionUrl`
  and `InvokeFunction` scoped by `lambda:InvokedViaFunctionUrl`, and CORS is
  answered by the application only because an edge CORS block duplicated the
  `Access-Control-Allow-Origin` header, which browsers reject. This remains a
  prototype showcase deployment, not the reviewed beta of ADR 0002.
- Public links follow the repository rename: GitHub Pages now serves the
  site at `https://chelseakr.github.io/permit-bearings/` and the old
  `/permit-pathways/` path returns 404, so the README live-demo links, the
  landing page's canonical/`og:url`/social-image URLs, the deployment-smoke
  default, the remediation plan, and the social-card text now name the new
  path. The no-service browser check aborts every off-origin request and
  expects one probe per listed candidate, so it stays hermetic with a hosted
  origin in the list.

### Added

- A second wave of runtime AI under ADR 0004. `POST /ask` answers one
  follow-up question (up to 500 characters) only from the matched rules'
  cited corpus passages, with the same verbatim-citation verifier; when the
  passages do not settle it the model abstains, and a one-sentence question
  for staff is returned whenever any part is unsettled. The project-check
  page gains the "Ask a question about this result" box after an
  explanation, offers the AI staff-question draft on its own when the result
  is "needs staff review", links each citation into the official source with
  a text fragment for the quoted words where the source is HTML, and probes
  a comma-separated list of service origins in order (local development
  first, hosted second). Every model-backed route is now metered by
  `permit_pathways.ai.budget`: a per-client sliding window and a hard daily
  cap (`PERMIT_AI_DAILY_CAP`, default 300 locally), in memory or as a
  DynamoDB conditional update when `PERMIT_AI_BUDGET_TABLE` is set; a 429
  `budget_exhausted` leaves the deterministic result untouched. The provider
  marks the system prompt cacheable and reports cache usage. `deploy/ai-service/`
  holds a prepared AWS Lambda deployment (Terraform: arm64 function, Function
  URL with CORS limited to the static site, reserved concurrency 2, DynamoDB
  daily-cap table, least-privilege Bedrock access to one model, 14-day logs
  without bodies, default cap 100/day) plus `build.sh` and a README stating
  what the shape does and does not provide; it has been planned but not
  applied. `docs/DATA-FLOW.md` records the subprocessor facts that shape
  would create. No evaluation set covers `/ask` yet.

- `python -m permit_pathways.ai.rule_drafts`: the stretch item in ADR 0004,
  as a CLI only. It asks the model for candidate rule entries in the
  `data/rules` schema from one ordinance text and keeps a proposal only if
  its `citation.excerpt` occurs verbatim in that text, its criteria use only
  the intake vocabulary, and it loads through the real `screening.load_rules`
  validator; rejections keep their reason. Output is a wrapper object marked
  `unreviewed_ai_draft` in Git-ignored `ai-drafts/`, refused under
  `data/rules`, with `verified_on` always null. A live trial on the
  committed Capitola chapter accepted 3 proposals and rejected 3 whose
  excerpts were not exact text. Nothing here is reviewed, registered, or
  loadable by the matcher.

### Added

- The project-check page can now use the optional AI service (ADR 0004)
  without changing its static path. `assets/ai.js`, loaded after `demo.js`,
  renders a closed "Describe your project in your own words" disclosure above
  the form that does nothing until the applicant presses "Use AI assistance";
  only then does the page probe the service named in the `permit-ai-service`
  meta tag. If the service answers, a free-text field appears and "Draft my
  answers" writes an AI draft of the same structured answers into the
  ordinary form, each shown with the quote from the description it came
  from, with unanswered questions left as "I'm not sure" under "I couldn't
  tell from what you wrote" and details no question uses listed separately;
  the applicant reviews and submits as before. After a result, "Explain this
  result in plain language (AI-generated)" shows a labeled explanation whose
  every statement cites verified source text, the count of withheld
  statements, and AI-drafted staff questions. If the service is absent, the
  control reports that and the page is the static experience it always was;
  a browser check proves the page makes no request beyond its origin until
  asked and exactly one failed probe afterwards. English and Spanish strings
  live in the existing catalog. `check.html` and the reference server allow
  `connect-src` to `127.0.0.1:8787` / `localhost:8787` only; a hosted
  service changes both. The capability matrix now lists natural-language
  intake, grounded explanation, and tailored staff questions as `Prototype`
  with the measured numbers and their limits, `docs/DESIGN.md` section 3
  describes the implemented layer, and `docs/DATA-FLOW.md`,
  `docs/ACCESSIBILITY.md`, and `docs/I18N.md` record its boundaries.

### Added

- An evaluation harness for the runtime AI layer, `python -m
  permit_pathways.ai.eval` (`make ai-eval`), with two committed case sets
  under `evals/ai/`: 40 synthetic bilingual natural-language intake cases
  (25 English, 15 Spanish; ADU, JADU, SB 9 two-unit and lot split; including
  deliberately underspecified and inference-tempting descriptions) with gold
  extractions, scored per field on exact match and separately on abstention
  versus gap-filling; and 8 confirmed-fact cases scored on how many
  generated claims carry citations that verify verbatim against the corpus.
  A result file records provider, model, prompt versions, UTC date, and Git
  commit, and a test refuses a result without that provenance. Two recorded
  live runs on Amazon Bedrock `global.anthropic.claude-sonnet-4-6` (the
  model this AWS account can invoke; Sonnet 5 is not enabled on it) are
  committed: intake 40/40 project types and jurisdictions, 97.0% per-field
  exact match, 96.6% abstention where the text did not say, 3.4% gap-filling
  (4 of 116), 0% wrong values, 85% of cases fully correct; grounding 59 of
  59 claims shown with verified citations and 0 withheld, 50 staff questions
  with 98% carrying a resolvable pointer. Building the harness surfaced two
  fixes that ship with it: jurisdiction names are matched without diacritics
  (`Los Ángeles`, `San José`), and grounding passages are now interleaved
  across matched rules so a long match list cannot starve the last rules of
  source text (two earlier runs the same day withheld 2 and 3 of about 60
  claims for exactly that reason, each a citation the verifier correctly
  rejected). Withheld-claim reasons now include the offending quote.

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
