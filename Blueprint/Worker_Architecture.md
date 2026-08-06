# Worker Architecture

**Blueprint deliverable:** B.8
**Scope:** every background, non-request-driven process in the platform — scheduled, event-triggered, or long-running.
**Status:** Blueprint v1.0, 2026-08-04
**Amended:** 2026-08-06 — the kill-switch self-halt heartbeat (`../Architecture/decisions/0018-kill-switch-three-tier-fail-closed-interlock.md`) was specified at the Architecture layer but dropped in this Blueprint's original translation. Restored here per [ADR-0044](../Architecture/decisions/0044-kill-switch-recheck-at-broker-send.md), found by an independent pre-implementation review.

---

## 1. Worker inventory

| Worker | Trigger | Owning service | Queue/schedule | Failure behaviour |
|---|---|---|---|---|
| **Data Ingestion** | Continuous (streaming) + scheduled backfill | `edge/ingestion` (C01) | NATS consumer on vendor webhooks/polling; backfill via Scheduler (C35) cron | Per-source circuit breaker (SM-7, `review/R07` §8); other sources unaffected |
| **Feature Generation** | Event-triggered (`evt.data_quality.scored`) | `data/feature_store` (C06) | NATS consumer, `MARKET` stream | Stale feature served, marked, downstream discounts (page 17 §"weighting") |
| **Evidence Aggregation** | Event-triggered (any of 4 quant engines publishing) | `decision/evidence_graph` (C15) | NATS consumer, admission-controlled (`review/R17` §6) | Cycle aborts `NO_ACTION`, never a partial graph (page 17 Degraded Mode) |
| **Model Training** | Scheduled (weekly) + event-triggered (drift detected) | `quant/model_training` (C12) | Scheduler (C35) cron + `evt.model.drift_detected` consumer | Training failure → `TRAINING_FAILED` state (SM-5), champion unaffected |
| **Backtesting** | On-demand (CLI/API invoked) | `quant/simulation_harness` (C28) | Not queued — synchronous long-running job with a job ID, polled | No partial results — a crashed run is discarded, not resumed (determinism requires a clean run) |
| **Optimization (ranking/desk weights)** | Weekly, as part of Continuous Learning | `decision/learning` (C27) | Scheduler (C35) cron | PBO/DSR-gated proposal, never auto-applied (ADR consistent with page 07/08/18's shared discipline) |
| **Notifications** | Event-triggered (any P0/P1 alert) | `platform/observability` (C31) | NATS consumer, `evt.observability.alert.raised` | Tiered: page vs Slack vs dashboard-only (`review/R12` §"Recovery Strategy") |
| **Monitoring (health aggregation)** | Continuous polling, 1s interval | `platform/supervisor` (C26) | In-process loop, not a queue | Missing heartbeat beyond threshold → mode degrades (SM-1) |
| **Cleanup (retention enforcement)** | Scheduled, daily | `platform/scheduler` (C35) | Cron | Per-stream retention policy already declared (`../Architecture/generated/15` §6) — this worker enforces what NATS's own retention doesn't cover (Postgres table pruning, MinIO lifecycle rules) |
| **Event Replay** | On-demand | `quant/simulation_harness` (C28) | Same as Backtesting | `env=sim` interlock hard-enforced; a mismatch halts the run, never silently proceeds |
| **Health Monitoring (synthetic transactions)** | Scheduled, every 60s | `platform/observability` (C31) | Cron | A synthetic transaction that doesn't complete pages, same severity as a real failure |
| **Reconciliation** | Scheduled (every N minutes) + event-triggered (`evt.execution.broker.reconnected`) | `capital/reconciliation` (C25) | Cron + NATS consumer | Break detected → `evt.reconciliation.break_detected`, Risk auto-trips kill switch on critical breaks |
| **Model Monitor** | Continuous polling | `quant/model_monitor` (C14) | In-process loop against live inference outcomes | Correlated degradation → platform-scope kill switch (page 20 §3) |
| **Cost Governor admission control** | Every LLM/data-vendor call | `decision/cost_governor` (C30) | In-process gate, not a background worker — listed for completeness since `review/R19` names it alongside the others | Budget exceeded → call blocked before it happens, not billed then regretted |
| **Kill-switch self-halt heartbeat** | Continuous, in-process timer | **Every order-capable process: `risk/authorisation` (C21) and `bridge/execution` (C24)** | In-process loop, not a queue — tracks age of the last successful full-tier (T1+T2+T3) kill-switch read | Age > **10 seconds** since last successful full-tier read → the process halts itself unconditionally, independent of any shared component being reachable (ADR-0018 §"Self-halt heartbeat", restored by ADR-0044). This is the control that makes the switch robust to a network partition; a process that cannot be reached cannot be told to stop and must decide to |

## 2. Queue design

Every event-triggered worker is a NATS JetStream durable consumer (`Event_Blueprint.md` §3) — there is no separate queueing technology (no Celery, no RQ, no SQS). This is a direct consequence of ADR-0004: introducing a second queue technology alongside JetStream would duplicate the ack/retry/DLQ machinery `../Architecture/generated/15` §6 already specifies once. Scheduled workers use the Scheduler (C35), which itself publishes `cmd.<target_context>.run_job.v1` commands onto the `CONTROL` stream — a scheduled job and an event-triggered job are the same consumer shape from the worker's point of view; only the trigger differs.

## 3. Ownership

Every worker is owned by exactly the bounded context whose data it touches (Package_Blueprint.md §2's dependency rule 2 applies to workers identically to request-handling code — a worker never reaches into another context's tables). No shared "worker pool" service exists; each worker lives inside its owning service's package.

## 4. Scaling

| Worker class | Scaling |
|---|---|
| Stateless, high-volume (Ingestion, Feature Generation) | Horizontal, NATS queue groups distribute load |
| Single-writer, ordering-sensitive (Reconciliation, Model Monitor, Cost Governor) | Single instance, matching their owning service's scaling strategy in `Service_Catalog.md` |
| On-demand, resource-heavy (Backtesting, Model Training) | One job per invocation, no persistent pool — scaled by job queue depth, not replica count |

---

## 5. Related

- `Service_Catalog.md` — the services each worker lives inside
- `Event_Blueprint.md` §3 — the consumer interface every event-triggered worker implements
- `../Architecture/review/R19_Missing_Components.md` §2 — the Simulation Harness this document's Backtesting/Replay rows are grounded in
