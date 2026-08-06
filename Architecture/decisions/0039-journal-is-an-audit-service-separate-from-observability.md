# ADR-0039: The Journal is an audit service, separate from observability

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** audit, observability, compliance

---

## Context

Page 13 places the Journal in the observability tier, in Postgres alongside the operational ledgers, with no immutability guarantee. This is document defect D9.

The placement conflates two things with opposite requirements:

| Property | Observability | Audit record |
|---|---|---|
| Completeness | Sampled, downsampled, lossy by design | **Every record, always** |
| Retention | Days to weeks | Years to permanent |
| Mutability | Freely mutable, retention policies delete | **Append-only, immutable** |
| Tamper evidence | None | **Required** |
| Availability model | Best effort | Must survive the loss of everything else |
| Purpose | Debugging and alerting | Forensic and legal record |

An audit record living in the observability tier inherits observability's properties, which means: **the record you would need in a dispute sits in a table anyone can update, subject to a retention policy designed for metrics.**

There is a sharper way to state the requirement: *if the entire observability stack were deleted, the platform's forensic and legal record must be intact.* Under page 13's design, it would not be.

## Options considered

**A. Journal in the observability tier (status quo).**
*Pros:* one place for "records of what happened"; no new component.
*Cons:* mutable, subject to operational retention policies, no tamper evidence, shares a failure and backup domain with tooling that is designed to be lossy.

**B. Append-only table in the operational database, by convention.**
*Pros:* no new component; ACID.
*Cons:* "append-only by convention" means the application does not issue `UPDATE`. Any operator with database access can, and so can a bug. There is no evidence of tampering after the fact.

**C. A Decision Record Store: a separate audit service with database-enforced append-only semantics, a hash chain, content-addressed blobs, and an independent restore path.**
*Pros:* immutability enforced by the database rather than by discipline; tamper-evident; independently restorable; separate retention.
*Cons:* a new component; a second store to back up and restore-test.

## Decision

**Option C.** The **Decision Record Store** (container C20) is an audit service in BC11, distinct from the observability stack.

| Property | Mechanism |
|---|---|
| **Append-only** | `UPDATE` and `DELETE` **revoked at the Postgres role level** on the `audit` schema. Enforced by the database, not by application code |
| **Tamper-evident** | Hash chain: each record carries `sha256(prev_hash \|\| canonical(record))`. A **daily checkpoint hash is published to a separate store** (MinIO, object-locked) |
| **Content-addressed blobs** | Evidence graphs, prompts, LLM requests and responses stored in MinIO with **object lock in compliance mode**, referenced by hash |
| **Complete** | Every decision cycle, every risk assessment, every order and fill, every kill-switch action, every limit change, every override, every privileged operation |
| **Queryable** | By `correlation_id`, `decision_id`, `trade_id`, time range, actor |
| **Independently restorable** | Its own backup and restore path, **tested separately** from the operational database |

### Binding rules

1. **The write path goes through the transactional outbox** (ADR-0038). An audit record that was not written because a publish failed is the exact gap the store exists to prevent.
2. **Records are sealed before the corresponding decision is published.** A proposal cannot be emitted before its evidence graph and desk opinions are durably recorded (R10 §10, PM responsibility 9).
3. **Retention is permanent** for the `TRADING` and `DECISION` classes. The `retention_class` field in the event envelope (ADR-0037) exists so an operational retention policy cannot reach these.
4. **Observability remains as designed** (Prometheus, Grafana, Loki, Tempo) and is unchanged. This ADR does not add audit requirements to it; it removes audit responsibility from it.
5. **The hash chain is verified on a schedule** and on demand. An unverified chain provides no tamper evidence, only the appearance of it.
6. **Restore is tested quarterly**, independently of the operational database restore. An untested backup is a hypothesis.

## Rationale

The two workloads have genuinely opposite requirements, and any design that shares a store between them resolves those conflicts in favour of one. Sharing means either the audit record inherits lossy retention, or metrics inherit permanent retention and immutability, which is absurd. Separating them lets each be correct.

Database-enforced append-only (revoking `UPDATE`/`DELETE` at the role level) is the difference between a claim and a property. "The application only inserts" is true until a migration, a repair script, or a well-intentioned cleanup. A revoked grant fails regardless of intent.

The hash chain adds the property that revocation alone cannot: **evidence of tampering by someone who can grant themselves permissions.** For a single-operator platform, the person with database access is the person the audit record might one day need to be defended against, not out of suspicion but because an audit record whose custodian can silently edit it is not evidence of anything. The daily checkpoint published to object-locked storage is what makes the chain meaningful.

Rule 2 is what makes the record trustworthy rather than merely present. A record written after the decision was published can, in principle, be written to match the outcome. Sealing first means the record is committed before anyone knows what happened.

Rule 4 is worth stating because the natural reading of this ADR is "audit is important, so make Loki durable." That is the wrong conclusion. Observability should stay lossy and cheap; the fix is to stop asking it to be an audit trail.

## Consequences

**Positive**
- The forensic record survives the loss of the entire observability stack.
- Tampering is detectable, including by a privileged actor.
- Audit retention is independent of operational retention policy.
- Every decision is reconstructible with its exact evidence, prompts and model versions.
- Observability can stay cheap and lossy, which is what it should be.

**Negative**
- A second store to operate, back up and restore-test.
- Content-addressed blobs in object-locked MinIO cannot be deleted, including by mistake, which is the point and is also a storage commitment.
- The hash chain adds a small write-path cost and a verification job.
- Sealing before publishing adds a durable write to the decision path, which is budgeted.

**Neutral**
- Postgres `audit` schema plus MinIO. Both already exist.

## Tripwire

1. **If hash chain verification ever fails**, treat it as a security incident and follow the R15 §11 sequence, not the operational incident path.
2. **If the audit restore drill has not run in six months**, the restore path does not work. Assume it does not until demonstrated.
3. **If any component is found reading the audit store as an operational data source**, that is a boundary violation: the audit store is written to and read from for forensics, never queried on the decision path.

## Related

- ADR-0038 (outbox) is the write path
- ADR-0007 (Postgres) supplies the role-level revocation
- ADR-0037 (`retention_class`) protects these records from operational policy
- ADR-0024 (limit governance) writes its change records here
- ADR-0036 (immutable raw data) is the same principle applied to ingestion
- `../review/R19_Missing_Components.md` §7
- `../review/R12_Observability.md`
- Document defect D9
- Source: `../13_Infrastructure_Platform.md`
