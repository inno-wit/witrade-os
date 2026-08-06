# R04 — Platform Services

**Deliverable:** 4
**Delta against:** `13_Infrastructure_Platform.md`, `00_Master_Architecture.md`
**Status:** Review v1.0

---

## 1. The gap

Page 13 maps **infrastructure technologies** (Postgres, NATS, MLflow) to the subsystems that use them. It does not identify **platform services**: the cross-cutting capabilities every domain service consumes, which must exist exactly once and be owned by nobody in particular.

The distinction matters because a capability with no owner gets reimplemented per service. Configuration is the canonical example: without a Configuration Service, every one of the 39 containers grows its own `config.py` with its own precedence rules, and changing a shared value becomes a 39-file edit with no audit trail.

Fourteen platform services below. Each entry states **where it belongs** (which is what the deliverable asks), what it owns exclusively, and the concrete recommendation, not a survey.

The organising principle:

> A platform service exists when a capability is (a) needed by three or more domain services, (b) dangerous or expensive to get wrong, and (c) has no natural domain owner. If any of the three is false, it belongs inside a domain service.

---

## 2. Authentication (PS-01)

**Status in the ADD:** absent from all 17 pages.

**Where it belongs:** its own container (C39), at the edge, in front of the API Gateway. Never inside a domain service.

**Two distinct populations, do not conflate them:**

| Population | Mechanism | Notes |
|---|---|---|
| **Humans** (Operator, Researcher, Auditor) | OIDC against an external IdP, MFA mandatory for the Operator role, short-lived session tokens (15 min) with refresh | Do not build this. Use an existing provider |
| **Services** | mTLS with per-service certificates, short-lived (24h), auto-rotated. Service identity is the certificate subject | Not shared API keys. A shared key means any compromised service can impersonate the Execution Service |

**Recommendation:** for a solo-operator platform, an external OIDC provider for humans plus a small internal CA (`step-ca`) issuing service certificates. Do not adopt a full service mesh at this scale, the operational cost exceeds the benefit below ~50 services. Revisit if the container count passes 50 (ADR-011).

**Non-negotiable:** the Execution Service accepts connections from exactly one identity (the Risk Engine) and rejects all others at the transport layer, not in application code.

---

## 3. Authorization (PS-02)

**Status in the ADD:** absent. Page 00 mentions "CLI/API auth failure blocks operator control" and nothing further.

**Where it belongs:** policy decisions centralised in a policy engine, policy **enforcement** distributed to every service. Centralised decision, distributed enforcement, never the reverse.

**Model:** RBAC as the base, with ABAC attributes for the cases that matter here.

| Role | Can | Cannot |
|---|---|---|
| `auditor` | Read every decision record, journal entry, and metric | Write anything |
| `researcher` | Run backtests, train models, propose hypotheses, read prod data | Touch prod config, approve deployments, trade |
| `operator` | Everything below plus halt, clear kill switch, force-release quarantine | Change risk limits alone (needs a second approver) |
| `risk_approver` | Second signature on limit changes | Trade |
| `service:<name>` | Exactly the subject prefixes it owns (R01 §15) plus its declared consumptions | Anything else |

**Attributes that gate beyond role:**
- `env`: a `researcher` token is valid in `sim` and `dev`, never in `prod`.
- `account_scope`: which accounts an action may affect.
- `dual_control_required`: on risk-limit mutation, kill-switch clearing after an automatic trip, and live-trading enablement.

**Recommendation:** Open Policy Agent with policies in Rego, versioned in the repo, evaluated as a library (not a sidecar) inside each service to avoid a network hop on the hot path. Policies are unit tested in CI like any other code.

**The rule the ADD most needs:** the kill switch can be *tripped* by anyone and any service. It can only be *cleared* by an `operator` with typed confirmation, and if it was tripped automatically, by two humans. Asymmetric authority on a safety interlock is the correct default and is currently unspecified.

---

## 4. Secrets Management (PS-03)

**Status in the ADD:** absent. This is the most serious single omission in the security dimension, because the platform holds live broker credentials on a Windows VPS.

**Where it belongs:** a dedicated secrets backend (C38), with secrets injected at process start, never at build time, never in an image, never in an environment variable that appears in a process listing.

**Recommendation, sized honestly for this platform:**

| Option | Verdict |
|---|---|
| HashiCorp Vault | Correct at scale, heavyweight for a solo operator. Adopt at P2 if the team grows |
| **SOPS + age, secrets encrypted in git, decrypted at deploy** | **Recommended for P1.** Auditable (git history), no new service to operate, works identically on the Windows VPS and in the cloud, supports per-environment keys |
| Cloud provider secrets manager | Fine if already committed to one cloud. Creates a hard dependency |
| `.env` files | Not acceptable once real capital is connected |

**Secret classes and rotation:**

| Class | Examples | Rotation | Blast radius if leaked |
|---|---|---|---|
| **Tier 0 — capital** | MT5 account credentials, broker API keys | 90 days, manual, dual-control | Total loss |
| Tier 1 — vendor | Databento, Polygon, Anthropic, news provider keys | 180 days, automatable | Cost and data access |
| Tier 2 — internal | Postgres passwords, NATS credentials, MinIO keys | 30 days, automated | Internal compromise |
| Tier 3 — signing | Approval-token signing key, artefact signing key | 365 days, ceremonial | Forged authorisations |

**Non-negotiables:**
1. Tier 0 secrets exist on exactly one host (the Execution VPS) and are readable by exactly one process.
2. No secret is ever logged. Enforce with a log redaction filter that pattern-matches known secret shapes and fails loudly on a match, rather than silently redacting (silent redaction hides the fact that someone tried to log it).
3. The approval-token signing key is separate from every other secret and lives only in the Risk Engine. If Execution could sign its own approvals, the entire authorisation model is decorative.

---

## 5. Configuration (PS-04)

**Status in the ADD:** implied everywhere ("configurable per symbol", "versioned per-symbol config", "tunable desk weights"), owned nowhere.

**Where it belongs:** this is the one that most needs a clear split, because "configuration" in this platform is actually four different things with four different lifecycles.

| Kind | Example | Lifecycle | Store | Change process |
|---|---|---|---|---|
| **Deployment config** | Service ports, connection strings, replica counts | Per environment, per release | Environment variables from the deploy manifest | Code review + deploy |
| **Domain parameters** | Swing length, GARCH window, quality thresholds, desk weights | Per symbol, changes with research | **Postgres, versioned, point-in-time resolvable** | PBO/DSR gate + promotion |
| **Risk limits** | Max daily loss, exposure caps, Kelly fraction | Rarely, deliberately | **Postgres `LimitSet` aggregate, immutable versions** | **Four-eyes, audited** |
| **Feature flags** | Enable a new desk, route to a new adapter | Runtime, fast | Redis + in-process cache with subscription | Operator, audited, auto-expiring |

**The critical correction:** page 08's desk weights and page 04's swing length are **domain parameters**, not config files. They must be point-in-time resolvable, because a backtest of a decision from three months ago must use the parameters that were live three months ago. If they live in a YAML file that gets edited in place, every historical backtest is contaminated and no one will notice.

```python
# The required interface
params = param_service.resolve(
    namespace="regime_engine",
    symbol=Symbol("XAUUSD"),
    timeframe=Timeframe.M15,
    as_of=cycle.as_of,          # <-- this argument is the whole point
)
```

**Non-negotiables:**
1. No component reads a config file at request time. Resolution happens at cycle start and the resolved set is hashed into the decision record.
2. Every parameter has a declared type, range, unit, and owner. An untyped parameter is how a "0.5% tolerance" becomes "50%".
3. Feature flags auto-expire after 30 days. A permanent feature flag is a fork in the codebase that nobody is maintaining.

---

## 6. Feature Registry (PS-05)

**Status in the ADD:** page 03 defines a Feature Store with nine categories and versioned definitions (`technical.rsi.v2`). Good. It does not define a **registry**: the metadata layer that answers "what features exist, who owns each, what does each depend on, which models consume it, and is it safe to serve online."

**Where it belongs:** inside the Feature Engineering context (BC3), as metadata alongside the store, not a separate service.

**What it must record per feature:**

| Field | Why |
|---|---|
| `name`, `version`, `category` | Page 03 has this |
| `definition_hash` | Detects a definition change that skipped a version bump. Page 03's second-worst failure mode |
| `owner`, `description`, `unit` | A feature nobody owns is a feature nobody fixes |
| `upstream_dependencies` | Impact analysis: which features break if a source goes down |
| `consumers` (models, desks) | The other direction: what breaks if this feature changes |
| `point_in_time_safe: bool` | **Explicit.** Some features (anything using a forward window) are training-only. Page 03 marks the Labels category as training-only but does not generalise the property |
| `online_serving_enabled: bool` + `max_staleness` | Which features may be served live and how fresh they must be |
| `expected_refresh_interval` | Powers page 03's staleness check, which currently has no data source |
| `null_policy`, `valid_range` | Data quality at the feature layer, not just the bar layer |
| `deprecated_at`, `superseded_by` | Retirement is a lifecycle stage, and page 03 has no retirement story |

**The train/serve skew guard, which the ADD lacks:** offline materialisation and online serving must execute the **same** feature definition object. Not the same logic reimplemented in a fast path. Registering a feature registers one callable, used by both paths, and CI asserts that offline and online produce identical output for a sampled set of timestamps. Train/serve skew is the most common production ML failure and page 03's architecture (one store, two access patterns) makes it likely without this guard.

---

## 7. Metadata Registry (PS-06)

**Status in the ADD:** absent.

**Where it belongs:** a thin service over Postgres, in the Platform Ops context. In practice it is a catalog that unifies four registries that would otherwise fragment.

| Sub-registry | Contents | Consumed by |
|---|---|---|
| **Dataset catalog** | Every Iceberg table, its schema, partitioning, owner, retention class, freshness SLO | Lineage (R08), backfills, DR |
| **Schema registry** | R01 §7 | Every producer and consumer |
| **Lineage graph** | Column-level derivation edges | R08, impact analysis |
| **Service catalog** | Every container, its owner, SLOs, dependencies, runbook link, on-call | Incident response (R12 §9) |

**Recommendation:** do not adopt a heavyweight data-catalog product (DataHub, Amundsen, OpenMetadata) at this scale. Build a ~500-line service over Postgres, populated **automatically** from code annotations and deployment manifests at CI time. The point is not the UI; it is that pages 15 and 16 stop being hand-maintained documents that the ADD itself predicts will rot (its words, finding D10).

**Success test:** after this exists, running `witctl impact --change feature:technical.rsi.v2` prints every model, desk, and decision path affected. That query is impossible today and will be needed within the first month of implementation.

---

## 8. Experiment Tracking (PS-07)

**Status in the ADD:** MLflow, named on pages 04, 05, 07, 12, 13. Correct choice, incompletely scoped.

**Where it belongs:** MLflow stays. The correction is **what** gets tracked.

Pages 04 and 05 say fitted GARCH/HMM parameters go into MLflow "for reproducibility". That is right and unusual to get right. But the ADD tracks only *models*. The platform's most important experiments are not model fits.

**Extend tracking to:**

| Experiment type | Currently tracked | Should be |
|---|---|---|
| ML/RL model training | Yes (page 07) | Yes |
| GARCH/HMM fits | Yes (pages 04, 05) | Yes |
| **Desk prompt versions** | No | **Yes.** A prompt is a model artefact with a version, a training rationale, and an evaluation score |
| **Desk weight sets** | No | **Yes.** Page 08 makes weights tunable via Learning; untracked tuning is untraceable overfitting |
| **Risk parameter changes** | No | **Yes.** A Kelly fraction change is an experiment with a P&L consequence |
| **Backtest runs** | No | **Yes,** with the code commit, data snapshot ID (Iceberg snapshot, R13 §3), parameter set hash, and seed. Without all four, a backtest is not reproducible and its result is an anecdote |

**Non-negotiable:** every experiment records the **Iceberg snapshot ID** of every input table. This is what makes "rerun this backtest exactly" possible, and it is the payoff for the storage decision in R13 §3.

---

## 9. Model Registry (PS-08)

**Status in the ADD:** MLflow registry with a PBO/DSR promotion gate (page 07). This is the strongest ML-ops decision in the document. Two extensions.

**Where it belongs:** MLflow stays as the registry. The promotion **gate** moves out of MLflow into an explicit, testable service, because a gate implemented as an MLflow tag convention is a gate that can be bypassed by setting a tag.

**Extension 1: registry entries are not only ML models.** The registry holds anything whose version affects a decision and must be point-in-time resolvable:

- ML/RL models (page 07)
- Fitted regime and volatility model parameters (pages 04, 05)
- **Desk prompts** (new)
- **Desk weight sets** (new)
- **Consensus strategy version** (new)
- **Risk limit sets** (cross-referenced, owned by BC6)

**Extension 2: five lifecycle stages, not two.** Page 07 implies candidate → promoted. Insufficient for a platform that mandates shadow runs (page 14).

`CANDIDATE → VALIDATED → SHADOW → CHAMPION → ARCHIVED`, with `CHALLENGER` running permanently in parallel with `CHAMPION`. See R07 §6 for the state machine and the transition guards.

---

## 10. Audit Logging (PS-09)

**Status in the ADD:** page 13 assigns the Journal to Postgres "alongside operational ledgers". This conflates two things with incompatible requirements (finding D9).

**Where it belongs:** its own service (C20, Decision Record Store) with its own storage, its own retention, and its own access path. **Not** in the observability stack, and not in the same tables as operational state.

| | Observability (R12) | Audit (this service) |
|---|---|---|
| Purpose | Debug a live problem | Prove what happened |
| Lossy | Acceptable, sampled | **Never** |
| Mutable | Rolled up, downsampled | **Append-only, immutable** |
| Retention | 30 to 90 days | Years |
| Query pattern | Time series, high cardinality | Point lookup by decision, correlation, or account |
| Failure impact | Reduced visibility | **Regulatory and forensic loss** |

**Design:**

- Append-only Postgres table, `INSERT` only, revoked `UPDATE`/`DELETE` at the role level so it is enforced by the database rather than by discipline.
- **Hash chain:** each record carries `sha256(previous_hash || canonical(record))`. Tampering is detectable. A daily checkpoint hash is published to a separate store, so even a database-level rewrite is detectable.
- Large payloads (evidence graphs, full prompts, LLM responses) are content-addressed blobs in MinIO with object-lock enabled; the Postgres row holds the hash.
- Every record carries `correlation_id`, `actor` (human or service identity), `env`, and `platform_mode`.

**What must be audited (not optional):**

| Event | Why |
|---|---|
| Every decision cycle: evidence hash, all desk opinions, prompts, model versions, parameter set, outcome | Reconstructability |
| Every risk assessment: rule-by-rule verdicts, limit-set version, inputs hash | "Why was this allowed" |
| Every order and fill | Financial record |
| Every kill-switch trip and clear, with actor | Safety interlock accountability |
| Every risk-limit change, with both approvers | Dual control |
| Every quarantine force-release (page 02's operator override) | Data integrity accountability |
| Every gate bypass or administrative override (page 14 names this failure mode) | The failure mode page 14 identifies has no detection mechanism today |
| Every `ALLOW_TRADING` transition | Live-capital accountability |

---

## 11. Notification Service (PS-10)

**Status in the ADD:** page 00 mentions tiered alerting (page / Slack / dashboard). Good instinct, no service.

**Where it belongs:** a small service in Platform Ops, consuming `evt.observability.alert.raised.v1`.

**Why it must be centralised rather than each service calling Slack:** deduplication, rate limiting, escalation, and quiet hours are cross-cutting. Page 00 names alert fatigue as a failure mode. Alert fatigue is caused precisely by every service having its own notification path with no shared suppression.

| Tier | Channel | Latency | Examples | Suppression |
|---|---|---|---|---|
| **P0 Page** | Phone, SMS, push, repeat until acked | < 30s | Kill switch tripped, reconciliation break, order state `UNKNOWN` > 60s, broker disconnected with open positions, platform HALTED | Never suppressed. Never rate limited |
| **P1 Urgent** | Push + Slack | < 2 min | Risk rejection rate spike, committee deadlock rate spike, DLQ on TRADING/DECISION, data source degraded with no fallback | Deduplicated by fingerprint, max 1 per 5 min |
| **P2 Attention** | Slack | < 15 min | Quality rejections, model drift, cost budget at 80%, consumer lag | Batched, max 1 digest per 15 min |
| **P3 Informational** | Dashboard + daily digest | Next digest | Deploy completed, weekly review done, feature backfill finished | Fully batched |

**Non-negotiables:**
1. **Every P0 has a runbook link in the notification payload.** An alert without a runbook is an alert that produces panic instead of action. This directly mitigates page 00's alert-fatigue failure mode.
2. **Synthetic heartbeat.** Page 00 already proposes this and it is correct: a heartbeat alert fires if the notification path itself goes quiet. Extend it to a dead-man's switch: if the platform does not emit a healthy heartbeat every 5 minutes during market hours, page.
3. Notifications carry `correlation_id` so the operator can jump straight to the decision trace.

---

## 12. Scheduler (PS-11)

**Status in the ADD:** page 00 names a Scheduler inside the Orchestration Layer. Underspecified for the correctness requirements it actually carries.

**Where it belongs:** its own small container (C35). It emits **commands** (R01 §2), not events.

**Requirements the ADD does not state but needs:**

| Requirement | Why |
|---|---|
| **Market-calendar aware, not cron** | "Every bar close" is not a cron expression. Bar closes shift with DST, holidays, and early closes. The Scheduler must consult the Instrument Master (BC2), which is precisely why BC2 is a blocking dependency |
| **Idempotent triggers** | A missed-then-caught-up scheduler must not fire the same bar-close twice. The trigger's idempotency key is `(job, logical_period)` |
| **Misfire policy per job** | Options: fire immediately, skip to next, backfill all missed. A missed bar-close should skip (the bar is stale). A missed weekly review should fire immediately (page 12 names cadence slippage as a failure mode) |
| **Clock injection** | In `sim`, the Scheduler is driven by the Simulation Clock, not wall time. Without this, backtests cannot run the same orchestration code as production |
| **Leader election** | Two schedulers means two committee cycles means two orders |
| **Overrun protection** | If a job is still running when the next trigger fires, skip or queue, declared per job. Never run two instances of the weekly review concurrently |

**Recommendation:** APScheduler with a Postgres job store and a Postgres advisory lock for leadership, plus a `MarketCalendar` trigger type built against BC2. Do not use raw cron: it has no concept of the trading calendar, and page 01's DST failure mode will recur at the scheduling layer.

---

## 13. Object Storage (PS-12)

**Status in the ADD:** MinIO, for "Parquet files, MLflow model artifacts" (page 13).

**Where it belongs:** MinIO stays, with a materially expanded role and a bucket policy the ADD does not have.

| Bucket | Contents | Object lock | Versioning | Lifecycle |
|---|---|---|---|---|
| `raw` | Immutable source payloads, including raw news text (which the ACL archives but nothing else reads) | **Yes, compliance mode** | Yes | Never delete |
| `lakehouse` | Iceberg data and metadata files (R13 §3) | No (Iceberg manages) | Yes | Snapshot expiry per table policy |
| `models` | MLflow artefacts, fitted parameters | Yes, governance mode | Yes | Archive after 2 years |
| `decisions` | Evidence graphs, prompts, LLM responses, rendered explanations | **Yes, compliance mode** | Yes | Never delete |
| `backups` | Postgres dumps, NATS stream snapshots | Yes | Yes | 90-day rolling + monthly annual |
| `artifacts` | Container images, signed build outputs | Yes | Yes | Retain the last 20 releases |
| `scratch` | Backtest intermediates, research output | No | No | **Auto-delete after 30 days** |

**The non-obvious requirement:** object lock in compliance mode on `raw` and `decisions` means even the root credential cannot delete an object before its retention expires. That is the property that makes the audit trail credible, and it is free with MinIO.

**Operational reality check:** MinIO on a single node is not durable. Either run it with erasure coding across ≥4 drives, or replicate to a cloud object store. A single-node MinIO holding the only copy of the audit trail is a worse outcome than no audit trail, because it creates false confidence.

---

## 14. Cache Layer (PS-13)

**Status in the ADD:** Redis, for "live portfolio state cache" (page 10) and "future real-time feature cache" (page 03).

**Where it belongs:** Redis stays. The correction is a discipline the ADD lacks: **classify every Redis use, because two of the current ones are not caches.**

| Use | Class | Correct? | Correction |
|---|---|---|---|
| Feature serving (page 03) | Read-through cache | Yes | Fine. TTL from the Feature Registry's `max_staleness` |
| Portfolio state (page 10) | Described as "cache", used as truth | **No** | It is a **projection** of BC7's event stream, rebuildable from Postgres. Never written by Risk. Rebuild on startup before trading is permitted |
| Kill switch state (page 10) | Described as state, single tier | **No** | It is a **safety interlock**, not cache. Three-tier fail-closed (B2). Redis is the middle tier only |
| Leader lease (new) | Coordination primitive | — | Acceptable with a TTL shorter than the failure-detection window. NATS KV is an equally good choice and one fewer dependency on the hot path |
| Rate limiting, cost budgets (new) | Counter | — | Correct Redis use |
| Idempotency dedup (new) | Short-lived set | — | Acceptable for non-durable dedup only. Durable dedup goes in the Postgres inbox |

**The rule the ADD needs stated:** **nothing in Redis is durable.** Any component whose correctness depends on a Redis value must be able to rebuild that value from Postgres or the event stream, and must refuse to operate (fail closed) while rebuilding. If that is not true for some value, that value is in the wrong store.

**Cache invalidation strategy, per class:** TTL for features (staleness is already a first-class concept), event-driven invalidation for projections (the projector writes), and no caching at all for anything on the authorisation path except the three-tier interlock.

---

## 15. API Gateway (PS-14)

**Status in the ADD:** page 00 says the Dashboard has "read access to all downstream layers via API" and mentions an API gateway in one parenthetical. Page 16 has no such container.

**Where it belongs:** its own container (C32), the single ingress for all human traffic. Nothing else is reachable from the operator plane.

**Responsibilities:**

| Responsibility | Detail |
|---|---|
| Authentication termination | Validates the OIDC token, injects a verified identity downstream |
| Authorization enforcement | Calls the policy engine, denies before routing |
| Rate limiting | Per identity and per endpoint. Protects the platform from a runaway dashboard poll loop |
| Request/response shaping (BFF) | The dashboard needs composed views (a decision plus its evidence plus its outcome). Composing in the gateway avoids the dashboard fanning out to eight services |
| Audit | Every mutating call is audited before it is forwarded |
| **Typed confirmation enforcement** | Dangerous operations (go live, clear kill switch, force-release quarantine, override a gate) require a confirmation token minted by a separate endpoint. Page 14 relies on this pattern; the gateway is where it is enforced |
| Circuit breaking | A slow downstream must not exhaust gateway connections |

**Explicit non-responsibility:** the gateway is **not** on the trading path. Nothing about placing an order routes through it. If the gateway is down, trading continues headless (page 00 already asserts this correctly for the dashboard; making the gateway a separate container is what makes the assertion true).

**Recommendation:** FastAPI, consistent with the rest of the stack, rather than introducing Kong/Traefik-as-gateway. At this scale the BFF composition logic is the majority of the value, and that is application code regardless.

---

## 16. Placement summary

| # | Service | Owning context | Container | Priority | On the trading hot path? |
|---|---|---|---|---|---|
| PS-01 | Authentication | BC11 Identity | C39 | P1 | No |
| PS-02 | Authorization | BC11 Identity | library + policy bundle | P1 | Only for privileged ops |
| PS-03 | Secrets | BC11 Identity | C38 | **P1** | At process start only |
| PS-04 | Configuration | BC10 Platform Ops | part of C37 | **P0** (domain params must be point-in-time from day one) | Resolved at cycle start |
| PS-05 | Feature Registry | BC3 Feature Eng | part of C06/C07 | **P0** | Yes, via serving |
| PS-06 | Metadata Registry | BC10 Platform Ops | C37 | P1 | No |
| PS-07 | Experiment Tracking | BC9 Learning | MLflow | P1 | No |
| PS-08 | Model Registry | BC4 + BC9 | MLflow + gate service | P1 | Yes, inference loads from it |
| PS-09 | Audit Logging | BC11 Identity | C20 | **P1** | Written async, never blocks |
| PS-10 | Notification | BC10 Platform Ops | part of C31 | P1 | No |
| PS-11 | Scheduler | BC10 Platform Ops | C35 | P1 | Triggers it |
| PS-12 | Object Storage | BC10 Platform Ops | MinIO | P0 (bucket policy) | No |
| PS-13 | Cache | BC10 Platform Ops | Redis | P0 (classification) | **Yes** |
| PS-14 | API Gateway | BC10 Platform Ops | C32 | P1 | **No, by design** |

---

## 17. What deliberately does not become a platform service

Stated so that these do not get built by default:

| Not a platform service | Why | Where it lives instead |
|---|---|---|
| A shared "utils" or "common" library beyond the shared kernel | It becomes a dumping ground and couples every context | The shared kernel (R03 §10) is the strict, governed limit |
| A generic workflow engine | Only one flow (the decision saga) genuinely needs orchestration | Domain-owned saga in BC5, R01 §13 |
| A service mesh | Operational cost exceeds benefit below ~50 services | mTLS via an internal CA |
| A central logging *library* with business logic | Cross-context coupling through a logger is invisible and unfixable | Structured logging config in the shared kernel, no logic |
| A "data access layer" shared across contexts | It reintroduces the shared database that bounded contexts exist to prevent | Each context owns its own persistence |

---

## 18. Related

- `R00_Executive_Review.md` (P0.4, P1.3, P1.4, P1.9)
- `R03_Domain_Model_DDD.md` (contexts these services support)
- `R12_Observability.md` (PS-10 sits inside the observability strategy)
- `R13_Infrastructure.md` (technology decisions behind PS-12, PS-13)
- `R15_Security.md` (PS-01, PS-02, PS-03 in depth)
- Source: `../13_Infrastructure_Platform.md`
