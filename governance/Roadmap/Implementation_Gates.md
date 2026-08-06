# Implementation Gates

**Purpose:** the thirteen mandatory gates (Gate 0 through Gate 12) implementation must pass through, each with objectives, entry/exit criteria, deliverables, acceptance criteria, required reviews, and artefacts produced.
**Relationship to `../../Blueprint/Engineering_Roadmap.md`:** that document is the canonical, dependency-justified sequencing (15 phases, reasoned individually in its §2). These thirteen gates map onto that sequencing rather than re-deriving it — where a gate number and a roadmap phase number appear to disagree, the roadmap's dependency justification governs which work can actually start when; the gate number is an executive checkpoint label, not a claim that gate N's work only begins after gate N-1's work fully ends. This is stated explicitly in §0 below to avoid exactly the kind of silent renumbering `../../Architecture/freeze/Canonical_Source_Validation.md`'s discipline exists to prevent.
**Status:** Active from Program Charter ratification, 2026-08-05.

---

## 0. How to read the gate-to-phase mapping

`../../Blueprint/Engineering_Roadmap.md` §1 states plainly that phases 13-14 (Observability, Infrastructure) run continuously alongside phases 1-12, not after them, and that Event Backbone (its phase 2) precedes Configuration & Platform Services (its phase 3) for a specific dependency reason (the Clock, which the Event Backbone phase ships, is needed before the mode-gate the Platform Services phase provides can be meaningfully tested). Gate 2 (Platform Foundation) and Gate 3 (Event Backbone) below are ordered to match the executive request this charter responds to; the actual build order within them follows the roadmap's own dependency chain, not this list's numbering. Each gate below states this explicitly where it applies.

| Gate | Roadmap phase(s) it corresponds to |
|---|---|
| 0 | Pre-Phase 1 (the freeze itself) |
| 1 | Phase 1 — Shared Contracts & Schemas |
| 2 | Phase 3 — Configuration & Platform Services |
| 3 | Phase 2 — Event Backbone |
| 4 | Phase 4 — Data Platform (+ Phase 5 Feature Store) |
| 5 | Phase 6 — Research Platform |
| 6 | Phase 7 — Evidence Graph |
| 7 | Phase 8 — AI Investment Committee (Decision Intelligence) |
| 8 | Phase 9 — Portfolio Construction |
| 9 | Phase 10 — Risk Platform |
| 10 | Phase 11 — Execution Platform |
| 11 | Phase 12 — Learning Platform |
| 12 | Phases 13-15 — Observability, Infrastructure, Dashboard/UI, plus `../../Blueprint/Production_Readiness.md`'s full checklist |

---

## Gate 0 — Architecture Freeze

**Objectives:** close the architecture phase; establish the certified baseline every later gate builds against.

**Entry criteria:** none (this is the program's origin gate).

**Exit criteria:** `../Architecture_Freeze/Architecture_Freeze_Certificate_v1.0.md` ratified; governance system (this repository) active.

**Deliverables:** 109 architecture files, 43 Accepted ADRs, 15 Blueprint documents, this governance system.

**Acceptance criteria:** every item in `../../Architecture/freeze/Architecture_Freeze_v1.md` §6 and §7 checked, with all open items (BC2/BC7 pages, data dictionary, Testing Strategy/Version fields) tracked as non-blocking technical debt, not silently dropped.

**Required reviews:** Architecture Review Board self-certification (`../Review_Board/Architecture_Review_Process.md`).

**Artefacts produced:** Architecture Freeze Certificate v1.0, Program Charter, this gate document.

**Status:** **CLOSED, 2026-08-04/05.**

---

## Gate 1 — Shared Contracts

**Objectives:** establish `packages/kernel` and `packages/schemas`, the only permitted cross-service import surface (`../../Blueprint/Repository_Architecture.md` §3).

**Entry criteria:** Gate 0 closed.

**Exit criteria:** every type in `../../Blueprint/Schema_Blueprint.md` §1-13 exists, unit-tested, importable by a stub consumer.

**Deliverables:** `packages/kernel` (Symbol, Timeframe, Timestamp, AsOf, Money/Quantity/Price/Bps, EventEnvelope, Clock, Result[T,E], Staleness/Confidence/Probability, TenantId/AccountId — ADR-0014's seven type groups), `packages/schemas` (generated Pydantic models from the schema registry, ADR-0040).

**Acceptance criteria:** per `../../Blueprint/Engineering_Roadmap.md` Phase 1 table.

**Required reviews:** code review only (`../Engineering_Handbook.md`) — no cross-context surface exists yet to require Architecture Review.

**Artefacts produced:** `packages/kernel`, `packages/schemas`, their test suites.

**Risk carried forward:** under-scoping the kernel invites later services to invent their own `Money` type — mitigated by a CI-enforced lint from day one (`../../Blueprint/Engineering_Roadmap.md` Phase 1).

---

## Gate 2 — Platform Foundation

**Objectives:** the Platform Supervisor (mode state machine, SM-1), Scheduler, Identity, and Secrets services — every later service's entry gate.

**Entry criteria:** Gate 1 closed. (Per §0 above, this gate's build may proceed alongside Gate 3's Event Backbone work; the roadmap sequences the Clock, part of Gate 3, before this gate's mode-gating is *testable*, not before this gate's code can be *written*.)

**Exit criteria:** every later service can call `get_mode()` and `authorize()` and receive a real answer.

**Deliverables:** Platform Supervisor (C26) with the full SM-1 ten-state transition table (`../../Architecture/review/R07_State_Machines.md` §2), Scheduler (C35), Identity (C39), Secrets (C38).

**Acceptance criteria:** SM-1 implemented in full, not stubbed to always return `NORMAL`.

**Required reviews:** Architecture Review for the mode state machine specifically (safety-relevant, gates every downstream authorisation path).

**Artefacts produced:** Platform Supervisor service, Scheduler, Identity/Secrets services, SM-1 conformance test suite.

---

## Gate 3 — Event Backbone

**Objectives:** the NATS JetStream cluster and the Clock (C05), the bus every bounded context communicates over.

**Entry criteria:** Gate 1 closed.

**Exit criteria:** synthetic publish/consume round-trip verified on every stream tier; DLQ routing verified by forcing `max_deliver` exhaustion.

**Deliverables:** 3-node NATS JetStream cluster (ADR-0004), envelope/streams/DLQ/ack-policy configured per `../../Architecture/generated/15_Event_Catalog_v2.md` §3/§6, the Clock library (C05).

**Acceptance criteria:** per `../../Blueprint/Engineering_Roadmap.md` Phase 2 table, including the chaos test that kills a NATS node and verifies no message loss.

**Required reviews:** Architecture Review for the Clock specifically — `../../Architecture/generated/16_Container_Model_v2.md` §6 calls it out as the one thing that must be done first because retrofitting it later means auditing every call site.

**Artefacts produced:** NATS cluster config, Clock library, replay-determinism test harness.

---

## Gate 4 — Data Platform

**Objectives:** real market data flowing, quality-scored, into the lakehouse and the Feature Store.

**Entry criteria:** Gates 1-3 closed.

**Exit criteria:** a real bar flows from a live vendor feed through quality scoring into the lakehouse, queryable point-in-time; `get_features(symbol, tf, as_of)` returns a point-in-time-correct vector, verified by a look-ahead-bias test.

**Deliverables:** Ingestion (C01), Untrusted Text ACL (C02, only if news feed connected), Quality Engine (C03), Instrument Master (C04), Feature Materialiser (C06), Feature Serving (C07).

**Acceptance criteria:** per `../../Blueprint/Engineering_Roadmap.md` Phases 4 and 5 combined.

**Required reviews:** Architecture Review, specifically to confirm TD1 (BC2's missing dedicated page, `../../Blueprint/Technical_Debt_Register.md`) is closed before this gate's BC2 work proceeds, and that the news feed is not connected until C02 passes the prompt-injection test corpus (`../../Architecture/21_Security_Architecture.md` §10).

**Artefacts produced:** live vendor integrations, quality-scoring pipeline, lakehouse tables, feature-serving API, look-ahead-bias CI gate.

---

## Gate 5 — Research Platform

**Objectives:** the differentiated quantitative core — Regime, Volatility, Structure, ML/RL engines.

**Entry criteria:** Gate 4 closed.

**Exit criteria:** every engine publishes its `evt.*.updated` subject on a real feature vector; the Model Registry governs promotion from the first model onward.

**Deliverables:** Regime Engine (C09), Volatility Engine (C10), Market Structure Engine (C11), Model Training/Inference/Monitor (C12-C14).

**Acceptance criteria:** per `../../Blueprint/Engineering_Roadmap.md` Phase 6 table.

**Required reviews:** Architecture Review — flagged as genuinely novel quantitative engineering, not scaffolding, per the roadmap's own complexity rating (High).

**Artefacts produced:** four production engines, Model Registry promotion gate wired live from this gate onward (not retrofitted).

---

## Gate 6 — Evidence Graph

**Objectives:** the deterministic, citable substrate the AI Committee reads from — never raw engine output directly.

**Entry criteria:** Gate 5 closed.

**Exit criteria:** a sealed graph with a computed `graph_baseline_posterior`, content-hash-stable across two identical runs.

**Deliverables:** Evidence Graph Service (C15) per `../../Architecture/17_Evidence_Graph.md` in full.

**Acceptance criteria:** per `../../Blueprint/Engineering_Roadmap.md` Phase 7 table.

**Required reviews:** Architecture Review, specifically checking no LLM-asserted edge exists in the graph — the deterministic-edge-derivation discipline is this gate's entire safety property.

**Artefacts produced:** Evidence Graph service, content-hash determinism test.

---

## Gate 7 — Decision Intelligence

**Objectives:** the AI Investment Committee, LLM Gateway, and Prompt & Policy Registry — the deliberation cycle that produces a `TradeProposal`.

**Entry criteria:** Gate 6 closed.

**Exit criteria:** a full six-desk cycle produces a schema-valid `TradeProposal` with citations resolving to real graph nodes (ADR-0013), inside the 10s latency budget.

**Deliverables:** Committee (C16), LLM Gateway (C17), Prompt & Policy Registry (C18, ADR-0042).

**Acceptance criteria:** per `../../Blueprint/Engineering_Roadmap.md` Phase 8 table.

**Required reviews:** Architecture Review, at the highest scrutiny level in the roadmap — `../../Architecture/ROADMAP.md` itself names this the highest design-effort page in the whole ADD, and the Cost Governor (C30) plus Text ACL (C02) must be wired before this gate's first live LLM call, not after.

**Artefacts produced:** Committee orchestrator, LLM Gateway, Prompt Registry, desk-isolation conformance test (six separate API calls, verified not one mega-prompt).

---

## Gate 8 — Portfolio Construction

**Objectives:** rank and allocate across concurrent `TradeProposal`s without ever crossing into authorisation.

**Entry criteria:** Gate 7 closed. First full integration test deferred to Gate 9 (BC12's `get_budget_snapshot()`/`get_snapshot()` calls need BC6/BC7 to exist — this is a normal CQRS read-model dependency, ADR-0012, not a blocker to writing BC12's code now).

**Exit criteria:** candidate ranking and allocation logic unit-tested against synthetic candidate pools; the displacement/dwell-time race (`../../Architecture/review/R20_Architecture_Freeze.md` §4 W12) specifically tested.

**Deliverables:** Portfolio Construction Engine (C40) per `../../Architecture/18_Portfolio_Construction.md`.

**Acceptance criteria:** per `../../Blueprint/Engineering_Roadmap.md` Phase 9 table.

**Required reviews:** Architecture Review, specifically the credential-isolation test extension (`../../Blueprint/Testing_Blueprint.md` §4) — this is the one context where a subtle bug could resemble an authorisation bypass even though it structurally cannot be one, and that structural guarantee must be independently verified, not assumed.

**Artefacts produced:** Portfolio Construction Engine, displacement-race test, synthetic candidate-pool test harness.

---

## Gate 9 — Risk

**Objectives:** the sole authorisation authority (ADR-0011) and the Portfolio Ledger it depends on. The single most safety-critical gate in the program.

**Entry criteria:** Gate 8 closed (candidates exist), and this gate is what makes Gate 8 fully testable in turn.

**Exit criteria:** the full gate-then-sizing-then-issuance chain passes every stress scenario in `../../Architecture/review/R11_Risk_Architecture.md` §3; the three-tier kill switch passes the fail-closed chaos suite; exits verified structurally exempt from every entry-only gate (ADR-0019).

**Deliverables:** Risk Engine (C21), Account & Position Ledger (C22). TD1's BC7 page must be closed before this gate's BC7 work proceeds.

**Acceptance criteria:** per `../../Blueprint/Engineering_Roadmap.md` Phase 10 table.

**Required reviews:** Architecture Review at maximum scrutiny — `../../Architecture/contracts/README.md`'s own stated reading-order advice names this "the largest concentration of things that are expensive to get wrong." No fast-path change control applies anywhere in this gate (`../Policies/Implementation_Change_Control.md`).

**Artefacts produced:** Risk Engine (single-leader with lease standby), Position Ledger (event-sourced), full stress-scenario test suite, three-tier kill switch chaos suite.

---

## Gate 10 — Execution

**Objectives:** get an authorised order to a broker and back, reliably, with idempotency and failover.

**Entry criteria:** Gate 9 closed (a real `AuthorisedOrder` exists to execute).

**Exit criteria:** idempotent order submission verified under forced redelivery; leader-lease failover tested by killing the active instance; `UNPROTECTED` position detection verified with a synthetic no-stop fill.

**Deliverables:** Execution Service (C24, Windows VPS-bound), OMS (C23), Reconciliation (C25).

**Acceptance criteria:** per `../../Blueprint/Engineering_Roadmap.md` Phase 11 table.

**Required reviews:** Architecture Review, specifically the standby lease handover (`../../Blueprint/Deployment_Blueprint.md` §2) as an exit gate for this phase, not a later hardening pass — the Windows-VPS bridge is the platform's single point of physical infrastructure fragility.

**Artefacts produced:** Execution service, OMS, Reconciliation service, lease-failover test, idempotency-under-redelivery test.

---

## Gate 11 — Learning

**Objectives:** close the loop — trade history and fills feed back into model and prompt revision.

**Entry criteria:** Gate 10 closed (fills exist to learn from); Gate 9 closed (trade history exists).

**Exit criteria:** per `../../Blueprint/Engineering_Roadmap.md` Phase 12 table, including PBO/DSR gating on every proposal this loop generates, without exception.

**Deliverables:** Continuous Learning service (C27).

**Acceptance criteria:** every proposal from this loop passes PBO/DSR gating before it can influence a live model or prompt.

**Required reviews:** Architecture Review, specifically checking that no learning-loop proposal bypasses the promotion gate `../../Architecture/20_Model_Registry.md` established at Gate 5 — this is the loop most exposed to silent overfitting if the gate is weakened "just this once."

**Artefacts produced:** Continuous Learning service, weekly retraining schedule, PBO/DSR gate conformance test.

---

## Gate 12 — Production Readiness

**Objectives:** the go/no-go gate for `paper -> prod` promotion — the point at which live capital becomes possible.

**Entry criteria:** Gates 1-11 closed. Observability and Infrastructure work (roadmap phases 13-14, threaded throughout) fully caught up to every prior gate's instrumentation requirements. Dashboard/UI (roadmap phase 15) complete.

**Exit criteria:** all 15 categories of `../../Blueprint/Production_Readiness.md` checked: Architecture, Infrastructure, Security, Observability, Testing, Deployment, Rollback, and the remaining categories in that document, in full.

**Deliverables:** `apps/dashboard`, `apps/cli`, aggregated observability (dashboards, alert routing, runbooks for every P0/P1 alert), the `dr` environment stood up and drilled, annual penetration test scheduled.

**Acceptance criteria:** zero P0 items outstanding in `../../Blueprint/Technical_Debt_Register.md`; every tripwire metric instrumented; fail-closed chaos suite passing for every dependency including all three Phase 11-originated subsystems.

**Required reviews:** full Architecture Review Board sign-off, explicitly, before the first `paper -> prod` promotion request is approved — this is the one gate where the review is not "does this change match the architecture" but "does the whole system, as built, match what Gate 0 certified it would be."

**Artefacts produced:** Production Readiness certification (dated, specific to the promotion request it gates), dashboard and CLI applications, DR runbook, full operational documentation set.

**What this gate is not:** authorisation for any specific trade or capital allocation. It is authorisation for the *platform* to be eligible for live capital. Per-strategy or per-account go-live remains a separate, later decision.

---

## Related

- `../../Blueprint/Engineering_Roadmap.md` — the canonical dependency-justified sequencing these gates map onto
- `../Standards/Definition_of_Ready.md`, `../Standards/Definition_of_Done.md` — the per-unit-of-work checklists inside each gate
- `../../Blueprint/Production_Readiness.md` — Gate 12's full exit checklist, in detail
- `../../Blueprint/Technical_Debt_Register.md` — the risk register every gate's acceptance criteria cross-check against
