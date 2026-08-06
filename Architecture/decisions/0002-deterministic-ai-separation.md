# ADR-0002: Deterministic computation and AI reasoning are architecturally separated

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** architecture, ai, correctness, foundational

---

## Context

The platform contains two fundamentally different kinds of computation:

1. **Deterministic quantitative computation.** Bar aggregation, ATR, GARCH forecasts, HMM regime posteriors, swing detection, order block identification, position sizing, risk limit evaluation. Every one of these has a defined input, a defined output, and a correct answer that can be tested.
2. **Probabilistic reasoning over evidence.** The six committee desks assessing whether a given set of computed facts supports taking a position, and why.

The ADD keeps these separated (page 09 states the rule, page 08 enforces a weak version of it) but states the rule in prose, in two places, with no record of what was rejected or why. Nothing in the current document stops it eroding.

It will erode. The specific pressures are predictable:

- A desk needs a number that is not in the evidence graph. The fast fix is to let it compute one.
- A tool-use loop looks like an elegant way to let a desk "look things up."
- Six API calls look expensive next to one prompt containing all six personas.
- An LLM is genuinely better at some pattern-recognition tasks than a hand-written detector, which makes "let the model look at the chart" seem reasonable.

Each of those is locally reasonable and collectively fatal to the platform's central claim: that every number in a decision is reproducible, attributable to a versioned deterministic engine, and identical on replay.

## Options considered

**A. One reasoning agent with tools.** The LLM is given tool access to the feature store, the engines, and the broker, and reasons its way to a decision.
*Pros:* flexible, less plumbing, adapts to new instruments without new code.
*Cons:* no reproducibility (the same inputs produce different tool-call sequences); no point-in-time guarantee (the agent decides what to fetch, so it can fetch the future); no backtest that means anything; the decision path is unbounded in latency and cost; every safety property becomes a prompt instruction rather than a code path.

**B. LLM computes indicators from raw price data.** Pass the model bars, ask it for a regime read and volatility assessment.
*Pros:* fewer components.
*Cons:* the model does arithmetic badly and confidently; the same bars produce different numbers across calls; no model version to attribute a number to; a wrong number is indistinguishable from a right one at the point of use.

**C. LLM tool-use for calculation only.** Deterministic engines exposed as tools, the model calls them.
*Pros:* the numbers are correct.
*Cons:* the model still chooses *which* facts to obtain, which reintroduces look-ahead risk and non-determinism in the evidence set. A replay produces a different evidence graph, so the decision is not reproducible even when every individual number is.

**D. Hard separation (the ADD's implied position, made explicit).** Deterministic engines compute everything and publish an `EvidenceGraph`. Desks receive a sealed, immutable evidence graph and emit only a stance, a confidence, and citations into that graph. No desk has tools, memory of the live system, or any path to a number that is not already in the graph.
*Pros:* every number is reproducible and attributable; the evidence set is fixed before reasoning starts, so look-ahead is structurally impossible; the same graph replays to the same inputs; cost and latency are bounded; the AI is used for the thing it is actually good at.
*Cons:* new evidence requires a new deterministic engine, which is slower to build than a prompt change; the design is less flexible by construction.

## Decision

**Option D.**

1. Every number that enters a decision is produced by a deterministic, versioned engine and lands in the `EvidenceGraph` before any desk is invoked.
2. The evidence graph is **sealed** (content-addressed by `sha256` of its canonical serialisation) before the first desk call. No evidence is added during deliberation.
3. Desks receive the sealed graph and nothing else. No tools, no retrieval, no live system access, no conversational memory of prior cycles beyond the `as_of`-filtered precedent set (ADR-033).
4. Desks emit stance, raw confidence, citations, and a rationale template. They never emit a literal number (ADR-0013).
5. Position sizing, risk evaluation, and order construction are **entirely** deterministic. No LLM output is an input to any of them except as a bounded `conviction` scalar.

The boundary is a package boundary, not a convention: domain engines live under `engines/`, the deliberation layer under `deliberation/`, and `deliberation/` may not import from `engines/` except through the published `Evidence` language.

## Rationale

The separation is what makes every other guarantee in the platform possible. Reproducibility, point-in-time correctness, backtest validity, auditability, and the ability to attribute a loss to a specific model version all rest on it. Break it in one place and all of them degrade at once, silently.

Option A is the design most teams reach for and is the reason most LLM trading systems cannot be backtested. Its failure is not that the model reasons badly; it is that the system stops being a system and becomes a sequence of unrepeatable events.

Option C is the subtle one, and it is why this ADR names it explicitly. Correct numbers obtained in a non-deterministic order still produce a non-reproducible evidence set. Fixing the arithmetic does not fix the architecture.

Option D's cost is real: adding a new kind of evidence means writing an engine, not editing a prompt. That cost is the point. It is what keeps the number of things that can silently change small.

## Consequences

**Positive**
- Every decision is replayable from its evidence graph hash.
- A number in a rationale can always be traced to an engine, a version, and an `as_of`.
- Committee cost and latency are bounded and predictable (six calls, one round, no loops).
- Model upgrades are testable: the same sealed graphs, a different model, a measurable difference in stance.
- Prompt injection has no calculation path to exploit (ADR-0032 closes the text path).

**Negative**
- New evidence is slower to add. Deliberately.
- Some genuinely useful LLM capabilities (reading a chart image, ad-hoc lookup) are unavailable on the decision path. They remain available in research and post-hoc analysis, which is where their non-determinism costs nothing.
- The evidence graph must be complete enough for good reasoning, which puts real design pressure on R09's node taxonomy.

**Neutral**
- Six separate API calls rather than one. Cost is addressed by ADR-0026 and the Cost Governor, not by merging the desks.

## Tripwire

Revisit only if a class of decision-relevant evidence proves impossible to compute deterministically **and** its absence is measurably costing money (demonstrated in the rejection analysis of R11 §12).

Even then, the resolution is a new deterministic engine, not a tool-using desk. A tripwire that would genuinely reverse this decision does not exist. The ADR exists to be pointed at when the pressure to erode it arrives.

## Related

- ADR-0013 (citations as references) makes this rule structural at the desk boundary
- ADR-0026 (six isolated desks)
- ADR-0032 (untrusted text ACL)
- ADR-0035 (clock injection) is the same class of discipline for time
- `../review/R03_Domain_Model_DDD.md` §5
- `../review/R09_Evidence_Graph.md`
- Source: `../09_Decision_Intelligence_Layer.md`, `../08_AI_Investment_Committee.md`
