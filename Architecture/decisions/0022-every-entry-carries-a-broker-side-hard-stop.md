# ADR-0022: Every entry carries a broker-side hard stop

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** risk, safety, execution

---

## Context

**This requirement does not appear anywhere in the ADD.** It is added by this review because it is what protects capital through total platform loss, and nothing else does.

Every safety control specified across the seventeen pages depends on the platform being alive: the kill switch, the drawdown ladder, the exposure limits, the OMS management policies, the reconciliation service. Each assumes a running process that can observe and act.

Consider the states where that assumption fails:

- The Windows VPS holding the MT5 terminal loses power or network.
- The Execution service crashes and the container fails to restart.
- A cloud provider incident takes the Linux host down.
- A bug halts the platform cleanly with positions open (which is the *correct* behaviour under ADR-0025).
- The operator is asleep, travelling, or without connectivity.

In each of these, an open position with no broker-side stop is exposed to an **unbounded** loss for the entire duration of the outage. Gold can move several percent in the minutes after an unexpected macro print. A position sized for a 1% risk budget can lose many multiples of it while the platform that was supposed to manage it is simply not running.

A stop that lives only in platform logic is not a stop. It is an intention held by a process.

## Options considered

**A. Platform-managed stops only (implied status quo).** The OMS watches price and sends a close order when the stop level is hit.
*Pros:* flexible; supports stop logic the broker cannot express (structure-based, time-based, volatility-adaptive); no broker-side order to keep synchronised.
*Cons:* provides zero protection when the platform is not running, which is the only scenario where protection is indispensable.

**B. Broker-side stop only.** Attach a stop-loss to every order and never manage it in the platform.
*Pros:* always in force; simple.
*Cons:* the broker can only express price-level stops. Structure-based exits, time exits and thesis-invalidation exits are unavailable, and those are a large part of the OMS's value.

**C. Both, with the broker-side stop as the mandatory floor.** Every entry carries a broker-side stop at or beyond the platform's intended stop. The OMS manages the position more intelligently on top, and updates the broker-side stop when it tightens.
*Pros:* protection survives total platform loss; intelligent management is retained; the broker-side stop is a floor, never a ceiling.
*Cons:* two stops to keep synchronised; a divergence between them is a real failure mode requiring detection.

## Decision

**Option C.**

1. **Every entry order carries a broker-side `stop_loss`.** The `OrderRequest` type makes `stop_loss` **non-optional** for entries. An entry without one is not constructible.
2. **The broker-side stop is placed atomically with the entry** where the broker supports it (MT5 does, via the order's SL field). Where a broker does not, the stop is placed immediately after the fill and the position is `UNPROTECTED` until it is confirmed.
3. **`UNPROTECTED` is a P0 condition** owned by the OMS (ADR-0016). An open position with no confirmed broker-side stop triggers: immediate retry, then escalation to a platform halt plus an alert. It must never persist silently. Any `UNPROTECTED` duration above 60 seconds is an incident.
4. **The broker-side stop is a floor, not the working stop.** It sits at or beyond the platform's intended stop level. The OMS may manage a tighter stop in platform logic, and **when the platform stop tightens, the broker-side stop is moved to match.**
5. **The broker-side stop is never widened** except by an explicit, audited operator action. Tightening is automatic; loosening requires a human. This is the same asymmetry as ADR-0024 and for the same reason.
6. **Reconciliation verifies stop presence**, not only position quantity. A position whose broker-side stop was removed or was never placed is a reconciliation break, and a break of this kind halts new entries.
7. **The stop level is derived deterministically** from the instrument's volatility and the risk budget at authorisation time, and is part of the `AuthorisedOrder` token. It is not an LLM output and is not adjustable at the point of submission.

## Rationale

This is the only control in the entire architecture that works when the architecture does not. Every other safety mechanism (kill switch, drawdown ladder, exposure caps, OMS policies) requires a running process. The broker-side stop is enforced by the broker's infrastructure, which is a different failure domain entirely.

Rule 1 is what makes it real. A requirement enforced by convention will be violated by the first code path that constructs an order slightly differently (a manual close-and-reverse, a test helper promoted to production, a retry path). Making `stop_loss` non-optional on the type means an entry without one does not compile.

Rule 3 exists because rules 1 and 2 can still fail at runtime: the broker can reject the stop, the fill can arrive before the stop is confirmed, a partial fill can leave a fraction unprotected. A requirement with no detector is a hope, and `UNPROTECTED` is the specific state that must be detected.

Rule 4 resolves the tension between protection and intelligence. The broker-side stop is a **disaster floor**, deliberately placed at the level beyond which the loss is unacceptable regardless of any thesis. The OMS's working stop is usually tighter and smarter. Both can exist; only one needs to survive a power cut.

Rule 5 matters because the pressure to widen a stop arrives at exactly the moment it should not be granted: when price is approaching it and the thesis still "feels" right. Making widening a human, audited action is the same insider-risk control as ADR-0024.

## Consequences

**Positive**
- Total platform loss with open positions has a bounded outcome.
- The kill switch and the platform-halt behaviours become genuinely safe to use aggressively, because halting with open positions no longer means unprotected positions.
- Reconciliation gains a second dimension (protection state) that catches a real failure the quantity check misses.
- The maximum loss per trade becomes a property enforced outside the platform.

**Negative**
- Two stops to keep synchronised. Divergence must be detected (rule 6) and is a real ongoing correctness burden.
- A broker-side stop can be hit by a spread spike or a wick that the platform's own logic would have ignored. Mitigated by placing the broker stop at or **beyond** the working stop, so it should never be the first one hit in normal operation. If it is being hit first, the placement is wrong and that is measurable.
- Some brokers handle stop modification poorly under fast markets. The `BrokerAdapter` contract's "never raise on timeout, return `unknown`" rule (R02 §5) applies here too.

**Neutral**
- Slightly more complex order construction.

## Tripwire

**None for the requirement.** Positions do not go unprotected.

**Operational tripwires:**
1. If the broker-side stop is the first stop hit in more than ~5% of losing trades, the floor is placed too tightly relative to the working stop.
2. Any `UNPROTECTED` event is reviewed individually. A pattern indicates a broker interaction problem, not an operational blip.

## Related

- ADR-0016 (OMS) owns detection and remediation of `UNPROTECTED`
- ADR-0019 (exits never blocked) is the platform-side counterpart
- ADR-0023 (no auto-liquidation) is the deliberate limit on automated closing
- ADR-0025 (fail-closed) is why halting with open positions is common enough to matter
- `../review/R11_Risk_Architecture.md`
- `../review/R07_State_Machines.md` §5 (`UNPROTECTED`)
- `../review/R19_Missing_Components.md` §3
