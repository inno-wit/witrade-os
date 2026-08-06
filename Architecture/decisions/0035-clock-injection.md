# ADR-0035: The Clock is injected everywhere; direct wall-clock calls are a CI failure

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** determinism, testing, foundational

---

## Context

The ADD makes three claims that all depend on the same unstated property:

- Page 03: point-in-time correctness, with look-ahead leakage named as "the single most dangerous failure mode in the whole platform."
- Page 09: counterfactual replay as a capability.
- Page 12: hypothesis validation by replaying historical periods.

All three require that the system produce **identical output given identical historical input**. Nothing in the ADD provides that, and the thing that silently destroys it is a direct call to wall-clock time.

The failure mode is uniquely nasty for three reasons:

1. **It is silent.** A backtest containing `datetime.now()` still runs. It produces numbers. The numbers look plausible. Nothing fails.
2. **It is optimistically wrong.** Code that reads live time inside a historical simulation typically sees *the future* relative to the bar being processed, which biases results in the flattering direction.
3. **It is discovered late.** Typically when a strategy that backtested well fails live, months and many decisions later, with no way to determine which historical results were affected.

A single `datetime.now()` in a staleness check, a TTL calculation, a cache expiry, or a retry backoff is enough. And every one of those is a place where writing `datetime.now()` is the obvious, idiomatic thing to do.

The cost asymmetry is extreme. Establishing the discipline now is roughly one hour of work. Retrofitting it means auditing every file, and every instance missed leaves replay broken with no signal.

## Options considered

**A. Convention only.** Document that code should use an injected clock; rely on review.
*Pros:* zero tooling.
*Cons:* the erosion is invisible, so review will not catch it reliably. `datetime.now()` is what fingers type by default. One instance is enough to break determinism, and nothing reports it.

**B. Inject a clock, no enforcement.**
*Pros:* the right abstraction exists.
*Cons:* the abstraction erodes within weeks under any time pressure, and the erosion is undetectable without exactly the tooling this option omits.

**C. Inject a clock, enforce mechanically in CI.** A `Clock` protocol in the shared kernel, injected into every component that needs time, plus a lint rule that fails the build on any direct wall-clock call outside one file.
*Pros:* the property is maintained by a machine rather than by discipline; violations are caught at the commit that introduces them, when they are trivial to fix.
*Cons:* one lint rule to write and maintain; occasional friction with third-party code that reads the clock internally.

## Decision

**Option C.**

### The contract

```python
class Clock(Protocol):
    def now(self) -> "Timestamp": ...
    def logical(self) -> int: ...
    async def sleep(self, seconds: float) -> None: ...
    def deadline(self, seconds: float) -> "Deadline": ...

class WallClock(Clock): ...        # prod, paper
class SimulationClock(Clock):      # sim, replay
    """Advances only when the replay harness advances it.
       sleep() returns immediately and advances logical time.
       This is what makes a 5-year backtest run in minutes AND
       produce byte-identical output to a second run."""
```

1. `Clock` lives in the **shared kernel** (ADR-0014) and is injected into every component that needs time. It is a constructor dependency, never a module-level singleton.
2. `WallClock` is used in `prod`, `paper`, and `dev`. `SimulationClock` is used in `sim` and `shadow` replay.
3. **`sleep` and `deadline` are on the Clock, not just `now`.** This is the part most implementations omit. A backtest that genuinely sleeps for a 300ms broker timeout takes as long as the market did. Under `SimulationClock`, `sleep` returns immediately and advances logical time.
4. `logical()` supplies the `logical_clock` field in the event envelope (R01 §4), which is what makes replay ordering deterministic when two events share a wall-clock millisecond.
5. **CI lint:** any direct `datetime.now()`, `datetime.utcnow()`, `time.time()`, `time.monotonic()`, `asyncio.sleep()`, `pd.Timestamp.now()`, or `date.today()` outside `platform/clock.py` **fails the build**. No exceptions list, no per-file suppressions. Third-party libraries that read the clock internally are wrapped at the adapter boundary or accepted as a documented determinism boundary in the ADR that introduces them.
6. **Determinism test:** a CI test runs the same simulation twice with the same `replay_run_id` and seed and asserts byte-identical output. This is the test that proves the discipline is working, and it is the only way page 03's point-in-time claim is verifiable rather than merely asserted.

## Rationale

This is the cheapest high-value discipline in the entire implementation: roughly an hour of setup that permanently protects a property the platform's three headline capabilities all depend on.

The enforcement in point 5 is the whole decision. Options A and B are the same as C minus the lint, and without the lint the abstraction is gone within a month. This is not pessimism about discipline; it is recognition that the violation is invisible, has no immediate consequence, and looks completely normal in a diff.

Point 3 deserves emphasis because it is the most commonly missed part. Teams that inject `now()` and leave `asyncio.sleep()` alone end up with backtests that are deterministic but take real time to run, which makes them too slow to run often, which means they are not run.

Point 6 is what turns this from a rule into a verified property. A determinism test that runs on every commit converts "we are careful about clocks" into "the system provably replays identically," which is the claim the platform actually needs to make.

## Consequences

**Positive**
- Replay determinism is a verified property rather than an intention.
- Backtests run in minutes rather than in real time, which means they run often enough to be useful.
- Time becomes trivially controllable in tests: a staleness test does not need to sleep, it advances the clock.
- Look-ahead through the clock, one of the two main leakage paths, is closed mechanically. (The other is data-versioning, closed by ADR-0003.)
- Every deadline, TTL, and staleness computation in the system becomes testable at its boundary conditions.

**Negative**
- One lint rule to write and maintain.
- Occasional friction with third-party libraries that read the clock internally. Each such case must be wrapped or explicitly accepted as a documented determinism boundary, which is a small ongoing tax.
- Every component that needs time gains a constructor parameter. This is verbose and it is worth it.

**Neutral**
- Production behaviour is identical. `WallClock` is a thin passthrough.

## Tripwire

**None. This decision should not be revisited.**

The only plausible pressure is a request to suppress the lint for a specific file. The answer is no: the file should take a `Clock`. If a third-party dependency genuinely cannot be wrapped, that is recorded as a named determinism boundary in the ADR that introduces the dependency, and the determinism test is expected to keep passing regardless, because a boundary that breaks it is a boundary that is not acceptable.

## Related

- ADR-0003 (Iceberg) closes the data-versioning leakage path; this ADR closes the time path
- ADR-0014 (shared kernel governance) covers `Clock`'s presence there
- ADR-0034 (point-in-time correctness in five layers); this ADR is layer 4
- `../review/R02_C4_Expansion.md` §5, L4.6
- `../review/R19_Missing_Components.md` §2 (Simulation & Replay Harness)
- `../review/R18_Technical_Debt.md` D2
- Source: `../03_Feature_Store.md`, `../12_Continuous_Learning.md`
