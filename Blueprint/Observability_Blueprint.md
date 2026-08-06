# Observability Blueprint

**Blueprint deliverable:** B.11
**Canonical source, not duplicated:** `../Architecture/review/R12_Observability.md` (metrics, logs, traces, SLIs/SLOs, incident response for pages 00-16) and `../Architecture/13_Infrastructure_Platform.md`. This document is the implementation-level realisation, extended per `../Architecture/freeze/Architecture_Audit_Report.md` §6's disclosed gap: Phase 11's own two new metrics (`graph_committee_divergence`, correlated-degradation trigger) had no dashboard/alert spec until now.
**Status:** Blueprint v1.0, 2026-08-04

---

## 1. Logging

Implementation of `Service_Catalog.md` §1's cross-cutting policy: `packages/observability` provides one `get_logger()` call, every service uses it, structured JSON, `correlation_id`/`causation_id` on every line, shipped to Loki. No service configures its own logging independently — a service that does is a code-review rejection.

## 2. Metrics

Every SLO named in every `../Architecture/` page and contract becomes a Prometheus metric, exported by `packages/observability`'s standard exporter. The naming convention: `witrade_{bounded_context}_{metric}_{unit}`, e.g. `witrade_risk_evaluate_latency_seconds`, `witrade_evidence_graph_assembly_latency_seconds`.

### 2.1 The 17 tripwire metrics (from `../Architecture/decisions/README.md`), instrumented

| Metric | ADR | Threshold | Dashboard panel |
|---|---|---|---|
| `preview_decide_divergence_rate` | 0011 | >10% sustained | Risk dashboard |
| `portfolio_projection_lag_seconds` | 0012 | p99 >2s sustained | Portfolio dashboard |
| `desk_schema_violation_rate` | 0013 | >2% per model version | Committee dashboard |
| Spurious kill-switch halts/month | 0018 | >2 | Risk dashboard, P1 |
| Fail-closed halts/month (infra-caused) | 0025 | >4 | Platform dashboard |
| `UNPROTECTED` position duration | 0022 | any >60s | Position dashboard, P0 |
| Deadlock rate | 0021 | >40% sustained | Committee dashboard |
| `QUORUM_NOT_MET` rate | 0021 | >5% | Committee dashboard |
| Pairwise desk agreement | 0026 | >90% | Committee dashboard |
| Per-desk resolution | 0028 | near-zero | Committee dashboard |
| Committee vs baseline on disagreements | 0027 | no edge over 200 decisions | Committee dashboard |
| `outbox_unpublished_age_seconds` | 0038 | p99 >5s | Platform dashboard |
| p99 order path latency vs budget | 0001 | >50% | Execution dashboard |
| Sustained tick throughput | 0004 | >50k msg/s | Platform dashboard |
| **`graph_committee_divergence`** | **0041** | absent from metrics for >1 quarter post-go-live | **Evidence Graph dashboard — new, Phase 11** |
| **Tier-0 promotions missing second confirmation** | **0042** | any occurrence | **Model Registry dashboard — new, Phase 11, P0** |
| **BC12 admits nothing over 12 months** | **0043** | signal to promote cross-strategy allocation | **Portfolio Construction dashboard — new, Phase 11** |

**This is the closure of the exact gap `../Architecture/freeze/Architecture_Audit_Report.md` §6 disclosed:** the three Phase 11 metrics now have a named dashboard panel each, not just a name in an ADR.

## 3. Tracing

OpenTelemetry, one trace per deliberation cycle / order lifecycle / rebalance tick (`Event_Blueprint.md` §"Monitoring hooks" references this). Trace ID equals `correlation_id` from the event envelope — no separate trace-ID scheme, so a log line, a metric label, and a trace span are all joinable on the same identifier.

## 4. Dashboards

| Dashboard | Audience | Key panels |
|---|---|---|
| Platform | Operator | Mode (SM-1), circuit breaker states, outbox lag, event throughput |
| Risk | Operator, auditor | Exposure by symbol/cluster, drawdown ladder position, VaR/CVaR vs limit, kill-switch state, `preview_decide_divergence_rate` |
| Committee | Operator | Desk agreement, deadlock rate, quorum rate, per-desk resolution, `graph_committee_divergence` |
| Portfolio Construction | Operator | Live `PortfolioAllocationPlan`, admitted/deferred/rejected rates, opportunity-cost log |
| Model Registry | Operator | SM-5 state per slot, shadow comparison in flight, Tier-0 promotion audit |
| Execution | Operator | Order path latency, slippage decomposition (TCA), fill rate |
| Position | Operator, auditor | `UNPROTECTED` duration (P0 alert source), open position list |

## 5. Alerts

Tiered exactly as `../Architecture/review/R12_Observability.md` specifies (page vs Slack vs dashboard-only). This document adds the Phase 11-specific routing:

| Alert | Tier | Route |
|---|---|---|
| `UNPROTECTED` position >60s | P0 | Page |
| Tier-0 model/prompt promotion missing second confirmation | P0 | Page |
| Correlated model degradation (2+ slots) | P0 | Page — this is the kill-switch trigger itself, so the alert and the action are simultaneous |
| `graph_committee_divergence` absent from metrics | P2 | Ticket, quarterly review item |
| BC12 candidate deferred/rejected rate anomaly | P2 | Dashboard-only, weekly review input |

## 6. Runbooks

One runbook per P0/P1 alert, stored alongside the alert definition (not in a separate wiki that drifts) — `infra/runbooks/{alert_name}.md`, linked directly from the Grafana alert annotation. Every runbook follows one shape: Detect → Verify → Contain → Resolve → Post-mortem trigger, matching `../Architecture/review/R15_Security.md` §11's incident-response ordering for the security-specific case and generalised here for every P0/P1.

## 7. Incident response

Extends `../Architecture/review/R12_Observability.md` and `../Architecture/review/R15_Security.md` §11 without duplicating either — this document's only addition is the runbook-storage convention in §6, which neither source specifies at the file-path level.

## 8. Health monitoring

Implementation of `Service_Catalog.md` §1's `/healthz`/`/readyz` convention, aggregated by the Platform Supervisor (C26) into the platform mode state machine (SM-1) — a service's own health check is a local fact, the Supervisor's mode computation is the platform-wide consequence.

---

## 9. Related

- `../Architecture/review/R12_Observability.md` — the canonical observability design this blueprint implements
- `../Architecture/decisions/README.md` — the tripwire metrics table §2.1 instruments
- `../Architecture/freeze/Architecture_Audit_Report.md` §6 — the disclosed gap §2.1 and §5 close
- `Service_Catalog.md` §1 — the cross-cutting health/metrics/logging/tracing policy this document details
