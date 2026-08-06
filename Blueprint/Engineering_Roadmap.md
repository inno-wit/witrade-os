# Engineering Roadmap

**Blueprint deliverable:** B.12
**Rule:** relative complexity only, never a time estimate. Sequencing is derived strictly from the dependency graph already frozen in `../Architecture/19_Bounded_Context_Map.md` and `../Architecture/generated/16_Container_Model_v2.md` §6 (the ten-container minimum viable subset) — this document does not invent a new order, it makes the existing one executable.
**Status:** Blueprint v1.0, 2026-08-04

---

## 1. Implementation order, justified

| # | Phase | Bounded context(s) | Why it must come before the next phase |
|---|---|---|---|
| 1 | **Shared Contracts & Schemas** | `packages/kernel`, `packages/schemas` | Every other phase imports these on day one (`Package_Blueprint.md` §4 rule 1). Building anything before this exists means rework the moment two services need to agree on a `Money` type |
| 2 | **Event Backbone** | Infrastructure (NATS JetStream, ADR-0004) + the Clock (C05) | Every bounded context communicates only by event, command, or sync read model (ADR-0037, ADR-0010 binding rule 3). Nothing downstream can be wired without a bus to wire it to. The Clock ships here specifically because `../Architecture/generated/16_Container_Model_v2.md` §6 ranks it first for exactly this reason: "one hour of work, permanent protection of replay determinism. Do it first because retrofitting it means auditing every call site" |
| 3 | **Configuration & Platform Services** | BC10 (Platform Supervisor, Scheduler), BC11 (Identity, Secrets) | Every later service needs to know the platform mode before it may act (mode-gating is universal, `../Architecture/19_Bounded_Context_Map.md` BC10 row) and needs an identity to authenticate as (BC11). Building Risk or Execution before the Supervisor exists means building them with no mode gate to wire into later |
| 4 | **Data Platform** | BC1 Market Data, BC2 Reference Data | Nothing downstream has real data without this. BC2 specifically is ranked Tier 0 in `../Architecture/generated/16_Container_Model_v2.md` because "position sizing is arithmetically impossible without contract size, tick value, lot step, and margin" |
| 5 | **Feature Store** | BC3 Feature Engineering | Depends on BC1/BC2 existing and publishing. Every Research Platform engine depends on this |
| 6 | **Research Platform** | BC4 Market Intelligence (Regime, Volatility, Structure, ML/RL) | Depends on Feature Store. Nothing in Deliberation can run without at least one of these engines publishing |
| 7 | **Evidence Graph** | BC5 (the graph specifically, C15) | Depends on BC4 publishing. Must exist before the Committee, because the Committee reads graph slices, never raw engine output (page 17, ADR-0041) |
| 8 | **AI Investment Committee** | BC5 (Committee, C16), plus the LLM Gateway and Prompt Registry it depends on | Depends on the Evidence Graph. Produces the `TradeProposal` every downstream phase consumes |
| 9 | **Portfolio Construction** | BC12 | Depends on BC5's proposals and a read model from BC7 (which does not yet exist at this point in the sequence — see the note below) and BC6 (built next). **Sequencing nuance, addressed explicitly:** BC12 is built here structurally, but its `get_budget_snapshot()` call to BC6 and `get_snapshot()` call to BC7 mean its *first working version* can only be smoke-tested once phase 10 lands. This is normal for the CQRS read-model pattern (ADR-0012) and does not block writing BC12's code now |
| 10 | **Risk Platform** | BC6 Risk Authorisation, BC7 Portfolio (Ledger) | Both ship together because BC6's synchronous `GetPortfolioSnapshot` call (30ms, fail-closed) has no meaning without BC7 existing to answer it. This is the single most safety-critical phase — `../Architecture/contracts/README.md`'s own reading-order advice ("One file only: 10... the largest concentration of things that are expensive to get wrong") applies with full force here |
| 11 | **Execution Platform** | BC8 Order Execution, plus the OMS | Depends on BC6 issuing a real `AuthorisedOrder`. Cannot be meaningfully tested before phase 10 completes |
| 12 | **Learning Platform** | BC9 Learning | Depends on BC7 (trade history) and BC8 (fills) existing to learn from. Correctly last among the core contexts — `../Architecture/00_Master_Architecture.md`'s own layering already places Continuous Learning downstream of everything it observes |
| 13 | **Observability** | Cross-cutting (C31, and every dashboard panel named in `Observability_Blueprint.md`) | Deliberately threaded through every phase above, not deferred to the end as a single phase — every service ships with health checks and metrics from phase 1 onward (`Service_Catalog.md` §1). What lands specifically at this position is the aggregation layer: dashboards, alert routing, runbooks — the parts that need every upstream metric already flowing to be meaningful |
| 14 | **Infrastructure** | Deployment mechanics (`Deployment_Blueprint.md`) | Also threaded throughout (every phase needs `dev`/`ci` to exist from day one), with the `paper` and `prod` environment promotion gates specifically landing once phases 1-12 are individually provable in `research` |
| 15 | **Dashboard & User Interfaces** | `apps/dashboard`, `apps/cli` | Correctly last — a dashboard for a platform that does not yet make decisions has nothing to show. Every panel in `Observability_Blueprint.md` §4 depends on the phase that produces its data existing first |

**This is not fifteen sequential, gated releases.** Phases 13-14 (Observability, Infrastructure) run continuously alongside 1-12, not after them — the table states dependency order for when each phase's *distinct, novel* work is ready to be the main focus, not a strict "nothing else happens until this phase closes" rule. Phase 15 is the one genuine "wait until the end" phase.

---

## 2. Per-phase detail: dependencies, prerequisites, deliverables, acceptance criteria, risk, complexity

### Phase 1 — Shared Contracts & Schemas

| Field | Detail |
|---|---|
| Dependencies | None |
| Prerequisites | `../Architecture/freeze/Architecture_Freeze_v1.md` certified (done, 2026-08-04) |
| Deliverables | `packages/kernel`, `packages/schemas` fully implemented per `Schema_Blueprint.md` |
| Acceptance criteria | Every type in `Schema_Blueprint.md` §1-13 exists, unit-tested, importable by a stub consumer |
| Risks | Under-scoping the kernel invites every later service to invent its own `Money` type — mitigate by treating `Package_Blueprint.md` §4 rule 1 as a CI-enforced lint from day one |
| Complexity | **Low.** Well-specified, no external dependency, no design decision left open |

### Phase 2 — Event Backbone

| Field | Detail |
|---|---|
| Dependencies | Phase 1 |
| Prerequisites | NATS JetStream cluster (3 nodes minimum, ADR-0004) provisioned |
| Deliverables | Cluster running, envelope/streams/DLQ/ack-policy configured exactly per `../Architecture/generated/15_Event_Catalog_v2.md` §3, §6; the Clock (C05) library |
| Acceptance criteria | A synthetic publish/consume round-trip on every stream tier, DLQ routing verified by forcing `max_deliver` exhaustion in a test |
| Risks | Retention/replica misconfiguration is invisible until a real incident needs it — mitigate with a chaos test that kills a NATS node and verifies no message loss |
| Complexity | **Low-medium.** Configuration-heavy, not logic-heavy |

### Phase 3 — Configuration & Platform Services

| Field | Detail |
|---|---|
| Dependencies | Phases 1-2 |
| Prerequisites | None beyond those |
| Deliverables | Platform Supervisor (C26) with the mode state machine (SM-1); Scheduler (C35); Identity (C39) + Secrets (C38) |
| Acceptance criteria | Every later service can call `get_mode()` and `authorize()` and get a real answer, even with nothing else built yet |
| Risks | Building this too thin (mode as a stub returning `NORMAL` always) defeats its purpose — mitigate by implementing the full SM-1 transition table from `../Architecture/review/R07_State_Machines.md` §2 in phase 3, not deferring it |
| Complexity | **Medium.** SM-1's ten states are non-trivial; everything else in this phase is comparatively simple |

### Phase 4 — Data Platform

| Field | Detail |
|---|---|
| Dependencies | Phases 1-3 |
| Prerequisites | Vendor API credentials (MT5, Databento, Polygon), Iceberg-on-MinIO provisioned (ADR-0003) |
| Deliverables | Ingestion (C01), Untrusted Text ACL (C02) — only if the news feed is connected, Quality Engine (C03), Instrument Master (C04) |
| Acceptance criteria | A real bar flows from a live vendor feed through quality scoring into the lakehouse, queryable point-in-time |
| Risks | Connecting the news feed before the Text ACL is production-hardened re-opens B5 — mitigate by literally not connecting the feed until C02 passes the prompt-injection test corpus (`../Architecture/21_Security_Architecture.md` §10) |
| Complexity | **Medium-high.** Multiple external vendor integrations, each with its own failure modes |

### Phase 5 — Feature Store

| Field | Detail |
|---|---|
| Dependencies | Phase 4 |
| Deliverables | Feature Materialiser (C06), Feature Serving (C07) |
| Acceptance criteria | `get_features(symbol, tf, as_of)` returns a point-in-time-correct vector, verified by a look-ahead-bias test that deliberately tries to leak a future bar |
| Risks | Point-in-time correctness is the platform's most safety-critical data property outside the capital plane — mitigate with the leakage test as a permanent CI gate, not a one-time check |
| Complexity | **Medium.** The materialise/serve split adds real complexity over a naive single-path design, and that complexity is deliberate (train/serve skew detectability) |

### Phase 6 — Research Platform

| Field | Detail |
|---|---|
| Dependencies | Phase 5 |
| Deliverables | Regime (C09), Volatility (C10), Structure (C11), Model Training/Inference/Monitor (C12-14) |
| Acceptance criteria | Every engine publishes its `evt.*.updated` subject on a real feature vector; the Model Registry (`../Architecture/20_Model_Registry.md`) governs promotion from day one, not retrofitted later |
| Risks | Building models before the registry's SM-5 gate exists invites a "just this once" fast path — mitigate by sequencing Phase 6's model work to depend on the registry's promotion gate being live first, even though the registry container itself is formally listed under Phase 8 |
| Complexity | **High.** This is genuinely novel quantitative engineering, not scaffolding |

### Phase 7 — Evidence Graph

| Field | Detail |
|---|---|
| Dependencies | Phase 6 |
| Deliverables | Evidence Graph Service (C15) per `../Architecture/17_Evidence_Graph.md` in full |
| Acceptance criteria | A sealed graph with a computed `graph_baseline_posterior`, content-hash-stable across two identical runs (`Testing_Blueprint.md` §3) |
| Risks | Skipping the deterministic-edge-derivation discipline and letting an LLM assert an edge "just to get something working" defeats the whole subsystem's purpose — mitigate by not building the Committee (Phase 8) until this phase's edge rule table is complete, so there's no working LLM path to be tempted to shortcut into |
| Complexity | **High.** The weighting/propagation/contradiction-classification logic is intricate and safety-relevant |

### Phase 8 — AI Investment Committee

| Field | Detail |
|---|---|
| Dependencies | Phase 7 |
| Deliverables | Committee (C16), LLM Gateway (C17), Prompt & Policy Registry (C18) — the Model Registry generalised per ADR-0042 |
| Acceptance criteria | A full six-desk cycle produces a schema-valid `TradeProposal` with citations resolving to real graph nodes (ADR-0013), inside the 10s latency budget |
| Risks | The single highest-cost-if-wrong phase for LLM spend and prompt-injection exposure — mitigate by wiring the Cost Governor (C30) and the Text ACL (C02, if news is connected) before this phase's first live LLM call, not after |
| Complexity | **Highest in the roadmap.** `../Architecture/ROADMAP.md` itself calls this "the highest design effort page in the ADD," and that carries through to implementation |

### Phase 9 — Portfolio Construction

| Field | Detail |
|---|---|
| Dependencies | Phase 8 (proposals) — first full test after Phase 10 |
| Deliverables | Portfolio Construction Engine (C40) per `../Architecture/18_Portfolio_Construction.md` |
| Acceptance criteria | Candidate ranking and allocation logic unit-tested against synthetic candidate pools before Phase 10's real budget snapshot exists; the displacement/dwell-time race (`../Architecture/review/R20_Architecture_Freeze.md` §4's W12 sequence) specifically tested |
| Risks | The one context where a subtle bug could look like an authorisation bypass even though it structurally cannot be one — mitigate with the credential-isolation test extension (`Testing_Blueprint.md` §4) as a Phase 9 exit gate, not deferred |
| Complexity | **Medium-high.** Genuinely new algorithmic work (the scoring/ranking model), but bounded and well-specified |

### Phase 10 — Risk Platform

| Field | Detail |
|---|---|
| Dependencies | Phase 9 (candidates), but is the phase that makes Phase 9 fully testable |
| Deliverables | Risk Engine (C21), Position Ledger (C22) |
| Acceptance criteria | The full gate-then-sizing-then-issuance chain (`../Architecture/review/R11_Risk_Architecture.md` §3) passes every stress scenario in that section, the three-tier kill switch passes the fail-closed chaos suite, exits are verified structurally exempt from every entry-only gate (ADR-0019) |
| Risks | The single most consequential phase in the entire roadmap — a defect here is the platform's primary path to a large, fast loss. Mitigate with the reading-order discipline `../Architecture/contracts/README.md` already states: this phase gets the most review attention of any phase, full stop |
| Complexity | **Highest tied with Phase 8**, for different reasons — not algorithmically novel, but the blast radius of a defect is larger than anywhere else in the platform |

### Phase 11 — Execution Platform

| Field | Detail |
|---|---|
| Dependencies | Phase 10 |
| Deliverables | Execution Service (C24), OMS (C23), Reconciliation (C25) |
| Acceptance criteria | Idempotent order submission verified under forced redelivery, leader-lease failover tested by killing the active instance, `UNPROTECTED` position detection verified with a synthetic no-stop fill |
| Risks | The Windows-VPS-bound bridge is the platform's single point of physical infrastructure fragility — mitigate by building the standby lease handover (`Deployment_Blueprint.md` §2) as a Phase 11 exit gate, not a later hardening pass |
| Complexity | **High.** Broker integration is inherently messy (partial fills, requotes, `UNKNOWN` states) |

### Phase 12 — Learning Platform

| Field | Detail |
|---|---|
| Dependencies | Phase 11 (needs real fills and trade history to learn from) |
| Deliverables | Continuous Learning (C27) |
| Acceptance criteria | A generated hypothesis passes PBO/DSR gating in a test before this phase is considered done — the gate must reject a deliberately overfit synthetic hypothesis in CI |
| Risks | Lowest capital-risk phase in the roadmap (BC9 has no write authority, ADR-0010), but a broken PBO/DSR gate here silently reintroduces every risk the gate exists to prevent — mitigate with the rejection test above as a permanent regression test |
| Complexity | **Medium.** Statistically involved, but low blast radius bounds the engineering risk |

---

## 3. Sprint breakdown, relative complexity only

No dates. Each phase above is broken into sprint-sized units by relative complexity (S/M/L/XL, not story points tied to a calendar).

| Phase | Sprint-sized units | Relative sizes |
|---|---|---|
| 1 Shared Contracts | 1 unit | S |
| 2 Event Backbone | 1 unit | S |
| 3 Platform Services | 2 units (Supervisor+SM1; Identity+Secrets) | M, S |
| 4 Data Platform | 3 units (Ingestion; Quality; Instrument Master + Text ACL) | M, M, M |
| 5 Feature Store | 2 units (Materialiser; Serving) | M, M |
| 6 Research Platform | 4 units (one per engine family: Regime, Volatility, Structure, ML/RL+Registry) | L, L, L, XL |
| 7 Evidence Graph | 2 units (node/edge/weighting; contradiction+precedent+explainability) | XL, L |
| 8 AI Committee | 3 units (Gateway+Registry; six desks; consensus+conflict) | L, XL, L |
| 9 Portfolio Construction | 2 units (scoring/ranking; displacement+lifecycle) | L, M |
| 10 Risk Platform | 3 units (gate chain; sizing chain; kill switch+ledger) | XL, L, XL |
| 11 Execution Platform | 3 units (broker adapter; OMS; reconciliation) | L, L, M |
| 12 Learning Platform | 1 unit | M |

**The four XL units (Research/ML+Registry, Evidence Graph core, Committee's six desks, Risk's gate chain and kill switch) are where estimation risk concentrates.** `Technical_Debt_Register.md` treats each as a named risk, not a generic "this might take longer" caveat.

---

## 4. Related

- `../Architecture/generated/16_Container_Model_v2.md` §6 — the ten-container MVS this roadmap's early phases are built from
- `../Architecture/freeze/ADR_Index.md` §4 — the 25 P0 ADRs each phase's acceptance criteria draws its hard constraints from
- `Technical_Debt_Register.md` — the risks named per phase above, tracked with mitigations
- `Production_Readiness.md` — the gate this roadmap's Phase 11 must clear before `prod` entry
