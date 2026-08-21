# Runtime AI evaluation (ADR 0004)

Two committed case sets and one harness, `python -m permit_pathways.ai.eval`.
The scoring is model-independent; the model under test is whatever
`PERMIT_AI_PROVIDER` / `PERMIT_AI_MODEL` select.

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

What these numbers do not measure: legal fidelity, whether a shown claim is
a correct reading of the passage it cites, Spanish quality, or comprehension.
A verified citation proves the passage exists and says those words.

## Results

`results/` holds one JSON file per recorded run. Each records
`run.status` (`recorded_live_run` or `not_run`), provider, model, prompt
versions, UTC date, and the Git commit the run used, then the per-case
detail. `tests/test_ai_eval.py` rejects a result file that claims a number
without that provenance. Numbers are never written by hand.

## Running

```sh
uv sync --extra ai
PERMIT_AI_PROVIDER=anthropic PYTHONPATH=src .venv/bin/python -m permit_pathways.ai.eval intake \
  --cases evals/ai/intake-cases.json --output evals/ai/results/<date>-intake-<provider>-<model>.json
PERMIT_AI_PROVIDER=bedrock PERMIT_AI_MODEL=global.anthropic.claude-sonnet-4-6 PYTHONPATH=src \
  .venv/bin/python -m permit_pathways.ai.eval grounding \
  --cases evals/ai/grounding-cases.json --output evals/ai/results/<date>-grounding-<provider>-<model>.json
```

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
