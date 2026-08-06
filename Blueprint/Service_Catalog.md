# Service Catalog

**Blueprint deliverable:** B.3
**Canonical source for Purpose / Failure Modes / Recovery Strategy / Latency Budget:** the cited `../Architecture/` page or contract, per service. This catalog does not restate that content — see `../Architecture/freeze/Canonical_Source_Validation.md` for why. What this catalog adds that `../Architecture/` does not yet state: **Deployment Model, Scaling Strategy, Health Checks, Metrics, Logging, Tracing** — genuinely implementation-level facts.
**Status:** Blueprint v1.0, 2026-08-04

---

## 1. Cross-cutting policy (applies identically to all 40 services, stated once)

| Concern | Standard, every service |
|---|---|
| **Health checks** | `GET /healthz` (liveness: process is up) and `GET /readyz` (readiness: dependencies reachable, per that service's own Degraded Mode table) — both required, both wired into the Platform Supervisor's (C26) mode computation |
| **Metrics** | Prometheus `/metrics` endpoint. Every service emits the four golden signals (latency, traffic, errors, saturation) plus its own domain SLI named in its `../Architecture/` page's Latency Budget / SLO field |
| **Logging** | Structured JSON via `packages/observability`, one schema, `correlation_id` and `causation_id` on every line (ADR-0037's envelope fields, propagated into logs) |
| **Tracing** | OpenTelemetry, one trace per deliberation cycle / order lifecycle / rebalance tick, span per service hop — this is what makes the end-to-end budget (`../Architecture/review/R00_Executive_Review.md` D3, the 11.2s bar-close-to-ack chain) actually measurable rather than asserted |
| **Deployment model** | Docker Compose service (ADR-0008), one container image per service, health-checked before the Platform Supervisor reports `NORMAL` |
| **Config** | Typed, validated at startup (Pydantic), no untyped env var read anywhere outside `config.py` |

**Scaling strategy is stated per service below because it genuinely differs** (a stateless HTTP service scales differently from a single-leader-lease Execution service).

---

## 2. Edge group — C01-C05

| Container | Purpose (1 line, full detail: cited page) | Tech | Scaling strategy | SLO source |
|---|---|---|---|---|
| C01 Market Data Ingestion | Ingest and normalise every external feed (`../Architecture/01_Data_Ingestion.md`) | Python asyncio | Horizontal, one process per source adapter, stateless | Page 01 Latency Budget |
| C02 Untrusted Text ACL | Prose to typed features, closes B5 (`../Architecture/review/R03` §9 ACL-2) | Python, constrained LLM call | Horizontal, stateless, rate-limited by the Cost Governor (C30) | `../Architecture/21_Security_Architecture.md` T2 |
| C03 Data Quality Engine | Score every dataset (`../Architecture/02_Data_Quality_Engine.md`) | Python | Horizontal, stateless | Page 02 |
| C04 Instrument & Reference Data Master | Contract specs, calendar, clusters (`../Architecture/review/R19` §4) | Python + Postgres | Single writer, read replicas for scale (Tier 0, low write volume) | R19 §4 |
| C05 Clock | Injected library, not a deployed service | Python | N/A — imported, not deployed | ADR-0035 |

## 3. Data group — C06-C08

| Container | Purpose | Tech | Scaling strategy | SLO source |
|---|---|---|---|---|
| C06 Feature Materialiser | Offline batch write (`../Architecture/03_Feature_Store.md`) | Python + Iceberg writer | Horizontal by symbol/timeframe partition | Page 03 |
| C07 Feature Serving | Online read (`../Architecture/03_Feature_Store.md`) | Python + Redis | Horizontal, stateless, Redis as the shared cache | Page 03 |
| C08 Lakehouse | Storage, not a service | Iceberg on MinIO, DuckDB embedded per consumer | Storage scales independently; DuckDB is embedded, not shared | ADR-0003 |

## 4. Quant group — C09-C14, C28

| Container | Purpose | Tech | Scaling strategy | SLO source |
|---|---|---|---|---|
| C09 Regime Engine | `../Architecture/04_Regime_Engine.md` | Python `arch`, `hmmlearn` | Horizontal by symbol | Page 04 |
| C10 Volatility Engine | `../Architecture/05_Volatility_Engine.md` | Python `arch`, `scipy` | Horizontal by symbol | Page 05 |
| C11 Market Structure Engine | `../Architecture/06_Market_Structure_Engine.md` | Python `smartmoneyconcepts` | Horizontal by symbol | Page 06 |
| C12 Model Training | `../Architecture/07_ML_RL_Model_Layer.md` | Python, MLflow | Batch/scheduled, not latency-sensitive, single worker per training run | Page 07 |
| C13 Model Inference | `../Architecture/07_ML_RL_Model_Layer.md` | Python, MLflow artefacts | Horizontal, stateless, model artefact cached per replica | Page 07 |
| C14 Model Monitor | `../Architecture/20_Model_Registry.md` §3 | Python | Single instance, continuous polling loop | Page 20 |
| C28 Simulation & Replay Harness | `../Architecture/review/R19` §2 | Python | On-demand, one run per invocation, not resident | R19 §2 |

## 5. Decision group — C15-C20, C27, C30, C40

| Container | Purpose | Tech | Scaling strategy | SLO source |
|---|---|---|---|---|
| C15 Evidence Graph | `../Architecture/17_Evidence_Graph.md` | Python `networkx`, Postgres, MinIO | Horizontal, stateless per cycle | Page 17 |
| C16 Committee | `../Architecture/08_AI_Investment_Committee.md` | Python orchestrating 6 parallel LLM calls | Horizontal, stateless orchestrator | Page 08 |
| C17 LLM Gateway | `../Architecture/review/R19` §8 | Python, FastAPI + Redis + Postgres | Horizontal, stateless, budget state in Redis | R19 §9 |
| C18 Prompt & Policy Registry | `../Architecture/20_Model_Registry.md` | Postgres + MinIO | Single writer, cached reads | Page 20 |
| C19 Decision Saga | `../Architecture/09_Decision_Intelligence_Layer.md` | Python + Postgres | Horizontal, saga state in Postgres, idempotent steps | Page 09 |
| C20 Decision Record Store | `../Architecture/review/R19` §7 | Postgres + MinIO, append-only | Single writer (append-only, hash-chained — cannot shard without breaking the chain) | R19 §7 |
| C27 Continuous Learning | `../Architecture/12_Continuous_Learning.md` | Python, pandas, MLflow | Scheduled, weekly, single worker | Page 12 |
| C30 Cost Governor | `../Architecture/review/R19` §13 | Python + Redis | Single instance (admission control needs one source of truth for budget state) | R19 |
| **C40 Portfolio Construction Engine** | `../Architecture/18_Portfolio_Construction.md` | Python + Redis + Postgres | **Single instance per account** — the candidate pool is a shared, consistent view; horizontal replicas would need to coordinate on the pool, which the design deliberately avoids by keeping it single-writer | Page 18 |

## 6. Capital group — C21-C23, C25-C26

| Container | Purpose | Tech | Scaling strategy | SLO source |
|---|---|---|---|---|
| C21 Risk Engine | `../Architecture/10_Risk_Portfolio_Platform.md` | Python + Redis + Postgres | **Single leader**, standby with lease (a second live evaluator risks two different verdicts on the same proposal) | Page 10, Tier 0 |
| C22 Account & Position Ledger | `../Architecture/review/R19` §5 | Python, event-sourced, Postgres | Single writer per account (event-sourcing requires ordered append) | R19 §5, Tier 0 |
| C23 OMS | `../Architecture/review/R19` §3 | Python + Postgres | Single leader per account, standby with lease | R19 §3, Tier 0 |
| C25 Reconciliation | `../Architecture/review/R19` §6 | Python | Scheduled + event-triggered, single instance | R19 §6, Tier 0 |
| C26 Platform Supervisor | `../Architecture/review/R19` §6 | Python | **Single instance, no exceptions** — it is the one source of truth for platform mode | R19, Tier 0 |

## 7. Bridge group — C24

| Container | Purpose | Tech | Scaling strategy | SLO source |
|---|---|---|---|---|
| C24 Execution Service | `../Architecture/11_Execution_Platform.md` | Python + MT5 bridge | **Active/standby, leader lease, Windows VPS** — never two active writers to the broker | Page 11, Tier 0 |

## 8. Platform group — C31-C39

| Container | Purpose | Tech | Scaling strategy | SLO source |
|---|---|---|---|---|
| C31 Observability Stack | `../Architecture/13_Infrastructure_Platform.md` | Prometheus, Grafana, Loki, Tempo | Standard HA pattern for each component, out of the box | `../Architecture/review/R12` |
| C32 API Gateway / BFF | `../Architecture/review/R19` §13 | FastAPI | Horizontal, stateless | R19 |
| C33 Dashboard | `../Architecture/00_Master_Architecture.md` | Next.js | Horizontal, stateless, static-friendly | Page 00 |
| C34 Ops CLI | `../Architecture/00_Master_Architecture.md` | Python typer | N/A — client tool, not deployed | Page 00 |
| C35 Scheduler | `../Architecture/00_Master_Architecture.md` | Python + NATS | Single instance (cron-style triggers need one source) | Page 00 |
| C36 Event Bus | `../Architecture/decisions/0004-nats-jetstream-as-event-backbone.md` | NATS JetStream | Clustered, min 3 nodes (ADR-0004) | Page 00, Tier 0 |
| C37 Schema Registry | `../Architecture/review/R19` §11 | Git + small read service | Horizontal read replicas, single write path (CI-gated) | R19 §11 |
| C38 Secrets Manager | `../Architecture/21_Security_Architecture.md` §4 | Vault or SOPS+age | Standard HA per chosen tool | Security page, Tier 0 |
| C39 Identity Provider | `../Architecture/19_Bounded_Context_Map.md` BC11 | OIDC | Standard HA per chosen tool | BC11 spec |

---

## 9. Failure-mode and recovery cross-reference

Every service's Failure Modes and Recovery Strategy are defined once, in its `../Architecture/` page or contract, and are not restated here — restating them in a second file is exactly the duplication `../Architecture/freeze/Canonical_Source_Validation.md` checks against. This catalog's `SLO source` column is the pointer.

---

## 10. Related

- `Package_Blueprint.md` — the code-level structure inside each service listed here
- `Deployment_Blueprint.md` — how these services are actually brought up, per environment
- `../Architecture/generated/16_Container_Model_v2.md` — the canonical 40-container source this catalog is an implementation-facing view of
- `Observability_Blueprint.md` — the full detail behind §1's metrics/logging/tracing row
