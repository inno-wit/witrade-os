# ADR-0003: Apache Iceberg on object storage as the analytical table format

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** storage, data, correctness, foundational

---

## Context

The ADD specifies DuckDB over Parquet, with the Feature Store as "a schema within" the ingestion warehouse (page 03). Pages 04, 05 and 06 write engine outputs back into it. Page 07 trains from it, backtests read it, and page 16 lists it as an independently deployable container.

DuckDB is an embedded single-writer engine. Multiple writer processes against one database file is not supported, network filesystems are not supported, and there is no network protocol. **The design as written cannot be deployed as multiple services.** This is blocking defect B6.

Separately, page 03 identifies point-in-time leakage as "the single most dangerous failure mode in the whole platform" and states that correctness is "enforced at the query layer" without describing a mechanism (finding D8). A bar corrected and backfilled three days later legitimately carries an older business timestamp, so an `as_of` filter alone does not reproduce what was visible at decision time. Two things are needed: the business timestamp filter, and a way to pin the *version of the data* as it stood at decision time.

## Options considered

**A. Raw Parquet with a naming convention (status quo).**
*Pros:* simple, no new concepts, no catalog to operate.
*Cons:* no atomic multi-writer commits; no schema evolution without rewriting; no snapshot isolation; the small-file problem arrives quickly with tick data. Point-in-time correctness remains a convention that a careless query silently violates.

**B. Postgres / TimescaleDB for everything.**
*Pros:* one store, operationally simplest, good time-series support, already present.
*Cons:* backfills and multi-year backtests are scan-heavy analytical workloads that would contend with the transactional workload on the same instance; no snapshot-versioning primitive that maps onto the point-in-time requirement.

**C. Apache Iceberg on MinIO, DuckDB as an embedded read engine.**
*Pros:* ACID multi-writer via a catalog; snapshot isolation with time travel; schema and partition evolution; engine independence.
*Cons:* a catalog to operate (Postgres-backed, already present); a less mature Python ecosystem than the JVM one; one new concept.

**D. Delta Lake on MinIO.**
*Pros:* comparable capability, stronger JVM tooling.
*Cons:* weaker Python-native story, weaker catalog abstraction and multi-engine future.

**E. A feature-store product (Feast).**
*Pros:* solves the online/offline split directly.
*Cons:* substantial operational surface; does not solve the general analytical-store problem (bars, engine outputs, backtest results); imposes its own data model.

## Decision

Adopt **Option C**.

1. Iceberg is the table format, on MinIO.
2. The catalog is Postgres-backed (the instance already exists).
3. Each consumer embeds its own DuckDB **for reads**. DuckDB is a query engine, never a shared database.
4. Each Iceberg table has **exactly one owning writer service**, declared in the table's metadata and enforced in code review.
5. Every read on the decision path **pins an explicit snapshot ID**. A decision cycle resolves one snapshot at cycle start and every read within that cycle uses it.
6. Snapshot expiry and compaction are scheduled maintenance jobs, not manual operations.

## Rationale

Two independent problems are solved by one change.

The multi-writer failure is a hard blocker that appears on day one of multi-service deployment. Option C is the only option that solves it without abandoning the analytical-store design that pages 03 through 07 are built on.

Snapshot time travel converts the platform's stated most-dangerous failure mode from a discipline into a property of the substrate. This is decisive: `SELECT ... FOR SYSTEM_VERSION AS OF <snapshot>` is a mechanism, where "enforced at the query layer" is an intention. Combined with an `as_of` business-time filter (layer 2 of the five in R08 §4), it is the pair that actually reproduces what was visible at decision time.

D is nearly equivalent and would be an acceptable substitute. C is preferred for the catalog abstraction and the stronger multi-engine trajectory, which matters over a ten-year horizon.
B is rejected on workload contention, and because it has no versioning primitive that maps onto point-in-time.
A is rejected because it cannot be deployed.
E is rejected as disproportionate to a platform with one operator and a small instrument universe.

## Consequences

**Positive**
- Multi-writer works, so the service decomposition in R02 is deployable.
- Point-in-time correctness is mechanical rather than aspirational.
- Schema evolution stops being a migration.
- Every backtest can pin an exact input version, which is the foundation of reproducibility and of the determinism CI test (R01 §10, guardrail 5).
- The query engine can change later without a data migration.

**Negative**
- One new concept, roughly a day of learning.
- `pyiceberg` maturity must be verified against the actual write path **before** committing. This is a prerequisite task, not an assumption.
- Commits go through a catalog rather than a file write, so the write path is slightly more complex.
- Snapshot expiry and compaction become scheduled maintenance jobs that must exist before tick volume accumulates.

**Neutral**
- DuckDB is retained, in its correct role as a per-process read engine.
- Page 13's three-tier storage rule (hot / warm / cold) is preserved unchanged.

## Tripwire

1. **Before commitment:** if `pyiceberg` proves insufficient for the write path under a realistic load test, reconsider Option D.
2. **Informational:** if the platform grows to a scale where a JVM query engine becomes necessary. Iceberg supports this natively, so this is a note rather than a reversal.
3. **Reversal:** if after twelve months exactly one service writes to exactly one table and no backtest has ever pinned a snapshot, the complexity is unearned and Option A becomes defensible again. Check this at the first annual review.

## Related

- ADR-0034 (point-in-time correctness in five layers) depends on this
- ADR-0035 (clock injection) is the other half of replay determinism
- ADR-0007 (Postgres as the transactional store) draws the boundary against this one
- `../review/R13_Infrastructure.md` §3
- `../review/R08_Data_Lineage.md` §4
- Blocking defect B6, document defect D8
- Source: `../03_Feature_Store.md`, `../13_Infrastructure_Platform.md`
