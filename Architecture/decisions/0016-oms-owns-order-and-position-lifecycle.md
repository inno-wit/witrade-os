# ADR-0016: Order and position lifecycle is owned by a dedicated OMS

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** execution, risk, domain

---

## Context

**The current architecture is entirely entry-biased.** Trace the ADD end to end: trigger, evidence, committee, decision, risk, order, fill, journal. **It ends at the fill.**

Nothing in seventeen pages owns:

- Moving a stop to breakeven
- Trailing a stop
- Taking partial profit
- Time-based exits
- Exiting because the structural thesis was invalidated
- A position modified manually at the MT5 terminal
- A position closed by the broker (margin call, stop-out) that the platform did not initiate
- A position that exists at the broker and not in the platform

For most discretionary and systematic strategies, **exit management contributes as much to the outcome as entry selection.** A platform with a six-desk AI committee for entries and nothing at all for exits is optimising the wrong half.

Three structural consequences follow:

1. The trade lifecycle state machine (R07 §5) has no home.
2. The `UNPROTECTED` state (an open position with no broker-side stop) is undetectable, and it is the single most dangerous state a position can be in.
3. Learning receives entry attribution without management attribution, so it cannot distinguish a bad entry from a badly-managed good entry. That distinction is most of what a review cycle should produce.

## Options considered

**A. Extend the Execution Service to manage positions.**
*Pros:* no new service; execution already talks to the broker.
*Cons:* conflates two responsibilities with different shapes. Execution is a stateless translator: take an authorised order, talk to the broker, report what happened. Lifecycle management is stateful, long-running, and policy-driven. Merging them makes the broker adapter path stateful, which is exactly where statelessness is most valuable.

**B. Let the Committee manage exits by running a decision cycle per open position.**
*Pros:* reuses the existing machinery; exits get the same reasoning quality as entries.
*Cons:* the latency and cost are wrong by orders of magnitude. A stop that should move to breakeven when price reaches 1R cannot wait eleven seconds and six LLM calls. Most exit management is deterministic policy, not deliberation. It would also make exits dependent on LLM availability, which violates ADR-0019's spirit entirely.

**C. A dedicated OMS owning order and position lifecycle.**
*Pros:* one owner for the whole trade, entry to exit; deterministic and fast; the trade lifecycle state machine has a home; `UNPROTECTED` becomes detectable and actionable; management actions are attributable for Learning.
*Cons:* a new service; a second component that can originate orders, which needs its authorisation path defined carefully.

## Decision

**Option C.** A dedicated **Order & Position Lifecycle Manager (OMS)**, container C23, in BC8.

### It owns

1. **The order state machine**, including the `UNKNOWN` state (R07 §4). An order whose status could not be determined is never blind-retried.
2. **The trade lifecycle state machine** (R07 §5), from `PROPOSED` through `PROTECTED`, `MANAGED`, `SCALING_OUT`, to a terminal state.
3. **Management policies**, evaluated deterministically on every bar close and on every material price move:
   - Move stop to breakeven at a configured R multiple
   - Trail stop by ATR or by structure
   - Partial take-profit at configured levels
   - Time-based exit (maximum holding period)
   - Thesis invalidation exit (the structural condition that justified entry no longer holds)
4. **Exit origination.** The OMS is the only component other than the operator that may originate an exit. Exits route through `authorise_exit` (ADR-0019) and are not blocked by entry gates.
5. **Detection and remediation of `UNPROTECTED`.** A position with no live broker-side stop is a P0 condition. The OMS attempts to place the stop; failing that, it escalates to a halt and alerts. This state must never persist silently.
6. **Reconciliation of externally-originated changes.** A position modified at the MT5 terminal, or closed by the broker, is detected and folded into the trade record rather than causing a permanent divergence.

### Boundaries

| Component | Responsibility |
|---|---|
| Decision Service | Proposes **entries** |
| Risk Engine | **Authorises** everything (ADR-0011) |
| **OMS** | Owns the **lifecycle**: management policy, exit origination, protection state |
| Execution Service | **Stateless translator** to the broker |
| Position Ledger (BC7) | Owns the **book**: what is open, at what cost basis |

7. **Management policies are versioned, point-in-time-resolvable domain parameters** (ADR-0030's registry), not code constants. A backtest must use the trailing rule that was live at the time.
8. **Every management action is an event** (`evt.position.stop_moved.v1`, `evt.position.reduced.v1`) carrying the `decision_id` of the originating entry, so Learning can attribute management separately from entry selection.

## Rationale

The strongest argument is the one about attribution. Without management events, the Learning loop sees "entry at X, exit at Y, result Z" and can only conclude something about entry quality. With them, it can distinguish a good entry ruined by a stop trailed too tightly from a bad entry rescued by a time exit. That distinction is most of the value of a review cycle, and it is unavailable in the current design at any level of effort, because the data does not exist.

The second argument is `UNPROTECTED`. An open position with no broker-side stop is exposed to an unbounded loss if the platform dies. ADR-0022 requires the stop; the OMS is what **notices** when it is missing. A requirement with no detector is a hope.

Option B is worth naming because it is superficially attractive: the committee already reasons well, so why not use it for exits? The answer is that most exit management is not a judgement call, it is a rule, and routing rules through a probabilistic, expensive, high-latency, externally-dependent path makes them slower, costlier, and less reliable for no gain. Deliberation belongs where the question is genuinely open.

Rule 4 combined with ADR-0019 is what makes exits actually work: a dedicated originator that is not blocked by the gates designed to prevent taking on risk.

## Consequences

**Positive**
- The trade lifecycle has an owner, entry to exit.
- `UNPROTECTED` is detectable and remediated.
- Learning can attribute entry and management separately.
- Exit management is deterministic, fast, cheap, and independent of LLM availability.
- Externally-originated position changes are folded in rather than causing permanent divergence.

**Negative**
- A new service, and a second component that can originate orders. Its authorisation path (via `authorise_exit`) must be exercised in testing as thoroughly as the entry path.
- Management policies are a new class of domain parameter to version, tune and validate, with their own overfitting risk. They go through the same PBO/DSR gate as any other tunable.
- The OMS evaluates policies on every bar close for every open position, which is a new recurring workload (small, but it must not stall).

**Neutral**
- Execution stays stateless, which is where its value is.

## Tripwire

**None for the decision.** A platform that manages entries and not exits is incomplete.

**Operational tripwires:**
1. Any `UNPROTECTED` duration exceeding 60 seconds is an incident, reviewed individually.
2. If management policies grow past ~8 rule types, revisit whether some belong in a strategy definition rather than in the OMS.

## Related

- ADR-0019 (exits never blocked) is what makes the OMS's exit path work
- ADR-0022 (broker-side hard stop) is the requirement the OMS enforces
- ADR-0011 (Risk as sole authoriser) governs OMS-originated actions
- ADR-0012 (Portfolio owns the book) draws the boundary against BC7
- `../review/R19_Missing_Components.md` §3 (largest functional gap in the ADD)
- `../review/R07_State_Machines.md` §4, §5
- `../review/R05_Interface_Contracts.md` §5
