# Showcase demo script (40 min: 30 presentation + 10 Q&A)

Audience: state program staff (ODI/GovOps/CHHA/GO-Biz) + jurisdiction
observers. Goal: be the vendor they remember for *trust*, not features.

Preflight: use the hosted demo, open `index.html` directly, or serve the
repository with `python3 -m http.server 8765`. After changing canonical JSON,
run `python3 scripts/build_demo_bundle.py` and the static-demo regression test.

## Arc: “Every tool will show you an answer. I’ll show you the evidence—and when it needs review.”

### 0. The opener — scan an ordinance live (4 min)
- Paste an ADU ordinance provision into the conformance scanner. Watch it
  flag the stale SB 477 citation, the 16-ft height cap, the subjective
  "similar styled roof design" — each with the controlling state law and
  the HCD enforcement letter where that exact failure mode appeared.
- The kicker: these are the *actual provisions* HCD quoted in its June 2025
  findings letter to Santa Clara County. For that named six-provision
  regression fixture, the scanner reproduces HCD's six expected review flags.
  It is a review queue, not a compliance verdict or statewide accuracy claim.
- Positioning sentence: "Permit platforms can help applicants navigate and
  file. This component makes the rule, handout, or AI corpus auditable as its
  sources change—and can sit inside somebody else's stack."

### 1. The problem nobody demos (3 min)
- Housing law changes every session. SB 477 (2024) renumbered all of state
  ADU law (§ 65852.2 → §§ 66310–66342); 2025 legislation renumbered sections
  again. Every handout, chatbot, and ordinance citing the old sections became
  wrong without anyone touching it.
- Live evidence: HCD's Santa Clara findings letter documents the obsolete
  numbering in an operative ordinance. The local Davis source in this
  prototype is unavailable and therefore labeled unverified, not treated as
  proof of a local defect.
- Frame: correctness *decays*. An AI guidance tool without a currency
  mechanism is a liability with a friendly interface.

### 2. Applicant flow — Scenario A (7 min)
- Live intake: Davis homeowner, backyard ADU. Show the grouped decision
  records: candidate routes first, relevant standards second, and the
  unverified Davis local-process record last. In one card, walk from “What
  this result means” through the separate 15-business-day and conditional
  60-day deadlines, then “What you can do next” and “Questions to ask staff.”
  Point to the always-visible citation and expand “Why we're saying this.”
- Name the integrity boundary: deterministic rules selected the record; the
  plain-language explanation is a versioned AI-assisted draft and cannot
  change the match. The unverified Davis card keeps the visible source and
  no-dated-source warning but withholds drafted actions, interpretive notes,
  and generic document hints rather than turning weak evidence into a
  confident answer.
- Switch the intake/results to Spanish. Be explicit that Spanish
  plain-language copy is an unreviewed machine draft with no semantic-parity
  review; pathway titles, source excerpts, and document hints remain English.
- Show the separate clock prototype and name its single-date assumption.
- The trust moment: select an SB 9 fact combination with no matching encoded
  rule → the system abstains and routes to staff. "No match means insufficient
  encoded evidence, not ineligibility."
- Show the unpermitted-unit legalization path (§ 66311.7) as an example of a
  homeowner workflow often omitted by developer-oriented intake.

### 3. The verification harness — Scenario C (7 min)
- Trust dashboard: % of rule records with dated source evidence inside the
  review window, plus the Davis record with no dated source check because its
  source blocks retrieval.
- Watched sources table: content hashes of the March 2026 ADU Handbook and
  April 2026 SB 9 fact sheet; weekly automated re-fetch (show the GitHub
  Action) reports when either changes or becomes unreachable.
- One click: rehearse an amendment to § 66321. Three dependent rules flip
  stale; matching result cards rerender and withhold their drafted actions,
  while unrelated records remain unchanged. Label this as a simulation;
  stable dependency IDs and a persisted review queue are the next
  implementation step. "This is what the morning after the legislative
  session should look like."
- Nine structured golden scenarios replay in the browser. They prove matcher
  regression behavior, not natural-language accuracy or jurisdiction
  acceptance.

### 3b. Data-driven determinations, not self-attestation (3 min)
- The parking exemption and 18-ft height allowance both turn on transit
  proximity. Run the GTFS module live against the Unitrans feed for a
  downtown Davis point. The local summer bus feed contains no stop meeting the
  encoded peak screen, but the statewide dataset supplies the Davis Amtrak
  major-stop candidate.
- The reveal is the disagreement, not a citywide legal conclusion: feed date,
  planned/current facility status, operator completeness, walking distance,
  and service-calendar logic all need confirmation. "Even the map and
  schedule are versioned evidence."

### 4. Fit and posture (3 min)
- Jurisdiction owns everything: rules, corpus, golden set — plain JSON,
  exportable, no lock-in. The demo persists no applicant data; production
  retention, CPRA export, and security controls remain deployment work.
  Decision support, not a legal agent, is stated on every page.
- Built for low-capacity jurisdictions: static-friendly, runs beside existing
  permitting systems, no rip-and-replace.
- Teaming: this verification layer composes with full-pipeline platforms —
  happy to be the trust layer inside someone else's stack.

### 5. What I want from you (3 min)
- Market-research honesty: the permit-readiness requirement manifest and the
  staleness review queue are where jurisdiction feedback matters most.
- Ask: which one jurisdiction and ADU subtype should be the deep pilot, which
  public/redacted packet examples can staff review, and who approves rule and
  translation changes?

## Q&A prep (10 min)
- "What about Scenario B?" → The same harness architecture extends to staff
  reports and consistency review; v1 does one thing well per the challenge's
  own scope note.
- "LLM involvement?" → Deterministic rules where the standard is objective;
  the current runtime has no live LLM. The next bounded AI step is
  page-evidenced document extraction and cited remedy drafting, with human
  approval and model-independent regression fixtures.
- "Solo vendor risk?" → Working public code, dated history, CI, and a design
  where the jurisdiction owns everything — the bus factor is mitigated by
  exportability, not headcount. Open to teaming.
- "Accuracy of the rule base?" → Every rule links its quoted source excerpt;
  the current `verified_on` field records dated source evidence, not
  jurisdiction or counsel approval. Encoding was machine-assisted; a named
  human review level and held-out evaluation are next.
