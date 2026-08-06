# Interface Definitions

**Blueprint deliverable:** B.7
**Rule:** interfaces only. No implementation. Every method signature below is the public contract a service exposes to the rest of the platform (per `Package_Blueprint.md` §1's `api/` module) — the body is deferred entirely to implementation.
**Status:** Blueprint v1.0, 2026-08-04

---

```python
from typing import Protocol
from packages.schemas import *  # types defined in Schema_Blueprint.md

# ── BC1/BC2 — Market Data & Reference Data ──────────────────────────────

class IngestionService(Protocol):
    async def get_bars(self, symbol: Symbol, timeframe: Timeframe,
                        range: tuple[Timestamp, Timestamp]) -> list[Bar]: ...

class QualityService(Protocol):
    async def get_quality_score(self, dataset_id: str) -> QualityScore: ...

class ReferenceDataService(Protocol):
    async def get_spec(self, symbol: Symbol) -> InstrumentSpec: ...
    async def is_tradable(self, symbol: Symbol, as_of: AsOf) -> bool: ...
    async def cluster_of(self, symbol: Symbol) -> str: ...

# ── BC3 — Feature Engineering ────────────────────────────────────────────

class FeatureStoreService(Protocol):
    async def get_features(self, symbol: Symbol, timeframe: Timeframe,
                            as_of: AsOf) -> FeatureVector: ...

# ── BC4 — Market Intelligence (one interface per engine, same shape) ────

class MarketIntelligenceEngine(Protocol):
    """Implemented separately by RegimeService, VolatilityService, StructureService."""
    async def get_view(self, symbol: Symbol, timeframe: Timeframe,
                        as_of: AsOf) -> dict: ...  # MarketView subset specific to the engine

class ModelInferenceService(Protocol):
    async def predict(self, model_id: str, features: FeatureVector) -> dict: ...  # {prediction, confidence}

# ── BC5 — Deliberation (Evidence Graph, page 17) ─────────────────────────

class EvidenceGraphService(Protocol):
    async def assemble(self, symbol: Symbol, timeframe: Timeframe,
                        as_of: AsOf) -> EvidenceGraph: ...
    async def slice(self, graph_id: str, desk: str) -> dict: ...  # GraphSlice
    async def explain(self, decision_id: str,
                       view: Literal["one_line","decision_card","full_trace","counterfactual"]) -> dict: ...
    async def ablate(self, graph_id: str, node_id: str) -> dict: ...  # HypotheticalPosterior, research-only

class CommitteeService(Protocol):
    async def convene(self, trigger: dict) -> str: ...  # returns cycle_id
    async def get_proposal(self, cycle_id: str) -> TradeProposal | None: ...

# ── BC12 — Portfolio Construction (page 18) ──────────────────────────────

class PortfolioConstructionService(Protocol):
    async def submit(self, proposal: TradeProposal) -> str: ...  # returns candidate_id
    async def rebalance(self) -> PortfolioAllocationPlan: ...
    async def get_plan(self, as_of: AsOf) -> PortfolioAllocationPlan: ...

# ── BC6 — Risk Authorisation (page 10) ───────────────────────────────────

class RiskService(Protocol):
    async def evaluate(self, candidate: CandidateAllocation,
                        mode: Literal["PREVIEW", "DECIDE"]) -> RiskAssessment | AuthorisedOrder: ...
    async def get_budget_snapshot(self) -> dict: ...  # RiskBudgetSnapshot, read model published to BC12

class KillSwitchService(Protocol):
    """In-process interlock, not a network call — listed for interface completeness."""
    def check(self) -> bool: ...  # True == HALTED. Checked last, no await after this point.
    def trip(self, scope: Literal["platform","account","symbol","strategy"], reason: str) -> None: ...
    def clear(self, scope: str, approvals: list[str]) -> None: ...  # dual control enforced by the caller

# ── BC7 — Portfolio (Ledger) ──────────────────────────────────────────────

class LedgerService(Protocol):
    async def get_snapshot(self, as_of: AsOf) -> PortfolioSnapshot: ...
    # Write side is event-sourced — no direct "set" method exists; state changes
    # only via consuming Fill events (Package_Blueprint.md §1's dependency rule).

# ── BC8 — Order Execution ─────────────────────────────────────────────────

class ExecutionService(Protocol):
    async def submit(self, order: AuthorisedOrder) -> Order: ...

class OMSService(Protocol):
    async def move_stop(self, position_id: str, new_stop: Decimal) -> None: ...
    async def partial_close(self, position_id: str, quantity: Quantity) -> None: ...
    async def request_exit(self, position_id: str, reason: str) -> None: ...

# ── BC9 — Learning ─────────────────────────────────────────────────────────

class LearningService(Protocol):
    async def propose_change(self, target_context: str, change: dict) -> Hypothesis: ...

# ── Model Registry (BC4 models + BC5 prompts/weights, page 20) ───────────

class ModelRegistryService(Protocol):
    async def resolve(self, artefact_kind: str, slot: str, as_of: AsOf) -> Artefact: ...
    async def register(self, artefact: Artefact, provenance: dict) -> str: ...  # returns artefact_id
    async def promote(self, artefact_id: str, approvals: list[str]) -> dict: ...  # PromotionRecord
    async def rollback(self, slot: str) -> dict: ...  # RollbackRecord, no approval required

# ── BC10 — Platform Operations ────────────────────────────────────────────

class PlatformSupervisorService(Protocol):
    async def get_mode(self) -> Literal["NORMAL","DEGRADED","HALTED","MAINTENANCE","RECONCILING"]: ...

# ── BC11 — Identity & Governance ─────────────────────────────────────────

class IdentityService(Protocol):
    async def authorize(self, identity: str, action: str) -> bool: ...
    async def record(self, audit_record: AuditRecord) -> None: ...

# ── Journal / Decision Record Store ───────────────────────────────────────

class JournalService(Protocol):
    async def append(self, record: AuditRecord) -> None: ...  # append-only, hash-chained
    async def query(self, correlation_id: str | None = None,
                     decision_id: str | None = None,
                     time_range: tuple[Timestamp, Timestamp] | None = None) -> list[AuditRecord]: ...

# ── Simulation & Replay Harness ───────────────────────────────────────────

class SimulationHarnessService(Protocol):
    async def run_backtest(self, period: tuple[Timestamp, Timestamp], seed: int) -> str: ...  # replay_run_id
    async def run_counterfactual(self, decision_id: str, override: dict) -> str: ...
    async def run_whatif(self, hypothetical_proposal: TradeProposal) -> RiskAssessment: ...
```

---

## Notes on this interface set

- **Every method is `async`** except `KillSwitchService.check()`, which is in-process and synchronous by design (ADR-0017) — the one deliberate exception, matching the architecture's own single deliberate exception to its async-everywhere norm.
- **No interface exposes a setter for another context's aggregate.** `LedgerService` has no `set_position()` — matching `../Architecture/review/R03_Domain_Model_DDD.md` §11 rule 6 ("no aggregate exposes a setter") at the service-interface level, not just the object level.
- **Every `Protocol` here is what `Package_Blueprint.md` §1 calls the `api/` module** — the only importable surface of its package. `domain/` internals never appear in this file.
- **This list is not exhaustive of every method a service will eventually need** (e.g., admin/config methods are omitted — those are covered by `API_Blueprint.md` §3's REST surface, not this internal interface layer). It is exhaustive of the *cross-context* calls the architecture specifies.

---

## Related

- `Schema_Blueprint.md` — every type referenced above
- `API_Blueprint.md` §2 — the network-level (gRPC) realisation of the synchronous calls among these interfaces
- `Package_Blueprint.md` §1 — where these interfaces live inside a service's own package structure
- `../Architecture/19_Bounded_Context_Map.md` — the per-context "External interfaces" column this file makes concrete
