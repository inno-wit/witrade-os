# 05 — Volatility Engine

**Diagram:** `05_Volatility_Engine.excalidraw`
**Phase:** 3 — Quantitative Intelligence (2 of 4)
**C4 Level:** L3 — Component
**Depends on:** `04_Regime_Engine.md`
**Status:** Draft

---

## Purpose

Give every downstream consumer — position sizing, the Volatility Desk, the Data Quality Engine's thresholds — one consistent, multi-lens view of "how much is this instrument moving right now and how much should we expect it to move."

## Responsibilities

Compute six volatility metrics per symbol, combining a backward-looking realized measure, a forward-looking forecast, and tail-risk estimation, conditioned on the current regime.

## Metrics Produced

| Metric | Definition |
|---|---|
| ATR | Average True Range — classic bar-range volatility |
| Forecast Vol | Forward-looking estimate, GARCH-derived (shares the fitted GARCH model from page 04) |
| Realized Vol | Backward-looking, rolling-window realized volatility |
| Expected Move | Options-style expected range for an N-bar horizon |
| Volatility Percentile | Current vol vs. trailing 1-year distribution |
| Tail Risk | Fat-tail / extreme-move probability (Extreme Value Theory-based) |

## Inputs

Price/returns from the Feature Store (page 03), regime state from the Regime Engine (page 04) — forecast vol and tail risk are regime-conditional, not computed in isolation.

## Outputs

`get_volatility(symbol, as_of) -> { atr, forecast, realized, expected_move, percentile, tail_risk }`, written to the Feature Store's Volatility category, consumed by the Volatility Desk (page 08) and, critically, by Risk Management (page 10) for position sizing.

## Dependencies

Feature Store (page 03), Regime Engine (page 04) — this is a genuine dependency, not just a suggestion: forecast vol is meaningfully different in a trending vs. sideways regime, and this engine is where that conditioning happens rather than leaving each consumer to redo it.

## Events Published

- `volatility.updated` — per symbol, per recompute.
- `volatility.regime_shift` — expected-move recalibration triggered by a regime shift event from page 04.

## Events Consumed

- `feature.updated` (returns), `regime.updated` (page 04).

## Failure Modes

- **Realized/forecast divergence** — realized vol spikes but the GARCH forecast hasn't caught up yet (lag inherent to any conditional vol model), producing a temporarily misleading picture.
- **Tail risk instability** — EVT estimation is sensitive to sample size and window choice; short windows produce noisy tail estimates.
- **Percentile distortion** — the trailing 1-year window itself contains a regime change, making "percentile" comparisons apples-to-oranges across that boundary.

## Recovery Strategy

- Both realized and forecast vol are always returned together, never just one — consumers are expected to reconcile the two rather than the engine picking a single "truth."
- Tail risk carries its own confidence interval, not a point estimate — the Committee's Risk Desk is required to treat a wide-CI tail estimate as weaker evidence.
- Percentile computation flags whether the trailing window spans a known regime shift (per page 04's `regime.shift.detected` history) so consumers can discount if needed.

## Latency Budget

Recomputed on every bar close alongside the Regime Engine, budget **< 500ms per symbol** (shared Quant Research Platform budget from page 00).

## Technology

Python: `arch` (shared GARCH fit with page 04), custom EVT implementation (`scipy.stats.genextreme` or equivalent) for tail risk. Same MLflow registration pattern as page 04 for reproducibility.

## Future Expansion

- Implied volatility surface once an options data source is added (Alternative Data category, page 03) — would sit alongside Expected Move as a market-implied cross-check on the model-implied version.
- Cross-asset volatility spillover (e.g., DXY vol affecting XAUUSD forecast) — currently each symbol's volatility is computed independently.

---

## Related

- Previous: `04_Regime_Engine.md`
- Next: `06_Market_Structure_Engine.md`
