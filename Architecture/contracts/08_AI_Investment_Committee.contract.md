# 08 — AI Investment Committee, contract completion

**Delta against:** `../08_AI_Investment_Committee.md` (unmodified)
**Adds:** Owns, Invariants, Interfaces, Degraded Mode, SLO, Security Boundary
**Containers:** C16 Committee + C17 LLM Gateway + C18 Prompt Registry · **Context:** Deliberation (BC5) · **Criticality:** Tier 1 · **Group:** Decision
**Highest-value field for this page (R05 §11):** **Invariants.** Quorum, citation-by-reference, and the critical-staleness veto
**Note:** this is the page behind document defect D1. Where page 08 contradicts pages 04, 05, 06, 09 or 10, **page 08 is the one that is wrong**

---

## What page 08 gets right, and must not be lost

This is the highest-design-effort page in the ADD and it earns that. Four things here are better than most institutional designs manage, and every correction below is built to preserve them:

- **Desk isolation by construction.** Six separate API calls, not one mega-prompt simulating six personas. The boundary is structural (the context window literally does not contain the other engines' data) rather than an instruction a model can ignore. Almost nobody gets this right.
- **Deadlock resolves to no-trade, with the asymmetry argued explicitly.** A missed trade costs opportunity; a coin-flip trade costs capital.
- **Citation validation as a hard rejection**, not a soft warning, with a failed desk treated as abstaining rather than neutral.
- **Desk correlation monitored as a first-class health metric**, distinguishing expected correlation (Regime and Volatility share a GARCH fit) from suspicious correlation (Regime and Execution).

The corrections are: make citation validation impossible to fail rather than merely checked, break the two dependency cycles the desk table creates, and give the cycle a quorum rule and a cost bound.

## Owns (exclusive write access)

| Asset | Owner | Note |
|---|---|---|
| `committee_cycles` (Postgres) | C16 | One row per `cycle_id`, with the saga state |
| `desk_opinions` (Postgres + Decision Record Store) | C16 | Immutable once written |
| `desk_memory` (Postgres) | C16 | Last N cycles per symbol, `as_of`-filtered on read |
| `consensus_results`, `desk_weights` (versioned) | C16 | Weights are a **promotable artefact**, gated like a model |
| `llm_calls`, `llm_cache`, `cost_counters` | **C17 only** | No other component imports a vendor SDK |
| `prompts`, `prompt_versions`, `model_pins` | **C18 only** | Effective-dated, point-in-time resolvable |

## Invariants

### Structural

1. **A desk reads its evidence from an immutable Evidence Snapshot, never from a live API.** This closes B3. The desk table in page 08 has the Risk Desk reading live portfolio state from page 10 and the Execution Desk reading live conditions from page 11, which makes the dependency graph cyclic (Committee → Risk → Execution → Committee) and makes any cycle unreplayable. The Risk Desk reads the Portfolio read model published by the Ledger; the Execution Desk reads a liquidity snapshot. Both are `as_of`-stamped facts, not calls into services downstream of the committee.
2. **A desk citation is a reference to an evidence node, never a literal value.** Page 08 validates that a cited number appears in the desk's inputs. Referencing instead makes the failure inexpressible: a desk emits `evidence_ref: "ev:regime:XAUUSD:M15:2026-08-03T14:30Z#confidence"`, and the value is resolved by the platform from the snapshot. A hallucinated number has nowhere to live. This also removes the "citation-schema false negative" failure mode page 08 names, because a rounded number is no longer a mismatch, it is a resolution.
3. Six desks, six separate API calls. Never one prompt containing multiple personas. Never a desk seeing another desk's output before submitting its own (ADR-0026).
4. Every desk output is schema-valid before it reaches the Consensus Engine. A non-conforming response is an **abstention with a distinct reason code**, never a coerced parse and never a neutral vote.
5. Desk memory is `as_of`-filtered. A cycle replayed for 3 May sees only memory that existed on 3 May.

### Quorum and consensus

6. **A cycle requires a quorum of at least 4 of 6 desks submitting valid opinions.** Below quorum, the cycle terminates `NO_ACTION`. Page 08 has no quorum rule, which means five abstentions and one confident desk currently produces a recommendation from a committee of one.
7. **Abstention is not a neutral vote.** It is excluded from the vote and counted against quorum. Page 08 gets this right for citation failures; here it applies to every abstention cause (timeout, schema failure, stale input, budget refusal, engine down).
8. Confidence is calibrated before it is weighted. A raw self-reported LLM confidence is not a probability of being right (ADR-0028).
9. Pooling is log-odds with dependence discounting, not a naive weighted average. Six desks reading correlated inputs are not six independent opinions, and averaging them overstates certainty exactly when they are all wrong together.
10. Deadlock resolves to `NO_ACTION`. **No tiebreak mechanism toward taking a position exists anywhere in the codebase** (ADR-0021).
11. Desk weights are a versioned, PBO/DSR-gated artefact. Never a config constant, never hand-tuned.

### Staleness and evidence

12. **Critical staleness is a veto, not a discount.** If regime or volatility evidence exceeds its hard staleness bound, the cycle terminates `NO_ACTION` regardless of desk confidence. Page 08 requires desks to "discount" stale inputs, which is a soft response to a hard condition: a confident desk can discount a stale input and still dominate the vote.
13. Every desk opinion records the `prompt_version`, `model_version`, `evidence_snapshot_hash`, and `as_of` used. Without these a replay is not a replay (ADR-0030).
14. **No untrusted text ever reaches a desk.** Desks receive typed features. Prose from a news provider terminates at the ACL (ADR-0032, closes B5).

Invariants 2, 6 and 12 are the three with no counterpart in page 08, and each closes a path by which a wrong committee output becomes a real position.

## Interfaces

### C16 Committee

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Command | `convene(symbol, timeframe, trigger, as_of) -> CycleResult` | No | 10s | service (Scheduler, triggers) |
| Query | `get_cycle(cycle_id) -> CommitteeCycle` | Yes | 100ms | service, auditor |
| Query | `desk_health() -> [DeskHealth]` | Yes | 50ms | operator |
| Adapter | `DeskContract` protocol (L4.2) | — | — | — |

```python
class DeskContract(Protocol):
    name: str
    evidence_scope: frozenset[str]     # which snapshot sections it may read
    def build_prompt(self, snapshot: EvidenceSnapshot,
                     memory: DeskMemory, prompt_version: str) -> Prompt: ...
    def parse(self, response: RawResponse) -> DeskOpinion | Abstention: ...

@dataclass(frozen=True)
class DeskOpinion:
    desk: str
    stance: Literal["bullish", "bearish", "neutral"]
    raw_confidence: Decimal            # 0-100, uncalibrated
    calibrated_confidence: Decimal     # set by the platform, not the desk
    evidence_refs: tuple[str, ...]     # references, never values
    reasoning: str
    prompt_version: str
    model_version: str
    snapshot_hash: str
```

`evidence_scope` is the mechanical form of page 08's "reads exclusively from one engine". The snapshot is filtered to that scope before the prompt is built, so a desk cannot see out of its lane even if its prompt asks to.

### C17 LLM Gateway

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Command | `invoke_desk(desk, evidence_ref, cycle_id, as_of) -> DeskOpinion \| Abstention` | Yes | 8s | service (C16 only) |
| Query | `budget_status(scope) -> Budget` | Yes | 10ms | service |
| Query | `get_call(call_id) -> LlmCallRecord` | Yes | 100ms | auditor |

### C18 Prompt Registry

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Query | `resolve(desk, as_of) -> PromptVersion` | Yes | 10ms | service (C17) |
| Command | `publish(prompt, effective_from, model_pin, approver)` | Yes | 1s | operator, audited, shadow-validated |

C18 closes a look-ahead vector that page 03's careful feature-level discipline does not cover, because it operates through the prompt rather than through the data. Page 08 makes prompts implicitly editable and page 12 proposes revising them based on outcomes. Without effective-dated versions, replaying a decision from three months ago uses **today's** prompts, tuned on the outcomes of the very trades being replayed. The backtest runs, produces plausible numbers, and is contaminated in the optimistic direction, invisibly.

## Degraded Mode

| Condition | Behaviour |
|---|---|
| One desk times out or fails schema validation | Abstention with a reason code. Cycle continues **if quorum holds** |
| Fewer than 4 valid opinions | Cycle terminates `NO_ACTION`, emits `evt.committee.quorum.failed.v1` |
| Anthropic API circuit open | Every desk abstains, quorum fails, cycle terminates `NO_ACTION`. **The platform does not fall back to trading on quant signals without the committee** |
| Cost budget exceeded | New-entry cycles refused admission. **Exit-related and risk-related calls are never budget-blocked** |
| Evidence snapshot incomplete on a non-critical section | Affected desk abstains |
| Regime or volatility evidence critically stale | **Cycle terminates `NO_ACTION` regardless of desk confidence** (invariant 12) |
| Prompt Registry unavailable | **Hard failure.** No cycle runs. Running with an unresolvable prompt version means the cycle cannot be replayed, which makes it unauditable |
| Deadlock | `NO_ACTION`, emit `evt.committee.cycle.deadlocked.v1`. Tracked separately from quorum failure: deadlock is desks disagreeing, quorum failure is desks unavailable |

The circuit-open row states the tempting fallback explicitly in order to forbid it. When the LLM layer is down, the available quant signals still exist and it feels reasonable to trade on them. That is precisely the moment the platform would be removing its safety layer while already degraded, and the decision needs to have been made in advance, in writing, rather than at 3am.

## SLO

| Dimension | Target |
|---|---|
| Availability (C16) | 99.5%. Correctly lower than the trading path: no committee means no new entries, not unsafe entries |
| Full cycle, six desks | p50 < 6s, p95 < 9s, p99 < 10s |
| `invoke_desk` (C17) | p95 < 5s, p99 < 8s |
| Correctness | **Zero desk opinions containing a value not resolvable from the evidence snapshot.** Zero cycles with fewer than 4 valid opinions producing a recommendation |
| Cost | Within per-cycle and per-day budget 100% of the time. Zero unrecorded LLM calls |
| Replay | A cycle replayed with the same snapshot, prompt version, and model version produces the identical recommendation from cache. A cache miss in `sim` is a hard error, never a live call |
| **Calibration** | **Per-desk resolution above zero, reviewed monthly** |
| **Value** | **Committee-versus-deterministic-baseline on disagreement cases, over a rolling 200 decisions** |

The last two lines are load-bearing and unusual. Per-desk resolution near zero means that desk contributes nothing and should be removed. No edge over a deterministic baseline on the cases where they disagree means the entire LLM layer is decoration on top of the quant signals. **Together they are the only two metrics that make this committee falsifiable rather than assumed**, and they should survive every future revision of this page.

## Security Boundary

| | |
|---|---|
| **Zone** | CORE for C16 and C18. **C17 is the only egress path to any vendor and sits in the DMZ** |
| **Callers permitted** | C16 convened by Scheduler and trigger events. C17 callable only by C16. C18 readable only by C17 |
| **Secrets held** | **C17 holds the Anthropic API key and nothing else in the platform does.** C16 and C18 hold Postgres credentials only |
| **Egress** | C17 is egress-restricted to the vendor endpoint. All other CORE services have no outbound internet |
| **Trusts** | The evidence snapshot. **Trusts no model output as fact:** every desk output is schema-validated and every citation is resolved against the snapshot before use |
| **Prompt injection** | Closed structurally at the ACL (no prose reaches a desk). C17 adds a redundant check: any evidence field containing instruction-like patterns fails the call and raises P1 |
| **Privileged actions** | Publishing a prompt version requires an operator, an audit record, and a shadow run. Publishing desk weights requires the PBO/DSR gate and two approvers |

Two independent controls close B5 and that redundancy is intentional. The ACL is the real control: prose never crosses into CORE, so injection has no delivery path. The gateway check is the backstop for the case where a future change adds a text field to the snapshot without anyone noticing what they have re-opened.

---

## Related

- Source page, unmodified: `../08_AI_Investment_Committee.md`
- `09_Decision_Intelligence_Layer.contract.md` — the consumer of the recommendation, which proposes rather than approves
- `04_Regime_Engine.contract.md`, `05_Volatility_Engine.contract.md`, `06_Market_Structure_Engine.contract.md` — the abstention ladders desks inherit
- `../review/R10_Committee_Architecture.md` — quorum, calibration, log-odds pooling, Red Team, CRO Gate, cost model
- `../decisions/0026-six-isolated-desks-separate-api-calls.md` — invariant 3
- `../decisions/0013-citations-are-references-not-values.md` — invariant 2
- `../decisions/0027-log-odds-pooling-with-dependence-discounting.md` — invariant 9 and the value SLO
- `../decisions/0028-desk-confidence-is-calibrated-before-use.md` — invariant 8 and the calibration SLO
- `../decisions/0032-untrusted-text-becomes-typed-features-at-an-acl.md` — invariant 14, closes B5
