# ADR-0006: Event sourcing for the Portfolio context only

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** ddd, persistence, audit

---

## Context

ADR-0012 introduces BC7 Portfolio as a new bounded context that owns positions, lots, trades and the ledger, and states that it is event-sourced. That is a significant persistence decision applied to exactly one of eleven contexts, and an inconsistency of that size needs its reasoning recorded or it will be read as an accident.

Two opposite failure modes follow from leaving it unrecorded:

- **Over-application.** Event sourcing looks principled, so it spreads. Six months later the Feature Store is event-sourced, every projection needs a rebuild path, and the platform has paid the cost eleven times for a benefit that exists once.
- **Erosion.** Someone refactoring for simplicity sees one context persisting differently from the other ten, concludes it is legacy inconsistency, and "fixes" it into a mutable positions table. The audit trail and the reconciliation baseline disappear with it.

## Options considered

**A. Event-source everything.**
*Pros:* consistent; full history everywhere; every context gets time-travel debugging.
*Cons:* every context pays projection cost, rebuild cost and eventual-consistency cost. For the Feature Store and the quantitative engines, the "history" is already in Iceberg with snapshot time travel (ADR-0003), so it is paid for twice. Ten contexts carry the complexity for no benefit.

**B. Event-source nothing.** Mutable state everywhere, with an audit log alongside.
*Pros:* simplest; the model everyone knows.
*Cons:* an audit log written alongside a mutable table is a dual write, so the two can and will diverge; reconstructing the book at a past instant becomes a reconstruction from logs rather than a query; reconciliation has no canonical sequence of internal beliefs to diff against broker truth.

**C. Event-source exactly one context: Portfolio.**
*Pros:* the benefit lands where the requirement is absolute, and the cost is paid once; every other context stays simple.
*Cons:* an inconsistency in the codebase that must be explained (which is what this ADR does).

## Decision

**Option C.** **BC7 Portfolio is event-sourced. No other context is.**

1. The append-only event stream is the **truth**: `PositionOpened`, `PositionIncreased`, `PositionReduced`, `PositionClosed`, `StopMoved`, `TargetAdjusted`, `SwapCharged`, `CommissionCharged`, `EquityMarked`, `ReconciliationBreakDetected`.
2. The stream is stored in **Postgres** (ADR-0007), not in NATS. The message bus transports events; it is not the system of record.
3. **`PortfolioSnapshot` is a projection**, rebuilt from the stream and cached in Redis. Redis holds the projection, never the truth (ADR-0012).
4. **The projection is written only by the projector.** No other component mutates it. In particular, the Risk Engine does not optimistically update it after an approval; only a fill changes the book.
5. **A rebuild-determinism test runs in CI**: replaying the full stream must reproduce the current projection byte-identically. Event sourcing without this test is event sourcing that has already silently broken.
6. **Every other context uses ordinary mutable persistence** with the transactional outbox (ADR-0038) where it publishes.

## Rationale

Four conditions justify event sourcing, and BC7 is the only context where all four hold.

1. **The audit requirement is absolute.** Reconstructing the book at any past instant is not a debugging convenience here, it is the basis of every post-mortem, every tax record and every attribution of a loss to a decision.
2. **Reconciliation needs a canonical sequence of what we believed happened**, to diff against what the broker says happened. A mutable table records only the current belief, which makes a reconciliation break detectable but not diagnosable.
3. **Learning (BC9) needs the full history anyway.** Event sourcing supplies it directly instead of via a separate ETL that can drift from its source.
4. **Write volume is trivially low**: tens to hundreds of events per day. The usual cost objection to event sourcing (projection lag and rebuild time at high volume) simply does not apply. A full rebuild from genesis takes seconds.

No other context satisfies all four. The quantitative engines have their history in Iceberg with snapshot time travel already. The Deliberation context has immutable sealed cycles, which gives it the audit property without the projection machinery. The Feature Store is append-mostly by nature. Applying event sourcing to any of them would be paying a real cost for a benefit already obtained elsewhere.

Point 5 deserves emphasis. The characteristic failure of event sourcing is a projector that silently diverges from its stream, at which point the "truth" and the thing everyone reads disagree and nobody notices for weeks. A rebuild-determinism test in CI is the only thing that catches this, and it is cheap at this volume.

## Consequences

**Positive**
- The book at any past instant is a query, not a reconstruction.
- Reconciliation can diff sequences, not just end states, so a break can be traced to the specific event where beliefs diverged.
- Learning gets complete history with no ETL.
- Correct lot-level cost basis (FIFO/LIFO) becomes natural rather than bolted on. The ADD has no `Lot` concept at all, which makes realised P&L wrong for any partially closed position.
- An accidental mutation is structurally impossible: there is no row to update.

**Negative**
- One context whose persistence differs from every other. This ADR is the explanation, and BC7's code should link to it.
- A projector that must be monitored: `portfolio_projection_lag_seconds`, with an SLO and an alert.
- Every state change must be expressible as an event, which occasionally forces an awkward event name. That friction is a feature: it prevents unmodelled mutation.

**Neutral**
- Redis remains a cache. Its role is unchanged, only clarified.

## Tripwire

1. **Reversal:** if the rebuild-determinism test cannot be kept green, event sourcing is not being maintained correctly and is providing false confidence. Fix it or abandon the pattern deliberately, but do not let it rot.
2. **Extension:** if a second context is proposed for event sourcing, check it against all four conditions above. Satisfying three is not sufficient.
3. **Scale:** if daily event volume exceeds ~50k, revisit projection strategy (snapshotting intervals), though not the decision itself.

## Related

- ADR-0012 (portfolio read model) introduces BC7 and depends on this
- ADR-0007 (Postgres as the transactional store) holds the stream
- ADR-0003 (Iceberg) is why the analytical contexts do not need this
- ADR-0038 (transactional outbox) is what every other context uses instead
- `../review/R03_Domain_Model_DDD.md` §7
- `../review/R19_Missing_Components.md` (Account & Position Ledger)
- Source: `../10_Risk_Portfolio_Platform.md`, `../11_Execution_Platform.md`
