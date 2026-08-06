# 03 — Feature Store

**Diagram:** `03_Feature_Store.excalidraw`
**Phase:** 2 — Data Platform (3 of 3)
**C4 Level:** L3 — Component
**Depends on:** `02_Data_Quality_Engine.md`
**Status:** Draft

---

## Purpose

Replace a `features.py` grab-bag with a real feature store: a versioned, queryable, category-organized set of features that every model and every AI Committee desk reads from the same source of truth, instead of each recomputing its own version of "RSI" slightly differently.

## Responsibilities

Compute, version, and serve nine feature categories, keyed by `(symbol, timeframe, timestamp)`, backed by validated data only (PASS/FLAG from page 02).

## Feature Categories

| Category | Examples | Primary Consumer |
|---|---|---|
| Technical | RSI, MACD, EMA, Bollinger Bands, Stochastic, ATR | ML Models (page 07) |
| Regime | Bull/bear/sideways probability, HMM state | Regime Desk (page 08) |
| SMC | BOS, CHoCH, Order Blocks, FVG, liquidity zones | SMC Desk (page 08) |
| Volatility | Realized/forecast vol, vol percentile, expected move | Volatility Desk (page 08) |
| Time | Session (Asia/London/NY), day-of-week, time-to-event | All desks (context) |
| Macro | Rates, DXY, yield curve, risk-on/off score | Macro Desk (page 08) |
| Alternative Data | Options flow, sentiment scores, on-chain (future) | ML Models, Macro Desk |
| Cross Asset | Correlated pair moves, intermarket signals | Risk Desk, Portfolio (page 10) |
| Labels | Forward returns, triple-barrier outcomes | ML/RL training only — never served live |

**Note on Regime/SMC/Volatility features:** these categories are *populated by* pages 04/05/06 respectively — the Feature Store is where their output lands for reuse, not where they're computed. This page defines the storage/access contract; those pages define the computation.

## Inputs

Validated (PASS/FLAG-tagged) bars from the Data Quality Engine (page 02).

## Outputs

A versioned feature API — `get_features(symbol, timeframe, as_of, categories=[...])` — consumed by the Quant Research Platform (pages 04-07) and, transitively, by the AI Committee desks (page 08) via those engines.

## Dependencies

Data Quality Engine (page 02).

## Events Published

- `feature.updated` — per category, per symbol/timeframe, on recompute.
- `feature.backfilled` — historical recompute completed (e.g., after a feature definition change).

## Events Consumed

- `data.quality.scored` (PASS/FLAG only — REJECT never reaches here).
- `regime.updated`, `structure.updated`, `volatility.updated` — from pages 04/05/06, written back into their respective categories.

## Failure Modes

- **Point-in-time leakage** — a feature computed with data that wouldn't have been available at that historical timestamp (classic backtest look-ahead bias). This is the single most dangerous failure mode in the whole platform.
- **Feature definition drift** — someone changes how RSI is computed without versioning, silently invalidating every model trained on the old definition.
- **Stale category** — one category (e.g., Macro) stops updating while others continue, producing internally inconsistent feature vectors.

## Recovery Strategy

- Every feature is stored with an `as_of` timestamp and computed strictly from data with `timestamp <= as_of` — point-in-time correctness is enforced at the query layer, not left to caller discipline. See `backtesting-frameworks` skill for the look-ahead-bias discipline this must satisfy.
- Feature definitions are versioned (`technical.rsi.v2`); changing a definition creates a new version rather than mutating the old one, so existing trained models keep working against the version they were trained on.
- Staleness check on every `get_features()` call — if any requested category's last update exceeds its expected refresh interval, the response includes a staleness flag the caller (ultimately, the AI Committee) is required to factor into confidence.

## Latency Budget

- Live query (`get_features` for current bar): **< 50ms**.
- Historical backfill query (backtest range): best-effort, not latency-sensitive.

## Technology

DuckDB as the query layer (same as page 01's warehouse — the Feature Store is a schema within it, not a separate database), Parquet for versioned feature snapshots. Feature computation itself runs as scheduled/event-triggered Python jobs orchestrated by the Orchestration Layer.

## Future Expansion

- Add a real-time feature cache (Redis) in front of DuckDB once query volume from the AI Committee's per-decision reads justifies it.
- Alternative Data category is a placeholder — options flow and on-chain data sources are not yet wired (see page 00 Future Expansion note).

---

## Related

- Previous: `02_Data_Quality_Engine.md`
- Next: `04_Regime_Engine.md` (Phase 3 begins)
