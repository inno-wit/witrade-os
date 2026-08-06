# ADR-0018: The kill switch is a three-tier fail-closed interlock

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** risk, safety, reliability

---

## Context

Page 10 specifies a kill switch and gets the hardest part right: it is a **synchronous in-process gate, not a pub/sub subscriber**, with the propagation-window reasoning stated. That decision is preserved by ADR-0017 and is not what this ADR changes.

What page 10 does not specify is **where the switch state lives and what happens when reading it fails.** The document places live risk state in Redis. Following that through:

- Redis is unreachable → the check cannot be performed → the code path that "checks the kill switch" either throws or returns a default.
- If it throws and the caller catches broadly (the common pattern under an order-submission try block), trading continues.
- If it returns a default, the default in almost every implementation of a boolean flag is `False`, meaning "not halted."

**The switch therefore fails open.** The single control designed to stop the platform when something is badly wrong is disabled by exactly the kind of infrastructure failure that indicates something is badly wrong. This is blocking defect B2.

There is a second gap. A network partition that isolates the Execution service from the Risk service and from Redis leaves Execution holding a stale in-process boolean that says "trading permitted," with no way to learn otherwise and no reason to stop. It will keep trading on stale state for as long as the partition lasts.

## Options considered

**A. Single store (Redis), with an explicit fail-closed catch.**
*Pros:* one line of change from the status quo; simple.
*Cons:* a single point of failure for the platform's most important control. Every Redis blip becomes a full trading halt, which is safe but operationally punishing enough that someone will eventually widen the catch. Does not address the partition case at all.

**B. Postgres only, as the durable truth.**
*Pros:* durable, transactional, no divergence.
*Cons:* ~5ms per check on the hot order path, and it makes the order path depend on the transactional database's availability. Also does not address the partition case.

**C. Three tiers, fail-closed on any failure, plus an independent self-halt heartbeat.** In-process boolean (T1), Redis (T2), Postgres (T3). Halted if any tier says halted **or any tier is unreadable**. Every order-capable process independently halts itself if its last successful full-tier verification is older than a threshold.
*Pros:* no single point of failure; fast path stays fast; every partial failure resolves to halted; the self-halt heartbeat covers the partition case that no amount of shared state can.
*Cons:* three stores to keep consistent; more failure modes to reason about; a spurious halt is more likely than under a single-store design.

## Decision

**Option C.**

### Tiers

| Tier | Store | Read latency | Purpose | On failure |
|---|---|---|---|---|
| **T1** | In-process boolean, refreshed by subscription plus a 1s poll | ~0ms | The final check on the order path | If last refresh > 5s ago, treat as **HALTED** |
| **T2** | Redis | ~1ms | Shared state across processes | If unreachable, treat as **HALTED** |
| **T3** | Postgres | ~5ms | Durable truth, checked at token issuance | If unreachable, treat as **HALTED** |

### Combination rule

```
HALTED if ANY tier says HALTED
      OR ANY tier is unreadable
```

**Never a majority vote. Never a fallback to the fastest available tier.** Both of those are the natural engineering instincts here and both reintroduce fail-open behaviour.

### Write ordering

- **On trip:** T3 (durable) → T2 → T1 → broadcast `cmd.platform.halt.v1`.
- **On clear:** T3 → T2 → T1.

Both orders are chosen so that a crash at any point leaves the switch **engaged**. Tripping writes durable-first so a crash mid-trip is still halted. Clearing writes durable-first so a crash mid-clear leaves the fast tiers still halted, which is the safe direction.

### Self-halt heartbeat

Every order-capable process independently tracks the age of its last successful **full-tier** verification (all three tiers read successfully). Beyond **10 seconds** it halts itself, without waiting to be told and without any dependency on being reachable.

This is the control that makes the switch robust to a network partition. It is also the only element of this design that does not depend on any shared component being available.

### Placement on the order path

The kill switch check is the **last rule evaluated** and is **re-checked at token issuance**. Between the final check and minting the `AuthorisedOrder` there must be **no awaitable operation** (R11 §3, phase 3). An `await` in that gap is a window in which the switch can trip while an authorisation is in flight.

### Scope

`(scope, account_id)` where scope is one of `platform`, `account`, `symbol`, `strategy`. A halt at a broader scope implies a halt at every narrower scope within it.

## Rationale

Fail-closed is the only defensible default for a control whose entire purpose is to stop the platform when something is wrong. Infrastructure failure is correlated with the conditions that warrant a halt, so a design that trades in the presence of infrastructure failure is a design that trades in exactly the wrong circumstances.

The three tiers exist because the requirements conflict. The order path needs a sub-millisecond check (T1). Multiple processes need shared state (T2). The state must survive a restart and be provable after the fact (T3). No single store gives all three. Combining them with an OR over both "halted" and "unreadable" means the design has no single point of failure in the safe direction and three in the fail-safe direction, which is the correct asymmetry.

The self-halt heartbeat is the piece most likely to be omitted and the one that covers the failure no shared state can. A partitioned process cannot be told to stop. It has to decide to.

**The cost is accepted deliberately:** this design will halt trading spuriously more often than a single-store design. That is the correct trade. A spurious halt costs a missed setup. A fail-open switch costs the account. ADR-0019 is what makes this cost bearable: because exits are never blocked, a spurious halt cannot trap the platform in a position, which is what would otherwise make operators reluctant to run a sensitive switch.

## Consequences

**Positive**
- No infrastructure failure mode results in continued trading.
- A network partition halts the isolated process within 10 seconds, autonomously.
- Every partial write leaves the system halted, so there is no dangerous intermediate state.
- The switch becomes safe to trip aggressively, which makes every other control that escalates to it more usable.

**Negative**
- Spurious halts will happen. They need a clear operator signal that distinguishes "halted because a limit was breached" from "halted because Redis was unreachable for six seconds," or the operator will learn to ignore halts.
- Three stores must be kept consistent, and a divergence between them is itself an incident. Add a periodic consistency check that alerts on any tier disagreeing with T3 while all three are readable.
- Clearing is now a multi-store operation with its own partial-failure modes, all of which resolve to still-halted, which means a clear can silently fail to take effect. The clear operation must verify all three tiers post-write and report failure explicitly.

**Neutral**
- Latency on the order path is unchanged in the common case: T1 is the hot check, T3 is consulted once at issuance.

## Tripwire

If spurious halts (halts with no risk cause) exceed **two per month**, the infrastructure underneath is not reliable enough and the fix is the infrastructure, not the switch's sensitivity. Loosening the combination rule is not an available response, and this ADR should be cited when that is proposed.

## Related

- ADR-0017 (kill switch is synchronous, not pub/sub) preserves page 10's original decision
- ADR-0019 (exits never blocked) is what makes an aggressive switch safe
- ADR-0023 (the switch does not auto-liquidate)
- ADR-0025 (fail-closed as the universal default)
- ADR-0037 (commands vs events) governs `cmd.platform.halt.v1`
- `../review/R11_Risk_Architecture.md` §7
- `../review/R07_State_Machines.md` §7
- Blocking defect B2
- Source: `../10_Risk_Portfolio_Platform.md`
