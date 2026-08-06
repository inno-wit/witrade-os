# 00 — Master System Architecture

**Diagram:** `00_Master_Architecture.excalidraw`
**Phase:** 1 — Foundation
**C4 Level:** L1 — System Context
**Status:** Draft

---

## Purpose

This is the "Google Maps" of WITrade Quant Platform. It answers, at a glance:

- What exists?
- What communicates with what?
- Where does data flow?
- Where are decisions made?
- What is deterministic (Python) vs. AI-driven (LLM reasoning)?

Every subsystem page in this ADD (01 onward) zooms into exactly one box on this diagram. If a component doesn't trace back to a box here, it doesn't belong in the platform yet — extend this page first.

---

## C4 Level 1 — System Context

**Actors:**
- **Operator (human)** — the only human in the loop. Reviews recommendations, can override or halt trading, consumes dashboards.

**External systems:**
- **MT5 (MetaTrader 5)** — broker terminal; source of live/historical price data and destination for order execution.
- **Databento** — institutional-grade tick/bar data provider.
- **Polygon.io** — OHLCV, fundamentals, reference data.
- **News providers** (NewsAPI/Benzinga-class) — headline + sentiment feed.
- **Economic calendar provider** — scheduled macro event data (NFP, CPI, FOMC).
- **Broker(s)** — order execution destination, downstream of MT5 or a direct broker adapter.

**The system:** WITrade Quant Platform — ingests market + news + macro data, runs deterministic quant models, convenes an AI committee to reason over model outputs, applies hard risk constraints, executes approved trades, and learns from its own trade history weekly.

---

## Layer-by-Layer Breakdown

### 1. Users

**Purpose:** Single human entry point — dashboard for monitoring, CLI for research/ops tasks (backtests, model retrains, manual overrides).

**Responsibilities:** Display system state, surface AI Committee reasoning, accept kill-switch / override commands.

**Inputs:** Read access to all downstream layers via API.
**Outputs:** Operator commands (start/stop, override, parameter changes).
**Dependencies:** Orchestration Layer (API gateway), Monitoring (for dashboards).
**Technology:** Next.js dashboard + a thin CLI (Python `click` or `typer`).
**Failure Modes:** Dashboard down ≠ trading stopped — the platform must keep running headless. CLI/API auth failure blocks operator control but not automated flows.
**Recovery Strategy:** Dashboard is stateless and horizontally restartable; no platform state lives in it.

---

### 2. Orchestration Layer

**Purpose:** The nervous system — routes events between every other layer, schedules recurring jobs, and runs multi-step workflows (e.g., "on new bar close → validate → feature-engineer → regime-check → committee review").

**Responsibilities:** Event routing, job scheduling, workflow/DAG execution with retries.

**Components:**
| Component | Role |
|---|---|
| Event Bus (NATS) | Pub/sub backbone. Every layer publishes and subscribes here rather than calling each other directly — this is what keeps layers independently deployable. |
| Scheduler | Cron-style triggers: bar-close events, daily earnings sync, weekly learning review. |
| Workflow Engine | Executes DAGs (e.g., ingestion → validation → feature store → regime engine → committee) with retry/backoff on failure. |

**Inputs:** Operator commands, scheduled triggers, upstream events from every layer.
**Outputs:** Routed events to all subscribing layers.
**Dependencies:** None (this is the substrate everything else depends on).
**Events Published:** `job.scheduled`, `workflow.started`, `workflow.failed`, `workflow.completed`.
**Events Consumed:** All events from all layers (it is the bus itself).
**Failure Modes:** Event bus down = platform-wide outage. This is the single highest-blast-radius component.
**Recovery Strategy:** NATS clustered (min 3 nodes) with JetStream persistence so in-flight events aren't lost on a node failure. Workflow engine checkpoints DAG state so a restart resumes, not restarts.
**Latency Budget:** < 5ms publish-to-subscribe for hot-path trading events (price ticks, signals). Batch/cron jobs are not latency-sensitive.
**Technology:** NATS (JetStream), a lightweight workflow engine (Temporal or a custom asyncio DAG runner — TBD, see Future Expansion).
**Future Expansion:** Evaluate Temporal.io if workflow complexity outgrows a custom DAG runner.

---

### 3. Data Platform *(detail: pages 01-03)*

**Purpose:** Turn raw, messy, multi-source market data into a validated, queryable feature store that every downstream model trusts without re-checking.

**Responsibilities:** Ingest from 5 external sources, validate/quality-score every dataset, compute and store features.

**Sub-flow:** `MT5 / Databento / Polygon / News / Econ Calendar → Data Validation → Feature Store`

**Inputs:** External market/news/macro feeds (pull + push).
**Outputs:** Validated features, keyed by symbol/timeframe/timestamp, consumed by the Quant Research Platform.
**Dependencies:** Orchestration Layer (scheduled pulls, event triggers on new bars).
**Events Published:** `data.bar.received`, `data.quality.scored`, `feature.updated`.
**Events Consumed:** `job.scheduled` (ingestion triggers).
**Failure Modes:** Source outage (broker down, API rate limit), bad ticks, missing candles, DST transition bugs, flash-crash outliers.
**Recovery Strategy:** Per-source circuit breaker + fallback source where available (e.g., Databento as fallback if Polygon rate-limits). Quality Engine flags rather than silently drops — every dataset gets a quality score, downstream consumers set their own minimum threshold.
**Latency Budget:** Real-time tick path < 200ms source-to-feature-store. Batch/historical backfill: best-effort, hours acceptable.
**Technology:** Parquet + DuckDB for storage/query, Python ingestion workers.
**Future Expansion:** Add alternative data sources (options flow, on-chain data) without touching the validation/feature-store contract — see page 03.

---

### 4. Quant Research Platform *(detail: pages 04-07)*

**Purpose:** All deterministic quantitative computation lives here. **This layer calculates. It does not reason.** Every number the AI Committee cites traces back to a function call in this layer.

**Components:** Regime Engine, Volatility Engine, SMC (Market Structure) Engine, ML Models, RL Models.

**Inputs:** Feature Store output.
**Outputs:** Regime probabilities, volatility forecasts, structure confidence scores, model predictions — each exposed via a stable API other layers consume.
**Dependencies:** Data Platform (Feature Store).
**Events Published:** `regime.updated`, `volatility.updated`, `structure.updated`, `model.prediction`.
**Events Consumed:** `feature.updated`.
**Failure Modes:** Model drift (silent degradation, not a crash), stale feature inputs, GARCH/HMM non-convergence on regime change.
**Recovery Strategy:** Every model output carries a confidence/staleness field; the AI Committee is required to discount or reject stale/low-confidence inputs rather than the Quant layer hiding the problem.
**Latency Budget:** Regime/Vol/Structure: recompute on every bar close, budget < 500ms per symbol. ML/RL inference: < 200ms per call (committee is synchronous on this).
**Technology:** Python (statsmodels/arch for GARCH, hmmlearn for HMM, PyTorch/sklearn for ML, custom or Stable-Baselines3 for RL). MLflow for model registry.
**Future Expansion:** Additional engines (options-implied vol surface, cross-asset correlation regime) plug in as new boxes at this layer without touching the Committee's interface — they just add another desk.

---

### 5. Decision Intelligence Layer — AI Investment Committee *(detail: pages 08-09)*

**Purpose:** **This is the only layer allowed to reason with an LLM.** It takes deterministic quant outputs, debates them across six specialized "desks," and produces a trade recommendation with an explainable rationale.

**Components:** AI Investment Committee (6 desks: Regime, SMC, Volatility, Macro, Risk, Execution), Consensus Engine, Explainability module.

**Inputs:** Quant Research Platform outputs (regime, vol, structure, model predictions).
**Outputs:** Trade Recommendation (direction, size hint, confidence, full reasoning trace) — not yet an approved trade.
**Dependencies:** Quant Research Platform.
**Events Published:** `committee.recommendation`, `committee.debate.logged`.
**Events Consumed:** `regime.updated`, `volatility.updated`, `structure.updated`, `model.prediction`.
**Failure Modes:** LLM hallucination (citing a number the quant layer never produced), desk disagreement deadlock, prompt/context drift after model upgrades.
**Recovery Strategy:** Every desk output is schema-validated JSON — a citation that doesn't match a real Quant Layer output is rejected before it reaches the Consensus Engine. Deadlocked votes default to "no trade," never a forced tiebreak toward action.
**Latency Budget:** < 10s per committee cycle (this is reasoning, not the hot path — it runs on bar-close/signal events, not tick-by-tick).
**Technology:** Claude API (see `claude-api` skill for model selection), structured output/tool-use for schema enforcement.
**Future Expansion:** Additional desks (e.g., a dedicated Correlation Desk) or a second LLM as an adversarial reviewer of the first — see page 08.

---

### 6. Risk Management *(detail: page 10)*

**Purpose:** The layer with veto power. No trade reaches Execution without passing here — deterministic, non-negotiable, cannot be reasoned around by the AI Committee.

**Components:** Position Sizing, Portfolio (correlation/concentration), Exposure limits, Kill Switch.

**Inputs:** Trade Recommendation from the Committee.
**Outputs:** Approved Trade (or rejection with reason).
**Dependencies:** Decision Intelligence Layer.
**Events Published:** `risk.approved`, `risk.rejected`, `risk.killswitch.triggered`.
**Events Consumed:** `committee.recommendation`.
**Failure Modes:** Stale portfolio state (approving a trade against outdated exposure), kill switch failing to propagate before an in-flight order sends.
**Recovery Strategy:** Portfolio state reconciled against broker truth (not just internal ledger) before every approval. Kill switch is a hard synchronous gate in the Execution path, not an async event — see page 10/11 interface contract.
**Latency Budget:** < 100ms per check (sits on the hot path between recommendation and execution).
**Technology:** Python, Redis for live portfolio state cache, Postgres for durable ledger.
**Future Expansion:** Portfolio-level Kelly optimization across correlated strategies (see `capital-allocator` skill).

---

### 7. Execution Engine *(detail: page 11)*

**Purpose:** Turn an approved trade into a broker order and verify the fill actually matches what was approved.

**Components:** Broker Adapter (MT5 first, broker-agnostic design), Order Verification, Fill Verification / Slippage Analysis.

**Inputs:** Approved Trade.
**Outputs:** Trade Confirmation → Journal.
**Dependencies:** Risk Management.
**Events Published:** `order.sent`, `order.filled`, `order.rejected`, `execution.slippage.recorded`.
**Events Consumed:** `risk.approved`.
**Failure Modes:** Broker connectivity loss mid-order, partial fills, slippage beyond tolerance, duplicate order submission on retry.
**Recovery Strategy:** Idempotent order IDs (retries never double-submit), explicit partial-fill handling state machine, hard slippage tolerance that auto-flags (not auto-cancels) for operator review.
**Latency Budget:** < 300ms order-send to broker ack (MT5-dependent).
**Technology:** MT5 Python bridge (Windows VPS, per existing TradeHub SMC microservice pattern), broker-agnostic adapter interface for future brokers.
**Future Expansion:** Multi-broker smart order routing (see `execution-safety` skill for the human-confirmation gate pattern this should extend).

---

### 8. Monitoring & Observability *(cross-cutting — detail: page 13)*

**Purpose:** Drawn here as a band for readability, but it is architecturally **cross-cutting** — every layer above publishes logs/metrics here, it does not sit only after Execution.

**Components:** Logs, Metrics, Alerts, Journal.

**Inputs:** Telemetry from every layer.
**Outputs:** Dashboards, alerts, permanent trade/decision journal.
**Dependencies:** None functionally, but conceptually depends on every other layer emitting telemetry correctly.
**Events Published:** `alert.triggered`.
**Events Consumed:** Every `*.updated`, `*.approved`, `*.rejected`, `*.filled` event on the bus.
**Failure Modes:** Alert fatigue (too many low-signal alerts trains the operator to ignore them), silent metrics pipeline failure (you don't know monitoring is broken until you need it).
**Recovery Strategy:** Tiered alerting (page vs. Slack vs. dashboard-only), synthetic heartbeat check that pages if metrics stop arriving.
**Latency Budget:** Logs/metrics: near-real-time, < 5s. Alerts on critical events (kill switch, execution failure): < 2s.
**Technology:** Prometheus + Grafana (metrics), structured JSON logs, Postgres/S3-backed permanent Journal.
**Future Expansion:** Anomaly-detection alerting (statistical, not just threshold) once baseline metrics exist.

---

### 9. Continuous Learning *(detail: page 12)*

**Purpose:** The platform is required to get better weekly, not just run. This layer reviews its own trade history and generates hypotheses for the Quant Research and Decision Intelligence layers to test.

**Components:** Weekly Review, Trade Analytics, Model Evaluation, Strategy Evolution.

**Inputs:** Journal (from Monitoring), model performance history.
**Outputs:** Research Backlog — feeds back into Quant Research Platform (retrained models) and AI Committee (revised desk prompts/weights).
**Dependencies:** Monitoring & Observability (Journal), Execution Engine (realized trade outcomes).
**Events Published:** `learning.review.completed`, `learning.hypothesis.generated`.
**Events Consumed:** `order.filled`, `execution.slippage.recorded`.
**Failure Modes:** Overfitting to recent regime (the loop "learns" noise), review cadence slipping under operational load.
**Recovery Strategy:** All proposed changes go through the same PBO/Deflated Sharpe overfitting checks as any new strategy before being promoted — the learning loop doesn't get a shortcut around validation. See `pbo-deflated-sharpe` skill.
**Latency Budget:** Not latency-sensitive — weekly cadence by design.
**Technology:** Python analytics (pandas), MLflow for model version comparison.
**Future Expansion:** This is the entry point for the `trading-loop` / `autoresearch` self-learning pattern already scaffolded in the `trading-suite` skill pack.

---

## What is deterministic vs. AI-driven — the one rule that governs everything else

| Layer | Nature |
|---|---|
| Data Platform | Deterministic |
| Quant Research Platform | Deterministic (includes ML/RL — trained models, not reasoning) |
| **Decision Intelligence Layer** | **AI-driven (LLM reasoning) — the only layer where this happens** |
| Risk Management | Deterministic, non-negotiable |
| Execution Engine | Deterministic |
| Continuous Learning | Deterministic analytics generating hypotheses; any resulting strategy change is itself validated deterministically before promotion |

The Committee explains and recommends. It never computes a number itself and never bypasses Risk Management.

---

## Open Questions / Decisions Deferred to Later Pages

- Exact workflow engine choice (Temporal vs. custom DAG runner) — page 13 (Infrastructure).
- Full event schema per topic — page 15 (Event Catalog).
- Broker-agnostic adapter interface definition — page 11 (Execution Platform).
- Desk-level contract (Inputs/Memory/Tools/Output JSON) — page 08.

---

## Related

- Roadmap: `ROADMAP.md`
- Next: `01_Data_Ingestion.md`
