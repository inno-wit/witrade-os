# ADR-0043: Portfolio Construction is a twelfth bounded context, upstream of Risk Authorisation, with no authorisation power

**Status:** Accepted
**Date:** 2026-08-04
**Decided:** 2026-08-04 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** ddd, boundaries, portfolio, capital-allocation

---

## Context

The platform's pipeline, from page 00 through page 10, is `Signal -> Risk -> Execution`: one `TradeProposal` at a time, evaluated against the portfolio it happens to arrive to. `../review/R19_Missing_Components.md` §12 names the gap this leaves — capital allocation *between* concurrent opportunities is a distinct problem from position sizing *within* one — but defers it as a P3 "Strategy Portfolio Manager," reasoning that a single-strategy, effectively single-symbol platform does not yet face real capital competition.

That deferral is sound for a platform that only ever considers one live candidate at a time. It stops being sound as soon as two deliberation cycles (different symbols, or the same symbol on a re-triggered evidence set) can produce two unexpired `TradeProposal`s before either is authorised — which the existing architecture already permits, since BC5 Deliberation cycles run independently per symbol and nothing currently queues or ranks their outputs against each other. At that point the platform has no answer to "we can afford one of these, which one, and what did we give up." ADR-0010 drew eleven contexts and explicitly anticipated this: its Tripwire section states "a new context proposal that satisfies fewer than three criteria is rejected as a module, not a context," which presumes new proposals will be evaluated, not that the eleven are permanently final.

The question this ADR resolves: does capital-competition ranking belong inside BC5 (Deliberation), inside BC6 (Risk Authorisation), or as its own context — and if its own context, how does it avoid weakening ADR-0011 (Risk Authorisation is the sole authorisation authority).

## Options considered

**A. Fold ranking into BC5 Deliberation — the Committee ranks its own candidates.**
*Pros:* no new context; the Committee already produces the proposals.
*Cons:* ranking multiple candidates against a shared, scarce capital budget is a portfolio-level optimisation problem, evaluated by a different kind of correctness (is the allocation efficient) than Deliberation's own correctness (is the reasoning sound and citable). Conflating them means a change to the ranking heuristic risks touching the Committee's evidence-citation machinery, and vice versa.

**B. Fold ranking into BC6 Risk Authorisation — Risk decides which candidates get how much budget as part of its gate chain.**
*Pros:* keeps all capital-related decisions in one context.
*Cons:* directly contradicts the deterministic, rule-chain nature of BC6 established in `../review/R11_Risk_Architecture.md` §3: Risk's gates are pass/fail on hard limits, individually versioned and auditable; ranking by opportunity score is a tunable, PBO/DSR-gated heuristic, the same *kind* of thing as a desk weight (page 08) or an evidence-reliability parameter (page 17), not the same kind of thing as `ExposureLimitRule`. Mixing a learned ranking function into the same aggregate as `KillSwitchState` and `LimitSet` would make BC6's safety-critical rule chain harder to reason about and, per ADR-0010 criterion 5 (a different kind of correctness applies), is exactly the smell the eleven contexts were drawn to eliminate elsewhere in the platform.

**C. A twelfth bounded context, Portfolio Construction (BC12), sitting between BC5 and BC6 in the data flow, with a hard invariant that it can only narrow the candidate set and cap size — never authorise.**
*Pros:* gives capital-competition ranking a home whose rate of change (research-tunable) and correctness type (optimisation-graded, not pass/fail) match its actual nature; keeps BC6 unchanged and its sole-authority property intact by construction, not by discipline.
*Cons:* a twelfth boundary to maintain; the pipeline diagram in page 00 (frozen) now understates the platform relative to page 18, exactly as ADR-0041 already accepted for the Evidence Graph.

## Decision

**Option C.** Portfolio Construction is BC12, specified in `../18_Portfolio_Construction.md`. Evaluated against ADR-0010's six boundary criteria:

| Criterion | Satisfied? |
|---|---|
| 1. Ubiquitous language changes | Yes — "opportunity cost," "capital competition," "displacement" are not BC5 or BC6 vocabulary |
| 2. Consistency requirement differs | Marginal — both need a fresh portfolio view, not a strong differentiator on its own |
| 3. Rate of change differs | Yes — the ranking function is retuned on a research cadence (PBO/DSR-gated, like desk weights); BC6's gates change on a safety-review cadence, rarely |
| 4. Failure domain should be independent | Yes — a halted BC12 fails closed to "admit nothing," which must never take down BC6's ability to gate whatever does reach it directly |
| 5. A different kind of correctness applies | Yes — BC12 is optimisation-graded (was the allocation efficient); BC6 is deterministic pass/fail (did the rule fire) |
| 6. Data has exactly one legitimate owner | Yes — nobody currently owns "which candidate wins the capital," the exact gap `../review/R19_Missing_Components.md` §12 names |

Four of six criteria are satisfied, exceeding ADR-0010's "three or more" bar. **BC12 is architecturally forbidden from calling BC6's authorisation path, from reaching BC8, and from touching a filled position.** It reads BC6's `RiskBudgetSnapshot` as a published, synchronous, fail-closed read model — the identical pattern ADR-0012 established for BC7 -> BC6 — and it is never the reverse.

## Rationale

The alternative to naming this a context is not "no capital competition problem" — it is the same problem solved inside BC5 or BC6 without a name, which is precisely the layered-decomposition failure ADR-0010 already diagnosed once (concepts smearing across boundaries, dependency direction following convenience rather than domain). Giving it a boundary now, before code exists, costs one more container. Discovering the need for the boundary after BC6's rule chain has already absorbed a half-implemented ranking heuristic costs a migration, exactly as ADR-0010's own Consequences section warns for any boundary drawn wrongly.

The non-negotiable design constraint is that this new context must not be, or become, a second authorisation authority. Every interface, invariant, and failure mode in `../18_Portfolio_Construction.md` is written so that BC12 is structurally incapable of producing an `AuthorisedOrder` — it has no signing key, no call path to BC8, and its output to BC6 is a filtered, capped candidate that BC6 evaluates exactly as it would evaluate any other candidate arriving without BC12 in the picture at all.

## Consequences

**Positive**
- The "why this trade, why not another, how much capital, what was the opportunity cost" questions now have a component that answers them, with the same audit durability as an authorisation decision.
- BC6's rule chain (R11 §3) is untouched — no new coupling, no new correctness-type conflation.
- The deferred Strategy Portfolio Manager (`../review/R19_Missing_Components.md` §12, P3) now has a concrete architectural home to extend into once a second strategy exists, rather than needing to be designed from scratch at that point.

**Negative**
- One more context to operate, monitor, and reason about in a solo-operator codebase.
- The scoring model (`opportunity_score`, `diversification`) is a new learned-parameter surface requiring the same PBO/DSR governance discipline as desk weights — more machinery, accepted as the cost of the correctness-type separation in criterion 5.

**Neutral**
- Page 00's original three-stage pipeline diagram (frozen, unmodified) does not show BC12. This is the same situation ADR-0041 already accepted for the Evidence Graph: the source pages remain the correct record of 2026-08-03's design, and pages 17-21 are where 2026-08-04's completion work lives.

## Tripwire

1. If BC12 is ever found calling into BC6's authorisation internals rather than reading the published `RiskBudgetSnapshot`, the acyclic dependency graph (ADR-0010 binding rule 5) has been violated and this ADR's central safety property no longer holds — treat as a P0 finding.
2. If, after twelve months of live operation, BC12 never actually defers or displaces a candidate (every proposal is trivially admitted because the platform never runs more than one live candidate at a time in practice), the context is not yet earning its complexity — this is not a reason to remove it, but it is the signal that promotes `../review/R19_Missing_Components.md` §12's cross-strategy allocation from "future extension" to "worth building now."
3. Track deployment coupling between BC12 and BC6 per ADR-0010's own tripwire 1: if the two are never deployed or changed independently over a year, reconsider whether the boundary earned its keep.

## Related

- ADR-0010 (eleven bounded contexts, and the criteria) — the register this ADR extends by one
- ADR-0011 (Risk Engine is the sole authorisation authority) — the invariant this ADR is designed never to weaken
- ADR-0012 (Portfolio state as a published read model) — the pattern BC12's read of BC6 directly reuses
- ADR-0019 (exits never blocked), ADR-0020 (fractional Kelly as platform default) — the sizing-chain properties BC12's `allocated_risk_budget` cap must remain compatible with
- `../18_Portfolio_Construction.md` — the full specification
- `../19_Bounded_Context_Map.md` — BC12 in the complete context map
- `../review/R19_Missing_Components.md` §12 — the deferred Strategy Portfolio Manager this ADR supersedes for the capital-competition problem specifically
- Source: `../10_Risk_Portfolio_Platform.md`, `../00_Master_Architecture.md`
