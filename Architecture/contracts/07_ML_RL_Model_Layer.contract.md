# 07 — ML / RL Model Layer, contract completion

**Delta against:** `../07_ML_RL_Model_Layer.md` (unmodified)
**Adds:** Owns, Invariants, Interfaces, Degraded Mode, SLO, Security Boundary
**Containers:** C12 Model Training + C13 Model Inference + C14 Model Monitor · **Context:** Model Lifecycle · **Criticality:** C13 Tier 1, C12 and C14 Tier 2 · **Group:** Quant
**Highest-value field for this page (R05 §11):** **Owns.** Training and inference must not share writable state

---

## The three-way split this contract assumes

Page 07 describes one layer. It is three containers, and the reason is the field R05 flags:

| | C12 Training | C13 Inference | C14 Monitor |
|---|---|---|---|
| Writes | Candidate artefacts, training runs | **Nothing durable** | Drift records, alerts |
| Reads | Features + Labels | Features (no Labels) | Live predictions vs training distribution |
| Runs | Offline, batch | On the committee's synchronous path | Continuous |
| Failure | Delayed retrain | Desk abstains | Drift goes undetected |

C14 is new. Page 07 names model staleness as a failure mode and delegates detection to page 12's **weekly** cycle. A model can degrade materially in a day, so weekly detection permits up to seven days of capital decisions made on a model already known in retrospect to be failing. That is not a monitoring gap, it is a risk control that does not exist.

## Owns (exclusive write access)

| Asset | Owner | Note |
|---|---|---|
| `training_runs`, `training_datasets` | **C12 only** | Every run records input snapshot IDs and the label definition version |
| MLflow experiments and candidate artefacts | C12 | |
| `model_registry` promotion state | C12, **dual-controlled** | The promotion record, not the artefact |
| `inference_log` (to Decision Record Store) | **C13 only** | Per-call, attached to the requesting cycle |
| `drift_metrics`, `drift_alerts` | **C14 only** | |

**C13 writes no model state.** It loads a pinned artefact version and serves. An inference service that can update its own weights is an inference service whose behaviour cannot be replayed.

`model.prediction` is removed from the event bus entirely (see `../generated/15_Event_Catalog_v2.md` §4.6). Per-inference records are Tier C: written to the Decision Record Store attached to the cycle that requested them, never published. Volume then scales with committee cycles instead of with bars.

## Invariants

1. **No model reaches `promoted` without passing PBO and Deflated Sharpe Ratio gates.** Page 07 states this as a hard gate; here it is mechanical: the promotion API rejects a version whose run record lacks a passing gate result. There is no manual path, including for the operator.
2. The PBO/DSR gate applies to **every** promotable artefact, including desk weights and consensus strategy versions proposed by the learning loop. The learning loop does not get to grade its own homework (ADR-0029 pattern, applied here).
3. Labels are read only by C12, only with `purpose="training"`, and never by C13. Enforced by a Postgres grant, not a code convention.
4. Every candidate records the Iceberg snapshot IDs of every input table and the label definition version. A run that cannot name its inputs cannot be promoted.
5. Inference is deterministic given `(model_version, FeatureView)`. The same inputs produce the same output on any host at any time. Seeds pinned, no wall clock, no ambient randomness.
6. One promoted version per slot at a time. A slot change is an event with a shadow period, never an in-place swap.
7. Every prediction carries `model_version`, `training_snapshot_ids`, `feature_versions`, and `as_of`. A prediction that cannot name what produced it cannot be cited as evidence (ADR-0013).
8. RL simulator transaction costs are calibrated against observed live slippage, and the calibration's own age is recorded. A simulator calibrated on year-old slippage is training against a market that no longer exists.

Invariant 2 is worth dwelling on. Page 12 proposes revising desk weights based on outcomes, and page 08 makes those weights tunable. Desk weights are a model: fitted to historical outcomes, subject to overfitting, and capable of being curve-fitted into confident nonsense exactly like any other. Routing them through the same gate is the difference between a learning loop and a slow-motion overfit.

## Interfaces

### C13 Inference (synchronous, on the committee path)

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Query | `predict(slot, view: FeatureView, as_of) -> Prediction \| Unavailable` | Yes | 200ms | service |
| Query | `active_version(slot) -> ModelVersion` | Yes | 10ms | service |

### C12 Training (offline)

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Command | `train(spec, range, run_id) -> CandidateRef` | No | 24h | researcher, Scheduler |
| Command | `evaluate(candidate) -> GateResult` | No | 4h | researcher |
| Command | `promote(candidate, slot, approver_a, approver_b)` | Yes | 1s | **dual-control, audited** |
| Command | `rollback(slot, to_version, actor, reason)` | Yes | 1s | operator, audited |

### C14 Monitor

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Query | `health(slot) -> ModelHealth` | Yes | 20ms | service, operator |
| Query | `drift_report(slot, window) -> DriftReport` | Yes | 2s | operator, researcher |

`predict` returning `Unavailable` rather than raising is deliberate, and it matches the `BrokerAdapter` rule that a timeout is a return value rather than an exception. A desk that receives `Unavailable` abstains. A desk that receives an exception from an inference call has to decide what an exception means, and that decision will be made inconsistently in six places.

## Degraded Mode

| Condition | Behaviour | **Consumer behaviour** |
|---|---|---|
| Inference times out or the artefact fails to load | Return `Unavailable` with a reason | The desk consuming it abstains. **Quorum arithmetic sees an abstention, never a neutral prediction** |
| Model staleness beyond `max_staleness` | Serve with `staleness` set; beyond a hard bound, refuse to serve | Desk abstains. Risk's `ModelRiskRule` blocks new entries that depend on that slot |
| C14 detects drift beyond threshold | Raise `evt.model.drift.detected.v1`, do **not** auto-demote | Risk applies the degradation ladder. **Correlated drift across multiple slots auto-trips the kill switch**, because simultaneous degradation usually means the market changed, not the models |
| Feature Store unavailable | Cannot infer. Return `Unavailable` | As row 1 |
| C12 unavailable | No retraining, no promotion | No live impact. Alert at P2, escalating with the age of the oldest slot |
| Two versions promoted to one slot | **Hard error, refuse to serve the slot** | Total abstention for that slot. Ambiguity about which model spoke is worse than no model speaking |

The correlated-drift row is the control that matters most and that nothing in pages 00-16 owns. One model drifting is a model problem. Four models drifting in the same week is the market having moved out from under all of them, and continuing to trade through it on the assumption that the ensemble compensates is the mechanism by which a quiet system produces a bad month.

Auto-demotion is deliberately excluded. A demotion that fires on a drift metric during a genuine regime change removes the platform's models at the moment conditions are hardest, with no human aware it happened. Drift raises an alert and constrains risk; a human demotes.

## SLO

| Dimension | Target |
|---|---|
| C13 availability, market hours | 99.9% |
| `predict` | p50 < 60ms, p95 < 150ms, p99 < 200ms |
| C14 drift detection latency | Detected within **1 trading day**, not 1 week |
| Correctness | Zero promotions without a passing PBO/DSR record. Zero label reads on the serving path |
| Reproducibility | Two inferences of the same `(version, view)` are byte-identical |
| Freshness | Zero slots serving a model past its hard staleness bound |
| Honesty | **Live hit rate stays inside the backtest confidence interval. Falling outside it is a P1 finding, not a note for the weekly review** |

The last line is the SLO that makes this layer falsifiable, and it is the one the source design cannot express because it has no continuous monitor. A model whose live performance sits outside the interval its own backtest predicted is, empirically, not the model that was promoted.

## Security Boundary

| | |
|---|---|
| **Zone** | CORE. No inbound internet, no broker credentials |
| **Callers permitted (C13)** | Evidence Graph (C15) and Committee (C16) via evidence, Risk (C21) for RL sizing hints |
| **Callers permitted (C12)** | Researchers (train, evaluate). **Promotion requires two approvers** |
| **Secrets held** | Object storage and Postgres credentials. MLflow credential |
| **Trusts** | Feature Store output. Trusts nothing external. **Model artefacts are loaded by pinned version and hash, never by "latest"** |
| **Researcher boundary** | Researchers have no production write authority. They can train, evaluate, and propose. They cannot promote |
| **Supply chain** | Artefacts are pickled objects, which are executable. They are loaded only from the platform's own object store, verified by hash, never from a URL or a shared drive |

The supply chain line matters more than it looks. A model artefact is code. Loading one from anywhere other than a verified internal store is remote code execution into the process that advises on capital allocation, and page 07's own Purpose ("never an untracked pickle file someone trained on a laptop") is exactly the right instinct written as an aspiration rather than a control.

---

## Related

- Source page, unmodified: `../07_ML_RL_Model_Layer.md`
- `03_Feature_Store.contract.md` — the Labels invariant this contract extends
- `12_Continuous_Learning.contract.md` — the loop whose own proposals invariant 2 gates
- `../generated/16_Container_Model_v2.md` §3 — the C12/C13/C14 split
- `../review/R19_Missing_Components.md` §9 — the case for the Model Monitor
- `../decisions/0013-citations-are-references-not-values.md` — invariant 7
