# Changelog

All notable changes to this project are recorded here. The project has not
published a versioned release.

## [Unreleased]

### Fixed

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
