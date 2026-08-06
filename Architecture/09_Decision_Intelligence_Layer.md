# 09 — Decision Intelligence Layer

**Diagram:** `09_Decision_Intelligence_Layer.excalidraw`
**Phase:** 5 — Decision Intelligence
**C4 Level:** L2 — Container
**Depends on:** `08_AI_Investment_Committee.md`
**Status:** Draft

---

## Purpose

Page 08 defines what happens *inside* the Committee. This page defines the container-level flow the Committee sits inside — from raw quant model output, through debate, to a fully-explained, portfolio-aware Decision. It is the L2 view that shows how Decision Intelligence connects to its neighbors (Quant Research upstream, Risk Management downstream) rather than the L3 internals of the Committee itself.

## The Governing Rule

> **The AI reasons. It does NOT calculate. Python calculates.**

Every stage in this pipeline either transforms data mechanically (Python, deterministic, testable) or reasons about already-computed data (LLM, the Committee stage only). No stage does both. This is the single most important architectural constraint in the entire platform — violate it once (let an LLM compute a number instead of citing one) and the audit trail this layer exists to provide becomes worthless.

## Responsibilities

Take the combined output of the Quant Research Platform, structure it into evidence the Committee can debate, run that debate, evaluate the resulting recommendation against current portfolio state and hard risk constraints, and produce a Decision with a complete, human-readable Explanation.

## Pipeline

```
Quant Models          (aggregated pages 04-07 output)
  -> Evidence Graph     (structures raw output into linked evidence nodes)
  -> Committee Debate    (page 08 — the only AI-reasoning stage)
  -> Portfolio Impact    (how does this change current exposure/correlation?)
  -> Risk Constraints    (hard deterministic checks — page 10)
  -> Decision             (approve / reject / defer, with evidence lineage)
  -> Explanation           (human-readable rationale)
```

## Inputs

Aggregated outputs from Regime Engine (04), Volatility Engine (05), Market Structure Engine (06), ML/RL Model Layer (07).

## Outputs

A Decision (approve / reject / defer) with full Explanation, passed to Risk Management (page 10) for final gating — note this layer's "Decision" is not the same as Risk Management's "Approved Trade." This layer decides whether the *recommendation* is sound; Risk Management separately decides whether the *portfolio* can currently accept it. Both must say yes.

## Dependencies

Quant Research Platform (pages 04-07) directly; AI Investment Committee (page 08) is the debate stage embedded in this pipeline, not a separate upstream dependency — it's internal to this layer.

## Events Published

- `evidence.graph.built` — per cycle, before debate starts (useful for replay/audit — lets you reconstruct exactly what evidence the Committee saw).
- `decision.made` — approve/reject/defer with full lineage.
- `decision.explained` — Explanation rendered, pushed to dashboard + Journal.

## Events Consumed

`model.prediction`, `regime.updated`, `volatility.updated`, `structure.updated` (via the Committee's own trigger events from page 08).

## Failure Modes

- **Evidence Graph incompleteness** — a relevant piece of Quant output exists but isn't wired into the graph, so the Committee never sees it (a silent blind spot, not an error).
- **Portfolio Impact staleness** — evaluating impact against portfolio state that's a few seconds out of date during fast-moving conditions.
- **Explanation drift from Decision** — the rendered human-readable explanation doesn't actually match the evidence lineage that produced the Decision (a rendering bug, not a reasoning bug, but equally damaging to trust).

## Recovery Strategy

- Evidence Graph construction is itself deterministic and unit-tested against the current schema of every upstream engine (pages 04-07) — a new engine output field requires an explicit graph-schema update, not silent inclusion/exclusion.
- Portfolio Impact reads the same live state source Risk Management uses (page 10), not a cached copy — if that state is stale, both layers are stale together and consistently, not divergently.
- Explanation is generated directly *from* the evidence lineage object (not regenerated independently from the Decision) — the lineage is rendered, not re-summarized, eliminating the drift failure mode by construction.

## Latency Budget

Dominated by the Committee Debate stage (page 08's < 10s budget). Evidence Graph construction and Portfolio Impact/Risk Constraints checks: **< 1s combined** — these are deterministic Python, not LLM calls.

## Technology

Python for Evidence Graph, Portfolio Impact, Risk Constraints, Decision, and Explanation-rendering stages. The Committee Debate stage is the Claude API work described in page 08. Evidence Graph likely backed by a lightweight in-memory graph structure (networkx) rather than a persistent graph database at this scale — revisit if cross-symbol/cross-cycle graph queries become a real need.

## Future Expansion

- Persistent, queryable evidence graph (e.g., for "show me every decision that cited this SMC order block") once the Journal's query needs outgrow simple per-decision lookup.
- Counterfactual replay — re-running the Evidence Graph and Committee Debate against a historical Decision's inputs with a newer model version, to evaluate model upgrades against known outcomes before promoting them (ties into page 08's shadow-mode deployment practice).

---

## Related

- Previous: `08_AI_Investment_Committee.md`
- Next: `10_Risk_Portfolio_Platform.md` (Phase 6 — not yet built)
