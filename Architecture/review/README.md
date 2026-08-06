# Architecture Review — WITrade Quant Platform

**Type:** Pre-implementation architectural review, institutional production readiness
**Subject:** `Architecture/00_Master_Architecture.md` through `16_C4_Container_Diagram.md`
**Version:** Review v1.0
**Date:** 2026-08-03

---

## What this is

An overlay on the existing ADD. **Pages 00-16 are not modified.** Every recommendation is stated as a delta against the page it affects, so the original design intent stays readable and the changes are traceable.

Start with `R00_Executive_Review.md`: findings, scores, and the prioritised roadmap. Everything else is depth.

---

## Headline

| | |
|---|---|
| Overall maturity | **5.3 / 10** |
| Blocking defects | **6** (capital-threatening, must close before code) |
| Document defects | 10 |
| Containers in page 16 | 15 |
| Containers actually required | **39** |
| Bounded contexts with no page in the ADD | **3** (Reference Data, Portfolio, Identity) |

**Verdict:** a strong Level-1 design document and roughly half of an institutional blueprint. The missing half is almost entirely the half that is expensive to add after code exists.

**This headline describes review v1.0 (pages 00-16 only) and is left as written, unmodified, as the historical record of that pass.** For the current, full-directory maturity score (7.4/10, after the 2026-08-03 remediation layers and the 2026-08-04 Phase 11 pages 17-21), see [R20_Architecture_Freeze.md](R20_Architecture_Freeze.md) §1. The bounded-context gap named here (Reference Data, Portfolio, Identity) is **unchanged by Phase 11** — those three still have no dedicated page, only contract-level treatment. Phase 11 added a page for a *different*, newly-created twelfth context (Portfolio Construction, BC12 — capital allocation across candidates, not the ledger BC7 names), so the "3" above does not become "2"; see R20 §3 (M1).

### The six blocking defects

| | Defect | Fix in |
|---|---|---|
| B1 | Broadcast events used as commands on the order path (duplicate orders) | R01 §2 |
| B2 | Kill switch lives only in Redis with undefined failure behaviour (fails open) | R11 §7 |
| B3 | Circular dependency: Committee desks read from Risk and Execution | R03 §2 |
| B4 | Two components both claim authorisation authority | R03 §6 |
| B5 | Untrusted news text reaches an LLM that allocates capital | R15 §5 |
| B6 | DuckDB used as a shared multi-writer database | R13 §3 |

---

## Files

| File | Deliverable | Read it for |
|---|---|---|
| [R00_Executive_Review.md](R00_Executive_Review.md) | 20 | Findings, scores, prioritised roadmap. **Start here** |
| [R01_Event_Architecture.md](R01_Event_Architecture.md) | 1 | Envelope, command/event split, catalog v2, versioning, DLQ, replay, idempotency, outbox |
| [R02_C4_Expansion.md](R02_C4_Expansion.md) | 2 | C4 L1-L4, trust boundaries, 39 containers, six L4 contracts to freeze now |
| [R03_Domain_Model_DDD.md](R03_Domain_Model_DDD.md) | 3 | 11 bounded contexts, aggregates, value objects, ACLs, shared kernel |
| [R04_Platform_Services.md](R04_Platform_Services.md) | 4 | 14 platform services and where each belongs |
| [R05_Interface_Contracts.md](R05_Interface_Contracts.md) | 5 | Corrected contract template + contracts for every new subsystem |
| [R06_Sequence_Diagrams.md](R06_Sequence_Diagrams.md) | 6 | 11 critical workflows with deadlines and abort semantics |
| [R07_State_Machines.md](R07_State_Machines.md) | 7 | 9 formal state machines |
| [R08_Data_Lineage.md](R08_Data_Lineage.md) | 8 | Raw tick to learning, forward and backward, point-in-time in five layers |
| [R09_Evidence_Graph.md](R09_Evidence_Graph.md) | 9 | Nodes, edges, weighting, confidence propagation, contradiction, explainability |
| [R10_Committee_Architecture.md](R10_Committee_Architecture.md) | 10 | Quorum, calibration, log-odds pooling, Red Team, CRO Gate, cost model |
| [R11_Risk_Architecture.md](R11_Risk_Architecture.md) | 11 | 8-category taxonomy, rule chain, VaR/CVaR, stress, model risk, kill switch |
| [R12_Observability.md](R12_Observability.md) | 12 | Metrics, logs, traces, trading telemetry, SLIs/SLOs, incident response |
| [R13_Infrastructure.md](R13_Infrastructure.md) | 13 | Keep/re-scope/add per component, Iceberg decision, Windows constraint |
| [R14_Deployment.md](R14_Deployment.md) | 14 | 6 environments, 4 deployment tracks, canary by capital, rollback, DR |
| [R15_Security.md](R15_Security.md) | 15 | Threat model, trust zones, prompt injection, supply chain, insider controls |
| [R16_ADR_Register.md](R16_ADR_Register.md) | 16 | 40 ADRs, the 9 that cannot wait, 2 worked examples |
| [R17_Performance.md](R17_Performance.md) | 17 | Latency budgets with percentiles, throughput, admission control, backpressure |
| [R18_Technical_Debt.md](R18_Technical_Debt.md) | 18 | Debt register, 4 mechanical disciplines, pre-agreed answers to future pressure |
| [R19_Missing_Components.md](R19_Missing_Components.md) | 19 | 21 new/split containers, minimum viable subset |
| [R20_Architecture_Freeze.md](R20_Architecture_Freeze.md) | 20 | **2026-08-04.** Phase 11 audit: rescored maturity (5.3 → 7.4/10), missing-artefact checklist, cross-reference validation, governance compliance, v1.0 Architecture Freeze checklist |

---

## What the ADD already gets right

Preserve these. They are the reason this review is an overlay rather than a rewrite.

- The deterministic/AI boundary. The load-bearing constraint of the whole platform, and almost nobody gets it right.
- Desk isolation by construction (separate API calls, not one mega-prompt).
- Deadlock resolves to no-trade, with the asymmetry explicitly justified.
- Kill switch as a synchronous in-process gate, not a pub/sub subscriber.
- Quality scoring with a reviewable quarantine, rather than silent drops.
- PBO/DSR as a hard promotion gate, including for the learning loop's own proposals.
- Broker truth over internal ledger.
- Broker-agnostic adapter from day one despite a single broker.
- Idempotent client-generated order IDs.
- Per-page latency budgets and failure-mode discipline throughout.

---

## Suggested reading order

**If you have 20 minutes:** R00.

**If you are about to start implementation:** R00 → R16 (write the 9 P0 ADRs) → R03 → R01 → R05.

**If you want the highest-leverage single changes:**
1. R03 §5 (citations as references, not values) — converts the platform's central claim from a policy into a property
2. R13 §3 (Iceberg) — converts point-in-time correctness from discipline into a storage property
3. R01 §2 (commands vs events) — closes the duplicate-order class
4. R11 §3 (exits never blocked) — the highest-value single safety fix
5. R19 §3 (OMS) — the largest functional gap

---

## What was built from this review

Four sibling layers, all additive, pages 00-16 still unmodified:

| Layer | Contents | Implements |
|---|---|---|
| `../decisions/` | 40 ADRs, all Accepted, each with a tripwire | R16, and the closure of every blocking defect |
| `../generated/` | Regenerated pages 15 and 16 (77 subjects, 39 containers) | R01, R02, R19, and ADR-0040 |
| `../contracts/` | The six missing contract fields for pages 01-14 | R05 §11 |
| `../diagrams/` | Excalidraw for the 39-container model and all nine R07 state machines | R02, R07, R19 |

---

## Related

- `../README.md` — master index across all six layers
- `../decisions/README.md` — the ADR register
- `../generated/README.md` — regenerated event catalog and container model
- `../diagrams/README.md` — visual companions to the container model and state machines
- `../contracts/README.md` — contract completions for pages 01-14
- Source ADD: `../00_Master_Architecture.md` … `../16_C4_Container_Diagram.md`
- Source roadmap: `../ROADMAP.md`
