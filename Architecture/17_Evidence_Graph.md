# 17 — Evidence Graph

**Diagram:** `17_Evidence_Graph.excalidraw`
**Phase:** 11 — Architecture Completion (1 of 5)
**C4 Level:** L3 — Component
**Depends on:** `03_Feature_Store.md`, `04_Regime_Engine.md`, `05_Volatility_Engine.md`, `06_Market_Structure_Engine.md`, `07_ML_RL_Model_Layer.md`, `09_Decision_Intelligence_Layer.md`
**Container:** C15 (`generated/16_Container_Model_v2.md`)
**Status:** Draft — promotes `review/R09_Evidence_Graph.md` from review finding to canonical page. R09 remains the design record of *why*; this page is the design record of *what ships*.
**Bounded context:** BC5 Deliberation (`19_Bounded_Context_Map.md`)

---

## Purpose

Sit between the Research Platform (pages 03-07) and the AI Investment Committee (page 08) as a first-class subsystem, not a pipeline stage. Page 09 originally named an "Evidence Graph" step that structures raw engine output into nodes; this page is what that step had to become once it was asked to carry the platform's central claim: **every number a desk cites is a reference to a fact this graph produced, and the fact is verifiable by walking the graph, never by re-trusting the LLM that cited it.**

The graph is the mechanism behind ADR-0013 (citations are references, not values). Without it, ADR-0013 is a policy with no place to point. With it, a hallucinated number is structurally unrepresentable, not merely detectable after the fact.

## Responsibilities

- Assemble every relevant `Observation`, `Level`, `State`, `Forecast`, `Event`, `Constraint`, `PortfolioFact`, and `Precedent` node for one deliberation cycle into a single, immutable, content-addressed graph.
- Derive every edge deterministically from node attributes and a versioned rule table. No LLM asserts an edge, ever.
- Compute a weight for every node from reliability, freshness, quality, regime applicability, and independence.
- Propagate a graph-baseline posterior (log-odds) for `LONG`/`SHORT` before any desk is polled, so the Committee's conclusion can be measured against a deterministic reference.
- Detect and classify contradiction (timeframe, direct, model, stale, data) before the Committee is convened, and short-circuit to `NO_ACTION` when unresolved contradiction weight exceeds threshold.
- Serve graph slices to each desk: a desk's assigned engine's nodes plus every node connected by an edge, edge types visible, never another desk's raw engine output.
- Render all four explanation views (one-line, decision card, full trace, counterfactual) from the sealed graph, never by re-generating text from the decision.

## Node model

| Node type | Represents | Produced by |
|---|---|---|
| `Observation` | A raw measured fact | Engines 04-07 |
| `Level` | A price locus (OB, FVG, liquidity, grid, swing) | Structure engine (06) |
| `State` | A classification (regime label + probability vector) | Regime engine (04) |
| `Forecast` | A forward estimate with uncertainty | Volatility (05), ML (07) |
| `Event` | A scheduled or occurred discrete event | Calendar, News ACL |
| `Constraint` | A hard boundary | Risk (BC6), Reference Data (BC2) |
| `PortfolioFact` | Current book state | Position Ledger (BC7) |
| `Precedent` | A historical analogue, `as_of`-filtered | Learning (BC9), see §7 below |
| `Derived` | A deterministic combination of other nodes | Graph builder itself |

Node identity: `{type}:{symbol}:{timeframe}:{as_of}:{field}`. Every node carries `value`, `as_of`, `source{engine, version, params_ref}`, `staleness{is_stale, age_s, max_age_s, severity}`, `reliability`, `weight`, and `provenance{snapshot_id, feature_versions}` without exception — there is no "unknown freshness" state (ADR-0034).

## Edge model

Nine deterministic edge types: `SUPPORTS`, `CONTRADICTS`, `CONFLUENT_WITH`, `DERIVED_FROM`, `SHARES_MODEL_WITH`, `INVALIDATES`, `CONSTRAINS`, `PRECEDES`, `ANALOGOUS_TO`. Each has a stated derivation rule versioned in the edge rule table (a domain-parameter artefact per R04 §5, point-in-time resolvable). `SHARES_MODEL_WITH` is the mechanism that makes the Regime/Volatility GARCH dependence explicit and correctable, closing the double-counting gap page 08 names but does not fix.

## Weighting and propagation

```
weight(n) = reliability(n) x freshness(n) x quality(n) x regime_applicability(n) x independence(n)
```

Multiplicative, so any factor at zero removes the evidence entirely (correct semantics for critical staleness). Confidence propagates by log-odds accumulation with a dependence-discount term subtracted for nodes sharing a fitted model — full derivation in `review/R09_Evidence_Graph.md` §4-5, canonical here going forward.

## Inputs

Feature Store output (03) and every Research Platform engine output (04-07), Reference Data constraints (BC2), live `PortfolioSnapshot` (BC7), scheduled/occurred `Event` nodes from the calendar and the Untrusted Text ACL (never raw text — ADR-0032).

## Outputs

One sealed `EvidenceGraph` per deliberation cycle: `{graph_id, content_hash, nodes[], edges[], graph_baseline_posterior, contradiction_report}`, consumed by every desk (as a slice) and by the Decision Record Store in full.

## Dependencies

Every Research Platform engine (03-07) must publish before a cycle can assemble; Position Ledger (BC7) for `PortfolioFact` nodes; the Precedent index (Learning, BC9) for `Precedent` nodes; the Reference Data Master (BC2) for `Constraint` nodes.

## Owns (exclusive)

- The `EvidenceGraph` aggregate and its node/edge tables (own schema; no other context writes here).
- The edge derivation rule table and its version history.
- The graph-baseline posterior computation.

No other component may construct an `EvidenceGraph`, and no desk may write to it — the graph is read-only from the Committee's perspective (ADR-0002, deterministic/AI separation, applied at the container boundary).

## Interfaces

| Call | Direction | Contract |
|---|---|---|
| `assemble(symbol, timeframe, as_of) -> EvidenceGraph` | Called by the Deliberation orchestrator (page 08's Portfolio Manager) | Synchronous, must complete inside the cycle's evidence-assembly budget below |
| `slice(graph_id, desk) -> GraphSlice` | Called once per desk, in parallel | Returns only nodes the desk's engine owns plus first-order connected nodes, with edge types visible |
| `explain(decision_id, view) -> RenderedExplanation` | Called by the dashboard and by post-mortem tooling | `view` one of `one_line`, `decision_card`, `full_trace`, `counterfactual` |
| `ablate(graph_id, node_id) -> HypotheticalPosterior` | Research/counterfactual only, never on the live path | Recomputes the graph-baseline posterior with one node removed |

## Events Published

- `evidence.graph.sealed` — cycle's graph is immutable and content-addressed; carries the hash every downstream `TradeProposal` must reference (ADR-0013).
- `evidence.contradiction.detected` — per contradiction found, classified by kind (§ below).
- `evidence.cycle.aborted` — unresolved contradiction weight exceeded threshold; cycle terminates `NO_ACTION` before any desk is polled.

## Events Consumed

`feature.updated`, `regime.updated` (renamed `RegimeClassified`/`RegimeShifted` under the domain event set — see `generated/15_Event_Catalog_v2.md`), `volatility.updated`, `structure.updated`, `model.prediction`, portfolio snapshot updates from BC7, `Event` nodes from the calendar/News ACL.

## Invariants

1. A node is never constructed without an explicit `staleness` field (ADR-0034).
2. An edge is never asserted by an LLM call; every edge traces to a rule-table entry and the node attributes that triggered it.
3. A sealed `EvidenceGraph` is immutable. A correction is a new graph with a new `as_of` or a `supersedes` link, never a mutation (mirrors page 01's raw-data rule, ADR-0036, extended upward).
4. A graph containing any node with `staleness.severity == critical` cannot be sealed into a state that permits a `TradeProposal`; the cycle terminates `NO_ACTION` (hardens page 08's "required to be discounted" into a structural block, per R03 §4 invariant).
5. Canonical serialisation is byte-stable: two runs producing the same graph produce the same hash. Key ordering, float formatting, and timestamp precision are pinned. This is what the replay determinism test (R01 §10) actually checks.

## Failure Modes

- **Assembly incompleteness** — a Research Platform engine's output exists but a schema mismatch prevents the graph builder from converting it to a node, producing a silent blind spot rather than an error.
- **Edge rule table staleness** — a new evidence type ships without a corresponding rule-table entry, so it can be included as a node but never participates in `SUPPORTS`/`CONTRADICTS` reasoning.
- **Contradiction misclassification** — a genuine model contradiction is classified as a benign timeframe hierarchy (or vice versa), which either hides a regime-change signal or manufactures false deadlocks.
- **Precedent small-sample deception** — a `Precedent` node with a low `sample_size` is treated by a desk as a strong signal despite the schema-mandated discount.

## Degraded Mode

| Condition | Behaviour |
|---|---|
| One Research Platform engine unavailable | That engine's node types are omitted, not defaulted. The graph is sealed as-is; desks reading only that engine abstain (not a neutral vote — R03 §4) |
| Precedent index unavailable | Graph seals with zero `Precedent` nodes; desks reason without historical analogues, which is a documented capability reduction, not a fabricated one |
| Graph assembly exceeds budget | Cycle aborts `NO_ACTION` with reason `evidence_assembly_timeout`, never a partial or best-effort graph reaching the Committee |
| Contradiction weight above threshold | Cycle aborts `NO_ACTION` with reason `evidence_conflict` before any desk is polled — cheaper and cleaner than a post-vote deadlock |

## Recovery Strategy

Graph assembly is itself deterministic and unit-tested against the current schema of every upstream engine; a new engine output field requires an explicit graph-schema update, never silent inclusion or exclusion. The graph-baseline posterior versus the Committee's pooled posterior is a first-class, permanently logged metric (`graph_committee_divergence`) — a persistent gap in either direction is a calibration finding, and if the Committee never disagrees with the graph baseline, the LLM layer is adding nothing and should be removed. This is the falsifiability test the pre-graph design could not run.

## Latency Budget / SLO

- Graph assembly: **< 500ms p99** per cycle (deterministic Python, in-memory).
- Slice serving per desk: **< 50ms p99**.
- `explain()` rendering: **< 200ms p99** for `one_line`/`decision_card`; `full_trace` and `ablate()` are not on the hot path and carry no SLO.
- Availability: assembly must succeed or abort cleanly; there is no partial-success state (see Invariant 4).

## Security Boundary

- Reads from every Research Platform engine and BC7's published read model; writes only to its own schema.
- No inbound calls from OPS or DMZ. Sits entirely in CORE (R15 §2).
- `explain()` output filtering follows the caller's role: an `auditor` receives `full_trace`; a dashboard viewer receives `one_line`/`decision_card` only, per R15 §9.
- The graph never contains raw untrusted text (ADR-0032) — only the typed, schema-clamped output of the Untrusted Text ACL ever becomes an `Event` or `Observation` node.

## Technology

`networkx` in-memory per cycle, canonically serialised and stored as a content-addressed blob in MinIO with node/edge rows also written to Postgres for querying (R09 §9 phase P0-P1). A Postgres recursive-CTE layer is the P2 promotion; a dedicated graph store (Neo4j/Memgraph/Kùzu) is P3 and adopted only if cross-cycle multi-hop queries become routine and CTE latency exceeds ~1s.

## Future Expansion

- Cross-symbol confluence detection (a locus shared across correlated instruments) once the Instrument Master's cluster map (R11 §4) is live.
- Streaming graph updates intra-cycle for very short timeframe trading, evaluated only after the batch-per-cycle model is proven.

---

## Related

- `review/R09_Evidence_Graph.md` — the full design rationale this page canonicalises
- `08_AI_Investment_Committee.md`, `09_Decision_Intelligence_Layer.md` — the pages this subsystem now sits between
- `decisions/0013-citations-are-references-not-values.md`, `decisions/0041-evidence-graph-is-a-first-class-subsystem.md`
- `19_Bounded_Context_Map.md` — BC5 Deliberation, `EvidenceGraph` entity
- `review/R03_Domain_Model_DDD.md` §4-5
- Previous: `16_C4_Container_Diagram.md` (source ADD) / `generated/16_Container_Model_v2.md` (C15)
- Next: `18_Portfolio_Construction.md`
