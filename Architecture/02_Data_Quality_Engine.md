# 02 — Data Quality Engine

**Diagram:** `02_Data_Quality_Engine.excalidraw`
**Phase:** 2 — Data Platform (2 of 3)
**C4 Level:** L3 — Component
**Depends on:** `01_Data_Ingestion.md`
**Status:** Draft

---

## Purpose

Every dataset that reaches the Feature Store must have earned trust — this engine is the only place that trust gets decided. Nothing downstream re-checks data quality; they trust the score attached here.

## Responsibilities

Run seven independent detectors against every incoming dataset in parallel, combine their outputs into a single composite quality score, and route the dataset to Pass / Flag / Reject based on that score.

## Detectors

| Detector | Detects |
|---|---|
| Missing Candles | Gap in the expected bar sequence for the symbol's trading calendar |
| Duplicates | Same `(symbol, timestamp)` delivered twice |
| DST Issues | Off-by-one-hour bar misalignment at daylight-saving transitions |
| Broker Outages | Feed silence beyond the expected heartbeat interval |
| Spread Spikes | Bid/ask spread exceeding N standard deviations from rolling norm |
| Flash Crashes | Single-bar move beyond threshold that reverts within K bars |
| Bad Ticks | Zero/negative price, impossible OHLC ordering (e.g., low > high) |

Each detector returns a `(triggered: bool, severity: float, detail: str)` tuple — detectors don't reject on their own, they contribute evidence to the Quality Scorer.

## Inputs

Cleaned bars from Data Ingestion (page 01), keyed by `(source, symbol, timeframe, timestamp)`.

## Outputs

Every dataset gets a **quality score (0.0-1.0)** and is routed:

- **PASS (>= 0.8)** — forwarded to Feature Store with no annotation.
- **FLAG (0.5-0.8)** — forwarded to Feature Store, tagged; downstream consumers (e.g., the AI Committee) are required to discount flagged data in their confidence, not treat it as equal to clean data.
- **REJECT (< 0.5)** — quarantined, never reaches the Feature Store, triggers an alert.

## Dependencies

Data Ingestion (page 01) — this engine sits directly in that pipeline's Validation stage.

## Events Published

- `data.quality.scored` — every dataset, with score + detector breakdown.
- `data.quality.rejected` — quarantine events, routed to Monitoring for alerting.

## Events Consumed

- `data.bar.received` from Data Ingestion.

## Failure Modes

- **False positive storm** — a legitimate but unusual market event (real flash crash, real broker maintenance window) trips detectors and quarantines good data.
- **Threshold drift** — static thresholds (e.g., "spread > 3 std dev") become miscalibrated as volatility regime shifts, causing chronic false flags in high-vol regimes.
- **Detector blind spot** — a new failure mode not covered by the seven detectors above passes through undetected.

## Recovery Strategy

- Quarantined data is never silently discarded — it's held in a quarantine table for manual review, so a false-positive storm during a real market event is recoverable (operator can force-release after review).
- Spread/flash-crash thresholds are regime-aware: they read the current volatility regime from page 04 (Regime Engine) rather than using a single static threshold — this is a deliberate cross-dependency, documented so it doesn't get "fixed" into a circular one (Quality Engine reads Regime output about *past* data, never gates on same-bar regime classification).
- Weekly Continuous Learning review (page 12) includes a false-positive/false-negative audit of quarantine decisions.

## Latency Budget

- Detectors run in parallel per dataset: **< 100ms** combined (this sits on the real-time ingestion path for MT5 tick data).
- Scorer aggregation: **< 10ms**.

## Technology

Python, vectorized with pandas/numpy for batch detector runs (historical backfill) and a lightweight per-tick path for the live MT5 feed. Quarantine table in Postgres (durable, queryable for the weekly audit).

## Future Expansion

- Additional detectors (e.g., cross-source consistency check — does Databento agree with Polygon within tolerance) plug in as new boxes without changing the Scorer or routing logic.
- Move static severity weights in the Quality Scorer to a learned model once enough labeled quarantine-review data exists (a natural Continuous Learning output).

---

## Related

- Previous: `01_Data_Ingestion.md`
- Next: `03_Feature_Store.md`
