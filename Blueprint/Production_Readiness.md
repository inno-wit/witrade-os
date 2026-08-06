# Production Readiness

**Blueprint deliverable:** B.14
**Scope:** the go/no-go gate for `paper` → `prod` promotion (`Deployment_Blueprint.md` §4), stated as one checklist spanning every dimension the brief named.
**Status:** Blueprint v1.0, 2026-08-04 — **not yet applicable** (no code exists; this is the checklist implementation will be held to, not a current pass/fail state)

---

## 1. Architecture

| Item | Gate |
|---|---|
| `../Architecture/freeze/Architecture_Freeze_v1.md` certified | ✅ Done, 2026-08-04 |
| TD1 (BC2/BC7 pages) resolved before implementation starts on those contexts | Required before Phases 4/10 close, per `Engineering_Roadmap.md` |
| No frozen artefact edited without a new ADR | Standing rule, CI-enforced via the cross-reference linter's file-hash tracking |

## 2. Infrastructure

| Item | Gate |
|---|---|
| NATS JetStream, 3-node cluster | Phase 2 exit criteria |
| Postgres, Iceberg-on-MinIO provisioned | Phase 4 exit criteria |
| Windows VPS bridge with lease handover tested | Phase 11 exit criteria |
| `dr` environment stood up and exercised | Quarterly drill, `Deployment_Blueprint.md` §5 |

## 3. Security

| Item | Gate |
|---|---|
| All P0 controls from `../Architecture/21_Security_Architecture.md` §8 live | Before any live capital, no exception |
| Credential isolation test passing (only Execution can construct a broker client) | Every commit, CI |
| Prompt-injection corpus passing | Every commit, CI — and the Text ACL not connected until it does |
| Secrets scanning (repo + history + images) clean | Every commit, CI |
| Penetration test | Annually, or before any material scope change — **cannot happen before code exists**, tracked, not skipped |

## 4. Observability

| Item | Gate |
|---|---|
| All 17 tripwire metrics instrumented (`Observability_Blueprint.md` §2.1) | Before `prod` entry |
| Dashboards for Platform, Risk, Committee, Portfolio Construction, Model Registry, Execution, Position live | Before `prod` entry |
| Runbook exists for every P0/P1 alert | Before `prod` entry |

## 5. Testing

| Item | Gate |
|---|---|
| Every level in `Testing_Blueprint.md` §1 wired into CI | Before `paper` entry |
| Replay determinism proven (byte-identical, two runs, same seed) | Before any model/strategy promotion |
| Fail-closed chaos suite passing for every dependency, including the three Phase 11 subsystems | Before `prod` entry |

## 6. Deployment

| Item | Gate |
|---|---|
| Blue/green verified for every stateless service | Phase-by-phase, as each service ships |
| Lease handover verified for every singleton service (Risk, Execution, Ledger, OMS, Reconciliation, Scheduler) | Before `prod` entry for that service |
| Canary-by-capital armed and auto-rollback tested | Before `prod` entry |

## 7. Rollback

| Item | Gate |
|---|---|
| Code rollback (blue/green pointer flip) | Tested monthly, `Deployment_Blueprint.md` §2 / `../Architecture/review/R14_Deployment.md` §7 |
| Model/prompt rollback (registry pointer flip, ~5s) | Tested monthly |
| Config rollback (new version, never an edit) | Tested monthly |
| Rollback rehearsed in `paper` before every `paper` → `prod` promotion | Standing gate, `Deployment_Blueprint.md` §4 |

## 8. Monitoring

Covered in full by §4 — not restated.

## 9. Compliance

| Item | Gate |
|---|---|
| Vendor data licensing checked before any raw vendor bar reaches a dashboard or external surface | `../Architecture/review/R15_Security.md` §8's note, carried forward as a standing pre-launch check |
| Audit log (Decision Record Store) append-only, hash-chained, independently restorable | Before `prod` entry, tested by a restore-from-backup drill |

## 10. Documentation

| Item | Gate |
|---|---|
| Every service's `README.md` points to its `../Architecture/` source page (`Package_Blueprint.md` §1) | Per-service, at merge time |
| This document itself kept current — a new production-readiness gap gets added here, not left in a PR description | Standing discipline |

## 11. Operations

| Item | Gate |
|---|---|
| On-call rotation defined (even for a single operator — a documented "who gets paged" is not optional) | Before `prod` entry |
| Startup, shutdown, broker-disconnect sequences implemented, not just documented (`../Architecture/review/R06_Sequence_Diagrams.md` W3, W4, W5) | Before `prod` entry |

## 12. Runbooks

Covered in `Observability_Blueprint.md` §6 — not restated.

## 13. Support

| Item | Gate |
|---|---|
| Escalation path documented for a broker-side incident (contact, phone verification channel per `../Architecture/21_Security_Architecture.md` §"Incident response") | Before `prod` entry |

## 14. Disaster Recovery

| Item | Gate |
|---|---|
| RTO/RPO targets stated (`../Architecture/review/R14_Deployment.md` §10) | Already specified, canonical |
| `dr` environment exercised, not simulated | Quarterly, `Deployment_Blueprint.md` §5 |

## 15. Business Continuity

| Item | Gate |
|---|---|
| Single-operator dependency acknowledged (ADR-0009) — no assumption of a second responder unless multi-tenancy's tripwire fires | Standing, documented, not a gap to close |
| Broker relationship has a documented fallback (a second broker adapter exists in code even with one broker live, per the broker-agnostic-from-day-one principle) | Phase 11 deliverable |

---

## 16. Overall gate

**This checklist has zero items currently gradable pass/fail, because no code exists.** Its purpose is to be the list implementation is held to, filled in phase by phase as `Engineering_Roadmap.md`'s phases close, not a retrospective audit. The first time this document carries a real status column is the first `paper` → `prod` promotion request.

---

## 17. Related

- `Deployment_Blueprint.md` §4 — the promotion gate this checklist backs
- `Technical_Debt_Register.md` — the P1 items (TD1, TD8) this checklist's §1 references
- `../Architecture/review/R14_Deployment.md` §10 — the DR targets §14 cites
- `../Architecture/21_Security_Architecture.md` §8 — the P0 security controls §3 cites
