# 09 — Decision Intelligence Layer, contract completion

**Delta against:** `../09_Decision_Intelligence_Layer.md` (unmodified)
**Adds:** Owns, Invariants, Interfaces, Degraded Mode, SLO, Security Boundary
**Containers:** C15 Evidence Graph + C19 Decision Saga + C20 Decision Record Store · **Context:** Deliberation (BC5) · **Criticality:** C19 Tier 1, C20 Tier 0 · **Group:** Decision
**Highest-value field for this page (R05 §11):** **Interfaces, plus a verb change.** This layer **proposes**. It does not approve (closes B4)

---

## The verb change, first

Page 09's pipeline ends `-> Decision (approve / reject / defer)` and its Outputs section works hard to explain that this "Decision" is not Risk Management's "Approved Trade": one decides whether the recommendation is sound, the other whether the portfolio can accept it, and both must say yes.

That distinction is real and correct. The problem is the word. Two components in the same platform both documented as approving trades is blocking defect B4, and the failure it produces is not a documentation confusion: it is a code path where something other than the Risk Engine emits an artefact that looks like an authorisation and Execution acts on it.

**Resolution:** this layer emits a `TradeProposal`. Only the Risk Engine emits an `AuthorisedOrder`, and only that carries a signed, single-use token that Execution will accept (ADR-0011). The distinction page 09 explains in prose becomes a type distinction, and the intent is preserved exactly.

## The governing rule, preserved

> **The AI reasons. It does NOT calculate. Python calculates.**

Page 09 calls this the single most important architectural constraint in the platform and it is right. Every invariant below is built to make it mechanically true rather than a rule people remember. Invariant 3 is where it becomes a property: if a desk can only cite references and the platform resolves the values, an LLM computing a number has nowhere to put it.

## Owns (exclusive write access)

| Asset | Owner | Note |
|---|---|---|
| `evidence_graphs` (Postgres + content-addressed blobs in MinIO) | **C15 only** | Immutable, hash-addressed |
| `evidence_nodes`, `evidence_edges` | C15 | With provenance per node |
| `decision_cycles` (Postgres) | **C19 only** | One row per `cycle_id`, the saga state |
| `trade_proposals` | C19 | Immutable once issued |
| `explanations` | C19 | Rendered from lineage, never re-summarised |
| `decision_records` (append-only, hash-chained) | **C20 only** | `UPDATE`/`DELETE` revoked at the role level |

C20 is separate from C31 Observability by design (ADR-0039, closes D9). Page 13 places the Journal in the observability tier alongside operational ledgers with no immutability guarantee, which means the record you would need in a dispute sits in a table anyone can update. Observability is lossy, downsampled, short-retention and mutable by design. An audit record must be none of those.

**The test of correctness for C20:** if the entire observability stack were deleted, the platform's forensic record must be intact.

## Invariants

1. **This layer never issues an authorisation.** It issues a `TradeProposal`. No component other than the Risk Engine can produce an artefact that Execution will act on.
2. Every proposal carries a complete evidence lineage: the `evidence_graph_hash`, every `cycle_id`, every model and prompt version, and the `as_of` of each input.
3. **No number in a proposal or an explanation is authored by an LLM.** Every value resolves to a deterministic engine output through an evidence reference. This is the governing rule made mechanical (ADR-0013).
4. The explanation is **rendered from** the lineage object, never regenerated from the decision. Page 09 identifies this and it is preserved as an invariant because it eliminates explanation drift by construction rather than by testing.
5. Evidence graph construction is deterministic. The same inputs produce the same graph hash. A new upstream field requires an explicit schema update: never silent inclusion, never silent exclusion.
6. **Every proposal carries `valid_until`, and it is shorter than the triggering bar interval.** An expired proposal is dead, emits `evt.decision.expired.v1`, and can never be executed late (closes D3).
7. A cycle has exactly one terminal state, always recorded: `PROPOSED`, `NO_ACTION`, `EXPIRED`, or `ABORTED`. A cycle that ends without a terminal state is a defect, not an absence.
8. Portfolio state used for impact analysis is the **published read model** from the Ledger, `as_of`-stamped. Never a call into the Risk Engine (closes B3).
9. Every decision record is written before its proposal is published. An unrecorded decision cannot influence capital.

Invariant 8 is the correction to page 09's Recovery Strategy. That page resolves the staleness risk by having this layer and the Risk Engine "read the same live state source", so that if state is stale both are stale together, consistently rather than divergently. The reasoning is sound and the implementation creates the cycle: Committee desks reading Risk state makes the dependency graph circular and every cycle unreplayable. A published, versioned read model from the Ledger gives the same consistency property with an acyclic graph, and additionally lets a consumer detect that it read a stale snapshot, which a shared live source does not.

## Interfaces

### C15 Evidence Graph

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Command | `assemble(symbol, timeframe, as_of, trigger) -> EvidenceSnapshot` | Yes | 800ms | service (C19) |
| Query | `get_snapshot(hash) -> EvidenceSnapshot` | Yes | 100ms | service, auditor |
| Query | `resolve(evidence_ref) -> Value` | Yes | 10ms | service |
| Query | `decisions_citing(node_id) -> [DecisionId]` | Yes | 2s | auditor, researcher |

`decisions_citing` is page 09's future expansion ("show me every decision that cited this SMC order block") and it is available immediately, because references rather than values make it a lookup instead of a text search. It is also what turns the evidence graph from a passthrough into an asset.

### C19 Decision Saga

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Command | `run_cycle(symbol, timeframe, trigger, as_of) -> CycleResult` | No | 15s | service (Scheduler, triggers) |
| Query | `get_proposal(decision_id) -> TradeProposal` | Yes | 50ms | service, auditor |
| Query | `get_explanation(decision_id) -> Explanation` | Yes | 100ms | service, operator |
| Query | `cycle_state(cycle_id) -> SagaState` | Yes | 20ms | service, operator |

### C20 Decision Record Store

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Command | `append(record) -> RecordRef` | Yes | 50ms | service |
| Query | `by_correlation(correlation_id) -> [Record]` | Yes | 2s | auditor |
| Query | `verify_chain(from, to) -> ChainVerdict` | Yes | 30s | auditor, operator |

```python
@dataclass(frozen=True)
class TradeProposal:
    decision_id: str
    correlation_id: str
    symbol: str
    direction: Literal["long", "short"]
    size_hint: Decimal | None          # a hint. Risk sizes. This is advisory
    stop_hint: Decimal | None
    target_hints: tuple[Decimal, ...]
    confidence: Decimal                 # calibrated, pooled
    evidence_graph_hash: str
    cycle_ids: tuple[str, ...]
    as_of: Timestamp
    valid_until: Timestamp              # invariant 6
    terminal_state: Literal["PROPOSED"]
```

`size_hint` is named a hint and typed as optional deliberately. Page 08 emits a `size_hint` and page 10 sizes the position. If the proposal carried an authoritative size, the sizing authority would be ambiguous in exactly the way the approval authority was.

## Degraded Mode

| Condition | Behaviour |
|---|---|
| Evidence graph incomplete on a non-critical section | Proceed, mark the section absent in the snapshot. Affected desk abstains |
| Evidence graph incomplete on a **critical** section (regime, volatility, structure) | **Cycle terminates `NO_ACTION`.** Never proceed on partial critical evidence |
| Committee unavailable or below quorum | `NO_ACTION`. **The platform does not fall back to proposing on quant signals alone** |
| Portfolio read model stale beyond 2s | Proceed to propose, marking `portfolio_stale=true`. **The Risk Engine rejects authoritatively downstream**, which is the correct place for that judgement |
| Risk preview unavailable | Proceed with `preview_unavailable=true`. Preview is advisory; `decide` is authoritative |
| **C20 unavailable** | **Hard stop. No proposal is issued.** Invariant 9: an unrecorded decision cannot influence capital |
| Saga exceeds its deadline | Terminate `EXPIRED`, emit `evt.decision.expired.v1`. Never extend a deadline mid-cycle |
| Explanation rendering fails | Proposal still issues. The explanation is retried and its absence is a P1. **A missing explanation never blocks an exit or a risk action** |

The C20 row is the strictest rule in this layer and it is worth being explicit about the trade. Making the audit store a hard dependency means an audit outage stops new entries. That is the intended behaviour: a platform that keeps trading while unable to record why is producing exactly the positions that will be impossible to explain afterwards. Exits are unaffected, because exits do not originate here.

## SLO

| Dimension | Target |
|---|---|
| C19 availability | 99.5% |
| C20 availability | 99.95% (higher: it gates proposal issuance) |
| Evidence assembly | p50 < 300ms, p95 < 600ms, p99 < 800ms |
| Deterministic stages combined (graph, impact, constraints) | p99 < 1s, per page 09's budget |
| Full cycle including committee | p99 < 15s |
| Correctness | **Zero proposals without a complete evidence lineage. Zero values in an explanation not resolvable from the graph** |
| Audit | Hash chain verifies end to end, checked daily. Zero decision records missing for an issued proposal |
| Replay | A cycle replayed from its snapshot hash produces the identical proposal |

## Security Boundary

| | |
|---|---|
| **Zone** | CORE. No inbound internet, no broker credentials, no vendor keys (C17 holds the only one) |
| **Callers permitted (C19)** | Scheduler and trigger events. **Never called by the Risk Engine or Execution.** Dependency direction is one-way and enforced by the container network policy, not only by convention |
| **Callers permitted (C20)** | Append: C19, C16, C17, C21, C24. Read: auditor, operator, researcher |
| **Secrets held** | Postgres, MinIO credentials. **The hash-chain checkpoint is published to a separate store the write path cannot reach** |
| **Trusts** | Deterministic engine output. **Trusts no LLM output as fact:** every citation resolves against the graph before it appears anywhere |
| **Immutability** | `UPDATE` and `DELETE` on `decision_records` are revoked at the Postgres role level. The application cannot rewrite history even if compromised |
| **Blob storage** | Evidence graphs, prompts and responses in MinIO with object lock, referenced by hash |

The separate checkpoint store is the detail that makes tamper-evidence real. A hash chain whose checkpoints live in the same database as the records proves only that the records are internally consistent, which is exactly what an attacker with write access would arrange.

---

## Related

- Source page, unmodified: `../09_Decision_Intelligence_Layer.md`
- `08_AI_Investment_Committee.contract.md` — the debate stage embedded in this pipeline
- `10_Risk_Portfolio_Platform.contract.md` — the sole authorisation authority downstream
- `../generated/15_Event_Catalog_v2.md` §4.8 — `decision.made` becomes `decision.proposal.issued`
- `../review/R09_Evidence_Graph.md` — nodes, edges, weighting, confidence propagation, contradiction
- `../decisions/0011-risk-engine-sole-authorisation-authority.md` — closes B4
- `../decisions/0012-portfolio-state-as-published-read-model.md` — invariant 8, closes B3
- `../decisions/0039-journal-is-an-audit-service-separate-from-observability.md` — C20, closes D9
