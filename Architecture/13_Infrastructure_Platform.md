# 13 — Infrastructure Platform

**Diagram:** `13_Infrastructure_Platform.excalidraw`
**Phase:** 9 — Infrastructure
**C4 Level:** L2 — Container
**Depends on:** `00_Master_Architecture.md` (this page is a cross-cutting index into every layer, not a linear continuation of page 12)
**Status:** Draft

---

## Purpose

Answer "which service backs which subsystem" in one place, so infrastructure choices aren't re-decided piecemeal across pages 01-12. Every technology named in an earlier page's "Technology" section traces back to a box here.

## Responsibilities

Provide the shared infrastructure substrate — compute, messaging, storage, ML tracking, observability, and CI/CD — that every functional layer (pages 01-12) runs on top of.

## Infrastructure Map

| Category | Technology | Backs |
|---|---|---|
| Compute / API | FastAPI | Every Python service's HTTP/API surface (Data Platform, Quant engines, Committee desks, Risk, Execution) |
| Compute / API | Docker | Container runtime for all services — the unit of deployment referenced in page 14 |
| Messaging | NATS (JetStream) | The Event Bus itself — page 00's Orchestration Layer; JetStream persistence so in-flight events survive a node failure |
| Data Storage | DuckDB | Query layer over Parquet — pages 01 (Ingestion), 03 (Feature Store) |
| Data Storage | Postgres | Durable ledgers — Risk Management's ledger (page 10), Execution's Journal (page 11), Data Quality's quarantine table (page 02) |
| Data Storage | MinIO | S3-compatible object storage — Parquet files, MLflow model artifacts |
| ML Ops | MLflow | Model registry and experiment tracking — page 07's promotion gate, and reproducibility tracking for pages 04/05's fitted GARCH/HMM parameters |
| Observability | Prometheus | Metrics scrape target for every service — feeds page 00's Monitoring & Observability band |
| Observability | Grafana | Dashboards over Prometheus metrics — what the Operator (page 00) actually looks at |
| CI/CD | GitHub Actions | Build, test, deploy pipeline — page 14 |

## Inputs

None functionally — this is infrastructure, not a data-flow stage. Every other page is this page's "input" in the sense that their technology choices are what populate this map.

## Outputs

A shared substrate every functional layer runs on. No direct data output of its own.

## Dependencies

None — this is the foundation layer, alongside the Orchestration Layer (page 00) which it hosts (NATS).

## Events Published / Consumed

Not applicable at this page's level — infrastructure doesn't participate in the platform's event schema, it carries it (NATS) or stores it (Postgres/DuckDB/MinIO).

## Failure Modes

- **Single point of failure in shared infra** — NATS or Postgres going down has platform-wide blast radius, disproportionate to any single functional layer's own failure modes.
- **Storage tier confusion** — a service writes durable state to DuckDB (meant for queryable analytical data) instead of Postgres (meant for transactional ledgers), or vice versa, because the boundary wasn't clear.
- **Metrics blind spot** — a new service ships without wiring into Prometheus, so it's invisible to Monitoring until something breaks.

## Recovery Strategy

- NATS runs clustered (minimum 3 nodes) with JetStream persistence, per page 00's Orchestration Layer recovery strategy — this page doesn't duplicate that detail, just confirms the technology choice.
- Storage tier boundary is explicit and documented here as the canonical reference: **Postgres = transactional/durable ledgers requiring ACID guarantees** (Risk ledger, Journal, quarantine table). **DuckDB/Parquet = analytical/queryable bulk data** (bars, features). **MinIO = blob/artifact storage** (raw Parquet files at rest, MLflow artifacts). A new component's storage choice should map to one of these three, not invent a fourth pattern.
- New service checklist (referenced by page 14's CI/CD pipeline) includes a mandatory Prometheus scrape endpoint before a service is considered deployable — this is enforced at the deployment pipeline level, not left to convention.

## Latency Budget

Not applicable at this page's level — see each consuming layer's own latency budget (pages 01-12); this page documents what backs those budgets, not a budget of its own.

## Technology

See Infrastructure Map above — this page's content *is* its own technology section.

## Future Expansion

- Evaluate Temporal.io for the Workflow Engine (page 00) if the custom DAG runner outgrows what a lightweight implementation can handle — flagged as an open question in page 00.
- Managed/hosted variants of each component (e.g., managed Postgres, managed NATS) as the platform moves from research workstation to production deployment — see page 14.

---

## Related

- Previous: `12_Continuous_Learning.md`
- Next: `14_Deployment_Pipeline.md`
