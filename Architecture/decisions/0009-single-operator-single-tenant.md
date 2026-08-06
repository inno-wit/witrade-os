# ADR-0009: Single-operator, single-tenant architecture

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** foundational, scope, security, data-model

---

## Context

This is the most consequential deferred decision in the ADD, and the ADD does not acknowledge that it is a decision at all.

The evidence points both ways:

| Points to single-tenant | Points to multi-tenant |
|---|---|
| Every page assumes one operator: one account, one kill switch, one set of limits, one dashboard | The repository root is `SAAS/` |
| Page 14's deployment model has one operator performing typed confirmations | TradeHub is an existing product with users |
| Page 10's dual control is described as "a delay plus a written justification" rather than a second person | R00's roadmap lists "the platform is productised for users other than the operator" as a future fork |
| Page 13 sizes infrastructure for a single host | Pages 06 and 11 propose reusing TradeHub components |

Nothing in the ADD resolves this. Implementation will therefore resolve it by accident, in the first migration that creates a table without a tenant column.

**Why it cannot be deferred:** multi-tenancy is not a feature that gets added. It is a property of every table (a partition key), every NATS subject (a routing token), every authorisation check (a scope), every cache key, every metric label, and every kill switch scope. Retrofitting it means touching all of them at once, in a system that by then holds real capital and real history. It is the single most expensive possible late change in this design.

## Options considered

**A. Single-tenant, and say so.** One operator, one set of accounts, no tenant concept anywhere.
*Pros:* simplest possible data model, authorisation, and operations; no partition key discipline to maintain; every query is simpler; fastest to build.
*Cons:* productisation later is a rewrite of the persistence and authorisation layers, not an increment.

**B. Full multi-tenant from day one.** Tenant isolation in every table, subject, cache key, and authorisation check, with per-tenant limits, kill switches, and cost budgets.
*Pros:* productisation is a business decision rather than an engineering programme.
*Cons:* it roughly doubles the surface area of the authorisation and data-access layers before there is a second user; every query gains a predicate; every test gains a fixture; per-tenant capital segregation is a regulated activity in most jurisdictions, which is a compliance programme, not a schema change. Building all of this for one user is the classic way a solo project fails to ship.

**C. Single-tenant, with a reserved seam.** Operate as single-tenant. Carry `TenantId` and `AccountId` in the shared kernel from commit one, stamp `tenant` in the event envelope (constant `"default"`), and include a tenant column in every table that would need one, defaulted and unindexed. Do not build tenant-aware authorisation, per-tenant limits, per-tenant kill switches, or tenant-scoped operations.
*Pros:* the expensive-to-retrofit part (the identifier threaded through every record and message) is present from the start at near-zero cost; the expensive-to-build part (isolation, authorisation, per-tenant controls, compliance) is deferred until it is paid for by a real second user.
*Cons:* a column and a field that do nothing for an unknown period, which invites deletion by a future cleanup; it is not real multi-tenancy and must not be mistaken for it; it does not remove the compliance work, it only removes the schema migration from it.

## Decision

**Recommended: Option C.** WITrade is a **single-tenant, single-operator platform**. `TenantId` exists in the shared kernel and in the event envelope from commit one as a reserved seam, permanently set to `"default"`. No tenant-aware authorisation, isolation, or per-tenant control is built.

Specifically:
1. `TenantId` and `AccountId` are shared-kernel value objects (R03 §10), present from the first commit.
2. The event envelope's `tenant` field is mandatory and constant (R01 §4).
3. Tables whose rows are logically tenant-scoped carry a `tenant_id` column, `NOT NULL DEFAULT 'default'`, **not** indexed and **not** in any query predicate.
4. Authorisation, kill switch scopes, risk limits, cost budgets and dashboards are **platform-wide**, not tenant-scoped.
5. Any pull request that adds a tenant-aware code path is rejected until this ADR is superseded.
6. Multi-tenancy, if it ever arrives, is a **superseding ADR and a project**, not an increment. TradeHub-facing productisation does not silently reopen this.

### Operator ruling, 2026-08-03

The open business question is answered: **multi-tenancy comes after the platform has proven an edge in the market, not before.** Option C is Accepted.

This is an event-gated horizon rather than a calendar one, which is stronger than the two-year framing the question was originally posed in. It converts the tripwire from "has enough time passed" into "has the thing that would justify the spend actually happened," and that condition is observable rather than guessed. Two consequences follow:

- **No date-based review of this ADR.** A quarterly tripwire pass checks the conditions below, not the calendar.
- **Proven edge is defined here, not later**, because a term left undefined until it is convenient becomes whatever the person wanting to productise says it means. Edge is proven when the live track record clears the same bar the platform applies to its own strategy proposals: a Deflated Sharpe Ratio above 0.95 confidence on **live** (not backtested) returns over a minimum of 200 decision cycles, with PBO below 0.5, at capital the operator would be unhappy to lose. Until that holds, this ADR is not in play regardless of external interest.

## Rationale

The asymmetry is what drives the recommendation. The cost of Option C over Option A is roughly one afternoon: two value objects, one envelope field, one column convention. The cost of Option A over Option C, discovered eighteen months in, is a migration of every table and a re-audit of every query in a system holding live positions.

The cost of Option B over Option C is months of authorisation, isolation and compliance work that no user has asked for, in a project whose primary risk is not shipping.

Option C buys the cheap half of the insurance and declines the expensive half. That is the right trade when the probability of productisation is real but unquantified.

The rule in point 5 is the load-bearing part. A reserved seam that people start coding against becomes half-built multi-tenancy, which is worse than either endpoint: it looks isolated and is not.

## Consequences

**Positive**
- Simplest possible authorisation model, which matters because R15 identifies operator error rather than external attack as the dominant risk.
- Every query stays simple, and no query carries a tenant predicate that could be forgotten.
- If productisation happens, the identifier is already in every historical record and every archived event, so history is not orphaned.

**Negative**
- A column and an envelope field that do nothing, indefinitely. They must be documented as a deliberate seam or a future cleanup will remove them.
- Real multi-tenancy remains a project. This ADR reduces its cost, it does not eliminate it.
- The reversal is expensive and the operator ruling makes it *later*, which makes it more expensive in absolute terms: by the time edge is proven there is more history, more capital, and more code to migrate. This is accepted knowingly. The alternative is paying that cost now against a platform that may never earn the right to have users.
- Proving edge and building multi-tenancy will want to happen at the same moment, because the first is what creates demand for the second. Expect the pressure to arrive when attention is least available.

**Neutral**
- `AccountId` is genuinely used from day one (multi-account under one operator is in scope). Only `TenantId` is dormant.

## Tripwire

The operator ruling makes this a two-part tripwire: a **gate** that must open before multi-tenancy is even discussable, and **conditions** that force the discussion once it is open.

**The gate (must be true first):** live-traded edge is proven, per the definition in the Decision section. DSR clearing 0.95 confidence on live returns over at least 200 decision cycles, PBO below 0.5, at meaningful capital. Before the gate opens, every condition below is answered "no, and here is this ADR."

**Conditions, once the gate is open.** Revisit when **any** becomes true:

1. A second human being needs their own capital, their own limits, or their own kill switch on this platform.
2. TradeHub or any other product is proposed to run on WITrade's decision path rather than alongside it.
3. Any requirement appears that would be satisfied by a tenant-scoped authorisation check.
4. A regulator, broker, or counterparty asks how client funds are segregated.

Conditions 1 and 2 are the likely ones. Condition 4 is the one that turns this from an engineering decision into a compliance programme, and it should be understood in advance that reaching it means the reversal is not a sprint.

**The gate does not apply to condition 4.** A regulator does not wait for a Sharpe ratio. If condition 4 fires before edge is proven, this ADR is revisited immediately regardless of the gate.

**What the gate does not license.** An open gate permits the *conversation*, not a drift into tenant-aware code. Decision point 5 (any pull request adding a tenant-aware code path is rejected) holds until a superseding ADR exists, gate or no gate.

## Related

- ADR-0008 (Docker Compose over Kubernetes) shares the multi-tenancy tripwire
- ADR-0014 (shared kernel governance) governs `TenantId`'s presence there
- `../review/R03_Domain_Model_DDD.md` §10
- `../review/R00_Executive_Review.md` (deferred forks)
- `../review/R18_Technical_Debt.md` A5
- Source: `../00_Master_Architecture.md` (Open Questions)
