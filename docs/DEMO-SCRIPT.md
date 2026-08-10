# Showcase demo script (40 min: 30 presentation + 10 Q&A)

Audience: state program staff (ODI/GovOps/CHHA/GO-Biz) + jurisdiction
observers. Goal: be the vendor they remember for *trust*, not features.

Preflight: use the hosted demo, open `index.html` directly, or serve the
repository with `python3 -m http.server 8765`. After changing canonical JSON,
run `python3 scripts/build_demo_bundle.py` and the static-demo regression test.
Start at `/` for the product boundary, then use `/review.html`,
`/check.html`, `/prepare.html`, and `/evidence.html` for the four live jobs.
The project-specific landing and project-check illustrations are decorative visual
orientation only; do not describe them as workflow, source, or approval
evidence.

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
- A separate held-out evaluation manifest now fixes the future scoring and
  evidence boundary, but its status is `not_run` and its cases, answer key,
  blind predictions, result, evaluator hash, and execution receipts are null.
  Do not present it as accuracy, precision, recall, or statewide evidence.
- Positioning sentence: "Permit platforms can help applicants navigate and
  file. This component makes the rule, handout, or AI corpus auditable as its
  sources change and can sit inside somebody else's stack."

### 1. The problem nobody demos (2 min)
- Housing law changes every session. SB 477 (2024) renumbered all of state
  ADU law (§ 65852.2 → §§ 66310–66342); 2025 legislation renumbered sections
  again. Every handout, chatbot, and ordinance citing the old sections became
  wrong without anyone touching it.
- Live evidence: HCD's Santa Clara findings letter documents the obsolete
  numbering in an operative ordinance. For Davis, the prototype binds a
  January 2026 City handout to HCD's October 2025 warning that the latest
  ordinance on file may be outdated or null. It reports only the City's three
  published processing categories; it does not treat the handout as operative
  law, resolve the source conflict, or decide which category applies.
- Frame: correctness *decays*. An AI guidance tool without a currency
  mechanism is a liability with a friendly interface.

### 2. Applicant flow: Scenario A (6 min)
- Open the labeled hypothetical ADU sample at
  `check.html?sample=adu`. Point out that it loads an existing Woodland golden
  fixture, fills the native form controls, and submits through the same
  validation and matching path as manual answers. It is not a real parcel,
  applicant record, pilot, or external validation result.
- Start with the candidate route, then open the "Sample answers used for this
  result" disclosure. It shows exactly which made-up jurisdiction and project
  answers produced this view.
  State that the cover sheet exists only in the current page. It is not a
  stored applicant record, verified parcel record, completeness finding, or
  exportable evidence manifest.
- Before submitting a new result, open the **Statewide Coverage Navigator**
  disclosure that appears for a recognized jurisdiction. It always starts with the same
  17 bounded statewide candidate-rule records—not a local-code conclusion.
  Type Albany to show `Not encoded` and no linked HCD record; say that neither
  means Albany lacks local requirements, has no HCD activity, or is compliant.
  Type Alameda to open its dated public HCD-record disclosure; it is a source
  reference, not a current ordinance or compliance determination. Type Davis
  to show its one limited jurisdiction-scoped source record and repeat that it
  is not a complete local code or checklist. The profile is bundled data, not
  a live search, parcel lookup, or applicant record. Its onboarding note names
  the material a maintainer should assemble before adding a local layer.
- Change the jurisdiction to Los Angeles County and submit the same made-up
  facts. Show the statewide orientation receipt: selected facts, candidate-
  route source status, an explicit "local requirements not encoded" boundary,
  and questions for the local counter. Print or save the receipt, then state
  that the browser owns that operation and the app stores nothing. This is the
  useful statewide handoff; it does not make Woodland's deeper checklist
  workflow statewide.
- Read the generated result sentence and use the jump links. Show candidate
  routes first, relevant standards second, and the bounded Woodland local
  information record last. State that Woodland is not a comprehensive local
  code or checklist.
- Read the three-line **Decision boundary** before opening a result. It says
  what the candidate result shows, what property/local/checklist facts remain
  unconfirmed, and which questions go to jurisdiction staff. Show that the
  candidate heading says it is for discussion—not approval—while the separate
  route-record line preserves the exact matched route. Mention that unresolved,
  no-route, and source-review states replace this copy rather than implying a
  favorable answer.
- The explicitly configured ADU candidate route appears first. Point to its
  visible consequence, citation, and source-status label, then open its details.
  Walk through the separate 15-business-day and
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
  jurisdiction reviewed the explanation. The dated Davis card keeps both the
  City's published categories and HCD's unresolved ordinance-status warning
  visible. Its review-pending draft asks staff which current path applies; it
  does not make an eligibility or ordinance-compliance finding.
- Switch the intake/results to Spanish. Be explicit that Spanish
  plain-language copy is an unreviewed machine draft with no semantic-parity
  review. Applicant-facing result titles are localized drafts; canonical
  pathway labels, source excerpts, citations, and document hints remain
  English.
- Open the optional clock disclosure and name its single-date assumption. The
  ADU route's deadline link opens the same disclosure.
- The trust moment: select an SB 9 fact combination with no matching encoded
  rule → the system abstains and routes to staff. "No match means insufficient
  encoded evidence, not ineligibility."
- Show the unpermitted-unit legalization path (§ 66311.7) as an example of a
  homeowner workflow often omitted by developer-oriented intake.

### 2b. Bounded packet-presence sample (5 min)

- Before following the packet link, show the strict program-availability
  record. The official City of Woodland program page was checked 2026-08-09
  and says **“Preapproved ADU List: Coming soon!”** No listed City plan was
  identified. Say plainly: “This flagship is a source-bound future-state
  simulation, not a currently usable preapproved plan or an applicant-ready
  workflow.” The browser blocks the link when that record is missing,
  malformed, or expired; a passing check permits only the labeled simulation.
- Follow the simulation link to `prepare.html`. State that this is a generated,
  made-up record, not a real applicant packet, completeness assessment, pilot,
  or external validation result. **Yes** in the prior applicability gate did
  not establish that a City plan is available.
- Show that the Python evaluator compared explicit synthetic facts and
  inventory statuses with 25 requirements from one City of Woodland
  preapproved ADU checklist, source checked 2026-07-29. The checklist is not
  presented as inherently dated. The public browser validates and renders the
  generated result; it does not run a second evaluator.
- Show the parcel-aware fixture panel. Two fabricated values are bound to the
  real `CITY` and `LU_Descr` fields in the dated Yolo County public
  parcel-layer metadata. No address, APN, or live parcel was queried; this
  demonstrates evidence shape, not verified parcel facts.
- Read the result: three known gaps, five items needing confirmation, 14
  reported present, and three not applicable from the made-up facts. Open one
  missing item, one staff question, and one reported-present item. Emphasize
  that reported presence is not file inspection or a finding that contents
  are correct.
- Open the generated evidence manifest. Point to both source bindings, the
  per-fact provenance/source-field/date records, requirement and packet
  fingerprints, per-item source locators, inventory, source-status date and
  review deadline, findings, staff questions, and explicit boundary.
- Show the action-copy status. AI proposed the checklist mapping and
  plain-language actions before runtime. The mapping and actions are
  fingerprint-bound, versioned, and `prototype_review_pending`; no named
  applicant, planner, counsel, Woodland reviewer, or other jurisdiction
  representative has approved them. The mapping records exact input-source
  fingerprints, but provider, model, and a reproducible run record were not
  retained.
- Name the runtime and privacy boundary: no model runs in the Python evaluator,
  CLI, build, or public browser; the bundled sample stores no applicant data.
  The evaluator does not open files, query or verify a live parcel, determine
  legal sufficiency, certify completeness, limit staff requests, or predict
  approval.
- If demonstrating the CLI, run
  `PYTHONPATH=src python3 -m permit_pathways.readiness_cli --as-of 2026-07-30`.
  Its JSON is the same evidence-manifest shape committed for the sample.

### 3. The verification harness: Scenario C (5 min)
- Open **Evidence & updates**. Start with **Snapshot used by this build**:
  checked August 3, 2026, 19 unchanged, 0 changed, and 0 could not be
  re-fetched. Open the exact GitHub Actions run and the machine-readable
  receipt. Say that receipt status `reviewed` means deliberately selected for
  this repository build; it is not legal, jurisdiction, counsel, or named-human
  content approval, and it is not a live per-page source check.
- Show the separate rule-review coverage. All 19 current rules are
  `machine_linked`; zero have a named human review or jurisdiction approval.
  Schema version 2 requires any promotion to bind both citation and full-rule
  fingerprints. Citation drift, rule drift, a changed dependency, source age,
  or review age demotes the effective claim. If showing the CLI, read its
  exact result as `automated source/regression checks: pass`—bounded automation
  passed; it is not a substantive review or approval claim.
- Show that every current rule record has dated source evidence inside the
  review window. For Davis, distinguish the watched City handout and HCD letter
  from the blocked, unwatched municipal-code reference, and point out that the
  local/state interaction still needs human resolution.
- Watched sources table: content hashes of the March 2026 ADU Handbook and
  April 2026 SB 9 fact sheet; weekly automated re-fetch (show the GitHub
  Action) reports when either changes or becomes unreachable and retains a
  proposed JSON receipt. Automation does not rewrite the public snapshot.
- One click: rehearse an amendment to § 66321. Five dependent rules flip
  stale; matching result cards rerender and withhold their drafted actions,
  while unrelated records remain unchanged. Follow the link into the
  applicant guide to show the stale state. Label this as a temporary simulation
  layered over—not written into—the adopted snapshot. Durable strict snapshot
  propagation is implemented; automatic adoption, packet-field assignments,
  named ownership, and a staffed disposition workflow are not. "This is what
  the morning after the legislative session should look like."
- 29 structured golden scenarios replay in the browser. They prove matcher
  regression behavior, not natural-language accuracy or jurisdiction
  acceptance.
- The held-out scanner contract is separately validated but unrun. Its future
  unit is one passage/check pair; it will report recomputable raw flag/quiet and
  abstention counts only after official passages, two independent initial
  reviews, adjudication, freeze custody, and blind predictions exist.

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
- Rules, sources, and the golden set are portable files. A schema-v1 command
  packages the exact Git-tracked public/synthetic evidence profile into a
  deterministic ZIP, verifies its hashes and source digests, and restores it
  inertly without vendor-only tooling. This is prototype-data portability,
  not applicant-data or CPRA export, contractual ownership or offboarding,
  partner acceptance, or a backup. Production retention, privacy review, and
  security controls remain deployment work. The demo persists no applicant
  data. Decision support, not a legal agent, is stated on every page.
- Built for low-capacity jurisdictions: static-friendly, runs beside existing
  permitting systems, no rip-and-replace.
- Teaming: this verification layer composes with full-pipeline platforms and is
  happy to be the trust layer inside someone else's stack.

### 5. What I want from you (3 min)
- Market-research honesty: the bounded packet-presence manifest is executable,
  but it is a future-state simulation because Woodland currently lists no
  preapproved plan. Its checklist mapping, action copy, and usefulness have
  not been validated. The adopted source-state overlay and browser holds are
  executable, but the maintenance process has not been exercised as a timed,
  staffed, end-to-end re-verification and republication workflow.
- Ask: which one jurisdiction and currently active ADU subtype should be the deep pilot, which
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
  and supporting excerpt. The Davis local record verifies only three
  City-published processing categories while preserving HCD's unresolved
  ordinance-status warning; it does not establish the operative ordinance or
  decide which category applies. The current `verified_on` field records dated
  source evidence, not jurisdiction or counsel approval. Encoding was
  machine-assisted; a named human review level and execution of the separately
  `not_run` held-out contract are next. The public evidence page shows the
  actual review level: all 19 rules
  are `machine_linked`, with no named review. The separate Woodland checklist
  mapping has automated source, schema, and fingerprint checks, but no
  applicant, planner, counsel, or jurisdiction validation; its official
  program-page record also says no preapproved plan list is available yet.
