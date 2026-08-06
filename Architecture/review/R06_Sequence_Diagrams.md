# R06 — Sequence Diagrams

**Deliverable:** 6
**Delta against:** the whole ADD. No page contains a sequence diagram. Every page contains a pipeline, which shows *order* but not *interaction*, *timing*, *failure branches*, or *who waits on whom*.
**Status:** Review v1.0

---

## 1. Why pipelines are not enough

Page 09's `Quant Models → Evidence Graph → Committee Debate → Portfolio Impact → Risk Constraints → Decision → Explanation` reads as one linear flow. It hides four things that determine whether the system works:

1. Which steps are concurrent (six desks are parallel; the pipeline implies serial).
2. Which steps are synchronous calls with timeouts versus async event handoffs.
3. What happens on the failure branch at each step.
4. Where the deadline is enforced.

The eleven workflows below cover the critical paths. Each states its **trigger**, its **deadline**, and its **abort semantics**, because an interaction without a deadline is an interaction that hangs in production.

---

## 2. W1 — Happy path: bar close to journalled trade

**Trigger:** bar close for a tracked `(symbol, timeframe)`.
**Deadline:** 12s from bar close to order acknowledgement. Exceeded means the decision expires unexecuted.
**Abort:** any step may terminate the cycle. Termination is always recorded, never silent.

```mermaid
sequenceDiagram
    autonumber
    participant SCH as Scheduler
    participant ING as Ingestion
    participant DQ as Quality Engine
    participant FS as Feature Store
    participant QE as Quant Engines<br/>(Regime/Vol/Structure/Model)
    participant EG as Evidence Graph
    participant CM as Committee
    participant GW as LLM Gateway
    participant DS as Decision Saga
    participant LG as Position Ledger
    participant RK as Risk Engine
    participant EX as Execution
    participant BR as Broker (MT5)
    participant AU as Decision Records

    Note over SCH: t=0 bar close (from Instrument Master calendar)
    SCH->>ING: cmd.ingestion.close_bar (symbol, tf, logical_period)
    ING->>ING: normalise, dedupe on (source,symbol,ts)
    ING-->>DQ: evt.market_data.bar.ingested [t+50ms]

    DQ->>DQ: 7 detectors in parallel
    alt score < 0.5 REJECT
        DQ-->>AU: quarantine + evt.dataset.quarantined
        DQ--xFS: nothing forwarded
        Note over DQ: CYCLE ENDS. No decision on bad data.
    else score >= 0.5
        DQ-->>FS: evt.dataset.scored (score, flags) [t+150ms]
    end

    FS->>FS: materialise features (as_of = bar close)
    FS-->>QE: evt.feature_set.materialised [t+250ms]

    par Quant engines run concurrently
        QE->>QE: Regime (arbiter + calibration)
    and
        QE->>QE: Volatility (regime-conditional)
    and
        QE->>QE: Structure (multi-timeframe)
    and
        QE->>QE: Model inference
    end
    QE-->>EG: evt.*.published (x4) [t+750ms]

    Note over EG: Admission control (R17 section 6)
    EG->>EG: assemble graph, compute node weights
    alt no confluence AND no regime shift AND not scheduled review
        EG--xCM: no cycle convened
        Note over EG: CYCLE ENDS. Cheap. Most bars end here.
    end
    EG->>EG: seal graph, hash it
    EG-->>AU: evidence snapshot (content-addressed)
    EG-->>CM: evt.evidence_graph.assembled [t+900ms]

    CM->>CM: cycle_id = ULID, deadline = t+11s
    par Six desks, concurrent, isolated contexts
        CM->>GW: invoke_desk(regime, evidence_ref)
        GW->>GW: resolve prompt version @ as_of, check budget
        GW-->>CM: DeskOpinion (citations only, no numbers)
    and
        CM->>GW: invoke_desk(smc, ...)
        GW-->>CM: DeskOpinion
    and
        CM->>GW: invoke_desk(volatility, ...)
        GW-->>CM: DeskOpinion
    and
        CM->>GW: invoke_desk(macro, ...)
        GW-->>CM: DeskOpinion
    and
        CM->>GW: invoke_desk(risk, ...)
        GW-->>CM: DeskOpinion
    and
        CM->>GW: invoke_desk(execution, ...)
        GW-->>CM: DeskOpinion
    end
    CM->>CM: validate citations against sealed graph
    alt valid opinions < quorum (4 of 6)
        CM-->>AU: evt.committee.cycle.deadlocked (reason=quorum)
        Note over CM: CYCLE ENDS as NO_ACTION.
    end
    CM->>CM: Red Team pass (sees all evidence + majority stance)
    CM->>CM: log-odds pooling with calibrated weights
    alt dispersion > threshold
        CM-->>AU: evt.cycle.deadlocked (reason=conflict)
        Note over CM: CYCLE ENDS as NO_ACTION. No forced tiebreak.
    end
    CM-->>DS: evt.committee.recommendation.issued [t+9s]

    DS->>RK: qry.risk.preview(proposal) [SYNC 50ms]
    RK-->>DS: RiskAssessment (advisory, no token)
    alt preview fails hard
        DS-->>AU: evt.decision.proposal.withdrawn
        Note over DS: CYCLE ENDS.
    end
    DS->>DS: attach valid_until = t+12s
    DS-->>AU: full decision record sealed
    DS-->>RK: evt.decision.proposal.issued [t+9.2s]

    RK->>LG: qry.ledger.snapshot [SYNC 30ms, fail closed]
    LG-->>RK: PortfolioSnapshot (as_of, sequence)
    alt snapshot stale > 5s
        RK-->>AU: evt.risk.trade.rejected (stale_portfolio)
        Note over RK: CYCLE ENDS.
    end
    RK->>RK: rule chain (9 rules, ordered)
    RK->>RK: sizing: vol-target -> fractional Kelly -> hard caps
    RK->>RK: KILL SWITCH: 3-tier, last op, no await after
    alt any rule FAIL or any tier HALTED
        RK-->>AU: evt.risk.trade.rejected {stage, reason}
        Note over RK: CYCLE ENDS. Rejection is a first-class artefact.
    end
    RK->>RK: mint signed AuthorisedOrder (single-use, TTL)
    RK-->>AU: evt.risk.trade.approved
    RK->>EX: cmd.execution.place_order [EXACTLY ONCE, work queue] [t+9.4s]

    EX->>EX: leader lease check
    EX->>EX: validate token: signature, TTL, not consumed
    EX->>EX: staleness gate: valid_until, price drift tolerance
    alt expired or drifted
        EX-->>AU: evt.decision.expired
        Note over EX: CYCLE ENDS. Never execute a stale decision.
    end
    EX->>EX: client_order_id = det_hash(decision_id, leg)
    EX->>EX: idempotency check
    EX->>BR: place_order via MT5 adapter
    BR-->>EX: ack + broker_order_id [t+9.7s]
    EX-->>AU: evt.execution.order.submitted
    BR-->>EX: fill
    EX->>EX: FillAnalyser: decompose slippage
    EX-->>LG: evt.execution.order.filled [t+10s]
    EX-->>AU: evt.execution.fill.analysed
    LG->>LG: apply fill, update lots, cost basis, P&L
    LG-->>AU: evt.position.opened
    LG-->>OMS: evt.position.opened
    Note over OMS: W2 begins. The position now has an owner.
```

**Design points this diagram makes visible that the ADD does not:**

- The overwhelming majority of bars terminate at admission control (step ~19) without an LLM call. That is what makes the cost model viable, and it is invisible in page 09's linear pipeline.
- Six termination points, each producing a durable artefact. There is no path where a cycle simply stops with no record.
- The Risk Engine calls the Ledger, not the reverse. This is the fixed dependency direction from B3.
- `valid_until` is set once, in the Decision Saga, and checked last, in Execution. The staleness gate is the only thing standing between an 11-second reasoning cycle and an order placed on a price that no longer exists.

---

## 3. W2 — Position lifecycle management (entirely absent from the ADD)

**Trigger:** `evt.position.opened`, then every bar close while the position is open.
**Deadline:** management decision to broker command, 500ms p99.

```mermaid
sequenceDiagram
    autonumber
    participant LG as Position Ledger
    participant OMS as OMS
    participant MI as Market Intelligence
    participant RK as Risk Engine
    participant EX as Execution
    participant BR as Broker

    LG-->>OMS: evt.position.opened
    OMS->>OMS: attach ManagementPlan<br/>(BE trigger, trail rule, partials,<br/>time stop, invalidation level)
    OMS->>EX: cmd.execution.modify_position (hard broker stop)
    EX->>BR: set SL/TP at broker
    Note over OMS,BR: INVARIANT: every position has a<br/>broker-side stop before management begins

    loop every bar close while open
        MI-->>OMS: evt.market_structure.structure.published
        OMS->>OMS: evaluate plan against new bar
        alt BE trigger hit
            OMS->>EX: cmd.modify_position(sl=entry)
            EX->>BR: modify
            OMS-->>LG: evt.position.stop_moved
        else partial TP hit
            OMS->>RK: authorise_exit(partial, reason=plan_tp1)
            RK-->>OMS: AuthorisedOrder (EXIT intent)
            OMS->>EX: cmd.place_order(reduce)
            EX->>BR: close partial
            BR-->>EX: fill
            EX-->>LG: evt.order.filled
            LG-->>OMS: evt.position.reduced
        else structure invalidated
            OMS->>RK: authorise_exit(full, reason=invalidation)
            Note over RK: EXIT intent bypasses entry-blocking rules.<br/>Kill switch must never trap a position.
            RK-->>OMS: AuthorisedOrder
            OMS->>EX: cmd.place_order(close)
        else time stop reached
            OMS->>RK: authorise_exit(full, reason=time_stop)
        else nothing triggered
            Note over OMS: no action, recorded as a no-op tick
        end
    end

    BR-->>EX: broker-side SL hit (we did not initiate)
    EX-->>LG: evt.order.filled (exit)
    LG-->>OMS: evt.position.closed
    OMS->>OMS: retire plan
    OMS-->>LEARN: trade complete, full attribution to decision_id
```

The last branch matters: a broker-side stop firing is an exit the platform did not initiate. If the OMS only reacts to its own actions, that position stays "open" in its model forever. Reacting to the Ledger, not to its own commands, is what makes the OMS correct.

---

## 4. W3 — Broker disconnect with open positions

**Trigger:** adapter health check fails, or an order times out.
**This is the highest-stakes failure workflow in the platform.** Page 11 names it; no page sequences it.

```mermaid
sequenceDiagram
    autonumber
    participant EX as Execution
    participant BR as Broker (MT5)
    participant SUP as Platform Supervisor
    participant RK as Risk Engine
    participant REC as Reconciliation
    participant NOT as Notification
    participant OP as Operator

    EX->>BR: place_order / health check
    BR--xEX: timeout (no response)
    Note over EX: CRITICAL: outcome UNKNOWN.<br/>Did it fill or not?

    EX->>EX: order -> state UNKNOWN (first-class state)
    EX-->>NOT: P0 alert (order state unknown)
    EX-->>SUP: request_transition(DEGRADED, reason=broker_unreachable)
    SUP->>SUP: mode = DEGRADED
    SUP-->>RK: evt.platform.mode.changed
    RK->>RK: block ALL new entries. Exits still permitted.
    NOT->>OP: P0 page + runbook link

    loop reconnect backoff 1s,2s,5s,10s,30s (max 5m)
        EX->>BR: reconnect
        alt still down
            Note over EX: continue backoff.<br/>NEVER blind-retry the order.
        else reconnected
            EX->>BR: get_order_status(client_order_id)
            alt order exists and filled
                EX-->>LG: evt.order.filled (late)
                Note over EX: idempotency makes the late<br/>fill safe to apply
            else order exists and working
                EX->>EX: resume tracking
            else order does not exist
                EX->>EX: order -> NOT_SENT, safe to abandon
            end
            EX->>REC: run(account, mode=FULL)
            REC->>BR: get_positions, get_orders, get_account
            REC->>REC: diff against Ledger
            alt critical break
                REC-->>RK: trip_killswitch(critical_break)
                REC-->>NOT: P0
                SUP->>SUP: mode = HALTED
                Note over OP: Manual resolution required.<br/>Dual control to clear.
            else clean
                REC-->>SUP: evt.reconciliation.completed (clean)
                SUP->>SUP: mode = NORMAL (auto, since no capital event occurred)
                SUP-->>NOT: P2 recovered
            end
        end
    end
```

Three rules encoded here that the ADD lacks:

1. **Never blind-retry an order after a timeout.** Query status first. Page 11 has this right in principle via idempotent IDs; the sequence makes the ordering explicit.
2. **`UNKNOWN` is a state, not an error.** A timeout does not mean "not sent."
3. **Exits remain permitted in `DEGRADED`.** Only new entries are blocked. Halting exits during a broker problem is how a manageable loss becomes an unmanageable one.

---

## 5. W4 — Cold start

**Trigger:** platform start or restart.
**Deadline:** none. Correctness beats speed. Trading is not permitted until every gate passes.

```mermaid
sequenceDiagram
    autonumber
    participant SUP as Supervisor
    participant INF as Infra (NATS/PG/Redis/MinIO)
    participant REF as Instrument Master
    participant LG as Position Ledger
    participant EX as Execution
    participant BR as Broker
    participant REC as Reconciliation
    participant OMS as OMS
    participant RK as Risk
    participant OP as Operator

    SUP->>SUP: mode = STARTING (no trading, no decisions)
    SUP->>INF: health check all Tier-0 infra
    alt any unhealthy
        SUP->>SUP: mode = HALTED, P0 alert
        Note over SUP: STOP. Never start degraded.
    end

    SUP->>REF: load specs + calendars
    REF->>REF: verify calendar coverage >= 30 days forward
    alt coverage insufficient
        SUP->>SUP: HALTED
    end

    SUP->>LG: rebuild projection from ledger_events
    LG->>LG: replay, assert invariants (lots sum, books balance)
    alt invariant violated
        SUP->>SUP: HALTED, P0. Ledger corruption.
    end

    SUP->>EX: acquire leader lease
    alt lease held by another instance
        SUP->>SUP: mode = STANDBY (hot spare, no orders)
        Note over SUP: Correct outcome. Not an error.
    end

    SUP->>SUP: mode = RECONCILING
    EX->>BR: connect
    REC->>BR: get_positions, get_orders, get_account
    REC->>REC: full diff vs rebuilt Ledger
    alt breaks found
        REC-->>OP: break report, P0
        SUP->>SUP: HALTED until dual-control resolution
    end

    SUP->>OMS: load open positions
    OMS->>OMS: reattach management plans
    OMS->>OMS: verify every open position has a broker-side stop
    alt any position unprotected
        OMS->>EX: cmd.modify_position (restore stop)
        OMS-->>OP: P1 (a position was unprotected during downtime)
    end

    SUP->>SUP: catch-up: replay missed events from<br/>last checkpoint (idempotent consumers)
    Note over SUP: Stale market data is DISCARDED, not acted on.<br/>Ledger events are replayed. Decision triggers are not.

    SUP->>SUP: all gates green
    alt previous shutdown was clean AND no breaks
        SUP->>SUP: mode = NORMAL
    else previous shutdown was a crash OR breaks were resolved
        SUP->>OP: require typed confirmation to resume trading
        OP->>SUP: confirm
        SUP->>SUP: mode = NORMAL
    end
```

The distinction in the catch-up step is important and easy to get wrong: replaying ledger events on startup is mandatory (they are facts about capital). Replaying decision triggers is forbidden (they would produce trades based on the market as it was ten minutes ago).

---

## 6. W5 — Graceful shutdown

```mermaid
sequenceDiagram
    autonumber
    participant OP as Operator
    participant SUP as Supervisor
    participant RK as Risk
    participant CM as Committee
    participant EX as Execution
    participant LG as Ledger
    participant BUS as NATS

    OP->>SUP: request_transition(DRAINING, reason)
    SUP->>RK: stop accepting new proposals
    SUP->>CM: finish in-flight cycles, convene no new ones
    CM->>CM: in-flight cycles run to their deadline or complete
    SUP->>EX: no new orders. Track outstanding ones to terminal state.
    EX->>EX: wait for all orders to reach a terminal state<br/>(filled/cancelled/rejected), max 60s
    alt orders still non-terminal after 60s
        EX-->>OP: P1. Shutdown proceeds; these become<br/>UNKNOWN and are reconciled on next start.
    end
    EX->>EX: verify every open position has a broker-side stop
    Note over EX: CRITICAL: positions survive the shutdown.<br/>The broker stop is what protects them.
    LG->>LG: flush outbox, checkpoint projection
    BUS->>BUS: consumers ack outstanding, record sequences
    SUP->>SUP: write clean_shutdown marker
    SUP->>SUP: mode = STOPPED
```

The clean-shutdown marker is what allows W4 to skip the operator confirmation. Without it, every restart requires human intervention, which trains the operator to click through the confirmation reflexively, which defeats it.

---

## 7. W6 — Model retraining and promotion

**Trigger:** scheduled retrain, drift detection, or a validated Learning hypothesis.

```mermaid
sequenceDiagram
    autonumber
    participant LRN as Learning
    participant TR as Model Training
    participant VAL as Validation Gate
    participant REG as Model Registry
    participant SH as Shadow Runner
    participant OP as Operator
    participant INF as Model Inference

    LRN->>LRN: weekly review, failure detection
    LRN->>LRN: generate hypothesis (schema-enforced, falsifiable)
    LRN->>TR: enqueue experiment (params, data snapshot id, seed)
    TR->>TR: train against Iceberg snapshot (pinned, reproducible)
    TR->>REG: register CANDIDATE (metrics, snapshot id, code commit, seed)

    TR->>VAL: submit for validation
    VAL->>VAL: PBO across the full trial matrix
    VAL->>VAL: Deflated Sharpe (accounting for trial count)
    VAL->>VAL: walk-forward out of sample
    VAL->>VAL: leakage audit: assert no feature with<br/>point_in_time_safe=false was used
    alt any check fails
        VAL->>REG: mark REJECTED with the failing statistic
        VAL-->>LRN: negative result recorded
        Note over LRN: A rejected hypothesis is a RESULT,<br/>not a failure. It is recorded and never retried blind.
    end
    VAL->>REG: promote to VALIDATED

    REG->>SH: deploy to shadow
    SH->>SH: run alongside CHAMPION on live data,<br/>outputs recorded, NEVER acted on
    Note over SH: minimum 24h AND minimum N decisions,<br/>whichever is longer
    SH->>SH: compare: agreement rate, calibration,<br/>hypothetical P&L, latency, cost
    SH-->>OP: shadow report

    alt shadow degrades on any dimension
        OP->>REG: reject. Back to Learning with evidence.
    end
    OP->>REG: promote to CHAMPION (typed confirmation, audited)
    REG->>REG: previous CHAMPION -> CHALLENGER (keeps running)
    REG-->>INF: evt.model.version.promoted
    INF->>INF: hot-load new version, keep old loaded for rollback
    Note over INF: Rollback is a registry pointer change,<br/>not a redeploy. Seconds, not minutes.
```

Two points the ADD implies but does not sequence: the previous champion becomes a permanently-running challenger rather than being archived (which is what makes "was the change actually an improvement" answerable a month later), and rollback is a pointer flip because the old version is still loaded.

---

## 8. W7 — Kill switch trip and clear

```mermaid
sequenceDiagram
    autonumber
    participant SRC as Trigger source<br/>(any component or human)
    participant RK as Risk Engine
    participant T1 as Tier1 in-process
    participant T2 as Tier2 Redis
    participant T3 as Tier3 Postgres
    participant EX as Execution
    participant SUP as Supervisor
    participant NOT as Notification
    participant OP as Operator

    SRC->>RK: trip_killswitch(scope, reason, actor)
    RK->>T3: write HALTED (durable first)
    RK->>T2: write HALTED
    RK->>T1: set local flag
    RK-->>EX: cmd.platform.halt (fan-out, ack required)
    EX->>EX: set local flag immediately
    Note over EX: In-flight orders already sent are<br/>NOT cancelled. Cancelling into a fast market<br/>can be worse. They are tracked to completion.
    RK-->>SUP: evt.risk.killswitch.triggered
    SUP->>SUP: mode = HALTED
    RK-->>NOT: P0
    NOT->>OP: page + runbook

    Note over RK,EX: ORDER MATTERS: durable tier first.<br/>A crash mid-trip leaves the switch ON, not OFF.

    par Every order path, every request
        EX->>T1: check (in-process, ~0ms)
        EX->>T2: check (Redis, ~1ms)
        EX->>T3: check on token issuance (~5ms)
        Note over EX: ANY tier HALTED or unreachable = HALTED.
    end

    OP->>OP: investigate using the runbook
    OP->>RK: clear_killswitch(scope, typed_confirmation)
    alt trip was automatic
        RK->>RK: require SECOND approver
        Note over RK: Asymmetric authority: anyone can stop,<br/>two people restart after an automatic trip.
    end
    RK->>REC: require clean reconciliation before clearing
    REC-->>RK: clean
    RK->>T3: write ACTIVE
    RK->>T2: write ACTIVE
    RK->>T1: clear flag
    RK-->>EX: cmd.platform.resume
    RK-->>SUP: evt.killswitch.cleared
    SUP->>SUP: mode = NORMAL
```

Write order (durable tier first on trip) is not incidental. On clear, the order reverses: in-process last, so a partial failure leaves the switch engaged.

---

## 9. W8 — Data source degradation and failover

```mermaid
sequenceDiagram
    autonumber
    participant ING as Ingestion
    participant CB as Circuit Breaker
    participant P as Polygon
    participant D as Databento
    participant DQ as Quality
    participant SUP as Supervisor
    participant NOT as Notification

    ING->>P: fetch bars
    P--xING: 429 / 5xx / timeout
    ING->>CB: record failure (1 of 3)
    ING->>P: retry with jitter
    P--xING: fail (2 of 3)
    ING->>P: retry
    P--xING: fail (3 of 3)
    CB->>CB: state = OPEN
    ING-->>NOT: evt.market_data.source.degraded (P1)

    alt OHLCV, fallback available
        ING->>D: fetch same range from Databento
        D-->>ING: bars
        ING->>ING: tag source=databento, fallback=true
        ING->>DQ: forward with a cross-source consistency check
        DQ->>DQ: compare overlap with last Polygon bars
        alt divergence beyond tolerance
            DQ-->>NOT: P1. Providers disagree.
            DQ->>DQ: score down, FLAG not PASS
            Note over DQ: Downstream must discount.<br/>Two sources disagreeing is information,<br/>not something to average away.
        end
    else tick data, MT5 only, no fallback
        ING-->>SUP: no fallback for this feed
        SUP->>SUP: mode = DEGRADED for affected symbols only
        Note over SUP: Scoped degradation. Other symbols<br/>and paper accounts continue.
    end

    loop half-open probe every 60s
        CB->>P: single probe request
        alt success
            CB->>CB: state = HALF_OPEN, then CLOSED after 3 successes
            ING->>ING: backfill the gap, mark backfilled=true
            ING-->>NOT: P2 recovered
        end
    end
```

The cross-source consistency check on failover is an addition to page 01. Silently switching providers hides the case where they disagree, which is exactly when you most want to know.

---

## 10. W9 — Deployment with canary

```mermaid
sequenceDiagram
    autonumber
    participant DEV as Researcher
    participant CI as GitHub Actions
    participant REG as Artifact Registry
    participant STG as Staging
    participant SHD as Shadow
    participant OP as Operator
    participant PRD as Production

    DEV->>CI: push / PR
    CI->>CI: lint, type check, unit, contract tests
    CI->>CI: schema compatibility check (R01 section 7)
    CI->>CI: orphan/missing event check
    CI->>CI: clock lint (no direct datetime.now)
    CI->>CI: determinism test: replay twice, assert identical
    CI->>CI: PBO/DSR gate if models or params changed
    alt any gate fails
        CI--xDEV: blocked. No override path in the tool.
    end
    CI->>CI: build, SBOM, sign artefact
    CI->>REG: push signed image

    REG->>STG: deploy to staging
    STG->>STG: integration + simulated broker E2E
    STG->>STG: chaos: kill broker, kill Redis, kill NATS,<br/>assert fail-closed in every case

    alt change affects Committee, models, or risk logic
        REG->>SHD: deploy to shadow (live data, null broker adapter)
        SHD->>SHD: >= 24h and >= N decisions
        SHD-->>OP: comparison report
    end

    OP->>PRD: approve promotion (typed confirmation, audited)
    PRD->>PRD: stateless services: blue/green, instant switch
    PRD->>PRD: Execution: drain -> lease handover -> new leader
    Note over PRD: Execution is never blue/green.<br/>Two leaders means duplicate orders.

    alt change affects trading behaviour
        PRD->>PRD: CANARY BY CAPITAL: new logic gets<br/>10% of normal size for N trades
        PRD->>PRD: auto-rollback on: error rate,<br/>latency SLO breach, or realised slippage<br/>beyond the shadow-predicted band
    end
    PRD->>PRD: full rollout
```

Canary by *capital allocation* rather than by request percentage is the correct primitive here. Routing 10% of decisions to a new model tells you almost nothing at this decision volume; sizing every decision at 10% for N trades tells you what you need with bounded loss.

---

## 11. W10 — Disaster recovery

**Scenario:** total loss of the primary environment with open positions at the broker.
**RPO:** 0 for capital events (fills, orders). 5 minutes for market data. **RTO:** 30 minutes to `RECONCILING`, 60 minutes to `NORMAL`.

```mermaid
sequenceDiagram
    autonumber
    participant OP as Operator
    participant BR as Broker
    participant DR as DR environment
    participant BK as Backups (MinIO + PG)
    participant REC as Reconciliation
    participant SUP as Supervisor

    Note over OP: T+0 primary lost. Positions are LIVE at the broker.
    OP->>BR: MANUAL FIRST STEP: verify via the MT5 terminal<br/>directly that every open position has a stop.
    Note over OP,BR: This is why every entry carries a broker-side<br/>stop. It is the only protection that survives<br/>total platform loss.

    OP->>DR: provision DR environment
    DR->>BK: restore Postgres (PITR to last transaction)
    DR->>BK: restore MinIO/Iceberg (last snapshot)
    DR->>BK: restore NATS stream state
    DR->>DR: rebuild Ledger projection from ledger_events
    DR->>DR: assert invariants
    SUP->>SUP: mode = RECONCILING, ALLOW_TRADING = false
    DR->>BR: connect READ ONLY first
    REC->>REC: full diff: broker truth vs restored Ledger
    REC-->>OP: break report
    OP->>OP: resolve every break with dual control
    Note over OP: Any fills that occurred during the outage<br/>appear here as breaks. This is the RPO=0<br/>guarantee for capital: broker truth is the backstop.
    OP->>DR: typed confirmation to enable trading
    SUP->>SUP: mode = NORMAL
```

The critical insight: RPO 0 for capital events is achieved not by replication but by the broker being the authoritative record and reconciliation being able to reconstruct from it. That only works if reconciliation is a first-class service, which is the argument for C25.

---

## 12. W11 — Weekly learning review

```mermaid
sequenceDiagram
    autonumber
    participant SCH as Scheduler
    participant LRN as Learning
    participant AU as Decision Records
    participant LG as Ledger
    participant TCA as TCA Service
    participant VAL as Validation Gate
    participant OP as Operator

    SCH->>LRN: cmd.learning.run_review (misfire policy: fire immediately)
    LRN->>AU: fetch all decision records for the period
    LRN->>LG: fetch all trades and P&L
    LRN->>TCA: fetch execution quality
    LRN->>LRN: per-desk: stance vs outcome, Brier score,<br/>calibration curve
    LRN->>LRN: pairwise desk correlation (page 08's<br/>collusion-drift detector, now concrete)
    LRN->>LRN: failure clustering: where did realised<br/>outcome diverge most from pooled confidence
    LRN->>LRN: attribute P&L: decision quality vs<br/>execution quality vs sizing
    LRN->>LRN: generate falsifiable hypotheses (schema-enforced)
    LRN->>VAL: submit each hypothesis
    VAL->>VAL: PBO / DSR, same gate as any new strategy
    VAL-->>LRN: pass or fail per hypothesis
    LRN-->>OP: review report: what worked, what did not,<br/>which hypotheses passed, proposed changes
    Note over OP: Changes still require the W6 promotion path.<br/>Learning proposes. It never promotes.
```

---

## 13. Workflow coverage summary

| # | Workflow | Deadline | Fail-safe direction | Priority |
|---|---|---|---|---|
| W1 | Bar close to journalled trade | 12s | No trade | P0 |
| W2 | Position lifecycle | 500ms per action | Broker stop protects | P0 |
| W3 | Broker disconnect | reconnect ≤ 5min | Block entries, permit exits | P0 |
| W4 | Cold start | none | HALTED until every gate green | P0 |
| W5 | Graceful shutdown | 60s drain | Positions protected by broker stops | P1 |
| W6 | Model retraining | days | Champion keeps running | P1 |
| W7 | Kill switch | < 10ms trip | Fail closed | P0 |
| W8 | Source degradation | 3 failures to open | Scoped degradation | P1 |
| W9 | Deployment | 24h shadow | No override in the tool | P1 |
| W10 | Disaster recovery | RTO 60min | Broker truth is the backstop | P1 |
| W11 | Weekly review | weekly, fire-immediately on misfire | Learning cannot promote | P2 |

**Workflows still to be sequenced (P2):** quarantine review and force-release, limit-set change with dual control, symbol onboarding, prompt-version promotion, replay/rewind execution, standby VPS failover.

---

## 14. Related

- `R00_Executive_Review.md`
- `R01_Event_Architecture.md` (commands vs events visible in W1 and W7)
- `R05_Interface_Contracts.md` (degraded-mode fields these sequences realise)
- `R07_State_Machines.md` (states these sequences transition between)
- `R14_Deployment.md` (W9 in depth)
