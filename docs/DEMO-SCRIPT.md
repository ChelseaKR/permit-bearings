# Showcase demo script (40 min: 30 presentation + 10 Q&A)

Audience: state program staff (ODI/GovOps/CHHA/GO-Biz) + jurisdiction
observers. Goal: be the vendor they remember for *trust*, not features.

Preflight: use the hosted demo, open `index.html` directly, or serve the
repository with `python3 -m http.server 8765`. After changing canonical JSON,
run `python3 scripts/build_demo_bundle.py` and the static-demo regression test.
Start at `/` for the product boundary, then use `/review.html`,
`/check.html`, `/prepare.html`, and `/evidence.html` for the four live jobs.

## Arc: “Every tool will show you an answer. I’ll show you the evidence and when it needs review.”

### 0. The opener: scan an ordinance live (3 min)
- From the landing page, choose **Review local rules**. The separation is
  intentional: this is a staff review aid, not an applicant chatbot.
- Paste an ADU ordinance provision into the conformance scanner. Watch it
  flag the stale SB 477 citation, the 16-ft height cap, the subjective
  "similar styled roof design," each with the controlling state law and
  the HCD enforcement letter where that exact failure mode appeared.
- The kicker: these are the *actual provisions* HCD quoted in its June 2025
  findings letter to Santa Clara County. For that named six-provision
  regression fixture, the scanner reproduces HCD's six expected review flags.
  It is a review queue, not a compliance verdict or statewide accuracy claim.
- Positioning sentence: "Permit platforms can help applicants navigate and
  file. This component makes the rule, handout, or AI corpus auditable as its
  sources change and can sit inside somebody else's stack."

### 1. The problem nobody demos (2 min)
- Housing law changes every session. SB 477 (2024) renumbered all of state
  ADU law (§ 65852.2 → §§ 66310–66342); 2025 legislation renumbered sections
  again. Every handout, chatbot, and ordinance citing the old sections became
  wrong without anyone touching it.
- Live evidence: HCD's Santa Clara findings letter documents the obsolete
  numbering in an operative ordinance. The current Davis code text is
  discoverable, but direct currency retrieval remains blocked and the City
  warns its 2021 regulations may differ from later State law. The prototype
  therefore keeps that local record unverified and does not treat the
  discrepancy as proof of a local defect.
- Frame: correctness *decays*. An AI guidance tool without a currency
  mechanism is a liability with a friendly interface.

### 2. Applicant flow: Scenario A (6 min)
- Open the labeled hypothetical ADU sample at
  `check.html?sample=adu`. Point out that it loads an existing Woodland golden
  fixture, fills the native form controls, and submits through the same
  validation and matching path as manual answers. It is not a real parcel,
  applicant record, pilot, or external validation result.
- Start with the "Sample answers used for this result" cover sheet. It shows
  exactly which made-up jurisdiction and project answers produced this view.
  State that the cover sheet exists only in the current page. It is not a
  stored applicant record, verified parcel record, completeness finding, or
  exportable evidence manifest.
- Read the generated result sentence and use the jump links. Show candidate
  routes first, relevant standards second, and the bounded Woodland local
  information record last. State that Woodland is not a comprehensive local
  code or checklist.
- The explicitly configured ADU candidate route starts open. Point to its
  citation and source-status label, which remain visible even when the
  disclosure is closed. Walk through the separate 15-business-day and
  conditional 60-day deadlines, starting steps, staff questions, and evidence.
  Then show how supporting standards and the local information record remain
  compact until opened.
- Follow "Edit these answers," change one ordinary project answer, and show
  that the old cover sheet and result disappear. Submit again before discussing
  the new result. This prevents changed facts from sitting beside a result they
  did not produce.
- Name the integrity boundary: deterministic rules selected the record; the
  plain-language explanation is a versioned AI-assisted draft and cannot
  change the match. A source date does not mean a person, counsel, or
  jurisdiction reviewed the explanation. The unverified Davis card keeps the
  visible source and no-dated-source warning but withholds drafted actions,
  interpretive notes, and generic document hints rather than turning weak
  evidence into a confident answer.
- Switch the intake/results to Spanish. Be explicit that Spanish
  plain-language copy is an unreviewed machine draft with no semantic-parity
  review. Applicant-facing result titles are localized drafts; canonical
  pathway labels, source excerpts, citations, and document hints remain
  English.
- Show the separate clock prototype and name its single-date assumption.
- The trust moment: select an SB 9 fact combination with no matching encoded
  rule → the system abstains and routes to staff. "No match means insufficient
  encoded evidence, not ineligibility."
- Show the unpermitted-unit legalization path (§ 66311.7) as an example of a
  homeowner workflow often omitted by developer-oriented intake.

### 2b. Bounded packet-presence sample (5 min)

- Follow the link from the hypothetical route to `prepare.html`. State first
  that this is a generated, made-up record, not a real applicant packet,
  completeness assessment, pilot, or external validation result.
- Show that the Python evaluator compared explicit synthetic facts and
  inventory statuses with 25 requirements from one dated City of Woodland
  preapproved ADU checklist. The public browser validates and renders the
  generated result; it does not run a second evaluator.
- Read the result: three known gaps, five items needing confirmation, 14
  reported present, and three not applicable from the made-up facts. Open one
  missing item, one staff question, and one reported-present item. Emphasize
  that reported presence is not file inspection or a finding that contents
  are correct.
- Open the generated evidence manifest. Point to the source binding,
  requirement and packet fingerprints, per-item source locators, inventory,
  source-status date and review deadline, findings, staff questions, and
  explicit boundary.
- Show the action-copy status. AI proposed the checklist mapping and
  plain-language actions before runtime. The mapping and actions are
  fingerprint-bound, versioned, and `prototype_review_pending`; no named
  applicant, planner, counsel, Woodland reviewer, or other jurisdiction
  representative has approved them. The mapping records exact input-source
  fingerprints, but provider, model, and a reproducible run record were not
  retained.
- Name the runtime and privacy boundary: no model runs in the Python evaluator,
  CLI, build, or public browser; the bundled sample stores no applicant data.
  The evaluator does not open files, retrieve parcel records, determine legal
  sufficiency, certify completeness, limit staff requests, or predict
  approval.
- If demonstrating the CLI, run
  `PYTHONPATH=src python3 -m permit_pathways.readiness_cli --as-of 2026-07-29`.
  Its JSON is the same evidence-manifest shape committed for the sample.

### 3. The verification harness: Scenario C (5 min)
- Open **Evidence & updates**. Show the percentage of rule records with dated
  source evidence inside the review window, plus the Davis record with no
  dated source check because its host blocks the automated currency fetch and
  its local/state interaction still needs review.
- Watched sources table: content hashes of the March 2026 ADU Handbook and
  April 2026 SB 9 fact sheet; weekly automated re-fetch (show the GitHub
  Action) reports when either changes or becomes unreachable.
- One click: rehearse an amendment to § 66321. Five dependent rules flip
  stale; matching result cards rerender and withhold their drafted actions,
  while unrelated records remain unchanged. Follow the link into the
  applicant guide to show the stale state. Label this as a simulation.
  Stable dependency IDs are implemented; persisted changed state and a staffed
  review queue are not. "This is what the morning after the legislative
  session should look like."
- 29 structured golden scenarios replay in the browser. They prove matcher
  regression behavior, not natural-language accuracy or jurisdiction
  acceptance.

### 3b. Data-driven determinations, not self-attestation (2 min)
- The parking exemption and 18-ft height allowance both turn on transit
  proximity. Run the GTFS module live against the Unitrans feed for a
  downtown Davis point. The local summer bus feed contains no stop meeting the
  encoded peak screen, but the statewide dataset supplies the Davis Amtrak
  major-stop candidate.
- The reveal is the disagreement, not a citywide legal conclusion: feed date,
  planned/current facility status, operator completeness, walking distance,
  and service-calendar logic all need confirmation. "Even the map and
  schedule are versioned evidence."

### 4. Fit and posture (4 min)
- Rules, sources, and the golden set are portable files that can be copied and
  inspected without vendor-only tooling. Operational export, ownership terms,
  production retention, CPRA export, privacy review, and security controls
  remain deployment work. The demo persists no applicant data. Decision
  support, not a legal agent, is stated on every page.
- Built for low-capacity jurisdictions: static-friendly, runs beside existing
  permitting systems, no rip-and-replace.
- Teaming: this verification layer composes with full-pipeline platforms and is
  happy to be the trust layer inside someone else's stack.

### 5. What I want from you (3 min)
- Market-research honesty: the bounded packet-presence manifest is executable,
  but its checklist mapping, action copy, and usefulness have not been
  validated. The source review queue is also still a rehearsal.
- Ask: which one jurisdiction and ADU subtype should be the deep pilot, which
  public/redacted packet examples can staff review, and who approves rule and
  translation changes?

## Q&A prep (10 min)
- "What about Scenario B?" → The same harness architecture extends to staff
  reports and consistency review; v1 does one thing well per the challenge's
  own scope note.
- "LLM involvement?" → Deterministic rules where the standard is objective;
  the current runtime has no live LLM. AI-assisted mapping and remedy drafts
  are implemented for the one Woodland sample but remain review-pending.
  Page-evidenced document extraction and human-approved remedies are next.
- "Solo vendor risk?" → Working public code, dated history, CI, and a design
  based on portable, exportable artifacts. That reduces lock-in but does not
  remove key-person risk. Open to teaming.
- "Accuracy of the rule base?" → Each rule with dated evidence links a source
  and supporting excerpt; the Davis local record remains explicitly
  unverified because no stable fetchable artifact has been retained and its
  local/state interaction still needs review. The current
  `verified_on` field records dated source evidence, not jurisdiction or
  counsel approval. Encoding was machine-assisted; a named human review level
  and held-out evaluation are next. The separate Woodland checklist mapping
  has automated source, schema, and fingerprint checks, but no applicant,
  planner, counsel, or jurisdiction validation.
