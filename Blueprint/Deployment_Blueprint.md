# Deployment Blueprint

**Blueprint deliverable:** B.9
**Canonical source, not duplicated:** `../Architecture/review/R14_Deployment.md` — six environments, four deployment tracks (code/models/prompts/config, each with its own rollback mechanism), blue/green vs lease-handover by service class, canary-by-capital, disaster recovery. This document is the **implementation-level realisation** of R14's design: actual `infra/compose/` file structure, actual CI stage names, tied to `Repository_Architecture.md` and `Service_Catalog.md`.
**Status:** Blueprint v1.0, 2026-08-04

---

## 1. Six environments, as `infra/compose/` files

| Environment | R14 definition | Compose file |
|---|---|---|
| `dev` | Local developer workstation, all services, fake/mocked broker | `infra/compose/docker-compose.dev.yml` |
| `research` | Full stack minus the live broker connection, Simulation Harness the only order path | `infra/compose/docker-compose.research.yml` |
| `ci` | Ephemeral, spun up per test run, torn down after | `infra/compose/docker-compose.ci.yml` |
| `paper` | Full stack, live market data, `SimulatedBrokerAdapter` instead of MT5 | `infra/compose/docker-compose.paper.yml` |
| `prod` | Full stack, live MT5 bridge, `ALLOW_TRADING` gate armed | `infra/compose/docker-compose.prod.yml` + `infra/compose/docker-compose.bridge.yml` (the Windows-only override, per `Repository_Architecture.md` §4's `bridge/` isolation) |
| `dr` | Cold-standby mirror of `prod`, brought up only during a declared disaster recovery event | `infra/compose/docker-compose.dr.yml` |

Each file composes from `infra/compose/base/*.yml` fragments per deployment group (`Service_Catalog.md` §2-8) via Compose's file-merge feature — a change to the Edge group's resource limits is one fragment edit, not six file edits.

## 2. Four deployment tracks, implementation mechanism

| Track | R14 rollback mechanism | Implementation |
|---|---|---|
| **Code** | Blue/green (stateless) or lease handover (singleton) | `scripts/deploy.py`, service-class-aware — reads `Service_Catalog.md`'s scaling-strategy column to pick the mechanism automatically, never a manual per-service choice |
| **Models / RL policies** | Registry pointer flip, ~5 sec | `ModelRegistryService.promote()` / `.rollback()` (`Interface_Definitions.md`) — no container redeploy involved at all |
| **Prompts / weights** | Same registry mechanism, same interface | Identical code path to models, per ADR-0042's unification |
| **Configuration** | New version, never an edit | `RiskLimitConfig` and `InstrumentSpec` (`Schema_Blueprint.md` §12) are themselves versioned artefacts, published through the same `packages/kernel` outbox pattern as any other state change |

## 3. CI pipeline stages

```
1. lint          — ruff/mypy, plus the cross-reference linter (Architecture/freeze/A.1 §7's
                    script, wired into CI per that report's own recommendation)
2. unit           — per-package, Package_Blueprint.md §1's tests/unit/
3. contract        — verify every api/ module's DTOs match packages/schemas exactly
4. schema-check    — new/changed event subjects registered, backward-compatible (ADR-0040)
5. integration      — docker-compose.ci.yml, cross-service flows
6. replay-determinism — Event_Blueprint.md §4's backtest mode, same seed twice, byte-identical
7. security         — secret scan (repo + history + images), dependency scan, prompt-injection
                       corpus, authorisation matrix, credential-isolation test
                       (all six from Architecture/21_Security_Architecture.md §10)
8. chaos-closed      — fail-closed suite: kill each dependency, assert refuse-to-trade
9. build             — image build, cosign signing (Architecture/review/R15 §6)
10. publish           — to the internal registry, SBOM attached
```

**Stage 6 (replay-determinism) is the one CI stage this platform has that a generic trading system would not**, and it exists specifically because `../Architecture/review/R19_Missing_Components.md` §2 states nothing about look-ahead bias is testable without it.

## 4. Promotion gates (implementation of R14 §8)

| Transition | Automated gate | Human gate |
|---|---|---|
| `dev` → `ci` | All CI stages pass | None |
| `ci` → `research`/`paper` | Same, plus replay-determinism | None |
| `paper` → `prod` | 7-day or 50-decision paper soak, reconciliation clean throughout, zero correctness SLO violations | Operator approval, typed confirmation |
| `prod` entry (`ALLOW_TRADING`) | Canary-by-capital window armed, auto-rollback armed | `ALLOW_TRADING` typed confirmation (R14 §8) |

## 5. Disaster recovery

Implementation of R14 §10: `infra/compose/docker-compose.dr.yml` mirrors `prod`'s service topology against a separate Postgres replica and a separate NATS JetStream mirror. The DR runbook (`Production_Readiness.md` §"Disaster Recovery") is exercised quarterly against this compose file specifically, not simulated — an untested DR path is a hypothesis, matching R14 §7's own stated principle for rollback.

## 6. What this document does not repeat

Canary-by-capital's exact mechanics (position-size-scaled traffic, auto-rollback trigger conditions), the full six-environment connection matrix, and the disaster-recovery RTO/RPO targets all remain exactly as specified in `../Architecture/review/R14_Deployment.md` §6, §2, and §10 respectively — restating them here would violate the same canonical-source rule `../Architecture/freeze/Canonical_Source_Validation.md` exists to check.

---

## 7. Related

- `../Architecture/review/R14_Deployment.md` — the canonical deployment design this blueprint implements
- `Repository_Architecture.md` §2 — the `infra/` directory this document details
- `Service_Catalog.md` — the per-service scaling strategy §2's `deploy.py` reads
- `Production_Readiness.md` — the DR runbook this document's §5 is exercised against
