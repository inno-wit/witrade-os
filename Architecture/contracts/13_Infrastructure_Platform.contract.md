# 13 — Infrastructure Platform, contract completion

**Delta against:** `../13_Infrastructure_Platform.md` (unmodified)
**Adds:** Owns, Invariants, Interfaces, Degraded Mode, SLO, Security Boundary
**Containers:** C08 Lakehouse, C31 Observability, C36 Event Bus, C37 Schema Registry, C38 Secrets, C39 Identity · **Context:** Platform Ops (BC10) · **Group:** Platform
**Highest-value field for this page (R05 §11):** **SLO.** Per-dependency availability targets, because every dependent service's SLO is built on top of them

---

## What page 13 gets right, and must not be lost

The storage tier boundary is the best thing on this page and it should survive every future revision:

> **Postgres = transactional/durable ledgers requiring ACID. DuckDB/Parquet = analytical/queryable bulk. MinIO = blob/artifact.** A new component maps to one of these three, not a fourth pattern.

That rule, stated once and enforced, prevents a whole class of drift. The new-service checklist requiring a Prometheus scrape endpoint before a service is deployable is the same instinct applied to observability, and it is also right.

## Two corrections to the map

### DuckDB is not a shared database (closes B6)

Page 13 lists DuckDB as the query layer backing pages 01 and 03, and page 03 describes the Feature Store as "a schema within it". DuckDB is an embedded, single-process, single-writer engine. Multiple services writing one DuckDB file concurrently is not a supported mode, and the failure is corruption rather than an error.

**Resolution:** Apache Iceberg on MinIO is the table format. DuckDB stays, embedded per consumer, as a read engine over Iceberg. One writer per table, many readers, snapshot isolation, and time travel by snapshot ID. That last property is what converts point-in-time correctness from a discipline into a storage guarantee (ADR-0003).

The tier rule survives intact and gains precision: **Iceberg on MinIO = analytical tables. DuckDB = the embedded engine that reads them. Postgres = transactional. MinIO = blobs.**

### Three infrastructure components are missing entirely

| Missing | Consequence |
|---|---|
| **Secrets Manager (C38)** | The platform holds live broker credentials and has no management story across all 17 pages |
| **Identity Provider (C39)** | No authentication model for the operator plane |
| **Schema Registry (C37)** | The wire contract is prose in a document that predicts its own rot |

## Owns

| Asset | Owner |
|---|---|
| Iceberg catalog and table metadata | C08 |
| NATS streams, consumers, KV buckets | C36 |
| Prometheus, Loki, Tempo, Grafana state | C31 |
| `contracts/schemas/` and the registry cache | C37 |
| Secret material and rotation state | C38 |
| Identities, roles, sessions | C39 |

## Invariants

1. **One writer per Iceberg table.** Enforced by catalog-level permissions, not by convention. Multiple writers is B6.
2. Storage tier boundary holds: transactional state in Postgres, analytical tables in Iceberg, blobs in MinIO. A fourth pattern requires an ADR.
3. Every Iceberg write is a new snapshot. Snapshots are retained for the table's retention class and are never rewritten. `as_of` queries resolve by snapshot ID.
4. NATS runs clustered, minimum three nodes, JetStream persisted. A single-node bus is a single point of failure with platform-wide blast radius (page 13's own top failure mode).
5. **Every secret is retrieved from C38 at runtime. No secret appears in an environment variable baked into an image, a config file in the repo, or a container layer.** Rotation does not require a redeploy.
6. Every service authenticates with a service identity from C39. **The broker credential is issued to exactly one identity** (C24 Execution) and the issuance is audited.
7. Every deployable service exposes a Prometheus scrape endpoint, a health endpoint, and a readiness endpoint. Missing any of the three fails the deployment gate.
8. The schema registry is the wire contract. Pydantic models are generated **from** schemas, never the reverse, so a Python refactor cannot silently change the wire format (ADR-0040).
9. Infrastructure state is declarative and version-controlled. A change made by hand on a host is drift, and drift is detected by a periodic diff, not discovered during an incident.

Invariant 5 deserves emphasis because the shortcut is so natural. The MT5 bridge runs as a Windows service under `nssm`, and the path of least resistance is a credential in the service definition or a `.env` beside the executable. That credential then lives on the one machine with a live broker connection, in plaintext, surviving every redeploy, with no rotation path and no audit record of its use.

## Interfaces

| Component | Kind | Signature | Timeout | Auth |
|---|---|---|---|---|
| C38 Secrets | Query | `get_secret(path, version?) -> Secret` | 100ms | service identity |
| C38 | Command | `rotate(path, actor)` | 5s | operator, audited |
| C39 Identity | Query | `authenticate(token) -> Principal` | 50ms | public |
| C39 | Query | `authorize(principal, action, resource) -> bool` | 20ms | service |
| C37 Registry | Query | `get_schema(subject, version) -> Schema` | 20ms | service |
| C37 | Command | `register(schema, compatibility_check)` | 1s | CI only |
| C08 Lakehouse | Query | `snapshot_id(table, as_of) -> str` | 100ms | service |
| C36 Bus | — | NATS client protocol | — | mTLS |

## Degraded Mode

| Component down | Blast radius | Behaviour |
|---|---|---|
| **Postgres** | Platform-wide | **HALT.** Risk cannot record, Ledger cannot write, no decision can be made. Fail closed |
| **NATS** | Platform-wide | Commands undeliverable. **Order path halts.** Ingestion buffers locally to bounded disk, then sheds ticks (Tier B) rather than blocking |
| **MinIO / Iceberg** | Research and materialisation | Live trading continues on cached reference data and the online feature cache. **New feature materialisation stops, staleness grows, and the staleness ladders in pages 03-06 take over.** Research halts |
| **C38 Secrets** | Startup and rotation | Running services keep cached leases until expiry. **No new service can start.** Lease expiry during an outage is a HALT, not a bypass |
| **C39 Identity** | Operator plane | Existing service-to-service mTLS is unaffected. **Operator login fails.** The Ops CLI retains a break-glass path with an offline-verifiable credential, because losing operator access during an incident is its own emergency |
| **C31 Observability** | Visibility only | **Trading continues.** The audit trail is unaffected because C20 is a separate store (ADR-0039). This is exactly the separation's payoff: an observability outage is not an audit outage |
| **C37 Registry** | Build time | Running services hold their schemas. **CI fails closed:** no deploy without a reachable registry |

The observability row is worth stating explicitly. In the source design the Journal lives in the observability tier, which means an observability outage is an audit gap for the period, discovered later, unrecoverable. With C20 separate, an observability outage costs visibility and nothing else.

## SLO

The field R05 flags as highest-value here. Every dependent service's SLO is arithmetic on top of these, and page 13 currently states none.

| Component | Availability | Latency | Durability | Notes |
|---|---|---|---|---|
| **Postgres** | 99.99% | p99 < 5ms simple read | RPO 0, synchronous commit on trading schemas | The whole platform's floor |
| **NATS JetStream** | 99.99% | p99 publish < 5ms | 3 replicas on TRADING, DECISION, QUANT, REFERENCE | Cluster of 3 minimum |
| **Iceberg / MinIO** | 99.9% | p99 metadata < 100ms | 11 nines object durability, versioned | Lower bar than Postgres, correctly |
| **C38 Secrets** | 99.95% | p99 < 100ms | Sealed backups, tested restore | Lease TTL exceeds plausible outage |
| **C39 Identity** | 99.9% | p99 < 50ms | — | Break-glass path is the mitigation |
| **C37 Registry** | 99.5% | p99 < 20ms | Git is the source of truth | Build-time critical, runtime cached |
| **C31 Observability** | 99% | — | 30d metrics, 14d logs | Deliberately the lowest bar here |

**The arithmetic that matters:** the Risk Engine's 99.99% target depends synchronously on Postgres and the Ledger. A service cannot be more available than its hard dependencies, so a 99.9% Postgres would cap C21 at 99.9% regardless of how C21 is built. That is why Postgres carries the highest number on this page, and why the Capital group colocates in one failure domain rather than spreading across zones for a redundancy that would add latency to the hot path without adding availability.

Backup and restore: Postgres continuous archiving with a **restore tested monthly, not annually**. An untested restore is a hope. The Decision Record Store restores independently of the operational database, on its own path, tested separately.

## Security Boundary

| | |
|---|---|
| **Network zones** | DMZ (inbound internet), CORE (no inbound internet), VAULT (isolated segment, most restricted), Operator plane. Enforced by network policy, not only by grouping |
| **Service identity** | Every service authenticates with mTLS. **Network position alone never grants access** |
| **Secrets** | C38 is the only source. Broker credentials issued to the C24 identity only. Vendor API key to C17 only. Every retrieval is audited |
| **Database roles** | Per-service roles with least privilege. `UPDATE`/`DELETE` revoked on append-only tables (`ledger_events`, `decision_records`, raw tables) at the role level, so the application cannot rewrite history even if compromised |
| **Object storage** | Object lock on audit blobs. Versioning on all buckets |
| **Egress** | Default deny. Explicit allowlist per zone: DMZ to named data providers, C17 to the vendor endpoint, C24 to the broker. **CORE has no outbound internet at all** |
| **Operator access** | mTLS plus MFA through C32. Typed confirmation for anything touching VAULT. Every action audited |
| **Supply chain** | Pinned dependency hashes, an SBOM per build, image signing. Model artefacts are executable and load only from the internal store, verified by hash |

The dominant risk here is not an external attacker. It is operator error on a platform where one person holds every role, which is why the controls that matter most are the ones that constrain the operator: dual control on limits and corrections, typed confirmation on live actions, and database-level immutability that no credential in the building can override.

---

## Related

- Source page, unmodified: `../13_Infrastructure_Platform.md`
- `../generated/16_Container_Model_v2.md` §5 — deployment grouping and the Windows constraint
- `../generated/15_Event_Catalog_v2.md` §6 — NATS stream configuration
- `../review/R13_Infrastructure.md` — keep/re-scope/add per component, the Iceberg decision
- `../review/R15_Security.md` — threat model, trust zones, supply chain, insider controls
- `../decisions/0003-iceberg-analytical-table-format.md` — closes B6
- `../decisions/0007-postgres-as-transactional-store.md` — the tier boundary
- `../decisions/0008-docker-compose-over-kubernetes.md` — orchestration scope
