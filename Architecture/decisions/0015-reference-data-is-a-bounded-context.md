# ADR-0015: Reference data is a separate bounded context, not configuration

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** ddd, correctness, risk

---

## Context

Page 10 specifies volatility-adjusted position sizing, fractional Kelly, and exposure limits. Every one of those computations requires: **contract size, tick size, tick value, minimum lot, lot step, margin requirement, and the account currency conversion.**

**None of these appear anywhere in the ADD.**

Page 01 names DST transitions as a failure mode and page 02 has a DST detector, but **no component owns the trading calendar** that both depend on. Page 06 stores "grid parameters as versioned per-symbol config" without saying where that config lives or who versions it.

The default resolution, absent a decision, is a YAML file. That is the failure this ADR prevents. Instrument specifications are not configuration:

- They **change without warning**, decided by a third party (the broker), and the platform is not notified.
- They are **inputs to a financial calculation**, so a wrong value produces a wrong position size rather than a wrong behaviour.
- They must be **point-in-time resolvable**, because a backtest of a trade from six months ago must use the contract size that was in force then.
- Being wrong is **silent**. There is no error, only a position that is the wrong size.

**The concrete failure:** the broker changes `contract_size` on a CFD. Nothing detects it. Every position sized after that moment is wrong by that ratio, and it will be discovered from the P&L rather than from a check.

## Options considered

**A. YAML configuration files.**
*Pros:* trivial; version-controlled; no service.
*Cons:* no point-in-time resolution (editing in place silently rewrites history); no drift detection against the broker; no validation; no ownership; every consumer parses it independently and may parse it differently.

**B. A table in each consuming context's schema.**
*Pros:* no new service; each context owns what it needs.
*Cons:* the same instrument defined in three places, guaranteed to diverge. This is the "position smear" failure (ADR-0010, criterion 6) applied to reference data.

**C. A Reference Data bounded context (BC2) with an Instrument Master service.**
*Pros:* one owner; versioned with effective dates; drift detection against the broker; a calendar with a real owner; conformist relationship so nobody adjusts a tick size locally.
*Cons:* a new service and context; a blocking startup dependency for Risk and Execution.

## Decision

**Option C.** Reference Data is **BC2**, a bounded context with an **Instrument Master** service (container C04).

### It owns

| Data | Notes |
|---|---|
| Instrument specifications | `contract_size`, `tick_size`, `tick_value`, `min_lot`, `lot_step`, `max_lot`, `margin_requirement`, `currency`, `quote_currency` |
| Trading calendars | Session open/close per instrument, holidays, DST transitions, early closes |
| Symbol mappings | Platform symbol ↔ per-broker symbol, per-vendor symbol |
| Instrument cluster map | Gold complex, USD complex, risk-on complex. Used by the correlation limit (R11 §4) |
| Tradability state | Halted, delisted, session-closed |

### Rules

1. **Conformist relationship with every other context.** Everyone accepts BC2's model verbatim. **Any context "adjusting" a tick size locally is a bug**, not a workaround.
2. **Versioned with effective dates.** `resolve(symbol, as_of)` is the only accessor. Specs are never edited in place. A change publishes a new version with `effective_from`.
3. **Drift detection.** A scheduled job compares every spec against the broker's live values and emits `evt.instrument.spec.changed.v1` on any difference. A change on an instrument with an open position is a **P0 alert**, because every existing size assumption is now suspect.
4. **Blocking startup dependency.** The Risk Engine and Execution Service **do not start** without a reachable Instrument Master. Sizing against a default or a cached-and-possibly-stale spec is worse than not trading.
5. **Synchronous reads with a 10ms budget**, served from an in-process cache invalidated by `evt.instrument.spec.changed.v1`. Cache miss plus unreachable master means reject the order (fail closed, ADR-0025).
6. **The calendar publishes session events:** `evt.calendar.session.opened.v1` / `.closed.v1`. The Scheduler cannot compute bar-close times without them, and the DST detectors on pages 01 and 02 finally have an authority to compare against.

## Rationale

The decisive property is **silence**. Almost every other kind of configuration error announces itself: a service fails to start, a request 500s, a test breaks. A wrong `contract_size` produces a perfectly successful order for the wrong quantity. Nothing fails. The loss appears in the P&L weeks later and is attributed to strategy underperformance.

Point-in-time resolution is the second reason a file cannot work. Rule 2 means a backtest resolves the spec that was in force at the historical timestamp. With a YAML file edited in place, every historical backtest silently uses today's spec, which is the same class of contamination as the prompt-versioning problem (ADR-0030) and equally invisible.

Rule 3 is the control that catches the concrete failure above, and it exists only because reference data has an owner with a scheduled job. Configuration files do not detect their own drift.

Rule 4 is deliberately strict. The alternative (start with cached specs and hope) fails exactly when the cache is stale, which is after a restart, which is after an incident.

Rule 1 sounds obvious and is the one most likely to be violated in practice. The violation looks like a local `round_to_tick()` helper in the Execution service "because the master's value seemed off." That helper is the bug.

## Consequences

**Positive**
- Position sizing has correct inputs, which is a precondition for every risk control on page 10 meaning anything.
- Lot rounding against a real `lot_step` becomes possible. Rounding 0.007 to 0.01 is a 43% size increase, and this is a real and commonly missed bug.
- Broker spec changes are detected rather than discovered from P&L.
- The DST failure modes on pages 01 and 02 have an authority.
- Backtests resolve historically correct specs.

**Negative**
- A new service, and a blocking startup dependency for the two most critical services.
- A cache invalidation path that must be correct, because a stale spec is exactly the failure being prevented.
- Someone must populate and maintain the initial spec data, and the drift job is what keeps it honest.

**Neutral**
- Small data volume. Postgres `refdata` schema (ADR-0007).

## Tripwire

**None for the decision.** Reference data does not become configuration again.

**Operational tripwire:** if `evt.instrument.spec.changed.v1` never fires in a year, verify the drift job is actually running and comparing. A silent detector is indistinguishable from no detector, and this one is silent by design in the normal case.

## Related

- ADR-0010 (bounded contexts) criterion 6
- ADR-0020 (fractional Kelly) depends on correct specs
- ADR-0019 (exits) uses `InstrumentTradableRule`
- ADR-0025 (fail-closed) governs the unreachable case
- `../review/R19_Missing_Components.md` §4
- `../review/R11_Risk_Architecture.md` §3 (lot rounding)
- `../review/R05_Interface_Contracts.md` §3
