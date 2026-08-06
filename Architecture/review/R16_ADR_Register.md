# R16 — Architecture Decision Records

**Deliverable:** 16
**Delta against:** the whole ADD. No ADRs exist. Several decisions are made in prose across pages 00-16 without their alternatives, and page 00 explicitly defers four decisions with no record of what is being weighed.
**Status:** Review v1.0

---

## 1. Why this matters here specifically

An ADD without ADRs answers "what" and not "why." In a platform expected to run for a decade and operated by one person, the "why" is the entire defence against the most expensive failure mode in long-lived systems: **re-litigating a settled decision, badly, eighteen months later, with the original reasoning forgotten.**

Two ADD-specific reasons this matters more than usual:

1. **Several excellent decisions are stated without their reasoning.** "Kill switch is synchronous, not pub/sub" (page 10) has one sentence of justification. Someone refactoring for cleanliness in 2028 will see a synchronous call in an otherwise event-driven system and "fix" it. An ADR is what stops that.
2. **Several deferred decisions have no record of the options.** Page 00 defers Temporal versus a custom DAG runner. Without an ADR, that decision will be made by whoever writes the code first, on the day, with no context.

---

## 2. Format

Lightweight MADR. Stored in `Architecture/decisions/NNNN-slug.md`. Immutable once accepted; a change supersedes rather than edits.

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

**The Tripwire section is the addition to standard MADR and is the most valuable field.** Most ADRs record a decision and never get revisited even when the conditions that justified them have changed. A written tripwire turns a decision into something with a monitored expiry condition.

---

## 3. The register

40 ADRs. Priority: **P0** must exist before implementation starts (they constrain code that would otherwise be written wrong). **P1** before live capital. **P2** as encountered.

### Foundational

| # | Title | Priority | Note |
|---|---|---|---|
| 001 | Python as the primary implementation language | P0 | Records the tripwire that would force a compiled hot path |
| 002 | Deterministic computation and AI reasoning are architecturally separated | **P0** | The platform's central constraint. Currently stated in prose on pages 00 and 09 with no record of what was rejected (a single reasoning agent, LLM-computed indicators, LLM tool-use for calculation) |
| 003 | Apache Iceberg on object storage as the analytical table format | **P0** | Closes B6 and D8. Alternatives: raw Parquet (status quo), Delta Lake, Postgres/Timescale for everything, a feature-store product |
| 004 | NATS JetStream as the event backbone | **P0** | Alternatives: Kafka/Redpanda, RabbitMQ, Postgres LISTEN/NOTIFY, direct HTTP. **Tripwire: the four conditions in R13 §4** |
| 005 | Choreography for data flow, one orchestrated saga for the decision cycle | **P0** | Resolves page 00's deferred Temporal question. Tripwire: three human-gated long-running workflows |
| 006 | Event sourcing for the Portfolio context only | **P0** | Explains why exactly one context is event-sourced and the other ten are not. Prevents both over-application and later "why is this one different" confusion |
| 007 | Postgres as the transactional store for every context | P0 | Alternatives: per-context databases, a document store |
| 008 | Docker Compose over Kubernetes | P1 | Tripwire: >3 hosts, autoscaling, >1 operator, or multi-tenancy |
| 009 | Single-operator, single-tenant architecture | **P0** | **The most consequential deferred decision in the ADD.** The folder is `SAAS/`, TradeHub is a product, but the ADD assumes one operator throughout. Multi-tenancy retrofitted later touches every table, every subject, every authorisation check. Decide now, in writing, either way |

### Domain and boundaries

| # | Title | Priority |
|---|---|---|
| 010 | Eleven bounded contexts, and the criteria used to draw them | **P0** |
| 011 | The Risk Engine is the sole authorisation authority (closes B4) | **P0** |
| 012 | Portfolio state is published as a read model, not queried from Risk (closes B3) | **P0** |
| 013 | Desk citations are references to evidence nodes, never literal values (closes W1) | **P0** |
| 014 | The shared kernel is limited to seven types, and the governance around changing it | P0 |
| 015 | Reference data is a separate bounded context, not configuration | P0 |
| 016 | Order and position lifecycle is owned by a dedicated OMS, not by Execution | **P0** |

### Safety and risk

| # | Title | Priority |
|---|---|---|
| 017 | The kill switch is a synchronous in-process gate, not a pub/sub subscriber | **P0.** Preserves page 10's excellent decision with its reasoning, so it survives a future refactor |
| 018 | The kill switch is a three-tier fail-closed interlock (closes B2) | **P0** |
| 019 | Exits are never blocked by entry-blocking rules (closes G8) | **P0.** The highest-value single safety ADR |
| 020 | Fractional Kelly as a platform default, not a per-trade tunable | P0. Page 10's decision, recorded |
| 021 | Deadlock and quorum failure resolve to no-trade, with the asymmetry justified | P0. Page 08's decision, recorded |
| 022 | Every entry carries a broker-side hard stop | **P0.** Not in the ADD. It is what protects positions through total platform loss |
| 023 | The kill switch does not auto-liquidate | P0. Page 10's decision, recorded, with the reasoning that auto-liquidating into a bad market can be worse |
| 024 | Risk limits are versioned, dual-controlled artefacts, not configuration | P1 |
| 025 | Fail-closed is the universal default for every dependency failure | **P0.** Stated once, applies everywhere, tested by the chaos suite |

### AI and decision

| # | Title | Priority |
|---|---|---|
| 026 | Six isolated desks with separate API calls, not one multi-persona prompt | P0. Page 08's decision, recorded with its reasoning |
| 027 | Log-odds pooling with dependence discounting, replacing the weighted vote | P1 |
| 028 | Desk confidence is calibrated before use; raw confidence is never a weight | P1 |
| 029 | A Red Team desk and a deterministic CRO Gate exist and outrank the pooled committee | P1 |
| 030 | Prompts are versioned registry artefacts with point-in-time resolution | **P0.** Without this, every committee backtest is contaminated |
| 031 | All LLM traffic goes through one gateway; no service imports a vendor SDK | P1 |
| 032 | Untrusted external text is converted to typed features at an ACL and never reaches a desk (closes B5) | **P0** |
| 033 | Precedent memory is similarity-based and `as_of`-filtered, replacing recency memory | P1 |

### Data and lineage

| # | Title | Priority |
|---|---|---|
| 034 | Point-in-time correctness is enforced by five layers, not by caller discipline | **P0** |
| 035 | The Clock is injected everywhere; direct wall-clock calls are a CI failure | **P0.** Cheap now, effectively impossible to retrofit |
| 036 | Raw data is immutable; corrections are new versions with downstream backfill | P0. Extends page 01's rule |
| 037 | Commands and events are distinct primitives; nothing moving capital is a broadcast event (closes B1) | **P0** |
| 038 | The transactional outbox pattern is mandatory for any service that writes state and publishes | P1 |
| 039 | The Journal is an audit service, separate from observability (closes D9) | P1 |
| 040 | The schema registry is the wire contract; Pydantic models are generated from it | P1 |

---

## 4. The nine that cannot wait

If only nine ADRs are written before implementation begins, these are the nine, because each constrains code that would otherwise be written in a way that is expensive to reverse.

| # | ADR | What goes wrong without it |
|---|---|---|
| 1 | **009 Single-tenant** | Multi-tenancy retrofit touches every table, subject, and authorisation check. The most expensive possible late change |
| 2 | **003 Iceberg** | Storage format migration after data accumulates. Also, point-in-time correctness stays unenforceable |
| 3 | **037 Commands vs events** | The wire protocol is the hardest thing to change once services exist. Also closes the duplicate-order class |
| 4 | **035 Clock injection** | Every `datetime.now()` written before this decision must be found and removed later, and the ones missed break replay silently |
| 5 | **013 Citations as references** | Changes the desk output schema, the evidence model, and the validation logic. Cheap now, a rewrite of the committee later |
| 6 | **011 + 012 Sole authority and read models** | Two dependency cycles baked into the module graph |
| 7 | **018 Fail-closed kill switch** | The safety-critical path written wrong, and it works fine in testing |
| 8 | **019 Exits never blocked** | The bug does not appear until the first genuine emergency, which is the worst possible time to find it |
| 9 | **002 Deterministic/AI separation** | Already correct in the ADD. The ADR exists to stop it eroding under implementation pressure, which it will |

---

## 5. Two worked examples

Full ADRs for the two decisions where the reasoning is least obvious from the conclusion.

---

### ADR-003: Apache Iceberg on object storage as the analytical table format

**Status:** Proposed
**Date:** 2026-08-03
**Tags:** storage, data, correctness

**Context**

The ADD specifies DuckDB over Parquet, with the Feature Store as "a schema within" the ingestion warehouse (page 03). Pages 04, 05 and 06 write engine outputs back into it. Page 07 trains from it, backtests read it, and page 16 lists it as an independently deployable container.

DuckDB is an embedded single-writer engine. Multiple writer processes against one database file is not supported, network filesystems are not supported, and there is no network protocol. The design as written cannot be deployed as multiple services.

Separately, page 03 identifies point-in-time leakage as "the single most dangerous failure mode in the whole platform" and states that correctness is "enforced at the query layer" without describing a mechanism. A bar corrected and backfilled three days later legitimately carries an older business timestamp, so an `as_of` filter alone does not reproduce what was visible at decision time.

**Options considered**

**A. Raw Parquet with a naming convention (status quo).** Simple, no new concepts. But no atomic multi-writer commits, no schema evolution without rewriting, no snapshot isolation, and the small-file problem arrives quickly with tick data. Point-in-time correctness remains a convention.

**B. Postgres/TimescaleDB for everything.** One store, operationally simplest, good time-series support. But backfills and multi-year backtests are scan-heavy analytical workloads that would contend with the transactional workload on the same instance, and there is no snapshot-versioning primitive that maps onto the point-in-time requirement.

**C. Apache Iceberg on MinIO, DuckDB as an embedded read engine.** ACID multi-writer via a catalog, snapshot isolation with time travel, schema and partition evolution, engine independence. Costs: a catalog to operate (Postgres-backed, already present), a less mature Python ecosystem than the JVM one, one new concept.

**D. Delta Lake on MinIO.** Comparable capability. Stronger JVM tooling, weaker Python-native story, weaker catalog abstraction and multi-engine future.

**E. A feature-store product (Feast).** Solves the online/offline split directly. But adds a substantial operational surface, does not solve the general analytical-store problem (bars, engine outputs, backtest results), and imposes its own data model.

**Decision**

Adopt **Option C**. Iceberg is the table format on MinIO. Each consumer embeds its own DuckDB for reads. Each table has exactly one owning writer service. All reads on the decision path pin an explicit snapshot ID.

**Rationale**

Two independent problems are solved by one change. The multi-writer failure is a hard blocker that appears on day one of multi-service deployment; C is the only option that solves it without abandoning the analytical-store design. And snapshot time travel converts the platform's stated most-dangerous failure mode from a discipline into a property of the substrate. That second point is decisive: `SELECT ... FOR SYSTEM_VERSION AS OF <snapshot>` is a mechanism, where "enforced at the query layer" is an intention.

D is nearly equivalent and would be an acceptable substitute. C is preferred for the catalog abstraction and the stronger multi-engine trajectory, which matters over a ten-year horizon. B is rejected on workload contention. A is rejected because it cannot be deployed. E is rejected as disproportionate.

**Consequences**

*Positive:* multi-writer works; point-in-time correctness is mechanical; schema evolution stops being a migration; every backtest can pin an exact input version, which is the foundation of reproducibility; the query engine can change later without a data migration.

*Negative:* one new concept and roughly a day of learning; `pyiceberg` maturity must be verified before commitment; commits go through a catalog rather than a file write, so the write path is slightly more complex; snapshot expiry and compaction become scheduled maintenance jobs.

*Neutral:* DuckDB is retained, in its correct role. Page 13's three-tier storage rule is preserved unchanged.

**Tripwire**

Revisit if `pyiceberg` proves insufficient for the write path (verify before committing), or if the platform grows to a scale where a JVM query engine becomes necessary (Iceberg supports this natively, so the tripwire is informational rather than a reversal).

**Related:** R13 §3, R08 §4, B6, D8.

---

### ADR-019: Exits are never blocked by entry-blocking rules

**Status:** Proposed
**Date:** 2026-08-03
**Tags:** risk, safety

**Context**

Page 10 defines a sequential risk pipeline ending in a kill switch, applied to "every Trade Recommendation." It does not distinguish opening a position from closing one. Every rule (drawdown guard, exposure limits, news blackout, kill switch) is described as gating trades generically.

A naive implementation of that pipeline blocks exits under exactly the conditions where exits matter most: a breached drawdown limit, an active kill switch, an approaching high-impact event, or an exposure cap.

Page 10 gets the adjacent decision right (the kill switch does not auto-liquidate) but that decision addresses whether the platform should *force* exits. It does not address whether the platform can still *permit* them.

**Options considered**

**A. One pipeline for all actions (implied status quo).** Simplest, one code path. But it can trap the platform in a position it cannot close, which is an unbounded loss.

**B. Separate exit pipeline.** Clear separation. But it duplicates logic, and the duplicate will drift.

**C. One pipeline, per-rule applicability flags.** Each rule declares whether it applies to `ENTRY`, `EXIT`, or both. One chain, one implementation, different behaviour by intent.

**Decision**

**Option C.** Every `RiskRule` declares `applies_to: set[Intent]`. Exit authorisations skip every rule not applicable to `EXIT`. The rules that remain for exits are only those that make an exit *worse* if ignored: instrument tradability (informational), liquidity (which shapes order type rather than blocking), and proposal validity.

Additionally: exits use a distinct `authorise_exit` entry point so that the intent is explicit at the call site rather than inferred from a direction field, which is a common source of this bug.

**Rationale**

The purpose of every entry-blocking rule is to prevent *taking on* risk. An exit *reduces* risk. Applying a risk-reduction control to a risk-reducing action inverts its purpose.

The concrete scenario: drawdown breaches 12%, the kill switch trips, the platform holds three losing positions. Under Option A, it cannot close them. The control designed to limit the loss has guaranteed its continuation. This is the failure mode where an automated system does the most damage, and it is entirely avoidable.

Option C over B because a duplicated pipeline will diverge, and a divergence in the exit path would be discovered during an emergency.

**Consequences**

*Positive:* the platform can always reduce risk; the kill switch becomes safe to trip aggressively, which in turn makes every other safety control more usable; one implementation, no drift.

*Negative:* the `Intent` concept must be threaded through the risk API; a bug that mislabels an entry as an exit would bypass the gates, so intent must be derived from the authoritative position state rather than from a caller-supplied field, and must be tested explicitly.

*Neutral:* rules gain one declarative field.

**Tripwire**

None. This decision should not be revisited. If a future requirement appears to need exits blocked, the requirement is wrong.

**Related:** R11 §3, R07 §2, R05 §6, G8.

---

## 6. Process

| Rule | Reason |
|---|---|
| An ADR is written **before** the code that implements it | An ADR written afterwards is a justification, not a decision |
| ADRs are immutable once Accepted | A superseding ADR links back. The history of thinking is the point |
| Every ADR has a Tripwire section, even if it says "none" | Forces the question of what would change the answer |
| The ADD pages link to the ADRs that justify their content | Page 10's kill-switch paragraph links to ADR-017 and ADR-018 |
| Quarterly tripwire review | Walk every Tripwire section, check whether any condition has been met. This is the ritual that keeps ADRs alive rather than archaeological |

The quarterly tripwire review is the practice most likely to be skipped and the one that determines whether this register is useful in year three.

---

## 7. Related

- `R00_Executive_Review.md` (P0.10)
- All other R-files (each recommendation maps to at least one ADR)
- Source: `../00_Master_Architecture.md` (Open Questions section, resolved by ADR-004, 005, 009)
