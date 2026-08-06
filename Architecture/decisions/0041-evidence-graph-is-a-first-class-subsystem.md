# ADR-0041: The Evidence Graph is a first-class subsystem, not a pipeline stage

**Status:** Accepted
**Date:** 2026-08-04
**Decided:** 2026-08-04 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** deliberation, evidence, ddd, foundational

---

## Context

Page 09 named an "Evidence Graph" as one stage in a linear pipeline: `Quant Models -> Evidence Graph -> Committee Debate -> Portfolio Impact -> Risk Constraints -> Decision -> Explanation`. `../review/R09_Evidence_Graph.md` found that as specified it is a container, not a reasoning structure: nodes exist, edges are unspecified, weights are unspecified, and nothing consumes the graph's structure. Each desk still receives a flat slice of its own engine's output, which cannot represent confluence (evidence agreeing for a shared reason), contradiction at the evidence level, or dependence (two nodes sharing a fitted model).

ADR-0013 already decided that desk citations are references to evidence nodes, never literal values. That decision presumes something citable exists with stable identity, derived edges, and a weight function. Nothing in pages 00-16 built that thing; R09 designed it. The question this ADR resolves is whether the designed graph is a pipeline step internal to page 09, or a subsystem with its own container, contract, and container-diagram entry.

## Options considered

**A. Leave it as a pipeline stage inside page 09.**
*Pros:* no new container, no new page.
*Cons:* a "stage" has no independent latency budget, no independent failure mode, no independent degraded-mode contract, and — critically — no place to state the invariant that a hallucinated number is structurally unrepresentable. `../review/R19_Missing_Components.md` already lists it as C15, a new container, because the review found it needed all of these.

**B. Fold it into the AI Investment Committee (page 08) as an internal data structure.**
*Pros:* keeps the "committee" story in one page.
*Cons:* the graph is built deterministically and read by six desks; it does not belong to any one desk, and page 08's isolation boundary ("a desk sees only its own engine's output") would have to be rewritten as "a desk sees a slice of a shared graph," which is a large enough change to page 08's contract to warrant its own record rather than a silent edit.

**C. Promote it to a first-class subsystem (C15) sitting between Market Intelligence (BC4) and Deliberation (BC5), with its own page, contract, and container entry.**
*Pros:* gives the graph an owner, a latency budget, a degraded-mode contract, and a place for the weighting/propagation/contradiction-classification logic that R09 designed. Makes the "AI never calculates" rule structural rather than aspirational, because the graph — not the LLM — is what produces the weights and the propagated baseline.
*Cons:* one more container to deploy and operate.

## Decision

**Option C.** The Evidence Graph is container C15, specified in full in `../17_Evidence_Graph.md`, sitting inside BC5 Deliberation but architecturally distinct from the Committee (page 08) that reads it. Desks receive a **graph slice** — their engine's nodes plus every node connected by an edge, edge types visible — never a flat engine dump and never write access to the graph.

## Rationale

The graph's most important property, the graph-baseline posterior computed before any desk is polled, only means anything if the graph is a subsystem with its own deterministic computation path, checkable independently of whether the Committee agrees with it. If the graph were merely a data structure inside page 08, "does the Committee ever disagree with the graph" would not be a testable question, because there would be no graph-only output to compare against. That comparison — `graph_committee_divergence` — is the test that makes the Committee's existence falsifiable (R09 §5), and it requires the graph to be built and sealed before the Committee runs, by a component that does not know what the Committee will conclude.

## Consequences

**Positive**
- The graph gets its own latency budget (page 17: <500ms assembly), its own degraded-mode contract, and its own security boundary, none of which a "stage" can meaningfully have.
- Citations (ADR-0013) now point at something with a real lifecycle: sealed, content-addressed, immutable.
- Counterfactual replay (page 09's Future Expansion) becomes a graph ablation query, available immediately rather than deferred.

**Negative**
- One more container in the C4 model (C15, already anticipated in `../review/R19_Missing_Components.md` §13) and one more service to operate and monitor.
- Page 09's original three-line description of "Evidence Graph" as a stage is now understated relative to what actually ships; page 09 is not edited (frozen), so a reader of page 09 alone will underestimate this component until they reach page 17.

**Neutral**
- The Committee's isolation boundary (page 08) is preserved in spirit and strengthened in practice: a desk still cannot see another engine's raw output, but can now see that a contradiction exists and what kind, which page 09's original design could not represent.

## Tripwire

1. If graph assembly latency regularly exceeds the 500ms budget and materially delays the Committee's 10s cycle, revisit whether the graph should be incrementally maintained rather than rebuilt per cycle.
2. If `graph_committee_divergence` is never measured in production, this decision has been implemented in name only — the metric, not the container boundary, is the point. Absence of the metric for more than one full quarter after go-live is the signal to re-open this ADR.
3. If a desk is ever found reading another desk's slice directly rather than through the graph, the isolation boundary has been bypassed and the container boundary did not prevent it — a code-level, not architectural, failure, but one this ADR's existence should have made harder to introduce by accident.

## Related

- ADR-0013 (citations are references, not values) — the decision this ADR gives a real mechanism to
- ADR-0002 (deterministic/AI separation) — the graph is the clearest embodiment of this rule outside the sizing chain
- `../17_Evidence_Graph.md` — the full specification
- `../review/R09_Evidence_Graph.md` — the design rationale in depth
- `../08_AI_Investment_Committee.md`, `../09_Decision_Intelligence_Layer.md` — the two pages this subsystem now sits between
- `../review/R19_Missing_Components.md` §13 (C15)
- Source: `../09_Decision_Intelligence_Layer.md`
