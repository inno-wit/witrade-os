# 12 — Continuous Learning, contract completion

**Delta against:** `../12_Continuous_Learning.md` (unmodified)
**Adds:** Owns, Invariants, Interfaces, Degraded Mode, SLO, Security Boundary
**Container:** C27 (+ C28 Simulation Harness as its validation substrate) · **Context:** Learning · **Criticality:** Tier 2 · **Group:** Decision
**Highest-value field for this page (R05 §11):** **Invariants.** "No change reaches production without a PBO/DSR pass" must be a mechanical gate, not a policy

---

## What page 12 gets right, and must not be lost

- **The no-shortcut rule.** Every proposed change, including one the learning loop generated about itself, goes through the identical PBO and Deflated Sharpe Ratio gate as a brand-new strategy. The page argues why: "learning about itself" is precisely the scenario overfitting checks exist for. This is the single best decision on the page and most self-improving systems get it wrong.
- **Hypotheses must be falsifiable**, schema-enforced with concrete before/after values, not open-ended commentary.
- **Weekly cadence as a deliberate choice**, with the reasoning stated: running faster risks reacting to noise. Cadence slippage is alerted rather than silently tolerated.

The corrections are: make the gate a mechanism instead of a rule, close the attribution gap that makes half the loop's conclusions unreliable, and give the loop a source of truth that is not the observability tier.

## Owns (exclusive write access)

| Asset | Note |
|---|---|
| `reviews` (Postgres) | One row per review cycle, with the window and inputs used |
| `hypotheses` | Schema-validated, each with a concrete falsifiable claim |
| `experiments`, `experiment_results` | Every run's PBO/DSR output, pass or fail |
| `research_backlog` | Validated changes awaiting human promotion |
| `desk_accuracy`, `desk_correlation` | Per-desk calibration history |

**This service writes nothing that reaches production directly.** It proposes. Promotion is a dual-controlled action in C12 (models) or C16 (desk weights), and deployment is human-gated per page 14. The learning loop has no write path to anything that trades, and that is the property that makes it safe to let it run unattended.

## Invariants

1. **No hypothesis becomes a backlog item without a recorded passing PBO and DSR result.** Enforced by the backlog API rejecting an item whose experiment record lacks one. Not by review discipline, not by a checklist. There is no operator override, because the operator is the person the loop is most likely to persuade.
2. The gate applies identically to model changes, desk weight changes, prompt changes, threshold changes, and rule parameter changes. **Anything fitted to historical outcomes is a model** (extends `07_ML_RL_Model_Layer.contract.md` invariant 2).
3. Every hypothesis is falsifiable: a named parameter, a concrete before value, a concrete after value, a predicted effect, and the metric that would disconfirm it. Schema-enforced.
4. Every review names its input window, the Decision Record Store snapshot it read, and the trade set it analysed. A review that cannot name its inputs is not reproducible and its conclusions are not citable.
5. **Analysis reads the Decision Record Store, never the observability tier.** Metrics are downsampled and lossy by design, and a conclusion drawn from downsampled data about individual trades is an artefact of the sampling.
6. Validation runs through the Simulation Harness on the **actual production decision path**, not against a model in isolation. A model can pass every statistical gate while the system using it loses money to slippage, latency, or a risk rule the model-level backtest never ran.
7. Backtests resolve prompts, models, features, and limits **as of** the decision being replayed, never as of today.
8. A missed review cycle is an alert, never a silent skip. The count of consecutive missed cycles is a first-class metric.
9. **Attribution separates entry quality from management quality.** A trade's outcome is decomposed into the entry decision and the management decisions that followed it.

Invariant 7 is the one that silently invalidates everything if it is missing. Page 12 proposes revising desk prompts based on outcomes, and page 08 makes weights tunable. Without point-in-time prompt resolution, replaying a decision from three months ago uses today's prompts, which were tuned on the outcomes of the very trades being replayed. The backtest runs, produces plausible numbers, and is contaminated in the optimistic direction with nothing visibly wrong. This is a look-ahead vector that operates through the prompt rather than through the data, so page 03's careful feature-level discipline does not cover it.

Invariant 9 is the one page 12 cannot currently satisfy at all. Its inputs are entry decisions and fills, with nothing in between, because nothing in the source design owns position management. A loop that sees "committee was confident, trade lost" cannot distinguish a bad entry from a good entry managed badly, and it will happily generate a hypothesis blaming the desk. Attribution requires the OMS to exist and to emit management events.

## Interfaces

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Command | `run_review(window, run_id) -> ReviewResult` | No | 2h | Scheduler, operator |
| Command | `run_triggered_review(reason, window) -> ReviewResult` | No | 2h | service (acute failure), operator |
| Query | `get_review(review_id) -> Review` | Yes | 1s | operator, researcher |
| Query | `backlog(status) -> [BacklogItem]` | Yes | 500ms | operator, researcher |
| Command | `validate(hypothesis_id) -> GateResult` | No | 8h | researcher, Scheduler |
| Query | `desk_calibration(desk, window) -> CalibrationReport` | Yes | 2s | operator, researcher |

```python
@dataclass(frozen=True)
class Hypothesis:
    hypothesis_id: str
    target: Literal["model", "desk_weight", "prompt", "threshold", "rule_param"]
    parameter: str                  # fully qualified, e.g. "committee.macro_desk.weight"
    current_value: Decimal | str
    proposed_value: Decimal | str
    predicted_effect: str
    disconfirming_metric: str       # what would prove this wrong
    evidence_refs: tuple[str, ...]  # references into the Decision Record Store
    window: TimeRange
```

`disconfirming_metric` is the field that makes invariant 3 real. A hypothesis that cannot name what would disprove it is not a hypothesis, and requiring the field at construction time is cheaper than catching the omission at review.

`run_triggered_review` implements page 12's future expansion (three consecutive kill-switch trips triggers an immediate review) and is available from the start, because the acute case is exactly when a weekly cadence is most wrong.

## Degraded Mode

| Condition | Behaviour |
|---|---|
| Decision Record Store unavailable | **No review runs.** Never substitute the observability tier (invariant 5). A skipped review is alerted; a review on lossy data produces conclusions that outlive the outage |
| Simulation Harness unavailable | Hypotheses generate normally, **nothing validates, nothing enters the backlog**. The queue grows visibly rather than the gate quietly loosening |
| Review overruns its window | Alert, do not truncate the analysis window. A partial window analysed as if complete produces a biased conclusion |
| Insufficient sample (< 30 closed trades in the window) | Produce the review, mark every conclusion `underpowered=true`. **Generate no hypotheses.** This is the routine state for the first months of live trading and must not produce action |
| Attribution incomplete (management events missing) | Mark affected trades `attribution_partial=true` and **exclude them from desk accuracy calculations**. A desk graded on a trade whose loss came from management is being graded on someone else's work |
| Cadence missed twice consecutively | Escalate to P1. The loop that is supposed to make the platform improve has stopped, and its failure mode is silence |
| A hypothesis fails PBO/DSR | Record the failure, keep it in the register. **Failed hypotheses are the most valuable output**: they are the record of what was tried and did not survive, which is what stops the same idea returning in six months with a fresh coat of paint |

The underpowered row is the guard the loop most needs early on. With thirty trades of history, every pattern is visible and almost none are real. A learning loop that starts generating hypotheses in month one will spend month two implementing noise.

## SLO

| Dimension | Target |
|---|---|
| Availability | 99% (batch service, no live path) |
| Review completion | Within 4h of trigger, p99 |
| **Cadence** | **Zero missed weekly cycles. Two consecutive is P1** |
| Correctness | **Zero backlog items without a passing PBO/DSR record.** Zero hypotheses without a disconfirming metric |
| Correctness | Zero reviews sourced from the observability tier |
| Reproducibility | A review re-run against the same window and store snapshot produces the identical conclusions |
| **Value** | **Backlog items promoted per quarter, and their realised effect versus predicted.** A loop whose promoted changes do not produce their predicted effects is generating noise with statistical decoration |

The value SLO is the one that makes this layer falsifiable about itself. It is uncomfortable by design: a learning loop is very good at producing activity, and the only honest question is whether the changes it promoted actually did what it said they would.

## Security Boundary

| | |
|---|---|
| **Zone** | CORE. No inbound internet, no broker credentials |
| **Callers permitted** | Scheduler, operator, researcher. **Nothing on the trading path calls this service, and it calls nothing on the trading path** |
| **Secrets held** | Postgres credential, read-only Decision Record Store credential |
| **Write authority** | **None outside its own tables.** It cannot promote a model, publish a prompt, change a weight, or alter a limit. It writes proposals; humans and dual-controlled services act on them |
| **Reads** | Decision Record Store (read-only role), trade history, committee traces. No production write access anywhere |
| **Trusts** | The Decision Record Store as immutable truth. **Trusts its own conclusions least of all**, which is what the gate encodes |

The read-only credential is worth being literal about. This is the one service in the platform whose entire purpose is to change the platform's behaviour, which makes it the one most dangerous to give write access to. The separation between proposing and promoting is the whole safety model, and it is preserved by the credential, not by the code.

---

## Related

- Source page, unmodified: `../12_Continuous_Learning.md`
- `07_ML_RL_Model_Layer.contract.md` — the promotion gate reused here without exception
- `08_AI_Investment_Committee.contract.md` — desk weights as a gated artefact, prompt versioning
- `11_Execution_Platform.contract.md` — the OMS management events invariant 9 depends on
- `../review/R19_Missing_Components.md` §2, §8 — Simulation Harness and Prompt Registry
- `../decisions/0030-prompts-are-versioned-point-in-time-artefacts.md` — invariant 7
- `../decisions/0039-journal-is-an-audit-service-separate-from-observability.md` — invariant 5
