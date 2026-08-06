# ADR-0031: All LLM traffic goes through one gateway; no service imports a vendor SDK

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** ai, boundaries, security, cost

---

## Context

The ADD has at least eight components that call an LLM: six committee desks, the text-extraction ACL, and the Red Team. Page 08 names "prompt and model drift" as a failure mode and provides no component that owns it.

If each caller imports the vendor SDK directly, several properties become impossible rather than merely difficult:

- **A model upgrade is a change in eight places**, and any one missed produces a silent inconsistency where two desks run different models.
- **Cost is unbounded and unattributable.** No component knows the total spend, so nothing can stop a runaway loop.
- **Vendor error semantics leak into domain code.** Rate limits, overloaded errors, stop reasons and token accounting become concepts that the Deliberation context has opinions about.
- **There is no place to enforce redaction**, so an evidence payload containing something sensitive leaves the network with nothing having inspected it.
- **There is no place to put the L4 injection check** (ADR-0032).

## Options considered

**A. Direct SDK use in each service.**
*Pros:* simplest; fewer components; no extra hop.
*Cons:* all five problems above. Each is individually survivable and collectively they mean nobody owns the LLM relationship.

**B. A shared client library, no service.**
*Pros:* one place for retry and model configuration; no network hop.
*Cons:* budget enforcement across processes requires shared state anyway; a library cannot enforce anything on a caller that chooses not to use it; version skew between services running different library versions.

**C. An LLM Gateway service that every caller goes through.**
*Pros:* one enforcement point for budget, redaction, injection inspection, model pinning, circuit breaking and cost accounting; vendor concepts translated once; a model upgrade is a one-line change in one place.
*Cons:* a network hop on the decision path; a new single point of failure.

## Decision

**Option C.** The **LLM Gateway** (container C17) is ACL-3 in the domain model.

1. **No `anthropic` import outside `adapters/llm/`.** A `grep -r "anthropic" --exclude-dir=adapters` returning any hit is a **CI failure**.
2. **The gateway translates vendor concepts into domain concepts.** Model IDs, token counts, stop reasons, rate-limit errors and tool-use blocks become `DeskOpinion`, `DeskAbstained(reason)`, `BudgetExceeded`. No vendor type crosses the boundary.
3. **Model pinning is resolved by the gateway** from the prompt registry (ADR-0030). The caller names a desk and an `as_of`; it does not name a model. **A model upgrade is a one-line change in one file**, which is what page 08's drift failure mode requires and currently has no home for.
4. **Budget enforcement.** Per-cycle, per-day and per-month caps, enforced synchronously. Exceeding a cap returns `BudgetExceeded`, which the caller converts to an abstention with reason `BUDGET_EXCEEDED` (ADR-0021). **The gateway fails closed on a budget check** (ADR-0025).
5. **Circuit breaker.** On vendor outage, the breaker opens and every desk abstains, quorum fails, and the cycle terminates `NO_ACTION`. **There is explicitly no fallback to quant-only trading.** A platform designed around a committee does not silently become a different platform when the committee is unavailable.
6. **Redaction and inspection.** Outbound payloads are inspected for anything that must not leave the network, and for instruction-like patterns (L4 of ADR-0032). A hit is `INJECTION_SUSPECTED` plus a P1 alert.
7. **Cost accounting per call.** `evt.llm.call.completed.v1` carries tokens, cost, latency, model version and prompt version, feeding the Cost Governor and the Decision Record Store.
8. **The gateway lives in the DMZ trust zone** (R15 §2). It is the only component with egress to the vendor endpoint. Nothing in CORE or VAULT talks to the internet.

## Rationale

The strongest argument is the one about model pinning. A quant platform's decisions are a function of its model version, and a platform that cannot state which model produced a given decision cannot backtest, cannot attribute, and cannot upgrade safely. Centralising resolution means the model version is a **property of the resolved prompt artefact**, and every decision record carries it.

Budget enforcement genuinely requires a service rather than a library. Per-day and per-month caps are cross-process state, and the failure being prevented (a bug that convenes committees in a loop) is exactly the case where each process individually believes it is behaving reasonably. A library cannot see the aggregate.

Rule 5 deserves emphasis because the tempting alternative is real. When the vendor is down, it feels reasonable to fall back to the deterministic baseline and keep trading. That would mean the platform silently switches to a strategy that has never been validated as a standalone strategy, at the moment of an unrelated infrastructure failure. If the deterministic baseline is good enough to trade alone, that should be a deliberate, backtested, promoted decision (which is exactly what ADR-0027's tripwire 1 provides for), not an outage fallback.

The single-point-of-failure objection is answered by ADR-0025: a gateway failure resolves to no trading, which is the correct outcome and is the same outcome as a vendor outage. It adds no new failure mode, only a new location for an existing one.

## Consequences

**Positive**
- A model upgrade is one line in one file.
- Total LLM spend is known, capped, and attributable per cycle and per desk.
- Vendor semantics stay out of domain code, so a vendor change is an adapter change.
- One enforcement point for redaction and injection inspection.
- Per-call cost, latency and version telemetry for free.

**Negative**
- A network hop on the decision path. Budgeted; the hop is microseconds against an 8s desk deadline.
- A component that must be highly available, or nothing deliberates. Mitigated by it being stateless and trivially restartable.
- A grep-based CI rule that must be maintained, and that will produce a false positive on a docs file eventually.

**Neutral**
- The vendor relationship is unchanged. This is purely an internal boundary.

## Tripwire

1. **If a second LLM vendor is introduced** (ADR-0026 tripwire 3), the gateway is where it lands and this decision is validated rather than revisited.
2. **If gateway latency ever becomes material** relative to the desk deadline, measure before optimising. It should be a rounding error.
3. **If the circuit breaker fallback is ever proposed** as "just use the baseline," point at rule 5 and at ADR-0027's tripwire. The baseline trading alone is a promotion decision, not a failover.

## Related

- ADR-0032 (text ACL) places its L4 check here
- ADR-0030 (prompt registry) supplies the model pin
- ADR-0026 (isolated desks) sends six calls through this
- ADR-0025 (fail-closed) governs budget and breaker behaviour
- ADR-0021 (quorum) consumes the abstentions this produces
- `../review/R03_Domain_Model_DDD.md` §9 (ACL-3)
- `../review/R15_Security.md` §2
- `../review/R10_Committee_Architecture.md` §8, §12
