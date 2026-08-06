# Repository Architecture

**Blueprint deliverable:** B.1
**Constrains, does not choose, technology:** ADR-0001 (Python), ADR-0004 (NATS JetStream), ADR-0007 (Postgres), ADR-0003 (Iceberg on MinIO), ADR-0008 (Docker Compose over Kubernetes) are already Accepted and frozen (`../Architecture/freeze/ADR_Index.md`). This layout is the container these decisions live in, not a new decision.
**Status:** Blueprint v1.0, 2026-08-04

---

## 1. Monorepo, not polyrepo — and why that follows from what's already decided

ADR-0008 chose Docker Compose over Kubernetes specifically because the platform is single-operator, ~40 containers, one deployment target class (a research workstation plus a small number of VPS/cloud hosts). A polyrepo split (one git repository per one of 40 containers) would multiply the operational overhead ADR-0008 was written to avoid, and would fight ADR-0014's shared kernel (seven type groups every one of the twelve bounded contexts depends on) — a shared kernel across repository boundaries needs its own publish/version/consume cycle, which is exactly the kind of machinery a single operator does not want. **One monorepo, `witrade/`, containing every bounded context as a top-level package, with the shared kernel as a first-class internal dependency.**

## 2. Top-level layout

```
witrade/
├── apps/                    # Things a human runs directly
│   ├── dashboard/           # Next.js — page 00's "Web Dashboard"
│   └── cli/                 # Python typer — page 00's "CLI"
├── services/                # The 40 containers, one directory each, grouped by
│   │                        # deployment group (generated/16 §5), not by bounded context —
│   │                        # a service can be one BC's only container or one of several
│   ├── edge/                # C01, C02, C03, C04            (Market Data + Reference Data)
│   ├── data/                # C06, C07, C08                 (Feature Engineering)
│   ├── quant/                # C09-C14, C28                  (Market Intelligence + Simulation)
│   ├── decision/            # C15-C20, C27, C30, C40        (Deliberation + Learning + Portfolio Construction)
│   ├── capital/             # C21, C22, C23, C25, C26       (Risk Authorisation + Portfolio + Platform Ops mode)
│   ├── bridge/               # C24                           (Order Execution — Windows-bound, isolated)
│   └── platform/            # C31-C39                       (Observability, Gateway, Scheduler, Identity, Secrets)
├── packages/                 # Shared, versioned, internal libraries — never a service
│   ├── kernel/               # ADR-0014's seven type groups: Symbol, Timeframe, Timestamp,
│   │                         # AsOf, Money/Quantity/Price/Bps, EventEnvelope, Clock,
│   │                         # Result[T,E], Staleness/Confidence/Probability, TenantId/AccountId
│   ├── schemas/              # Generated Pydantic models from the schema registry (ADR-0040) —
│   │                         # the ONE place a wire-format type is defined
│   ├── testkit/              # Shared test fixtures: the Simulation Harness's fixed seeds,
│   │                         # the fail-closed chaos-suite helpers, the replay-determinism assertions
│   └── observability/        # Shared logging/tracing/metrics setup, one config, every service imports it
├── contracts/                 # Machine-checkable wire contracts — NOT the Architecture/contracts/
│   │                         # markdown layer (that stays in Architecture/). This is the eventual
│   │                         # home of the Schema Registry's actual schema files (ADR-0040, C37)
│   └── events/                # One file per event subject family, generated from
│                              # Architecture/generated/15_Event_Catalog_v2.md
├── infra/                     # Deployment definitions
│   ├── compose/               # docker-compose.yml per environment (ADR-0008)
│   └── terraform/             # Only if/when a cloud target needs declared infra — not day one
├── tests/                     # Cross-service tests that don't belong to one service
│   ├── integration/
│   ├── contract/
│   ├── replay/                # Against the Simulation Harness (C28)
│   └── chaos/                 # The fail-closed suite (review/R15_Security.md §10)
├── scripts/                    # Operational one-offs: DB migrations runner, backfill triggers
├── research/                   # Notebooks, backtests, model experiments — NEVER imported by services/
│   │                          # (a one-way dependency: research reads services' public APIs,
│   │                          # services never import research/)
└── docs/                       # A symlink or thin pointer to Architecture/ and Blueprint/,
                                # NOT a duplicate — this repository's docs/ never restates
                                # what Architecture/ already canonically states
```

## 3. The rule that keeps `services/` from becoming a monolith by accident

`packages/kernel` and `packages/schemas` are the **only** cross-service imports permitted. A linter rule (wired into CI per `Testing_Blueprint.md` §6) fails any `import` from one `services/*` directory into another — **all cross-service communication is over the event bus or a published HTTP/gRPC API, never a Python import**, mirroring the "no context reads another context's tables" rule (ADR-0010 binding rule 1) at the code level, not just the data level.

## 4. Directory-to-bounded-context map

| `services/` group | Bounded context(s) | Containers | Deployment host class (`../Architecture/generated/16_Container_Model_v2.md` §5) |
|---|---|---|---|
| `edge/` | BC1 Market Data, BC2 Reference Data | C01, C02, C03, C04 | Linux, cloud, only group with inbound internet |
| `data/` | BC3 Feature Engineering | C06, C07, C08 | Linux, cloud, high IO |
| `quant/` | BC4 Market Intelligence | C09-C14, C28 | Linux, cloud, CPU/GPU |
| `decision/` | BC5 Deliberation, BC9 Learning, **BC12 Portfolio Construction** | C15-C20, C27, C30, **C40** | Linux, cloud |
| `capital/` | BC6 Risk Authorisation, BC7 Portfolio, BC10 Platform Ops (mode) | C21, C22, C23, C25, C26 | Linux, cloud, isolated network segment (VAULT, `../Architecture/21_Security_Architecture.md`) |
| `bridge/` | BC8 Order Execution | C24 | **Windows VPS**, active/standby with lease |
| `platform/` | BC10 Platform Ops, BC11 Identity & Governance | C31-C39 | Linux, cloud, shared services |

## 5. What is deliberately NOT in this repository

- **Broker credentials, API keys, any secret.** `services/capital/` and `services/bridge/` read secrets from the Secrets Manager (C38) at runtime; nothing is checked in, ever (`../Architecture/21_Security_Architecture.md` §4).
- **Trained model artefacts.** Stored in MLflow's own backing store (S3/MinIO-compatible), referenced by ID, never committed as a binary blob.
- **Raw market data.** Lives in the Iceberg lakehouse (ADR-0003), not the repository.
- **A second copy of anything in `../Architecture/`.** `docs/` points at it; nothing here restates it.

## 6. Related

- `Package_Blueprint.md` — the internal structure of every `services/*` and `packages/*` directory above
- `Service_Catalog.md` — the full 40-container inventory this layout organises
- `../Architecture/generated/16_Container_Model_v2.md` §5 — the deployment grouping this layout is directly derived from
- `../Architecture/decisions/0001-python-as-primary-language.md`, `../Architecture/decisions/0008-docker-compose-over-kubernetes.md`, `../Architecture/decisions/0014-shared-kernel-limited-to-seven-types.md` — the ADRs this layout implements without revisiting
