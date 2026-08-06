# R12 — Observability

**Deliverable:** 12
**Delta against:** `00_Master_Architecture.md` (§8 Monitoring band), `13_Infrastructure_Platform.md`
**Status:** Review v1.0

---

## 1. Assessment

Page 00 gets three things right that are commonly wrong: monitoring is declared **cross-cutting** rather than a downstream stage, **alert fatigue** is named as a failure mode, and a **synthetic heartbeat** is proposed for the "monitoring is silently broken" case. That is a better starting position than most.

Four gaps:

| # | Gap | Consequence |
|---|---|---|
| O1 | The Journal (a legal and forensic record) is placed inside the observability stack | Audit truth sits in the same lossy, downsampled tier as Grafana metrics (finding D9) |
| O2 | No distributed tracing | An 11-second, 8-service decision path cannot be debugged. This is the single most valuable missing capability |
| O3 | No SLIs or SLOs. Latency budgets exist without percentiles | Nothing is measurable, so nothing can page correctly (finding D2) |
| O4 | Only technical signals. No trading-specific observability | The system can be perfectly healthy by every infrastructure metric while making consistently bad decisions |

O4 is the most important. A trading platform's most dangerous failures are silent: a model degrading, desks becoming correlated, slippage creeping up, the committee agreeing with the deterministic baseline 100% of the time. None of these produce an error, a latency spike, or a failed health check.

---

## 2. The four pillars, plus one

| Pillar | Question | Technology | Retention |
|---|---|---|---|
| **Metrics** | Is it healthy, and how healthy over time? | Prometheus + Grafana | 15d raw, 400d downsampled |
| **Logs** | What happened in this specific execution? | Structured JSON → Loki | 30d |
| **Traces** | Where did the time go across services? | OpenTelemetry → Tempo | 7d, 100% sampled on the decision path |
| **Audit** | What can we prove happened? | Decision Record Store (separate, R04 §10) | **Forever** |
| **Trading telemetry** | Are the decisions any good? | Purpose-built, in Postgres + Grafana | Forever |

**The separation of Audit from the other four is the structural correction.** Audit has different durability, different mutability, different retention, and different access control. Putting it in Loki or Prometheus, as page 00 implies, means the record you would need in a dispute is the one that got downsampled.

---

## 3. Metrics

### RED per service (request-driven)

| Metric | Labels |
|---|---|
| `witrade_requests_total` | `service`, `endpoint`, `status` |
| `witrade_request_duration_seconds` (histogram) | `service`, `endpoint` |
| `witrade_errors_total` | `service`, `endpoint`, `error_class` |

### USE per resource

`witrade_resource_utilisation`, `witrade_resource_saturation`, `witrade_resource_errors`, labelled by `resource` (cpu, memory, disk, connection_pool, nats_consumer).

### Event bus (absent from the ADD, and critical)

| Metric | Alert |
|---|---|
| `witrade_consumer_lag_messages{stream,durable}` | Lag on `TRADING`/`DECISION` > 10 for 30s → P1 |
| `witrade_consumer_ack_pending{stream,durable}` | Approaching `max_ack_pending` → P2 |
| `witrade_dlq_messages_total{subject}` | Any increase on `TRADING`/`DECISION` → **P0** |
| `witrade_redelivery_total{subject}` | Sustained redelivery → P1, indicates a poison message |
| `witrade_publish_failures_total{subject}` | Any → P1, indicates an outbox problem |
| `witrade_outbox_unpublished_age_seconds` | > 30s → **P0**. The outbox relay is stuck and state is diverging |

### Domain metrics per subsystem

| Subsystem | Metrics |
|---|---|
| Ingestion | `bars_ingested_total{source,symbol}`, `ingestion_lag_seconds`, `source_circuit_state`, `gap_bars_total` |
| Quality | `quality_score` (histogram), `datasets_routed_total{verdict}`, `detector_triggered_total{detector}`, `quarantine_open_count` |
| Features | `feature_materialisation_duration`, `feature_staleness_seconds{category}`, `feature_serving_cache_hit_ratio`, **`train_serve_skew_detected_total`** |
| Regime/Vol/Structure | `engine_compute_duration{engine}`, `model_convergence_failures_total`, `stale_output_served_total`, `regime_dwell_bars` |
| Committee | `cycles_total{outcome}`, `desk_latency_seconds{desk}`, `desk_abstain_total{desk,reason}`, `quorum_failures_total`, `deadlock_total{kind}`, `tokens_used_total{desk}`, `cost_usd_total` |
| Risk | `assessments_total{verdict}`, `rejections_total{rule}`, `limit_utilisation{limit}`, `killswitch_state{scope}`, `sizing_clamp_total{stage}` |
| Execution | `orders_total{state}`, `order_latency_seconds`, `slippage_bps` (histogram), `unknown_state_duration_seconds`, `leader_lease_held` |
| Ledger | `positions_open`, `reconciliation_breaks_total{severity}`, `projection_rebuild_duration`, `projection_divergence_detected_total` |
| OMS | `unmanaged_positions`, `positions_without_broker_stop`, `management_actions_total{action}` |

Three of these are worth calling out because they exist only as a result of this review and each catches a class of silent failure: `train_serve_skew_detected_total`, `positions_without_broker_stop`, and `outbox_unpublished_age_seconds`.

---

## 4. Trading-specific observability (the missing pillar)

These are the metrics that detect the failures that matter. None of them are infrastructure metrics.

### Decision quality

| Metric | Detects |
|---|---|
| `committee_baseline_agreement_ratio` | If it approaches 1.0, the LLM layer adds nothing. If it approaches 0.5, one of the two is noise (R09 §5) |
| `desk_brier_score{desk}` (weekly) | Calibration decay |
| `desk_resolution{desk}` (weekly) | A desk that does not discriminate. **The metric that answers whether six desks are better than three** |
| `desk_pairwise_agreement{a,b}` (weekly) | Page 08's collusion drift, now measured |
| `desk_expected_calibration_error{desk}` | Which desk needs prompt review |
| `red_team_overrule_outcome` | When the Red Team objected and was overruled, what happened |
| `conviction_vs_realised_r` (scatter) | The core calibration picture: does higher conviction actually produce better outcomes |

### Execution quality

| Metric | Detects |
|---|---|
| `implementation_shortfall_bps` | Total cost from decision price to fill price |
| `slippage_decomposed_bps{component}` | Spread vs delay vs impact. A rising delay component means the platform is getting slower, not the market worse |
| `fill_ratio` | Partial-fill frequency |
| `slippage_vs_model_ratio` | Realised versus the assumption used in sizing. Feeds back into sizing (R11 §8) |

### Model health

| Metric | Detects |
|---|---|
| `prediction_psi{model}` | Distribution shift versus training |
| `model_live_vs_backtest_delta{model}` | Degradation |
| `feature_drift_psi{feature}` | Which input is shifting |
| `models_degraded_count` | The correlated-degradation kill condition (R11 §6) |

### Portfolio and risk

`drawdown_from_peak`, `exposure_by_cluster`, `var_utilisation`, `cvar_utilisation`, `stress_scenario_worst_case`, `limit_headroom{limit}`, `rejected_trade_hypothetical_pnl` (R11 §12, the metric that tells you whether the limits are well-calibrated).

---

## 5. Logging

**Structured JSON only.** Every log line carries: `timestamp`, `level`, `service`, `version`, `env`, `correlation_id`, `causation_id`, `trace_id`, `span_id`, and the domain identifiers in scope (`cycle_id`, `decision_id`, `order_id`, `account_id`).

`correlation_id` on every line is what makes "show me everything that happened for this decision, across eight services" a single query. Without it, debugging an 11-second multi-service path means manual timestamp correlation, which does not work.

### Level discipline

| Level | Use | Alertable |
|---|---|---|
| `ERROR` | An operation failed and could not be recovered | Yes |
| `WARN` | Degraded but handled. A fallback engaged | Trended, not paged |
| `INFO` | State transitions, decisions, business events | No |
| `DEBUG` | Off in production. Enableable per service per correlation ID | No |

**Rule: no `ERROR` without an actionable response.** A log line that says something is broken but which nobody can act on trains the operator to ignore ERROR, which is alert fatigue arriving through the log channel.

**Redaction:** a filter that pattern-matches secret shapes and **fails loudly** on a match rather than silently redacting. Silent redaction hides the fact that a code path tried to log a credential.

---

## 6. Distributed tracing (O2)

The highest-value missing capability.

### Trace boundaries

One trace per **decision cycle**, from trigger to fill. Spans:

```
decision_cycle (root, correlation_id = trace_id)
├── admission_control
├── evidence_assembly
│   ├── fetch_regime, fetch_volatility, fetch_structure, fetch_prediction
│   ├── fetch_portfolio_snapshot
│   ├── build_graph, seal_graph
├── desk_polling
│   ├── desk.regime → llm_gateway → anthropic_api (external span)
│   ├── desk.smc, desk.volatility, desk.macro,
│   │   desk.positioning, desk.microstructure  (parallel)
│   ├── citation_validation, quorum_check
├── calibration, red_team, consensus_pooling, cro_gate
├── risk_preview
├── risk_decide
│   ├── ledger_snapshot_query
│   ├── rule_chain (span per rule)
│   ├── sizing_chain
│   ├── killswitch_check (3 tier spans)
│   └── token_issuance
└── execution
    ├── lease_check, token_validation, staleness_gate
    ├── broker_place_order (external span)
    └── fill_analysis
```

**Sampling:** 100% on the decision path. Volume is hundreds of traces per day, not millions. Sampling here to save cost would be saving nothing and losing everything.

**Propagation:** W3C `traceparent` in the event envelope (R01 §4), so the trace survives every async hop. This is why the envelope field is mandatory rather than optional.

### What tracing immediately answers

- Where did the 11 seconds actually go? (Almost certainly desk polling, but "almost certainly" is not a number.)
- Which desk is the straggler forcing the deadline?
- Is the ledger query on the critical path adding latency under load?
- Did the kill-switch check actually run, and in what order relative to token issuance?

That last one is a correctness question that tracing answers structurally. A span ordering assertion in a test is a real way to enforce "no await between the kill-switch check and issuance."

---

## 7. Health checks

Three distinct kinds, commonly conflated into one endpoint.

| Endpoint | Question | Failure action |
|---|---|---|
| `/health/live` | Is the process alive? | Restart the container |
| `/health/ready` | Can it serve traffic? Dependencies reachable, caches warm, projections rebuilt | Remove from routing. Do not restart |
| `/health/startup` | Has initialisation completed? | Extend the grace period |

**Plus a platform-level readiness endpoint** on the Supervisor that aggregates: are all Tier-0 dependencies healthy, is reconciliation clean, is the ledger projection current, is the leader lease held, is the calendar coverage sufficient, is the kill switch readable on all three tiers. This is the endpoint that gates entry into `NORMAL` (R07 §2).

**Synthetic transactions** (extending page 00's heartbeat idea):

| Probe | Frequency | Alert |
|---|---|---|
| Synthetic decision cycle in `sim` env, end to end, asserting the expected outcome | Every 15 min | Failure → P1. Proves the whole path works, not just each service |
| Broker connectivity probe (read-only account query) | Every 30s | Failure → P0 with open positions |
| Dead-man's switch: platform heartbeat during market hours | Every 5 min | Absence → **P0**. Catches the case where everything is silently dead |

The dead-man's switch is the one that catches total failure. Every other alert requires something to be running in order to fire.

---

## 8. SLIs and SLOs (O3)

Latency budgets without percentiles are unmeasurable. Restated properly, with an explicit error budget.

| # | SLI | SLO | Budget |
|---|---|---|---|
| S1 | **Order placement correctness**: authorisations issued with a complete assessment | **100%** | Zero. Any violation is an incident |
| S2 | **No duplicate orders**: distinct `client_order_id` per intended order | **100%** | Zero |
| S3 | **Kill switch effectiveness**: orders sent while any tier reports HALTED | **0** | Zero |
| S4 | **Position protection**: open positions with a broker-side stop | **100%**, measured every 60s | Zero |
| S5 | Reconciliation freshness: critical breaks open > 5 min | **0** | Zero |
| S6 | Decision path latency: bar close to authorisation | p95 < 10s, p99 < 12s | 5% of cycles |
| S7 | Risk decision latency | p99 < 100ms | 1% |
| S8 | Order submission latency: command to broker ack | p99 < 300ms | 1% |
| S9 | Feature serving latency | p99 < 50ms | 1% |
| S10 | Data freshness: bar close to feature availability | p99 < 250ms | 1% |
| S11 | Ingestion completeness: expected bars actually ingested | > 99.9% per day | 0.1% |
| S12 | Committee availability: cycles that complete without infrastructure failure | > 99% | 1% |
| S13 | Platform availability during market hours (able to trade if signalled) | > 99.5% | ~3.5h/month |

**S1 through S5 are correctness SLOs with zero error budget.** This is the important structural point: they are not performance targets to be traded off. A latency SLO breach degrades the service; a correctness SLO breach loses money. Mixing them in one table with one alerting policy is how the second gets treated like the first.

**Error budget policy:** if the S6 to S13 budget is exhausted in a month, feature work stops and reliability work takes priority until the budget recovers. Stated in advance so it is not negotiated during the incident.

---

## 9. Alerting

Tiers per R04 §11. The routing rules that matter:

### The five P0s

1. Kill switch tripped (any scope)
2. Order in `UNKNOWN` state > 60 seconds
3. Reconciliation critical break
4. Any position without a broker-side stop
5. Dead-man's switch silence during market hours

Every one of these has a defined runbook and an unambiguous first action. Nothing else is a P0. Keeping this list at five is what preserves its meaning.

### Anti-fatigue mechanisms (operationalising page 00's stated concern)

| Mechanism | Effect |
|---|---|
| **Every alert has a runbook link in the payload** | Removes the "what do I do" latency that makes alerts feel useless |
| **Symptom-based, not cause-based** | Alert on "no bars ingested for 5 minutes", not on "the Polygon connection object is null". One symptom alert replaces twenty cause alerts |
| **Deduplication by fingerprint** | One root cause produces one alert, not forty |
| **Inhibition rules** | A platform HALTED alert suppresses every downstream alert it causes |
| **Auto-resolve** | An alert that clears itself resolves itself, and the resolution is visible |
| **Monthly alert review** | Every alert that fired: was it actionable? Non-actionable alerts are deleted, not tuned. Deletion is the right response and it is the one nobody takes |

The last row is the actual fix for alert fatigue. Tuning a useless alert to fire less often preserves it; deleting it removes the noise permanently.

---

## 10. Dashboards

Five, each for one audience and one question. A dashboard with no question is a wall of graphs nobody reads.

| Dashboard | Question | Key panels |
|---|---|---|
| **Trading Now** | Is it working right now? | Platform mode, kill-switch state per scope, open positions with P&L and protection status, today's decisions with outcomes, drawdown vs ladder, next scheduled event |
| **Decision Quality** | Are the decisions good? | Conviction vs realised R scatter, per-desk calibration curves, deadlock and quorum-failure rates, baseline-agreement ratio, Red Team overrule outcomes |
| **Execution Quality** | Are we getting good fills? | Slippage distribution and decomposition, implementation shortfall trend, fill ratios, realised vs modelled slippage |
| **System Health** | Is the infrastructure healthy? | RED per service, consumer lag, DLQ depth, outbox age, error budget burn-down per SLO |
| **Risk** | How much risk are we carrying? | Exposure by cluster, limit headroom, VaR/CVaR utilisation, stress scenario results, rejection analysis |

**Trading Now must be readable in five seconds on a phone.** During an incident, that is the constraint that matters.

---

## 11. Incident response

### Severity

| Sev | Definition | Response | Post-mortem |
|---|---|---|---|
| **SEV1** | Capital at risk or lost. Duplicate orders, unprotected positions, kill switch failed | Immediate, halt first and investigate second | Mandatory, blameless, within 48h |
| **SEV2** | Trading impaired but capital safe. Committee down, broker disconnected with flat book | Within 15 min | Mandatory |
| **SEV3** | Degraded, no trading impact. A data source down with fallback working | Next business day | Optional |
| **SEV4** | Cosmetic | Backlog | No |

### The universal first action for SEV1

```
1. HALT. Trip the kill switch. Do not investigate first.
2. Verify positions at the broker terminal DIRECTLY, not through the platform.
3. Verify every open position has a stop, manually if necessary.
4. Only then begin investigation.
```

This ordering is deliberate and should be written on the runbook. The instinct under pressure is to diagnose before halting, and halting is nearly free while diagnosing while exposed is not.

### Runbooks

One per P0, structured identically: symptoms, immediate action, diagnosis steps with the exact commands, resolution, rollback, escalation, and post-incident checklist. Linked from the alert payload. Tested quarterly by executing them in `sim` against an injected fault, because an untested runbook is a document, not a procedure.

---

## 12. Audit trail (O1)

Fully specified in R04 §10. Restated here as the boundary:

**The Journal is not observability.** It is the Decision Record Store: append-only, hash-chained, object-locked, retained forever, with its own access control and its own restore procedure. Page 00's Monitoring band should keep logs, metrics, traces and alerts, and hand the Journal to a separate service.

Test of correctness: if the entire observability stack were deleted, the platform's legal and forensic record must be intact. Under page 13's current design it would not be.

---

## 13. Related

- `R00_Executive_Review.md` (D2, D9)
- `R01_Event_Architecture.md` (envelope carries the correlation and trace fields)
- `R04_Platform_Services.md` (PS-09 Audit, PS-10 Notification)
- `R17_Performance.md` (latency budgets these SLOs measure)
- Source: `../00_Master_Architecture.md` §8
