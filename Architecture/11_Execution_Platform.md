# 11 — Execution Platform

**Diagram:** `11_Execution_Platform.excalidraw`
**Phase:** 7 — Execution Platform
**C4 Level:** L3 — Component
**Depends on:** `10_Risk_Portfolio_Platform.md`
**Status:** Draft

---

## Purpose

Turn an Approved Trade into a real broker order, and — just as important — verify the fill actually matches what was approved before calling it done. Execution is where a sound decision can still be undermined by slippage, partial fills, or connectivity issues; this layer's job is to catch that, not assume it away.

## Responsibilities

Route the approved order through a broker-agnostic adapter, verify pre-send conditions still hold, analyze the resulting fill for slippage, produce an idempotent trade confirmation, and write a permanent Journal entry.

## Pipeline

```
Approved Trade (page 10)
  -> Broker Adapter        (broker-agnostic interface, MT5 first)
  -> MT5                     (order send via Windows VPS bridge)
  -> Order Verification        (pre-send: price still valid, size within limits)
  -> Fill / Slippage Analysis    (actual vs. expected, feeds Risk Kill Switch)
  -> Trade Confirmation            (idempotent, reconciled against broker truth)
  -> Journal                         (permanent record)
```

## Inputs

Approved Trade from Risk Management (page 10): `{ direction, size, entry, stopLoss, targets }`.

## Outputs

Trade Confirmation → Journal (permanent audit record), plus `execution.slippage.recorded` fed back to Risk Management's Kill Switch (page 10) and RL simulator calibration (page 07).

## Dependencies

Risk Management (page 10) — this layer never originates an order on its own; it only ever acts on an Approved Trade.

## Events Published

- `order.sent` — order transmitted to broker.
- `order.filled` — confirmed fill received.
- `order.rejected` — broker-side rejection (distinct from a Risk Management rejection — this is "the broker said no," not "we decided not to").
- `execution.slippage.recorded` — every fill, whether within tolerance or not.

## Events Consumed

`risk.approved` (from page 10).

## Failure Modes

- **Broker connectivity loss mid-order** — the send times out with an unknown outcome (did it fill or not?).
- **Partial fills** — the broker fills less than the requested size.
- **Slippage beyond tolerance** — fill price diverges meaningfully from the approved entry.
- **Duplicate submission on retry** — a naive retry after a timeout re-sends an order that actually did go through.

## Recovery Strategy

- **Idempotent order IDs**: every order carries a client-generated ID; the Broker Adapter checks order status by that ID before any retry, so a retried send after a timeout never double-submits — see the diagram's side panel.
- Partial fills are an explicit, first-class state (not an error path): remaining unfilled size is either re-queued or cancelled per the original trade's time-in-force, decided deterministically, not left to ad hoc handling.
- Slippage beyond tolerance **auto-flags for operator review** — it does not auto-cancel or auto-retry, because both of those actions carry their own risk (an auto-retry into a fast market can compound the problem). It does feed `execution.slippage.recorded` to Risk Management, where a *pattern* of bad slippage (not a single incident) can trip the Kill Switch.
- Trade Confirmation is reconciled against broker truth (queried state), never trusted purely from the initial order-send response — this is the same "broker truth over internal ledger" principle Risk Management applies in page 10.

## Latency Budget

**< 300ms** order-send to broker acknowledgment (MT5-dependent — this is a hard external constraint, not something this layer controls beyond choosing an efficient bridge implementation).

## Technology

MT5 Python bridge running on a Windows VPS — this reuses the existing TradeHub `smc-service`-style bridge pattern (MT5's Python library only works on Windows, communicating with the running MT5 terminal process). The Broker Adapter is built as a broker-agnostic interface from day one even though MT5 is the only implementation initially, per the `execution-safety` skill's adapter-stub pattern (wraps `alpaca-py`/`ib_async`/`ccxt`-style adapters, testable with no broker keys).

## Future Expansion

- Multi-broker smart order routing once a second broker adapter exists.
- Extend the `execution-safety` skill's human-confirmation gate (paper-by-default, explicit typed confirmation to go live) as the standard pattern for any new broker integration added here.

---

## Related

- Previous: `10_Risk_Portfolio_Platform.md`
- Next: `12_Continuous_Learning.md`
