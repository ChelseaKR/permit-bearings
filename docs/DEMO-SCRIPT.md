# Showcase demo script (40 min: 30 presentation + 10 Q&A)

Audience: state program staff (ODI/GovOps/CHHA/GO-Biz) + jurisdiction
observers. Goal: be the vendor they remember for *trust*, not features.

## Arc: "Every tool will show you an answer. I'll show you how a
## jurisdiction knows the answer is still right."

### 0. The opener — scan an ordinance live (5 min)
- Paste an ADU ordinance provision into the conformance scanner. Watch it
  flag the stale SB 477 citation, the 16-ft height cap, the subjective
  "similar styled roof design" — each with the controlling state law and
  the HCD enforcement letter where that exact failure mode appeared.
- The kicker: these are the *actual provisions* HCD quoted in its June 2025
  findings letter to Santa Clara County. The scanner independently re-derives
  HCD's findings. "HCD does this by hand, one letter at a time. This is that
  review, as software, validated against their own letters."
- Positioning sentence: "Symbium helps applicants navigate the rules as
  coded. PermitFlow helps builders file. Nobody verifies that the rules
  themselves — the ordinance, the handout, the chatbot's training corpus —
  are still lawful. That's us."

### 1. The problem nobody demos (4 min)
- Housing law changes every session. SB 477 (2024) renumbered all of state
  ADU law (§ 65852.2 → §§ 66310–66342); 2025 legislation renumbered sections
  again. Every handout, chatbot, and ordinance citing the old sections became
  wrong without anyone touching it.
- Live evidence: a pilot jurisdiction's municipal code still references the
  superseded numbering. Not hypothetical — flagged on the dashboard right now.
- Frame: correctness *decays*. An AI guidance tool without a currency
  mechanism is a liability with a friendly interface.

### 2. Applicant flow — Scenario A (8 min)
- Live intake: Davis homeowner, backyard ADU. Show pathway cards: ministerial
  routing, 60-day clock, 15-business-day completeness deadline, size/height/
  parking protections — every card citing its code section with the quoted
  source text and a verification date.
- Switch to Spanish. Same grounded content, one click.
- The trust moment: ask something the corpus doesn't support (SB 9 with
  exclusions unresolved) → the system abstains and routes to staff. "It would
  rather hand you to a person than guess."
- Unpermitted-unit path (§ 66311.7 legalization): the applicant nobody's
  tool serves, and one that matters for equity — pre-2020 units are
  disproportionately in lower-income neighborhoods.

### 3. The verification harness — Scenario C (10 min)
- Trust dashboard: % verified-current, the one honestly-unverified rule
  (Davis — source blocks automated retrieval; the system says so instead of
  pretending).
- Watched sources table: content hashes of the March 2026 ADU Handbook and
  April 2026 SB 9 fact sheet; weekly automated re-fetch (show the GitHub
  Action) opens an alert when HCD revises either.
- One click: rehearse an amendment to § 66321. Three dependent rules flip
  stale; unrelated rules stay verified; staff get a review queue. "This is
  what the morning after the legislative session looks like."
- Golden-question replay running in the browser — the jurisdiction's own
  acceptance test, re-run on every change.

### 4. Fit and posture (5 min)
- Jurisdiction owns everything: rules, corpus, golden set — plain JSON,
  exportable, no lock-in. CPRA-aware; minimal data collection (the demo
  collects none). Decision support, not a legal agent, stated on every page.
- Built for low-capacity jurisdictions: static-friendly, runs beside existing
  permitting systems, no rip-and-replace.
- Teaming: this verification layer composes with full-pipeline platforms —
  happy to be the trust layer inside someone else's stack.

### 5. What I want from you (3 min)
- Market-research honesty: the golden-set curation workflow and the staleness
  review queue are where jurisdiction staff feedback matters most.
- Ask: which two scenarios would a pilot jurisdiction want covered first, and
  who maintains the golden set — staff, vendor, or shared?

## Q&A prep (10 min)
- "What about Scenario B?" → The same harness architecture extends to staff
  reports and consistency review; v1 does one thing well per the challenge's
  own scope note.
- "LLM involvement?" → Deterministic rules where the standard is objective;
  retrieval-grounded generation only where interpretation is needed, always
  cited, always able to abstain. The harness doesn't care which layer answered
  — it verifies both.
- "Solo vendor risk?" → Working public code, dated history, CI, and a design
  where the jurisdiction owns everything — the bus factor is mitigated by
  exportability, not headcount. Open to teaming.
- "Accuracy of the rule base?" → Every rule links its quoted source excerpt;
  the harness's whole job is catching drift; staleness is surfaced, never
  hidden. Machine-assisted encoding, human verification pass, dated.
