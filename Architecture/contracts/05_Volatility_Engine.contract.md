# 05 — Volatility Engine, contract completion

**Delta against:** `../05_Volatility_Engine.md` (unmodified)
**Adds:** Owns, Invariants, Interfaces, Degraded Mode, SLO, Security Boundary
**Container:** C10 · **Context:** Quant Research · **Criticality:** Tier 1, **on the sizing path** · **Group:** Quant
**Highest-value field for this page (R05 §11):** **Degraded Mode.** This engine feeds position sizing, so what a consumer does with a stale forecast is a capital question, not a display question

---

## Owns (exclusive write access)

| Asset | Note |
|---|---|
| `volatility_estimates` (Postgres + published to Iceberg via C06) | One row per `(symbol, timeframe, as_of, model_version)` |
| `vol_fit_state` (Postgres) | Last converged GARCH parameters. Durable across restart |
| `evt_parameters` (Postgres) | Tail-risk fit state with its own sample-size record |
| `vol_percentile_windows` (Postgres) | Trailing distributions, with regime-shift markers |

**The shared GARCH fit is a seam that needs naming.** Pages 04 and 05 both say they use the same fitted GARCH model. Two engines sharing a fit means one of them owns it. Resolution: the Volatility Engine owns `vol_fit_state`, the Regime Engine reads it through `get_conditional_volatility(symbol, as_of)`, and neither writes the other's tables. Left unresolved, this becomes two processes fitting the same model on different schedules and disagreeing about the volatility of the same bar.

## Invariants

1. Realized and forecast volatility are **always returned together**. Neither is servable alone. Page 05 states this as an expectation on consumers; here the API makes it impossible to receive one without the other.
2. Tail risk is returned as an interval, never a point estimate. A tail estimate whose confidence interval is wider than a configured bound carries `tail_unusable=true`.
3. Every estimate carries `staleness`, `model_version`, `fit_as_of`, `sample_size`, and `regime_conditioned_on`.
4. Percentile results declare whether the trailing window spans a known regime shift. A percentile across a regime boundary is a comparison between two different distributions and must be visibly marked as such.
5. All volatility values are `Decimal`. They multiply into position size, and float rounding in a sizing chain is a real, silent loss.
6. Point-in-time: computed only from features with `event_time <= as_of`, and conditioned on the regime as of the **previous** bar, never the current one.
7. **No consumer receives a volatility estimate without a staleness duration.** There is no API shape that returns a bare number.

Invariant 7 is deliberately blunt. This is the engine whose output multiplies into position size. A stale forecast that looks like a fresh one produces a position sized for a market that no longer exists, and it does so without any error appearing anywhere.

## Interfaces

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Query | `get_volatility(symbol, timeframe, as_of) -> VolEstimate` | Yes | 20ms | service |
| Query | `get_conditional_volatility(symbol, as_of) -> Decimal` | Yes | 10ms | service (Regime Engine) |
| Query | `get_expected_move(symbol, horizon_bars, as_of) -> Interval` | Yes | 20ms | service |
| Command | `refit(symbol, window, run_id)` | No | 5m | service (Scheduler), operator |
| Adapter | `VolModel` protocol | — | — | — |

`VolEstimate` carries `{atr, forecast, realized, expected_move, percentile, tail_risk, tail_ci, staleness, sample_size, model_version, fit_as_of, regime_conditioned_on, flags}`.

`VolModel` follows the same plugin protocol as `RegimeModel` (see `04_Regime_Engine.contract.md`), with a `VolArbiter` combining outputs. The same requirement applies: **a trivial baseline (rolling realized volatility) is always registered and always scored**, so the question of whether GARCH plus EVT beats a rolling window out of sample is answerable rather than assumed.

## Degraded Mode

| Condition | Engine behaviour | **Consumer behaviour, previously unstated** |
|---|---|---|
| GARCH did not converge | Serve last converged with `staleness`, `converged=false` | **Risk sizes on realized volatility only, with the conservative multiplier.** Never on a stale forecast, never on a default |
| Realized and forecast diverge beyond tolerance | Serve both, set `divergent=true` | Risk uses **the higher of the two**. The asymmetry is deliberate: overestimating volatility costs opportunity, underestimating it costs capital |
| Staleness beyond `max_staleness` (default 3 bar intervals) | Serve with `confidence=0` | Volatility Desk abstains. **Risk sizes at the platform minimum, or declines the entry if a minimum-size position is below the instrument's lot step** |
| Tail CI wider than bound | Serve with `tail_unusable=true` | Risk Desk treats tail evidence as absent, not as benign. Absent tail risk is not low tail risk |
| Percentile window spans a regime shift | Serve with `percentile_cross_regime=true` | Consumers may use it for display, **never for sizing** |
| Engine process down | Nothing served | Volatility Desk abstains. **Risk Engine rejects new entries**, because unsized is not the same as sized conservatively. Exits proceed normally |

The last row is the sharpest difference between this engine and pages 04 and 06. A missing regime read degrades a committee opinion. A missing volatility read means no defensible position size exists, and the correct behaviour is to decline the entry rather than fall back to a fixed lot. A fixed-lot fallback is the single most likely way this platform takes a position ten times larger than intended.

Exits are never blocked by any of this (ADR-0019). An exit sizes to the existing position, which is known from the Ledger and does not require a volatility forecast.

## SLO

| Dimension | Target |
|---|---|
| Availability, market hours | 99.95% (higher than pages 04 and 06: this one is on the sizing path) |
| `get_volatility` | p50 < 3ms, p95 < 12ms, p99 < 20ms |
| Recompute per bar close per symbol | p99 < 500ms |
| Freshness | Zero active symbols with staleness > 3 bar intervals during market hours |
| Correctness | Zero estimates served without a staleness duration. Zero float-typed values reaching the sizer |
| Model quality | Forecast calibration reviewed weekly: realized vol should fall inside the forecast interval at the stated rate. **Systematic underestimation is a P1, not a research note** |

Systematic underestimation is called out because its consequence is directional. A forecast that runs 20% low produces positions 25% too large, permanently, and it looks like nothing at all until a volatile week.

## Security Boundary

| | |
|---|---|
| **Zone** | CORE. No inbound internet, no broker credentials, no vendor keys |
| **Callers permitted** | Risk Engine (C21, sizing), Evidence Graph (C15), Regime Engine (C09, conditional vol only), Data Quality (C03, threshold conditioning), Feature Materialiser (C06) |
| **Secrets held** | Postgres credential only |
| **Trusts** | Feature Store output with its flags. Regime output as of the previous bar |
| **Privileged actions** | `refit` with a manual window is operator-only and audited, because a refit over a hand-picked window is a way to change every future position size without changing any limit |

The Risk Engine caller is the one that sets this service's criticality. Every other consumer of this data forms an opinion with it; the Risk Engine multiplies by it.

---

## Related

- Source page, unmodified: `../05_Volatility_Engine.md`
- `04_Regime_Engine.contract.md` — the shared GARCH fit seam, resolved above
- `10_Risk_Portfolio_Platform.contract.md` — the consumer whose behaviour the degradation table specifies
- `../review/R11_Risk_Architecture.md` — sizing chain and the conservative-multiplier rule
- `../decisions/0020-fractional-kelly-as-platform-default.md` — what this output feeds
- `../decisions/0019-exits-never-blocked-by-entry-rules.md` — why exits ignore this table
