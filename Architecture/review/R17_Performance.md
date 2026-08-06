# R17 — Performance Engineering

**Deliverable:** 17
**Delta against:** the per-page Latency Budget fields across pages 00-14
**Status:** Review v1.0

---

## 1. Assessment

Having per-component latency budgets at all is unusual and good. Four problems with them as stated:

| # | Problem | Consequence |
|---|---|---|
| L1 | No percentiles. "< 500ms" without p50/p95/p99 is unmeasurable (finding D2) | Nothing can be alerted on correctly |
| L2 | Never summed end to end (finding D3) | The real budget from bar close to broker ack is ~11.2s and no page states it |
| L3 | No consequence defined for a breach | A budget with no enforcement is a comment |
| L4 | No throughput dimension at all | Everything is specified per single symbol per single call. Scaling behaviour is undefined |

---

## 2. The end-to-end budget (L2)

Summing the ADD's own per-stage budgets:

| Stage | Page 00-14 budget | Cumulative |
|---|---|---|
| MT5 tick to raw storage | 50ms | 50ms |
| Quality detectors + scorer | 110ms | 160ms |
| Feature store live query | 50ms | 210ms |
| Quant engines (parallel) | 500ms | 710ms |
| Model inference | 200ms | 910ms |
| Committee cycle | **10,000ms** | 10.9s |
| Risk check | 100ms | 11.0s |
| Order send to ack | 300ms | **11.3s** |

**Bar close to broker acknowledgement: ~11.3 seconds.**

On a 15-minute timeframe this is completely acceptable: 1.3% of the bar interval. The design is sound. But two things must follow from stating it, and neither is in the ADD.

### Consequence 1: decision expiry is mandatory (P0.9)

An 11-second-old decision was formed against a price that may no longer exist. Without an expiry mechanism, a decision delayed by a slow desk or a retry executes against a materially different market than the one it reasoned about.

```
valid_until = decision.created_at + min(
    12s,                                   # hard platform ceiling
    0.10 x bar_interval,                   # never more than 10% of the bar
    atr_based_window(symbol, tolerance)    # tighter when vol is high
)
```

Checked immediately before order send (R05 §6 StalenessGate). Expiry emits `evt.decision.expired.v1` and is tracked as an SLI. A rising expiry rate is the earliest signal that the decision path is degrading.

**Plus a price-drift gate:** if price has moved more than a configured fraction of ATR since the evidence was sealed, reject regardless of remaining time. Time and price are different staleness dimensions and both matter.

### Consequence 2: the timeframe floor is an architectural constraint

| Timeframe | Budget as % of bar | Verdict |
|---|---|---|
| 1D, 4H, 1H | < 0.4% | Comfortable |
| **15m (primary)** | **1.3%** | **Comfortable. This is the design point** |
| 5m | 3.8% | Workable |
| 1m | 19% | Marginal. Requires admission control to be very selective |
| < 1m | > 19% | **Architecturally out of scope.** Would require removing the LLM from the decision path |

This should be stated explicitly in page 00 as a constraint, not discovered later. The committee-in-the-loop design has a floor, and that floor is around one minute.

---

## 3. Latency budgets, restated with percentiles (L1, L3)

| Path | p50 | p95 | p99 | On p99 breach |
|---|---|---|---|---|
| Tick ingest to storage | 10ms | 30ms | 50ms | P2, drop oldest ticks (TICKS stream discard policy) |
| Bar ingest to quality verdict | 40ms | 80ms | 150ms | P2 |
| Quality verdict to feature materialised | 60ms | 120ms | 250ms | P2 |
| Feature serving (online read) | 5ms | 20ms | 50ms | P1, fall back to the offline path and mark stale |
| Regime / Vol / Structure compute | 150ms | 350ms | 500ms | P2, serve last good with `stale=true` |
| Model inference | 50ms | 120ms | 200ms | P2, desk abstains |
| Evidence graph assembly | 100ms | 300ms | 1000ms | P1, cycle aborts |
| Single desk call | 2s | 5s | 8s | Desk abstains at 8s. Not negotiable |
| Full committee cycle | 5s | 9s | 11s | Cycle terminates at deadline with whatever quorum exists |
| **Ledger snapshot query** | **5ms** | **15ms** | **30ms** | **Risk rejects. Fail closed** |
| **Risk decide** | **20ms** | **60ms** | **100ms** | **Reject. Fail closed** |
| **Kill switch check (3 tier)** | **1ms** | **4ms** | **10ms** | **HALT. Fail closed** |
| Order command to broker ack | 80ms | 200ms | 300ms | Order enters `UNKNOWN`, P0 if sustained |
| Fill to ledger applied | 20ms | 60ms | 100ms | P1 |
| Reconciliation full run | 2s | 6s | 10s | P1 |

**The bold rows are the ones where a breach means "fail closed", not "degrade".** That distinction is the missing L3 element: for most of the platform, exceeding the budget means serving a stale answer with a flag. For the three authorisation-path components, it means refusing to trade. Mixing the two policies is how a fail-closed control quietly becomes a fail-open one under load.

---

## 4. Throughput targets (L4)

| Dimension | Current design point | Target | Ceiling before redesign |
|---|---|---|---|
| Symbols tracked | 1 (XAUUSD) | 5 | ~25 |
| Timeframes per symbol | 5 | 5 | 8 |
| Bars/second ingested | ~0.02 | ~0.5 | ~50 |
| Ticks/second | ~10 | ~100 | ~5,000 |
| **Committee cycles/day** | **~10** | **~50** (5 symbols) | **~200** |
| Orders/day | ~5 | ~25 | ~200 |
| Feature reads/second | ~1 | ~10 | ~1,000 |
| Concurrent backtests | 1 | 4 | Bounded by CPU |

**The binding constraint is committee cycles**, and it binds on **cost** before it binds on latency or compute. At ~38k tokens per cycle (R10 §12), 200 cycles/day is ~7.6M tokens/day. That is the real ceiling, and it is why admission control is architectural rather than an optimisation.

**Scaling shape by component:**

| Component | Scales with | Strategy |
|---|---|---|
| Ingestion | Sources x symbols | Horizontal, one worker per source |
| Quality | Bars/sec | Horizontal, stateless, partition by symbol |
| Feature materialisation | Symbols x timeframes x features | Horizontal by symbol, single writer per Iceberg table |
| Quant engines | Symbols x timeframes | **Horizontal by symbol.** The natural partition key |
| Committee | Cycles/day | Horizontal, but **cost-bound before compute-bound** |
| **Risk Engine** | Decisions/sec | **Vertical only.** Single-writer semantics on limits and the kill switch. Correct and deliberate |
| **Execution** | Orders/sec | **Singleton, leader-elected.** Never horizontal |
| Ledger | Fills/sec | Single writer, read replicas for projections |

Two components must never scale horizontally, and both are on the capital path. That is not a limitation; it is the design. The throughput they need (hundreds of decisions per day) is three orders of magnitude below what a single process handles.

---

## 5. Caching

| Cache | Contents | Invalidation | TTL | Notes |
|---|---|---|---|---|
| Instrument specs | In-process | Event-driven on `spec.changed` | 300s safety | Highest-value cache. Sub-ms reads on the sizing path |
| Feature online store | Redis | Written by the materialiser | From the registry's `max_staleness` per feature | Read-through, never write-back |
| Portfolio projection | Redis | Written by the projector on each ledger event | None; freshness by `as_of` on read | **Not a cache.** A projection. Never written by a reader |
| LLM responses | Redis + Postgres | Content-addressed by (prompt version, evidence hash) | 24h live, forever in sim | **Makes replay determinism achievable** |
| Evidence graphs | MinIO, content-addressed | Immutable | Forever | Enables counterfactual replay |
| Calendar / sessions | In-process | Daily refresh + event | 3600s | |
| Kill switch tier 1 | In-process | Subscription + 1s poll | **5s hard, then HALT** | The TTL is a safety control, not a performance one |

**Two rules:**

1. **Nothing on the authorisation path is cached except the three-tier kill switch and instrument specs.** Portfolio state, limits, and the kill switch itself are read fresh. Caching a limit is how a limit change fails to take effect.
2. **Every cache entry carries the `as_of` of its underlying data**, so a consumer can detect staleness rather than trusting a TTL. TTL-only caching hides the case where the upstream stopped updating.

---

## 6. Admission control (the most important performance mechanism)

Not mentioned anywhere in the ADD, and it is what makes the committee architecture viable. Without it, every bar close on every symbol on every timeframe triggers a cycle: 5 symbols x 5 timeframes x 96 bars/day = 2,400 cycles/day at ~38k tokens each. Untenable, and unnecessary.

### Four-tier funnel

```
Tier 0  Every bar close                        ~2,400/day
        Cost: nothing. Just an event.
   |
   v  Cheap deterministic filter
Tier 1  Structural trigger present?             ~200/day
        - structure.confluence.detected (page 06, already the right primitive)
        - regime.shift.detected
        - volatility.regime_shift
        - scheduled fallback (so a symbol is never ignored indefinitely)
        Cost: nothing. Already computed.
   |
   v  Cheap deterministic gate
Tier 2  Pre-conditions satisfiable?             ~80/day
        - platform mode permits entries
        - no news blackout
        - exposure headroom exists for this symbol
        - not within cooldown of the last cycle for this symbol
        - deterministic graph baseline |log-odds| above a floor
        Cost: microseconds. NO LLM.
   |
   v  Budget gate
Tier 3  Cost budget available?                  ~50/day
        - daily and per-symbol token budget
        - degraded mode reduces the desk count before refusing entirely
   |
   v
Tier 4  FULL COMMITTEE CYCLE                    ~50/day
        Cost: ~38k tokens
```

**Tier 2's baseline gate is the highest-leverage filter.** The deterministic evidence-graph propagation (R09 §5) is free and already computed. If it says the evidence is flat, there is nothing for six language models to deliberate about, and calling them anyway is pure cost. Roughly a 48x reduction from Tier 0 to Tier 4.

**Cooldown** prevents a chattering trigger (a regime probability oscillating around a boundary, which page 04 names as a failure mode) from producing a cycle storm. Default: no more than one cycle per symbol per 3 bars, except for regime shifts, which bypass cooldown once.

---

## 7. Parallelism

| Level | Where | Mechanism |
|---|---|---|
| Desk calls | 6 concurrent per cycle | `asyncio.gather` with per-desk deadlines. The single largest latency win: 6 x 3s serial becomes ~3s |
| Quality detectors | 7 concurrent per dataset | Vectorised where possible, threads for IO |
| Quant engines | 4 concurrent per bar | Independent processes; regime must complete before volatility (a genuine dependency, page 05) |
| Symbols | Fully independent | Partition key throughout |
| Risk rule chain | **Sequential, deliberately** | Fail-fast ordering matters, and the total is under 100ms. Parallelising would obscure which rule failed first |
| Backtests | Parallel across parameter sets | Bounded by a worker pool with a hard resource limit |

**The one place parallelism is deliberately refused is the risk rule chain.** Ordering carries meaning (cheapest and most-likely-to-fail first), the sequential total is well within budget, and knowing which rule rejected first is diagnostically valuable.

---

## 8. Worker architecture

| Class | Pattern | Concurrency | Isolation |
|---|---|---|---|
| IO-bound (ingestion, LLM gateway, API) | `asyncio` single process | High | Process per service |
| CPU-bound (GARCH/HMM fits, feature computation) | Process pool | `cpu_count - 2` | Never on the same host as the Risk Engine |
| Batch (backtests, training) | Dedicated worker pool | Bounded | **Separate host or hard cgroup limits** |
| Latency-critical (Risk, Execution) | Single process, no pool | 1 | **Dedicated CPU reservation, own host** |

**Resource isolation is a correctness requirement, not tidiness.** A backtest sweep that saturates CPU on the same host as the Risk Engine turns a 20ms risk check into a 2-second one, breaching a fail-closed budget and halting trading. Hard limits on every container, and batch work never colocated with the capital path.

---

## 9. GPU

Honest assessment: **not needed, and adopting it now would be premature.**

| Workload | GPU benefit |
|---|---|
| GARCH / HMM fitting | None. Small matrices, iterative, CPU-bound |
| Gradient boosting (XGBoost/LightGBM) | Marginal at this data size. CPU is fine |
| SMC detection | None. Vectorised pandas/numpy |
| RL training | **Yes, if the policy network is non-trivial.** The only genuine candidate |
| LLM inference | Not applicable. Vendor API |

**Recommendation:** no GPU in the platform. If RL training becomes substantial, run it as an on-demand cloud instance in the `sim` environment. It is offline, batch, and not latency-sensitive, so a persistent GPU host is unjustified.

---

## 10. Backpressure

Absent from the ADD, and it is where event-driven systems fail under load. Per stream:

| Stream | Policy | Rationale |
|---|---|---|
| `TICKS` | **Discard old.** Never block a producer | A tick from 30 seconds ago is worthless. Dropping is correct |
| `MARKET` | **Reject new** (producer sees an error and retries with backoff) | Losing a bar creates a permanent gap. Backpressure to the producer is the right answer |
| `QUANT`, `DECISION`, `TRADING` | **Reject new**, alert immediately | These streams should never approach their limits. Doing so is itself an incident |
| `CONTROL` (commands) | Bounded queue, reject with an explicit error | A command that cannot be queued must fail loudly, never be silently dropped |
| `OPS` | Discard old | Reconstructible |

**Application-level backpressure:**

1. **Admission control (§6) is the primary mechanism.** Shed load before the expensive stage, not after.
2. **Bounded queues everywhere.** An unbounded queue converts a throughput problem into an out-of-memory crash, which is strictly worse.
3. **Circuit breakers on every external call**, so a slow vendor cannot exhaust the caller's connection pool.
4. **Consumer lag as an SLI** with alerting before the limit, not on breach.
5. **Degradation ladder under sustained load:** reduce the desk count → skip round 2 debate → raise the Tier 2 baseline threshold → suppress non-critical symbols → refuse new cycles. **Never** shorten the risk chain or skip reconciliation. Load shedding removes deliberation, never safety.

That last sentence is the rule that matters. Under pressure, the tempting shed is the expensive check, and the expensive checks on the capital path are the ones that must never be shed.

---

## 11. Performance testing

| Test | Frequency | Asserts |
|---|---|---|
| Latency regression on the decision path | Every build | No p99 exceeds its budget |
| Load test: 10x expected cycle rate | Weekly | Admission control sheds correctly, no unbounded queue growth |
| Soak test: 72h at expected load | Before each prod release | No memory growth, no connection leak, no consumer lag drift |
| Chaos + latency: inject 500ms into the ledger query | Every build | Risk fails closed rather than exceeding its budget |
| Cost regression | Every build | Tokens per cycle within budget |
| Backtest throughput | Weekly | 5 years x 1 symbol completes within the target |

The chaos-plus-latency test is the one that matters most and is rarely written: it proves that a slow dependency produces a rejection rather than a silently-exceeded budget.

---

## 12. Related

- `R00_Executive_Review.md` (D2, D3, P0.9)
- `R10_Committee_Architecture.md` (§12 cost model)
- `R12_Observability.md` (§8 SLOs measuring these budgets)
- `R13_Infrastructure.md` (compute topology, isolation)
- Source: latency budget sections across `../00` to `../14`
