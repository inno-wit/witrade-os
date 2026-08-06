# 04 — Regime Engine, contract completion

**Delta against:** `../04_Regime_Engine.md` (unmodified)
**Adds:** Owns, Invariants, Interfaces, Degraded Mode, SLO, Security Boundary
**Container:** C09 · **Context:** Quant Research · **Criticality:** Tier 1 · **Group:** Quant
**Highest-value field for this page (R05 §11):** **Degraded Mode.** The page says it returns the last good value with `stale: true`. What consumers must then do is unstated

---

## Owns (exclusive write access)

| Asset | Note |
|---|---|
| `regime_estimates` (Postgres + published to Iceberg via C06) | One row per `(symbol, timeframe, as_of, model_version)` |
| `regime_fit_state` (Postgres) | Last converged parameters per model per symbol. **Survives restart** |
| `regime_model_registry` (Postgres) | Registered plugins and their versions |
| `regime_calibration` (Postgres) | Score-to-probability mappings, versioned |

`regime_fit_state` being durable is a correction rather than an addition. Page 04's recovery strategy is to "return the last successfully converged estimate", which requires that estimate to exist somewhere a restart does not erase. In-process memory does not satisfy the page's own stated behaviour.

The engine does **not** write the Feature Store's Regime category directly. It publishes `evt.regime.classification.published.v1` and C06 materialises it (see `03_Feature_Store.contract.md`).

## Invariants

1. `get_regime(symbol, tf, as_of)` never returns "no answer". It returns an estimate with an explicit `staleness` duration and a `confidence`, or it raises. It never returns a fabricated neutral state.
2. A regime estimate at `as_of` is computed only from features with `event_time <= as_of`. The engine inherits, and must not weaken, the Feature Store's point-in-time guarantee.
3. Dwell time and hysteresis are applied by the Arbiter, not inside any model. A model reports what it sees; the Arbiter decides what the platform is told.
4. `confidence` is a **calibrated** probability, not a raw model posterior. A raw HMM posterior is not a probability of being right (ADR-0028).
5. A shift event fires only after the minimum dwell time has elapsed. A shift that has not persisted is not a shift, it is noise, and page 04 is right that this is per-symbol configurable.
6. Every estimate carries the `model_version`, `calibration_version`, and `fit_as_of` that produced it. A decision citing a regime must be able to name which fit said so.
7. The trivial baseline model is always registered and always evaluated, even when it is not used. Its score is recorded alongside the ensemble's.

Invariant 7 is the one with no counterpart in the source page and the one most likely to be skipped. Page 04 specifies a GARCH → Markov Switching → HMM pipeline. Markov Switching models and HMMs are the same model family, and the page does not justify stacking them. Whether that stack beats a volatility-threshold classifier out of sample is an empirical question, and it is unanswerable unless the baseline is a first-class plugin producing a comparable score on every bar. If the stack does not beat it, that is a finding worth more than the stack.

## Interfaces

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Query | `get_regime(symbol, timeframe, as_of) -> RegimeEstimate` | Yes | 20ms (cached) | service |
| Query | `get_transition_matrix(symbol, timeframe, as_of) -> Matrix` | Yes | 20ms | service |
| Command | `refit(symbol, timeframe, window, run_id)` | No | 5m | service (Scheduler), operator |
| Query | `model_health(symbol) -> [ModelHealth]` | Yes | 50ms | service, operator |
| Adapter | `RegimeModel` protocol | — | — | — |

```python
class RegimeModel(Protocol):
    name: str
    version: str
    def fit(self, window: FeatureWindow, clock: Clock) -> FitResult: ...
    def predict(self, view: FeatureView, as_of: Timestamp) -> RegimeEstimate: ...
    def is_converged(self) -> bool: ...
    def max_staleness(self) -> timedelta: ...
```

Page 04 hardcodes the pipeline into the component, so adding a competing model (a change-point detector, a clustering approach, the baseline) means editing the engine. Behind this protocol they are plugins, and the Arbiter combines them. The identical pattern applies to `VolModel` (page 05) and `StructureDetector` (page 06), which turns `smartmoneyconcepts` from a hard dependency into one implementation.

`RegimeEstimate` carries `{state, probabilities, confidence, staleness, model_version, calibration_version, fit_as_of, converged}`. Note `staleness` is a duration, not a boolean: "12 seconds old" and "four days old" are both `stale: true` in the source page's design and mean entirely different things to a consumer.

## Degraded Mode

This is the field R05 flags as highest-value for pages 04-06, and it is the one the source pages leave to the reader. The behaviour of every consumer while the engine is broken:

| Condition | Engine behaviour | **Consumer behaviour, previously unstated** |
|---|---|---|
| Fit did not converge | Serve the last converged estimate with `staleness` and `converged=false` | Committee Regime Desk **must lower confidence proportionally to staleness**, and abstains beyond `max_staleness`. Risk uses the most conservative regime interpretation, never the last one |
| Staleness beyond `max_staleness` (default 3 bar intervals) | Serve with `staleness` set and `confidence=0` | Regime Desk **abstains**. Quorum arithmetic sees an abstention, not a neutral vote. Page 08's quorum rule then applies |
| Feature Store unavailable | Cannot compute. Serve last known with growing staleness | Same ladder as above. The engine does not invent inputs |
| Whipsaw (state oscillating near the boundary) | Suppress the shift event, serve the incumbent state, set `whipsaw=true` | Committee treats a whipsaw flag as reduced confidence, not as a shift signal |
| Transition matrix below minimum sample size | Fall back to the unconditional matrix, set `matrix_degraded=true` | Any consumer using transition probabilities for forward-looking sizing must widen its interval or decline |
| Engine process down | Nothing served | Regime Desk abstains. **The cycle continues without it if quorum still holds.** A missing desk is not a platform halt |

Two rules make the whole table coherent, and neither is in pages 00-16:

> **Staleness reduces confidence; it never substitutes a default.** A neutral or sideways regime returned because nothing better was available is a fabricated input to a capital decision.

> **An unavailable desk input is an abstention, never a neutral vote.** These are different in the quorum arithmetic, and treating them alike lets a broken engine silently swing a decision.

## SLO

| Dimension | Target |
|---|---|
| Availability, market hours | 99.9% |
| `get_regime` | p50 < 3ms (cached), p95 < 12ms, p99 < 20ms |
| Recompute per bar close per symbol | p99 < 500ms (page 04's budget, retained) |
| Freshness | Zero active symbols with staleness > 3 bar intervals |
| Correctness | Zero estimates served that used data after their `as_of` |
| Model quality | Calibration error (Brier decomposition) reviewed weekly. **Ensemble must beat the baseline out of sample or the ensemble is the finding** |

The last row is the SLO that makes this engine falsifiable. A regime engine that cannot demonstrate an edge over a volatility threshold is a source of confident-sounding noise feeding a capital decision, and the platform should be able to discover that about itself.

## Security Boundary

| | |
|---|---|
| **Zone** | CORE. No inbound internet, no broker credentials, no vendor keys |
| **Callers permitted** | Evidence Graph (C15), Volatility Engine (C10), Feature Materialiser (C06), Data Quality (C03, previous-bar regime only), Operator |
| **Secrets held** | Postgres credential only |
| **Trusts** | Feature Store output including its quality flags and staleness. Trusts nothing external |
| **Privileged actions** | `refit` with a manual window, and publishing a calibration version, are operator actions and audited |
| **Model artefacts** | Registered in MLflow with pinned versions. A model artefact is loaded by version, never by "latest" |

The Data Quality caller is worth naming explicitly because it is the platform's one deliberate near-circular dependency: page 02 reads regime output to set volatility-aware thresholds, and page 04 reads quality-scored features. Page 02 documents the resolution (Quality reads regime about *past* bars, never gates on same-bar classification) so that a later refactor does not "fix" it into a real cycle. The `as_of` argument on `get_regime` is what makes that resolution mechanical rather than remembered.

---

## Related

- Source page, unmodified: `../04_Regime_Engine.md`
- `05_Volatility_Engine.contract.md`, `06_Market_Structure_Engine.contract.md` — same plugin and degradation pattern
- `03_Feature_Store.contract.md` — the point-in-time guarantee inherited here
- `../review/R02_C4_Expansion.md` §4 (L3.1) — the plugin restructure in full
- `../review/R10_Committee_Architecture.md` — calibration and quorum arithmetic
- `../decisions/0028-desk-confidence-is-calibrated-before-use.md` — invariant 4
- `../decisions/0021-deadlock-and-quorum-failure-resolve-to-no-trade.md` — the abstention rule
