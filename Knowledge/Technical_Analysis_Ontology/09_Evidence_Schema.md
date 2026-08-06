# 09 — Evidence Schema

**Diagram:** `09_Evidence_Schema.excalidraw`
**Domain:** Schema extension of the Evidence Graph
**Computed by:** Evidence Graph node model (`Architecture/17_Evidence_Graph.md` §Node model), extended here for TA-specific `field` values
**Depends on:** `06_Evidence_Generation.md`, `08_Relationship_Model.md`
**Status:** Draft, non-normative — a proposed vocabulary, not a deployed schema validator

---

## Purpose

Page 17 fixes the node identity format — `{type}:{symbol}:{timeframe}:{as_of}:{field}` — and the mandatory attribute set (`value`, `as_of`, `source`, `staleness`, `reliability`, `weight`, `provenance`), but leaves `field` an open string: whatever a Research Platform engine chooses to publish. That is correct at the Architecture layer, which must stay generic across every engine it will ever host. It is a gap at the ontology layer: nothing stops two future contributors from independently naming the same concept `structure_confidence` and `struct_conf`, silently fragmenting evidence a desk should have treated as one fact. This chapter closes that gap for Technical Analysis specifically — a single closed table mapping every entity in chapters 01-06 to the exact `field` string it populates, so `field` is a controlled vocabulary within this domain even though page 17 does not require one platform-wide.

## Node identity, recapped

```
{type}:{symbol}:{timeframe}:{as_of}:{field}
```

Example: `Level:XAUUSD:M15:2026-08-05T14:30:00Z:order_block_bullish`

Every node also carries, without exception (ADR-0034, page 17 §Node model): `value`, `as_of`, `source{engine, version, params_ref}`, `staleness{is_stale, age_s, max_age_s, severity}`, `reliability`, `weight`, `provenance{snapshot_id, feature_versions}`.

## Field vocabulary — 01 Market State

| Entity | `field` | Node type | `value` shape |
|---|---|---|---|
| Market Regime | `market_regime` | `State` | `{state, probabilities, confidence, transition_matrix}` |
| Market Phase | `market_phase` | `Derived` | `{phase: enum}` |
| Trend (macro read) | `trend_macro` | `Derived` | `{direction: enum}` |
| Volatility | `volatility_atr`, `volatility_forecast`, `volatility_realized`, `volatility_expected_move`, `volatility_percentile`, `volatility_tail_risk` | `Forecast` / `Observation` | one field per metric, per ch. 01's six-metric definition |
| Session | `session` | `Observation` | `{session: enum, is_overlap: bool}` |
| Time | `time_context` | `Observation` / `Event` | `{day_of_week, time_to_next_event, event_type}` |
| Macro Environment | `macro_environment` | `Observation` | `{rates, dxy, yield_curve, risk_on_off_score}` |
| Cross Asset Context | `cross_asset_context` | `Observation` | `{correlated_moves, intermarket_signals}` |

## Field vocabulary — 02 Market Structure

| Entity | `field` | Node type | `value` shape |
|---|---|---|---|
| Swing Point | `swing_point` | `Level` | `{type, price, bar_index}` |
| BOS | `bos` | `Level` | `{direction, broken_swing, bar_index}` |
| CHoCH | `choch` | `Level` | `{direction, broken_swing, bar_index}` |
| Structure Confidence | `structure_confidence` | attribute (not a node) | `float [0,10]` on the parent `Level`/composite |
| External Structure | `structure_external` | `Level` | Same shape as Swing Point, higher timeframe |
| Internal Structure | `structure_internal` | `Level` | Same shape, lower timeframe |
| HH/HL/LH/LL | `swing_label` | attribute | `enum {HH, HL, LH, LL}` on the parent Swing Point node |
| Trend (structural read) | `trend_structural` | `Derived` | `{structural_direction: enum}` |

## Field vocabulary — 03 Liquidity

| Entity | `field` | Node type | `value` shape |
|---|---|---|---|
| Liquidity Pool | `liquidity_pool` | `Level` | `{level, cluster_swings, side, swept}` |
| Buy/Sell Side Liquidity | `liquidity_pool` (attribute `side`) | `Level` | Same node, `side` resolved |
| Equal Highs/Lows | `liquidity_pool` (attribute `swings`, `tolerance_pct`) | `Level` | Attribute set on the same node |
| Sweep | `sweep` | `Event` | `{pool, sweep_bar, wick_extent, closed_back}` |

## Field vocabulary — 04 Price Efficiency

| Entity | `field` | Node type | `value` shape |
|---|---|---|---|
| Fair Value Gap | `fvg` | `Level` | `{high, low, direction, mitigated, mitigated_at}` |
| Order Block | `order_block` | `Level` | `{high, low, direction, mitigated, mitigated_at}` |
| Mitigation | attribute on `fvg` / `order_block` | mutation | `{mitigated: bool, mitigated_at: timestamp\|null}` |
| Premium / Discount | `premium_discount` | `Derived` | `{zone: enum, distance_from_midpoint_pct}` |
| Zone Freshness | attribute on `fvg` / `order_block` | attribute | `{age_bars, age_duration}` |

## Field vocabulary — 05 Execution Context

| Entity | `field` | Node type | `value` shape |
|---|---|---|---|
| News | `news_sentiment` | `Observation` | `{sentiment_score, headline_category, relevance, timestamp}` |
| Execution Costs / Slippage | `execution_slippage` | `Observation` | `{expected_price, fill_price, slippage_bps, within_tolerance}` |
| Candlestick Momentum | `candle_momentum` | `Observation` | `{body_pct, direction, atr_normalized_body}` |
| Momentum | `momentum` | `Observation` | `{rsi, macd, stochastic}` |
| Context Confidence | `context_confidence` | `Derived` | `{context_confidence: float, contributing_factors}` |

## Field vocabulary — 06 Evidence Generation

Chapter 06's entities are largely mechanism, not new `field` values — `Weight`, `Freshness`, and `Provenance` are mandatory attributes on *every* node above, not separate nodes with their own field name. The exceptions:

| Entity | `field` | Node type | `value` shape |
|---|---|---|---|
| Contradiction | `contradiction` | `Event` | `{kind, node_a, node_b, weight}` |
| Confidence Propagation | `graph_baseline_posterior` | field on sealed `EvidenceGraph`, not a node | `float` (log-odds) |

## Entities with no `field` entry

Consistent with every chapter's own honesty discipline, three categories deliberately have no row above:

1. **Terminology notes** (MSS, Imbalance, Grab, Liquidity Voids) — resolve to an existing `field` (`choch`, `fvg`, `sweep`) and must never be given a second field name, or the fragmentation this chapter exists to prevent recurs immediately.
2. **Interpretive, not observable** (Stops/Resting Orders, Institutional Absorption, Magnet) — per ADR-0013, cannot be assigned a `field` because no engine produces a `value` for them.
3. **Ontology-proposed** (Impulse, Correction, Consolidation, Structure Strength, Liquidity Efficiency, Liquidity Strength, Breaker/Mitigation/Reclaimed Block, Efficiency Zones, Gap Fill Probability, Zone Strength) — a `field` name is proposed informally in their home chapter's derivation table, but does not enter this closed vocabulary until adopted via RFC+ADR. Pre-registering a field for an uncomputed entity would let a desk reference a `field` string with no engine ever populating it — the exact failure page 17's edge-rule-table-staleness failure mode describes (§Failure Modes: "a new evidence type ships without a corresponding rule-table entry").

## Edge rule table entry format

Page 17 states every edge traces to a rule-table entry (§Invariants: "an edge is never asserted by an LLM call"). This ontology does not redefine that table's schema, but records the shape a TA-specific rule entry takes, for consistency with chapter 08's consolidated edge tables:

```
{
  rule_id: string,
  edge_type: one of the 9 types (page 17 §Edge model),
  from_field: field value (this chapter's vocabulary),
  to_field: field value,
  condition: deterministic predicate over both nodes' attributes,
  version: semver, point-in-time resolvable (ADR-0034)
}
```

Example, from ch. 02/03/04's Confluence Rule: `{rule_id: "confluence_v1_fvg_bos", edge_type: CONFLUENT_WITH, from_field: "fvg", to_field: "bos", condition: "abs(fvg.midpoint - bos.broken_swing.price) / price < 0.005", version: "1.0.0"}`.

## Failure Modes / Known Gaps

- This vocabulary is proposed at the ontology layer; it is not enforced by any deployed schema validator today. A future graph-builder change should treat this chapter's tables as the source of truth for TA `field` names, per `governance/Policies/Implementation_Change_Control.md`.
- If two future engine changes independently add overlapping fields (e.g. a native Volume feature and a native Spread metric, both honest gaps in ch. 05), this chapter must be updated in the same change that ships them, or the fragmentation problem this chapter exists to prevent will recur for exactly the entities most likely to be extended next.

## Future Expansion

- Once any ontology-proposed entity is adopted, move its row from "Entities with no field entry" into the appropriate domain table with its real, ADR-approved field name.
- A machine-readable version of these tables (JSON Schema or a `field` enum in the graph builder's own config) would let this chapter's vocabulary be validated automatically rather than maintained by convention.

---

## Related

- Previous: `08_Relationship_Model.md`
- `Architecture/17_Evidence_Graph.md` §Node model — canonical node identity and mandatory attributes
- `07_Entity_Reference.md` — the entity list this schema assigns field names to
- `10_Confidence_Model.md` — where `weight`, `reliability`, `freshness` are formalized as computations, not just schema fields
- Next: `10_Confidence_Model.md`
