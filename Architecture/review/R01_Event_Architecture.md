# R01 — Event-Driven Architecture

**Deliverable:** 1
**Delta against:** `15_Event_Catalog.md`, `00_Master_Architecture.md` (Orchestration Layer), `13_Infrastructure_Platform.md`
**Status:** Review v1.0

---

## 1. What page 15 gets right, and what it is missing

Page 15 is a **list of message names**. An event architecture is a **contract**. The gap between those two things is where distributed systems fail.

| Present in page 15 | Absent |
|---|---|
| Event names | Envelope, versioning, schema, ownership, delivery semantics |
| Publisher | Producer identity, causation chain |
| Consumers | Durable consumer names, ack policy, redelivery, DLQ |
| Prose payload summary | Machine-checkable schema |
| A naming convention | Enforcement of that convention (it is violated in the same table) |
| — | Command/event/query distinction |
| — | Ordering guarantees and partition keys |
| — | Retention, replay, and rewind procedure |
| — | Idempotency strategy per consumer |
| — | Backpressure and poison-message handling |

Everything below is additive. Page 15's table is preserved as the domain inventory; this file gives it the missing half.

---

## 2. The three message kinds (this is the primary correction)

The blueprint currently has one primitive, "event", carrying three different semantics. Separate them. This closes blocking defect B1.

| Kind | Semantic | Tense | Delivery | Consumers | Failure meaning |
|---|---|---|---|---|---|
| **Event** | A fact that happened. Immutable. The producer does not care who listens. | Past (`bar.ingested`, `trade.approved`) | Publish/subscribe, at-least-once, fan-out | 0..N | A dropped event is lost information |
| **Command** | An instruction to do something. Addressed to exactly one owner. May be rejected. | Imperative (`PlaceOrder`, `CancelOrder`, `HaltTrading`) | Work queue, exactly-one-consumer, ack required, retry with dedup | Exactly 1 | A dropped command is unperformed work |
| **Query** | A request for current state. No side effects. | Interrogative (`GetPortfolioSnapshot`) | Request/reply, synchronous, timeout-bounded | 1, load balanced | A dropped query is a timeout, retry safe |

### The rule that follows

> Nothing that moves capital travels as a broadcast event.

Concretely, the following change kind:

| Page 15 today | Becomes |
|---|---|
| `risk.approved` consumed by Execution to send an order | **Command** `cmd.execution.place_order.v1` on a work queue, plus **event** `risk.trade.approved.v1` on the bus for observers (Journal, Monitoring, Learning) |
| `risk.killswitch.triggered` | **Command** `cmd.platform.halt.v1` (fan-out to every order-capable process, ack required, plus the synchronous in-process interlock of page 10) and **event** `risk.killswitch.triggered.v1` for observers |
| `job.scheduled` | **Command** `cmd.{service}.run_job.v1` addressed to the owning service, not a broadcast |
| `learning.change.validated` triggering a deployment | **Event**. Deployment is human-gated per page 14, so a fact is correct here. Keep. |

---

## 3. Naming convention v2

Page 15 uses `{layer}.{entity}.{action}`, which couples wire identifiers to architectural layer names and is violated three times in its own table.

### New convention

```
Events:   evt.<bounded_context>.<aggregate>.<event_name>.v<major>
Commands: cmd.<bounded_context>.<action>.v<major>
Queries:  qry.<bounded_context>.<query_name>.v<major>
DLQ:      dlq.<original_subject_without_version>
Replay:   rpl.<original_subject>        (replayed copies, flagged in envelope)
```

Rules, enforced in CI (see §7):

1. `bounded_context` comes from the DDD model in R03, not from a page number or a layer name. It is stable across refactors.
2. Event names are **past tense verbs**. `bar.ingested`, not `bar.receive` or `data.bar.received` (that last one is passive, ambiguous about who acted).
3. Commands are **imperative**. `place_order`, not `order_placement`.
4. Every subject carries an explicit major version. There is no unversioned subject.
5. Subject segments are `snake_case`, lowercase, no plurals.
6. NATS wildcard subscriptions remain natural: `evt.risk.>` for everything the Risk context emits, `evt.*.*.*.v1` for all v1 traffic.

### Migration of page 15's names

| Page 15 | v2 subject | Kind |
|---|---|---|
| `data.tick.received` | `evt.market_data.tick.ingested.v1` | Event (internal stream, not fanned out) |
| `data.bar.received` | `evt.market_data.bar.ingested.v1` | Event |
| `data.source.degraded` | `evt.market_data.source.degraded.v1` | Event |
| `data.quality.scored` | `evt.data_quality.dataset.scored.v1` | Event |
| `data.quality.rejected` | `evt.data_quality.dataset.quarantined.v1` | Event |
| `feature.updated` | `evt.feature_store.feature_set.materialised.v1` | Event |
| `feature.backfilled` | `evt.feature_store.feature_set.backfilled.v1` | Event |
| `regime.updated` | `evt.regime.classification.published.v1` | Event |
| `regime.shift.detected` | `evt.regime.classification.shifted.v1` | Event |
| `volatility.updated` | `evt.volatility.forecast.published.v1` | Event |
| `volatility.regime_shift` | `evt.volatility.forecast.recalibrated.v1` | Event |
| `structure.updated` | `evt.market_structure.structure.published.v1` | Event |
| `structure.confluence.detected` | `evt.market_structure.confluence.detected.v1` | Event |
| `model.trained` | `evt.model.candidate.trained.v1` | Event |
| `model.promoted` | `evt.model.version.promoted.v1` | Event |
| `model.prediction` | (removed from the bus, see §6 high-volume policy) | Log record |
| `committee.convened` | `evt.committee.cycle.convened.v1` | Event |
| `committee.desk.completed` | `evt.committee.desk_opinion.submitted.v1` | Event |
| `committee.recommendation` | `evt.committee.recommendation.issued.v1` | Event |
| `committee.deadlock` | `evt.committee.cycle.deadlocked.v1` | Event |
| `evidence.graph.built` | `evt.decision.evidence_graph.assembled.v1` | Event |
| `decision.made` | `evt.decision.proposal.issued.v1` | Event (verb changed per B4) |
| `decision.explained` | `evt.decision.explanation.rendered.v1` | Event |
| `risk.approved` | `evt.risk.trade.approved.v1` + `cmd.execution.place_order.v1` | Event + **Command** |
| `risk.rejected` | `evt.risk.trade.rejected.v1` | Event |
| `risk.killswitch.triggered` | `evt.risk.killswitch.triggered.v1` + `cmd.platform.halt.v1` | Event + **Command** |
| `risk.killswitch.cleared` | `evt.risk.killswitch.cleared.v1` | Event |
| `order.sent` | `evt.execution.order.submitted.v1` | Event |
| `order.filled` | `evt.execution.order.filled.v1` | Event |
| `order.rejected` | `evt.execution.order.rejected_by_broker.v1` | Event |
| `execution.slippage.recorded` | `evt.execution.fill.analysed.v1` | Event |
| `alert.triggered` | `evt.observability.alert.raised.v1` | Event |
| `learning.review.completed` | `evt.learning.review.completed.v1` | Event |
| `learning.hypothesis.generated` | `evt.learning.hypothesis.generated.v1` | Event |
| `learning.change.validated` | `evt.learning.change.validated.v1` | Event |
| `deploy.*` | `evt.deployment.release.{started,promoted,rolled_back}.v1` | Event |
| `shadow.run.completed` | `evt.deployment.shadow_run.completed.v1` | Event |
| `job.scheduled` | `cmd.<target_context>.run_job.v1` | **Command** |
| `workflow.*` | `evt.orchestration.workflow.{started,failed,completed}.v1` | Event |

---

## 4. The envelope (mandatory, every message)

Modelled on CloudEvents 1.0 with trading-specific extensions. Every message on every subject carries this. No exceptions, including internal high-volume streams.

```jsonc
{
  // --- CloudEvents core ---
  "specversion": "1.0",
  "id":          "01J8ZQ...",          // ULID, unique per message instance
  "source":      "svc://regime-engine/prod/eu-west-1/pod-7",
  "type":        "evt.regime.classification.shifted.v1",
  "subject":     "XAUUSD/M15",         // routing/partition hint, human meaningful
  "time":        "2026-08-03T14:30:00.117Z",   // producer wall clock, RFC3339 UTC
  "datacontenttype": "application/json",
  "dataschema":  "schemareg://evt.regime.classification.shifted/1.4.0",

  // --- Correlation and causation (mandatory) ---
  "correlation_id": "01J8ZQ...",       // constant for an entire decision cycle, end to end
  "causation_id":   "01J8ZP...",       // the `id` of the message that directly caused this one
  "trace_parent":   "00-4bf92f...-00f0...-01",  // W3C traceparent, links to the span

  // --- Determinism and replay (mandatory) ---
  "event_time":     "2026-08-03T14:30:00.000Z", // BUSINESS time (bar close), not wall clock
  "logical_clock":  1754231400,        // simulation-safe monotonic sequence
  "replay":         false,             // true when emitted by the replay harness
  "replay_run_id":  null,

  // --- Idempotency (mandatory) ---
  "idempotency_key": "sha256:9f2c...", // deterministic over the semantic content, see §5

  // --- Governance ---
  "producer_version": "regime-engine@2.3.1+g8ac21",
  "tenant":           "default",
  "env":              "prod",           // prod | paper | shadow | sim | dev
  "pii":              false,
  "retention_class":  "audit",          // audit | operational | ephemeral

  // --- Payload ---
  "data": { /* schema-validated body, see §7 */ }
}
```

### Why each mandatory field earns its place

| Field | Without it |
|---|---|
| `correlation_id` | You cannot answer "show me everything that happened for the decision that produced this loss." This is the single most valuable field in the envelope. |
| `causation_id` | You have a set of events, not a causal graph. Root-cause analysis becomes guesswork. |
| `event_time` vs `time` | Backtests and live runs cannot share code. Every out-of-order or late-arriving message becomes a correctness bug. |
| `logical_clock` | Replay is not deterministic; two runs of the same historical period produce different results. |
| `idempotency_key` | At-least-once delivery becomes at-least-once *side effects*. This is B1. |
| `replay` / `replay_run_id` | Replayed traffic contaminates live state, live metrics, and the live P&L ledger. |
| `producer_version` | You cannot answer "which build produced this decision" during an incident or an audit. |
| `env` | A shadow-environment message that leaks onto the production subject sends a real order. |
| `retention_class` | Audit records get deleted by an operational retention policy. |

---

## 5. Idempotency

### Key derivation (deterministic, not random)

`idempotency_key = sha256(canonical_json({type, subject, event_time, semantic_identity_fields}))`

`semantic_identity_fields` is defined per message type in its schema. Examples:

| Message | Semantic identity |
|---|---|
| `evt.market_data.bar.ingested.v1` | `{source, symbol, timeframe, bar_close_time}` |
| `evt.regime.classification.published.v1` | `{symbol, timeframe, as_of, model_version}` |
| `evt.committee.recommendation.issued.v1` | `{cycle_id}` |
| `cmd.execution.place_order.v1` | `{decision_id, leg_index}` |
| `evt.execution.order.filled.v1` | `{broker_order_id, fill_sequence}` |

### Consumer-side pattern (three tiers, choose per consumer)

| Tier | Mechanism | Use for |
|---|---|---|
| **Natural idempotence** | The operation is a pure upsert keyed by semantic identity. No dedup store needed. | Feature materialisation, regime/vol/structure writes, projections |
| **Inbox table** | `INSERT ... ON CONFLICT (idempotency_key) DO NOTHING` in the same transaction as the state change. If the insert affects 0 rows, skip the handler. | Anything writing to Postgres: ledger, journal, risk state |
| **Broker-side dedup** | Deterministic `client_order_id`, plus a pre-send `get_order_by_client_id` check against the broker. | Execution only. Already correct in page 11, now with a deterministic key rather than a generated one |

### The rule for the order path

`client_order_id = "wt-" + base32(sha256(decision_id + leg_index))[:20]`

Deterministic from the decision. A redelivered command, a replayed stream, or a restarted process all regenerate the identical ID, so the broker rejects the duplicate. This is what makes page 11's idempotency claim actually hold under redelivery, which it currently does not.

---

## 6. Delivery semantics, ordering, retention

### Stream design (NATS JetStream)

| Stream | Subjects | Storage | Retention | Replicas | Discard | Max age | Rationale |
|---|---|---|---|---|---|---|---|
| `TICKS` | `evt.market_data.tick.>` | File | Limits | 1 | Old | 24h | Highest volume, lowest value per message. Explicitly droppable. Never blocks a producer. |
| `MARKET` | `evt.market_data.bar.>`, `evt.data_quality.>`, `evt.feature_store.>` | File | Limits | 3 | New (reject) | 90d | Reproducibility inputs. Rejecting a write is better than losing one. |
| `QUANT` | `evt.regime.>`, `evt.volatility.>`, `evt.market_structure.>`, `evt.model.>` | File | Limits | 3 | New | 365d | Evidence lineage. Must survive to justify a decision a year later. |
| `DECISION` | `evt.committee.>`, `evt.decision.>` | File | Limits | 3 | New | Forever (compacted to the Decision Record Store) | Audit tier. |
| `TRADING` | `evt.risk.>`, `evt.execution.>` | File | Limits | 3 | New | Forever | Audit tier. Financial record. |
| `CONTROL` | `cmd.>` | File | Work queue | 3 | New | 7d | Commands. Work-queue retention: a message is removed once acked by its single consumer. |
| `OPS` | `evt.orchestration.>`, `evt.observability.>`, `evt.deployment.>`, `evt.learning.>` | File | Limits | 1 | Old | 30d | Operational, reconstructible. |
| `DLQ` | `dlq.>` | File | Limits | 3 | New | 30d | Never auto-purged before human review. |

### Ordering

NATS JetStream guarantees order **per subject** within a stream. That is sufficient if and only if the partition key is in the subject.

**Rule:** any message whose processing order matters carries its ordering key in the NATS subject token, not only in the payload.

```
evt.market_data.bar.ingested.v1.XAUUSD.M15
evt.execution.order.filled.v1.ACC7781
```

Consumers that require strict ordering bind one durable consumer per key-space with `max_ack_pending=1`. Consumers that do not (Monitoring, Journal) use a shared durable with high concurrency.

Order matters for: bars per `(symbol, timeframe)`, orders and fills per `account`, kill-switch commands per `account`, ledger postings per `account`. Order does not matter for: telemetry, alerts, learning events, deployment events.

### Ack, retry, backoff

```
ack_policy   = explicit
ack_wait     = 2 x p99(handler latency), minimum 5s
max_deliver  = 5
backoff      = [1s, 5s, 30s, 2m, 10m]
```

After `max_deliver`, the message is published to `dlq.<subject>` with a `dlq_reason` extension in the envelope, and `evt.observability.alert.raised.v1` fires. It is never silently dropped.

### High-volume policy (removes `model.prediction` from the bus)

Page 15 lists `model.prediction` and `data.tick.received` as "not broadcast platform-wide", which is a policy hidden in a prose note. Make it structural:

- **Tier A, bus:** anything a second service reacts to. Full envelope, full retention.
- **Tier B, stream-local:** `TICKS`, consumed only inside the Market Data context. Subject-scoped so no cross-context subscription is possible.
- **Tier C, log only:** per-inference records like model predictions. Written to the Decision Record Store attached to the cycle that requested them, never published. Volume is proportional to committee cycles, not to bars.

---

## 7. Schema registry and versioning

### Registry

A schema registry is a P1 requirement, not a nice-to-have, because §4's `dataschema` field is meaningless without one.

- **Format:** JSON Schema 2020-12. Chosen over Avro/Protobuf because the platform is Python-first, payloads are low-volume outside Tier B, and human readability of the audit record matters more than 30% wire savings. Reconsider Protobuf if tick data ever goes on the bus (ADR-004).
- **Storage:** the schemas live in the repo under `contracts/schemas/`, are the source of truth, and are published to a small registry service (or a versioned MinIO bucket) at build time. Git is the registry; the service is the runtime cache.
- **Generation:** Pydantic models are generated *from* the schemas, not the other way round. This prevents a Python-side refactor from silently changing the wire contract.

### Compatibility policy

| Change | Allowed within a major version | Requires |
|---|---|---|
| Add an optional field with a default | Yes | Minor bump |
| Add a required field | No | Major bump, new subject `.v2` |
| Remove a field | No | Deprecate for 2 releases, then major bump |
| Widen an enum | No (consumers may switch exhaustively) | Major bump, or add `_other` from day one |
| Narrow a type or tighten a constraint | No | Major bump |
| Rename a field | No | Major bump. Never rename in place |
| Change semantics of an existing field | No, and this is the dangerous one | Major bump. If the type is unchanged, this is undetectable by tooling and must be caught in review |

### Multi-version transition

Producers dual-publish `.v1` and `.v2` for one full release cycle. Consumers migrate. `.v1` is retired only when the registry reports zero consumers bound to it (tracked via durable consumer names, §9). This is why durable consumers must be named after the *service*, not auto-generated.

### CI enforcement

A required GitHub Actions check (page 14's gate model) that fails the build on:

1. A publish call whose subject is not in the registry.
2. A subject in the registry with a producer but no consumer (orphan event, page 15's own listed failure mode, now caught mechanically).
3. A subscribe call to a subject with no producer (silent gap, the other half of the same failure mode).
4. A schema change that violates the compatibility table.
5. A subject name that violates the §3 convention.
6. A message type published without an `idempotency_key` derivation rule declared.

This mechanises page 15's "Future Expansion" item and closes finding D10. Pages 15 and 16 become generated artefacts.

---

## 8. Transactional outbox (closes the dual-write gap)

Every service that both mutates durable state and publishes an event currently has an unstated dual-write problem: if the DB commit succeeds and the publish fails, downstream state diverges permanently. This affects the Risk ledger, the Journal, the position ledger, and the quarantine table.

### Pattern

```sql
BEGIN;
  UPDATE positions SET ... WHERE ...;
  INSERT INTO outbox (id, subject, envelope, payload, created_at, published_at)
       VALUES (:ulid, :subject, :envelope, :payload, now(), NULL);
COMMIT;
```

A relay process (one per service, leader-elected) polls `outbox WHERE published_at IS NULL ORDER BY id`, publishes to NATS, and marks published. At-least-once publish, which §5's idempotency keys make safe.

Symmetric **inbox** on the consuming side, as described in §5 tier 2.

Services requiring outbox: Risk Engine, Execution Service, Account & Position Ledger, Data Quality Engine, Decision Service. Services not requiring it (stateless or naturally idempotent): Regime, Volatility, Structure, Feature materialisers.

---

## 9. Consumer registry

Every durable consumer is declared in code and registered:

| Field | Example |
|---|---|
| `durable_name` | `risk-engine--committee-recommendations` |
| `owning_service` | `risk-engine` |
| `subjects` | `evt.committee.recommendation.issued.v1.>` |
| `delivery` | `ordered_by=account`, `max_ack_pending=1` |
| `idempotency` | `inbox_table` |
| `slo_lag` | p99 consumer lag < 500ms |
| `dlq_owner` | on-call risk |

Naming: `<service>--<purpose>`. Never auto-generated, because §7's retirement logic depends on being able to enumerate who is still bound to a version.

---

## 10. Replay strategy

Three distinct replay modes. The blueprint currently implies one and defines none.

| Mode | Purpose | Source | Sink | Side effects | Env |
|---|---|---|---|---|---|
| **Recovery replay** | A consumer crashed or was buggy; reprocess from a known-good sequence | The live stream, rewound to a stored sequence number | Live state, protected by idempotency | Yes, intentionally | `prod` |
| **Simulation replay** | Backtest, counterfactual, model comparison | Historical Iceberg snapshot, driven by the Simulation Clock (R19 §2) | An isolated sim namespace | No production side effects. Broker adapter is the simulated one | `sim` |
| **Shadow replay** | Validate a new model/prompt against live traffic without acting | Live stream, tapped read-only | Shadow store, compared against production output | None. Execution adapter is a null adapter | `shadow` |

### Guardrails, mandatory

1. `replay=true` in the envelope on every replayed message. Any order-capable component **rejects** a command with `replay=true` unless `env != prod`. This is a hard interlock, symmetric to the kill switch.
2. `env` mismatch between the message and the process is an immediate hard failure, not a warning.
3. Replay runs carry a `replay_run_id` so their output is attributable and purgeable.
4. Recovery replay requires an explicit operator command with the target start sequence and a dry-run count first (how many messages will be reprocessed).
5. Simulation replay must produce byte-identical output across two runs given the same `replay_run_id` and seed. This is a CI test, not a hope. It is the only way page 03's point-in-time claim is verifiable.

### Rewind procedure

```
1. Halt the affected consumer (cmd.platform.halt scoped to that consumer group)
2. Snapshot its current durable state
3. Record the target sequence: nats consumer info <stream> <durable>
4. Dry run: report message count and time span in the rewind window
5. Operator confirms with typed confirmation (execution-safety pattern, page 14)
6. nats consumer edit --start-seq=<n>
7. Resume, monitor consumer lag and inbox dedup-hit rate
8. Post-replay reconciliation against broker truth before trading resumes
```

---

## 11. Dead letter queues

| Property | Policy |
|---|---|
| Subject | `dlq.<original_subject_minus_version>` |
| Envelope | Original envelope preserved verbatim, plus `dlq_reason`, `dlq_attempts`, `dlq_first_seen`, `dlq_last_error`, `dlq_consumer` |
| Retention | 30 days minimum, never auto-purged before triage |
| Alerting | Any message landing in a DLQ on the `TRADING` or `DECISION` streams pages immediately. `MARKET`/`OPS` DLQ raises a ticket-tier alert. |
| Redrive | An explicit operator-run tool that republishes to the original subject with `redriven_from_dlq=true` and a fresh `id` but the **same** `idempotency_key` |
| Poison detection | If more than 3 distinct messages from the same producer hit the same DLQ within 5 minutes, the consumer is auto-paused and an incident is opened. Prevents a schema break from burning the whole stream through `max_deliver`. |

---

## 12. Synchronous vs asynchronous: the explicit boundary

Page 16 draws "solid arrows for the critical path" and "dashed for the bus" but does not say which integration primitive each uses. Make it a rule.

### Synchronous (request/reply or in-process, never fire-and-forget)

| Interaction | Why | Timeout | On timeout |
|---|---|---|---|
| Risk Engine → Account & Position Ledger (`qry.ledger.snapshot`) | Approving against stale exposure is B4-adjacent | 30ms | Reject the trade. Fail closed. |
| Risk Engine → Kill Switch interlock | Must be the last thing before the token is issued | 10ms | HALT. Fail closed. |
| Execution → Instrument Reference Data | Contract specs cannot be eventually consistent when sizing | 10ms (cached, see R17 §5) | Reject the order |
| Execution → Broker Adapter | It is an RPC to an external system | 300ms | Enter `UNKNOWN` order state, reconcile, never blind-retry |
| Committee desk → Claude API | It is an RPC | 8s | Desk abstains (page 08's existing abstain path) |
| Decision Service → Risk Preview (`qry.risk.preview`) | Advisory, must reflect current limits | 50ms | Proceed with `preview_unavailable=true`, which the Risk Engine will catch authoritatively downstream anyway |
| Dashboard → any read model | User-facing | 2s | Show stale-with-timestamp, never a spinner forever |

### Asynchronous (bus)

Everything else. Every fact. All telemetry. All triggers. All learning. All deployment.

### The one-line rule

> If a wrong or missing answer costs money in the next 300ms, it is synchronous and fails closed. Otherwise it is an event.

---

## 13. Workflow orchestration: choreography vs orchestration

Page 00 leaves "Temporal vs custom DAG runner" open. Resolve it as a boundary, not a tool choice.

| Flow type | Pattern | Implementation |
|---|---|---|
| Data pipeline (ingest → quality → features → engines) | **Choreography.** Each stage reacts to the previous stage's event. No central coordinator. | NATS consumers only. No workflow engine. |
| Decision cycle (trigger → evidence → committee → proposal → risk → execution) | **Orchestration.** There is a defined saga with compensation, a deadline, and a terminal state that must be recorded. | A Decision Cycle Saga owned by the Decision Service. State persisted in Postgres, one row per `cycle_id`, driven by a state machine (R07 §3). |
| Long-running human-gated flows (deployment promotion, quarantine review, risk-limit change) | **Orchestration with timers and human tasks.** | This is the only genuine Temporal use case. Defer until there are 3+ such flows. Until then, Postgres + a scheduler. |
| Scheduled jobs | **Commands from a scheduler**, not events. | The Scheduler emits `cmd.<ctx>.run_job.v1`. |

**Recommendation:** build the custom saga runner for the decision cycle now (it is ~300 lines and you need precise control over the deadline semantics in R17 §2), keep choreography for data, and set the Temporal tripwire at 3 human-gated long-running workflows. Recorded as ADR-005.

---

## 14. Event catalog v2, additions

Beyond the renamed page 15 entries, the following are new events required by the corrections in this review. Full payloads live in `contracts/schemas/`.

| Subject | Producer | Consumers | Why it is new |
|---|---|---|---|
| `cmd.execution.place_order.v1` | Risk Engine | Execution (exactly one) | B1 |
| `cmd.execution.cancel_order.v1` | OMS | Execution | Missing OMS |
| `cmd.execution.modify_position.v1` | OMS | Execution | Stop moves, partial TP, missing entirely |
| `cmd.platform.halt.v1` / `cmd.platform.resume.v1` | Risk Engine, Operator | Every order-capable process | B2 |
| `cmd.platform.set_mode.v1` | Operator | All services | Platform state machine, R07 §1 |
| `evt.platform.mode.changed.v1` | Platform Supervisor | All | ditto |
| `evt.position.opened.v1` / `.increased.v1` / `.reduced.v1` / `.closed.v1` | Account & Position Ledger | Risk, OMS, Learning, Journal | Missing position lifecycle |
| `evt.position.stop_moved.v1` | OMS | Journal, Learning | ditto |
| `evt.reconciliation.break_detected.v1` | Reconciliation Service | Risk (auto-halt), Monitoring | Missing reconciliation |
| `evt.reconciliation.completed.v1` | Reconciliation Service | Platform Supervisor (gates exit from RECONCILING) | ditto |
| `evt.instrument.spec.changed.v1` | Instrument Master | Risk, Execution, Feature Store | Missing reference data |
| `evt.calendar.session.opened.v1` / `.closed.v1` | Instrument Master | Ingestion, Quality, Committee triggers | DST/session correctness (D7) |
| `evt.decision.expired.v1` | Decision Saga | Monitoring, Learning | Decision TTL, D3 |
| `evt.cost.budget.exceeded.v1` | Cost Governor | Committee admission control | Missing cost governance |
| `evt.llm.call.completed.v1` | LLM Gateway | Cost Governor, Decision Record Store | Token/cost/latency accounting |
| `evt.prompt.version.promoted.v1` | Prompt Registry | Committee, Learning | Point-in-time prompt correctness |
| `evt.model.drift.detected.v1` | Model Monitor | Learning, Risk | Page 07 names staleness as a failure with no detector |
| `evt.audit.record.sealed.v1` | Decision Record Store | Compliance read model | Hash-chain checkpoint |

---

## 15. Ownership table

Every subject has exactly one owning bounded context. Only that context may publish it. This is enforced in CI by mapping the subject prefix to a CODEOWNERS path.

| Prefix | Owning context | Owning service |
|---|---|---|
| `evt.market_data.*` | Market Data | ingestion |
| `evt.data_quality.*` | Data Quality | quality-engine |
| `evt.feature_store.*` | Feature Store | feature-service |
| `evt.regime.*` | Regime | regime-engine |
| `evt.volatility.*` | Volatility | volatility-engine |
| `evt.market_structure.*` | Market Structure | structure-engine |
| `evt.model.*` | Model Lifecycle | model-service |
| `evt.committee.*` | Committee | committee-service |
| `evt.decision.*` | Decision | decision-service |
| `evt.risk.*`, `cmd.platform.halt` | Risk | risk-engine |
| `evt.execution.*`, `cmd.execution.*` (consumer) | Execution | execution-service |
| `evt.position.*` | Portfolio | ledger-service |
| `evt.instrument.*`, `evt.calendar.*` | Reference Data | instrument-master |
| `evt.reconciliation.*` | Reconciliation | recon-service |
| `evt.learning.*` | Learning | learning-service |
| `evt.deployment.*` | Delivery | ci/cd |
| `evt.observability.*` | Observability | monitoring |
| `evt.platform.*` | Platform | supervisor |

---

## 16. Related

- `R00_Executive_Review.md` (B1, D4, D5, D6)
- `R03_Domain_Model_DDD.md` (bounded contexts that define the subject namespace)
- `R07_State_Machines.md` (the sagas these messages drive)
- `R13_Infrastructure.md` (NATS vs Kafka decision and tripwire)
- `R17_Performance.md` (backpressure, consumer lag budgets)
- Source: `../15_Event_Catalog.md`
