# ADR-0011: The Risk Engine is the sole authorisation authority

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** risk, boundaries, safety

---

## Context

Two components in the ADD both claim the authority to approve a trade. This is blocking defect B4.

- **Page 09 (Decision Intelligence)** describes a decision layer that assesses portfolio impact and produces a decision, with approval semantics.
- **Page 10 (Risk & Portfolio)** describes a risk pipeline that evaluates every trade recommendation and approves or rejects it.

The pages do not contradict each other in wording, which is why the defect is easy to miss. They contradict each other in **authority**: if page 09 has already assessed portfolio impact and decided, then either page 10 is re-deciding (in which case page 09's assessment is advisory and should say so) or page 10 is rubber-stamping (in which case the risk controls are not the last word).

Either reading produces the same class of bug in implementation. Two components that both believe they are the gate will, under time pressure, be wired so that one is bypassed in some path. The bypassed one will be the one that was harder to call.

There is a second, more subtle problem. Page 09 genuinely *needs* risk information to produce a good proposal: a proposal that will obviously be rejected for exposure reasons is wasted deliberation and wasted LLM spend. The naive fix (remove risk knowledge from page 09) makes the system dumber. The correct fix distinguishes **knowing** from **deciding**.

## Options considered

**A. Status quo, resolved by convention.** Document that page 10 wins and rely on discipline.
*Pros:* no change.
*Cons:* the ambiguity is in the module graph, not the prose. Discipline does not survive the first urgent fix.

**B. Merge the two into one component.** One service that both proposes and authorises.
*Pros:* unambiguous by construction.
*Cons:* collapses the deliberation and risk contexts into one, which destroys the ability to test them independently, makes the risk rules untestable without an LLM, and puts a probabilistic component inside the authorisation path. This is the wrong direction.

**C. One Risk Engine with two modes: PREVIEW and DECIDE.** The Risk Engine is the only component that can authorise. It exposes an advisory `PREVIEW` query that the Decision Service may call to shape a proposal, and an authoritative `DECIDE` command that only it can act on. `PREVIEW` has no side effects and issues no token.
*Pros:* single authority; the Decision Service can still be smart about what it proposes; the advisory path is explicitly non-binding and typed as such.
*Cons:* two entry points to keep semantically aligned; a `PREVIEW` result could be mistaken for an approval by a careless caller.

## Decision

**Option C.**

1. The **Risk Engine (BC6) is the sole authorisation authority.** No other component may approve, and no component may act on anything other than an `AuthorisedOrder` token issued by it.
2. The Risk Engine exposes exactly two operations:
   - `qry.risk.preview.v1`: **advisory, side-effect free, issues no token.** Returns an indicative verdict, an indicative size, and the binding constraint if any. 50ms timeout. On timeout the caller proceeds with `preview_unavailable=true`.
   - `authorise(proposal) -> AuthorisedOrder | Rejection`: **authoritative.** Runs the full rule chain (R11 §3), mints a signed, single-use, TTL-bounded token, and persists the assessment.
3. Page 09's Decision Intelligence layer **proposes**. Its output type is renamed `TradeProposal`, and the event becomes `evt.decision.proposal.issued.v1` rather than `decision.made`. The verb change is not cosmetic: `made` implies finality that the component does not have.
4. The `Order` aggregate has **no constructor** other than one taking a valid, unexpired, unconsumed `AuthorisedOrder`. Page 10's "no trade reaches Execution without passing Risk" becomes a type-level guarantee rather than a policy.
5. A `PREVIEW` result is a distinct type (`RiskPreview`) that is not assignable to `AuthorisedOrder` and carries no signature. It is impossible to pass a preview where an authorisation is required.
6. The kill switch is re-checked at token issuance, after every rule has passed, with no awaitable operation between the check and the mint (R11 §3, phase 3).

## Rationale

The distinction that resolves the defect is between **information** and **authority**. The Decision Service is entitled to know what Risk would say. It is not entitled to conclude anything from it. Option C encodes exactly that: the preview is information, the token is authority, and the type system keeps them apart.

Point 5 is what makes this robust rather than aspirational. The most likely implementation bug is not someone deciding to bypass Risk; it is someone caching a preview result and treating it as good enough on a retry path. A distinct, unsigned type makes that a compile error.

Point 4 is the equivalent guarantee one layer down. An `Order` that cannot be constructed without a token cannot exist without authorisation, no matter what path reached the Execution service.

Option B is rejected because putting deliberation inside the authorisation boundary means the risk rules can no longer be tested deterministically, which is the property that makes them trustworthy.

## Consequences

**Positive**
- One place to look when asking "why was this trade allowed."
- The rule chain is deterministic and independently testable with no LLM in the loop.
- The Decision Service stays smart about what it proposes, so deliberation spend is not wasted on obviously-rejectable ideas.
- Rejections and approvals are persisted with equal durability by the same component, which makes the rejection analysis in R11 §12 possible at all.

**Negative**
- Two entry points that must stay semantically aligned. A preview that diverges materially from the eventual decision is a bug, and it needs a metric: `preview_decide_divergence_rate`, alerted above a threshold.
- One extra synchronous hop on the proposal path, budgeted at 50ms.

**Neutral**
- Page 09 keeps all of its analysis. Only its output verb and authority change.

## Tripwire

If `preview_decide_divergence_rate` exceeds 10% sustained, the preview is not modelling the decision well enough to be worth its latency, and it should either be fixed or removed. A preview that is frequently wrong is worse than no preview, because it trains the Decision Service on a false constraint surface.

## Related

- ADR-0012 (portfolio read models) closes the other half of the boundary problem
- ADR-0016 (OMS owns order lifecycle)
- ADR-0019 (exits never blocked) constrains the rule chain this ADR makes authoritative
- `../review/R03_Domain_Model_DDD.md` §6
- `../review/R11_Risk_Architecture.md` §3
- Blocking defect B4
- Source: `../09_Decision_Intelligence_Layer.md`, `../10_Risk_Portfolio_Platform.md`
