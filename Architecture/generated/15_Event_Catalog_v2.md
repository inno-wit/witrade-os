# 15v2 — Event Catalog (regenerated)

**Supersedes as the working contract:** `../15_Event_Catalog.md`
**Source page status:** unmodified, preserved as the original design-time inventory
**Delta against:** `../15_Event_Catalog.md`, corrected per `../review/R01_Event_Architecture.md`
**Governed by:** ADR-0037 (commands vs events), ADR-0040 (schema registry is the wire contract), ADR-0004 (NATS JetStream), ADR-0038 (transactional outbox)
**Status:** Generated artefact v2, design-time. Becomes machine-generated from `contracts/schemas/` once code exists (ADR-0040)

---

## Why this file exists rather than an edit to page 15

Page 15 is a list of message names. An event architecture is a contract. Page 15 says so itself: its own Status field predicts a rebuild pass, and its Failure Modes section names drift and orphan events as the two ways it rots.

This file is that rebuild. It is a sibling rather than a replacement because the overlay rule holds: pages 00-16 are not modified, so the original intent stays readable and every change stays traceable. Page 15 remains the correct record of what was designed on 2026-08-03. This file is what gets implemented.

**The eight things page 15 was missing**, all now present: envelope, kind (command vs event vs query), owning context, stream assignment, ordering key, idempotency identity, retention class, and DLQ subject.

---

## 1. The three message kinds

Page 15 has one primitive, "event", carrying three different semantics. That conflation is blocking defect B1: a broadcast event consumed by Execution as an instruction to send an order produces duplicate live orders under at-least-once redelivery.

| Kind | Semantic | Tense | Delivery | Consumers | A dropped one means |
|---|---|---|---|---|---|
| **Event** | A fact that happened. Immutable. The producer does not care who listens | Past | Pub/sub, at-least-once, fan-out | 0..N | Lost information |
| **Command** | An instruction addressed to exactly one owner. May be rejected | Imperative | Work queue, one consumer, ack required, retry with dedup | Exactly 1 | Unperformed work |
| **Query** | A request for current state. No side effects | Interrogative | Request/reply, synchronous, timeout-bounded | 1, load balanced | A timeout, retry safe |

> **The rule:** nothing that moves capital travels as a broadcast event. (ADR-0037, no tripwire, this is a fixed point.)

## 2. Naming convention v2

```
Events:   evt.<bounded_context>.<aggregate>.<event_name>.v<major>
Commands: cmd.<bounded_context>.<action>.v<major>
Queries:  qry.<bounded_context>.<query_name>.v<major>
DLQ:      dlq.<original_subject_without_version>
Replay:   rpl.<original_subject>
```

Ordering keys append as subject tokens: `evt.market_data.bar.ingested.v1.XAUUSD.M15`, `evt.execution.order.filled.v1.ACC7781`. NATS JetStream guarantees order per subject, so a partition key that is not in the subject is not an ordering guarantee.

Six rules, all CI-enforced (§8):

1. `bounded_context` comes from the DDD model (R03), never from a page number or layer name.
2. Event names are past-tense verbs. `bar.ingested`, not `data.bar.received`.
3. Commands are imperative. `place_order`, not `order_placement`.
4. Every subject carries an explicit major version. There is no unversioned subject.
5. Segments are lowercase `snake_case`, no plurals.
6. Wildcard subscription stays natural: `evt.risk.>` is everything the Risk context emits.

## 3. Envelope

Every message on every subject, including internal high-volume streams. Full field-by-field justification in R01 §4. The five fields with no equivalent anywhere in page 15, and what their absence costs:

| Field | Without it |
|---|---|
| `correlation_id` | You cannot ask "show me everything that happened for the decision that produced this loss" |
| `causation_id` | You have a set of events, not a causal graph |
| `event_time` (business time, distinct from `time`) | Backtest and live cannot share code |
| `logical_clock` | Replay is not deterministic |
| `idempotency_key` | At-least-once delivery becomes at-least-once side effects, which is B1 |
| `replay` / `replay_run_id` | Replayed traffic contaminates live state, live metrics, and the live P&L ledger |
| `env` | A shadow message leaking onto a production subject sends a real order |

`tenant` is present, mandatory, and permanently `"default"` per ADR-0009. It is a reserved seam, not a feature. Any code path that branches on it is rejected in review.

---

## 4. The catalog

Every subject in the platform. **Kind** is E (event), C (command). **Ord** is the ordering key appended to the subject, blank where order does not matter. **Idem** is the semantic identity from which `idempotency_key` is derived.

### 4.1 Reference data (BC2, owner: instrument-master)

| Subject | Kind | Publisher | Consumers | Stream | Ord | Idem | Page 15 origin |
|---|---|---|---|---|---|---|---|
| `evt.instrument.spec.changed.v1` | E | Instrument Master | Risk, Execution, Feature Materialiser, OMS | REFERENCE | symbol | `{symbol, broker, effective_from}` | **NEW** (D7) |
| `evt.calendar.session.opened.v1` | E | Instrument Master | Ingestion, Quality, Committee triggers, Scheduler | REFERENCE | symbol | `{symbol, session_id}` | **NEW** (D7) |
| `evt.calendar.session.closed.v1` | E | Instrument Master | Ingestion, Quality, OMS (time-based exits) | REFERENCE | symbol | `{symbol, session_id}` | **NEW** (D7) |
| `evt.calendar.holiday.upcoming.v1` | E | Instrument Master | Scheduler, Risk (News Guard) | REFERENCE | symbol | `{symbol, date}` | **NEW** |

The absence of this whole family from page 15 is why DST transitions and early closes have no owner in the current design. Position sizing is impossible without contract specs, which makes this context Tier 0 despite looking like configuration.

### 4.2 Market data (BC1, owner: ingestion)

| Subject | Kind | Publisher | Consumers | Stream | Ord | Idem | Page 15 origin |
|---|---|---|---|---|---|---|---|
| `evt.market_data.tick.ingested.v1` | E | Ingestion (MT5) | Market Data context only, never cross-context | TICKS | symbol | `{source, symbol, ts}` | `data.tick.received` |
| `evt.market_data.bar.ingested.v1` | E | Ingestion, all sources | Quality, OMS, Committee triggers | MARKET | symbol.tf | `{source, symbol, timeframe, bar_close_time}` | `data.bar.received` |
| `evt.market_data.source.degraded.v1` | E | Ingestion circuit breaker | Observability, Platform Supervisor | MARKET | | `{source, detected_at}` | `data.source.degraded` |
| `evt.market_data.text.extracted.v1` | E | Untrusted Text ACL (C02) | Feature Materialiser | MARKET | symbol | `{doc_hash}` | **NEW** (B5) |

`evt.market_data.text.extracted.v1` carries **typed features only, never prose**. It is the only path by which anything derived from a news provider reaches CORE. This is the structural half of closing B5 (ADR-0032); the LLM Gateway's instruction-pattern check is the second, redundant half.

Tick traffic is Tier B: stream-local, subject-scoped so no cross-context subscription is possible. Page 15 stated this as a prose note ("not broadcast"); here it is structural.

### 4.3 Data quality (BC1, owner: quality-engine)

| Subject | Kind | Publisher | Consumers | Stream | Ord | Idem | Page 15 origin |
|---|---|---|---|---|---|---|---|
| `evt.data_quality.dataset.scored.v1` | E | Quality Engine | Feature Materialiser | MARKET | symbol.tf | `{dataset_id, scorer_version}` | `data.quality.scored` |
| `evt.data_quality.dataset.quarantined.v1` | E | Quality Engine | Observability, quarantine review UI | MARKET | | `{dataset_id, reason_code}` | `data.quality.rejected` |

Renamed from `rejected` to `quarantined` deliberately. Page 02's design is a reviewable quarantine, not a silent drop, and the subject name should not suggest otherwise.

### 4.4 Feature store (BC3, owner: feature-service)

| Subject | Kind | Publisher | Consumers | Stream | Ord | Idem | Page 15 origin |
|---|---|---|---|---|---|---|---|
| `evt.feature_store.feature_set.materialised.v1` | E | Feature Materialiser (C06) | Regime, Volatility, Structure, Inference | MARKET | symbol.tf | `{symbol, timeframe, category, as_of, feature_version}` | `feature.updated` |
| `evt.feature_store.feature_set.backfilled.v1` | E | Feature Materialiser | Quant engines, Learning | MARKET | symbol | `{symbol, category, version, range_start, range_end}` | `feature.backfilled` |

Publisher changed from "Feature Store" to the materialiser specifically. After the C06/C07 split there are two containers and only one of them writes. That distinction is the point of the split.

### 4.5 Quant engines (BC4, owners: regime-engine, volatility-engine, structure-engine)

| Subject | Kind | Publisher | Consumers | Stream | Ord | Idem | Page 15 origin |
|---|---|---|---|---|---|---|---|
| `evt.regime.classification.published.v1` | E | Regime Engine | Evidence Graph, Volatility, Feature writeback | QUANT | symbol.tf | `{symbol, timeframe, as_of, model_version}` | `regime.updated` |
| `evt.regime.classification.shifted.v1` | E | Regime Engine | Evidence Graph, Committee trigger, Quality | QUANT | symbol.tf | `{symbol, timeframe, as_of}` | `regime.shift.detected` |
| `evt.volatility.forecast.published.v1` | E | Volatility Engine | Evidence Graph, Risk (sizing input) | QUANT | symbol.tf | `{symbol, timeframe, as_of, model_version}` | `volatility.updated` |
| `evt.volatility.forecast.recalibrated.v1` | E | Volatility Engine | Evidence Graph, Committee trigger | QUANT | symbol.tf | `{symbol, as_of, reason_code}` | `volatility.regime_shift` |
| `evt.market_structure.structure.published.v1` | E | Structure Engine | Evidence Graph, OMS (invalidation exits) | QUANT | symbol.tf | `{symbol, timeframe, as_of, detector_version}` | `structure.updated` |
| `evt.market_structure.confluence.detected.v1` | E | Structure Engine | Committee trigger (primary) | QUANT | symbol.tf | `{symbol, timeframe, as_of}` | `structure.confluence.detected` |

Consumer lists changed structurally: page 15 routes these to "AI Committee desks" directly. They now route to the **Evidence Graph Service**, which assembles a point-in-time snapshot that desks read. Desks never subscribe to live quant events. That is what makes a committee cycle replayable and is half of closing B3.

### 4.6 Model lifecycle (BC4, owner: model-service)

| Subject | Kind | Publisher | Consumers | Stream | Ord | Idem | Page 15 origin |
|---|---|---|---|---|---|---|---|
| `evt.model.candidate.trained.v1` | E | Model Training (C12) | MLflow, Learning | QUANT | | `{model_id, training_run_id}` | `model.trained` |
| `evt.model.version.promoted.v1` | E | Model Training | Inference, Committee, Learning | QUANT | | `{model_id, version, slot}` | `model.promoted` |
| `evt.model.drift.detected.v1` | E | Model Monitor (C14) | Learning, Risk (ModelRiskRule) | QUANT | | `{model_id, version, detector, window_end}` | **NEW** |
| ~~`model.prediction`~~ | — | — | — | **removed from the bus** | | | Tier C, log only |

`model.prediction` is removed as a subject. Per-inference records are written to the Decision Record Store attached to the cycle that requested them. Volume then scales with committee cycles rather than with bars, which is a difference of three orders of magnitude.

`evt.model.drift.detected.v1` is new because page 07 names model staleness as a failure mode and assigns detection to nobody.

### 4.7 Committee (BC5, owner: committee-service)

| Subject | Kind | Publisher | Consumers | Stream | Ord | Idem | Page 15 origin |
|---|---|---|---|---|---|---|---|
| `evt.committee.cycle.convened.v1` | E | Committee | Observability, Decision Record Store | DECISION | | `{cycle_id}` | `committee.convened` |
| `evt.committee.desk_opinion.submitted.v1` | E | Committee | Consensus (internal), Record Store, Learning | DECISION | cycle | `{cycle_id, desk, prompt_version}` | `committee.desk.completed` |
| `evt.committee.recommendation.issued.v1` | E | Committee | Decision Saga | DECISION | cycle | `{cycle_id}` | `committee.recommendation` |
| `evt.committee.cycle.deadlocked.v1` | E | Committee | Observability, Learning (calibration) | DECISION | cycle | `{cycle_id}` | `committee.deadlock` |
| `evt.committee.quorum.failed.v1` | E | Committee | Observability, Learning | DECISION | cycle | `{cycle_id}` | **NEW** |
| `evt.prompt.version.promoted.v1` | E | Prompt Registry (C18) | Committee, Learning | DECISION | | `{prompt_id, version}` | **NEW** |
| `evt.llm.call.completed.v1` | E | LLM Gateway (C17) | Cost Governor, Decision Record Store | DECISION | cycle | `{call_id}` | **NEW** |
| `evt.llm.call.failed.v1` | E | LLM Gateway | Cost Governor, Observability | DECISION | cycle | `{call_id}` | **NEW** |

`evt.committee.quorum.failed.v1` is separated from deadlock deliberately. They are different conditions with different meanings: deadlock is desks disagreeing (a signal), quorum failure is desks being unavailable (an outage). Page 08 conflates them, and the calibration metric that makes the committee falsifiable (ADR-0027) needs them apart.

### 4.8 Decision (BC5, owner: decision-service)

| Subject | Kind | Publisher | Consumers | Stream | Ord | Idem | Page 15 origin |
|---|---|---|---|---|---|---|---|
| `evt.decision.evidence_graph.assembled.v1` | E | Evidence Graph (C15) | Committee, Record Store, audit tooling | DECISION | cycle | `{cycle_id, graph_hash}` | `evidence.graph.built` |
| `evt.decision.proposal.issued.v1` | E | Decision Saga (C19) | Risk Engine, Record Store | DECISION | cycle | `{decision_id}` | `decision.made` |
| `evt.decision.explanation.rendered.v1` | E | Decision Saga | Dashboard, Journal | DECISION | cycle | `{decision_id}` | `decision.explained` |
| `evt.decision.expired.v1` | E | Decision Saga | Observability, Learning | DECISION | cycle | `{decision_id}` | **NEW** (D3) |
| `evt.audit.record.sealed.v1` | E | Decision Record Store (C20) | Compliance read model | DECISION | | `{checkpoint_id}` | **NEW** |

`decision.made` becomes `decision.proposal.issued`. The verb change is not cosmetic: it closes B4. Page 09 currently says the Decision Intelligence Layer approves trades, and page 10 says the Risk Engine approves trades. Two components claiming authorisation authority is how an unauthorised order reaches a broker. Decision **proposes**, Risk **authorises** (ADR-0011).

`evt.decision.expired.v1` closes D3: a decision whose `valid_until` has passed must be observably dead, not silently executed late.

### 4.8b Portfolio Construction (BC12, owner: portfolio-construction-service) — **added 2026-08-04, Phase 11**

| Subject | Kind | Publisher | Consumers | Stream | Ord | Idem | Page 15 origin |
|---|---|---|---|---|---|---|---|
| `evt.portfolio_construction.candidate.admitted.v1` | E | Portfolio Construction (C40) | Risk Engine, Record Store | DECISION | cycle | `{candidate_id}` | **NEW** (`../18_Portfolio_Construction.md`) |
| `evt.portfolio_construction.candidate.deferred.v1` | E | Portfolio Construction | Record Store, Learning | DECISION | cycle | `{candidate_id, rank}` | **NEW** |
| `evt.portfolio_construction.candidate.rejected.v1` | E | Portfolio Construction | Record Store, Learning | DECISION | cycle | `{candidate_id, reason}` | **NEW** |
| `evt.portfolio_construction.candidate.displaced.v1` | E | Portfolio Construction | Record Store, Learning | DECISION | cycle | `{candidate_id, displaced_by}` | **NEW** |
| `evt.portfolio_construction.plan.published.v1` | E | Portfolio Construction | Record Store, Dashboard | DECISION | cycle | `{plan_id}` | **NEW** |

Note the admitted candidate is forwarded to Risk as an **event carrying a filtered, capped proposal**, not a command — BC6 re-evaluates independently and issues its own `AuthorisedOrder` (ADR-0043); an `admitted` message is never itself sufficient to move capital, so it deliberately does not take the command shape used for `cmd.execution.place_order.v1` in §4.9. Every non-admitted candidate is published with the same durability as an admitted one (page 18 invariant 4) — the opportunity-cost record is the point of this subject group.

### 4.9 Risk (BC6, owner: risk-engine)

| Subject | Kind | Publisher | Consumers | Stream | Ord | Idem | Page 15 origin |
|---|---|---|---|---|---|---|---|
| **`cmd.execution.place_order.v1`** | **C** | **Risk Engine** | **Execution, exactly one** | **CONTROL** | account | `{decision_id, leg_index}` | **NEW, closes B1** |
| `evt.risk.trade.approved.v1` | E | Risk Engine | Journal, Observability, Learning (observers only) | TRADING | account | `{decision_id}` | `risk.approved` |
| `evt.risk.trade.rejected.v1` | E | Risk Engine | Observability, Learning | TRADING | account | `{decision_id, rule_id}` | `risk.rejected` |
| `evt.risk.limit.breached.v1` | E | Risk Engine | Observability, Platform Supervisor | TRADING | account | `{limit_id, breached_at}` | **NEW** |
| **`cmd.platform.halt.v1`** | **C** | **Risk Engine, Operator** | **every order-capable process, ack required** | **CONTROL** | account | `{trip_id}` | **NEW, part of B2** |
| **`cmd.platform.resume.v1`** | **C** | Operator | every order-capable process | CONTROL | account | `{clear_id}` | **NEW** |
| `evt.risk.killswitch.triggered.v1` | E | Risk Engine | Observability (P0 page), Journal | TRADING | account | `{trip_id}` | `risk.killswitch.triggered` |
| `evt.risk.killswitch.cleared.v1` | E | Risk Engine | Observability, Journal | TRADING | account | `{clear_id}` | `risk.killswitch.cleared` |
| `evt.risk.limit_set.published.v1` | E | Risk Engine | Observability, audit | TRADING | | `{limit_set_version}` | **NEW** |

**The split on the approval row is the single most important correction in this file.** `risk.approved` in page 15 is one broadcast event that Execution consumes as an instruction. Under at-least-once redelivery that is a duplicate live order. It becomes two things: a command with exactly-one-consumer semantics and broker-side dedup on a deterministic `client_order_id`, plus an event for observers who genuinely only need to know.

The kill switch is the same shape, and additionally retains its **synchronous in-process interlock** (ADR-0017). `cmd.platform.halt.v1` is the fan-out belt; the interlock is the braces. The command does not replace the interlock and must never be refactored into doing so.

### 4.10 Execution (BC8, owner: execution-service)

| Subject | Kind | Publisher | Consumers | Stream | Ord | Idem | Page 15 origin |
|---|---|---|---|---|---|---|---|
| `cmd.execution.cancel_order.v1` | C | OMS | Execution | CONTROL | account | `{client_order_id}` | **NEW** |
| `cmd.execution.modify_position.v1` | C | OMS | Execution | CONTROL | account | `{position_id, action_seq}` | **NEW** |
| `evt.execution.order.submitted.v1` | E | Execution | Observability, Journal | TRADING | account | `{client_order_id}` | `order.sent` |
| `evt.execution.order.filled.v1` | E | Execution | Ledger, OMS, Reconciliation, Learning | TRADING | account | `{broker_order_id, fill_sequence}` | `order.filled` |
| `evt.execution.order.rejected_by_broker.v1` | E | Execution | Observability, Risk | TRADING | account | `{client_order_id, broker_reason}` | `order.rejected` |
| `evt.execution.order.unknown.v1` | E | Execution | Reconciliation, Observability (P0) | TRADING | account | `{client_order_id, detected_at}` | **NEW** |
| `evt.execution.fill.analysed.v1` | E | Execution / TCA (C29) | Risk (slippage trip), Ledger, Learning | TRADING | account | `{broker_order_id, fill_sequence}` | `execution.slippage.recorded` |
| `evt.execution.broker.reconnected.v1` | E | Execution | Reconciliation (forces a run) | TRADING | account | `{session_id}` | **NEW** |

`evt.execution.order.unknown.v1` makes page 11's own named failure mode ("connectivity loss mid-order, unknown outcome") into a first-class, observable state rather than something handled ad hoc. An order in `UNKNOWN` is never blind-retried; it is reconciled.

### 4.11 Portfolio (BC7, owner: ledger-service)

| Subject | Kind | Publisher | Consumers | Stream | Ord | Idem | Page 15 origin |
|---|---|---|---|---|---|---|---|
| `evt.position.opened.v1` | E | Position Ledger (C22) | Risk, OMS, Learning, Journal | TRADING | account | `{trade_id}` | **NEW** |
| `evt.position.increased.v1` | E | Position Ledger | Risk, OMS, Journal | TRADING | account | `{trade_id, seq}` | **NEW** |
| `evt.position.reduced.v1` | E | Position Ledger | Risk, OMS, Journal | TRADING | account | `{trade_id, seq}` | **NEW** |
| `evt.position.closed.v1` | E | Position Ledger | Risk, OMS, Learning, Journal | TRADING | account | `{trade_id}` | **NEW** |
| `evt.position.stop_moved.v1` | E | OMS (C23) | Journal, Learning, Reconciliation | TRADING | account | `{position_id, action_seq}` | **NEW** |
| `evt.position.partial_closed.v1` | E | OMS | Journal, Learning | TRADING | account | `{position_id, action_seq}` | **NEW** |
| `evt.position.exit_requested.v1` | E | OMS | Observability, Journal | TRADING | account | `{position_id, request_id}` | **NEW** |
| `evt.position.plan_attached.v1` | E | OMS | Journal, Observability | TRADING | account | `{position_id, plan_version}` | **NEW** |
| `evt.position.adopted_unmanaged.v1` | E | OMS | Observability (P0), Operator | TRADING | account | `{position_id, detected_at}` | **NEW** |
| `evt.account.equity_marked.v1` | E | Position Ledger | Risk, Dashboard | TRADING | account | `{account_id, as_of}` | **NEW** |
| `evt.ledger.correction_applied.v1` | E | Position Ledger | Journal, audit, Observability | TRADING | account | `{correction_id}` | **NEW** |

**Eleven subjects, all new, none of which page 15 has any equivalent for.** This is the shape of the largest gap in the ADD: the design ends at the fill. Everything that happens to a position after it opens (the stop moves, the partial exits, the adoption of a position opened at the terminal, the corrections) had no owner and no event. Page 15 is entry-biased because the architecture behind it is.

### 4.12 Reconciliation (BC7/BC8, owner: recon-service)

| Subject | Kind | Publisher | Consumers | Stream | Ord | Idem | Page 15 origin |
|---|---|---|---|---|---|---|---|
| `evt.reconciliation.completed.v1` | E | Reconciliation (C25) | Platform Supervisor (gates RECONCILING exit) | TRADING | account | `{run_id}` | **NEW** |
| `evt.reconciliation.break_detected.v1` | E | Reconciliation | Risk (auto-trip), OMS, Observability (P0) | TRADING | account | `{break_id}` | **NEW** |
| `evt.reconciliation.break_resolved.v1` | E | Reconciliation | Journal, audit | TRADING | account | `{break_id, resolution_id}` | **NEW** |

### 4.13 Platform (BC10, owner: supervisor)

| Subject | Kind | Publisher | Consumers | Stream | Ord | Idem | Page 15 origin |
|---|---|---|---|---|---|---|---|
| `cmd.platform.set_mode.v1` | C | Operator | Platform Supervisor | CONTROL | account | `{transition_id}` | **NEW** |
| `evt.platform.mode.changed.v1` | E | Platform Supervisor (C26) | every service | TRADING | account | `{transition_id}` | **NEW** |
| `cmd.<target_context>.run_job.v1` | C | Scheduler (C35) | the owning service, exactly one | CONTROL | | `{job_id, scheduled_for}` | `job.scheduled` |
| `evt.orchestration.workflow.started.v1` | E | Saga runner | Observability | OPS | | `{workflow_id, step}` | `workflow.started` |
| `evt.orchestration.workflow.failed.v1` | E | Saga runner | Observability | OPS | | `{workflow_id, step}` | `workflow.failed` |
| `evt.orchestration.workflow.completed.v1` | E | Saga runner | Observability | OPS | | `{workflow_id}` | `workflow.completed` |

`job.scheduled` becomes a **command** addressed to the owning service. A broadcast "a job was scheduled" that every service inspects to decide whether it is theirs is how two services eventually run the same job.

`evt.platform.mode.changed.v1` sits on TRADING rather than OPS despite looking operational. Mode transitions are the context that makes every financial record interpretable ("why did nothing trade for four hours"), so they inherit TRADING's forever retention and three replicas.

### 4.14 Cost, observability, learning, delivery (BC10/BC9, owners: cost-governor, monitoring, learning-service, ci/cd)

| Subject | Kind | Publisher | Consumers | Stream | Ord | Idem | Page 15 origin |
|---|---|---|---|---|---|---|---|
| `evt.cost.budget.exceeded.v1` | E | Cost Governor (C30) | Committee admission control, Observability | OPS | | `{scope, window_start}` | **NEW** |
| `evt.observability.alert.raised.v1` | E | Monitoring | Operator paging | OPS | | `{alert_id}` | `alert.triggered` |
| `evt.learning.review.completed.v1` | E | Learning | Observability, Dashboard | OPS | | `{review_id, period}` | `learning.review.completed` |
| `evt.learning.hypothesis.generated.v1` | E | Learning | Experiment queue (internal) | OPS | | `{hypothesis_id}` | `learning.hypothesis.generated` |
| `evt.learning.change.validated.v1` | E | Learning | Deployment pipeline (human-gated) | OPS | | `{change_id}` | `learning.change.validated` |
| `evt.deployment.release.started.v1` | E | CI/CD | Observability | OPS | | `{deploy_id}` | `deploy.started` |
| `evt.deployment.release.promoted.v1` | E | CI/CD | Observability | OPS | | `{deploy_id}` | `deploy.promoted` |
| `evt.deployment.release.rolled_back.v1` | E | CI/CD | Observability (P1) | OPS | | `{deploy_id}` | `deploy.rolled_back` |
| `evt.deployment.shadow_run.completed.v1` | E | CI/CD | Deployment gate, Learning | OPS | | `{shadow_id}` | `shadow.run.completed` |

`learning.change.validated` correctly stays an event, not a command. Deployment is human-gated per page 14, so a fact is the right primitive: the learning loop states what it found, a human decides what happens. Turning this into a command would be the mechanism by which the platform silently starts deploying itself.

---

## 5. Counts

| | Page 15 | This file (2026-08-03) | This file + Phase 11 (2026-08-04) |
|---|---|---|---|
| Subjects | 43 (39 table rows, two of which carry three subjects each; 3 violate its own naming convention) | **80** | **85** |
| Commands, distinguished from events | 0 | **7** | 7 (§4.8b is all-event, by design — see below) |
| Removed from the bus | 0 | 1 (`model.prediction`, Tier C) | 1 |
| Subjects with an ordering key | 0 | 58 | 63 |
| Subjects with a declared idempotency identity | 0 | 80 | 85 |
| Subjects with a stream assignment | 0 | 80 | 85 |
| Bounded contexts represented | 8 loosely, by layer | 14, by DDD context | 15 (BC12 added) |

Counts are of the live subject rows in §4 and exclude the struck-through `model.prediction`. Page 15's own catalog is 39 table rows, but `workflow.started` / `.failed` / `.completed` and `deploy.started` / `.promoted` / `.rolled_back` each collapse three subjects into one row, so the comparable subject count is 43.

Thirty-eight subjects are marked **NEW** against page 15. Twenty of those are position lifecycle, reconciliation, reference data, and platform mode: the four families whose absence from page 15 is the honest measure of how entry-biased the source design is. Five more (§4.8b, Phase 11) are new against the 2026-08-03 catalog for a different reason: BC12 did not exist yet, not because the original catalog missed something.

---

## 6. Streams

Delta against R01 §6: that table predates the §14 additions, so five subject families had no stream assignment. Assigned here, with the additions marked.

| Stream | Subjects | Storage | Retention | Replicas | Discard | Max age |
|---|---|---|---|---|---|---|
| `TICKS` | `evt.market_data.tick.>` | File | Limits | 1 | Old | 24h |
| `MARKET` | `evt.market_data.{bar,source,text}.>`, `evt.data_quality.>`, `evt.feature_store.>` | File | Limits | 3 | New | 90d |
| **`REFERENCE`** | `evt.instrument.>`, `evt.calendar.>` | File | Limits | 3 | New | Forever | **added here** |
| `QUANT` | `evt.regime.>`, `evt.volatility.>`, `evt.market_structure.>`, `evt.model.>` | File | Limits | 3 | New | 365d |
| `DECISION` | `evt.committee.>`, `evt.decision.>`, `evt.llm.>`, `evt.prompt.>`, `evt.audit.>` | File | Limits | 3 | New | Forever | `evt.llm/prompt/audit` **added here** |
| `TRADING` | `evt.risk.>`, `evt.execution.>`, `evt.position.>`, `evt.account.>`, `evt.ledger.>`, `evt.reconciliation.>`, `evt.platform.>` | File | Limits | 3 | New | Forever | last five **added here** |
| `CONTROL` | `cmd.>` | File | **Work queue** | 3 | New | 7d |
| `OPS` | `evt.orchestration.>`, `evt.observability.>`, `evt.deployment.>`, `evt.learning.>`, `evt.cost.>` | File | Limits | 1 | Old | 30d |
| `DLQ` | `dlq.>` | File | Limits | 3 | New | 30d, never auto-purged before triage |

`REFERENCE` gets forever retention despite tiny volume because a spec change is often the explanation for a sizing change a year later, and losing it makes that decision unexplainable.

`CONTROL` is the only work-queue stream. That is what makes a command a command: the message is removed once acked by its single consumer, rather than fanned out and retained.

### Ack and retry, all streams

```
ack_policy   = explicit
ack_wait     = 2 x p99(handler latency), minimum 5s
max_deliver  = 5
backoff      = [1s, 5s, 30s, 2m, 10m]
```

After `max_deliver`, the message goes to `dlq.<subject>` with `dlq_reason` in the envelope and raises `evt.observability.alert.raised.v1`. It is never silently dropped. A DLQ landing on `TRADING` or `DECISION` pages immediately; `MARKET` and `OPS` raise a ticket.

---

## 7. What is deliberately not an event

Page 15 has no equivalent section, and its absence is why the catalog looks complete when it is not.

| Interaction | Primitive | Timeout | On timeout |
|---|---|---|---|
| Risk → Position Ledger snapshot | Sync query | 30ms | Reject the trade, fail closed |
| Risk → Kill switch interlock | In-process, last op before token issue | 10ms | HALT, fail closed |
| Execution → Instrument Master | Sync query, cached | 10ms | Reject the order |
| Execution → Broker | RPC | 300ms | `UNKNOWN` state, reconcile, never blind-retry |
| Committee desk → Claude API (via Gateway) | RPC | 8s | Desk abstains |
| Decision Saga → Risk preview | Sync query | 50ms | Proceed with `preview_unavailable=true` |
| Dashboard → any read model | Sync query | 2s | Stale-with-timestamp, never an infinite spinner |

> **The one-line rule:** if a wrong or missing answer costs money in the next 300ms, it is synchronous and fails closed. Otherwise it is an event.

---

## 8. What CI enforces

This is what turns page 15's two named failure modes (drift and orphan events) from documentation hazards into build failures. Six checks, all required per page 14's gate model:

1. A publish call whose subject is not in the registry fails the build.
2. A subject with a producer and no consumer fails the build (orphan event).
3. A subscribe to a subject with no producer fails the build (silent gap).
4. A schema change violating the compatibility table fails the build.
5. A subject name violating §2 fails the build.
6. A message type published without a declared `idempotency_key` derivation rule fails the build.

Once these exist, **this file is generated rather than written** (ADR-0040), and the drift failure mode is closed structurally rather than by discipline.

---

## 9. Related

- Source page, unmodified: `../15_Event_Catalog.md`
- `16_Container_Model_v2.md` — the container view these subjects flow between
- `../review/R01_Event_Architecture.md` — full envelope, idempotency, replay, DLQ, outbox derivation
- `../review/R03_Domain_Model_DDD.md` — the bounded contexts that define this namespace
- `../review/R07_State_Machines.md` — the sagas these messages drive
- `../decisions/0037-commands-and-events-are-distinct.md` — closes B1
- `../decisions/0040-schema-registry-is-the-wire-contract.md` — makes this file generated
- `../decisions/0004-nats-jetstream-as-event-backbone.md` — the streams in §6
- `../decisions/0038-transactional-outbox-is-mandatory.md` — how publishers avoid dual-write divergence
