# R11 — Risk Architecture

**Deliverable:** 11
**Delta against:** `10_Risk_Portfolio_Platform.md`
**Status:** Review v1.0

---

## 1. Assessment

Page 10 is the second-strongest page in the ADD. Three decisions are correct and load-bearing:

1. **The kill switch is a synchronous in-process gate, not a pub/sub subscriber**, with the propagation-window reasoning stated. This is the single best reliability call in the document.
2. **Broker truth over internal ledger** before every approval.
3. **Fractional Kelly as a standing platform default, not a per-trade tunable the Committee can override.** Removing discretion from sizing is exactly right.

The gaps are of two kinds: **completeness** (the risk taxonomy covers roughly half of what an institutional risk function covers) and **enforcement** (several correct policies have no mechanism that makes them true).

| # | Gap | Type |
|---|---|---|
| G1 | Kill switch fails open (B2) | Enforcement, critical |
| G2 | Sequential pipeline conflates gating with sizing | Structure |
| G3 | No VaR, CVaR, expected shortfall, or stress testing | Completeness |
| G4 | No model risk, operational risk, or liquidity risk treatment | Completeness |
| G5 | Limits are implied config, not a versioned dual-control artefact | Enforcement |
| G6 | No pre-trade impact simulation (page 10 lists it as future) | Completeness |
| G7 | No risk taxonomy at all, so nothing states what is measured against what | Structure |
| G8 | Exits are not distinguished from entries in the gating logic | **Critical safety** |

---

## 2. The risk taxonomy

Nothing measures what it does not name. Eight categories, each with an owner, a measure, a limit, and a control.

| # | Category | Question | Primary control | Owner |
|---|---|---|---|---|
| RT1 | **Market risk** | How much can we lose from price moves? | Position sizing, VaR/CVaR limits, stress scenarios | Risk Engine |
| RT2 | **Concentration risk** | Are we one idea pretending to be five? | Exposure caps, correlation limits, factor limits | Risk Engine |
| RT3 | **Drawdown risk** | Are we in a losing sequence that should reduce activity? | Drawdown guard, cooling periods, de-risking ladder | Risk Engine |
| RT4 | **Liquidity risk** | Can we get out at a reasonable price? | Position size vs typical volume, spread limits, session gating | Risk Engine + Microstructure |
| RT5 | **Execution risk** | Will we get the price we assumed? | Slippage tolerance, staleness gate, TCA feedback | Execution + Risk |
| RT6 | **Counterparty / broker risk** | What if the broker fails, freezes, or requotes? | Account limits, broker health, reconciliation | Risk + Reconciliation |
| RT7 | **Model risk** | What if the models are wrong in a correlated way? | Model risk register, drift detection, degradation ladder | Model Monitor + Risk |
| RT8 | **Operational risk** | What if the platform itself misbehaves? | Platform mode gating, circuit breakers, kill switch, audit | Platform Supervisor + Risk |

**RT7 and RT8 are absent from page 10 entirely**, and they are the two most likely to cause a large loss in a system of this type. A quant platform is far more likely to lose money because a model silently degraded or a bug placed ten orders than because of an adverse price move within its VaR.

---

## 3. The rule chain (replaces the sequential pipeline)

Page 10's pipeline mixes gates (pass/fail) with transforms (sizing) in one sequence. Separate them, because they have different semantics: a gate can reject, a transform can only reduce.

### Phase 1: Gates (ordered, fail fast, any FAIL rejects)

| # | Rule | Checks | Applies to entries | Applies to exits |
|---|---|---|---|---|
| 1 | `PlatformModeRule` | Mode permits this action type | Yes | **No** |
| 2 | `KillSwitchPreCheck` | Fast-path check (rechecked at issuance) | Yes | **No** |
| 3 | `InstrumentTradableRule` | Session open, not halted, spec valid | Yes | Yes (warn only) |
| 4 | `NewsBlackoutRule` | High-impact event proximity | Yes | **No** |
| 5 | `DrawdownGateRule` | Daily/total drawdown limits breached | Yes | **No** |
| 6 | `ExposureLimitRule` | Gross, net, per-symbol, per-currency caps | Yes | **No** |
| 7 | `CorrelationLimitRule` | Correlated cluster exposure | Yes | **No** |
| 8 | `LiquidityRule` | Spread, depth, size vs typical volume | Yes | Yes (sizing only) |
| 9 | `ModelRiskRule` | Any input model degraded or stale beyond tolerance | Yes | **No** |
| 10 | `VaRLimitRule` | Post-trade portfolio VaR within limit | Yes | **No** |
| 11 | `ProposalValidityRule` | Not expired, evidence hash present, signature chain intact | Yes | Yes |

**The critical column is the last one.** G8: **exits skip almost every gate.** A kill switch, a drawdown breach, a news blackout, or an exposure cap must never prevent closing a position. Page 10 does not distinguish entry from exit anywhere, which means a naive implementation of its pipeline traps the platform in positions precisely when it most needs to leave them. This is the most dangerous latent bug in the current risk design.

### Phase 2: Sizing (transforms, each can only reduce)

```
size_0 = volatility_target_size(risk_budget, atr_or_forecast_vol, instrument_spec)
size_1 = min(size_0, fractional_kelly_size(edge_estimate, kelly_fraction))
size_2 = min(size_1, exposure_headroom)
size_3 = min(size_2, correlation_adjusted_headroom)
size_4 = min(size_3, drawdown_scalar x size_3)      # de-risking ladder
size_5 = min(size_4, liquidity_cap)                  # % of typical volume
size_6 = min(size_5, hard_max_position)
size_7 = round_to_lot_step(size_6, instrument_spec)  # from BC2
if size_7 < instrument_spec.min_lot: REJECT (too small to trade)
```

**Monotonic reduction is the invariant.** No step may increase size. This makes the sizing chain trivially safe to extend: a new constraint can only ever make the position smaller, so adding one can never introduce an over-sizing bug.

Two additions to page 10:
- **Volatility targeting comes first, Kelly is an overlay that can only reduce.** Page 10 lists sizing then Kelly, which is right, but the "only reduce" property should be explicit.
- **Lot rounding at the end, against the instrument spec, with a minimum check.** Rounding a 0.007-lot position to 0.01 is a 43% size increase. This is a real and commonly-missed bug, and it is why the Instrument Master is a blocking dependency.

### Phase 3: Issuance (atomic)

```
1. Recheck kill switch, all three tiers          <- no await after this point
2. Recheck portfolio snapshot age <= 5s
3. Mint signed AuthorisedOrder (single use, TTL)
4. Persist assessment + authorisation in ONE transaction with the outbox row
5. Emit command
```

---

## 4. Portfolio risk measures

Page 10 has exposure and correlation. The following are needed and absent.

### VaR and CVaR

| Measure | Method | Horizon | Confidence | Limit example |
|---|---|---|---|---|
| Historical VaR | Empirical quantile over 500 trading days of the current portfolio's returns | 1 day | 99% | ≤ 2% of equity |
| Parametric VaR | EWMA covariance, cross-checked against historical | 1 day | 99% | Cross-check only, not a limit |
| **CVaR / Expected Shortfall** | Mean loss beyond VaR | 1 day | 97.5% | ≤ 3% of equity |

**Recommendation: make CVaR the binding limit, not VaR.** VaR tells you the loss you will not exceed 99% of the time and says nothing about the 1%. For a strategy on a single volatile instrument with fat tails, the 1% is where the account dies. CVaR is coherent (sub-additive, so diversification cannot increase it) and is the institutional standard for good reason.

**Honest caveat given this platform's scale:** with one to five instruments and a short history, VaR/CVaR estimates are noisy. They should be treated as a **secondary** control behind the primary controls (per-trade risk, drawdown, exposure), and their limits set loose enough that they bind only in genuinely unusual portfolio states. A tight VaR limit computed from 60 observations produces false confidence, which is worse than no limit.

### Stress testing (absent, and more valuable here than VaR)

Scenario-based stress is more useful than distributional VaR at this scale, because the scenarios are concrete and the estimates do not depend on a fitted distribution.

| Scenario | Shock | Pass criterion |
|---|---|---|
| Flash crash | 3% adverse gap on the primary instrument | Loss ≤ 1.5x max daily loss limit |
| Gap through stops | Adverse gap past every stop, filled 0.5% worse | Survivable, account not below margin call |
| Correlation goes to 1 | All positions move adversely together | Total loss ≤ drawdown limit |
| Spread blowout | Spread 10x normal at exit time | Exit cost ≤ 0.5% of equity |
| Broker freeze | No exits possible for 60 minutes during a 2% adverse move | Loss ≤ 2x max daily loss |
| Vol regime shift | Realised vol doubles | Position sizes auto-halve on the next cycle (verifies the vol-targeting chain) |

Run nightly against the current book and pre-trade for any proposal above a size threshold. A failing scenario is a P1 alert, not an automatic block, except for the broker-freeze scenario, which blocks new entries because it is the one with no recovery path.

### Correlation and clustering

Page 10 names a "correlation blind spot" (structurally correlated instruments not flagged). Fix:

1. **Rolling empirical correlation** over multiple windows (20/60/250 days). A single window is how a correlation regime change gets missed.
2. **A declared instrument cluster map** in the Instrument Master (gold complex, USD complex, risk-on complex). Empirical correlation misses structural relationships during quiet periods and finds them only after the loss.
3. **The binding limit is on cluster exposure**, not pairwise correlation. Pairwise limits are easy to game with three instruments at 0.65 correlation each.
4. **Stress correlation** assumed at 1.0 within a cluster for the stress scenarios above. Correlations converge in exactly the conditions that matter.

---

## 5. Drawdown control

Page 10 has a "Drawdown Guard" that "reduces/blocks new size as drawdown deepens." Make it a ladder with defined steps, because a continuous function invites a debate about the formula and a ladder does not.

| Drawdown from peak | Size multiplier | New entries | Additional |
|---|---|---|---|
| 0 to 3% | 1.00 | Normal | — |
| 3 to 5% | 0.75 | Normal | P2 notification |
| 5 to 8% | 0.50 | Normal | P1, mandatory review at the next weekly cycle |
| 8 to 12% | 0.25 | Highest-conviction only (conviction ≥ 80) | P0, operator acknowledgement required to continue |
| > 12% | 0.00 | **Blocked** | Kill switch trips. Manual dual-control restart |

Plus a **daily** limit that is independent of the peak-to-trough measure: max daily loss trips the kill switch for the remainder of the session regardless of where the account sits relative to its peak. Two different failure modes need two different controls.

**Cooling period:** after a kill-switch trip for drawdown, new entries are blocked for a defined period (default: until the next session open) even after the switch is cleared. The impulse to trade back a loss is the single most reliable way to turn a drawdown into a blow-up, and a platform that permits immediate resumption is a platform that will eventually do it.

---

## 6. Model risk (RT7, absent from the ADD)

The platform's decisions depend on at least seven models (regime, volatility, structure, ML predictor, RL policy, calibration, consensus weights). Page 07 names model staleness as a failure mode and assigns detection to page 12, weekly. Weekly is too slow for a model that degrades in a day.

### Model risk register

Every model in production carries:

| Field | Purpose |
|---|---|
| `criticality` | Tier 0 (a decision cannot be made without it) to Tier 2 (advisory) |
| `assumptions` | Written, explicit. E.g. "returns are conditionally normal", "the regime is persistent over ≥ N bars" |
| `known_failure_modes` | E.g. "GARCH underestimates vol immediately after a jump" |
| `degradation_signal` | The specific metric that indicates this model is failing |
| `degradation_action` | What happens automatically when it degrades |
| `fallback` | What is used instead |
| `max_staleness` | Beyond which the model's output is unusable, not just discounted |

### Degradation ladder

| Signal | Action |
|---|---|
| Prediction distribution shifts (PSI > 0.2 vs training) | P2, flag in the evidence graph as reduced reliability |
| Live hit rate below backtest CI lower bound over N predictions | P1, weight reduced by half |
| Two consecutive periods of degradation | Model demoted to `CHALLENGER`, previous champion restored |
| Model unavailable or non-convergent beyond `max_staleness` | Evidence node marked critically stale, which blocks proposals (R03 §4 invariant) |
| **Multiple models degrade simultaneously** | **Kill switch.** Correlated model failure means the regime has changed in a way none of the models represent, and that is the scenario where an automated system does the most damage |

The last row is the important one and it is the kind of control that only exists if someone deliberately thinks about model risk as a category.

---

## 7. Kill switch, corrected (B2)

### Three tiers, fail-closed

| Tier | Store | Read latency | Purpose | On failure |
|---|---|---|---|---|
| **T1** | In-process boolean, refreshed by subscription + 1s poll | ~0ms | The final check on the order path | If last refresh > 5s ago, treat as HALTED |
| **T2** | Redis | ~1ms | Shared state across processes | If unreachable, treat as HALTED |
| **T3** | Postgres | ~5ms | Durable truth, checked at token issuance | If unreachable, treat as HALTED |

**Combination rule:** `HALTED if ANY tier says HALTED OR ANY tier is unreadable.` Never a majority vote, never a fallback to the fastest available tier.

**Write order on trip:** T3 (durable) → T2 → T1 → broadcast command. A crash mid-trip leaves the switch engaged.
**Write order on clear:** T3 → T2 → T1. A crash mid-clear leaves the switch engaged.
Both orders are chosen so that every partial failure fails safe.

**Self-halt heartbeat:** every order-capable process independently tracks the age of its last successful full-tier verification. Beyond 10 seconds it halts itself without waiting to be told. This is what makes the switch robust to a network partition that isolates the Execution service from the Risk service.

### Trip conditions

| Condition | Scope | Auto-clear |
|---|---|---|
| Max daily loss breached | Account | No, session boundary + operator |
| Max drawdown breached | Account | No, dual control |
| Anomalous slippage pattern (page 10's existing condition) | Symbol | After N clean fills, auto |
| Reconciliation critical break | Account | No, dual control |
| Correlated model degradation | Platform | No, operator |
| News blackout window | Symbol | **Yes**, on window exit |
| Order rate exceeds a sane ceiling | Platform | No. A runaway loop is the operational failure that destroys accounts fastest |
| Platform mode HALTED | Platform | Follows mode |
| Manual | Any | Operator |

**The order-rate ceiling is not in page 10 and should be.** The most common way an automated trading system causes a catastrophic loss is not a bad prediction; it is a bug that submits orders in a loop. A hard ceiling (e.g. no more than 10 orders per minute per account, no more than 3 orders per symbol per minute) costs nothing in normal operation and is the only control that catches this class of bug before the account is gone.

---

## 8. Liquidity and execution risk

**Liquidity (RT4), absent from page 10:**

| Control | Limit |
|---|---|
| Position size vs typical session volume | ≤ 1% of typical volume for the session and instrument |
| Spread gate | Current spread ≤ 2x the trailing median for this instrument and session; otherwise reject entries, and for exits use a limit rather than a market order |
| Session gating | No new entries in the thinnest session unless the setup's historical performance in that session justifies it |
| Exit feasibility | Before entry, verify the position could be exited within the assumed slippage under stressed conditions. This is the check that stops the platform building a position it cannot leave |

**Execution risk (RT5):** page 10 already feeds slippage patterns to the kill switch, which is right. Add: TCA feedback closes the loop into sizing. If realised slippage on an instrument runs consistently above the modelled assumption, the effective risk per trade is higher than intended and position sizes should shrink automatically rather than waiting for a weekly review to notice.

---

## 9. Limits governance (G5)

Risk limits in a config file that anyone can edit are not limits. Requirements:

1. **Versioned `LimitSet` aggregate.** Immutable once published.
2. **Dual control.** Two distinct approvers, recorded in the audit log. In a solo-operator context this means a delay plus a written justification rather than a second person, which is weaker but still valuable: it prevents the impulsive change.
3. **Mandatory dry run.** Before publication, replay the last 30 days of proposals against the new limit set and report what would have changed. A limit change whose impact is unknown is a limit change nobody should approve.
4. **Effective-from timestamp.** Never retroactive.
5. **Every assessment records `limit_set_version`.** Post-mortem can prove what was in force.
6. **Loosening requires more scrutiny than tightening.** Tightening can be immediate; loosening requires the dry run and a cooling period.

Point 6 is the one that matters in practice, because every dangerous limit change is a loosening made during or immediately after a drawdown.

---

## 10. Operational risk (RT8, absent)

| Risk | Control |
|---|---|
| Duplicate orders | Deterministic `client_order_id`, single-use authorisation tokens, leader lease, order-rate ceiling |
| Split brain (two Execution instances) | Leader lease with TTL shorter than the failure-detection window |
| Stale decision executed late | `valid_until` + staleness gate (R05 §6) |
| Config error (a decimal place in a limit) | Typed parameters with declared ranges, dry run, dual control |
| Deploy of a broken build | Gates, shadow, canary by capital, auto-rollback |
| Platform acting on replayed events | `replay=true` interlock, `env` mismatch is a hard failure |
| Silent component failure | Heartbeats, dead-man's switch, synthetic transactions |
| Ledger corruption | Event sourcing with invariant assertions and rebuild determinism tests |
| Credential compromise | Segmentation, one credential holder, short-lived service certs |
| Operator error under stress | Typed confirmations, runbooks in every P0 alert, dual control on the dangerous operations |

**The operational-risk category is where most of this platform's actual loss probability sits**, and it is entirely absent from page 10. A quant platform run by one person is far more likely to lose money to a duplicate-order bug or a bad deploy than to a market move.

---

## 11. Pre-trade risk simulation (G6)

Page 10 lists this as future expansion. Recommend promoting it to P2, in a cheap form:

Before issuing an authorisation for any position above a size threshold, compute the post-trade portfolio under the six stress scenarios in §4 and verify each still passes. This is a deterministic, sub-10ms computation with a handful of positions. It catches the case that sequential per-rule checks structurally cannot: each rule passes individually while the combination is unacceptable.

---

## 12. Risk reporting

Absent from the ADD. Three artefacts:

| Report | Cadence | Contents |
|---|---|---|
| **Live risk dashboard** | Real time | Current exposure by symbol/cluster/currency, drawdown vs each ladder rung, VaR/CVaR vs limit, headroom on every limit, kill-switch state per scope, model health |
| **Daily risk summary** | Daily, post-session | P&L attribution, limit utilisation high-water marks, every rejection with reason, stress scenario results, any limit breach even if it did not block |
| **Weekly risk review** | Weekly, into the Learning cycle | Limit effectiveness (which limits actually bound and were they right), rejection analysis (what would those trades have done), model risk register review, near-misses |

The most valuable of the three is the rejection analysis: tracking what the trades the Risk Engine blocked would have done. If blocked trades would consistently have been profitable, the limits are miscalibrated and are costing money. If they would consistently have lost, the limits are working. Nobody measures this, and it is the only way to know whether the risk layer is well-tuned rather than just restrictive.

---

## 13. Related

- `R00_Executive_Review.md` (B2, B4)
- `R03_Domain_Model_DDD.md` (§6 BC6 aggregates and invariants)
- `R05_Interface_Contracts.md` (§6 Risk Engine contract)
- `R07_State_Machines.md` (§7 kill switch state machine)
- `R19_Missing_Components.md` (Instrument Master, Position Ledger as dependencies)
- Source: `../10_Risk_Portfolio_Platform.md`
