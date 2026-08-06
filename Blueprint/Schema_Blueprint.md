# Schema Blueprint

**Blueprint deliverable:** B.6
**Grounded in:** `../Architecture/review/R03_Domain_Model_DDD.md` (aggregates, entities, value objects per bounded context) and `../Architecture/decisions/0014-shared-kernel-limited-to-seven-types.md`. This document translates those DDD definitions into implementation-ready Pydantic-style schemas — it does not redesign the data model, which is frozen.
**Status:** Blueprint v1.0, 2026-08-04
**Amended:** 2026-08-06 — `AuthorisedOrder` gains `token_expires_at`, added by [ADR-0044](../Architecture/decisions/0044-kill-switch-recheck-at-broker-send.md) §5 (see §7 below for the field and why `halt_epoch` binding was considered and rejected).
**Home in the repository:** `packages/schemas/` (per `Repository_Architecture.md` §2) and `packages/kernel/` for the seven shared type groups

---

## 1. Shared kernel types (used by every schema below)

```python
Symbol = NewType("Symbol", str)               # validated against BC2, never a bare string
Timeframe: Enum                                 # M1, M5, M15, H1, H4, D1, ... with duration + bar_close_time()
Timestamp = datetime                            # always UTC
AsOf = Timestamp                                # the look-ahead-bias guard type — see review/R03 §3

class Money(BaseModel):
    amount: Decimal                             # NEVER float (review/R03 §6)
    currency: str

class Quantity(BaseModel):
    value: Decimal
    instrument: Symbol

class Probability(float):                       # constrained [0,1], raises at construction if out of range
class Confidence(BaseModel):
    value: float                                # distinct type from Probability — review/R03 §3 invariant
    source: str
    calibrated: bool

class Staleness(BaseModel):
    is_stale: bool
    age_s: float
    max_age_s: float
    severity: Literal["ok", "warn", "critical"]

class EventEnvelope(BaseModel):                 # generated/15_Event_Catalog_v2.md §3
    subject: str
    correlation_id: str
    causation_id: str
    event_time: Timestamp
    logical_clock: int
    idempotency_key: str
    replay: bool
    replay_run_id: str | None
    env: Literal["prod", "staging", "sim"]
    tenant: Literal["default"]                  # ADR-0009, reserved seam
```

---

## 2. Market Data (BC1)

```python
class Bar(BaseModel):
    symbol: Symbol
    timeframe: Timeframe
    open: Decimal; high: Decimal; low: Decimal; close: Decimal
    volume: Decimal
    source: str
    bar_close_time: Timestamp
    quality_score: float | None                  # attached post-scoring, page 02

class QualityScore(BaseModel):
    dataset_id: str
    score: float
    tier: Literal["PASS", "FLAG", "REJECT"]
    detectors_run: list[str]                      # incomplete detector set caps at FLAG (contracts/02)
```

## 3. Features (BC3)

```python
class FeatureVector(BaseModel):
    symbol: Symbol
    timeframe: Timeframe
    as_of: AsOf
    category: Literal["technical", "regime", "smc", "volatility", "time", "macro", "alt_data", "cross_asset", "labels"]
    values: dict[str, float]
    feature_versions: dict[str, str]               # for provenance (page 17 node model)
```

## 4. Evidence Graph (BC5)

```python
class EvidenceNode(BaseModel):
    node_id: str                                   # {type}:{symbol}:{timeframe}:{as_of}:{field}
    type: Literal["Observation","Level","State","Forecast","Event","Constraint","PortfolioFact","Precedent","Derived"]
    value: dict
    as_of: AsOf
    source: dict                                    # {engine, version, params_ref}
    staleness: Staleness
    reliability: float
    weight: float
    provenance: dict                                 # {snapshot_id, feature_versions}

class EvidenceEdge(BaseModel):
    kind: Literal["SUPPORTS","CONTRADICTS","CONFLUENT_WITH","DERIVED_FROM",
                   "SHARES_MODEL_WITH","INVALIDATES","CONSTRAINS","PRECEDES","ANALOGOUS_TO"]
    from_node: str; to_node: str
    strength: float

class EvidenceGraph(BaseModel):
    graph_id: str
    content_hash: str                                # sha256, canonical serialisation (page 17 invariant 5)
    nodes: list[EvidenceNode]
    edges: list[EvidenceEdge]
    graph_baseline_posterior: dict[Literal["LONG","SHORT"], float]
    contradiction_report: list[dict]

class Citation(BaseModel):                           # ADR-0013 — a reference, never a value
    node_id: str
    node_hash: str
```

## 5. Portfolio Construction (BC12)

```python
class CandidateAllocation(BaseModel):
    candidate_id: str
    proposal_ref: str                                # decision_id this candidate came from
    opportunity_score: float
    diversification: float
    status: Literal["PENDING","RANKED","ADMITTED","DEFERRED","REJECTED","DISPLACED","EXPIRED"]
    allocated_risk_budget: Money | None
    opportunity_cost_note: str | None

class PortfolioAllocationPlan(BaseModel):
    plan_id: str
    as_of: AsOf
    candidates: list[CandidateAllocation]            # ranked order
```

## 6. Portfolio / Ledger (BC7)

```python
class Position(BaseModel):
    account_id: str
    symbol: Symbol
    net_qty: Quantity
    unrealised: Money

class Lot(BaseModel):                                 # FIFO/LIFO cost basis, review/R03 §7
    lot_id: str
    quantity: Quantity
    entry_price: Decimal
    entry_time: Timestamp

class LedgerEntry(BaseModel):                          # append-only, double-entry
    entry_id: str
    account_id: str
    cause: str
    counterparty: str
    amount: Money
    recorded_at: Timestamp

class PortfolioSnapshot(BaseModel):                    # the READ MODEL, never the aggregate itself
    account_id: str
    as_of: AsOf
    positions: list[Position]
    equity: Money
    margin_used: Money
```

## 7. Risk (BC6)

```python
class RiskAssessment(BaseModel):
    assessment_id: str
    proposal_ref: str
    rule_evaluations: list[dict]                       # [{rule_id, rule_version, verdict, reason, inputs_hash}]
    verdict: Literal["APPROVED", "REJECTED"]
    limit_set_version: str

class AuthorisedOrder(BaseModel):                        # the signed, single-use token
    authorisation_id: str
    proposal_ref: str
    size: Quantity
    valid_until: Timestamp                                # decision staleness: age of the market/portfolio
                                                            # snapshot the assessment was made against
    token_expires_at: Timestamp                            # authorisation staleness: mint_time + 2s default,
                                                            # distinct from valid_until (ADR-0044 §5). Checked
                                                            # by C24's send-time recheck (contract 11 inv. 19)
                                                            # in addition to, not instead of, valid_until.
    signature: str

# `halt_epoch` / generation-counter binding was considered for AuthorisedOrder and rejected
# (ADR-0044 §5, finding F5): once C24 performs a live three-tier kill-switch read at send time,
# a generation-counter comparison is strictly subsumed by it, and would require new monotonic-
# counter infrastructure in Postgres that nothing else in the design calls for. Do not re-propose
# without first showing the live recheck (invariant 19) is insufficient on its own.

class LimitSet(BaseModel):                                # immutable once published, dual-control (ADR-0024)
    limit_set_version: str
    max_loss_per_trade: Money
    max_daily_loss: Money
    max_drawdown: float
    effective_from: Timestamp
```

## 8. Orders / Trades (BC8)

```python
class Order(BaseModel):
    client_order_id: str                                  # deterministic, idempotent
    authorisation_ref: str                                  # must trace to a valid AuthorisedOrder
    state: Literal["NOT_SENT","SUBMITTED","ACKNOWLEDGED","PARTIALLY_FILLED",
                    "FILLED","CANCELLED","REJECTED","UNKNOWN"]              # SM-3, review/R07 §4

class Fill(BaseModel):
    fill_id: str
    client_order_id: str
    quantity: Quantity
    price: Decimal
    timestamp: Timestamp
    liquidity_flag: str
    commission: Money

class SlippageAnalysis(BaseModel):
    fill_id: str
    expected: Decimal
    actual: Decimal
    bps: float
    decomposed: dict[Literal["spread","delay","impact"], float]           # TCA decomposition, R19 §10
```

## 9. Models (BC4, Model Registry)

```python
class Artefact(BaseModel):                                # generalised across model/prompt/weight kinds
    artefact_id: str
    kind: Literal["model","rl_policy","prompt","desk_weight","ranking_weight"]
    slot: str
    version: str
    hash: str
    effective_from: Timestamp
    effective_to: Timestamp | None
    state: Literal["TRAINING","CANDIDATE","VALIDATING","VALIDATED","SHADOW",
                    "SHADOW_PASSED","CHAMPION","CHALLENGER","ROLLED_BACK","ARCHIVED",
                    "TRAINING_FAILED","REJECTED","SHADOW_FAILED"]         # SM-5, review/R07 §6
    tier: Literal[0, 1, 2]                                                # criticality, review/R11 §6
    eval_scores: dict[str, float]
```

## 10. Experiments (BC9, Learning)

```python
class Hypothesis(BaseModel):
    hypothesis_id: str
    target_context: str
    proposed_change: dict
    pbo: float
    deflated_sharpe: float
    status: Literal["proposed","validated","rejected"]
```

## 11. Audit (BC11, Decision Record Store)

```python
class AuditRecord(BaseModel):                             # append-only, hash-chained (R19 §7)
    record_id: str
    prev_hash: str
    content_hash: str                                       # sha256(prev_hash || canonical(record))
    actor: str
    action: str
    correlation_id: str
    before: dict | None
    after: dict | None
    recorded_at: Timestamp
```

## 12. Configuration

```python
class RiskLimitConfig(BaseModel):                          # versioned, dual-control (ADR-0024)
    limit_set_version: str
    values: dict[str, Decimal]
    approvers: list[str]                                     # >= 2 for a solo operator: delay + written justification
    dry_run_report_ref: str

class InstrumentSpec(BaseModel):                            # BC2, review/R19 §4
    symbol: Symbol
    tick_size: Decimal
    lot_step: Decimal
    min_lot: Decimal
    contract_size: Decimal
    margin_requirement: Decimal
```

## 13. Events

Every event payload is one of the types above (or a thin subset of one), wrapped in `EventEnvelope` (§1). No event invents a new ad hoc payload shape outside this file — `../Architecture/generated/15_Event_Catalog_v2.md`'s 85 subjects each map to one of the schemas in §2-12, generated as concrete Pydantic classes in `packages/schemas/events/`.

---

## 14. Schema governance

Every type in this file is generated from, and versioned alongside, the Schema Registry (C37, ADR-0040) once it exists. Until then, these are the hand-maintained source of truth `packages/schemas` implements directly — the same staged approach `../Architecture/17_Evidence_Graph.md` §9 already applies to graph storage (P0-P1 hand-built, P2+ promoted once volume justifies it).

---

## 15. Related

- `../Architecture/review/R03_Domain_Model_DDD.md` — the DDD source these schemas implement
- `../Architecture/decisions/0014-shared-kernel-limited-to-seven-types.md` — §1's governance
- `Event_Blueprint.md` — how these schemas move over the event bus
- `Interface_Definitions.md` — the service interfaces that consume/produce these types
