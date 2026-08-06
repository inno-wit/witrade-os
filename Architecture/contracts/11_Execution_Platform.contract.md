# 11 — Execution Platform, contract completion

**Delta against:** `../11_Execution_Platform.md` (unmodified)
**Adds:** Owns, Invariants, Interfaces, Degraded Mode, SLO, Security Boundary
**Containers:** C24 Execution Service + C23 OMS + C25 Reconciliation · **Context:** Order Execution (BC8) · **Criticality:** Tier 0 · **Group:** Bridge (C24) and Capital (C23, C25)
**Highest-value field for this page (R05 §11):** **Degraded Mode.** Specifically, behaviour with an `UNKNOWN` order outstanding
**Amended:** 2026-08-06, invariant 19 added by [ADR-0044](../decisions/0044-kill-switch-recheck-at-broker-send.md) — closes the mint-to-send kill-switch hand-off window found by an independent pre-implementation review. Freeze rule 3 applies: this is a dated addition, invariants 1-18 unchanged.

---

## What page 11 gets right, and must not be lost

- **Broker-agnostic adapter from day one** despite MT5 being the only implementation. Most designs promise this later and never get it.
- **Idempotent client-generated order IDs**, with a status check by that ID before any retry.
- **Slippage beyond tolerance auto-flags for review, never auto-retries.** The page argues why: an auto-retry into a fast market compounds the problem. Correct.
- **A pattern of bad slippage trips the kill switch, a single incident does not.**
- **Trade confirmation reconciled against broker truth**, never trusted from the send response.
- **Partial fills as a first-class state**, resolved deterministically by time-in-force rather than ad hoc.

The corrections are: make the idempotency key deterministic rather than merely client-generated, add the leader lease before the standby exists, make `UNKNOWN` a real state, and give the platform an owner for everything after the fill.

## Owns (exclusive write access)

| Asset | Owner |
|---|---|
| `orders`, `order_state_transitions` | C24 |
| `fills`, `fill_analyses` | C24 |
| `idempotency_keys` (client order ID dedup) | C24 |
| `leader_lease` | C24 |
| `managed_positions`, `management_plans`, `management_actions` | **C23 OMS** |
| `reconciliation_runs`, `breaks`, `break_resolutions` | **C25** |

C23 is the largest single functional gap in the source design. Page 11 ends at the journal entry. Nothing in pages 00-16 owns moving a stop to breakeven, trailing, partial take-profit, time-based exits, structure-invalidation exits, a position modified by hand at the MT5 terminal, a position closed by the broker on margin, or a position that exists at the broker and not in the platform.

For most systematic and discretionary strategies, exit management contributes as much to the outcome as entry selection. A platform with a six-desk committee for entries and nothing for exits is optimising the wrong half.

## Invariants

### Execution (C24)

1. **No order is sent without a valid, unexpired, single-use approval token from C21.** Signature verified, TTL checked, consumed by compare-and-set.
2. `client_order_id = "wt-" + base32(sha256(decision_id + leg_index))[:20]`. **Deterministic, not generated.** A redelivered command, a replayed stream, and a restarted process all regenerate the identical ID, so the broker rejects the duplicate. This is what makes page 11's idempotency claim hold under redelivery, which a randomly generated ID does not.
3. **Exactly one process holds the leader lease and may send orders.** No lease, no sending.
4. `UNKNOWN` is a first-class order state. A send that times out returns `UNKNOWN` and **never raises**. The caller decides. Swallowing a timeout is how duplicate orders happen.
5. **An order in `UNKNOWN` is never blind-retried.** It is reconciled against broker truth first, always.
6. Broker symbol translation happens inside the adapter. The platform never sees a broker-specific symbol.
7. `get_order_status` is the authority. The return value of `place_order` is a hint, never a confirmation.
8. A command whose `valid_until` has passed is rejected and emits `evt.decision.expired.v1`. Never executed late.
9. A message with `replay=true` is rejected outright when `env=prod`. A hard interlock, symmetric to the kill switch.
10. **Every entry carries a broker-side hard stop**, placed atomically with the entry where the broker supports it and immediately after where it does not. A position with no broker-side stop is `UNPROTECTED` and any duration over 60 seconds is an incident (ADR-0022, no tripwire).

### Lifecycle (C23)

11. Every open position has exactly one active `ManagementPlan`, or is flagged `UNMANAGED` and alerted.
12. **A management action never increases risk.** Stops move only toward the entry, never away. Size only decreases. Anything increasing exposure is a new entry and goes through the full proposal and authorisation path.
13. Exits are authorised by C21 with a distinct `EXIT` intent that bypasses entry-blocking rules.
14. A position adopted from outside the platform enters `ADOPTED_UNMANAGED` and requires explicit operator action. **It is never silently managed with default rules**, because a position someone opened by hand was opened for a reason the platform does not know.

### Reconciliation (C25)

15. Runs at least every 60 seconds during market hours, and always after a fill, a restart, and a broker reconnect.
16. **A severe break auto-trips the kill switch before any human is involved.**
17. **No break is auto-corrected.** Corrections are dual-controlled operator actions, because an automatic correction against a temporarily wrong broker response would destroy the book.
18. Broker truth wins on positions and fills. The Ledger wins on decision attribution. Never the reverse.

### Execution (C24) — added 2026-08-06

19. **The three-tier kill switch is re-evaluated immediately before `BrokerAdapter.send`, for `ENTRY`-intent orders only, with no awaitable operation between the check and the send.** Same combination rule as ADR-0018: `HALTED if ANY tier says HALTED OR ANY tier is unreadable`. On halt or unreadable tier: drop the token unconsumed (no compare-and-set), never send, emit `evt.execution.aborted.v1` with `reason: kill_switch_recheck`. `intent` is read from authoritative position state (ADR-0019 rule 4), never a caller-supplied field. `EXIT`-intent orders are unaffected — this invariant must never block an exit (ADR-0044, closes the mint-to-send hand-off window; ADR-0019 fixed point). Numbered 19 rather than inserted into the 1-10 Execution group above, because those were numbered before this invariant existed; it belongs conceptually with invariant 1, not chronologically after 18.

Invariant 3 is the one that must exist before the thing it protects. Page 14 identifies the single Windows VPS as a failure risk and proposes a standby without addressing split-brain. Two live bridges without a lease is not redundancy, it is duplicate orders on every signal. The lease has to land before the standby does.

## Interfaces

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Command (bus) | `cmd.execution.place_order.v1` | queue | 300ms send | **C21 only, token required** |
| Command (bus) | `cmd.execution.cancel_order.v1` | queue | 300ms | C23 |
| Command (bus) | `cmd.execution.modify_position.v1` | queue | 300ms | C23 |
| Query | `get_order(client_order_id) -> OrderStatus` | Yes | 100ms | service, operator |
| Query | `broker_health() -> AdapterHealth` | Yes | 50ms | service, operator |
| Command | `attach_plan(position_id, plan)` (C23) | Yes | 100ms | service, operator |
| Command | `request_exit(position_id, reason, urgency)` (C23) | Yes | 100ms | service, operator |
| Query | `list_unmanaged() -> [Position]` (C23) | Yes | 100ms | service, operator |
| Command | `run(account_id, mode) -> ReconciliationResult` (C25) | Yes | 10s | service, operator |
| Command | `resolve_break(break_id, resolution, a, b)` (C25) | Yes | 1s | dual-control, audited |
| Adapter | `BrokerAdapter` protocol (L4.1) | — | — | — |

Three `BrokerAdapter` implementations exist from day one: `Mt5Adapter`, `SimulatedAdapter`, `NullAdapter` (shadow). They are not future work. Building the interface against three implementations from the start is the only way to know it is actually broker-agnostic rather than MT5 with a wrapper, and the simulated and null adapters are what make the Simulation Harness and shadow mode possible at all.

## Degraded Mode

The field R05 flags as highest-value here. Page 11 names connectivity loss with an unknown outcome as a failure mode and describes recovery; what it does not state is how the platform behaves **while** an `UNKNOWN` order is outstanding, which is the state during every real incident.

| Condition | Behaviour |
|---|---|
| **Order in `UNKNOWN`** | **Block all new entries for that account immediately.** Query broker status with backoff for up to 60s. Never resend. If unresolved at 60s, trip the kill switch for that account and page P0. The position may or may not exist, and sizing the next trade against an unknown book is how one bad order becomes two |
| Broker connection lost, no order in flight | Platform Supervisor moves the account to `DEGRADED`. No new entries. **Broker-side stops remain the protection**, which is why invariant 10 exists |
| Broker connection lost, order in flight | As row 1. In-flight plus disconnected is the worst case and is treated as such |
| Leader lease lost | **Stop sending immediately, mid-operation.** Do not finish the current send. A lease that has expired may already have been acquired elsewhere |
| Partial fill | First-class state. Remainder re-queued or cancelled per time-in-force, deterministically. **The filled portion gets a broker-side stop before the remainder is resolved** |
| Slippage beyond tolerance | Flag for review, publish `evt.execution.fill.analysed.v1`. Never auto-cancel, never auto-retry. A **pattern** trips the kill switch |
| C23 cannot reach the broker | Emit P0, platform enters `DEGRADED`, new entries blocked. Existing broker-side stops are the last line of defence |
| Open position with no plan | `UNMANAGED`, alerted. Any duration over 60s is P0 |
| Position at the broker unknown to the platform | Critical break. **Auto-trip the kill switch.** Adopt as `ADOPTED_UNMANAGED`, never auto-manage |
| Broker truth unobtainable | **That is itself a critical break. Trading halts.** The absence of an answer is not a passing result |
| Reconciliation finds a quantity mismatch | Critical break, auto-trip, P0 page. Never auto-correct |

The last-but-one row is the distinction that makes C25 worth building. A reconciliation service that treats "could not check" as "nothing found" is a reconciliation service that reports clean during exactly the outage it exists to catch.

## SLO

| Dimension | Target |
|---|---|
| C24 availability, market hours | 99.95% |
| Order send to broker ack | p50 < 120ms, p95 < 250ms, p99 < 300ms (page 11's budget, with percentiles) |
| C23 decision to command issued | p50 < 50ms, p99 < 500ms |
| C25 reconciliation run | p99 < 10s |
| **Correctness** | **Zero orders sent without a valid token. Zero duplicate `client_order_id` submissions** |
| **Correctness** | **Zero `ENTRY` orders sent while any kill-switch tier reports HALTED or unreadable. Zero `EXIT` orders blocked by the recheck** (invariant 19, ADR-0044) |
| **Correctness** | **Zero open positions without a broker-side stop. Zero unmanaged open positions** |
| Correctness | Zero orders left in `UNKNOWN` longer than 60s |
| Reconciliation | Zero critical breaks open longer than 5 minutes. 100% of restarts gated on a clean reconciliation |
| Redundancy | Zero intervals with two lease holders. Asserted continuously, not tested once |

## Security Boundary

| | |
|---|---|
| **Zone** | C24 in Bridge (Windows VPS), the only Windows-bound container. C23 and C25 in VAULT |
| **Callers permitted** | `place_order`: C21 only, and the token is checked regardless of caller identity. `cancel`/`modify`: C23 only. Never callable from CORE or the operator plane directly |
| **Secrets held** | **C24 is the only process in the platform holding broker credentials.** C23 and C25 hold none: C23 issues commands, C25 reads broker state through C24's adapter |
| **Trusts** | The approval token's signature and nothing else about the command. **Trusts broker responses on position truth, and not on anything else** |
| **Never trusts** | Its own send response as confirmation (invariant 7). A proposal's confidence. A retry's assumption that the previous attempt failed |
| **Network** | Outbound to the broker endpoint. Outbound to VAULT (T2 Redis, T3 Postgres), **kill-switch tier reads only**, added by ADR-0044 invariant 19 — see `21_Security_Architecture.md` §5 for the Bridge zone egress definition. **No inbound from the internet.** Operator access via C32 with mTLS, MFA, and typed confirmation |
| **Privileged actions** | Manual order actions via Ops CLI require typed confirmation and are audited. `resolve_break` requires two approvers |
| **Live trading gate** | Live is **off by default**. Two locks must open together: the environment gate and the per-order typed confirmation during any manual operation. Everything routes to paper until both do |

The credential isolation is the reason the VAULT boundary exists at all. Every other service in the platform can be fully compromised without an order reaching a broker. That property is worth more than any single control inside C24, and it survives only if nothing else is ever given a broker credential "temporarily".

---

## Related

- Source page, unmodified: `../11_Execution_Platform.md`
- `10_Risk_Portfolio_Platform.contract.md` — the token issuer upstream
- `../generated/15_Event_Catalog_v2.md` §4.10-4.12 — execution, position lifecycle, reconciliation subjects
- `../review/R05_Interface_Contracts.md` §5, §8 — full OMS and Reconciliation contracts
- `../review/R07_State_Machines.md` — the order and trade lifecycle state machines
- `../decisions/0016-oms-owns-order-and-position-lifecycle.md` — C23
- `../decisions/0022-every-entry-carries-a-broker-side-hard-stop.md` — invariant 10, fixed point
- `../decisions/0037-commands-and-events-are-distinct.md` — invariant 2, closes B1
- `../decisions/0044-kill-switch-recheck-at-broker-send.md` — invariant 19, added 2026-08-06
