# ADR-0037: Commands and events are distinct primitives; nothing moving capital is a broadcast event

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** messaging, safety, foundational

---

## Context

Page 15 defines one messaging primitive, "event," and uses it to carry three different semantics: facts that happened, instructions to act, and requests for state.

On most subjects this is a naming problem. On one subject it is a capital-loss defect.

`risk.approved` is published by the Risk Engine and consumed by the Execution Platform, which sends an order in response. That makes it an instruction, delivered over a broadcast publish/subscribe channel with at-least-once semantics. The consequences follow directly:

- **At-least-once delivery means the order is sent more than once.** A redelivery after an ack timeout, a consumer restart mid-processing, or a NATS retry all produce a second live order.
- **Broadcast means any number of consumers act.** Nothing in a pub/sub topic prevents a second Execution instance, a debug subscriber, or a misconfigured shadow process from also placing the order. There is no "exactly one owner" concept on a fan-out subject.
- **There is no rejection path.** An event is a statement of fact; a consumer cannot decline it. But placing an order can legitimately fail, and the sender needs to know.

The same defect applies to `risk.killswitch.triggered`, `job.scheduled`, and any future message that instructs rather than reports.

This is blocking defect B1. It is the class of bug that produces duplicate live positions, and it does so under exactly the conditions (restarts, network blips, redelivery) that occur during an incident.

## Options considered

**A. Keep one primitive, add idempotency everywhere.**
*Pros:* no protocol change; idempotency is needed regardless.
*Cons:* idempotency is a *mitigation* for duplicate delivery, not a fix for the wrong delivery model. It does nothing about multiple consumers each legitimately acting on a fan-out subject, and it provides no rejection path. It also puts the entire safety property in the consumer, where a single missed dedup check is a live duplicate order.

**B. Take the order path off the bus entirely, use synchronous RPC from Risk to Execution.**
*Pros:* unambiguous, one caller one callee, natural rejection path.
*Cons:* couples Risk's availability to Execution's; loses durability, so an Execution restart during a call loses the instruction with no record; loses the audit stream that observers (Journal, Monitoring, Learning) legitimately need.

**C. Three distinct primitives with distinct delivery semantics.** Events (facts, pub/sub, fan-out, 0..N consumers), commands (instructions, work queue, exactly one consumer, ack required, retry with dedup), queries (state requests, request/reply, timeout-bounded).
*Pros:* the delivery model matches the semantics in each case; commands get exactly-one-consumer plus ack plus a rejection path plus durability; observers still get the event; the distinction is visible in the subject name so a review can catch a misuse.
*Cons:* two stream configurations rather than one; the discipline must be enforced or the distinction rots.

## Decision

**Option C.**

### The three kinds

| Kind | Semantic | Tense | Delivery | Consumers | A drop means |
|---|---|---|---|---|---|
| **Event** | A fact that happened. Immutable. The producer does not care who listens. | Past (`bar.ingested`) | Pub/sub, at-least-once, fan-out | 0..N | Lost information |
| **Command** | An instruction to act. Addressed to exactly one owner. May be rejected. | Imperative (`place_order`) | Work queue, exactly-one-consumer, ack required, retry with dedup | Exactly 1 | Unperformed work |
| **Query** | A request for current state. No side effects. | Interrogative (`GetPortfolioSnapshot`) | Request/reply, synchronous, timeout-bounded | 1, load balanced | A timeout, retry safe |

### The rule

> **Nothing that moves capital travels as a broadcast event.**

### Naming

```
Events:   evt.<bounded_context>.<aggregate>.<event_name>.v<major>
Commands: cmd.<bounded_context>.<action>.v<major>
Queries:  qry.<bounded_context>.<query_name>.v<major>
DLQ:      dlq.<original_subject_without_version>
Replay:   rpl.<original_subject>
```

Every subject carries an explicit major version. Event names are past tense. Command names are imperative. `bounded_context` comes from the DDD model (ADR-0010), never from a page number or a layer name.

### The specific conversions

| Page 15 today | Becomes |
|---|---|
| `risk.approved` (Execution acts on it) | **Command** `cmd.execution.place_order.v1` on a work queue, **plus event** `evt.risk.trade.approved.v1` on the bus for observers (Journal, Monitoring, Learning) |
| `risk.killswitch.triggered` | **Command** `cmd.platform.halt.v1` (fan-out to every order-capable process, ack required, alongside the synchronous in-process interlock of ADR-0018), **plus event** `evt.risk.killswitch.triggered.v1` for observers |
| `job.scheduled` | **Command** `cmd.<target_context>.run_job.v1` addressed to the owning service, not a broadcast |
| `learning.change.validated` | **Stays an event.** Deployment is human-gated, so a fact is the correct primitive here |

The command/event pair on the order path is deliberate and is the shape to copy: **the command instructs exactly one actor, the event informs everyone else.** Observers subscribe to the event and never to the command.

### Supporting requirements

1. **`CONTROL` stream** carries `cmd.>` with **work-queue retention**: a message is removed once acked by its single consumer. 7-day max age, 3 replicas, discard-new on overflow.
2. **Deterministic idempotency keys**, not random: `idempotency_key = sha256(canonical_json({type, subject, event_time, semantic_identity_fields}))`. For `cmd.execution.place_order.v1` the semantic identity is `{decision_id, leg_index}`.
3. **Deterministic client order ID:** `client_order_id = "wt-" + base32(sha256(decision_id + leg_index))[:20]`. A redelivered command, a replayed stream, and a restarted process all regenerate the identical ID, so the broker rejects the duplicate. This is what makes page 11's idempotency claim actually hold under redelivery, which it currently does not.
4. **Single-use authorisation token.** Consuming the `AuthorisedOrder` is an atomic compare-and-set. A replayed command finds it consumed and is rejected. This is the second line of defence behind the deterministic ID (ADR-0011).
5. **CI enforcement:** a publish to a subject not in the schema registry, a subject violating the naming convention, or a command subject with more than one registered durable consumer all fail the build.

## Rationale

The distinction is not bookkeeping. Each kind needs a *different delivery guarantee*, and using one channel for all three means the weakest guarantee applies to the most dangerous message.

Option A is the tempting one and it is insufficient. Idempotency is genuinely required (points 2 through 4 above are not optional) but it is defence in depth, not the primary control. It does nothing about the fan-out problem, where two consumers each place the order exactly once and the account holds double the position with no duplicate to detect. A work queue makes that structurally impossible.

Option B is rejected because durability matters here. An instruction to place an order that is lost because a process restarted mid-call is as bad as one delivered twice, and it leaves no record.

The layered result is what makes the order path safe: **a work queue prevents multiple actors, an ack prevents loss, a deterministic client order ID prevents duplicate acceptance at the broker, and a single-use token prevents replay.** Four independent mechanisms, each of which alone would leave a gap.

Point 5 matters because this distinction is exactly the kind that rots. Six months in, adding `cmd.` in front of a subject looks like a formality. The CI check is what keeps it real.

## Consequences

**Positive**
- The duplicate-order class is closed structurally rather than by consumer discipline.
- Commands have a rejection path and an ack, so the sender learns about failure.
- Observers still receive everything they need, on the event, with no ability to act.
- The subject name states the semantics, so a misuse is visible in a diff.
- Replay safety composes: a replayed command carries `replay=true` and is rejected by any order-capable component when `env == prod` (R01 §10).

**Negative**
- Two stream configurations and two consumer patterns to understand.
- The command/event pair means two messages where page 15 had one, and they must be kept consistent. They are published in the same transaction via the outbox (ADR-0038), so they cannot diverge.
- The distinction must be enforced or it rots. Hence point 5.

**Neutral**
- Page 15's table is preserved as the domain inventory. Only the primitive kind and the subject names change.

## Tripwire

**None for the core rule.** "Nothing that moves capital is a broadcast event" does not have a plausible reversal condition.

The naming convention and the stream layout may be revised. If the platform ever moves off NATS JetStream (ADR-0004's tripwire), the command/event distinction must survive the migration intact, and this ADR is the reason.

## Related

- ADR-0004 (NATS JetStream as the event backbone)
- ADR-0011 (single-use authorisation token, the fourth defence)
- ADR-0018 (kill switch) uses `cmd.platform.halt.v1`
- ADR-0038 (transactional outbox) keeps the command/event pair consistent
- ADR-0040 (schema registry as the wire contract) supplies the CI enforcement
- `../review/R01_Event_Architecture.md` §2, §3, §5, §6
- Blocking defect B1
- Source: `../15_Event_Catalog.md`, `../11_Execution_Platform.md`
