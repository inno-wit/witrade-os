# 22 — Instrument & Reference Data Master

**Diagram:** none yet — see Future Expansion
**Phase:** 4 — Data Platform
**C4 Level:** L2 — Container
**Depends on:** `00_Master_Architecture.md`
**Status:** Draft
**Container:** C04 · **Context:** BC2 Reference Data · **Criticality:** Tier 0 (position sizing
is impossible without it) · **Group:** Edge

**Provenance:** this page did not exist at Architecture Freeze v1 — `Technical_Debt_Register.md`
row TD1 flagged BC2 as having no dedicated page, priority P1, blocking Gate 4's BC2 work (C04)
specifically until closed. The content below consolidates what already existed scattered across
`review/R05_Interface_Contracts.md` §3 and `review/R19_Missing_Components.md` §4 into the same
page template pages 01-21 use, closing that gap at implementation level (same treatment TD8
already received in the same register — an implementation-level closure, not a substitute for a
human Architecture Review, which remains a separate open step).

---

## Purpose

Answer, authoritatively and point-in-time-correctly, "what is this instrument, and may it be
traded right now." Every other service resolves symbols, contract specs, sessions, and holidays
through this one place rather than caching or re-deriving broker metadata itself.

## Responsibilities

- Serve authoritative contract specifications per symbol per broker.
- Serve the trading calendar: sessions, holidays, early closes, DST transitions, rollover dates.
- Map platform symbols to broker symbols and back (used by the Broker ACL).
- Version every specification change with an effective-from date — a change is a new version,
  never an in-place edit.
- Publish session-open/close events that the Scheduler and Quality Engine depend on.

## Owns (exclusive write access)

`instruments`, `instrument_specs`, `calendars`, `sessions`, `holidays`, `symbol_mappings`.

## Inputs

| Source | Protocol | Cadence | Data |
|---|---|---|---|
| Broker spec feed (MT5 `symbol_info`) | Pull, scheduled | Daily diff | Contract size, tick size, min lot, margin requirement |
| Exchange calendars | Pull, scheduled | Daily | Sessions, holidays, early closes, DST rules |
| Operator | Manual, audited | Ad hoc | New specs, corrections, rollover dates |

## Outputs

Instrument specs, trading calendars, tradability verdicts — read by every service that resolves a
`Symbol` (Ingestion for bar-close timing, Quality Engine's DST/broker-outage detectors, Risk,
Execution, the Feature Store).

## Dependencies

Hard: Postgres. Soft: broker connection for spec refresh (degrades to last-known-good, see below).

## Invariants

1. Every `Symbol` used anywhere in the platform resolves here. An unresolvable symbol is a hard
   error, never a default.
2. A spec is immutable once effective. A change creates a new version with a new `effective_from`.
3. `get_spec(symbol, broker, as_of)` always returns the spec that was in force at `as_of`, never
   the current one — point-in-time strict, same discipline as the Feature Store's invariant 1.
4. `tick_size`, `contract_size`, `pip_value` (and any other price-derived field) are `Decimal`.
   Never `float`.
5. A symbol with no spec effective at `as_of` is not tradable. There is no fallback default.

## Interfaces

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Query | `get_spec(symbol, broker, as_of) -> InstrumentSpec` | Yes | 10ms (cached) | service |
| Query | `is_tradable(symbol, at) -> TradabilityVerdict` | Yes | 10ms | service |
| Query | `next_bar_close(symbol, timeframe, after) -> Timestamp` | Yes | 10ms | service |
| Query | `session_for(symbol, at) -> Session` | Yes | 10ms | service |
| Query | `to_broker_symbol(symbol, broker) -> str` | Yes | 5ms | service |
| Command | `publish_spec_version(spec, effective_from)` | Yes | 1s | operator, audited |

## Events Published

- `evt.instrument.spec.changed.v1`
- `evt.calendar.session.opened.v1`
- `evt.calendar.session.closed.v1`
- `evt.calendar.holiday.upcoming.v1`

## Events Consumed

None. This context is a source, same posture as Ingestion (page 01).

## Failure Modes

| Mode | Detection |
|---|---|
| Broker changes a spec silently (contract size, min lot, margin) | Daily automated diff against the live broker feed; any delta raises P1 |
| Calendar wrong or stale (missed holiday, early close) | Staleness monitor: calendar coverage must extend ≥30 days forward, else P1 |
| Symbol mapping drift (broker renames a symbol) | Mapping resolution failure rate metric; any failure is P0 during market hours |
| DST transition mishandled | Assertion in CI: bar-close times across a DST boundary must be continuous |

## Degraded Mode

Serves the last-known-good specs from a local cache and sets `degraded=true` on every response.
**Any consumer receiving `degraded=true` may size and manage existing positions but may not open
new ones.** Fail-safe, not fail-open — the same posture Ingestion takes when all price sources are
open (page 01) and the Feature Store takes when a category goes stale (page 03 contract).

## Recovery Strategy

Specs are refreshed from the broker on a schedule and diffed. A diff is a P1 alert requiring human
confirmation, never auto-applied — a broker feed glitch that silently halved `contract_size` would
silently double every position size computed against it.

## SLO

Availability 99.95% during market hours; `get_spec` p50 < 1ms (cache hit), p99 < 10ms; calendar
forward coverage ≥ 30 days; zero unresolvable symbols in production.

## Security Boundary

Read by every service; written only by an `operator` with audit. No secrets beyond the Postgres
credential.

## Technology

Postgres, aggressive in-process caching with event-driven invalidation. (No FastAPI/HTTP surface
in this pass — Gate 4 wires this as an in-process service per the same interim posture Gate 2 used
for Supervisor/Scheduler/Identity/Secrets; a network-reachable deployment is a Gate 12 concern.)

## Future Expansion

Corporate actions, futures roll schedules, borrow/short availability, multiple broker specs per
symbol for smart routing, a dedicated Excalidraw diagram (deferred — no diagram exists for this
page yet, unlike pages 00-21).

---

## Related

- `01_Data_Ingestion.md` §"Failure Modes" — DST transitions, the specific failure mode invariant 3
  here and CI assertion above jointly close
- `contracts/02_Data_Quality_Engine.contract.md` — `DetectorContext` carries the instrument spec
  and calendar from this service
- `contracts/03_Feature_Store.contract.md` — invariant 1's point-in-time discipline mirrors
  invariant 3 here
- `review/R05_Interface_Contracts.md` §3 — source content consolidated into this page
- `review/R19_Missing_Components.md` §4 — source content consolidated into this page
- `../governance/Roadmap/Implementation_Gates.md` — Gate 4 entry gating BC2 work on this page's
  existence
- `../Blueprint/Technical_Debt_Register.md` — TD1, the debt item this page closes (BC2 half)
