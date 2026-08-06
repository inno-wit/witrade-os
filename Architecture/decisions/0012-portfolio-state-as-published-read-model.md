# ADR-0012: Portfolio state is published as a read model, not queried from Risk

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** boundaries, ddd, dependencies

---

## Context

Page 08 states that the Risk Desk and the Portfolio Desk read current portfolio state and current market conditions in order to form their opinions. In the ADD's component layout, portfolio state lives in the Risk & Portfolio Platform (page 10) and market conditions live in the Execution Platform (page 11).

Both of those are **downstream** of the Committee. The resulting dependency graph is:

```
08 Committee -> 10 Risk -> (execution) -> ... and 08 reads from 10
09 Decision  -> 08 Committee
10 Risk      -> 09 Decision
```

which contains the cycle **08 → 10 → 09 → 08**. This is blocking defect B3.

A cycle in a component graph is not a stylistic problem. It means the components cannot be deployed, versioned, started, or tested independently. It means a change to the Risk Engine's internal state model can break the Committee. And it means there is no correct startup order, so the system's behaviour on cold start depends on timing.

The underlying cause is a modelling gap rather than a wiring mistake: **no component owns "position"**. Page 03 has cross-asset features, page 08 has the Risk Desk reading portfolio state, page 09 has portfolio impact, page 10 has exposure and correlation, page 11 has fills, page 12 has trade history. Six pages touch the concept and none owns it. A layered decomposition has no vocabulary for "the Committee needs to know about portfolio state without depending on the Risk Engine."

## Options considered

**A. Break the cycle by removing portfolio awareness from the desks.**
*Pros:* trivially acyclic.
*Cons:* the Risk Desk and Portfolio Desk exist precisely to reason about the existing book. Removing their input removes their purpose. The system gets measurably dumber to satisfy a diagram.

**B. Allow the cycle, manage it with interfaces.** Dependency inversion at the module level, cycle tolerated at the service level.
*Pros:* minimal restructuring.
*Cons:* a service-level cycle is still a deployment-order problem and a cascading-failure path, whatever the module graph says. It hides the cycle rather than removing it.

**C. Extract a Portfolio bounded context that publishes a read model.** A new context (BC7) owns positions, lots, trades, and the ledger. It publishes a `PortfolioSnapshot` projection. The Committee consumes the projection. The Risk Engine queries the same context synchronously, because it needs freshness the projection cannot guarantee.
*Pros:* removes the cycle completely; gives "position" an owner, which fixes the six-way smear; makes reconciliation meaningful because there is one canonical belief to reconcile against broker truth.
*Cons:* a new context and a new service; two consumption patterns (async projection for the Committee, sync query for Risk) that must be understood as deliberate.

## Decision

**Option C.**

1. **BC7 Portfolio is a bounded context with a service (`ledger-service`).** It owns `Account`, `Position`, `Lot`, `Trade`, and `LedgerEntry`. No other context writes position state.
2. **BC7 is event-sourced.** It is the only context that is. Justification: the audit requirement is absolute, reconciliation needs a canonical sequence of what we believed happened to diff against what the broker says happened, Learning needs the full history anyway, and write volume is tens to hundreds of events per day so the usual cost objection does not apply.
3. **`PortfolioSnapshot` is a projection**, rebuilt from the event stream and cached in Redis. **Redis holds the projection, never the truth.** This corrects page 10, which places live portfolio state in Redis with Postgres as a separate durable ledger and does not define which wins.
4. **The Committee (BC5) consumes the published `PortfolioSnapshot` read model asynchronously.** It has no dependency on BC6 Risk or BC8 Execution at all. Each snapshot carries its `as_of` and its staleness, and a critically stale snapshot blocks a proposal under the BC5 invariant.
5. **The Risk Engine (BC6) queries BC7 synchronously** via `qry.ledger.snapshot`, 30ms timeout, **fail closed** (reject the trade on timeout). Risk approves against real exposure, never against a projection that might lag.
6. **`MarketConditions` (spread, session, broker health) is likewise published by BC8 as a read model**, consumed by BC5. Same pattern, same reasoning.
7. **The projection is written only by the projector.** Risk reads it and never updates it after an approval. Only a fill changes the book. An approved-but-unfilled order is not a position.

## Rationale

The two consumption patterns are the substance of this decision, and they are deliberate rather than inconsistent.

The Committee is reasoning on a 10-second-scale cycle about whether a setup is worth taking. A snapshot that is two seconds old is entirely adequate, and the asynchronous read model buys complete decoupling for that price.

The Risk Engine is deciding, in the last hundred milliseconds before capital moves, whether an exposure limit would be breached. A two-second-old snapshot there is a real limit breach. It gets the synchronous query, and it fails closed, because approving against stale exposure is exactly the failure this whole context exists to prevent.

Point 7 is the invariant that prevents the most likely bug in this design: optimistically updating the projection at approval time so that two rapid approvals see each other's effect. That is tempting and wrong. The correct control for in-flight exposure is a separate pending-authorisation reservation held by the Risk Engine itself, not a mutation of the book.

Option A is rejected because it solves a structural problem by deleting a capability. Option B is rejected because a cycle you have decided to tolerate is a cycle that will produce a cascading failure at the worst time.

## Consequences

**Positive**
- The dependency graph is acyclic. Every context is independently deployable and testable.
- "Position" has exactly one owner, so six components can no longer hold six divergent ideas of what is open.
- Reconciliation against broker truth becomes meaningful, because there is one canonical internal belief.
- `Lot` and correct cost-basis accounting become possible. The ADD has no lot concept at all, which makes realised P&L wrong for any partially closed position.
- Learning gets the full history for free rather than through a separate ETL.

**Negative**
- A new service to build, deploy and monitor.
- Event sourcing in one context and not the other ten is an inconsistency that must be explained, which is what ADR-0006 exists for.
- The projector is now a critical path component: if it stalls, the Committee reasons on stale state. It needs a lag SLO and an alert.

**Neutral**
- Redis is retained, in its correct role as a projection cache.

## Tripwire

If projection lag p99 exceeds 2 seconds sustained, the asynchronous read model is no longer adequate for the Committee and either the projector needs work or the Committee moves to the synchronous query. Monitor `portfolio_projection_lag_seconds` from day one.

## Related

- ADR-0006 (event sourcing for the Portfolio context only)
- ADR-0011 (Risk as sole authorisation authority) is the other half of the boundary correction
- ADR-0016 (OMS)
- `../review/R03_Domain_Model_DDD.md` §2, §7
- Blocking defect B3
- Source: `../08_AI_Investment_Committee.md`, `../10_Risk_Portfolio_Platform.md`, `../11_Execution_Platform.md`
