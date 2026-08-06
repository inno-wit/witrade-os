# 01 — Data Ingestion

**Diagram:** `01_Data_Ingestion.excalidraw`
**Phase:** 2 — Data Platform (1 of 3)
**C4 Level:** L2 — Container
**Depends on:** `00_Master_Architecture.md`
**Status:** Draft

---

## Purpose

Pull raw data from five heterogeneous external sources and land it in a validated, queryable warehouse (DuckDB over Parquet) that every downstream consumer — Quant Research, the AI Committee, the dashboard — reads from instead of re-implementing its own fetch logic.

## Responsibilities

- Maintain a live connection or scheduled pull per source.
- Normalize disparate formats (MT5 tick stream, Databento binary, Polygon JSON, News text, calendar events) into one internal bar/tick schema before they touch storage.
- Never mutate raw data after it's written — corrections happen via a new validated version, not an in-place edit (audit trail requirement for a quant desk).
- Hand off to the Data Quality Engine (page 02) before anything is marked usable.

## Inputs

| Source | Protocol | Cadence | Data |
|---|---|---|---|
| MT5 | Push (terminal API) | Tick-level, real-time | Price ticks, account/position state |
| Databento | Pull (REST/WS) | Configurable, tick or bar | Institutional tick/bar data |
| Polygon.io | Pull (REST) | On-demand / scheduled | OHLCV bars, fundamentals, earnings calendar |
| News provider | Pull (poll) | Every 5 min | Headlines, article text |
| Economic calendar | Pull (scheduled sync) | Daily | Macro event schedule (NFP, CPI, FOMC, etc.) |

## Outputs

Validated, resampled OHLCV bars (1m/5m/15m/1H/4H/1D) + raw tick archive, queryable via DuckDB, partitioned by symbol/date in Parquet. Feeds directly into the Feature Store (page 03).

## Dependencies

Orchestration Layer (Scheduler triggers pulls; Event Bus carries `data.bar.received` onward).

## Events Published

- `data.tick.received` — per-tick, MT5 only (highest volume — internal use, not broadcast platform-wide).
- `data.bar.received` — per-bar, all sources, post-resampling.
- `data.source.degraded` — circuit breaker opened for a source.

## Events Consumed

- `job.scheduled` — pull-triggers from the Orchestration Scheduler.

## Failure Modes

- **Source outage** — broker disconnect, API rate limit, provider downtime.
- **Bad ticks** — zero/negative prices, impossible spreads, out-of-sequence timestamps.
- **DST transitions** — off-by-one-hour bar misalignment twice a year.
- **Duplicate delivery** — retried pulls or WS reconnects re-sending already-ingested data.
- **Schema drift** — provider changes a field name/type without notice.

## Recovery Strategy

Per-source circuit breaker (see diagram, right panel): 3 consecutive failures trips OPEN, pipeline continues with remaining sources and flags a gap rather than blocking the whole platform. Half-open retry every 60s. Databento and Polygon can fall back for each other on OHLCV (not tick-level). MT5 has no fallback — broker feed loss halts live execution inputs for the affected account only, not the whole platform (other accounts/paper trading continue).

Deduplication is idempotent on `(source, symbol, timestamp)` — safe to replay a source's feed after an outage without creating duplicate bars.

## Latency Budget

- MT5 tick → raw storage: **< 50ms** (this feeds the live execution path).
- Polygon/Databento bar → DuckDB queryable: **< 2s** for real-time symbols.
- News/calendar: not latency-sensitive, best-effort within the poll interval.

## Technology

- Ingestion workers: Python (asyncio for WS sources, scheduled jobs for REST pull sources).
- Storage: Parquet (cold, partitioned) + DuckDB (query layer).
- MT5 bridge: Windows VPS process (per existing TradeHub SMC-service pattern — MT5's Python library is Windows-only).

## Future Expansion

- Add options flow / on-chain data as new source boxes — the Cleaning → Validation → Resampling → Parquet → DuckDB pipeline stages don't change, only the source adapter.
- Multi-broker MT5 (currently single-account bridge pattern from TradeHub; needs multiplexing for multi-user/multi-account).

---

## Related

- Previous: `00_Master_Architecture.md`
- Next: `02_Data_Quality_Engine.md`
