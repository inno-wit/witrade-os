# ADR-0013: Desk citations are references to evidence nodes, never literal values

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** ai, correctness, audit, evidence

---

## Context

The platform's central architectural claim is that the AI never calculates (ADR-0002). Page 09 states the rule. Page 08 enforces it by validating that any number appearing in a desk's reasoning also appears in that desk's inputs.

Page 08 then correctly identifies the weakness of its own mechanism: a rounded number produces a false rejection. A desk that says "volatility is at the 91st percentile" when the input was `90.7` fails a string match despite being entirely correct. Page 08 offers no fix.

The problem is deeper than rounding. The mechanism is **inverted**. It detects hallucinated numbers after they have been generated, using string matching over free prose. That approach has three failure modes that cannot all be fixed:

- **False positives** from rounding, unit changes, and reformatting.
- **False negatives** from a hallucinated number that happens to coincide with a real input elsewhere in the context.
- **Semantic drift** with no numeric signature at all: "the regime has been bullish for hours" when the regime flipped twelve minutes ago.

Detecting hallucinated numbers is strictly weaker than making them unrepresentable.

There is a second problem the current design does not name. Page 09 lists "explanation drifts from decision" as a failure mode. When the rationale is free prose generated alongside the stance, nothing structurally binds the two. The explanation shown to the operator can be a plausible story that is not what drove the decision.

## Options considered

**A. Improve the validator.** Numeric tolerance, unit normalisation, better extraction.
*Pros:* no schema change; incremental.
*Cons:* it is an arms race against a generative model, in free text, with no terminating condition. Every tolerance widened to fix a false positive opens a false negative. Semantic drift is untouched.

**B. Constrain the desk output to a fixed schema of stance and confidence only, with no rationale.**
*Pros:* nothing to hallucinate.
*Cons:* destroys explainability, which is a primary reason the committee architecture exists at all. An unexplained stance cannot be reviewed, cannot be red-teamed, and cannot be learned from.

**C. Citations as references, rationale as a template.** A desk emits a stance, a raw confidence, a list of `{node_id, node_hash}` citations into the sealed evidence graph, a rationale **template** with positional placeholders, and the bindings from placeholders to citations. The rendering layer substitutes actual values from the evidence graph at display time.
*Pros:* a hallucinated number is not expressible; the rounding problem disappears because there is nothing to string-match; the explanation is guaranteed to match the evidence; counterfactual replay is trivial (rebind the same template to a different graph).
*Cons:* a more constrained output format that the model must follow reliably; templates read slightly more stiffly than free prose; a desk can still misuse a legitimate node.

## Decision

**Option C.** A desk **never emits a number**. It emits references.

Rejected output shape (current page 08):

```jsonc
{ "reasoning": "Regime is bullish with 78% probability and vol at the 91st percentile" }
```

Required output shape:

```jsonc
{
  "stance": "long",
  "confidence_raw": 72,
  "citations": [
    {"node_id": "regime:XAUUSD:M15:2026-08-03T14:30:00Z:p_bull", "node_hash": "sha256:a1..."},
    {"node_id": "vol:XAUUSD:M15:2026-08-03T14:30:00Z:percentile",  "node_hash": "sha256:b7..."}
  ],
  "rationale_template": "Regime is bullish at {{0}} and volatility sits at {{1}}, which favours continuation over mean reversion.",
  "rationale_bindings": [0, 1]
}
```

Binding rules:

1. **Schema-enforced.** The desk response schema permits no free numeric field. A response containing a bare numeral outside a citation is a hard validation failure, and the desk abstains.
2. **Citations must resolve.** Every `node_id` must exist in the sealed evidence graph presented to that desk, and every `node_hash` must match. A citation to a node the desk was not given is a hard violation, detectable with no NLP.
3. **Every placeholder must bind.** A template with an unbound `{{n}}` is invalid.
4. **Rendering happens at display time**, from the evidence graph, never from anything the desk produced.
5. **`confidence_raw` is the one number a desk emits**, it is an integer 0-100, and it is never used as a weight without calibration (ADR-0028).

## Rationale

This converts the platform's central architectural claim from a policy into a property. Under this design a hallucinated number is not something to be caught, it is something that cannot be written down. That is a categorically stronger guarantee than any validator.

The knock-on effects are large and mostly free:

- Page 08's rounding false-negative problem disappears entirely. There is nothing to match.
- Page 09's "explanation drift" failure mode is eliminated by construction, because the explanation is literally rendered from the same nodes the decision cited.
- Counterfactual replay ("what would this desk have concluded if volatility had been at the 40th percentile") becomes a rebinding of an existing template rather than a fresh LLM call, which makes it cheap enough to do routinely.
- The audit record improves: a stored decision contains the exact node IDs and hashes, so the rationale can be re-rendered years later with certainty that it shows what drove the decision.

**The residual risk is honest and named:** a desk can still misuse a legitimate node, saying "volatility is low" while citing a node whose value is the 91st percentile. That is a *reasoning* error, not an arithmetic one. It is caught by the Red Team desk and by calibration scoring, and it is a fundamentally more tractable problem than hallucinated arithmetic, because it is visible to a reader comparing the rendered text against the rendered value.

Option A is rejected because it has no terminating condition. Option B is rejected because it trades away the explainability the whole design exists to provide.

## Consequences

**Positive**
- Hallucinated numbers are unrepresentable.
- Explanation and decision cannot diverge.
- Counterfactual replay is cheap.
- The desk output schema is machine-checkable end to end, with no NLP in the validation path.
- Evidence usage becomes measurable: which nodes actually drive decisions, and which are never cited, which feeds directly into R09's weighting and into pruning dead evidence.

**Negative**
- The output format is more constrained, and model compliance must be verified per model version. A model that produces malformed templates at a material rate is not usable, and this becomes a promotion gate.
- Templates are stiffer than free prose. The rendered result is slightly less fluent than an unconstrained model would produce. This is a fair price.
- The evidence graph must be rich enough that desks can express what they mean using only its nodes. This puts real design pressure on R09's node taxonomy, and a desk that repeatedly cannot express a valid observation is a signal that the graph is missing a node type.

**Neutral**
- One more validation stage at the desk boundary, sub-millisecond.

## Tripwire

Track `desk_schema_violation_rate` per desk and per model version. If it exceeds 2% for a given model, either the prompt needs work or that model is not suitable. If it exceeds 2% across every model, the format is too hard and this decision needs revisiting rather than the prompts.

Also track `citations_per_opinion` and the distribution of cited nodes. A desk citing the same two nodes on every cycle is not reasoning over the graph, and that is a finding this instrumentation surfaces for free.

## Related

- ADR-0002 (deterministic/AI separation) is the principle this ADR makes structural
- ADR-0028 (confidence calibration)
- ADR-0029 (Red Team desk) catches the residual reasoning-error risk
- ADR-0030 (prompt registry)
- `../review/R03_Domain_Model_DDD.md` §5 (identified as the highest-leverage single change in the review)
- `../review/R09_Evidence_Graph.md`
- `../review/R10_Committee_Architecture.md`
- Source: `../08_AI_Investment_Committee.md`, `../09_Decision_Intelligence_Layer.md`
