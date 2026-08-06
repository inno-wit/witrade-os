# 10 — Risk & Portfolio Management

**Diagram:** `10_Risk_Portfolio_Platform.excalidraw`
**Phase:** 6 — Risk Platform
**C4 Level:** L3 — Component
**Depends on:** `09_Decision_Intelligence_Layer.md`
**Status:** Draft

---

## Purpose

The layer with veto power. No trade reaches Execution without passing here, and — critically — this layer cannot be reasoned around by the AI Committee. Every check in this pipeline is deterministic, non-negotiable, and runs regardless of how confident the Committee's recommendation was.

## Responsibilities

Evaluate every Trade Recommendation against portfolio-level risk state and hard limits, size the position, and either produce an Approved Trade or a logged rejection.

## Pipeline

```
Trade Recommendation (page 09)
  -> Portfolio Risk       (current aggregate risk vs. limits)
  -> Exposure               (per-symbol & aggregate exposure caps)
  -> Position Sizing         (vol-adjusted base size)
  -> Correlation               (cross-position correlation check)
  -> Kelly                       (fractional Kelly overlay — half/quarter Kelly default)
  -> Drawdown Guard                (reduces/blocks new size as realized drawdown deepens)
  -> Kill Switch                     (hard synchronous stop)
  -> Approved Trade  |  Rejected (logged with reason)
```

## Inputs

Trade Recommendation from Decision Intelligence (page 09): `{ direction, size_hint, confidence, reasoning_trace }`.

## Outputs

- **Approved Trade** — passed to Execution (page 11).
- **Rejected** — logged with the specific stage and reason it failed; never silently dropped. A rejection is as important an audit artifact as an approval.

## Dependencies

Decision Intelligence Layer (page 09). Reads live portfolio/exposure state that the Portfolio Impact stage (page 09) also reads — both must consult the same live state source (see page 09's Recovery Strategy note on this).

## Events Published

- `risk.approved` — trade cleared all checks.
- `risk.rejected` — trade blocked, with `{ stage, reason }`.
- `risk.killswitch.triggered` — kill switch activated (highest-priority alert; Monitoring pages this immediately).
- `risk.killswitch.cleared` — manual operator action to resume.

## Events Consumed

`committee.recommendation` (from page 08, forwarded via page 09's Decision output).

## Failure Modes

- **Stale portfolio state** — approving a trade against exposure/correlation numbers that don't reflect very recent fills (race condition between Execution confirming a fill and Risk reading state for the next decision).
- **Kill switch propagation lag** — an in-flight order sends after the kill switch trips because the switch was implemented as an async event rather than a synchronous gate.
- **Kelly mis-sizing under regime change** — Kelly fraction calculated from a return distribution that no longer matches current regime (page 04), producing an overconfident size right as conditions shift.
- **Correlation blind spot** — two positions that are structurally correlated (e.g., XAUUSD and a gold-miner-adjacent instrument) but not flagged because the correlation model doesn't cover that pair.

## Recovery Strategy

- Portfolio state is reconciled against **broker truth** (queried from the Execution layer / MT5, not just the internal ledger) before every approval — internal state can drift from reality after partial fills or manual interventions; broker truth is the tiebreaker.
- **Kill Switch is implemented as a synchronous, in-process gate in the Execution path**, not a pub/sub subscriber — see the diagram's side panel. This is a deliberate architectural decision: an async kill switch has an inherent propagation window during which a bad order can still slip through. The switch is checked as the literal last step before an order leaves this layer, in the same function call, not "eventually" by a separate service.
- Kill switch trips on: max daily loss breached, max drawdown breached, anomalous fill/slippage pattern (fed back from page 11's slippage analysis), manual operator trigger, or a News Guard blackout window (see `news-guard` skill — NFP/FOMC/CPI proximity blocks new trades regardless of Committee confidence).
- Kelly sizing defaults to **half or quarter Kelly**, never full Kelly — see `capital-allocator` skill. This is a standing platform default, not a per-trade tunable the Committee can override.
- Kill switch tripping blocks **all new** Approved Trades platform-wide until manually cleared. It does **not** auto-close existing positions — that remains a distinct, explicit operator action, because auto-liquidating into a bad market can itself be the worse outcome.

## Latency Budget

**< 100ms per check** (per page 00's Risk Management latency budget) — this sits on the hot path between recommendation and execution, unlike the Committee's ~10s debate cycle upstream of it.

## Technology

Python, Redis for live portfolio state cache (low-latency reads), Postgres for the durable risk ledger and rejection log. Kill switch state itself lives in Redis with a synchronous read on every order path — no caching layer between the check and the read.

## Future Expansion

- Portfolio-level Kelly optimization across correlated strategies, not just correlated positions within one strategy — see `capital-allocator` skill's cross-strategy allocation framework.
- Pre-trade risk simulation (Monte Carlo impact of the new position on portfolio VaR) before finalizing size, rather than the current sequential-check pipeline.

---

## Related

- Previous: `09_Decision_Intelligence_Layer.md`
- Next: `11_Execution_Platform.md`
