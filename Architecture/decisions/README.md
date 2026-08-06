# Architecture Decision Records — WITrade Quant Platform

**Format:** lightweight MADR plus a mandatory **Tripwire** section.
**Location:** `Architecture/decisions/NNNN-slug.md`
**Register source:** `../review/R16_ADR_Register.md`
**Status:** **43 of 43 written, 43 of 43 `Accepted`.** 0001-0040 decided or review-passed 2026-08-03; 0041-0043 added 2026-08-04 alongside pages 17-21 (`../README.md` Phase 11). No ADR remains `Proposed`.

---

## Why these exist

An ADD answers "what." ADRs answer "why." In a platform expected to run for a decade and operated by one person, the "why" is the entire defence against the most expensive failure mode in long-lived systems: **re-litigating a settled decision, badly, eighteen months later, with the original reasoning forgotten.**

Two things here depend on that specifically:

- Several genuinely good decisions in the ADD are stated without their reasoning. "The kill switch is synchronous, not pub/sub" has one sentence of justification. Someone refactoring for cleanliness in 2028 will see a synchronous call in an otherwise event-driven system and "fix" it. ADR-0017 is what stops that.
- Several decisions were deferred with no record of the options. Page 00 defers Temporal versus a custom DAG runner. ADR-0005 resolves it in writing rather than leaving it to whoever writes the code first.

---

## Read these first

**If you read four, read these:** 0019, 0013, 0037, 0009.

| Order | ADR | Why first |
|---|---|---|
| 1 | [0019 Exits never blocked](0019-exits-never-blocked-by-entry-rules.md) | Highest-value single safety decision. The bug it prevents only appears in a real emergency |
| 2 | [0013 Citations as references](0013-citations-are-references-not-values.md) | Highest-leverage single change in the review. Makes hallucinated numbers inexpressible |
| 3 | [0037 Commands vs events](0037-commands-and-events-are-distinct.md) | Closes the duplicate-order class. Hardest thing to change once services exist |
| 4 | [0009 Single-tenant](0009-single-operator-single-tenant.md) | **Decided.** Read it for the edge-proven gate that now governs when productisation is discussable at all |

---

## The register

| # | Title | Priority | File |
|---|---|---|---|
| **Foundational** |
| 001 | Python as the primary implementation language | P0 | [0001](0001-python-as-primary-language.md) |
| 002 | Deterministic computation and AI reasoning are architecturally separated | **P0** | [0002](0002-deterministic-ai-separation.md) |
| 003 | Apache Iceberg on object storage as the analytical table format | **P0** | [0003](0003-iceberg-analytical-table-format.md) |
| 004 | NATS JetStream as the event backbone | **P0** | [0004](0004-nats-jetstream-as-event-backbone.md) |
| 005 | Choreography for data flow, one orchestrated saga for the decision cycle | **P0** | [0005](0005-choreography-with-one-orchestrated-saga.md) |
| 006 | Event sourcing for the Portfolio context only | **P0** | [0006](0006-event-sourcing-for-portfolio-context-only.md) |
| 007 | Postgres as the transactional store for every context | P0 | [0007](0007-postgres-as-transactional-store.md) |
| 008 | Docker Compose over Kubernetes | P1 | [0008](0008-docker-compose-over-kubernetes.md) |
| 009 | Single-operator, single-tenant architecture | **P0** | [0009](0009-single-operator-single-tenant.md) |
| **Domain and boundaries** |
| 010 | Eleven bounded contexts, and the criteria used to draw them | **P0** | [0010](0010-eleven-bounded-contexts.md) |
| 011 | The Risk Engine is the sole authorisation authority (closes B4) | **P0** | [0011](0011-risk-engine-sole-authorisation-authority.md) |
| 012 | Portfolio state is published as a read model (closes B3) | **P0** | [0012](0012-portfolio-state-as-published-read-model.md) |
| 013 | Desk citations are references to evidence nodes, never literal values | **P0** | [0013](0013-citations-are-references-not-values.md) |
| 014 | The shared kernel is limited to seven type groups, with governance | P0 | [0014](0014-shared-kernel-limited-to-seven-types.md) |
| 015 | Reference data is a separate bounded context, not configuration | P0 | [0015](0015-reference-data-is-a-bounded-context.md) |
| 016 | Order and position lifecycle is owned by a dedicated OMS | **P0** | [0016](0016-oms-owns-order-and-position-lifecycle.md) |
| **Safety and risk** |
| 017 | The kill switch is a synchronous in-process gate, not a pub/sub subscriber | **P0** | [0017](0017-kill-switch-is-synchronous-not-pubsub.md) |
| 018 | The kill switch is a three-tier fail-closed interlock (closes B2) | **P0** | [0018](0018-kill-switch-three-tier-fail-closed-interlock.md) |
| 019 | Exits are never blocked by entry-blocking rules (closes G8) | **P0** | [0019](0019-exits-never-blocked-by-entry-rules.md) |
| 020 | Fractional Kelly as a platform default, not a per-trade tunable | P0 | [0020](0020-fractional-kelly-as-platform-default.md) |
| 021 | Deadlock and quorum failure resolve to no-trade | P0 | [0021](0021-deadlock-and-quorum-failure-resolve-to-no-trade.md) |
| 022 | Every entry carries a broker-side hard stop | **P0** | [0022](0022-every-entry-carries-a-broker-side-hard-stop.md) |
| 023 | The kill switch does not auto-liquidate | P0 | [0023](0023-kill-switch-does-not-auto-liquidate.md) |
| 024 | Risk limits are versioned, dual-controlled artefacts | P1 | [0024](0024-risk-limits-are-versioned-dual-controlled-artefacts.md) |
| 025 | Fail-closed is the universal default for every dependency failure | **P0** | [0025](0025-fail-closed-is-the-universal-default.md) |
| **AI and decision** |
| 026 | Six isolated desks with separate API calls, not one multi-persona prompt | P0 | [0026](0026-six-isolated-desks-separate-api-calls.md) |
| 027 | Log-odds pooling with dependence discounting | P1 | [0027](0027-log-odds-pooling-with-dependence-discounting.md) |
| 028 | Desk confidence is calibrated before use | P1 | [0028](0028-desk-confidence-is-calibrated-before-use.md) |
| 029 | A Red Team desk and a deterministic CRO Gate outrank the pooled committee | P1 | [0029](0029-red-team-desk-and-cro-gate.md) |
| 030 | Prompts are versioned registry artefacts with point-in-time resolution | **P0** | [0030](0030-prompts-are-versioned-point-in-time-artefacts.md) |
| 031 | All LLM traffic goes through one gateway | P1 | [0031](0031-all-llm-traffic-through-one-gateway.md) |
| 032 | Untrusted external text becomes typed features at an ACL (closes B5) | **P0** | [0032](0032-untrusted-text-becomes-typed-features-at-an-acl.md) |
| 033 | Precedent memory is similarity-based and `as_of`-filtered | P1 | [0033](0033-precedent-memory-is-similarity-based-and-as-of-filtered.md) |
| **Data and lineage** |
| 034 | Point-in-time correctness is enforced by five layers | **P0** | [0034](0034-point-in-time-correctness-in-five-layers.md) |
| 035 | The Clock is injected everywhere; direct wall-clock calls are a CI failure | **P0** | [0035](0035-clock-injection.md) |
| 036 | Raw data is immutable; corrections are new versions with backfill | P0 | [0036](0036-raw-data-is-immutable-corrections-are-versions.md) |
| 037 | Commands and events are distinct primitives (closes B1) | **P0** | [0037](0037-commands-and-events-are-distinct.md) |
| 038 | The transactional outbox is mandatory for write-and-publish services | P1 | [0038](0038-transactional-outbox-is-mandatory.md) |
| 039 | The Journal is an audit service, separate from observability | P1 | [0039](0039-journal-is-an-audit-service-separate-from-observability.md) |
| 040 | The schema registry is the wire contract; Pydantic is generated from it | P1 | [0040](0040-schema-registry-is-the-wire-contract.md) |
| **Architecture completion (pages 17-21, 2026-08-04)** |
| 041 | The Evidence Graph is a first-class subsystem, not a pipeline stage | **P0** | [0041](0041-evidence-graph-is-a-first-class-subsystem.md) |
| 042 | One Model Registry governs models, prompts, and desk weights alike, with a dual promotion gate for Tier-0 artefacts | P1 | [0042](0042-model-registry-governance-with-dual-promotion-gates.md) |
| 043 | Portfolio Construction is a twelfth bounded context, upstream of Risk Authorisation, with no authorisation power | **P0** | [0043](0043-portfolio-construction-is-a-twelfth-bounded-context.md) |

---

## Blocking defects, and the ADRs that close them

| | Defect | Closed by |
|---|---|---|
| B1 | Broadcast events used as commands on the order path (duplicate orders) | **0037** |
| B2 | Kill switch lives only in Redis, fails open | **0018** (+ 0017, 0025) |
| B3 | Circular dependency: Committee desks read from Risk and Execution | **0012** (+ 0010) |
| B4 | Two components both claim authorisation authority | **0011** |
| B5 | Untrusted news text reaches an LLM that allocates capital | **0032** (+ 0031, 0026) |
| B6 | DuckDB used as a shared multi-writer database | **0003** |
| G8 | Exits not distinguished from entries in the gating logic | **0019** |
| D8 | Point-in-time correctness asserted with no mechanism | **0034** (+ 0003, 0035) |
| D9 | Journal placed in the observability tier | **0039** |
| D10 | Event catalog not machine-checkable; orphans undetectable | **0040** |

---

## Open items requiring a human decision

**None. The register has no open forks.**

| ADR | Question | Resolution |
|---|---|---|
| 0009 | Is WITrade intended to become a product with users other than the operator? | **Answered 2026-08-03:** multi-tenancy comes after the platform has proven an edge in the market. Option C (single-tenant, reserved `TenantId` seam) `Accepted`. The tripwire is now gated on proven live edge (DSR > 0.95 confidence on live returns, 200+ cycles, PBO < 0.5) rather than on a calendar horizon. The regulator condition is exempt from the gate |

Every other ADR carried a clear recommendation with no fork left open. All 39 were marked `Accepted` in that review pass on 2026-08-03 — a formality, not a decision exercise, since none of them had a fork to resolve.

### The edge gate, and what it costs

Deferring multi-tenancy until edge is proven is the correct call for a solo project whose dominant risk is not shipping, and the event-gated form is stronger than a date. It is worth being clear-eyed that it also makes the eventual migration more expensive, not less: more history, more capital, more code. That is a knowing trade, recorded in ADR-0009's Consequences, not an oversight.

---

## Decisions with no reversal tripwire

Eight ADRs open their Tripwire section with **None** for the decision itself. They are the platform's fixed points:

| ADR | Fixed point | Carries operational tripwires |
|---|---|---|
| 0015 | Reference data does not become configuration again | yes |
| 0016 | A platform that manages entries and not exits is incomplete | yes |
| 0017 | The kill switch does not become asynchronous | no |
| 0019 | Exits are never blocked | no |
| 0022 | Positions do not go unprotected | yes |
| 0023 | The platform does not auto-liquidate | no |
| 0035 | The clock lint is not suppressed | no |
| 0037 | Nothing that moves capital is a broadcast event | no (the naming convention may still be revised) |

If a future change proposes reversing one of these, the change is wrong. The right-hand column matters because "no reversal tripwire" is not the same as "no tripwire": 0015, 0016 and 0022 each pin the decision permanently while still carrying operational conditions worth monitoring.

---

## Format

```markdown
# ADR-NNNN: <Title>

**Status:** Proposed | Accepted | Superseded by ADR-XXXX | Deprecated
**Date:** YYYY-MM-DD
**Deciders:** <who>
**Tags:** <domain>

## Context
The forces at play. What makes this a decision rather than an obvious choice.

## Options considered
### Option A ... Pros / Cons
### Option B ... Pros / Cons

## Decision
What was chosen, stated unambiguously.

## Rationale
Why, against the alternatives. This is the section future-you reads.

## Consequences
### Positive / ### Negative / ### Neutral

## Tripwire
The observable condition that should cause this decision to be revisited.
If there is no plausible tripwire, say so explicitly.

## Related
```

**The Tripwire section is the addition to standard MADR and is the most valuable field.** Most ADRs record a decision and are never revisited even when the conditions that justified them have changed. A written tripwire turns a decision into something with a monitored expiry condition.

---

## Process

| Rule | Reason |
|---|---|
| An ADR is written **before** the code that implements it | An ADR written afterwards is a justification, not a decision |
| ADRs are **immutable once Accepted** | A superseding ADR links back. The history of thinking is the point |
| Every ADR has a Tripwire section, even if it says "none" | Forces the question of what would change the answer |
| The ADD pages link to the ADRs that justify their content | Page 10's kill-switch paragraph links to ADR-0017 and ADR-0018 |
| **Quarterly tripwire review** | Walk every Tripwire section, check whether any condition has been met |

The quarterly tripwire review is the practice most likely to be skipped and the one that determines whether this register is useful in year three.

### Tripwire metrics to instrument

Several ADRs name a metric. These must exist before the conditions can be evaluated at all.

| Metric | ADR | Threshold |
|---|---|---|
| `preview_decide_divergence_rate` | 0011 | >10% sustained |
| `portfolio_projection_lag_seconds` | 0012 | p99 >2s sustained |
| `desk_schema_violation_rate` | 0013 | >2% per model version |
| Spurious kill-switch halts per month | 0018 | >2 |
| Fail-closed halts per month (infrastructure-caused) | 0025 | >4 |
| `UNPROTECTED` position duration | 0022 | any >60s is an incident |
| Deadlock rate | 0021 | >40% sustained |
| `QUORUM_NOT_MET` rate | 0021 | >5% of cycles |
| Pairwise desk agreement | 0026 | >90% means desks are not independent |
| Per-desk resolution | 0028 | near-zero means the desk adds nothing |
| Committee vs deterministic baseline, on disagreements | 0027 | no edge over 200 decisions means the LLM layer is decoration |
| `outbox_unpublished_age_seconds` | 0038 | p99 >5s sustained |
| p99 order path latency vs budget | 0001 | >50% |
| Sustained tick throughput | 0004 | >50k msg/s |
| `graph_committee_divergence` | 0041 | absent from production metrics for >1 quarter post-go-live |
| Tier-0 promotions missing the second confirmation | 0042 | any occurrence is P0 |
| BC12 admits nothing over the live pool for >12 months | 0043 | signal to promote §12's cross-strategy allocation from future to now |

Two of these are unusual and worth keeping: **per-desk resolution** (0028) and **committee vs baseline on disagreements** (0027). Together they are the only things that make the committee's existence falsifiable rather than assumed. `graph_committee_divergence` (0041) is the same idea applied one layer earlier, at the evidence graph rather than the vote.

---

## Related

- `../review/R16_ADR_Register.md` — the register these implement, plus two worked examples
- `../review/R00_Executive_Review.md` §7 — the prioritised roadmap (P0.10 is this directory)
- `../review/README.md` — index of the whole architecture review
- `../ROADMAP.md` — the source roadmap
