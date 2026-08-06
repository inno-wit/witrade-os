# R14 — Deployment Architecture

**Deliverable:** 14
**Delta against:** `14_Deployment_Pipeline.md`
**Status:** Review v1.0

---

## 1. Assessment

Page 14 gets the most important thing right: **promotion gates with explicit approvers at each transition**, including the rule that Continuous Learning's own proposals do not get a shortcut. It also correctly names its own worst failure mode (gate bypass under time pressure) and correctly requires enforcement in CI tooling rather than by convention.

Five gaps:

| # | Gap |
|---|---|
| P1 | The pipeline is a single linear chain (`Research → CI → Cloud → VPS → MT5 → Dashboard`). It conflates **environments** with **hosts** and treats a Windows VPS as a pipeline stage rather than a deployment target |
| P2 | No distinction between deploying **code**, **models**, **prompts**, and **configuration**, which have four different lifecycles, four different rollback mechanisms, and four different risk profiles |
| P3 | Blue/green and canary are listed as future expansion. Canary in particular needs a trading-specific definition (canary by capital, not by traffic) and should be P1 |
| P4 | No rollback procedure. "Rolled back" appears as an event name with no mechanism |
| P5 | No environment parity definition. The most common source of production surprise |

---

## 2. Environments, corrected

Page 14 has five pipeline stages. What is actually needed is six **environments**, defined by what they connect to, not by where they run.

| Env | Data | Broker | Capital | Purpose | Parity with prod |
|---|---|---|---|---|---|
| `dev` | Seeded fixtures | Simulated adapter | None | Local development | Low, intentionally |
| `sim` | Historical, Iceberg snapshots | Simulated adapter, Simulation Clock | None | Backtests, replay, research | **Same decision code**, different clock and adapter |
| `ci` | Synthetic fixtures | Simulated adapter | None | Automated tests | Full stack, ephemeral |
| `shadow` | **Live**, read-only tap | **Null adapter** (records intent, sends nothing) | None | Validate behaviour against live conditions | **Full parity except the adapter** |
| `paper` | **Live** | **MT5 demo account** | None | Pre-production rehearsal | **Full structural parity** |
| `prod` | **Live** | **MT5 live account** | **Real** | Live trading | — |

**The parity rule (P5):** `shadow`, `paper` and `prod` run **the identical container images with identical configuration structure**. The only differences are the broker adapter binding, the `env` envelope tag, and the credentials. Every service that exists in prod exists in paper, including reconciliation, the leader lease, and the platform supervisor. Omitting a safety component from paper because "there is no real money" is how that component ships untested.

**The `env` interlock:** a process whose `env` does not match the `env` in a received message rejects the message as a hard failure. This is what prevents a shadow deployment misconfiguration from placing a live order, and it is not in the current design.

---

## 3. Four deployment tracks (P2)

The single pipeline in page 14 must become four, because a prompt change and an infrastructure change have nothing in common except that both end in production.

| Track | Artefact | Gate | Deploy mechanism | Rollback | Typical lead time |
|---|---|---|---|---|---|
| **Code** | Container image, signed | Tests, schema compat, determinism, chaos | Blue/green (stateless) or lease handover (Execution) | Redeploy previous digest | Hours |
| **Model** | MLflow version | **PBO + DSR + walk-forward + leakage** | Registry pointer flip, both versions loaded | Pointer flip back, **seconds** | Days (shadow window) |
| **Prompt / weights** | Prompt registry version | Same gate as models, plus shadow | Registry pointer, point-in-time effective date | Pointer flip back | Days |
| **Config / limits** | Versioned `LimitSet` or parameter set | Dry run against 30 days of history, dual control | New immutable version with an effective-from date | Publish a new version restoring the old values (never mutate) | Minutes to hours |

**The insight that makes this worth separating:** model and prompt rollback is a pointer flip taking seconds, because both versions are already loaded. Code rollback is a redeploy taking minutes. Config rollback is a new version, never an edit. Treating all four as "deployment" produces the slowest mechanism applied to the fastest-needed case.

---

## 4. CI/CD pipeline

### Gate stages, in order

```
1  Static:      lint, format, type check (strict), dependency audit
2  Contracts:   schema registry compatibility, orphan/missing event check,
                subject naming convention, CODEOWNERS subject ownership
3  Discipline:  clock lint (no datetime.now outside platform/clock.py),
                float lint (no float in money/price/quantity paths),
                vendor-import lint (no anthropic/mt5 outside their adapters)
4  Unit:        >= 80% on domain logic, 100% on the sizing chain,
                the rule chain, and the state machines
5  Property:    state machines reject every undeclared transition;
                sizing chain is monotonically non-increasing;
                every event round-trips through its schema
6  Determinism: run the same sim twice, assert byte-identical output
7  Integration: full stack in ci, simulated broker, end-to-end decision
8  Chaos:       kill Redis / NATS / Postgres / broker mid-flight;
                assert fail-closed in every case
9  Quant:       PBO + DSR + walk-forward + leakage assertion,
                only when models, features, or parameters changed
10 Security:    SBOM, container scan, secret scan, signed artefact
11 Performance: latency regression against the SLO budget on the
                decision path
```

**Stages 3, 5, 6 and 8 are the ones that do not exist in a normal CI pipeline and are the ones this platform most needs.**

- Stage 3 catches the disciplines that silently erode: a `datetime.now()` added under time pressure breaks replay determinism months before anyone notices.
- Stage 6 is the only mechanical proof that backtests are reproducible, which is the foundation every quant claim rests on.
- Stage 8 is the only way to know that "fails closed" is true rather than intended. Every fail-closed path in this review should have a chaos test asserting it.

**No override path exists in the tooling.** Page 14 correctly requires an "explicit, logged administrative override" rather than a fast-path button. Strengthen it: the override is a separate, rarely-used workflow that requires a written justification, notifies immediately, and creates a mandatory post-hoc review item. Make it possible but socially and procedurally expensive.

### Build outputs

Every build produces: a container image pinned by digest, an SBOM, a signature (cosign), a manifest of every schema version it produces and consumes, and a deployment note listing what changed across the four tracks.

---

## 5. Deployment mechanisms by service class

| Class | Services | Mechanism | Why |
|---|---|---|---|
| **Stateless** | Ingestion, Quality, Feature Materialiser, Quant engines, Committee, Decision, Evidence Graph, LLM Gateway, API Gateway, Dashboard | **Blue/green.** Start new, health check, switch, drain old | Instant rollback, no downtime |
| **Singleton, leader-elected** | Execution, Scheduler, Outbox relays, OMS | **Lease handover.** Start new in standby, old releases the lease, new acquires it | **Never blue/green.** Two Execution instances is duplicate orders |
| **Stateful, projection-backed** | Position Ledger | **Rolling with a rebuild gate.** New instance rebuilds and verifies the projection before accepting traffic | Correctness before availability |
| **Data stores** | Postgres, MinIO, NATS | **Maintenance window only, market closed.** Backup verified first | No exceptions |
| **Windows bridge** | MT5 bridge | **Standby VPS acquires the lease** after the active drains. Requires flat book or explicitly accepted risk | Highest-risk deployment on the platform |

**The rule:** any service that can send an order is deployed by lease handover, never by running two instances concurrently. This is the operational expression of the split-brain prevention in R13 §7.

---

## 6. Canary by capital (P3)

Traffic-percentage canary is meaningless at this decision volume. Routing 10% of ten daily decisions to a new version yields one data point.

**The correct primitive: canary by capital allocation.**

```
New version is CHAMPION for decision-making, but every position it
produces is sized at 25% of normal for the first N trades (default 20).

Auto-promote to full size when ALL hold:
  - N trades completed
  - realised slippage within the shadow-predicted band
  - no SLO breach on the decision path
  - no unexpected rejections or errors
  - realised outcome distribution not significantly worse than the
    challenger's recorded hypothetical over the same period

Auto-rollback (pointer flip) on ANY of:
  - error rate above baseline
  - decision-path p99 latency SLO breach
  - realised slippage beyond the predicted band
  - two consecutive losses exceeding the modelled worst case
  - any correctness SLO violation (R12 section 8, S1 to S5)
```

Bounded loss, real signal, no artificial traffic split. This should be P1, not future expansion, because it is the only safe way to promote a change that affects trading behaviour.

**Blue/green** applies to stateless services and is straightforward. It should also be P1 rather than deferred, since it is the mechanism that makes code rollback fast.

---

## 7. Rollback (P4)

| Track | Trigger | Mechanism | Time | Verification |
|---|---|---|---|---|
| Code | SLO breach, error rate, manual | Redeploy the previous image digest (already in the registry) | ~2 min | Health checks, then a synthetic decision cycle |
| Model / prompt | Canary auto-rollback or manual | Registry pointer flip; both versions loaded | **~5 sec** | Next cycle uses the previous version, verified in the decision record |
| Config / limits | Manual | Publish a new version restoring the previous values | ~1 min | Dry run first, then the next assessment records the new version |
| Schema | Consumer errors | **Cannot roll back a published event.** Consumers must be backward compatible | — | This is why the compatibility policy in R01 §7 is non-negotiable |
| Data | Bad ingest | New Iceberg snapshot; the old one remains queryable | ~1 min | Time travel proves both states |

**Two rollback rules:**

1. **Rollback first, diagnose second.** For any correctness SLO violation, roll back before investigating. Diagnosis with a broken version in production is diagnosis while exposed.
2. **Rollback is tested.** A monthly exercise that rolls back a real deployment in `paper` and verifies the platform recovers. An untested rollback path is a hypothesis, and it will be exercised for the first time during an incident.

**Forward-only cases:** database migrations and published event schemas cannot be rolled back. Both must therefore be **expand/contract**: add the new column or field, deploy code that writes both, migrate, deploy code that reads the new, remove the old in a later release. Slower, and it is the only safe pattern.

---

## 8. Promotion gates, corrected

Page 14's gate table, with the gates it is missing.

| Transition | Existing gate | Added |
|---|---|---|
| dev → ci | — | Static, contracts, discipline lints, unit, property |
| ci → sim | — | Determinism test passes |
| sim → shadow | PBO / DSR | Plus walk-forward, leakage assertion, integration and chaos suites |
| shadow → paper | Shadow run for LLM changes | **Shadow required for ALL behaviour-affecting changes**, min 24h **and** min N decisions, with a comparison report |
| paper → prod | Manual operator approval for live order paths | Plus: minimum paper soak (7 days or 50 decisions), reconciliation clean throughout, zero correctness SLO violations, rollback rehearsed |
| prod entry | `ALLOW_TRADING` typed confirmation | Plus canary-by-capital window, plus auto-rollback armed |

**The added paper soak is the most important addition.** Page 14 goes from shadow (no orders at all) to prod (real capital) with only a manual approval between them. Paper trading is the only environment that exercises the full order path, including partial fills, broker rejections, requotes, and reconciliation, without capital at risk. Skipping it means the first real execution of that path is with money.

---

## 9. Deployment safety windows

Absent from page 14, and cheap to add.

| Window | Policy |
|---|---|
| Market closed, no open positions | **All deployments permitted.** The default window |
| Market closed, positions open | Stateless services only. Nothing touching Execution or the Ledger |
| Market open, no open positions | Stateless only, with canary |
| Market open, positions open | **Emergency fixes only**, dual approval, halt first |
| Within 30 min of a high-impact scheduled event | **Frozen.** No deployments |
| Friday after 14:00 UTC | **Frozen** unless it is a fix for an active incident |

The last two are conventions rather than technical requirements, and they prevent the specific scenario where a routine deployment coincides with the market's most volatile moment and nobody is available to respond.

---

## 10. Disaster recovery

| Property | Target |
|---|---|
| **RPO, capital events** | **0.** Achieved because broker truth is authoritative and reconciliation can reconstruct from it |
| **RPO, market data** | 5 min (last ingestion checkpoint) |
| **RPO, decision records** | 0 (synchronous commit) |
| **RTO to RECONCILING** | 30 min |
| **RTO to NORMAL** | 60 min, including break resolution |

**Backups:**

| Asset | Method | Frequency | Restore tested |
|---|---|---|---|
| Postgres | WAL archiving to MinIO + nightly base backup | Continuous | **Monthly** |
| MinIO | Replication or erasure coding + weekly offsite | Continuous | Quarterly |
| NATS streams | Snapshot to MinIO | Daily | Quarterly |
| Container images | Registry with immutable digests | Per build | Per deploy |
| Secrets | Encrypted in git (SOPS) plus an offline copy | Per change | Quarterly |
| **Runbooks and this ADD** | Git, plus an offline copy | Per change | — |

The last row is not a joke: a DR procedure stored only in the environment being recovered is not a DR procedure.

**Full DR drill: quarterly.** Restore into a clean environment, connect to the demo broker, reconcile, verify the platform reaches `NORMAL`. The drill is the only thing that converts the RTO from an aspiration into a measurement.

---

## 11. What changes in page 14

| Page 14 element | Change |
|---|---|
| Linear five-stage pipeline | Six environments plus four deployment tracks |
| VPS and MT5 as pipeline stages | Deployment targets, not stages. Only two containers are Windows-bound |
| Blue/green and canary as future | **P1**, with canary redefined as capital allocation |
| Single "manual operator approval" gate | Paper soak, reconciliation clean, rollback rehearsed |
| `deploy.rolled_back` as an event with no mechanism | Four mechanisms, four rollback times, monthly rehearsal |
| Standby VPS as future expansion | **Leader lease is P1 and must precede the standby** |
| Shadow required only for Committee/LLM changes | Required for **all** behaviour-affecting changes |
| No deployment windows | Six windows with explicit policy |

---

## 12. Related

- `R00_Executive_Review.md` (P1.2 leader election, P1.10 sequences)
- `R06_Sequence_Diagrams.md` (W9 deployment, W10 disaster recovery)
- `R07_State_Machines.md` (§10 release lifecycle)
- `R13_Infrastructure.md` (§7 Windows constraint, §9 environment sizing)
- Source: `../14_Deployment_Pipeline.md`
