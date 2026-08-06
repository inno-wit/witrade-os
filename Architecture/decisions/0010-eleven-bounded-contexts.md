# ADR-0010: Eleven bounded contexts, and the criteria used to draw them

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** ddd, boundaries, foundational

---

## Context

The ADD decomposes the platform by **technical layer**: Data Platform, Quant Research Platform, Decision Intelligence, Risk, Execution, Learning. That is a reasonable first cut, it maps cleanly onto the data flow, and it is why the document reads well.

Layered decomposition has two known failure modes at this scale, and both are already visible:

1. **Concepts smear across layers.** "Position" appears on page 03 (cross-asset features), page 08 (Risk Desk reads portfolio state), page 09 (portfolio impact), page 10 (exposure, correlation), page 11 (fills) and page 12 (trade history). Six pages touch it. **No page owns it.** When six components each hold their own idea of what a position is, they will disagree, and the disagreement will surface as a risk-limit breach.
2. **Dependency direction follows the data flow rather than the domain.** This is how the 08 → 10 → 09 → 08 cycle (blocking defect B3) appeared. A layered model has no vocabulary for "the Committee needs to *know about* portfolio state without *depending on* the Risk Engine." A domain model does: it is a read model published by a different context.

The decision is what replaces or overlays the layering, and by what criteria the new boundaries are drawn. Recording the **criteria** matters as much as the list, because the list will need extending and an unprincipled extension is how a domain model degenerates back into layers.

## Options considered

**A. Keep the layered decomposition.**
*Pros:* already written; matches the data flow; easy to explain.
*Cons:* does not give "position" an owner, and has no mechanism to break the cycle. Both defects are structural, not incidental.

**B. One service per ADD page (17 services).**
*Pros:* mechanical mapping from the existing document.
*Cons:* pages are chapters, not boundaries. Some pages are one cohesive thing (page 10), some are three (page 11 mixes execution, portfolio and reconciliation), and three necessary contexts have no page at all.

**C. A modular monolith with no explicit contexts.**
*Pros:* simplest deployment; no distributed-systems problems.
*Cons:* the boundary questions do not go away, they just stop being visible. Without named contexts, module dependencies drift and the same smearing happens inside one process, where it is harder to see.

**D. Eleven bounded contexts overlaid on the layering, contexts owning the data.**
*Pros:* gives every concept exactly one owner; provides the vocabulary (published read model, ACL, published language) that breaks the cycle; each context maps to a deployable unit and a database schema; the layering survives as a narrative for the data flow.
*Cons:* eleven is more boundaries than the ADD currently has; a boundary drawn wrongly is expensive to move later.

## Decision

**Option D.** Eleven bounded contexts. **Each owns its data exclusively. No context reads another context's tables.** Cross-context communication is by published event, published read model, or an explicit anti-corruption layer.

| # | Bounded Context | Core question it answers | Type |
|---|---|---|---|
| BC1 | **Market Data** | What happened in the market, and can we trust the record of it? | Supporting |
| BC2 | **Reference Data** | What is this instrument, and is it tradable right now? | Supporting (but blocking) |
| BC3 | **Feature Engineering** | What derived quantities describe the market at time T, computable with only information available at T? | Supporting |
| BC4 | **Market Intelligence** | What state is the market in? | **Core** |
| BC5 | **Deliberation** | Given the evidence, what should we do and why? | **Core** |
| BC6 | **Risk Authorisation** | May this action be taken with this capital right now? | **Core** |
| BC7 | **Portfolio** | What do we own, what is it worth, what did it cost? | **Core** |
| BC8 | **Order Execution** | How do we get from an authorised intent to a confirmed broker state? | **Core** |
| BC9 | **Learning** | Where were we wrong, and what specific change would have helped? | **Core** |
| BC10 | **Platform Operations** | Is the system healthy, and what mode is it in? | Generic |
| BC11 | **Identity & Governance** | Who is allowed to do what, and what did they do? | Generic |

**BC2, BC7 and BC11 have no page in the current ADD.** Two of them (Reference Data, Portfolio) are blocking dependencies for position sizing, which page 10 specifies in detail without them.

### The criteria used to draw these boundaries

A boundary is justified when **three or more** of the following hold. Any proposal to add, split or merge a context is argued against this list.

1. **The ubiquitous language changes.** The same word means something different on each side. "Position" means an exposure to be limited in BC6 and a lot-level cost basis in BC7. That is a boundary.
2. **The consistency requirement differs.** BC7 needs transactional consistency over the book. BC4 is content with eventual consistency over an estimate. Different consistency requirements do not belong in one aggregate.
3. **The rate of change differs.** BC4's models change weekly with research. BC8's broker protocol changes yearly. Coupling them means the stable thing is redeployed at the volatile thing's cadence.
4. **The failure domain should be independent.** A degraded regime model must not be able to prevent an exit (ADR-0019). That requires BC4 and BC6 to fail separately.
5. **A different kind of correctness applies.** BC5 is probabilistic and its output is judged by calibration. BC6 is deterministic and its output is judged by whether the rule fired. Mixing them makes the deterministic part untestable.
6. **The data has exactly one legitimate owner.** If two components write it, one of them is wrong.

### Binding rules

1. **Exclusive data ownership.** One context, one set of tables, one schema (ADR-0007). Enforced by per-schema database roles, not convention.
2. **The subject namespace derives from the context, not from a page number or a layer name** (ADR-0037).
3. **Cross-context reads are by published event, published read model, or an ACL.** Never a direct table read, never a shared model object.
4. **Reference other aggregates by identity only.** `Trade` holds a `decision_id`, not a `DeliberationCycle` object.
5. **The context map (R03 §2) is acyclic.** A proposed change that introduces a cycle is rejected, and the fix is a read model (ADR-0012).

### Relationship patterns

| Upstream → Downstream | Pattern |
|---|---|
| Reference Data → everyone | **Conformist.** Instrument truth is not negotiable |
| Market Data → Feature Engineering | Customer/Supplier |
| Feature Engineering → Market Intelligence | Published Language (`FeatureVector`) |
| Market Intelligence → Deliberation | Published Language (`Evidence`) |
| Portfolio → Deliberation | Open Host Service, **async read model** |
| Portfolio → Risk Authorisation | Open Host Service, **sync query**, 30ms, fail closed |
| Risk Authorisation → Order Execution | Customer/Supplier with a signed contract (the token) |
| External broker → Order Execution | **Anti-Corruption Layer** (`BrokerAdapter`) |
| News provider → Market Data | **Anti-Corruption Layer** (text sanitiser, ADR-0032) |
| Anthropic → Deliberation | **Anti-Corruption Layer** (LLM Gateway) |
| Learning → Market Intelligence / Deliberation | Customer/Supplier, **gated** by PBO/DSR. BC9 has no write authority |

## Rationale

The two defects in the layered model are both symptoms of the same root cause: **data without an owner**. Criterion 6 addresses it directly, and BC7 exists entirely because of it.

Contexts are chosen over services as the primary unit because a context is a **modelling** boundary that can be enforced in a monolith and in a distributed system alike. Contexts map to deployable services here, but if a future consolidation merges two services into one process, the context boundary survives as a module boundary and the ownership rules still hold.

Eleven is more than the ADD's six because three necessary contexts were entirely missing and two pages were carrying two contexts each. It is not decomposition for its own sake: each of the eleven answers a distinct question that another context cannot answer on its behalf.

The written criteria matter more than the list. In eighteen months there will be pressure to add a twelfth context, or to let BC6 read BC7's tables "just for this one query." The criteria are what turn that into an argument with a standard rather than a matter of taste.

## Consequences

**Positive**
- Every concept has exactly one owner. The six-way "position" smear is resolved.
- The dependency graph is acyclic, so contexts are independently deployable and testable.
- The subject namespace is stable across refactors because it derives from the domain, not from the file layout.
- Three missing contexts are surfaced before implementation rather than discovered during it.
- Each context is small enough to hold in one person's head.

**Negative**
- Eleven boundaries to respect, which is real discipline in a solo codebase where crossing one is always locally easier.
- Some data is necessarily duplicated across contexts (a read model is a copy). Staleness becomes an explicit, monitored property rather than an ignored one, which is a net gain but is more machinery.
- A boundary drawn wrongly is expensive to move. The criteria above are the defence.

**Neutral**
- The ADD's layered narrative is preserved. R03 §12 maps every page to its context, so both models remain navigable.

## Tripwire

1. **A context that never changes independently of another** over a year should be merged. Track deployment coupling.
2. **A context that repeatedly needs another's internals** signals a boundary in the wrong place. Track the frequency of proposals to add a cross-context query API; more than two for the same pair is the signal.
3. **A new context proposal that satisfies fewer than three criteria** is rejected as a module, not a context.

## Related

- ADR-0011, ADR-0012 (the boundary corrections that motivated this)
- ADR-0014 (shared kernel: what is allowed to be common)
- ADR-0015 (Reference Data as a context, not configuration)
- ADR-0007 (one schema per context)
- `../review/R03_Domain_Model_DDD.md` §2, §12
- `../review/R02_C4_Expansion.md`
- Blocking defect B3
- Source: `../00_Master_Architecture.md`
