# ADR-0023: The kill switch does not auto-liquidate

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** risk, safety

---

## Context

Page 10 specifies that tripping the kill switch **stops new activity but does not liquidate existing positions.** That is the correct decision and it is recorded here because it is counter-intuitive enough to be "corrected" by someone reasoning from first principles about what an emergency stop should do.

The intuition that leads to auto-liquidation is straightforward: something has gone wrong, therefore reduce risk to zero immediately. It is wrong for this platform, and the reasoning needs to be attached to the code.

This ADR must be read alongside **ADR-0019**, which addresses the opposite failure. The two together define the complete position: the platform will not *force* exits, and it will never *prevent* them. Confusing these two is the most likely way to get this wrong in either direction.

## Options considered

**A. Auto-liquidate on any kill-switch trip.** Close everything at market.
*Pros:* risk goes to zero immediately; simple to reason about; no ongoing exposure while diagnosing.
*Cons:* the switch trips for many reasons, most of which are not "the market is going against us." Liquidating a full book at market during a spread blowout, a liquidity gap, or a broker incident **realises** losses that were unrealised and may have been recoverable. Worse, an operational trip (a Redis outage, a reconciliation break, a duplicate-order bug) would liquidate a perfectly healthy book because a cache was unreachable. Under ADR-0018 the switch is deliberately sensitive and will trip on infrastructure failure; auto-liquidation would turn every such failure into realised losses.

**B. Never liquidate automatically; the switch blocks new activity only.**
*Pros:* an operational trip has no market impact; positions retain their broker-side stops (ADR-0022), so the loss is already bounded; the operator decides with full information.
*Cons:* exposure persists while the incident is diagnosed; depends on the operator being available, or on the broker-side stop being adequate.

**C. Conditional auto-liquidation by trip reason.** Liquidate on market-driven trips, hold on operational trips.
*Pros:* seems to get both.
*Cons:* the classification must be correct at exactly the moment the system is known to be misbehaving. A kill switch whose behaviour depends on a judgement made by the code that just failed is not a reliable control. It also creates a category of trip whose consequences the operator must remember correctly under stress.

## Decision

**Option B.** Tripping the kill switch **blocks new entries and new risk-increasing activity. It does not close anything.**

1. **On trip:** no new entries, no position increases, no new risk-increasing orders of any kind.
2. **Existing positions remain open**, protected by their broker-side hard stops (ADR-0022), which are already in force and are unaffected by platform state.
3. **Exits remain fully available** (ADR-0019). The operator, and the OMS acting on existing management policy, may close at any time. The switch never prevents risk reduction.
4. **Working orders are cancelled** where they would open or increase a position. Working orders that would reduce a position (a take-profit, a stop) are **left in place.**
5. **The operator is alerted with the trip reason, current exposure, and the distance to every stop**, so the decision to hold or close is made with information rather than by default.
6. **There is no automatic liquidation path in the codebase at all.** Not disabled by a flag, not gated by a config value. It does not exist, so it cannot be enabled by a configuration change during an incident.

## Rationale

The decisive observation is **why the switch actually trips.** Under ADR-0018 the switch is a deliberately sensitive, fail-closed interlock: it trips on an unreachable Redis, a stale tier, a reconciliation break, a runaway order rate, correlated model degradation. Most trips are **operational**, not market-driven.

Auto-liquidating a healthy book because a cache was unreachable for six seconds converts an infrastructure blip into a realised loss plus spread plus slippage on every open position. That is a control that causes the harm it exists to prevent.

The second argument is about market conditions. The moments when a market-driven trip fires (a drawdown breach, an anomalous slippage pattern) are precisely the moments of worst liquidity and widest spreads. Dumping a full book at market into that is the most expensive possible way to exit. A human deciding to scale out over ten minutes will usually do better, and the broker-side stops mean the downside of taking those ten minutes is already bounded.

**The loss is already bounded without liquidation.** This is what makes Option B safe rather than merely cautious, and it is why ADR-0022 is a hard dependency. Without mandatory broker-side stops, "hold and decide" would be an unbounded exposure and Option A would have a real case.

Option C is rejected because it requires correct classification at the exact moment the system's judgement is least trustworthy, and it makes the control's behaviour something the operator must recall correctly under stress. A safety control should do one thing, always.

Rule 6 is deliberate. A liquidation path that exists but is disabled will be enabled during an incident by someone who is sure this time is different.

## Consequences

**Positive**
- An operational trip has zero market impact.
- No forced selling into the worst liquidity.
- The operator decides with full information rather than discovering the book was flattened.
- The switch is safe to trip aggressively, which makes ADR-0018's sensitivity acceptable.

**Negative**
- Exposure persists during an incident. Bounded by the broker-side stops, but real.
- Requires the operator to eventually make a decision. A trip at 3am with the operator asleep means positions ride to their stops, which is the accepted outcome and is exactly what ADR-0022 exists to bound.
- In a genuine fast-collapse scenario, holding is worse than immediate liquidation would have been. Accepted: that scenario is rarer than the operational trip, and the stops still bound it.

**Neutral**
- The operator retains full manual control at all times.

## Tripwire

**None. This decision should not be revisited.**

If a future scenario appears to require auto-liquidation, check first whether what is actually wanted is one of:
- **Tighter broker-side stops** (ADR-0022), which bound the loss without forced selling, or
- **A smaller position size** (ADR-0020), which is the real fix if the exposure is uncomfortable at rest, or
- **An OMS time-based exit policy** (ADR-0016), which closes on a schedule rather than on a panic.

All three are better answers to the underlying concern than a liquidation trigger, and all three are already in the design.

## Related

- ADR-0022 (broker-side hard stop) is what makes holding safe. **Hard dependency**
- ADR-0019 (exits never blocked) is the deliberately distinct adjacent decision
- ADR-0018 (three-tier fail-closed switch) is why most trips are operational
- ADR-0016 (OMS) owns any policy-driven closing
- `../review/R11_Risk_Architecture.md` §7
- Source: `../10_Risk_Portfolio_Platform.md` (this ADR preserves its decision)
