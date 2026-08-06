# ADR-0038: The transactional outbox is mandatory for any service that writes state and publishes

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** messaging, consistency, reliability

---

## Context

Every service that both mutates durable state and publishes an event has an unstated **dual-write problem**. The naive implementation is:

```python
db.commit()          # succeeds
await bus.publish()  # fails
```

The state changed and nobody was told. Downstream state diverges permanently, with no error and no retry, because from the writing service's point of view the operation succeeded.

The reverse ordering is no better: publish first, then commit, and a commit failure means the world was told about something that did not happen.

This affects, at minimum: the Risk ledger, the Journal, the position ledger, the quarantine table, and the decision saga. In each case the divergence is silent and permanent.

The ADD does not mention the problem. It is not an exotic edge case; it happens whenever a process is restarted, a connection drops, or the bus is briefly unavailable, all of which are routine.

## Options considered

**A. Publish then commit.**
*Pros:* trivial.
*Cons:* a commit failure means a published event for a state change that did not happen. Downstream acts on fiction, which is worse than acting late.

**B. Commit then publish, with a retry.**
*Pros:* trivial; retries cover transient bus failures.
*Cons:* a process crash between the commit and the retry loop's success loses the event permanently. The retry state is in memory, and memory does not survive the crash it is meant to protect against.

**C. Transactional outbox.** The event is written to an outbox table in the **same transaction** as the state change. A separate relay publishes from the outbox and marks rows published.
*Pros:* atomic by construction: either both the state change and the outbox row commit, or neither does. Crash-safe, because the outbox row survives in the database. At-least-once publish, which the idempotency design already makes safe.
*Cons:* a relay process per service; publish latency is polling-bounded; outbox rows to clean up.

**D. Change data capture (Debezium).**
*Pros:* no application-level outbox; captures everything.
*Cons:* a substantial new component (connector plus its own infrastructure) for a workload of tens to hundreds of events per day; the events published would be row-level changes requiring translation into domain events anyway.

## Decision

**Option C.**

```sql
BEGIN;
  UPDATE positions SET ... WHERE ...;
  INSERT INTO outbox (id, subject, envelope, payload, created_at, published_at)
       VALUES (:ulid, :subject, :envelope, :payload, now(), NULL);
COMMIT;
```

1. **A relay process per service**, leader-elected, polls `outbox WHERE published_at IS NULL ORDER BY id`, publishes to NATS, and marks published. Ordering by ULID preserves per-service publication order.
2. **At-least-once publish.** A crash between publish and mark-published republishes on restart. This is safe because every message carries a deterministic `idempotency_key` (ADR-0037).
3. **Symmetric inbox on the consuming side.** `INSERT ... ON CONFLICT (idempotency_key) DO NOTHING` **in the same transaction as the state change**. Zero rows affected means the message was already handled and the handler is skipped.
4. **The outbox row and the state change must be in the same database**, which is why a context's state and its outbox cannot be split across instances (ADR-0007).
5. **Services requiring an outbox:** Risk Engine, Execution Service, Account & Position Ledger, OMS, Data Quality Engine, Decision Service, Instrument Master.
6. **Services not requiring one** (stateless, or naturally idempotent upserts): Regime, Volatility, Structure, Feature materialisers. These publish directly, and a lost event is recovered by recomputation.
7. **The command/event pair on the order path** (ADR-0037) is written as two outbox rows in one transaction, so `cmd.execution.place_order.v1` and `evt.risk.trade.approved.v1` cannot diverge.
8. **Outbox lag is monitored.** `outbox_unpublished_age_seconds` with an SLO. A stalled relay is a silent failure otherwise: state is changing and nobody is being told, which is exactly the condition the outbox exists to prevent.
9. **Published rows are pruned** on a schedule (7 days), after which the event stream is the record.

## Rationale

The outbox is the only pattern that makes the state change and the intent-to-publish **atomic** without distributed transactions. Everything else is a probability argument, and the probabilities are bad: a crash between commit and publish is not rare, it is the normal consequence of any deploy, restart or OOM.

The at-least-once consequence is acceptable precisely because the idempotency work is required regardless (ADR-0037). The outbox converts an unbounded correctness problem (silent permanent divergence) into a bounded one (occasional duplicate delivery) that another mechanism already handles. That is a good trade.

Rule 3 is the half most often skipped. An outbox guarantees the message is published; it does nothing about the consumer processing it twice. Both halves are required, and the inbox must be in the consumer's state transaction for the same reason the outbox is in the producer's.

Rule 8 matters because the outbox's failure mode is quiet. If the relay stalls, the service continues writing state successfully and the outbox fills. Nothing errors. The first symptom is downstream staleness, which will be attributed to the wrong component. The lag metric is what makes it visible.

Option D is rejected on proportionality: a CDC pipeline is a real piece of infrastructure, and the workload here is tens of events per day per service.

## Consequences

**Positive**
- State changes and their events are atomic. No silent permanent divergence.
- Crash-safe: the outbox survives the crash.
- Publication order per service is preserved.
- The command/event pair cannot diverge.

**Negative**
- A relay process per service, leader-elected, which is more moving parts.
- Publish latency is bounded by the poll interval. For the order path this matters, so the relay uses `LISTEN/NOTIFY` to wake immediately on insert, with polling as the fallback.
- Outbox rows accumulate and must be pruned.
- Every write-and-publish operation is slightly more code. Mitigated by a shared helper in the platform library, which is the one place this pattern should be implemented.

**Neutral**
- Postgres already exists and handles this trivially at this volume.

## Tripwire

1. **If `outbox_unpublished_age_seconds` p99 exceeds 5 seconds sustained**, the relay is not keeping up and downstream state is stale in a way nobody is seeing.
2. **If a service on the list in rule 5 is found publishing directly**, treat it as a correctness defect, not a style issue.
3. **If outbox volume ever makes polling expensive** (far beyond current projections), that is the point to reconsider CDC.

## Related

- ADR-0037 (commands vs events) supplies the idempotency keys that make at-least-once safe
- ADR-0007 (Postgres per context) is why state and outbox share an instance
- ADR-0006 (event sourcing for BC7) still needs an outbox to publish beyond its own stream
- ADR-0004 (NATS JetStream) is the publish target
- `../review/R01_Event_Architecture.md` §5, §8
