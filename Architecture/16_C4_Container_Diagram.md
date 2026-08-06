# 16 — C4 Container Diagram (Whole Platform)

**Diagram:** `16_C4_Container_Diagram.excalidraw`
**Type:** Cross-cutting reference (not a phase page)
**C4 Level:** L2 — Container (formal, whole-platform view)
**Depends on:** All of pages 00-14
**Status:** Draft

---

## Purpose

Page 00 is the informal, narrative "Google Maps" of the platform. This page is its formal C4 counterpart: every container shown with its concrete technology stack, in one single-page view, so an engineer new to the platform can see every independently deployable service at once — what it's built in, not just what it conceptually does.

## Responsibilities

Enumerate every container in the system (in the C4 sense — an independently deployable/runnable unit, not a Docker container specifically, though most of these do map 1:1 to a Docker container per page 13), its technology stack, and how it connects to the Event Bus and to its immediate pipeline neighbors.

## Containers

| Container | Technology | Page |
|---|---|---|
| Dashboard / CLI | Next.js + Python CLI | 00 |
| Data Ingestion | Python (asyncio) | 01 |
| Data Quality Engine | Python | 02 |
| Feature Store | DuckDB + Parquet | 03 |
| Regime Engine | Python (`arch`, `hmmlearn`) | 04 |
| Volatility Engine | Python (`arch`, `scipy`) | 05 |
| Structure Engine | Python (`smartmoneyconcepts`) | 06 |
| ML/RL Service | Python (`sklearn`, Stable-Baselines3, MLflow) | 07 |
| AI Investment Committee | Claude API | 08 |
| Decision Intelligence Service | Python | 09 |
| Risk Engine | Python + Redis + Postgres | 10 |
| Execution Service | Python + MT5 bridge | 11 |
| Continuous Learning Service | Python (pandas, MLflow) | 12 |
| Monitoring | Prometheus + Grafana | 13 |
| Event Bus | NATS (JetStream) | 00 |

## Inputs

External systems: MT5, Databento, Polygon.io, News API, Economic Calendar, Broker — same actors as page 00's C4 Level 1.

## Outputs

A live, operator-facing trading platform — same overall system boundary as page 00, this page is strictly a different lens on the same system, not a different scope.

## Dependencies

Every functional page (00-14) — this diagram is a derived view, not an independent design decision. If a page's container list changes, this diagram needs regeneration.

## Two Kinds of Connection Shown

1. **Dashed lines (Event Bus)** — every container publishes/subscribes via NATS. This is the dominant integration pattern in the platform: containers don't call each other directly for anything that isn't latency-critical.
2. **Solid vertical arrows (primary synchronous path)** — the one request path that *is* latency-critical enough to matter for the diagram: Data → Quant Research → Decision Intelligence → Risk → Execution, the same pipeline page 00 walks through narratively. This is drawn separately from the Event Bus connections because conflating "everything talks to the bus" with "this is the critical path" would hide the one sequence an operator actually needs to reason about under latency pressure.

## Failure Modes

- **Diagram/reality drift** — same risk as page 15's Event Catalog: this is a design-time snapshot, and nothing enforces it staying in sync with actual deployed containers.
- **Missing containers** — a new service gets added to the platform (e.g., a new desk in page 08) without a corresponding update here.

## Recovery Strategy

- Treat this page the same way as page 15: a design-time contract to be diffed against real infrastructure (page 13's deployment manifests) periodically, not a guarantee of current state.
- New-service checklist (page 13/14) should include "update page 16" alongside "add Prometheus scrape endpoint" as a pre-deployment step.

## Future Expansion

- Once real deployment manifests exist (Docker Compose / Kubernetes), consider generating this diagram's container list programmatically from that manifest rather than hand-maintaining the table above.
- Add a companion L3 Component diagram set — the individual pages (04, 06, 08, etc.) already serve as de facto L3 views for their respective containers; a future pass could add pages that show the actual class/module structure per the C4 L4 Code View the original brief calls for (currently deferred — no code exists yet to diagram).

---

## Related

- Previous: `15_Event_Catalog.md`
- This closes out the currently-planned page set (00-16). See `ROADMAP.md` for what's next.
