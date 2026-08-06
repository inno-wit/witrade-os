# WITrade Quant Platform — Architecture Design Document Roadmap

**Version:** 1.0
**Status:** All 17 pages (00-16) drafted. Pending: human review pass, then Phase 11+ (implementation) or a C4 Level 4 code-view pass once real code exists.
**Format:** Each numbered page = one `.excalidraw` diagram + one matching `.md` spec, saved to `Architecture/`.

This roadmap sequences the full ADD so work can proceed incrementally across sessions without losing the plan. Update the Status column as pages land — this file is the single source of truth for "what exists vs. what's next."

---

## How to read this table

- **Page** — file prefix, e.g. `00` → `00_Master_Architecture.excalidraw` / `.md`
- **C4** — which C4 levels that page's Markdown covers (L1 System Context, L2 Container, L3 Component, L4 Code). Most pages are informal architecture diagrams; C4 views are called out explicitly where they add value rather than duplicating the same box-and-arrow picture four times.
- **Depends on** — pages that should exist first because this one references their component names/interfaces
- **Status** — Not started / In progress / Draft / Done

---

## Phase 1 — Foundation

| Page | Title | C4 | Depends on | Status |
|---|---|---|---|---|
| 00 | Master System Architecture | L1 (System Context) | — | Draft |

Answers: what exists, what talks to what, where data flows, where decisions get made, what's deterministic vs. AI-driven. Every later page zooms into one box from this diagram.

---

## Phase 2 — Data Platform (3 pages)

| Page | Title | C4 | Depends on | Status |
|---|---|---|---|---|
| 01 | Data Ingestion (MT5, Databento, Polygon, News, Econ Calendar → raw storage) | L2 (Container) | 00 | Draft |
| 02 | Data Quality Engine (missing candles, dupes, DST, outages, spread spikes, flash crashes, bad ticks → quality score) | L3 (Component) | 01 | Draft |
| 03 | Feature Store (Technical, Regime, SMC, Volatility, Time, Macro, Alt Data, Cross-Asset, Labels) | L3 (Component) | 01, 02 | Draft |

---

## Phase 3 — Quantitative Intelligence (4 pages)

This is the differentiated core — most design effort per page after the AI Committee.

| Page | Title | C4 | Depends on | Status |
|---|---|---|---|---|
| 04 | Regime Engine (Returns → GARCH → Markov Switching → HMM → Transition Matrix → Regime API) | L3 | 03 | Draft |
| 05 | Volatility Engine (ATR, Forecast Vol, Realized Vol, Expected Move, Vol Percentile, Tail Risk) | L3 | 03 | Draft |
| 06 | Market Structure Engine / SMC (Swing Detection → BOS → CHoCH → Liquidity → OB → FVG → Mitigation → Structure Confidence) | L3 | 03 | Draft |
| 07 | ML/RL Model Layer (supervised models, RL agents, training/inference split, model registry hook into MLflow) | L3 | 03, 04, 05, 06 | Draft |

---

## Phase 4 — AI Investment Committee (1-2 pages)

Highest design effort in the whole document — this is where the institutional-committee metaphor gets made concrete.

| Page | Title | C4 | Depends on | Status |
|---|---|---|---|---|
| 08 | AI Investment Committee (Regime / SMC / Volatility / Macro / Risk / Execution Desks → Consensus Engine → Conflict Resolver → Trade Recommendation) | L3 | 04, 05, 06, 07 | Draft |
| 08b | Desk Contract Spec — **folded into page 08** ("Shared Desk Contract" section); did not warrant a standalone page | L4 (Code View) | 08 | Folded into 08 |

---

## Phase 5 — Decision Intelligence Layer (1 page)

| Page | Title | C4 | Depends on | Status |
|---|---|---|---|---|
| 09 | Decision Intelligence (Quant Models → Evidence Graph → Committee Debate → Portfolio Impact → Risk Constraints → Decision → Explanation) | L2 | 08 | Draft |

Explicit design rule carried into this page: **the AI reasons, it does not calculate.** Every number the committee cites traces back to a deterministic Python output from Phase 2/3.

---

## Phase 6 — Risk Platform (1 page)

| Page | Title | C4 | Depends on | Status |
|---|---|---|---|---|
| 10 | Risk & Portfolio Management (Signals → Portfolio Risk → Exposure → Position Size → Correlation → Kelly → Drawdown Guard → Kill Switch → Approved Trade) | L3 | 09 | Draft |

---

## Phase 7 — Execution Platform (1 page)

| Page | Title | C4 | Depends on | Status |
|---|---|---|---|---|
| 11 | Execution Platform (Approved Trade → Broker Adapter → MT5 → Order Verification → Slippage Analysis → Trade Confirmation → Journal) | L3 | 10 | Draft |

---

## Phase 8 — Learning Platform (1 page)

| Page | Title | C4 | Depends on | Status |
|---|---|---|---|---|
| 12 | Continuous Learning (Trade History → Performance Analytics → Failure Detection → Hypothesis Generator → Experiment Queue → Research Backlog) | L2 | 11 | Draft |

Feeds back into Phase 3 (Regime/Vol/Structure engines get re-tuned) and Phase 4 (desk prompts/weights get revised) — this is the loop that makes the platform "learn every week."

---

## Phase 9 — Infrastructure (1 page)

| Page | Title | C4 | Depends on | Status |
|---|---|---|---|---|
| 13 | Infrastructure Platform (FastAPI, Redis, DuckDB, Postgres, MLflow, Docker, Grafana, Prometheus, NATS, GitHub Actions, MinIO — which service backs which subsystem) | L2 | 00 | Draft |

---

## Phase 10 — Deployment (1 page)

| Page | Title | C4 | Depends on | Status |
|---|---|---|---|---|
| 14 | Deployment Pipeline (Research Workstation → CI/CD → Cloud → VPS → MT5 → Dashboard) | — | 13 | Draft |

---

## Cross-Cutting Reference Pages (added — not in your original phase list, but needed once Phases 2-10 exist)

| Page | Title | C4 | Depends on | Status |
|---|---|---|---|---|
| 15 | Event Catalog (every "Events Published" / "Events Consumed" from every component's spec, in one lookup table — this is what makes the "Orchestration Layer / Event Bus" box in 00 actually implementable) | — | 01-14 | Draft |
| 16 | C4 Container Diagram — whole-platform (the single L2 view that shows all containers from 00 at once: Data Platform, Feature Store, Regime Engine, AI Committee, Risk Engine, Execution Engine, as independently deployable services) | L2 | 00-14 | Draft |

---

## Per-component spec template (applies to every page from 01 onward)

Per your brief, every component box gets these fields in its `.md`:

- Purpose
- Responsibilities
- Inputs
- Outputs
- Dependencies
- Events Published
- Events Consumed
- Failure Modes
- Recovery Strategy
- Latency Budget
- Technology
- Future Expansion

---

## Sequencing notes

- Pages must be built roughly in table order — later pages reference component names/interfaces defined earlier (e.g., the AI Committee's Regime Desk cites the exact `Regime API` output shape from page 04).
- **08 (AI Investment Committee)** is flagged in your brief as the highest-effort page — budget it its own session rather than rushing it alongside 09/10.
- **15 (Event Catalog)** can only be finalized after all component pages exist, but should be *started* as a running table from page 01 onward so it isn't a rewrite at the end.
- Total: **17 numbered pages** (00-14 + 15, 16) — within your 15-20 target once 08b is decided.

---

## Status legend

- **Not started** — no draft exists
- **In progress** — actively being worked in the current session
- **Draft** — diagram + md exist, not yet reviewed
- **Done** — reviewed and considered stable

---

## Next up

**All 17 planned pages (00-16) are drafted.** Every phase from the original brief is covered, plus the two cross-cutting reference pages (15 Event Catalog, 16 C4 Container Diagram).

What's genuinely next, in priority order:

1. **Human review pass** — every page here was generated in one continuous unattended session. Before anything builds further on top of this ADD, walk each page for: whether the C4 boundaries actually make sense, whether the desk/engine interface names are ones you'd actually want to build against, and whether the failure-mode/recovery-strategy calls match how you actually want the platform to fail. Page 08 (AI Investment Committee) and page 10 (Risk Management) are the highest-stakes to get right since the most other pages depend on their exact interfaces.
2. **Sync pass on pages 15 (Event Catalog) and 16 (C4 Container Diagram)** — both are explicitly marked as design-time snapshots compiled from the other 15 pages. If review changes anything in pages 00-14, these two need a re-sync.
3. **C4 Level 4 (Code View)** — deferred everywhere in this pass because no code exists yet. Once implementation starts on any one subsystem (Regime Engine, page 04, is probably the least entangled starting point), that's when an L4 page for it becomes possible to write honestly.
4. **Implementation** — this ADD is now a real blueprint to build against, not just a plan of a plan.
