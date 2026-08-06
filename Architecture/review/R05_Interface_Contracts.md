# R05 — Interface Contracts

**Deliverable:** 5
**Delta against:** the per-component template defined in `ROADMAP.md` and applied across pages 01-14
**Status:** Review v1.0

---

## 1. Assessment of the existing template

The ADD's 12-field template (Purpose, Responsibilities, Inputs, Outputs, Dependencies, Events Published, Events Consumed, Failure Modes, Recovery Strategy, Latency Budget, Technology, Future Expansion) is good and consistently applied. That consistency is a genuine asset and should be preserved.

Six fields are missing, and their absence is what keeps the pages descriptive rather than binding:

| Missing field | What its absence causes |
|---|---|
| **Interfaces** (the brief asks for it; no page provides one) | Every page says what a component does. No page says how to call it. Implementation will invent signatures per subsystem |
| **Owns (exclusive data)** | Nobody can tell which component may write which table. This is how the Position smear (R03 §1) happened |
| **Invariants** | Failure Modes describes what can go wrong. Invariants describe what must never be true. Only the second is testable |
| **Degraded Mode** | Recovery Strategy assumes recovery. It does not say how the component behaves while still broken, which is the state it will be in during every real incident |
| **SLO** | Latency Budget without a percentile or an availability target is not measurable (finding D2) |
| **Security Boundary** | No page states who may call it, what secrets it holds, or what it trusts |

## 2. The corrected template

```markdown
### <Component Name>

**Context:** <bounded context>            **Container:** <C-id>
**Owner:** <role>                          **Criticality:** Tier 0 | 1 | 2

**Purpose** — one sentence, the question this component answers.
**Responsibilities** — 3 to 6 bullets. If it needs more, it is two components.
**Owns (exclusive)** — the tables/streams/keys only this component writes.
**Invariants** — statements that must never be false. Each one testable.

**Interfaces**
| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|

**Inputs** / **Outputs**
**Dependencies** — hard (cannot start without) vs soft (degrades without).
**Events Published** / **Events Consumed** — v2 subjects (R01 §3).
**Failure Modes** — with detection mechanism, not just a name.
**Degraded Mode** — behaviour while broken. Must be explicit and fail-safe.
**Recovery Strategy**
**SLO** — availability, latency percentiles, correctness, freshness.
**Security Boundary** — callers permitted, secrets held, trust assumptions.
**Technology**
**Latency Budget** — p50 / p95 / p99, and what happens on breach.
**Future Expansion**
```

**The two fields that matter most and are hardest to retrofit are Invariants and Degraded Mode.** Everything else can be added later. Those two shape the code.

Contracts below cover the new and materially changed subsystems. Pages 01-14 keep their existing entries; add the six missing fields to each during the P0 pass.

---

## 3. Instrument & Reference Data Master (C04, NEW)

**Context:** BC2 Reference Data **Criticality:** Tier 0 (position sizing is impossible without it)
**Owner:** Platform **Priority:** P0

**Purpose** — answer "what is this instrument, and may it be traded right now."

**Responsibilities**
- Serve authoritative contract specifications per symbol per broker.
- Serve the trading calendar: sessions, holidays, early closes, DST transitions, rollover dates.
- Map platform symbols to broker symbols and back (used by the Broker ACL).
- Version every specification change with an effective-from date.
- Publish session-open/close events that the Scheduler and Quality Engine depend on.

**Owns (exclusive):** `instruments`, `instrument_specs`, `calendars`, `sessions`, `holidays`, `symbol_mappings`.

**Invariants**
1. Every `Symbol` used anywhere in the platform resolves here. An unresolvable symbol is a hard error, never a default.
2. A spec is immutable once effective. A change creates a new version with a new `effective_from`.
3. `resolve(symbol, as_of)` always returns the spec that was in force at `as_of`, never the current one.
4. `tick_size`, `contract_size`, `pip_value` are `Decimal`. Never float.
5. A symbol with no spec effective at `as_of` is not tradable. There is no fallback default.

**Interfaces**

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Query | `get_spec(symbol, broker, as_of) -> InstrumentSpec` | Yes | 10ms (cached) | service |
| Query | `is_tradable(symbol, at) -> TradabilityVerdict` | Yes | 10ms | service |
| Query | `next_bar_close(symbol, timeframe, after) -> Timestamp` | Yes | 10ms | service |
| Query | `session_for(symbol, at) -> Session` | Yes | 10ms | service |
| Query | `to_broker_symbol(symbol, broker) -> str` | Yes | 5ms | service |
| Command | `publish_spec_version(spec, effective_from)` | Yes | 1s | operator, audited |

**Inputs:** broker specification feeds (MT5 `symbol_info`), exchange calendars, manual operator entry.
**Outputs:** specs, calendars, tradability verdicts.
**Dependencies:** hard — Postgres. soft — broker connection for spec refresh.

**Events Published:** `evt.instrument.spec.changed.v1`, `evt.calendar.session.opened.v1`, `evt.calendar.session.closed.v1`, `evt.calendar.holiday.upcoming.v1`.
**Events Consumed:** none. This context is a source.

**Failure Modes**

| Mode | Detection |
|---|---|
| Broker changes a spec silently (contract size, min lot, margin) | Daily automated diff against the live broker feed; any delta raises P1 |
| Calendar wrong or stale (missed holiday, early close) | Staleness monitor: calendar coverage must extend ≥30 days forward, else P1 |
| Symbol mapping drift (broker renames a symbol) | Mapping resolution failure rate metric; any failure is P0 during market hours |
| DST transition mishandled | Assertion in CI: bar-close times across a DST boundary must be continuous |

**Degraded Mode:** serves the last-known-good specs from a local cache and sets `degraded=true` on every response. **Any consumer receiving `degraded=true` may size and manage existing positions but may not open new ones.** Fail-safe, not fail-open.

**Recovery Strategy:** specs are refreshed from the broker on a schedule and diffed. A diff is a P1 alert requiring human confirmation, never auto-applied, because a broker feed glitch that halves `contract_size` would silently double every position size.

**SLO:** availability 99.95% during market hours; `get_spec` p99 < 10ms; calendar forward coverage ≥ 30 days; zero unresolvable symbols in production.

**Security Boundary:** read by every service; written only by an `operator` with audit. No secrets beyond the Postgres credential.

**Technology:** FastAPI, Postgres, aggressive in-process caching with event-driven invalidation.

**Latency Budget:** p50 < 1ms (cache hit), p99 < 10ms. On breach: consumers use their local cache and mark degraded.

**Future Expansion:** corporate actions, futures roll schedules, borrow/short availability, multiple broker specs per symbol for smart routing.

---

## 4. Account & Position Ledger (C22, NEW)

**Context:** BC7 Portfolio **Criticality:** Tier 0
**Priority:** P0

**Purpose** — be the single authoritative answer to "what do we own, what is it worth, and what did it cost."

**Responsibilities**
- Maintain an event-sourced, append-only record of every position and balance change.
- Apply fills, swaps, commissions, and dividends to positions and lots.
- Maintain cost basis and realised/unrealised P&L per position, per trade, per account.
- Publish the `PortfolioSnapshot` projection consumed by Risk (sync) and Deliberation (async).
- Detect and report divergence from broker truth.

**Owns (exclusive):** `ledger_events` (append-only), `positions_projection`, `accounts_projection`, `lots`, `trades`.

**Invariants**
1. The ledger is append-only. No event is ever updated or deleted. A correction is a compensating event.
2. Sum of lot quantities equals the position quantity, per symbol per account, at every point in the stream.
3. Double-entry: every balance change has a matching counterparty entry. The books balance or the service halts.
4. The projection is derivable from the event stream alone. Rebuild must be byte-identical, asserted in CI.
5. Only fills, broker-reported adjustments, and reconciliation corrections mutate the book. **A risk approval never mutates the book.**
6. `PortfolioSnapshot` always carries `as_of` and `sequence`. A consumer can detect that it read a stale snapshot.

**Interfaces**

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Query | `get_snapshot(account_id) -> PortfolioSnapshot` | Yes | 30ms | service (Risk) |
| Query | `get_snapshot_at(account_id, as_of) -> PortfolioSnapshot` | Yes | 2s | service, researcher |
| Query | `get_position(account_id, symbol) -> Position \| None` | Yes | 10ms | service |
| Query | `get_trade(trade_id) -> Trade` | Yes | 100ms | service, auditor |
| Command | `apply_fill(fill) -> LedgerResult` | Yes | 50ms | service (Execution only) |
| Command | `apply_correction(correction, reason, actor)` | Yes | 100ms | operator, dual-control, audited |

**Dependencies:** hard — Postgres, Instrument Master (for contract size and pip value in P&L). soft — Redis (projection cache; rebuildable).

**Events Published:** `evt.position.opened/increased/reduced/closed.v1`, `evt.position.stop_moved.v1`, `evt.account.equity_marked.v1`, `evt.ledger.correction_applied.v1`.
**Events Consumed:** `evt.execution.order.filled.v1`, `evt.execution.fill.analysed.v1`, `evt.reconciliation.break_detected.v1`.

**Failure Modes**

| Mode | Detection |
|---|---|
| Projection diverges from the event stream | Periodic rebuild-and-compare, hourly. Mismatch is P0 |
| Ledger diverges from broker truth | Reconciliation Service (C25), continuous |
| Duplicate fill applied | Inbox dedup on `(broker_order_id, fill_sequence)` |
| Missed fill (broker filled, we never heard) | Reconciliation catches it. This is why reconciliation cannot be an inline check |
| Cost basis wrong after partial closes | Lot-level invariant assertion on every write |

**Degraded Mode:** if the projection cannot be served fresh, `get_snapshot` returns `stale=true` with the last known `as_of`. **The Risk Engine treats a stale snapshot as a hard rejection**, not a warning. Trading stops rather than sizing against an unknown book.

**Recovery Strategy:** the projection is always rebuildable from `ledger_events`. On startup, rebuild, then reconcile against the broker, and only then permit the Platform Supervisor to leave `RECONCILING`.

**SLO:** availability 99.99% (Risk depends on it synchronously); `get_snapshot` p99 < 30ms; zero unreconciled breaks older than 5 minutes; rebuild determinism 100%.

**Security Boundary:** `apply_fill` callable only by the Execution Service identity. `apply_correction` requires two human approvers. Read access for Risk, OMS, Learning, Auditor.

**Technology:** Python, Postgres (event store plus projection), Redis (projection cache only).

**Latency Budget:** p50 5ms, p95 15ms, p99 30ms. On breach: Risk fails closed.

**Future Expansion:** multi-currency accounts with FX revaluation, margin modelling per broker, tax-lot reporting.

---

## 5. Order & Position Lifecycle Manager / OMS (C23, NEW)

**Context:** BC8 Order Execution **Criticality:** Tier 0
**Priority:** P0. This is the largest functional gap in the ADD.

**Purpose** — own everything that happens to a position **after** it is opened, which the current ADD assigns to nobody.

**Responsibilities**
- Drive the trade lifecycle state machine (R07 §5) for every open position.
- Execute management actions: stop to breakeven, trailing stop, partial take-profit, time-based exit, structure-invalidation exit.
- Detect and adopt positions that were opened or modified outside the platform.
- Request exits, subject to the same Risk authorisation as entries.
- Emit management events for the Journal and for Learning.

**Owns (exclusive):** `managed_positions`, `management_plans`, `management_actions`.

**Invariants**
1. Every open position has exactly one active `ManagementPlan`, or is explicitly flagged `UNMANAGED` and alerted.
2. A management action never increases risk. Stops move only toward the entry, never away. Size only decreases. Any action that would increase exposure is a new entry and goes through the full Deliberation → Risk path.
3. Exit actions are authorised by the Risk Engine like entries, with a distinct `EXIT` intent that bypasses entry-blocking rules (a kill switch must never trap the platform in a position it cannot exit).
4. A position adopted from outside the platform enters `ADOPTED_UNMANAGED` and requires explicit operator action to attach a plan. It is never silently managed with default rules.

**Interfaces**

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Command | `attach_plan(position_id, plan)` | Yes | 100ms | service, operator |
| Command | `request_exit(position_id, reason, urgency)` | Yes | 100ms | service, operator |
| Command | `override_plan(position_id, plan, actor)` | Yes | 100ms | operator, audited |
| Query | `get_plan(position_id) -> ManagementPlan` | Yes | 10ms | service |
| Query | `list_unmanaged() -> [Position]` | Yes | 100ms | service, operator |

**Dependencies:** hard — Position Ledger, Risk Engine, Instrument Master. soft — Market Intelligence (structure invalidation triggers).

**Events Published:** `evt.position.plan_attached.v1`, `evt.position.stop_moved.v1`, `evt.position.partial_closed.v1`, `evt.position.exit_requested.v1`, `evt.position.adopted_unmanaged.v1`.
**Events Consumed:** `evt.position.opened.v1`, `evt.market_data.bar.ingested.v1`, `evt.market_structure.structure.published.v1`, `evt.reconciliation.break_detected.v1`.

**Failure Modes**

| Mode | Detection |
|---|---|
| Open position with no plan | Continuous scan, any unmanaged position for > 60s is P0 |
| Management action fails to reach the broker | Order state machine; unacked modification after 3 attempts is P0 |
| Plan and broker state diverge (stop moved manually at the terminal) | Reconciliation compares plan-intended stops against broker stops |
| Runaway trailing (repeated modifications on every tick) | Rate limit per position, plus a modification-count metric with an alert |
| Exit blocked by an entry-blocking rule | Invariant 3. Tested explicitly: kill switch active plus exit request must succeed |

**Degraded Mode:** if the OMS cannot reach the broker, it emits P0 and **the platform enters DEGRADED**, which blocks new entries. Existing stops at the broker remain the last line of defence, which is why every entry must carry a broker-side hard stop rather than a platform-side soft stop. That requirement is not in the current ADD and should be.

**Recovery Strategy:** on restart, reload every open position from the Ledger, reload plans from Postgres, reconcile intended versus actual broker stops, and repair differences before resuming management.

**SLO:** availability 99.95%; management action decision-to-broker p99 < 500ms; zero unmanaged open positions; zero positions without a broker-side stop.

**Security Boundary:** callable by Scheduler, Deliberation (for exit hypotheses), and Operator. Holds no broker credentials; it issues commands to Execution.

**Technology:** Python, Postgres, event-driven with a periodic sweep as a safety net (never purely event-driven for a safety-critical loop).

**Latency Budget:** p50 50ms, p99 500ms decision to command issued.

**Future Expansion:** scale-in ladders, options-style hedging overlays, a dedicated Exit Committee (an LLM cycle scoped to exit decisions, which is a natural extension of the existing Committee once entry calibration is stable).

---

## 6. Risk Engine (C21, CHANGED)

**Context:** BC6 Risk Authorisation **Criticality:** Tier 0
**Change from page 10:** dual-mode (`PREVIEW` / `DECIDE`), signed approval tokens, versioned limit sets, three-tier fail-closed kill switch, rules as an ordered chain of individually versioned units.

**Purpose** — be the single authority that answers "may this action be taken with this capital right now," and prove afterwards why.

**Owns (exclusive):** `limit_sets`, `risk_assessments`, `authorisations`, `killswitch_state`, `rejections`.

**Invariants**
1. Exactly one component in the platform issues authorisations. This one.
2. No `AuthorisedOrder` exists without a complete `RiskAssessment` recording every rule's verdict and the `limit_set_version` used.
3. `PREVIEW` mode never mutates state and never issues a token. Byte-identical rule evaluation to `DECIDE`, asserted in CI.
4. The kill-switch check is the final operation before token issuance, with no awaitable between them.
5. Every authorisation is single-use and TTL-bounded, and `valid_until` is shorter than the triggering bar interval.
6. A rejection is persisted as durably as an approval.
7. The signing key for approval tokens exists only in this service.

**Interfaces**

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Query | `preview(proposal) -> RiskAssessment` | Yes | 50ms | service (Deliberation) |
| Command | `decide(proposal) -> AuthorisedOrder \| Rejection` | Yes | 100ms | service (Deliberation) |
| Command | `authorise_exit(position_id, reason) -> AuthorisedOrder` | Yes | 100ms | service (OMS) |
| Command | `trip_killswitch(scope, reason, actor)` | Yes | 10ms | **any**, deliberately |
| Command | `clear_killswitch(scope, actor, confirmation)` | Yes | 1s | operator, dual-control if auto-tripped |
| Command | `publish_limit_set(limits, approver_a, approver_b)` | Yes | 1s | dual-control, audited |
| Query | `get_limits(as_of) -> LimitSet` | Yes | 10ms | service, auditor |

**Dependencies:** hard — Position Ledger (sync), Instrument Master (sync), Postgres, kill-switch tiers. soft — Volatility Engine (sizing input; absence forces the most conservative sizing, not a default).

**Events Published:** `evt.risk.trade.approved.v1`, `evt.risk.trade.rejected.v1`, `evt.risk.limit.breached.v1`, `evt.risk.killswitch.triggered.v1`, `evt.risk.killswitch.cleared.v1`, `evt.risk.limit_set.published.v1`, and the command `cmd.execution.place_order.v1`.
**Events Consumed:** `evt.decision.proposal.issued.v1`, `evt.position.*`, `evt.execution.fill.analysed.v1` (slippage-pattern trip), `evt.reconciliation.break_detected.v1` (auto-trip), `evt.calendar.*` (news blackout), `evt.platform.mode.changed.v1`.

**Failure Modes**

| Mode | Detection |
|---|---|
| Stale portfolio snapshot (page 10's own top failure) | Snapshot carries `as_of`; assessment rejects if older than 5s |
| Kill-switch tier unreachable | Heartbeat per tier; any tier unreachable means HALTED |
| Limit set misconfigured after a change | Dual control plus a mandatory dry-run against the last 30 days of proposals, showing what would have changed |
| Sizing overflow/underflow | `Decimal` throughout plus explicit min/max clamps with an alert on clamp |
| Rule ordering changed accidentally | Rule chain order is a versioned artefact; a change is a limit-set version bump |
| Token replay | Single-use compare-and-set on consumption |

**Degraded Mode:** any hard dependency unavailable results in **all `decide` calls rejecting**. `preview` returns `unavailable`. Exits remain authorisable if the Ledger is readable, because trapping the platform in a position is worse than the risk of an exit. This asymmetry is deliberate and must be tested.

**SLO:** availability 99.99%; `decide` p99 < 100ms; **zero authorisations issued without a complete assessment** (this is a correctness SLO, not a performance one, and it is the most important number on the platform); zero authorisations issued while any kill-switch tier reports HALTED.

**Security Boundary:** `decide` callable only by the Deliberation service identity. `authorise_exit` only by OMS. Holds the token signing key. Never holds broker credentials.

**Latency Budget:** p50 20ms, p95 60ms, p99 100ms. On breach: reject (fail closed), emit P1.

---

## 7. LLM Gateway (C17, NEW)

**Context:** BC5 Deliberation (ACL) **Criticality:** Tier 1
**Priority:** P1

**Purpose** — be the only path from the platform to any language model, so that vendor concerns, cost, and safety are enforced in exactly one place.

**Responsibilities**
- Resolve the point-in-time prompt version for a desk and bind it to the evidence.
- Enforce per-cycle and per-day cost budgets before the call, not after.
- Apply timeouts, retries with jitter, and circuit breaking.
- Cache identical (prompt version, evidence hash) pairs. In replay this is what makes determinism achievable.
- Record every call to the Decision Record Store: prompt, response, tokens, latency, model version, stop reason.
- Enforce output schema; a non-conforming response is an abstention, never a coerced parse.

**Owns (exclusive):** `llm_calls`, `llm_cache`, `cost_counters`.

**Invariants**
1. No component other than this one imports a vendor SDK.
2. Every call is recorded before its result is returned to the caller. An unrecorded call cannot influence a decision.
3. A call exceeding the budget is refused, and refusal maps to desk abstention, never to a cheaper model silently substituted.
4. In `sim` and `shadow`, a cache miss on a call that was recorded in the original run is a hard error, not a live call. This prevents a replay from quietly becoming a live experiment.
5. Model version is pinned per prompt version. An upgrade is a new prompt version requiring shadow validation (page 14's existing rule, now enforceable).

**Interfaces**

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Command | `invoke_desk(desk, evidence_ref, cycle_id, as_of) -> DeskOpinion \| Abstention` | Yes | 8s | service (Committee) |
| Query | `get_call(call_id) -> LlmCallRecord` | Yes | 100ms | auditor |
| Query | `budget_status(scope) -> Budget` | Yes | 10ms | service |

**Dependencies:** hard — Prompt Registry, Decision Record Store, Cost Governor. soft — Anthropic API (its absence is a designed degradation, not an outage).

**Events Published:** `evt.llm.call.completed.v1`, `evt.llm.call.failed.v1`, `evt.cost.budget.exceeded.v1`.

**Failure Modes**

| Mode | Detection |
|---|---|
| Vendor outage or rate limit | Circuit breaker; open circuit means all desks abstain, quorum fails, cycle terminates NO_ACTION |
| Response violates schema | Schema validation; counted as abstention with a distinct reason code, tracked as a calibration metric |
| Cost runaway (a trigger storm causing thousands of cycles) | Budget counters plus Committee admission control (R17 §6) |
| Prompt injection attempt reaching a desk | Should be impossible after the ACL (R03 §9). Gateway adds a second check: any evidence field containing instruction-like patterns fails the call and raises P1 |
| Silent model deprecation by the vendor | Pinned model ID; a deprecation error is P1, never an automatic fallback |

**Degraded Mode:** circuit open means every desk abstains. Quorum (R03 §4) fails. The cycle terminates `NO_ACTION`. **The platform does not fall back to trading on quant signals without the Committee.** Stating this explicitly matters: the tempting fallback is exactly the one that removes the safety layer at the moment the system is already degraded.

**SLO:** availability 99.5% (a lower bar than the trading path, correctly); `invoke_desk` p95 < 5s, p99 < 8s; cost per decision cycle within budget 100% of the time; zero unrecorded calls.

**Security Boundary:** the only holder of the Anthropic API key. Egress-restricted to the vendor endpoint. No inbound access except from the Committee service.

**Technology:** FastAPI, Redis (cache, budgets), Postgres (call records).

**Future Expansion:** multi-vendor routing for adversarial review (the `three-brain` pattern page 08 gestures at), response streaming for dashboard live-reasoning display.

---

## 8. Reconciliation Service (C25, NEW)

**Context:** BC7 Portfolio / BC8 Execution **Criticality:** Tier 0
**Priority:** P1

**Purpose** — continuously prove that what the platform believes about positions, orders, and balances matches what the broker believes, and halt trading when it does not.

**Responsibilities**
- Poll broker truth on a schedule and after every fill.
- Diff broker state against the Ledger projection across positions, orders, balances, and stop/target levels.
- Classify breaks by severity and auto-halt on severe ones.
- Produce a break report with a proposed correction; never auto-correct silently.
- Gate the Platform Supervisor's exit from `RECONCILING`.

**Owns (exclusive):** `reconciliation_runs`, `breaks`, `break_resolutions`.

**Invariants**
1. Reconciliation runs at least every 60 seconds during market hours, and always after a fill, a restart, and a broker reconnect.
2. A severe break (position quantity mismatch, unknown position, unknown order) **auto-trips the kill switch** before any human is involved.
3. No break is auto-corrected. Corrections are operator actions with dual control, because an automatic correction against a temporarily wrong broker response would destroy the book.
4. Broker truth wins on positions and fills. The Ledger wins on decision attribution. Never the reverse.

**Interfaces**

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Command | `run(account_id, mode) -> ReconciliationResult` | Yes | 10s | service, operator |
| Query | `open_breaks() -> [Break]` | Yes | 100ms | service, operator |
| Command | `resolve_break(break_id, resolution, a, b)` | Yes | 1s | dual-control, audited |

**Events Published:** `evt.reconciliation.completed.v1`, `evt.reconciliation.break_detected.v1`, `evt.reconciliation.break_resolved.v1`.
**Events Consumed:** `evt.execution.order.filled.v1`, `evt.platform.mode.changed.v1`, `evt.execution.broker.reconnected.v1`.

**Break severity**

| Severity | Example | Action |
|---|---|---|
| **Critical** | Position exists at the broker that the platform does not know about; quantity mismatch | Auto-trip kill switch, P0 page |
| **High** | Stop/target at the broker differs from the OMS plan; order in an unexpected state | P0 page, block new entries |
| **Medium** | Balance differs by more than tolerance (unexpected swap/commission) | P1, investigate |
| **Low** | Timestamp or rounding differences within tolerance | Logged, trended |

**Degraded Mode:** if broker truth is unobtainable, that is itself a critical break. Trading halts. The absence of an answer is not a passing result, which is the distinction that makes this service worth having.

**SLO:** reconciliation completes within 10s p99; zero critical breaks open longer than 5 minutes; 100% of restarts gated on a clean reconciliation.

---

## 9. Platform Supervisor (C26, NEW)

**Context:** BC10 Platform Ops **Criticality:** Tier 0
**Priority:** P0 (the state machine), P1 (the service)

**Purpose** — own the single global answer to "what mode is the platform in," and make every other component's behaviour a function of it.

**Owns (exclusive):** `platform_mode`, `mode_transitions`.

**Invariants**
1. Exactly one mode is active at any instant, per account and platform-wide.
2. Mode is fail-safe: an unreachable Supervisor means every order-capable component behaves as if `HALTED`.
3. Every transition is audited with actor, reason, and preconditions evaluated.
4. Entry into `NORMAL` requires a clean reconciliation, all Tier-0 dependencies healthy, and, after an automatic halt, human confirmation.

**Modes and permitted actions:** see R07 §1.

**Interfaces**

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Query | `current_mode(scope) -> PlatformMode` | Yes | 5ms | service |
| Command | `request_transition(to, reason, actor)` | Yes | 1s | operator or service |
| Query | `readiness() -> ReadinessReport` | Yes | 500ms | operator |

**Degraded Mode:** the Supervisor being unavailable is itself a HALT condition, propagated by each component's local heartbeat check rather than by the Supervisor announcing it.

**SLO:** `current_mode` p99 < 5ms; zero instances of a component acting on a mode more than 10 seconds stale.

---

## 10. Cost Governor (C30, NEW)

**Context:** BC10 Platform Ops **Criticality:** Tier 2
**Priority:** P2

**Purpose** — keep the cost of thinking bounded and attributable, so a trigger storm cannot produce an unbounded LLM bill or an unbounded vendor data bill.

**Responsibilities**
- Track spend per decision cycle, per symbol, per day, across LLM tokens and metered vendor API calls.
- Enforce budgets by refusing admission to new committee cycles when exceeded.
- Attribute cost to decisions so cost per decision and cost per realised R can be measured.
- Alert at 50/80/100% of daily budget.

**Invariants**
1. Budget checks happen **before** the spend, not after.
2. Exceeding the budget degrades gracefully: cheaper triage, fewer desks, or no cycle. It never degrades to trading with fewer safety checks.
3. Exit-related and risk-related calls are never budget-blocked. Only new-entry deliberation is.

**SLO:** budget check p99 < 5ms; zero days exceeding the hard daily cap.

---

## 11. Contract fields to retrofit onto pages 01-14

For the P0 documentation pass, the six new fields per existing page. Highest value first:

| Page | Most important missing field | Specifically |
|---|---|---|
| 01 Ingestion | **Owns** | Which service writes the raw tables. Currently ambiguous between ingestion and quality |
| 02 Quality | **Invariants** | "A REJECT dataset never reaches the Feature Store" must be a testable invariant, not a routing description |
| 03 Feature Store | **Interfaces** | `get_features()` signature is sketched; needs the full `FeatureView` contract (L4.4) |
| 04-06 Engines | **Degraded Mode** | Each says it returns the last good value with `stale: true`. What consumers must then do is unstated |
| 07 ML/RL | **Owns** | Training and inference must not share writable state |
| 08 Committee | **Invariants** | Quorum (R03 §4), citation-by-reference (R03 §5), critical-staleness veto |
| 09 Decision | **Interfaces** + verb change | `propose`, not `approve` (B4) |
| 10 Risk | **Security Boundary** | Who may call `decide`, who holds the signing key |
| 11 Execution | **Degraded Mode** | Behaviour with an `UNKNOWN` order outstanding |
| 12 Learning | **Invariants** | "No change reaches production without a PBO/DSR pass" as a mechanical gate, not a policy |
| 13 Infrastructure | **SLO** | Per-dependency availability targets that the dependent services' SLOs are built on |
| 14 Deployment | **Invariants** | "A gate bypass is impossible without a logged administrative override" |

---

## 12. Related

- `R02_C4_Expansion.md` (containers these contracts describe)
- `R03_Domain_Model_DDD.md` (the aggregates behind the invariants)
- `R07_State_Machines.md` (lifecycles referenced here)
- `R11_Risk_Architecture.md` (the rule chain in depth)
- `R19_Missing_Components.md` (rationale for each new service)
