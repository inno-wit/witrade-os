# 07 — Entity Reference

**Domain:** Cross-chapter compilation
**Computed by:** N/A — this chapter computes nothing; it indexes chapters 01-06
**Depends on:** `01_Market_State.md` through `06_Evidence_Generation.md`
**Status:** Draft, non-normative

---

## Purpose

Chapters 01-06 define roughly 50 entities across six domains, each with its own honesty status. A desk, an engineer extending the Evidence Graph, or a future chapter of this ontology needs one place to look up "what is this entity, which chapter defines it, and can it be cited today" without re-reading six chapters. This chapter is that index. It defines nothing new — every row links back to the chapter that is the entity's actual source of truth.

## How to read the Status column

This ontology has used five statuses consistently since chapter 01. Repeated here for reference:

| Status | Meaning |
|---|---|
| **Native** | Directly a frozen Architecture engine output, citable as evidence today |
| **Derived** | A deterministic composite of native outputs, computed by the graph builder (`Derived` node type, page 17), citable today |
| **Terminology note** | A synonym for an existing primitive — not a second entity, recorded to prevent double-counting or confusion |
| **Ontology-proposed** | Not computed by any frozen engine; would require an RFC and ADR to adopt (`governance/Policies/Implementation_Change_Control.md`) |
| **Interpretive, not observable** | A narrative claim no current data source can verify; per ADR-0013, cannot be a citable Evidence Graph node |

A small number of entities carry a compound or chapter-specific status (e.g. ch. 05's "Skill-layer, not Feature Store native," ch. 04's "Native-adjacent"); these are preserved as written in their home chapter rather than forced into the five above.

## 01 — Market State

| Entity | Status | Node type | One-line definition |
|---|---|---|---|
| Market Regime | Native | `State` | GARCH -> Markov Switching -> HMM classification over `{bull, bear, sideways}` |
| Market Phase | Derived | `Derived` | Market Regime state x Volatility percentile cross-product |
| Trend (macro read) | Derived | `Derived` | Directional interpretation of Market Regime's state |
| Volatility | Native | `Forecast` / `Observation` | Six metrics: ATR, Forecast Vol, Realized Vol, Expected Move, Percentile, Tail Risk |
| Session | Native | `Observation` | Asia / London / NY / overlap classification, `smc.sessions()` |
| Time | Native | `Event` / `Observation` | Day-of-week, time-to-next-event |
| Macro Environment | Native | `Observation` | Rates, DXY, yield curve, risk-on/off score |
| Cross Asset Context | Native | `Observation` | Correlated-pair moves, intermarket signals |

## 02 — Market Structure

| Entity | Status | Node type | One-line definition |
|---|---|---|---|
| Swing Point | Native | `Level` | Local high/low pivot, `swing_highs_lows()` |
| BOS (Break of Structure) | Native | `Level` | Swing broken in the direction of prevailing structure |
| CHoCH (Change of Character) | Native | `Level` | First swing break against prevailing structure |
| Structure Confidence | Native | attribute | 0-10 composite, >=2 of 5 confluence factors |
| External Structure | Derived | `Level` | Swing structure at the higher of two adjacent timeframes |
| Internal Structure | Derived | `Level` | Swing structure at the lower of two adjacent timeframes |
| HH / HL / LH / LL | Derived | attribute | Classical labels on consecutive Swing Points |
| MSS (Market Structure Shift) | Terminology note | — | Synonym for CHoCH in some SMC schools |
| Trend (structural read) | Derived | `Derived` | HH/HL vs. LH/LL sequence read, distinct from ch. 01's regime-level Trend |
| Impulse | Ontology-proposed | — | Displacement leg producing >=1 FVG |
| Correction | Ontology-proposed | — | Retracement leg with no continuation BOS |
| Consolidation | Ontology-proposed | — | Swing run with no BOS/CHoCH and low Structure Confidence |
| Structure Strength | Ontology-proposed | — | ATR-normalized displacement magnitude of a swing leg |

## 03 — Liquidity

| Entity | Status | Node type | One-line definition |
|---|---|---|---|
| Liquidity Pool | Native | `Level` | Unswept cluster of swing highs/lows, `liquidity()` |
| Buy Side Liquidity | Derived | attribute | Liquidity Pool above current price |
| Sell Side Liquidity | Derived | attribute | Liquidity Pool below current price |
| Equal Highs / Equal Lows | Derived | attribute | Swing Points within tolerance forming a pool |
| Sweep | Derived | `Event` | Pool level crossed intrabar, closed back on the originating side |
| Grab | Terminology note | — | Synonym for Sweep |
| Liquidity Voids | Terminology note | — | Often synonymous with Fair Value Gap (ch. 04) |
| Stops / Resting Orders | Interpretive, not observable | — | No order-book/DOM data source exists |
| Magnet | Interpretive, qualitative | — | Heuristic label, not an independently computed value |
| Institutional Absorption | Interpretive, not observable | — | Requires order-flow/volume-profile data not present in any Feature Store category |
| Liquidity Efficiency | Ontology-proposed | — | Ratio of swept to total pools over a rolling window |
| Liquidity Strength | Ontology-proposed | — | Cluster size / tolerance-band tightness, ATR-normalized |

## 04 — Price Efficiency

| Entity | Status | Node type | One-line definition |
|---|---|---|---|
| Fair Value Gap (FVG) | Native | `Level` | 3-candle imbalance, `fvg()` |
| Order Block (OB) | Native | `Level` | Last opposing candle before displacement, `ob()` |
| Mitigation | Native | mutation | Boolean: has price returned to fill the zone |
| Imbalance | Terminology note | — | Page 06's own name for FVG, not a second entity |
| Breaker Block | Derived (proposed) | — | Mitigated OB subsequently broken through, role flips |
| Mitigation Block | Derived (proposed) | — | Mitigated OB that holds, no break-through |
| Reclaimed Block | Derived (proposed) | — | Violated OB reclaimed by a second reversal |
| Premium / Discount | Derived | `Derived` | Price above/below the 50% midpoint of a defined range |
| Efficiency Zones | Ontology-proposed | — | Ranked map of unmitigated FVG/OB by recency and confluence |
| Gap Fill Probability | Ontology-proposed | — | Empirical fill probability by size and regime |
| Zone Strength | Ontology-proposed | — | ATR-normalized displacement magnitude at zone formation |
| Zone Freshness | Native-adjacent | attribute | Bars elapsed since formation, feeds `freshness(n)` (ch. 10) |

## 05 — Execution Context

| Entity | Status | Node type | One-line definition |
|---|---|---|---|
| News | Native, sanitized | `Observation` | ACL-2 typed output — sentiment, category, relevance, never raw text |
| Execution Costs / Slippage | Native | `Observation` | `execution.slippage.recorded`, expected vs. fill price |
| Candlestick Momentum | Derived | `Observation` | Body/ATR ratio, per-bar conviction read |
| Momentum | Native | `Observation` | RSI, MACD, Stochastic (Technical category) |
| Context Confidence | Derived | `Derived` | Composite of News, Execution Costs, Time -> Execution Desk input |
| Kill Zones | Skill-layer, not Feature Store native | — | Resolves to Session + Time, not a separately computed node |
| Volume | Honest gap | — | Raw `Bar` field exists (BC1); no derived Feature Store category |
| Spread | Honest gap (partially native) | — | Named by page 08 as a desk input; no independent computation defined |

## 06 — Evidence Generation

| Entity | Status | Node type | One-line definition |
|---|---|---|---|
| Evidence Type | Native | meta | The 9 closed node types every fact resolves to |
| Weight | Native | attribute | `reliability x freshness x quality x regime_applicability x independence` |
| Freshness | Native | attribute | `staleness{is_stale, age_s, max_age_s, severity}`, mandatory on every node |
| Decay / Aging | Derived (terminology note) | — | The general term for Freshness's time-progression, not a second mechanism |
| Contradiction | Native | `Event` | Classified conflict between two nodes, pre-Committee |
| Supporting / Composite Evidence | Native | edge / `Derived` | `SUPPORTS`/`CONFLUENT_WITH` edges, or a `Derived` combination node |
| Confidence Propagation | Native | computation | Log-odds accumulation with dependence-discount -> `graph_baseline_posterior` |
| Aggregation / Scoring | Terminology note | — | Resolves to Confidence Propagation or ADR-0027 pooling, no third mechanism |
| Provenance | Native | attribute | `{snapshot_id, feature_versions}`, mandatory on every node |
| Explainability | Native | read-model | `explain()`'s four views over the sealed graph |

## Summary counts

| Status | Count |
|---|---|
| Native | 24 |
| Derived | 13 |
| Terminology note | 6 |
| Ontology-proposed | 10 |
| Interpretive, not observable / qualitative | 3 |
| Honest gap / skill-layer / compound status | 4 |

Counts are entity rows, not sub-entities (e.g. HH/HL/LH/LL counts once). These numbers are a snapshot of this ontology's first draft — they will shift as ontology-proposed entities are adopted via RFC+ADR, and should be re-tallied at that point rather than trusted as permanently accurate.

---

## Related

- Previous: `06_Evidence_Generation.md`
- `01_Market_State.md` through `06_Evidence_Generation.md` — the source of truth for every row above
- `08_Relationship_Model.md` — the cross-entity relationship graph these entities participate in
- `11_Glossary.md` — one-line definitions in alphabetical order, distinct from this chapter's chapter-grouped view
- Next: `08_Relationship_Model.md`
