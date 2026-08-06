# 12 — Continuous Learning

**Diagram:** `12_Continuous_Learning.excalidraw`
**Phase:** 8 — Learning Platform
**C4 Level:** L2 — Container
**Depends on:** `11_Execution_Platform.md`
**Status:** Draft

---

## Purpose

The platform is required to get better weekly, not just run. This layer reviews the platform's own realized trade history, finds where reality diverged from what the Committee expected, and turns that into specific, testable hypotheses — never vague "do better" directives.

## Responsibilities

Run a scheduled (default: weekly) review of trade history, compute performance analytics, detect failure patterns, generate hypotheses, and maintain a prioritized backlog of validated changes ready to feed back into the platform.

## Pipeline

```
Trade History (Journal, page 11)
  -> Performance Analytics    (win rate, R-multiple, drawdown, per-desk accuracy)
  -> Failure Detection          (where did outcomes diverge from Committee confidence?)
  -> Hypothesis Generator         (specific, testable proposed changes)
  -> Experiment Queue               (prioritized backlog awaiting validation)
  -> Research Backlog                 (validated changes ready for promotion)
      -> Quant Research Platform (retrained models, pages 04-07)
      -> AI Investment Committee (revised desk weights/prompts, page 08)
```

## Inputs

Trade History / Journal (page 11), realized fills and outcomes, per-desk confidence-vs-outcome history (from page 08's committee reasoning traces).

## Outputs

Research Backlog items routed to two destinations: retrained/re-validated models in the Quant Research Platform (pages 04-07), or revised Consensus Engine desk weights in the AI Committee (page 08).

## Dependencies

Execution Engine (page 11) for realized trade outcomes; indirectly depends on every upstream layer since it's reviewing the whole platform's decisions.

## Events Published

- `learning.review.completed` — weekly cycle finished.
- `learning.hypothesis.generated` — per hypothesis, with supporting evidence.
- `learning.change.validated` — a hypothesis passed the PBO/DSR gate and entered the Research Backlog.

## Events Consumed

`order.filled`, `execution.slippage.recorded` (page 11), `committee.recommendation` history (page 08, for confidence-vs-outcome comparison).

## Failure Modes

- **Overfitting to recent regime** — the loop "learns" from a short recent window that happens to reflect noise or a temporary regime rather than a durable pattern.
- **Review cadence slipping** — under operational load, the weekly review gets postponed repeatedly, and the feedback loop that's supposed to make the platform improve weekly silently stops running.
- **Hypothesis vagueness** — a generated hypothesis is too broad to be testable ("the Macro Desk should be more conservative") rather than specific ("reduce Macro Desk weight by 15% when regime confidence < 60%").

## Recovery Strategy

- **No shortcut rule** (see diagram side panel): every proposed change — a retrained model or a revised desk weight — goes through the exact same PBO (Probability of Backtest Overfitting) and Deflated Sharpe Ratio validation gate as any brand-new strategy (page 07's promotion gate, reused here without exception). The learning loop does not get to bypass validation because it's the platform "learning about itself" — that's precisely the scenario overfitting checks exist for. See `pbo-deflated-sharpe` skill.
- Review cadence is enforced by the Orchestration Layer's Scheduler (page 00), with a missed-review alert routed through Monitoring — cadence slippage is made visible rather than silently tolerated.
- The Hypothesis Generator is required to output a specific, falsifiable change (parameter, threshold, or weight adjustment with a concrete before/after value), not open-ended commentary — enforced by schema, similar in spirit to the Committee desks' Output JSON schema (page 08).

## Latency Budget

Not latency-sensitive — weekly cadence by design. This is the one layer in the platform where "not latency-sensitive" is itself a design decision worth stating explicitly: rushing this loop faster than weekly risks reacting to noise rather than signal.

## Technology

Python analytics (pandas) for Performance Analytics and Failure Detection, MLflow for comparing model versions across review cycles. This is the natural home for the `trading-loop` / `autoresearch` self-learning pattern already scaffolded in the `trading-suite` skill pack — Hypothesis Generator and Experiment Queue map directly onto that pattern's plan → act → measure → keep-winners loop.

## Future Expansion

- Faster-than-weekly triggered reviews for acute failure patterns (e.g., three consecutive Kill Switch trips triggers an immediate review rather than waiting for the weekly cycle) — while keeping the routine cadence weekly by default.
- Automated A/B shadow-running of proposed Committee weight changes (per page 08's shadow-mode deployment practice) before they're promoted out of the Experiment Queue.

---

## Related

- Previous: `11_Execution_Platform.md`
- Next: `13_Infrastructure_Platform.md`
