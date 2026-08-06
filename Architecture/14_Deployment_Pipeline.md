# 14 — Deployment Pipeline

**Diagram:** `14_Deployment_Pipeline.excalidraw`
**Phase:** 10 — Deployment
**C4 Level:** — (deployment/operational view, not a C4 layer)
**Depends on:** `13_Infrastructure_Platform.md`
**Status:** Draft

---

## Purpose

Define how a change — a new model, a Committee prompt revision, a code fix — actually gets from a researcher's workstation to live capital, and what has to say yes at each step along the way.

## Responsibilities

Move validated changes through progressively higher-stakes environments, with an explicit promotion gate at each transition, ending at the live MT5 connection and operator dashboard.

## Pipeline

```
Research Workstation   (local dev, model research, backtesting)
  -> CI/CD (GitHub Actions)   (lint, test, PBO/DSR validation gate)
  -> Cloud                      (container registry, staged deploy, shadow-mode run)
  -> VPS                           (Windows VPS -- MT5 terminal + bridge process)
  -> MT5                             (live broker connection)
  -> Dashboard                         (operator-facing)
```

## Promotion Gates

| Transition | Gate |
|---|---|
| Research → CI/CD | PBO / Deflated Sharpe Ratio validation (page 07) — no model or Committee-weight change skips this, including changes proposed by Continuous Learning (page 12). |
| CI/CD → Cloud | Automated tests pass; any Committee/LLM-affecting change additionally requires a shadow-mode run (page 08) before cutover. |
| Cloud → VPS | Manual operator approval for anything touching live order paths. |
| VPS → MT5 | `ALLOW_TRADING` gate — paper trading by default, explicit typed confirmation to go live (per `execution-safety` skill). |

## Inputs

Code and model changes from Research Workstation, Continuous Learning's Research Backlog (page 12).

## Outputs

A deployed, live (or paper) trading system, plus dashboard availability for the Operator.

## Dependencies

Infrastructure Platform (page 13) for every technology named in this pipeline.

## Events Published

- `deploy.started`, `deploy.promoted`, `deploy.rolled_back` — per environment transition.
- `shadow.run.completed` — shadow-mode comparison results for Committee/LLM changes.

## Events Consumed

`learning.change.validated` (page 12) — a validated Research Backlog item is the typical trigger for a Research → CI/CD promotion.

## Failure Modes

- **Gate bypass under time pressure** — an operator manually pushes a change past a gate "just this once" during a fast-moving market situation, defeating the entire point of having gates.
- **Shadow-mode drift** — the shadow environment's data/conditions diverge enough from production that a clean shadow run doesn't actually predict production behavior.
- **VPS single point of failure** — MT5's Windows-only requirement concentrates the live execution path on one machine.

## Recovery Strategy

- Gates are enforced in CI/CD tooling (GitHub Actions required checks), not by convention or code review discipline alone — a bypass requires an explicit, logged administrative override, not a fast-path button.
- Shadow-mode environment is fed the same live data feed as production (read-only tap, per page 01's ingestion architecture) rather than a separate/stale data source, keeping shadow and production comparably grounded.
- VPS redundancy (standby VPS with MT5 pre-configured, per `execution-safety`-style failover patterns) is flagged here as a Future Expansion item — the current single-VPS design mirrors the existing TradeHub SMC-service deployment and inherits its single-point-of-failure risk until addressed.

## Latency Budget

Not latency-sensitive as a pipeline (deployment is not a hot-path operation) — but each individual gate should complete within a bounded time so deployment doesn't stall indefinitely: CI/CD tests target **< 10 min**, shadow-mode run target **< 24 hours** of live-shadow comparison before promotion eligibility.

## Technology

GitHub Actions (CI/CD), Docker + a container registry (Cloud stage), Windows VPS with `nssm`-managed Windows Service for the MT5 bridge process (VPS stage) — same pattern as the existing TradeHub deployment notes.

## Future Expansion

- Standby/failover VPS for the MT5 bridge, addressing the single-point-of-failure noted above.
- Blue/green or canary deployment for the Cloud stage once multiple committee/model versions need to run concurrently for comparison rather than strictly sequential shadow → promote.

---

## Related

- Previous: `13_Infrastructure_Platform.md`
- Next: `15_Event_Catalog.md` (cross-cutting reference)
