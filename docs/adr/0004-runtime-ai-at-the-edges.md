# ADR-0004: Put AI at the edges of the applicant path, keep the matcher deterministic, and verify every citation against the committed corpus

**Status:** Accepted (owner-directed change of direction)
**Date:** 2026-08-21
**Deciders:** Repository owner
**Amends:** ADR-0002 (the static no-storage boundary is retained for the
static site; this ADR adds a separate, optional runtime component outside it)

## Context

Until this decision, the only AI in Permit Bearings ran at build time: the
plain-language explanation sidecar, the Woodland checklist mapping, and the
Spanish drafts were produced offline, labeled `ai_assisted` and
`prototype_review_pending`, and shipped as static data. The README, ADR-0002,
`docs/DATA-FLOW.md`, `SECURITY.md`, and the beta-operations ledger all stated
"no runtime external model call" as a deliberate guarantee, and the standards
manifest recorded the repository as `llm: false`.

The owner has directed that this is not enough for the product. The
California AI Permitting Innovation Showcase asks for AI-enabled tools, and a
purely deterministic matcher with a review-pending draft layer does not put AI
in the applicant's path. The applicant experience today requires a person to
already know how to answer nineteen structured questions about their project,
and the "questions for staff" list is generic. Those are exactly the places
where a language model can help, and exactly the places where an ungrounded
model does the most damage: a model that invents a lot size, a jurisdiction,
or a statutory threshold is this portfolio's dominant defect, "absence
rendered as a value."

The existing trust discipline in `AGENTS.md` does not forbid runtime AI. It
forbids letting model prose create or change a rule, treating model output as
verification evidence, filling gaps with inference, and positioning output as
legal advice or an eligibility finding. The decision below is designed so that
every one of those constraints is enforced by code, not by prompt wording.

## Decision

Add runtime AI in three bounded roles, implemented in a separate optional
Python service (`permit_pathways.ai`) that the static site can call when it is
running and must work without:

1. **Natural-language intake (the model structures input; it does not
   decide).** An applicant may describe the project in English or Spanish.
   The model extracts a draft of the same structured facts the deterministic
   matcher already consumes, and nothing else. Every extracted value must be
   one of the vocabulary's allowed values and must be supported by a quoted
   span of the applicant's own text; a value without a supporting quote is
   downgraded to `unknown` by the service. Fields the text does not answer
   are returned as "could not tell from what you wrote", never guessed. The
   draft pre-fills the existing form; the applicant reviews, edits, and
   submits. The matcher runs only on the confirmed form values.

2. **Deterministic matching is unchanged.** `screening.py` and its browser
   port are not touched by this decision. The model never sees a rule's
   criteria as something to evaluate and never produces a match. When the
   service explains a result it first re-runs the Python matcher on the
   confirmed facts and refuses to explain a rule set that differs from what
   the browser computed.

3. **Grounded explanation and staff questions (the model narrates; the corpus
   is the evidence).** Given the matched rules, the service retrieves passages
   from the committed `corpus/` documents those rules already depend on and
   asks the model for a plain-language explanation, in the applicant's
   language, in which every substantive claim cites a passage by ID and
   quotes it. The service then verifies each quote programmatically against
   the extracted corpus text. A claim whose citations do not all resolve is
   withheld, and the count of withheld claims is shown. Staff questions are
   drafted the same way, tailored to the applicant's unresolved facts and
   matched rules, and are labeled as drafts. All of this output is labeled
   AI-generated and carries the existing non-advice, non-eligibility,
   non-approval disclaimers.

A fourth role, drafting candidate rule entries from pasted ordinance text, is
permitted only as an explicitly unreviewed draft written outside `data/rules/`
for a person to review; it can never be loaded by the matcher or published by
the service.

Consequential choices:

- **Provider and model.** The Anthropic API with `claude-sonnet-5` is the
  configurable default. Amazon Bedrock is supported through the same SDK, and
  its default is `global.anthropic.claude-sonnet-4-6` rather than the same
  model: this project's AWS account cannot invoke `claude-sonnet-5` on
  Bedrock, where `InvokeModel` answers `403 anthropic.claude-sonnet-5 is not
  available for this account` while the entitlement API reports it
  authorised. Bedrock is the path every recorded evaluation in
  `evals/ai/results/` ran on, so the two defaults differ on purpose and each
  should move only against a live invocation. The credential comes only from
  the environment; no key is ever written to the repository or to a file the
  service creates.
- **No applicant data is stored or logged by the service.** The service keeps
  no request body, writes no applicant text to disk or logs, and returns
  nothing it did not compute for that request. The model provider's own
  retention applies to the request while it is processed; that is a
  subprocessor relationship that a deployment must document and review before
  the service is exposed to real applicants.
- **The static site remains static.** With the service absent, `check.html`
  behaves exactly as before: zero network requests beyond its own origin,
  deterministic screening, sidecar explanations. The AI controls are disabled
  with a visible "needs the service running" note.
- **Evaluation is model-independent and committed.** A bilingual intake
  evaluation set with gold extractions, scored on per-field exact match and
  on abstention ("refused to guess when it should have"), and a
  citation-grounding evaluation that counts how many generated claims carry
  a citation that actually resolves, live in the repository with their
  harness. Measured numbers are committed only from a recorded live run that
  names the provider, model, date, and commit; otherwise the result is
  labeled `not_run`.

## Consequences

- Several public claims become false and are rewritten in the same change
  series: "no runtime external model calls" in the README, `SECURITY.md`,
  `docs/DATA-FLOW.md`, and `docs/PRODUCT-CONTEXT.md` now read "none in the
  static site; an optional AI service exists under ADR-0004." The standards
  manifest flag `llm` changes to `true`.
- ADR-0002 and `data/validation/beta-operations-readiness.json` continue to
  describe the static-only deployment, which is still the only deployment
  shape that has a prepared operations package. A deployment that includes
  the AI service is a different shape: it needs a host, a subprocessor
  record for the model provider, a cost envelope, abuse and rate limiting,
  a privacy review of the free-text field, and its own approvals. None of
  that is provided by this ADR; it is recorded as pending owner decisions.
- The capability matrix gains rows for natural-language intake, grounded
  explanation, tailored staff questions, and ordinance-to-rule drafting, each
  at `Prototype` once implemented and never above it until named human review
  of the prompts, the evaluation set, and the Spanish output exists.
- AI output remains review-pending in the same sense as the existing sidecar:
  labeled, versioned by prompt version, and never evidence of human, counsel,
  or jurisdiction review. The difference is that runtime output cannot be
  pre-reviewed, so the grounding verifier and the abstention rules are the
  review that exists, and their limits are stated next to the output.
- Runtime cost, latency, and provider availability become product
  properties. The service fails closed to the deterministic experience on
  any provider error.

## Alternatives considered

- **Keep AI at build time only.** Rejected by the owner: it leaves the
  applicant's path purely deterministic and does not meet the product goal.
- **A conversational agent that answers free-text questions directly.**
  Rejected for now. Free-text Q&A without a deterministic anchor makes the
  grounding problem open-ended; anchoring the explanation to a matched rule
  set keeps the retrieval scope to documents the rules already cite and makes
  the citation check exact.
- **Let the model evaluate rule criteria.** Rejected. The deterministic
  matcher is the product's verifiable core and the golden harness is its
  evidence; a model in that loop would make both unfalsifiable.
- **Vector embeddings for retrieval.** Not needed at this corpus size and
  scope. Retrieval is scoped by rule dependency and ranked lexically; this is
  inspectable and has no additional provider dependency. It can change later
  without changing the citation contract.
