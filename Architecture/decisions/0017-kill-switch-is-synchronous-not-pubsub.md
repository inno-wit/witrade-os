# ADR-0017: The kill switch is a synchronous in-process gate, not a pub/sub subscriber

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** risk, safety, reliability

---

## Context

Page 10 states that the kill switch is checked synchronously in-process rather than being delivered as a pub/sub event, and gives one sentence of justification about the propagation window.

**That decision is correct and it is recorded here because it is fragile against a future refactor.** The platform is event-driven nearly everywhere else. In 2028, someone tidying the architecture will see a synchronous, blocking call to a shared state store sitting in the middle of an otherwise fully asynchronous order path, will recognise it as an inconsistency, and will "fix" it by making the Execution Service subscribe to `evt.risk.killswitch.triggered.v1` like every other component.

That change would look like a cleanup. It would pass review. It would pass every test. And it would reintroduce a window, measured in the tens to hundreds of milliseconds, during which the switch is engaged and the platform is still sending orders.

This ADR exists so that the reasoning is attached to the code.

## Options considered

**A. Pub/sub subscription.** Execution subscribes to a kill-switch event and sets a local flag.
*Pros:* architecturally consistent; decoupled; no blocking call on the order path.
*Cons:* **a propagation window.** Between the switch tripping and the subscriber processing the message there is broker latency, network latency, queue depth and handler scheduling. Under normal conditions that is single-digit milliseconds. Under the conditions where the switch actually trips (a runaway order loop, a degraded network, a saturated event bus, a garbage-collection pause) it is exactly when queues are deepest and delivery is slowest. **The control is least responsive precisely when it is most needed.** Worse, a subscriber that has crashed or fallen behind has no idea it is stale, and the local flag says "trading permitted."

**B. Synchronous check on the order path.** Every order-capable code path checks the switch state directly and blocks on the result.
*Pros:* no propagation window; the check reflects state at the moment of the decision; a failed check is visible immediately rather than being silently stale.
*Cons:* a blocking call on the hot path; a dependency on a state store's availability at order time; architecturally inconsistent with the rest of the platform.

**C. Hybrid: subscribe for speed, verify synchronously before acting.**
*Pros:* the subscription keeps a local cache warm; the synchronous verification closes the window.
*Cons:* two mechanisms to reason about.

## Decision

**Option C, which is Option B with a warm cache.** Page 10's decision is preserved and made precise:

1. **The final check before any order is submitted is synchronous and blocking.** It is not a cached flag updated by a subscription, and it is not a value read at the start of the request.
2. **The subscription exists**, but only to keep the T1 in-process value warm and to make the common path fast. It is never the authority.
3. **The check is the last thing that happens before the order goes out.** Between the check and the submission there is **no awaitable operation**. An `await` in that gap reintroduces the window this ADR exists to close, in a form that is harder to see.
4. **Staleness of the in-process value is itself a halt condition.** A T1 value not refreshed within 5 seconds reads as HALTED (ADR-0018). This is what makes the fast path safe: a stale cache fails closed rather than silently permitting.
5. **The three-tier structure, the fail-closed combination rule, and the self-halt heartbeat are specified in ADR-0018.** This ADR governs *when and how* the check happens; ADR-0018 governs *what it reads and what failure means.*

## Rationale

The asymmetry is the whole argument. A synchronous check costs sub-millisecond latency on a path that is already spending hundreds of milliseconds on a broker round trip. It is, in relative terms, free.

A pub/sub check costs a propagation window, and that window is not a fixed small number. It scales with queue depth, and queue depth scales with exactly the conditions that trip the switch. The risk is correlated with the trigger, which is the worst possible property for a safety control.

The second, subtler argument is **observability of staleness**. A synchronous check that fails is a visible, immediate, actionable failure. A subscriber that has silently fallen behind, crashed, or been disconnected reports nothing: its local flag still says "trading permitted," and it will keep saying so indefinitely. Rule 4 converts that silent failure into a halt.

Rule 3 is the one most likely to be violated by accident. `check_kill_switch()` followed by `await build_order_payload()` followed by `await submit()` looks fine and contains the same window the ADR set out to eliminate, only smaller and harder to notice. The rule must be stated as "no awaitable operation between check and submit," not as "check before submitting."

**On architectural consistency:** the inconsistency is real and it is correct. Safety interlocks are not application logic and should not inherit application logic's coupling patterns. This is the same principle as a hardware emergency stop being hardwired rather than routed through a controller.

## Consequences

**Positive**
- No propagation window on the order path.
- Stale state fails closed and is visible, rather than silently permitting.
- The control's responsiveness does not degrade under the load conditions that trigger it.

**Negative**
- A blocking call on the hot path, and a dependency on the state tiers being reachable at order time. Both are addressed by ADR-0018's tier structure: T1 is in-process and always available, and its staleness is itself a halt.
- Architectural inconsistency that must be documented at the call site, or it will be refactored away. **Every implementation of the check carries a comment linking to this ADR.**

**Neutral**
- The event `evt.risk.killswitch.triggered.v1` still exists for observers (Journal, Monitoring, Learning). It is a notification, never a control (ADR-0037).

## Tripwire

**None. This decision should not be revisited.**

If a future refactor proposes making the kill switch fully asynchronous "for consistency," the answer is no, and this ADR is the reason. The only change that would be acceptable is one that reduces the window further, and there is no window left to reduce.

## Related

- ADR-0018 (three-tier fail-closed interlock) specifies what the check reads
- ADR-0019 (exits never blocked) is what makes an aggressive switch safe to use
- ADR-0025 (fail-closed universal default)
- ADR-0037 (commands vs events) governs `cmd.platform.halt.v1` and the observer event
- `../review/R11_Risk_Architecture.md` §1, §7
- Source: `../10_Risk_Portfolio_Platform.md` (this ADR preserves its decision)
