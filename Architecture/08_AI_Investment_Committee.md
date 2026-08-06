# 08 — AI Investment Committee

**Diagram:** `08_AI_Investment_Committee.excalidraw`
**Phase:** 4 — AI Investment Committee (1 of 2 — highest design effort page in the ADD)
**C4 Level:** L3 — Component
**Depends on:** `04_Regime_Engine.md`, `05_Volatility_Engine.md`, `06_Market_Structure_Engine.md`, `07_ML_RL_Model_Layer.md`
**Status:** Draft

---

## Purpose

Replace the naive "Bull agent / Bear agent / PM" pattern with an institutional committee structure: six specialized desks, each with a narrow domain and a hard boundary on what it's allowed to see and cite, debating toward a single trade recommendation that a human can audit line by line.

**08b (Desk Contract Spec) is folded into this page** rather than split out — the contract is small enough (six fields) that a separate page would just be this page's "Shared Desk Contract" section with different formatting.

## Responsibilities

- Convene the six desks on every triggering event (regime shift, structure confluence, scheduled review).
- Enforce that every desk output is schema-valid JSON before it reaches the Consensus Engine.
- Produce a single Trade Recommendation with a full, human-readable reasoning trace — never a bare signal with no explanation.
- Default to **no trade** on any unresolved conflict, ambiguity, or low-aggregate-confidence outcome.

## Components

### Portfolio Manager

Not a seventh opinion — an orchestrator. Convenes the committee (subscribes to trigger events), sets the agenda (which symbol, which timeframe context), collects the six desk outputs, and hands the final Trade Recommendation onward to Risk Management (page 10). Implemented as a workflow (Orchestration Layer, page 00), not itself an LLM call.

### The Six Desks

| Desk | Reads (exclusively) |
|---|---|
| Regime Desk | Regime API — page 04 |
| SMC Desk | Structure API — page 06 |
| Volatility Desk | Volatility API — page 05 |
| Macro Desk | Macro feature category — page 03 |
| Risk Desk | Live portfolio/exposure state — page 10 |
| Execution Desk | Current liquidity/spread conditions — page 11 |

Each desk is a bounded LLM call: it sees only its assigned engine's output plus its own short memory, never another desk's data directly and never raw market data. This boundary is deliberate — it is what makes each desk's reasoning traceable to a specific deterministic source instead of an LLM free-associating across everything at once.

### Shared Desk Contract

Every desk implements the identical interface:

| Field | Description |
|---|---|
| **Inputs** | Deterministic API output from its one assigned engine only |
| **Memory** | Last N committee cycles for this symbol — gives continuity across calls without re-deriving context each time |
| **Tools** | Read-only query functions into its engine's API. No write access. No calls into other desks or other engines. |
| **Output JSON** | `{ stance: "bullish"\|"bearish"\|"neutral", confidence: 0-100, key_evidence: [...], reasoning: str }` |
| **Confidence** | 0-100, required to be discounted (not just optionally lowered) whenever an input carries a staleness or flag tag from its source engine |
| **Reasoning** | Human-readable. Schema-validated against `key_evidence` — a desk cannot cite a number that doesn't appear in its own Inputs. A citation mismatch is a hard rejection of that desk's output for the cycle, not a soft warning. |

### Consensus Engine

Weighted vote across the six desk outputs. Weight per desk is not fixed — it is itself a tunable parameter (starting equal, adjusted by Continuous Learning per page 12 based on historical desk accuracy). Produces an aggregate stance + aggregate confidence.

### Conflict Resolver

Handles the case where desks disagree beyond a configurable threshold (e.g., Regime Desk bullish-high-confidence vs. SMC Desk bearish-high-confidence). **Deadlock always resolves to "no trade."** There is no forced tiebreak mechanism toward taking a position — asymmetry is intentional: the cost of a missed trade is a foregone opportunity, the cost of a wrong trade taken to resolve a coin-flip is capital.

### Trade Recommendation (output)

`{ direction, size_hint, confidence, reasoning_trace }` — not yet an approved trade. Passed to Decision Intelligence (page 09) and ultimately gated by Risk Management (page 10), which can still reject it regardless of committee confidence.

## Inputs

Regime API (04), Volatility API (05), Structure API (06), Model Prediction API (07, feeds Regime/SMC/Macro desk context where relevant), live portfolio state (10), execution/liquidity conditions (11).

## Outputs

Trade Recommendation, full committee reasoning trace (stored permanently — this is the primary input to Explainability, page 09).

## Dependencies

All four Quant Research Platform engines (pages 04-07) must be operational before this page can run for real; Risk Management (page 10) and Execution (page 11) are read-only dependencies for the Risk/Execution desks specifically.

## Events Published

- `committee.convened` — cycle started, with trigger reason.
- `committee.desk.completed` — per desk, as each finishes.
- `committee.recommendation` — final output.
- `committee.deadlock` — Conflict Resolver hit the no-trade default (worth tracking separately from a genuine "the market says do nothing" outcome — deadlock rate is a health metric for desk calibration).

## Events Consumed

`regime.shift.detected`, `structure.confluence.detected`, `volatility.regime_shift` — any of these can trigger a committee cycle. Also a scheduled fallback trigger (e.g., hourly) so a symbol isn't ignored indefinitely if no engine happens to cross a threshold.

## Failure Modes

- **LLM hallucination** — a desk states a number or fact not present in its Inputs.
- **Citation-schema false negative** — legitimate reasoning rejected because of an overly strict citation match (e.g., a rounded number).
- **Desk collusion drift** — over many cycles, desks trained/prompted similarly start correlating instead of providing independent perspectives, quietly defeating the point of having six of them.
- **Consensus gaming** — a single desk with a miscalibrated high-confidence-by-default pattern dominates the weighted vote.
- **Prompt/model drift** — an underlying LLM version upgrade changes desk behavior without anyone re-validating the committee's historical calibration.

## Recovery Strategy

- Citation-schema validation runs on every desk output before it reaches the Consensus Engine; a failed desk output is treated as "abstain" (excluded from the vote, logged), not silently passed through or defaulted to neutral.
- Desk correlation is monitored explicitly — Continuous Learning (page 12) tracks pairwise desk-agreement rates over time; a rising correlation between two desks that should be independent (e.g., Regime and Volatility, which share a GARCH fit — expected some correlation — vs. Regime and Execution, which shouldn't) is a flagged review item, not silently accepted.
- Desk weights are re-tuned, never manually eyeballed — Continuous Learning proposes weight changes based on realized per-desk accuracy, subject to the same overfitting checks (PBO/DSR) as any other model change (page 07's promotion gate pattern, reused here).
- Any LLM/model version change triggers a mandatory shadow-mode run (new version runs alongside the current one, outputs logged but not acted on) before cutover — see page 14 (Deployment).

## Latency Budget

**< 10s per full committee cycle** (six desks, largely parallelizable + consensus + conflict resolution). This runs on bar-close/trigger events, not the tick-level hot path — it is downstream of Risk Management's synchronous < 100ms check (page 10), not upstream of it.

## Technology

Claude API (see `claude-api` skill for current model/pricing guidance) with structured output / tool-use enforcing the Output JSON schema per desk. Each desk is a separate API call (parallelizable) rather than one mega-prompt simulating six personas — this is a deliberate design choice: separate calls make the "reads exclusively from one engine" boundary structurally enforced (the desk's context window literally doesn't contain the other engines' data) rather than a prompt instruction that could be ignored.

## Future Expansion

- Adversarial second-pass: a dedicated review call that argues against the majority stance before it's finalized, similar in spirit to the `three-brain` cross-model routing pattern — evaluate once desk-level calibration is stable.
- Additional desks (e.g., a Correlation/Cross-Asset Desk reading page 03's Cross Asset feature category) — the architecture accommodates this as a seventh box with zero changes to Consensus Engine or Conflict Resolver logic.

---

## Related

- Previous: `07_ML_RL_Model_Layer.md`
- Next: `09_Decision_Intelligence_Layer.md`
