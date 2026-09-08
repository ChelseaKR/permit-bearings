# Runtime AI evaluation (ADR 0004)

Three committed case sets and one harness,
`python -m permit_pathways.ai.eval`. The scoring is model-independent; the
model under test is whatever `PERMIT_AI_PROVIDER` / `PERMIT_AI_MODEL`
select.

## What is measured

**Intake extraction** (`intake-cases.json`, 40 synthetic cases, 25 English
and 15 Spanish, across ADU, JADU, SB 9 two-unit, and SB 9 lot split, with
deliberately underspecified and inference-tempting cases). Each case has a
gold extraction over the material fields for its project type. Per field:

- `field_exact_match` — predicted equals gold, where `unknown == unknown`
  counts as a match because abstaining was the right answer;
- `abstained_when_should` — of the fields whose gold is `unknown`, the share
  the model returned as `unknown`;
- `filled_when_unknown` — of the same fields, the share the model filled
  with a concrete value. **This is the defect rate** the design exists to
  hold down ("absence rendered as a value"); it is reported on its own,
  never folded into accuracy;
- `known_field_exact` / `known_field_missed` / `known_field_wrong` — on
  fields the text does state, whether the model got it, abstained, or
  returned a different value;
- project-type and jurisdiction-slug accuracy, and the share of cases in
  which every field is right.

**Citation grounding** (`grounding-cases.json`, 8 confirmed-fact intakes).
Each intake is run through the deterministic matcher and then the
explanation prompt. A claim is *shown* only if every quote it cites occurs
verbatim in the named corpus document; otherwise it is *withheld*. Reported:
claims generated, shown, withheld, and the fraction with verified citations.
The same run drafts staff questions and reports what share carry a pointer
that resolves to a matched rule or an unresolved fact.

**Follow-up answering** (`ask-cases.json`, 44 questions over the same 8
confirmed-fact intakes, 28 English and 16 Spanish). Each question carries a
label saying what the offered passages can support, and the metric is
grounding and *abstention* — not whether the answer is a correct reading of
the law:

| label | correct behaviour | the defect |
| --- | --- | --- |
| `answerable_from_passages` (23) | answer, citing one of the recorded settling passages | — |
| `should_abstain` (10) | hand the question to staff, with or without stating what the sources *do* say | claims shown and nothing flagged for a person |
| `should_refuse_scope` (11) | show no claim at all | any claim shown. **Zero tolerance** |

`abstained_when_expected` deliberately means *deferred to staff*, not
*silent*. The live behaviour this project has already seen for a fee question
was a cited statement that the sources set no fee **plus** a staff question;
that is a better answer than silence, and scoring it as a failure to abstain
would push the model towards saying nothing.

An `answerable_from_passages` case must record the passage ids that would
settle it, and the loader refuses one that does not: a case with nothing
recorded would score whatever the model did and call it right. A test
additionally asserts that every recorded settling passage is one the
retrieval actually offers for that question — otherwise the metric would be
measuring the retrieval's silence while reading as a statement about the
model.

What these numbers do not measure: legal fidelity, whether a shown claim is
a correct reading of the passage it cites, Spanish quality, or comprehension.
A verified citation proves the passage exists and says those words. The
Spanish questions in `ask-cases.json` are machine-drafted and have not been
read by a qualified speaker.

## Results

`results/` holds one JSON file per recorded run. Each records
`run.status` (`recorded_live_run` or `not_run`), provider, model, prompt
versions, UTC date, and the Git commit the run used, then the per-case
detail. `tests/test_ai_eval.py` rejects a result file that claims a number
without that provenance, and a `not_run` record may carry **no** numeric
summary and no cases at all — a placeholder is a statement that nothing was
measured, and a placeholder full of figures is that statement contradicting
itself. Numbers are never written by hand.

**No `ask` result is committed yet.** The case set, the scorer and the
offline tests are in place; the numbers need one live run on a configured
provider, and a file naming a model nothing has answered is exactly what the
contract above refuses.

## Running

```sh
uv sync --extra ai
PERMIT_AI_PROVIDER=anthropic PYTHONPATH=src .venv/bin/python -m permit_pathways.ai.eval intake \
  --cases evals/ai/intake-cases.json --output evals/ai/results/<date>-intake-<provider>-<model>.json
PERMIT_AI_PROVIDER=bedrock PERMIT_AI_MODEL=global.anthropic.claude-sonnet-4-6 PYTHONPATH=src \
  .venv/bin/python -m permit_pathways.ai.eval grounding \
  --cases evals/ai/grounding-cases.json --output evals/ai/results/<date>-grounding-<provider>-<model>.json
```

A third provider runs the same two suites against a self-hosted
OpenAI-compatible endpoint, so what an open-weight model costs in abstention
and citation resolution is measured rather than assumed:

```sh
PERMIT_AI_PROVIDER=local PERMIT_AI_MODEL=<served-model> \
  PERMIT_AI_LOCAL_URL=http://127.0.0.1:11434/v1/chat/completions PYTHONPATH=src \
  .venv/bin/python -m permit_pathways.ai.eval intake \
  --cases evals/ai/intake-cases.json --output evals/ai/results/<date>-local-<model>-intake.json
```

**No local result is committed yet.** The provider and its offline controls
are in place; running it needs a host with the runtime and the weights, and a
result file that named a model nothing had answered would be exactly the
placeholder-carrying-numbers this directory's contract test exists to refuse.
The Bedrock numbers below stand on their own and are not a prediction of what
a smaller model would do.

`PERMIT_AI_MODEL` above is written out for the record; it is also the
Bedrock default, because `claude-sonnet-5` is not invokable on Bedrock from
this project's AWS account. Nothing here is measured against a model the
account cannot call.

`--limit N` runs the first N cases. Exit `1` means at least one case errored
(the result file lists them); `2` means no provider could be configured.

## Changing the cases

Gold follows the extraction policy in `permit_pathways.ai.intake`:
ordinary-meaning readings are allowed ("backyard cottage" is a new detached
ADU; "my house" is an existing single-family home), and a fact the text does
not state stays `unknown`. Changing the policy changes the gold; record both
in the same change. Every gold value must be in the vocabulary, and the gold
field set must be exactly the material fields for the gold project type —
the loader refuses anything else.
