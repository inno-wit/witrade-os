# 07 — ML / RL Model Layer

**Diagram:** `07_ML_RL_Model_Layer.excalidraw`
**Phase:** 3 — Quantitative Intelligence (4 of 4)
**C4 Level:** L3 — Component
**Depends on:** `06_Market_Structure_Engine.md`
**Status:** Draft

---

## Purpose

Host every trained-model component of the platform — supervised predictors and reinforcement-learning policy agents — behind one versioned, validated registry so the AI Committee's ML input is never an untracked pickle file someone trained on a laptop.

## Responsibilities

- **ML Models**: train supervised predictors (direction, magnitude, or probability-of-target-hit classifiers) on Feature Store data + labels, validate them against overfitting, serve via inference API.
- **RL Models**: train policy agents (position sizing / entry-timing hints) against a transaction-cost-aware market simulator, validate out-of-sample, serve via the same inference pattern.
- Both tracks converge on a single MLflow registry — one promotion gate, one versioning scheme, regardless of model type.

## Pipelines

**ML Models:**
```
Feature Store + Labels -> Training Pipeline -> Validation -> Inference Service
```

**RL Models:**
```
Market Simulator -> Policy Training -> Validation -> Inference Service
```

Both converge into: `MLflow Model Registry -> Model Prediction API`

## Inputs

- ML: Feature Store categories (Technical, Regime, SMC, Volatility) + Labels category (page 03) — forward returns, triple-barrier outcomes.
- RL: historical market replay via a transaction-cost-aware simulator (not live data — training happens offline against historical episodes).

## Outputs

`predict(model_id, features) -> { prediction, confidence }` — consumed by ML/RL desk input within the AI Committee (page 08) and, for RL specifically, potentially by Risk Management (page 10) as a sizing hint.

## Dependencies

Feature Store (page 03, including Labels). RL additionally depends on a market simulator component (part of this layer, not a separate page — see Technology below).

## Events Published

- `model.trained` — new candidate model produced.
- `model.promoted` — model passed validation gate, now live in the registry as the active version for its slot.
- `model.prediction` — per inference call (high volume; not broadcast platform-wide, logged for audit instead).

## Events Consumed

- `feature.updated`, `feature.backfilled` (training triggers).

## Failure Modes

- **Overfitting** — a model looks great in-sample or even in a naively-split validation set but has no real edge (the classic backtest-lies problem).
- **Label leakage** — triple-barrier or forward-return labels computed with information not actually available at decision time.
- **RL reward hacking** — a policy agent finds a way to maximize reward that doesn't correspond to good trading behavior (e.g., exploiting simulator transaction-cost assumptions).
- **Model staleness** — a promoted model's live performance decays as market conditions drift from its training distribution, with no automatic detection.

## Recovery Strategy

- **No model reaches the registry's "promoted" state without passing PBO (Probability of Backtest Overfitting) and Deflated Sharpe Ratio checks** — see `pbo-deflated-sharpe` skill. This is a hard gate, not a recommendation, for both ML and RL tracks.
- Labels are computed through the same point-in-time-correct Feature Store query path as every other feature (page 03) — there is no separate, less-disciplined label-generation code path.
- RL simulator transaction costs are calibrated against actual observed slippage from the Execution Engine's `execution.slippage.recorded` events (page 11), closing the loop between simulated and real cost assumptions.
- Model staleness is monitored by the Continuous Learning layer (page 12) via live-vs-backtest performance divergence, not by this layer itself — this layer's job ends at "serve the currently-promoted model."

## Latency Budget

- Training: offline, batch — not latency-sensitive, runs on a schedule or on-demand via CLI.
- Inference: **< 200ms per call** (per page 00's Quant Research Platform budget — the Committee waits on this synchronously).

## Technology

- ML: scikit-learn / gradient boosting (XGBoost/LightGBM) for tabular predictors, PyTorch if a neural architecture is warranted.
- RL: Stable-Baselines3 or a custom policy-gradient implementation; simulator is a purpose-built historical replay environment (not a generic gym wrapper) so transaction costs and fill assumptions match this platform's actual execution model.
- Registry: MLflow — experiment tracking, versioning, and the promotion gate live here for both ML and RL uniformly.

## Future Expansion

- Ensemble/blending layer across multiple promoted ML models (currently the design assumes one active model per "slot"; see `alpha-combine` skill for the eventual signal-combination approach once multiple models exist per slot).
- Online/incremental learning for RL agents — currently strictly offline-trained, no live policy updates.

---

## Related

- Previous: `06_Market_Structure_Engine.md`
- Next: `08_AI_Investment_Committee.md` (Phase 4 begins — highest design effort page)
