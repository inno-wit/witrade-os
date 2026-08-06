# 06 — Market Structure Engine (SMC)

**Diagram:** `06_Market_Structure_Engine.excalidraw`
**Phase:** 3 — Quantitative Intelligence (3 of 4)
**C4 Level:** L3 — Component
**Depends on:** `05_Volatility_Engine.md`
**Status:** Draft

---

## Purpose

Compute Smart Money Concepts structure deterministically — swings, breaks of structure, order blocks, fair value gaps, liquidity, mitigation — so the AI Committee's SMC Desk (page 08) has real structural evidence to reason over instead of eyeballing a chart.

This is a direct architectural evolution of TradeHub's existing `smc-analyzer` background job: same core detection primitives (`swing_highs_lows`, `bos_choch`, `fvg`, `liquidity`, `ob`), now exposed as a first-class Quant Research engine rather than a single cron job feeding one setups table.

## Responsibilities

Run the SMC detection pipeline per symbol per timeframe, compute confluence-based structure confidence, and expose results via a stable API.

## Pipeline

```
OHLCV Bars (multi-timeframe: 5m/15m/1H/4H/D)
  -> Swing Detection        (swing_highs_lows -- local pivots)
  -> BOS / CHoCH            (Break of Structure / Change of Character)
  -> Liquidity               (unswept swing-high/low clusters)
  -> Order Blocks (OB)       (last opposing candle before displacement)
  -> Fair Value Gaps (FVG)   (3-candle imbalance, join_consecutive)
  -> Mitigation               (has price returned to fill OB/FVG?)
  -> Structure Confidence     (0-10 composite score)
  -> Structure API
```

## Confluence Rule

Structure Confidence rises when **>= 2** of the following align within 0.5% of price:

1. Unmitigated FVG
2. BOS/CHoCH confirmation
3. Unswept liquidity
4. Order block
5. Grid level (e.g., $10/$40 thin/thick grid for XAUUSD — ported from the existing Active Range Grid Pine indicator math)

**Top-down bias rule**: never trade against Daily + 4H combined bias. This engine reports per-timeframe structure independently; enforcing the top-down alignment rule is the SMC Desk's job in the Committee (page 08), not this engine's — this engine reports facts, the Committee applies the rule.

## Inputs

Multi-timeframe OHLCV bars from the Feature Store (page 03).

## Outputs

`get_structure(symbol, timeframe, as_of) -> { bos, choch, order_blocks, fvgs, liquidity, mitigation_status, confidence }`, written to the Feature Store's SMC category, consumed by the SMC Desk (page 08).

## Dependencies

Feature Store (page 03). Independent of Regime/Volatility engines (pages 04/05) at computation time, though the Committee combines all three.

## Events Published

- `structure.updated` — per symbol/timeframe, on bar close.
- `structure.confluence.detected` — when confidence crosses a configurable threshold (this is the trigger the existing TradeHub `smc-analyzer` used to gate DeepSeek calls — same pattern reused here to gate a Committee cycle).

## Events Consumed

- `feature.updated` (OHLCV bars, all tracked timeframes).

## Failure Modes

- **Swing detection noise** — too-sensitive swing length parameter produces excessive false BOS/CHoCH signals in choppy conditions.
- **Stale mitigation status** — an OB/FVG marked unmitigated when price actually filled it intrabar on a timeframe finer than the one being analyzed.
- **Grid math drift** — grid level parameters (thin/thick step, shift) are symbol-specific and hardcoded; a wrong constant silently misaligns confluence detection for that symbol.

## Recovery Strategy

- Swing length is regime-aware (reads page 04 regime state) rather than a single global constant — trending regimes use a longer swing length than choppy/sideways ones, matching what the current TradeHub implementation already does per-symbol.
- Mitigation status is recomputed from the finest available timeframe's data even when reporting structure at a coarser timeframe, avoiding the intrabar-fill blind spot.
- Grid parameters are stored as versioned per-symbol config (not inline constants), reviewed whenever a new instrument is onboarded.

## Latency Budget

**< 500ms per symbol per timeframe** (shared Quant Research Platform budget). Five-timeframe top-down analysis for one symbol should complete in **< 2s** total — this is the same batch job cadence the current TradeHub `smc-analyzer` runs (every 15 minutes), now decomposed into a reusable engine rather than one monolithic job.

## Technology

Python, `smartmoneyconcepts` (pandas/numpy-based) — same library already in production use in TradeHub's `smc-service`. Runs as its own engine process rather than being embedded in the MT5 bridge microservice, so it can operate over any OHLCV source (not just live MT5-connected accounts).

## Future Expansion

- Extend grid math beyond XAUUSD/US30 to additional instruments as they're onboarded.
- Session-aware structure weighting (London/NY overlap structure weighted higher) — currently `smc.sessions()` is computed but not yet fed into the confidence score.

---

## Related

- Previous: `05_Volatility_Engine.md`
- Next: `07_ML_RL_Model_Layer.md`
