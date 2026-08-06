# R09 — Evidence Graph / Knowledge Graph

**Deliverable:** 9
**Delta against:** `09_Decision_Intelligence_Layer.md` (Evidence Graph stage), `08_AI_Investment_Committee.md`
**Status:** Review v1.0

---

## 1. The current design and why it is not yet a graph

Page 09 names an "Evidence Graph" stage that "structures raw output into linked evidence nodes", and proposes `networkx` in memory with a persistent graph store as future expansion. The instinct is right and unusually sophisticated for a pre-code document. But as specified it is a **container**, not a reasoning structure: nodes exist, edges are unspecified, weights are unspecified, and nothing consumes the graph structure. Each desk still receives a flat slice of its own engine's output.

The concrete consequence: with a flat structure, the Committee cannot represent the three things that actually distinguish a good trading decision from a bad one.

| Cannot represent | Example | Why it matters |
|---|---|---|
| **Confluence** (evidence agreeing for a shared reason) | An order block, unswept liquidity, and a grid level all sitting at 2,412 | Page 06 computes a confluence *count*. The graph should represent *why* they are confluent (they share a price locus), so the Committee can distinguish three genuinely independent signals from three views of the same thing |
| **Contradiction** | Regime says trending-bull; structure says CHoCH bearish on 4H | Page 08 handles this only at the vote level (dispersion → deadlock). Contradiction detected at the *evidence* level is far more informative than at the opinion level |
| **Dependence** | Regime and Volatility share a fitted GARCH model | Page 08 explicitly notes this correlation exists and expects it. Treating those two desks as independent votes double-counts one model's opinion. The graph makes the dependence explicit and the pooling can discount it |

Everything below builds the graph into a structure that supports these three, while preserving the constraint that made the ADD's design good: **the graph is built deterministically in Python; the LLM reads it, never writes it.**

---

## 2. Node model

Nodes are typed. A typed node model is what allows edges to be inferred deterministically rather than asserted by an LLM.

| Node type | Represents | Key attributes | Produced by |
|---|---|---|---|
| `Observation` | A raw measured fact | `value`, `unit`, `as_of`, `source_engine`, `source_version`, `staleness`, `quality_score` | Engines 04-07 |
| `Level` | A price locus | `price`, `kind` (OB / FVG / liquidity / grid / swing), `timeframe`, `age_bars`, `mitigated` | Structure engine |
| `State` | A classification | `label`, `probability_vector`, `calibrated`, `dwell_bars` | Regime engine |
| `Forecast` | A forward-looking estimate with uncertainty | `point`, `interval`, `horizon`, `model_version` | Volatility, ML |
| `Event` | A scheduled or occurred discrete event | `event_type`, `time`, `impact_tier`, `currencies` | Calendar, News ACL |
| `Constraint` | A hard boundary | `limit_type`, `current`, `max`, `headroom` | Risk, Instrument Master |
| `PortfolioFact` | Current book state | `symbol`, `net_qty`, `unrealised`, `correlation_to_proposed` | Position Ledger |
| `Precedent` | A historical analogue | `similarity`, `past_cycle_id`, `outcome_r`, `sample_size` | Learning (see §7) |
| `Derived` | A deterministic combination of other nodes | `formula_id`, `inputs`, `value` | Graph builder |

**Node identity:** `{type}:{symbol}:{timeframe}:{as_of}:{field}` (per R08 S7). Stable, addressable, citable.

**Every node carries, without exception:**

```jsonc
{
  "node_id": "state:XAUUSD:M15:2026-08-03T14:30:00Z:regime",
  "type": "State",
  "value": {"label": "trending_bull", "p": [0.71, 0.12, 0.17]},
  "as_of": "2026-08-03T14:30:00Z",
  "source": {"engine": "regime", "version": "2.3.1", "params_ref": "mlflow://..."},
  "staleness": {"is_stale": false, "age_s": 3, "max_age_s": 900, "severity": "ok"},
  "reliability": 0.82,        // see section 4
  "weight": 0.0,              // computed, see section 4
  "provenance": {"snapshot_id": 88421, "feature_versions": {...}}
}
```

`reliability` and `weight` are distinct and conflating them is a common error. Reliability is a property of the *source* (how much do we trust this engine's output in general, and in this regime). Weight is a property of the *node in this graph* (how much should this specific piece of evidence count in this specific decision).

---

## 3. Edge model

Edges are **derived deterministically** by the graph builder from node attributes. No LLM asserts an edge. This is the property that keeps the reasoning auditable.

| Edge | Meaning | Derivation rule (deterministic) |
|---|---|---|
| `SUPPORTS(a → b, s)` | `a` increases confidence in `b` | Directional agreement plus a domain rule table. E.g. `State(trending_bull) SUPPORTS Level(demand_ob)` with strength from regime probability |
| `CONTRADICTS(a → b, s)` | `a` decreases confidence in `b` | Opposite directional implication. E.g. `State(trending_bull)` vs `Observation(choch_bearish, tf=H4)` |
| `CONFLUENT_WITH(a ↔ b, d)` | Two levels occupy the same locus | `abs(a.price - b.price) / price < confluence_tolerance` (page 06's 0.5%) |
| `DERIVED_FROM(a → b)` | `a` is computed from `b` | From the lineage record (R08 M2). Not inferred |
| `SHARES_MODEL_WITH(a ↔ b)` | Two nodes depend on the same fitted model | From `source.params_ref` equality. **This is what makes the Regime/Volatility GARCH dependence explicit** |
| `INVALIDATES(a → b)` | `a` makes `b` no longer applicable | E.g. `Observation(ob_mitigated) INVALIDATES Level(demand_ob)` |
| `CONSTRAINS(a → b)` | `a` bounds what can be done about `b` | `Constraint` nodes to actionable nodes |
| `PRECEDES(a → b)` | Temporal ordering that matters | Higher-timeframe structure precedes lower-timeframe |
| `ANALOGOUS_TO(a ↔ b, sim)` | Current state resembles a historical one | From the Precedent index (§7) |

### Why deterministic edges matter

If an LLM could assert `SUPPORTS`, the audit trail would contain LLM-generated claims about relationships, and validating those claims would be as hard as validating the original reasoning. Deterministic edges mean the graph is a **fact** the Committee reasons over, exactly parallel to the ADD's existing and correct rule that engines compute and the LLM only reasons.

The trade-off is honest: the edge rule table is a piece of domain knowledge that must be maintained, versioned, and tested. It is configuration (R04 §5, domain parameters), point-in-time resolvable like everything else.

---

## 4. Evidence weighting

A node's weight in a decision is a product of independent factors. Multiplicative rather than additive so that any single factor going to zero removes the evidence entirely, which is the correct semantic for staleness and quality.

```
weight(n) = reliability(n)
          x freshness(n)
          x quality(n)
          x regime_applicability(n)
          x independence(n)
```

| Factor | Range | Source | Note |
|---|---|---|---|
| `reliability` | [0,1] | Learning: historical hit rate of this evidence type, Brier-scored | Starts at a prior of 0.5 for a new evidence type. Updated weekly, PBO-gated like any other learned parameter |
| `freshness` | [0,1] | `exp(-age / half_life)` where half-life is per node type | An ATR from 3 bars ago is nearly as good. A spread reading from 3 bars ago is worthless. Half-life encodes that |
| `quality` | [0,1] | Page 02's quality score of the underlying data, propagated | **This is what makes page 02's FLAG tier actually do something.** Currently the ADD says consumers are "required to discount" flagged data with no mechanism. Here it is arithmetic |
| `regime_applicability` | [0,1] | Lookup: how predictive is this evidence type in the current regime | Order blocks matter more in trending regimes; mean-reversion signals matter more in ranging ones. Encoded as a matrix, learned, PBO-gated |
| `independence` | (0,1] | `1 / (1 + shared_model_degree)` from `SHARES_MODEL_WITH` edges | Two nodes sharing a GARCH fit each get ~0.5. This is the correction for the double-counting the ADD acknowledges but does not fix |

**Design principle:** every factor is a number a human can inspect and challenge, and every factor traces to either a measurement or a learned parameter with a validation gate. No factor is a magic constant.

---

## 5. Confidence propagation

The graph propagates confidence from evidence to hypotheses. Two hypotheses are always evaluated: `LONG` and `SHORT`. `FLAT` is the residual.

### Method: log-odds accumulation with dependence discounting

```
For hypothesis H:
  prior_logodds(H)                      // from regime base rates, not 0.5
  + SUM over supporting nodes n:
        weight(n) x log_likelihood_ratio(n | H)
  - SUM over contradicting nodes m:
        weight(m) x log_likelihood_ratio(m | not H)
  - dependence_penalty(node_set)         // from the shared-model graph
  = posterior_logodds(H)
```

Log-odds rather than a weighted average because:

1. It composes correctly for independent evidence (log-odds add, probabilities do not).
2. It has a principled home for the dependence correction.
3. Contradiction becomes subtraction rather than a special case.
4. The prior is explicit and comes from measured base rates rather than an implicit 0.5.

**Two-track design:** the graph's propagated posterior is computed deterministically in Python **before** the desks are polled. It is a baseline. The desks then reason and the consensus (R10 §6) is pooled separately. Comparing "what the graph says" to "what the committee concluded" is a first-class metric: a persistent gap in either direction is a calibration finding. If the committee never disagrees with the graph, the LLM layer is adding nothing and should be removed. That is a test the current architecture cannot run, and it is the test that justifies the Committee's existence.

---

## 6. Contradiction handling

Page 08 handles disagreement only at the vote level and resolves deadlock to no-trade. Correct as a default, but it discards information. Contradiction at the evidence level should be classified, because different kinds of contradiction warrant different responses.

| Kind | Example | Detection | Response |
|---|---|---|---|
| **Timeframe contradiction** | H4 bearish, M15 bullish | `CONTRADICTS` edge between nodes of different `timeframe` | **Not a true contradiction.** This is normal and expected. HTF wins per page 06's top-down rule. Encode as a hierarchy, not a conflict |
| **Direct contradiction** | Two structure detectors disagree at the same timeframe | Same type, same timeframe, opposite value | Both weights reduced. If neither is clearly more reliable, both approach zero and the evidence is effectively removed |
| **Model contradiction** | Regime says trending, volatility percentile says compression | Cross-type `CONTRADICTS` from the rule table | **Most informative case.** Flag it explicitly in the evidence presented to desks. A regime/vol disagreement often precedes a genuine regime change and is a signal, not noise |
| **Stale contradiction** | Fresh evidence contradicts stale evidence | One node has `staleness.severity >= warn` | Freshness factor already handles it arithmetically. No special case needed |
| **Data contradiction** | Two vendors disagree on a bar | Cross-source consistency check (R06 W8) | Quality score drops, propagates through the `quality` factor to every downstream node. This is the mechanism that makes the whole quality tier meaningful |

**Explicit rule:** contradiction is surfaced to desks as a first-class field, not hidden by netting. A desk should see "these two pieces of evidence conflict" rather than a pre-netted number, because reasoning about *why* they conflict is exactly the kind of work an LLM is better at than an arithmetic rule.

**Escalation:** if unresolved contradiction weight exceeds a threshold, the cycle terminates `NO_ACTION` with reason `evidence_conflict`, before any desk is polled. This saves the LLM cost and produces a cleaner signal than a deadlock after six calls.

---

## 7. Precedent nodes: the memory correction

Page 08 gives desks "last N committee cycles for this symbol" as memory. Two problems: it is recency-based rather than similarity-based (the last five cycles are usually uninformative), and it is a look-ahead leak in replay (R08 §5).

**Replace with a Precedent index:**

- Every sealed evidence graph is embedded into a fixed-dimension vector using its **structural features**, not LLM embeddings: regime state, vol percentile bucket, structure confluence count and kinds, session, distance to the nearest level, days to the next high-impact event.
- When a new graph is sealed, retrieve the K nearest historical graphs **whose outcomes are known and whose `as_of` precedes the current `as_of`**.
- Each becomes a `Precedent` node: `{similarity, past_cycle_id, stance_taken, outcome_r, sample_size}`.

Three properties this buys:

1. **Point-in-time safe by construction.** The retrieval filter on `as_of` is a hard constraint in the query, so replay cannot see the future.
2. **Similarity beats recency.** "The last time this exact confluence appeared in this regime, it went to +1.8R in 6 bars, 11 prior instances, 64% win rate" is genuinely useful context. "Here is what we decided 15 minutes ago" is not.
3. **Base rates become visible.** The prior in §5 can be conditioned on precedents rather than being a global constant.

**Guard:** precedent nodes carry `sample_size` and desks are instructed and schema-constrained to discount below a minimum (default 20). Small-sample precedent is how a system convinces itself of a pattern that does not exist, and it is the exact failure mode page 12 names as "overfitting to recent regime", now appearing in a new place.

---

## 8. Explainability

The graph makes explanation a rendering problem rather than a generation problem, which eliminates page 09's "explanation drift from decision" failure mode by construction.

### Four explanation views, all from the same sealed graph

| View | Audience | Content |
|---|---|---|
| **One-line** | Dashboard tile | "Long XAUUSD, 0.6% risk. Trending regime plus unmitigated demand OB at 2,412 with liquidity confluence. Vol at the 34th percentile supports continuation." Generated by binding the top-weighted nodes to a template |
| **Decision card** | Operator, at decision time | Top 5 supporting and top 3 contradicting nodes with weights, each desk's stance and conviction, the Red Team's objection, the risk assessment summary, the pooled versus graph-baseline comparison |
| **Full trace** | Post-mortem, audit | Every node, every edge, every desk's full opinion and prompt version, the complete rule-by-rule risk assessment, the lineage back to raw payloads |
| **Counterfactual** | Research | "Which single node, if removed, flips the decision?" Computed by ablation over the graph. This is the most useful research artefact the graph produces and it is impossible without the graph structure |

### The rendering rule

Explanations are **rendered from the graph**, never re-generated by an LLM from the decision. Page 09 states this principle correctly ("the lineage is rendered, not re-summarised") and it is preserved and strengthened here: with citations-as-references (R03 §5), the rendered text is guaranteed to contain the actual evidence values, because those values are substituted from the graph at render time.

---

## 9. Storage and technology

**Recommendation, staged:**

| Phase | Technology | Rationale |
|---|---|---|
| **P0-P1** | In-memory graph per cycle (`networkx`), serialised canonically and stored as a content-addressed blob in MinIO, with node and edge rows also written to Postgres for querying | Page 09's proposal is correct for the volume. A few hundred nodes per cycle, a few hundred cycles per day. A graph database is unjustified |
| **P2** | Add a Postgres recursive-CTE query layer over the node/edge tables | Handles "every decision that cited this order block" without a new datastore. Postgres does graph traversal adequately at this volume |
| **P3 tripwire** | Dedicated graph store (Neo4j / Memgraph / Kùzu) | Promote only if cross-cycle, multi-hop queries become routine and Postgres CTE latency exceeds ~1s. Do not adopt speculatively |

**Non-negotiable regardless of phase:** the canonical serialisation is stable and hashed. Two runs that produce the same graph must produce the same hash, byte for byte. Key ordering, float formatting, and timestamp precision all pinned. Without this the content addressing is decorative and the determinism test in R01 §10 cannot pass.

---

## 10. What this changes in the existing pages

| Page | Change |
|---|---|
| 08 | Desks receive a **graph slice** (their nodes plus every node connected by an edge, with the edge types visible), not a flat engine output. The isolation boundary is preserved: a desk still cannot see another engine's raw output, but it can see that a contradiction exists and what type it is. This is a meaningful strengthening rather than a weakening of the boundary |
| 08 | Desk output is citations to `node_id` (R03 §5), which requires nodes to have stable IDs, which requires the graph |
| 09 | Evidence Graph becomes a real component with a node/edge model, a weight function, and a propagation method, rather than a pipeline stage |
| 09 | "Counterfactual replay" moves from Future Expansion to a graph ablation query, available immediately |
| 02 | The quality score gains a consumer: the `quality` factor in §4. Page 02's FLAG tier currently has no mechanical effect anywhere |
| 12 | Learning gains a target: `reliability` and `regime_applicability` are learned parameters with a validation gate, which is a far more specific improvement loop than "revise desk weights" |

---

## 11. Related

- `R03_Domain_Model_DDD.md` (§5, citations as references; BC5 aggregates)
- `R08_Data_Lineage.md` (S7, S8; node provenance)
- `R10_Committee_Architecture.md` (how desks consume graph slices, pooling)
- `R12_Observability.md` (graph-baseline vs committee-output divergence as an SLI)
- Source: `../09_Decision_Intelligence_Layer.md`
