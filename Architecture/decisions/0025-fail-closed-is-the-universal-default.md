# ADR-0025: Fail-closed is the universal default for every dependency failure

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** safety, reliability, foundational

---

## Context

The ADD handles failure well in places and inconsistently overall. Page 01 has circuit breakers. Page 02 quarantines bad data. Page 04 serves stale regime data with a staleness flag. Page 08 has desks abstain on timeout. Page 10 has a kill switch.

What is missing is a **stated default.** Each page decides independently what happens when a dependency fails, and the decisions do not compose. The result is that failure behaviour is a property of whoever wrote each component rather than a property of the platform, and the composite behaviour under a multi-component failure is undefined.

The specific danger is that **fail-open is the natural default of almost every language and library.** A timeout raises, the caller catches it, logs a warning, and continues with a default value. That code looks defensive. It reads as robust. And on a trading platform it means: proceed with the trade despite not knowing the current exposure, the current kill-switch state, the current instrument spec, or whether the model that produced this signal is still healthy.

Blocking defect B2 (the kill switch failing open) is one instance of this general problem. Fixing only that instance leaves the pattern intact everywhere else.

## Options considered

**A. Per-component decisions (status quo).**
*Pros:* each component can optimise its own availability.
*Cons:* no composite guarantee; the most dangerous paths are the ones most likely to have a broad `except` clause added under time pressure; the behaviour under multi-component failure is undefined.

**B. Fail-open by default, fail-closed where explicitly required.**
*Pros:* maximises uptime; the platform keeps trading through partial degradation.
*Cons:* "keeps trading through partial degradation" is the sentence that describes every automated-trading disaster. Every fail-closed path must be individually identified, and the ones missed are silent.

**C. Fail-closed by default, fail-open only where explicitly justified and documented.**
*Pros:* the dangerous direction requires a deliberate, reviewable decision; unlisted paths are safe by default; composite behaviour is defined.
*Cons:* more halts, including some unnecessary ones; availability is lower.

## Decision

**Option C.** **Every dependency failure on any capital-affecting path resolves to "do not trade."**

### The rule

> If a component cannot verify that an action is safe, the action does not happen.
> Absence of a "no" is never a "yes."

### Applied concretely

| Dependency fails | Behaviour |
|---|---|
| Kill-switch tier unreadable | **HALTED** (ADR-0018) |
| Portfolio snapshot query times out (30ms) | **Reject the trade** |
| Instrument Master unreachable | **Reject the order** (ADR-0015) |
| Postgres unreachable | **Halt.** No authorisation can be persisted, so none is issued |
| Broker adapter times out | **`UNKNOWN` order state**, reconcile, **never blind-retry** |
| Evidence node critically stale | **`NO_ACTION`** (ADR-0021) |
| Below desk quorum | **`NO_ACTION`** (ADR-0021) |
| Model degraded beyond `max_staleness` | Evidence marked critically stale, which blocks proposals |
| Multiple models degrade simultaneously | **Kill switch** (R11 §6) |
| Reconciliation break, critical | **Halt new entries** |
| Schema validation failure on a desk response | **Desk abstains** (counts against quorum) |
| Platform mode not verifiable | **Treat as HALTED** |

### The documented exceptions

Fail-open is permitted **only** where a wrong or missing answer cannot cost money, and each exception is listed here:

| Path | Behaviour on failure | Why safe |
|---|---|---|
| `qry.risk.preview` (advisory) | Proceed with `preview_unavailable=true` | Advisory only. The authoritative Risk Engine still decides downstream (ADR-0011) |
| Dashboard read models | Show stale with a visible timestamp | Human-facing, never a control input. **Never a spinner forever** |
| Telemetry, metrics, tracing | Drop | Observability loss is not a capital risk. Alert on it separately |
| Tick stream (`TICKS`) | Drop | Explicitly droppable by design (R01 §6). Never a decision input |
| Learning pipeline | Retry, then defer to the next cycle | Nothing on the capital path depends on it completing |
| Cost Governor | Fail closed (block the cycle) | Listed here because the instinct is to fail open on a budget check. It fails closed |

**Any path not in this table fails closed.** Adding a row requires an ADR amendment.

### Enforcement

1. **A chaos suite in CI** kills each dependency in turn and asserts the platform refuses to trade rather than degrading open (R15 §10). This is the only way this ADR stays true.
2. **A broad `except Exception` on a capital path is a review failure.** Exception handling on those paths enumerates what it catches and what it does in each case.
3. **Timeouts are mandatory and explicit on every external call.** There is no default-infinite timeout anywhere. An unbounded wait is fail-open in slow motion.

## Rationale

The asymmetry that governs the whole platform applies here in its most general form: **not trading costs opportunity, trading wrongly costs capital.** Opportunity is replaceable and arrives again in fifteen minutes. Capital is not.

The choice of *default* matters more than the individual decisions, because the default governs every path nobody thought about. Under Option B, a path nobody considered is dangerous. Under Option C, a path nobody considered is merely unavailable. Over a decade, the number of unconsidered paths is large.

The chaos suite is what separates this from a slogan. Fail-closed behaviour is invisible in normal operation and therefore untested by ordinary use. Every claim in the table above is either verified by a test that kills the dependency, or it is an assumption that will be wrong when it matters.

Rule 3 deserves emphasis because it is the most commonly violated. A call with no timeout does not fail closed or open; it hangs, and a hung order path is worse than either. The kill switch cannot help a process that is blocked inside a socket read.

## Consequences

**Positive**
- The composite behaviour under multi-component failure is defined and safe.
- Paths nobody thought about are safe by default.
- The dangerous direction requires a deliberate, reviewable, documented decision.
- The chaos suite makes it verifiable rather than aspirational.

**Negative**
- **Lower availability, by design.** The platform will halt for reasons that turn out not to have mattered. This is the cost, and it is accepted.
- Infrastructure reliability becomes a trading concern: every dependency's uptime directly affects trading uptime. This is a real operational burden and it is the correct incentive.
- Spurious halts must be clearly distinguished from risk-driven halts in alerting, or the operator will learn to ignore halts. That is the failure mode that would undo this ADR in practice.

**Neutral**
- The exception table is small and reviewable.

## Tripwire

If **fail-closed halts exceed roughly 4 per month** and are attributable to infrastructure rather than to risk conditions, the response is to **fix the infrastructure**, not to loosen the rule. Repeated proposals to add rows to the exception table are the signal that this is happening, and this ADR should be cited.

If the chaos suite is ever disabled or allowed to fail, this ADR is no longer in force regardless of what the code appears to do.

## Related

- ADR-0018 (kill switch) is this principle's most important instance
- ADR-0015 (reference data), ADR-0021 (quorum), ADR-0011 (portfolio query) are all instances
- ADR-0023 (no auto-liquidation) is why frequent halts are tolerable
- ADR-0022 (broker-side stops) is why halting with open positions is safe
- `../review/R11_Risk_Architecture.md` §10
- `../review/R15_Security.md` §10 (chaos suite)
- `../review/R01_Event_Architecture.md` §12 (the sync/async boundary rule)
