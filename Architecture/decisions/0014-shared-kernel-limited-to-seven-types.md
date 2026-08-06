# ADR-0014: The shared kernel is limited to seven type groups, with explicit governance

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** ddd, boundaries, governance

---

## Context

ADR-0010 establishes eleven bounded contexts with exclusive data ownership. Some vocabulary must nonetheless be common: eleven independent definitions of `Symbol` guarantees conversion bugs at every boundary.

Anything placed in the shared kernel is depended on by every context, so **every change to it is a breaking change to eleven contexts.** That makes the shared kernel the single highest-leverage place to be wrong, and the place where scope creep is most expensive. In a solo codebase the pressure is severe: putting a type in `common/` is always the locally easier move.

The failure mode is well documented and specific: `common/` accumulates, becomes a de-facto domain model, and the bounded contexts stop being independent because they all share the same `Position` class. At that point the eleven contexts are eleven packages with one model, which is a layered monolith with extra ceremony.

## Options considered

**A. No shared kernel.** Each context defines everything it needs; translation at every boundary.
*Pros:* maximum independence; textbook microservices purity.
*Cons:* eleven `Symbol` types with eleven validation rules; conversion code at every boundary, each an opportunity for a rounding or timezone bug; the financial primitives in particular must not diverge.

**B. A generous shared kernel.** Anything used by more than one context goes in.
*Pros:* no duplication; convenient.
*Cons:* becomes the domain model; every change breaks everything; contexts lose independent deployability in practice even if they retain it on paper.

**C. A deliberately minimal shared kernel with a written inclusion test and governance.**
*Pros:* the genuinely universal vocabulary is shared; everything with behaviour tied to one context stays there; the boundary is defensible because the test is written down.
*Cons:* requires discipline at exactly the moment when discipline is least convenient; some duplication remains by design.

## Decision

**Option C.** **The inclusion rule: if it can live in one context, it does not go in the shared kernel.**

### What is in

| Group | Types | Justification |
|---|---|---|
| 1 | `Symbol`, `Timeframe`, `Timestamp`, `AsOf` | Universal vocabulary. Cannot be duplicated without conversion bugs at every boundary. `AsOf` in particular is the type system's defence against look-ahead (ADR-0034 L1) |
| 2 | `Money`, `Quantity`, `Price`, `Bps` | Financial primitives. **`Decimal`, never `float`.** Duplication here means rounding divergence between contexts |
| 3 | `EventEnvelope` and the correlation/causation types | Every service publishes. This is the wire contract (ADR-0037) |
| 4 | `Clock` | Injected everywhere (ADR-0035) |
| 5 | `Result[T, E]` and the error taxonomy | Consistent failure handling across boundaries |
| 6 | `Staleness`, `Confidence`, `Probability` | Semantic types whose confusion is the platform's most likely category error. `Confidence` and `Probability` are **distinct types that cannot be assigned to each other** |
| 7 | `TenantId`, `AccountId` | Multi-account partitioning, and the reserved tenancy seam (ADR-0009) |

### What is deliberately out

| Excluded | Why |
|---|---|
| `Position` | BC7 owns it. Other contexts get the read model |
| `Order` | BC8 owns it |
| `RegimeState` | BC4 owns it. BC5 sees it only as an `EvidenceNode` |
| `TradeProposal` | BC5 owns it. BC6 receives it as a published-language DTO and translates |
| Anything with behaviour tied to one context | By definition |

### Governance

1. **One package, its own semantic version, its own CHANGELOG.**
2. **Any change requires a written ADR.** In a solo setting, sign-off "representing every consuming context" means a written record, not a meeting.
3. **Additive changes are minor. Anything else is major**, and a major bump is a coordinated release across eleven contexts.
4. **Value objects are immutable and self-validating.** `Probability(1.7)` raises at construction, so no downstream check is needed.
5. **No I/O, no framework imports, no dependencies beyond the standard library and `decimal`.** A shared kernel that imports FastAPI or a database driver has stopped being a kernel.

## Rationale

Group 2 alone justifies having a kernel at all. Money arithmetic that diverges between two contexts produces position sizes that are wrong by a rounding step, silently, and the error compounds. There is no acceptable version of that being defined twice.

Group 6 is the least obvious and one of the most valuable. `Confidence` and `Probability` are both floats in [0,1] and mean entirely different things: one is a self-report from a desk, the other is a calibrated frequency. Making them distinct types that cannot be assigned to each other converts the platform's most likely category error into a compile-time failure. The same reasoning applies to `Staleness`: there is no "unknown freshness" state, because the type cannot be constructed without one.

Rule 5 is what keeps the boundary enforceable. A kernel with no dependencies can be imported by anything, including tests, simulations and notebooks, without dragging in a runtime. The moment it imports a framework, the contexts inherit that framework's version constraints, and independent deployability is gone.

## Consequences

**Positive**
- One definition of money arithmetic, one of time, one of the wire envelope.
- The two most likely category errors (confidence/probability, float/decimal) are compile-time failures.
- Contexts remain independently deployable in practice, not just on paper.

**Negative**
- Real discipline is required at exactly the wrong moment. Every "just put it in common" is a small, locally correct decision that is collectively fatal.
- Some duplication by design: two contexts may each define their own `Regime` view, and that is correct.
- A major version bump is a coordinated eleven-context release, which is genuinely painful. That pain is the mechanism that keeps the kernel small.

**Neutral**
- The kernel is small enough to review in full at each change.

## Tripwire

1. **The kernel exceeds the seven groups.** Every addition needs an ADR, and three additions in a year means the inclusion test is not being applied.
2. **A major version bump happens more than once a year.** The kernel is supposed to be stable. Frequent breaking changes mean something context-specific has crept in.
3. **Any type in the kernel gains a method that only one context calls.** That type belongs in that context.

## Related

- ADR-0010 (eleven bounded contexts) is what this supports
- ADR-0035 (`Clock`), ADR-0037 (`EventEnvelope`), ADR-0009 (`TenantId`), ADR-0034 (`AsOf`)
- ADR-0001 (Python) mandates the strict typing this depends on
- `../review/R03_Domain_Model_DDD.md` §10, §11
- `../review/R02_C4_Expansion.md` §5
