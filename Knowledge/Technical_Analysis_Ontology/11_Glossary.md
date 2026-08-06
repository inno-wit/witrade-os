# 11 — Glossary

**Domain:** Cross-volume terminology
**Depends on:** `00_Technical_Analysis_Ontology.md` through `10_Confidence_Model.md`
**Status:** Draft, non-normative

---

## Purpose

One alphabetical list, one line each, for every term this volume defines or relies on — entity names from chapters 01-06, schema and relationship vocabulary from chapters 08-09, confidence terms from chapter 10, and the small set of Architecture-layer acronyms (ADR, BC, ACL) a reader needs without re-reading the frozen pages. Where chapter 07 groups entities by domain and chapter 09 groups them by schema `field`, this chapter's only organizing principle is the alphabet — optimized purely for "I heard this term, what does it mean."

## A

- **ACL (Anti-Corruption Layer)** — a translation boundary that converts an external or untrusted input (news prose, a broker feed) into a typed, bounded internal representation. `05_Execution_Context.md`
- **ADR (Architecture Decision Record)** — a versioned, numbered decision document in `Architecture/decisions/`. Referenced throughout this volume as the source of a specific rule (e.g. ADR-0013, ADR-0027).
- **Aggregation / Scoring** — terminology note; resolves to Confidence Propagation or the Committee's log-odds pooling, not a third mechanism. `06_Evidence_Generation.md`
- **ANALOGOUS_TO** — edge type: a historical precedent resembles the current situation. No instance yet in this ontology. `08_Relationship_Model.md`

## B

- **BC (Bounded Context)** — a DDD-style ownership boundary (e.g. BC5 Deliberation). `Architecture/19_Bounded_Context_Map.md`
- **BOS (Break of Structure)** — a swing point broken in the direction of the prevailing structural trend. `02_Market_Structure.md`
- **Breaker Block** — an Order Block that mitigates and is then broken through, flipping role. Ontology-proposed. `04_Price_Efficiency.md`
- **Buy Side Liquidity** — a Liquidity Pool positioned above current price. `03_Liquidity.md`

## C

- **Candlestick Momentum** — per-bar body/ATR ratio, a finer-grained read than the oscillator-based Momentum entity. `05_Execution_Context.md`
- **CHoCH (Change of Character)** — the first swing break against the prevailing structural trend. `02_Market_Structure.md`
- **CONFLUENT_WITH** — edge type: two independent nodes align spatially or thematically. `08_Relationship_Model.md`
- **Confidence Propagation** — log-odds accumulation with dependence-discount producing the `graph_baseline_posterior`. `06_Evidence_Generation.md`, formalized `10_Confidence_Model.md`
- **Consolidation** — a swing run with no BOS/CHoCH and low Structure Confidence. Ontology-proposed. `02_Market_Structure.md`
- **CONSTRAINS** — edge type: one node bounds how another is interpreted, without invalidating it. `08_Relationship_Model.md`
- **Context Confidence** — composite of News, Execution Costs, and Time feeding the Execution Desk's `conviction_raw`. `05_Execution_Context.md`
- **Contradiction** — a classified conflict between two nodes, detected before the Committee is convened. `06_Evidence_Generation.md`
- **CONTRADICTS** — edge type: two nodes disagree in a way the graph must surface, not hide. `08_Relationship_Model.md`
- **conviction_calibrated** — a desk's `conviction_raw`, converted to an empirical probability via isotonic regression (ADR-0028). Committee layer, outside this volume's scope. `10_Confidence_Model.md`
- **conviction_raw** — a desk's uncalibrated self-reported confidence (0-100); never used directly as a weight (ADR-0028).
- **Correction** — a retracement leg following an Impulse, producing no continuation BOS. Ontology-proposed. `02_Market_Structure.md`
- **Cross Asset Context** — correlated-instrument moves and intermarket signals. `01_Market_State.md`

## D

- **Decay / Aging** — the general term for Freshness's time-progression; not a separate mechanism. `06_Evidence_Generation.md`
- **DERIVED_FROM** — edge type: one node is a deterministic function of another. `08_Relationship_Model.md`
- **Derived (node type)** — a deterministic combination of other nodes, produced by the graph builder, never by an LLM. `Architecture/17_Evidence_Graph.md`, `06_Evidence_Generation.md`
- **Discount** — price in the lower half of a defined range. `04_Price_Efficiency.md`

## E

- **Efficiency Zones** — a ranked composite view of unmitigated FVGs/OBs. Ontology-proposed. `04_Price_Efficiency.md`
- **Equal Highs / Equal Lows** — swing points within tolerance forming a Liquidity Pool. `03_Liquidity.md`
- **Evidence Graph** — the sealed, content-addressed graph of nodes and edges every deliberation cycle assembles. `Architecture/17_Evidence_Graph.md`
- **Evidence Type** — one of the nine closed node types (`Observation`, `Level`, `State`, `Forecast`, `Event`, `Constraint`, `PortfolioFact`, `Precedent`, `Derived`). `06_Evidence_Generation.md`
- **Execution Costs / Slippage** — the measured gap between an approved trade's expected and actual fill terms. `05_Execution_Context.md`
- **Explainability** — the `explain()` interface's four rendered views over a sealed graph. `06_Evidence_Generation.md`
- **External Structure** — swing structure at the higher of two adjacent analyzed timeframes. `02_Market_Structure.md`

## F

- **Fair Value Gap (FVG)** — a 3-candle imbalance where price displaced without two-way participation. `04_Price_Efficiency.md`
- **Field (schema)** — the closed vocabulary string identifying what a node represents within its `type`, e.g. `bos`, `fvg`. `09_Evidence_Schema.md`
- **Freshness** — the mandatory `staleness` object on every node, tracking age against a maximum before evidence is discounted to zero. `06_Evidence_Generation.md`
- **Freshness Factor** — the numeric `freshness(n)` term Node Weight multiplies by, derived from `staleness`. `10_Confidence_Model.md`

## G

- **Gap Fill Probability** — the empirical probability an FVG of a given size and regime is filled within N bars. Ontology-proposed. `04_Price_Efficiency.md`
- **Grab** — synonym for Sweep in most SMC teaching material; not a second computed entity. `03_Liquidity.md`
- **Graph-Baseline Posterior** — the deterministic, LLM-free log-odds reference probability computed once per cycle. `06_Evidence_Generation.md`, formalized `10_Confidence_Model.md`

## H

- **HH (Higher High)** — a swing high exceeding the prior swing high. `02_Market_Structure.md`
- **HL (Higher Low)** — a swing low exceeding the prior swing low. `02_Market_Structure.md`

## I

- **Imbalance** — page 06's own descriptive name for a Fair Value Gap; not a second entity. `04_Price_Efficiency.md`
- **Impulse** — a displacement leg between two swing points that produced at least one FVG. Ontology-proposed. `02_Market_Structure.md`
- **Independence Discount** — the `SHARES_MODEL_WITH`-derived factor that stops correlated nodes from being double-counted. `10_Confidence_Model.md`
- **Institutional Absorption** — a narrative claim about large participants absorbing supply/demand; not observable with any current data source. `03_Liquidity.md`
- **Internal Structure** — swing structure at the lower of two adjacent analyzed timeframes. `02_Market_Structure.md`
- **INVALIDATES** — edge type: one node's occurrence removes another's standing as live evidence. `08_Relationship_Model.md`

## K

- **Kill Zones** — the London/NY/overlap high-liquidity windows; a skill-layer concept, not a Feature Store native category. `05_Execution_Context.md`

## L

- **LH (Lower High)** — a swing high below the prior swing high. `02_Market_Structure.md`
- **Liquidity Efficiency** — the rate at which detected pools are eventually swept. Ontology-proposed. `03_Liquidity.md`
- **Liquidity Pool** — an unswept cluster of swing highs or lows, the SMC substitute for order-book depth. `03_Liquidity.md`
- **Liquidity Strength** — the magnitude of a Liquidity Pool, by cluster size or tightness. Ontology-proposed. `03_Liquidity.md`
- **Liquidity Voids** — often used synonymously with Fair Value Gap; not a separately computed entity. `03_Liquidity.md`
- **LL (Lower Low)** — a swing low below the prior swing low. `02_Market_Structure.md`

## M

- **Macro Environment** — rates, DXY, yield curve, and risk-on/off score. `01_Market_State.md`
- **Magnet** — a qualitative heuristic label for price being "drawn toward" a pool; not an independently computed value. `03_Liquidity.md`
- **Market Phase** — a `Derived` composite of Market Regime state and Volatility percentile. `01_Market_State.md`
- **Market Regime** — a GARCH -> Markov Switching -> HMM probabilistic classification over `{bull, bear, sideways}`. `01_Market_State.md`
- **Mitigation** — the boolean tracking whether an FVG or Order Block has been price-filled. `04_Price_Efficiency.md`
- **Mitigation Block** — an Order Block that is mitigated and holds, without a subsequent break-through. Ontology-proposed. `04_Price_Efficiency.md`
- **Momentum** — the multi-bar, oscillator-based read (RSI, MACD, Stochastic). `05_Execution_Context.md`
- **MSS (Market Structure Shift)** — a synonym some SMC schools use for CHoCH; not a separately computed entity. `02_Market_Structure.md`

## N

- **News** — ACL-2's typed, sanitized output from a news provider feed; raw text never reaches a desk. `05_Execution_Context.md`
- **NO_ACTION** — the cycle outcome when unresolved contradiction weight exceeds threshold, or evidence assembly fails, before any desk is polled. `Architecture/17_Evidence_Graph.md`
- **Node Weight** — see Weight.

## O

- **Order Block (OB)** — the last opposing candle before a displacement move. `04_Price_Efficiency.md`
- **Observation (node type)** — a raw measured fact. `Architecture/17_Evidence_Graph.md`

## P

- **PRECEDES** — edge type: temporal ordering between two events. No instance yet in this ontology. `08_Relationship_Model.md`
- **Precedent (node type)** — a historical analogue, `as_of`-filtered. `Architecture/17_Evidence_Graph.md`
- **Premium** — price in the upper half of a defined range. `04_Price_Efficiency.md`
- **Provenance** — the mandatory `{snapshot_id, feature_versions}` record on every node, enabling reproducibility. `06_Evidence_Generation.md`

## R

- **Reclaimed Block** — an Order Block violated, then reclaimed by a second reversal. Ontology-proposed. `04_Price_Efficiency.md`

## S

- **Session** — Asia/London/NY/overlap classification via `smc.sessions()`. `01_Market_State.md`
- **Sell Side Liquidity** — a Liquidity Pool positioned below current price. `03_Liquidity.md`
- **SHARES_MODEL_WITH** — edge type: two nodes share a fitted model, so their independence must be discounted. `08_Relationship_Model.md`
- **Spread** — named by page 08 as an Execution Desk input; no independent computation is defined. Honest gap. `05_Execution_Context.md`
- **State (node type)** — a classification with a probability vector, e.g. a regime label. `Architecture/17_Evidence_Graph.md`
- **Stops / Resting Orders** — inferred stop-loss or pending order locations; not observable, no order-book data source exists. `03_Liquidity.md`
- **Structure Confidence** — a 0-10 composite requiring at least 2 of 5 confluence factors. `02_Market_Structure.md`
- **Structure Strength** — the ATR-normalized displacement magnitude of a swing leg. Ontology-proposed. `02_Market_Structure.md`
- **SUPPORTS** — edge type: one node's value increases confidence in another's read. `08_Relationship_Model.md`
- **Sweep** — a Liquidity Pool level crossed intrabar and closed back on the originating side. `03_Liquidity.md`
- **Swing Point** — a local high or low pivot, the base primitive for the entire Market Structure domain. `02_Market_Structure.md`

## T

- **Time** — day-of-week and time-to-next-scheduled-event. `01_Market_State.md`
- **Trend (macro read)** — a `Derived` directional interpretation of Market Regime's state. `01_Market_State.md`
- **Trend (structural read)** — the HH/HL vs. LH/LL sequence read, distinct from the macro-read Trend. `02_Market_Structure.md`

## V

- **Volatility** — six regime-conditioned metrics: ATR, Forecast Vol, Realized Vol, Expected Move, Volatility Percentile, Tail Risk. `01_Market_State.md`
- **Volume** — present as a raw `Bar` field (BC1) but not a named Feature Store category. Honest gap. `05_Execution_Context.md`

## W

- **Weight** — `weight(n) = reliability x freshness x quality x regime_applicability x independence`, the node-level confidence primitive. `06_Evidence_Generation.md`, formalized `10_Confidence_Model.md`

## Z

- **Zone Freshness** — time elapsed since an FVG or OB's formation, while unmitigated; feeds the `freshness(n)` weighting term directly. `04_Price_Efficiency.md`
- **Zone Strength** — the ATR-normalized displacement magnitude that created a zone. Ontology-proposed. `04_Price_Efficiency.md`

---

## Related

- Previous: `10_Confidence_Model.md`
- `07_Entity_Reference.md` — the same entity set, grouped by chapter and status instead of alphabetically
- `09_Evidence_Schema.md` — the closed `field` vocabulary these terms resolve to
- Back to: `00_Technical_Analysis_Ontology.md`
