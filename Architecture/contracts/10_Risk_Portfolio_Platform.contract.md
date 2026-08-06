# 10 — Risk & Portfolio Management, contract completion

**Delta against:** `../10_Risk_Portfolio_Platform.md` (unmodified)
**Adds:** Owns, Invariants, Interfaces, Degraded Mode, SLO, Security Boundary
**Containers:** C21 Risk Engine + C22 Account & Position Ledger · **Contexts:** Risk Authorisation (BC6), Portfolio (BC7) · **Criticality:** Tier 0 · **Group:** Capital
**Highest-value field for this page (R05 §11):** **Security Boundary.** Who may call `decide`, and who holds the signing key

---

## What page 10 gets right, and must not be lost

Three decisions on this page are better than most institutional risk designs and every correction preserves them:

- **The kill switch is a synchronous in-process gate, checked as the literal last step before an order leaves, in the same function call.** Not a pub/sub subscriber. The page argues the propagation window explicitly. This is correct and is a permanent fixed point (ADR-0017, no tripwire).
- **The kill switch does not auto-liquidate.** Auto-closing into a bad market can be the worse outcome, so closing positions stays a distinct explicit operator action (ADR-0023, no tripwire).
- **Broker truth over internal ledger**, reconciled before every approval.
- **Fractional Kelly as a standing platform default, not a per-trade tunable the Committee can override.**

The corrections are: split the book out of the risk engine, make preview and decide one rule chain with two modes, make the kill switch fail closed, and make exits structurally exempt from entry-blocking rules.

## The split this contract assumes

Page 10 owns both the veto and the book. They separate:

| | C21 Risk Engine | C22 Account & Position Ledger |
|---|---|---|
| Answers | "May this action be taken with this capital right now" | "What do we own, what is it worth, what did it cost" |
| Writes | Assessments, authorisations, rejections, limits, kill-switch state | The event-sourced book |
| Never writes | **The book. A risk approval never mutates a position** | Authorisations |
| Store | Postgres + Redis (cache only) | Postgres event store + projection |

Page 10 places "live portfolio state" in Redis with Postgres as a "durable ledger" and never says which wins. Six components read some form of position state and none owns it. Redis is not durable, so a restart loses the book unless it is rebuildable, and nothing in pages 00-16 describes a rebuild. C22 makes the book event-sourced, rebuildable, and owned.

## Owns (exclusive write access)

| Asset | Owner |
|---|---|
| `limit_sets` (versioned, dual-controlled) | C21 |
| `risk_assessments`, `authorisations`, `rejections` | C21 |
| `killswitch_state` (three tiers) | C21 |
| `ledger_events` (append-only), `positions_projection`, `lots`, `trades` | C22 |

## Invariants

### Authorisation (C21)

1. **Exactly one component in the platform issues authorisations. This one.**
2. No `AuthorisedOrder` exists without a complete `RiskAssessment` recording every rule's verdict and the `limit_set_version` used.
3. `PREVIEW` never mutates state and never issues a token. Rule evaluation is byte-identical to `DECIDE`, asserted in CI. One chain, two modes: that is how B4 closes without duplicating logic.
4. **The kill-switch check is the final operation before token issuance, with no awaitable between them.** Page 10's synchronous gate, stated as a code-level constraint that a review can check.
5. Every authorisation is single-use and TTL-bounded, and `valid_until` is shorter than the triggering bar interval.
6. A rejection is persisted as durably as an approval. Page 10 is right that a rejection is as important an audit artefact as an approval, and this is the invariant that makes it one.
7. The token signing key exists only in this service.
8. **Exits are never blocked by entry-blocking rules.** An `EXIT` intent bypasses the drawdown guard, the news blackout, the exposure cap, and the kill switch. Trapping the platform in a position it cannot exit is worse than any risk those rules address (ADR-0019, no tripwire).
9. **Kill switch fails closed.** Any tier unreachable means HALTED. Page 10 puts the switch in Redis with a synchronous read and does not say what happens when Redis is unavailable, which means it fails **open**: the check errors, the error is handled, and the order proceeds. That is B2, and it is the single most dangerous gap in the source design.
10. Sizing is `Decimal` throughout with explicit clamps, and a clamp raises an alert. A silently clamped size is a position sized by a bug.

### The book (C22)

11. The ledger is append-only. A correction is a compensating event, never an update.
12. Sum of lot quantities equals position quantity, per symbol per account, at every point in the stream.
13. Double-entry: every balance change has a matching counterparty entry. The books balance or the service halts.
14. The projection is derivable from the event stream alone, and a rebuild is byte-identical. Asserted in CI.
15. **Only fills, broker-reported adjustments, and reconciliation corrections mutate the book. A risk approval never does.**
16. `PortfolioSnapshot` always carries `as_of` and `sequence`, so a consumer can detect that it read a stale snapshot.

Invariant 9 deserves the emphasis. The kill switch is the platform's last line of defence, and in the source design its failure mode is to stop defending without saying so. Three tiers, each independently checkable, any one unreachable meaning HALTED, is what turns page 10's correct synchronous design into a correct synchronous design that also survives its own dependency failing (ADR-0018).

## Interfaces

### C21 Risk Engine

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Query | `preview(proposal) -> RiskAssessment` | Yes | 50ms | service (C19) |
| Command | `decide(proposal) -> AuthorisedOrder \| Rejection` | Yes | 100ms | **service (C19) only** |
| Command | `authorise_exit(position_id, reason) -> AuthorisedOrder` | Yes | 100ms | **service (C23) only** |
| Command | `trip_killswitch(scope, reason, actor)` | Yes | 10ms | **any, deliberately** |
| Command | `clear_killswitch(scope, actor, confirmation)` | Yes | 1s | operator, dual-control if auto-tripped |
| Command | `publish_limit_set(limits, approver_a, approver_b)` | Yes | 1s | dual-control, audited |
| Query | `get_limits(as_of) -> LimitSet` | Yes | 10ms | service, auditor |
| Adapter | `RiskRule` protocol (L4.3), ordered chain | — | — | — |

`trip_killswitch` is callable by anything, deliberately and asymmetrically. Stopping is always allowed; starting requires authority. A halt path that requires a permission check is a halt path that can fail for the wrong reason at the worst moment.

The rule chain is an ordered sequence of individually versioned units (`PlatformMode`, `NewsBlackout`, `InstrumentTradable`, `PortfolioRisk`, `ExposureLimit`, `Correlation`, `DrawdownGuard`, `Liquidity`, `ModelRisk`). Chain order is itself a versioned artefact: reordering is a limit-set version bump, because rule order changes outcomes and an accidental reorder is invisible in a diff of behaviour.

### C22 Position Ledger

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Query | `get_snapshot(account_id) -> PortfolioSnapshot` | Yes | 30ms | service (C21) |
| Query | `get_snapshot_at(account_id, as_of) -> PortfolioSnapshot` | Yes | 2s | service, researcher |
| Command | `apply_fill(fill) -> LedgerResult` | Yes | 50ms | **service (C24) only** |
| Command | `apply_correction(correction, reason, actor)` | Yes | 100ms | operator, **dual-control**, audited |

## Degraded Mode

| Condition | Behaviour |
|---|---|
| Portfolio snapshot older than 5s | **`decide` rejects.** Approving against unknown exposure is page 10's own top failure mode, and staleness is now detectable because the snapshot carries `as_of` |
| Ledger unreachable | All `decide` calls reject. `preview` returns `unavailable`. **`authorise_exit` still succeeds if the position is known**, because trapping the platform is worse |
| Any kill-switch tier unreachable | **HALTED.** Fail closed (invariant 9) |
| Volatility Engine unavailable | Reject new entries. **Never size on a default.** Exits unaffected |
| Instrument Master unavailable | Reject new entries: no contract spec means no defensible size or lot rounding |
| Limit set unresolvable for `as_of` | **Hard error, HALT.** Never fall back to the current limit set, which would authorise against limits that were not in force |
| Postgres unavailable | Reject everything, HALT. A decision that cannot be recorded cannot be made (invariant 6) |
| C22 projection diverges from its event stream | C22 halts and raises P0. **A book that disagrees with itself is not a book** |
| Reconciliation break detected | Auto-trip the kill switch before any human is involved |

Every row rejects or halts. That uniformity is the point: this is the component where fail-closed is not a preference but the definition of the job (ADR-0025). The one asymmetry, exits remaining authorisable, is deliberate, argued, and must be tested explicitly rather than assumed to work.

## SLO

| Dimension | Target |
|---|---|
| C21 availability | 99.99% |
| C22 availability | 99.99% (C21 depends on it synchronously) |
| `decide` | p50 < 20ms, p95 < 60ms, p99 < 100ms. Page 10's budget, now with percentiles |
| `get_snapshot` | p50 < 5ms, p95 < 15ms, p99 < 30ms |
| `trip_killswitch` | p99 < 10ms |
| **Correctness** | **Zero authorisations issued without a complete assessment.** This is the most important number on the platform |
| Correctness | Zero authorisations issued while any kill-switch tier reports HALTED |
| Correctness | Zero exits blocked by an entry-blocking rule. **Tested explicitly: kill switch active plus exit request must succeed** |
| Book integrity | Rebuild determinism 100%. Zero unreconciled breaks older than 5 minutes |
| Tripwire metrics | `preview_decide_divergence_rate` < 10%; spurious halts ≤ 2/month; `UNPROTECTED` duration: any > 60s is an incident |

The first correctness line is a correctness SLO, not a performance one, and it is the number this entire platform exists to keep at zero.

## Security Boundary

This is the field R05 flags as highest-value for this page, and page 10 states none of it.

| | |
|---|---|
| **Zone** | VAULT, the most restricted segment. Isolated network, same failure domain as C22 and C23 |
| **`decide` callable by** | **The Decision Saga service identity (C19) and nothing else.** Enforced by mTLS service identity, not by network position |
| **`authorise_exit` callable by** | **The OMS service identity (C23) and nothing else** |
| **`trip_killswitch` callable by** | **Anything, including an unauthenticated internal call.** Deliberate |
| **`clear_killswitch`** | Operator only. **Dual control when the trip was automatic**, because the automatic trip is the one where a single tired human is most likely to clear a condition they have not understood |
| **`publish_limit_set`** | Two approvers, audited, plus a mandatory dry-run against the last 30 days of proposals showing what would have changed |
| **`apply_correction` (C22)** | Two approvers, audited. Correcting the book by hand is the highest-consequence non-trading action available |
| **Secrets held** | **The approval-token signing key, and it exists nowhere else in the platform.** Postgres and Redis credentials |
| **Never holds** | **Broker credentials.** C21 cannot send an order even if fully compromised; it can only sign a token that C24 will honour |
| **Trusts** | The Ledger snapshot with its `as_of`. Instrument Master specs. **Trusts no committee output and no proposal confidence:** every rule runs regardless |

The signing key is what converts "no trade reaches Execution without passing Risk" from a wiring convention into a cryptographic property. Execution rejects any command without a valid, unexpired, single-use token. A compromised or buggy service elsewhere in the platform cannot manufacture one, and a rewired NATS subject cannot bypass one.

The credential separation is the other half. C21 decides and cannot act; C24 acts and cannot decide. Neither alone can put on a position.

---

## Related

- Source page, unmodified: `../10_Risk_Portfolio_Platform.md`
- `09_Decision_Intelligence_Layer.contract.md` — the proposer upstream
- `11_Execution_Platform.contract.md` — the token validator downstream
- `05_Volatility_Engine.contract.md` — the sizing input and its degradation rules
- `../review/R11_Risk_Architecture.md` — 8-category taxonomy, rule chain, VaR/CVaR, stress, model risk
- `../decisions/0011-risk-engine-sole-authorisation-authority.md` — invariant 1, closes B4
- `../decisions/0018-kill-switch-three-tier-fail-closed-interlock.md` — invariant 9, closes B2
- `../decisions/0017-kill-switch-is-synchronous-not-pubsub.md` — invariant 4, fixed point
- `../decisions/0019-exits-never-blocked-by-entry-rules.md` — invariant 8, fixed point
- `../decisions/0023-kill-switch-does-not-auto-liquidate.md` — preserved from page 10, fixed point
- `../decisions/0024-risk-limits-are-versioned-dual-controlled-artefacts.md` — `publish_limit_set`
