# ADR-0004: NATS JetStream as the event backbone

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** messaging, infrastructure, foundational

---

## Context

Page 13 selects NATS JetStream without recording alternatives. The choice constrains the wire protocol, the delivery semantics available to ADR-0037, the replay design, and the retention strategy for the audit tier, so it needs a record.

The platform's messaging requirements:

| Requirement | Source |
|---|---|
| Sub-millisecond publish latency on the hot path | 5ms hot-path budget (page 13) |
| Work queues with exactly-one-consumer and ack | ADR-0037's command primitive |
| Durable retention: forever on `TRADING` and `DECISION` | Audit tier (R01 §6) |
| Per-subject ordering | Bars per `(symbol, timeframe)`, fills per account |
| Replay from a stored sequence | Recovery replay (R01 §10) |
| A KV store for the leader lease | Split-brain prevention (R13 §7) |
| Operable by one person | Every page |

Volume is modest: thousands of events per day on the decision path, plus a tick stream that is explicitly droppable and explicitly not fanned out.

## Options considered

**A. NATS JetStream.**
*Pros:* sub-ms publish; native work queues, which are exactly what commands need; built-in KV, usable for the leader lease; a single binary that is genuinely trivial to operate; subject hierarchy maps directly onto the naming convention in ADR-0037; low resource footprint.
*Cons:* multi-year retention as a system of record is not what it is designed for; replay-from-genesis tooling is thinner than Kafka's; consumer-lag observability is adequate rather than rich; no native exactly-once.

**B. Kafka or Redpanda.**
*Pros:* the reference system of record for event streaming; excellent long-retention and compaction; rich consumer-lag tooling; mature replay.
*Cons:* materially higher operational burden (Redpanda less so than Kafka, but still); no native work-queue semantics, so commands must be emulated with a consumer group of one plus manual offset discipline; no built-in KV for the lease; heavier footprint for a workload measured in thousands of messages per day.

**C. RabbitMQ.**
*Pros:* excellent work queues and routing.
*Cons:* weak as an event log; retention and replay are not its model; would need a second system for the audit stream.

**D. Postgres LISTEN/NOTIFY, or a Postgres-backed queue.**
*Pros:* no new infrastructure; transactional with the outbox.
*Cons:* `NOTIFY` payloads are not durable and are dropped when no listener is connected, which is disqualifying for the audit tier; polling a queue table at the required latency is workable but reinvents a message broker badly.

**E. Direct HTTP between services.**
*Pros:* simplest possible.
*Cons:* no durability, no replay, no fan-out, no buffering. Every consumer failure becomes a producer failure. Disqualified by the audit and replay requirements.

## Decision

**Option A, with a documented migration tripwire and an insulating interface.**

1. **NATS JetStream only.** Do **not** run NATS and Kafka side by side. Two messaging systems is a real, recurring operational cost for a solo operator, and this workload does not need one of them.
2. **Eight streams** as specified in R01 §6: `TICKS`, `MARKET`, `QUANT`, `DECISION`, `TRADING`, `CONTROL`, `OPS`, `DLQ`. `CONTROL` uses **work-queue retention** and carries `cmd.>`.
3. **Ordering keys go in the subject**, not only in the payload, because JetStream guarantees order per subject: `evt.market_data.bar.ingested.v1.XAUUSD.M15`.
4. **Exactly-once is achieved by the idempotency design in ADR-0037**, not by the broker. This is required regardless of the broker chosen, so it is not a point against NATS.
5. **Architectural insulation:** the event log sits behind a thin `EventBus` interface with `publish`, `subscribe`, `replay_from`, and `ack`. **No NATS type appears in domain code.** A `grep -r "nats\." --exclude-dir=adapters` returning a hit is a CI failure.
6. **The JetStream KV store holds the leader lease** (TTL 5s, renewed every 2s) for the Execution bridge.

## Rationale

NATS wins on the two requirements that are hardest to satisfy elsewhere: **native work queues** and **operational simplicity for one person**.

The work-queue point is not a convenience. ADR-0037 makes the command/event distinction the primary defence against duplicate orders, and a work queue with exactly-one-consumer plus ack is the mechanism. Kafka can emulate this with a single-member consumer group, but it is emulation, and the property that matters (a second consumer structurally cannot also act) is a configuration convention there rather than a primitive.

The operational point is decisive at this scale. One binary versus a cluster with a coordination layer, for a workload of thousands of messages per day, run by one person who also has to trade.

The honest weakness is long-term retention as a system of record. This is addressed not by choosing Kafka but by **not asking the message broker to be the system of record**: the audit truth lives in the Decision Record Store and the Postgres ledger (hash-chained, object-locked in MinIO), and JetStream's `TRADING` and `DECISION` streams are the transport plus a recent-history buffer. That separation is correct architecture independent of the broker choice, and it removes the main reason to prefer Kafka.

Point 5 is what makes the tripwire actionable rather than theoretical. A migration that requires touching every service is a migration that does not happen.

## Consequences

**Positive**
- Commands get a native primitive rather than an emulation.
- One binary to operate, monitor, back up, and upgrade.
- The leader lease needs no additional infrastructure.
- Publish latency comfortably inside the hot-path budget.

**Negative**
- Consumer-lag observability must be built out explicitly in R12 rather than inherited from mature tooling.
- Replay-from-genesis is a procedure to write and test, not a command to run. It must be exercised at least once before live capital, or it does not work.
- Multi-year stream retention is possible but is not the intended use. This is why the audit truth is deliberately not in the stream.

**Neutral**
- Exactly-once semantics are the application's responsibility either way.

## Tripwire

Promote to **Redpanda** (preferred over Kafka for the same operational reasons that selected NATS) if **any** of these becomes true:

1. Replay-from-genesis becomes a **routine** operation rather than a recovery procedure.
2. Retention on `TRADING` or `DECISION` needs to exceed **2 years with a compaction requirement**.
3. A second consumer group needs **independent replay of the same stream at different offsets, routinely**.
4. Tick volume exceeds **~50k messages/second sustained**.

Conditions 1 and 3 are the realistic ones, and both are consequences of the research workflow growing rather than of trading volume. Review at each quarterly tripwire walk.

## Related

- ADR-0037 (commands vs events) depends on the work-queue primitive
- ADR-0005 (choreography plus one saga) determines what actually flows over this
- ADR-0040 (schema registry as the wire contract)
- `../review/R13_Infrastructure.md` §4
- `../review/R01_Event_Architecture.md` §6, §10
- Source: `../13_Infrastructure_Platform.md`, `../15_Event_Catalog.md`
