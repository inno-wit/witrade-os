# ADR-0007: Postgres is the transactional store for every context

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** persistence, infrastructure, foundational

---

## Context

Page 13 assigns Postgres three responsibilities: the risk ledger, the journal, and the quarantine table. Everything else transactional is either unassigned or implicitly placed in Redis or DuckDB, both of which are the wrong tier for it. The kill switch ending up in Redis with no durability guarantee (blocking defect B2) is a direct consequence of that under-assignment.

Meanwhile several new requirements from this review all need the same properties (ACID, low volume, point lookups, durability): the transactional outbox and inbox, saga state, the Iceberg catalog, instrument specs, limit sets, the prompt registry, the decision-record hash chain, and the BC7 event stream.

The question is whether these share one store, get one store each, or go somewhere other than a relational database.

## Options considered

**A. Postgres for all transactional workloads, logically separated by schema.**
*Pros:* one store to operate, back up, restore and monitor; cross-schema transactions where genuinely needed (the outbox, which *must* commit with its state change); one connection-pooling story; mature point-in-time recovery.
*Cons:* a shared availability domain (Postgres down means everything transactional is down); schema-level separation is weaker than instance-level; noisy-neighbour contention is possible.

**B. A database per bounded context.**
*Pros:* the textbook microservices position; true isolation; independent scaling and failure domains.
*Cons:* eleven instances to operate for one person; the outbox pattern still requires the state change and the outbox row in one transaction, so a context's state and its outbox must share an instance regardless; backup, restore and PITR multiply by eleven; cross-context reporting becomes an integration project.

**C. A document store (MongoDB) for flexible domain state.**
*Pros:* schema flexibility during early development.
*Cons:* the domain here is highly relational (accounts, positions, lots, trades, ledger entries); the platform needs strong constraints, not flexible ones; adds a store without removing one.

**D. Redis for hot transactional state, Postgres for archive.**
*Pros:* fast.
*Cons:* this is precisely the mistake that produced B2. Redis has no durability guarantee suitable for a financial ledger or a safety interlock. It is a cache tier.

## Decision

**Option A.** **Postgres is the transactional store for every bounded context, logically separated by schema, not by instance.**

### Workload assignment

| Workload | Schema | Note |
|---|---|---|
| BC7 Portfolio event stream | `portfolio` | ADR-0006 |
| Transactional outbox and inbox | per-context | **Must** be in the same transaction as the state change |
| Decision cycle saga state | `decision` | One row per `cycle_id` (ADR-0005) |
| Risk assessments, limit sets, authorisations | `risk` | |
| Kill switch tier 3 (durable truth) | `risk` | ADR-0018 |
| Iceberg catalog | `catalog` | The JDBC catalog is the standard choice (ADR-0003) |
| Instrument specs and calendars | `refdata` | BC2 |
| Decision records and hash chain | `audit` | Append-only, see below |
| Prompt registry, desk weights, domain parameters | `registry` | Point-in-time resolvable (ADR-0030) |
| Scheduler job store and advisory locks | `ops` | APScheduler Postgres store, `pg_advisory_lock` for leadership |
| Data quarantine | `quality` | |

### Binding rules

1. **No context reads another context's schema.** Cross-context access is by published event, published read model, or an explicit query API. Enforced by per-schema database roles, not by convention: each service connects with a role that has no grant on other schemas.
2. **`synchronous_commit = on` for the capital-path schemas** (`portfolio`, `risk`, `audit`). A fill acknowledged and then lost on a crash is exactly the divergence the reconciliation apparatus exists to catch, and preventing it is cheaper than detecting it.
3. **The `audit` schema revokes `UPDATE` and `DELETE` at the role level.** Append-only is enforced by the database, not by application code.
4. **Deployment:** one primary with streaming replication to a standby. Point-in-time recovery enabled with WAL archiving to MinIO. **Restore tested quarterly** (an untested backup is a hypothesis).
5. **Redis holds nothing durable.** Projections, caches, leases, counters, budgets, kill-switch tier 2. Everything in Redis must be rebuildable from Postgres or from the event stream.
6. **Analytical workloads do not run here.** Bars, features, engine outputs and backtest results live in Iceberg on MinIO (ADR-0003). This boundary is what prevents a multi-year backtest from contending with the order path.

## Rationale

Rule 6 is why one shared instance is safe. The classic argument for splitting a database is workload contention, and the workload that would cause it (scan-heavy analytical queries over years of bars) is architecturally excluded by ADR-0003. What remains is genuinely small: tens to hundreds of writes per day on the capital path, plus point lookups. A single well-configured Postgres handles that with enormous headroom.

Rule 1 is what buys most of Option B's benefit at none of its cost. Schema separation enforced by database roles gives real isolation of *access*. What it does not give is isolation of *availability*, and that is accepted deliberately: at this scale, a service that cannot reach its database is down regardless of whether the outage was shared, and one database that is properly monitored, backed up and restore-tested is more reliable in practice than eleven that are not.

The outbox requirement (ADR-0038) settles the question independently. The outbox row must commit in the same transaction as the state change, so a context's state and its outbox cannot be split across instances. Given that constraint, per-context instances buy isolation between contexts only, which is exactly what roles already provide.

Rules 2 and 3 are the ones that matter most for correctness and cost almost nothing. `synchronous_commit = on` trades a small amount of write latency on a path that writes tens of times per day. Revoking `UPDATE`/`DELETE` on `audit` turns "the audit log is append-only" from a claim into a database constraint.

Option D is named explicitly because it is the mistake already present in the ADD, and this ADR is partly a record of why it is not available.

## Consequences

**Positive**
- One store to operate, monitor, back up and restore.
- Cross-schema transactions available where genuinely required (the outbox).
- Append-only audit is enforced by the database.
- Mature PITR gives a real recovery story for the ledger.
- The kill switch has a durable tier that actually is durable (ADR-0018 T3).

**Negative**
- A shared availability domain. Postgres down is a full platform halt. Given ADR-0025 (fail-closed everywhere) that is the correct behaviour, but it makes Postgres availability a P0 concern: replication, monitoring, and a tested failover.
- Noisy-neighbour contention is possible in principle. Mitigated by rule 6 and by per-role connection limits; revisit only when measured.
- Schema-level separation is weaker than instance-level and depends on the role grants being correct. Grants must be part of the migration and reviewed like code.

**Neutral**
- Redis and MinIO retain their roles. This ADR clarifies the boundary rather than moving it.

## Tripwire

Split a context onto its own instance when **measured** contention appears: p99 on `qry.ledger.snapshot` exceeding its 30ms budget with the cause attributed to database contention rather than query shape. Split on measurement, never on principle.

Separately, if the standby is ever promoted in anger, review whether the failover procedure was actually exercised beforehand. An untested failover is not a failover.

## Related

- ADR-0003 (Iceberg) draws the analytical boundary that makes one instance viable
- ADR-0006 (event sourcing for Portfolio) stores its stream here
- ADR-0018 (kill switch tier 3)
- ADR-0038 (transactional outbox) is why state and outbox cannot be split
- `../review/R13_Infrastructure.md` §5
- Source: `../13_Infrastructure_Platform.md`
