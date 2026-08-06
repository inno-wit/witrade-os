# 04 — Regime Engine

**Diagram:** `04_Regime_Engine.excalidraw`
**Phase:** 3 — Quantitative Intelligence (1 of 4)
**C4 Level:** L3 — Component
**Depends on:** `03_Feature_Store.md`
**Status:** Draft

---

## Purpose

Answer one question every other engine and every Committee desk needs answered first: **what kind of market are we in right now** — trending, mean-reverting, high/low volatility — and how confident are we in that read. Every downstream model consumes this rather than each guessing independently.

## Responsibilities

Compute a probabilistic regime classification per symbol from price returns, using a GARCH → Markov Switching → HMM pipeline, and expose it via a stable API.

## Pipeline

```
Price Returns
  -> GARCH                     (conditional volatility estimate)
  -> Markov Switching Model    (discrete regime states)
  -> Hidden Markov Model       (latent state inference, smoothed path)
  -> Transition Matrix         (P(regime[t+1] | regime[t]))
  -> Regime Probability        (current-state probability vector)
  -> Regime API
```

## Inputs

Price returns per symbol from the Feature Store (page 03).

## Outputs

`get_regime(symbol, as_of) -> { state, probabilities: {bull, bear, sideways}, confidence, transition_matrix }`, written back into the Feature Store's Regime category and consumed directly by the Regime Desk (page 08).

## Dependencies

Feature Store (page 03).

## Events Published

- `regime.updated` — per symbol, on each recompute (bar-close triggered).
- `regime.shift.detected` — when the most-probable state changes (higher-priority event; downstream consumers may want to react faster to a shift than to a routine update).

## Events Consumed

- `feature.updated` (Technical category — returns).

## Failure Modes

- **Non-convergence** — GARCH/HMM fitting fails to converge, especially right after a genuine regime change when the data itself is non-stationary.
- **Regime whipsaw** — probability estimate oscillates near a 50/50 boundary between two states, producing unstable classifications bar-to-bar.
- **Stale transition matrix** — matrix fit on a rolling window that no longer reflects current dynamics after an extended regime change.

## Recovery Strategy

- On non-convergence, the engine returns the last successfully converged estimate with an explicit `stale: true` flag rather than a fitting error propagating downstream — the Regime API never returns "no answer."
- Whipsaw is dampened with a minimum dwell time (a regime call must persist N bars before being reported as a shift) — configurable per symbol, since some instruments (XAUUSD 15m) genuinely regime-shift faster than others.
- Transition matrix refit runs on a rolling window with a minimum sample size guard; below that guard, the engine falls back to the unconditional (long-run average) transition matrix.

## Latency Budget

Recomputed on every bar close, budget **< 500ms per symbol** (per page 00's Quant Research Platform latency budget) — this is on the path the AI Committee waits on, not an offline batch job.

## Technology

Python: `arch` (GARCH), `statsmodels` (Markov Switching), `hmmlearn` (HMM). Output registered in MLflow for reproducibility of the fitted parameters, not just the model code.

## Future Expansion

- Multi-timeframe regime (currently one regime call per symbol; HTF/LTF regime alignment is a Committee-level concern today via separate calls — could become a native multi-timeframe output here).
- Regime-conditional feature weighting fed directly into ML Models (page 07) rather than only informing the Committee.

---

## Related

- Previous: `03_Feature_Store.md`
- Next: `05_Volatility_Engine.md`
