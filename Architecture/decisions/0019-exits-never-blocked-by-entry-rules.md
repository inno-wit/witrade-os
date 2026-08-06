# ADR-0019: Exits are never blocked by entry-blocking rules

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** risk, safety

---

## Context

Page 10 defines a sequential risk pipeline ending in a kill switch, applied to "every Trade Recommendation." It does not distinguish opening a position from closing one. Every rule (drawdown guard, exposure limits, news blackout, kill switch) is described as gating trades generically.

A naive implementation of that pipeline blocks exits under exactly the conditions where exits matter most: a breached drawdown limit, an active kill switch, an approaching high-impact event, or an exposure cap already at its limit.

Page 10 gets the adjacent decision right (the kill switch does not auto-liquidate) but that decision addresses whether the platform should *force* exits. It does not address whether the platform can still *permit* them. Those are different questions and the ADD only answers one.

This is finding G8, and it is the most dangerous latent bug in the current risk design because it does not appear during normal operation or during testing. It appears the first time there is a genuine emergency.

## Options considered

**A. One pipeline for all actions (the implied status quo).**
*Pros:* simplest, one code path, nothing to thread through the API.
*Cons:* it can trap the platform in a position it cannot close, which is an unbounded loss. Every control designed to limit a loss becomes a control that guarantees its continuation.

**B. A separate exit pipeline.**
*Pros:* clear separation, impossible to confuse the two.
*Cons:* it duplicates logic, and the duplicate will drift. The drift will be discovered during an emergency, because that is the only time the exit path is exercised under stress.

**C. One pipeline, per-rule applicability flags.** Each rule declares whether it applies to `ENTRY`, `EXIT`, or both. One chain, one implementation, different behaviour by intent.
*Pros:* one implementation so no drift; the applicability of each rule is declared and reviewable in one table; adding a rule forces the author to answer the question.
*Cons:* the `Intent` concept must be threaded through the risk API; a bug that mislabels an entry as an exit would bypass the gates.

## Decision

**Option C.**

1. Every `RiskRule` declares `applies_to: set[Intent]` where `Intent` is `{ENTRY, EXIT}`.
2. Exit authorisations **skip every rule not applicable to `EXIT`**.
3. Exits use a **distinct entry point**, `authorise_exit(...)`, so the intent is explicit at the call site rather than inferred from a direction field. Inferring intent from direction is a well-known source of exactly this bug.
4. **Intent is derived from the authoritative position state** held by BC7 Portfolio, never from a caller-supplied field. A request to sell when flat is an entry, whatever the caller labelled it. A request to sell 1.0 lots when long 0.6 is an exit for 0.6 and an entry for 0.4, and it is split.

### Rule applicability

| # | Rule | Entries | Exits |
|---|---|---|---|
| 1 | `PlatformModeRule` | Yes | **No** |
| 2 | `KillSwitchPreCheck` | Yes | **No** |
| 3 | `InstrumentTradableRule` | Yes | Yes, **warn only** |
| 4 | `NewsBlackoutRule` | Yes | **No** |
| 5 | `DrawdownGateRule` | Yes | **No** |
| 6 | `ExposureLimitRule` | Yes | **No** |
| 7 | `CorrelationLimitRule` | Yes | **No** |
| 8 | `LiquidityRule` | Yes | Yes, **shapes order type, never blocks** |
| 9 | `ModelRiskRule` | Yes | **No** |
| 10 | `VaRLimitRule` | Yes | **No** |
| 11 | `ProposalValidityRule` | Yes | Yes |

The only rules that survive for exits are the ones that make an exit *worse* if ignored: instrument tradability (informational), liquidity (which shapes the order type, for example a limit rather than a market order into a blown-out spread, rather than blocking), and proposal validity (a corrupted or expired instruction should not be acted on).

5. **Every broker-side hard stop remains in place regardless of platform state** (ADR-0022). The exit path described here is the platform's ability to close deliberately; the broker-side stop is what closes positions when the platform is not there at all. They are independent and both required.

## Rationale

The purpose of every entry-blocking rule is to prevent *taking on* risk. An exit *reduces* risk. Applying a risk-reduction control to a risk-reducing action inverts its purpose.

The concrete scenario: drawdown breaches 12%, the kill switch trips per the R11 §5 ladder, the platform holds three losing positions. Under Option A it cannot close them. The control designed to limit the loss has guaranteed its continuation, and it did so at the precise moment the operator was most likely to be under stress and least likely to diagnose why the close button does nothing.

This is the failure mode where an automated system does the most damage, and it is entirely avoidable at the cost of one declarative field per rule.

Option C over B because a duplicated pipeline will diverge, and the divergence would be discovered during an emergency.

Point 4 is the part that makes this safe rather than merely correct. The obvious objection to Option C is that mislabelling an entry as an exit bypasses every gate. Deriving intent from the authoritative position state rather than trusting the caller removes the attack surface entirely: there is no field an upstream bug can set wrongly. The split case (a sell order larger than the open long) is the one that must be explicitly tested, because it is where a naive implementation would classify the whole order as an exit.

## Consequences

**Positive**
- The platform can always reduce risk.
- The kill switch becomes safe to trip aggressively, which in turn makes every other safety control more usable. This is what makes ADR-0018's deliberately sensitive switch bearable.
- One implementation, no drift between the entry and exit paths.
- The applicability table is a single reviewable artefact, so adding a rule forces an explicit answer to "does this block exits."

**Negative**
- The `Intent` concept must be threaded through the risk API and the OMS.
- The entry/exit split for orders that cross flat is genuinely fiddly and must be tested explicitly: sell 1.0 while long 0.6 is exit(0.6) + entry(0.4), and the entry half runs the full gate chain while the exit half does not.
- An exit path with fewer gates is a smaller target but still a target. Only the OMS and the operator may originate exits, and both are authenticated.

**Neutral**
- Rules gain one declarative field.

## Tripwire

**None. This decision should not be revisited.**

If a future requirement appears to need exits blocked, the requirement is wrong. The thing being asked for is almost certainly either "do not open new positions" (which is what the entry gates already do) or "do not liquidate automatically" (which is ADR-0023 and is a separate, already-correct decision).

## Related

- ADR-0018 (three-tier fail-closed kill switch) is what makes this ADR load-bearing
- ADR-0022 (every entry carries a broker-side hard stop) covers total platform loss
- ADR-0023 (the kill switch does not auto-liquidate) is the adjacent decision, deliberately distinct
- ADR-0016 (OMS owns the exit path)
- `../review/R11_Risk_Architecture.md` §3
- `../review/R07_State_Machines.md`, `../review/R05_Interface_Contracts.md` §6
- Finding G8
- Source: `../10_Risk_Portfolio_Platform.md`
