# ADR-0005: Choreography for data flow, one orchestrated saga for the decision cycle

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** orchestration, messaging, foundational

---

## Context

Page 00 lists "Temporal versus a custom DAG runner" as an open question and defers it. Deferred workflow decisions do not stay deferred: they get made by whoever writes the first pipeline, on the day, with no context. The result is usually a mixture of both patterns applied inconsistently, which is the worst outcome available.

The platform has four distinguishable flow types, and treating them as one problem is what makes the question look hard:

1. **Data pipeline.** Ingest → quality → features → regime/volatility/structure. Each stage's output is the next stage's trigger. No stage needs to know what happens after it. No compensation is meaningful: a failed feature materialisation is retried, not rolled back.
2. **Decision cycle.** Trigger → assemble evidence → poll six desks → reach consensus → issue proposal → authorise → execute. This has a **deadline** (the whole cycle is worthless after `valid_until`), a **terminal state that must be recorded** (including `DEADLOCKED` and `EXPIRED`), and **partial-failure semantics** that matter (four of six desks answered: proceed or abort?).
3. **Long-running human-gated flows.** Deployment promotion, quarantine review, risk-limit change. Timers measured in hours or days, with a human task in the middle.
4. **Scheduled jobs.** Nightly stress tests, weekly learning review, retraining.

These have genuinely different requirements, and the mistake is picking one tool for all four.

## Options considered

**A. Full orchestration (Temporal) for everything.**
*Pros:* one model; durable timers; visibility into every flow; retries and compensation for free.
*Cons:* a substantial new runtime (server plus workers plus its own datastore) to operate for a solo operator; every data-pipeline stage gains a workflow definition it does not need; it couples the entire data path to Temporal's availability; the learning curve is real.

**B. Full choreography for everything.**
*Pros:* no coordinator, maximum decoupling, nothing extra to run.
*Cons:* the decision cycle has no home for its deadline, no terminal state, and no way to answer "what is the state of cycle X right now." Debugging a cycle becomes reconstructing it from a log. Deadlock and expiry become emergent behaviours rather than recorded states, which is unacceptable for something that must be audited.

**C. Split by flow type.** Choreography for data, one custom saga for the decision cycle, Postgres plus a scheduler for the rest, with a tripwire to Temporal.
*Pros:* each flow gets the pattern that fits; nothing new to operate; the saga is small enough to own; the deadline semantics can be exactly what R17 requires rather than what a framework offers.
*Cons:* two patterns to understand; the saga runner is code to write and maintain (~300 lines); it must not grow into a general-purpose workflow engine by accretion.

## Decision

**Option C.**

| Flow type | Pattern | Implementation |
|---|---|---|
| **Data pipeline** (ingest → quality → features → engines) | **Choreography.** Each stage reacts to the previous stage's event. No central coordinator. | NATS consumers only. No workflow engine. |
| **Decision cycle** | **Orchestration.** A defined saga with a deadline, compensation, and a recorded terminal state. | A **Decision Cycle Saga** owned by the Decision Service. One Postgres row per `cycle_id`, driven by an explicit state machine (R07 §3). |
| **Long-running human-gated flows** | **Orchestration with timers and human tasks.** | Postgres plus the scheduler. **Deferred; this is the only genuine Temporal use case.** |
| **Scheduled jobs** | **Commands from a scheduler**, never events. | The Scheduler emits `cmd.<ctx>.run_job.v1` addressed to the owning service (ADR-0037). |

Binding constraints on the saga runner:

1. **It orchestrates exactly one workflow type: the decision cycle.** A second workflow type is not added to it. If a second one appears, that is the signal to evaluate Temporal, not to generalise the runner.
2. **State is a Postgres row**, transitioned explicitly, with every transition recorded. The current state of any cycle is a single-row query.
3. **The deadline is owned by the saga**, not by the participants. On `valid_until` expiry the saga terminates the cycle as `EXPIRED` and emits `evt.decision.expired.v1`, regardless of what any participant is still doing (D3, R17 §2).
4. **Terminal states are exhaustive and final:** `PROPOSAL_ISSUED`, `NO_ACTION`, `DEADLOCKED`, `EXPIRED`, `ABORTED`. A cycle is never reopened. A revision is a new cycle with a `supersedes` link.
5. **Compensation is defined per step.** The only step with a real-world side effect is order placement, and its compensation is a cancel or a flatten routed through the OMS, never a silent retry.
6. **The saga is driven by the injected `Clock`** (ADR-0035), so a full decision cycle replays deterministically in simulation.

## Rationale

The split follows from a single observation: **choreography cannot express a deadline, and orchestration is dead weight where there is no deadline.**

The data pipeline has no deadline. A bar that arrives late is processed late; nothing is invalidated. Choreography is exactly right, and adding a coordinator would add a failure mode with no compensating benefit.

The decision cycle is defined by its deadline. A proposal issued after `valid_until` is not a late proposal, it is a wrong one, and acting on it moves capital on stale information. Something must own that deadline, must be able to abort participants, and must record why the cycle ended. That is an orchestrator, and it needs to be one whose deadline semantics are precisely specified rather than inherited.

Building the saga rather than adopting Temporal is justified by scope: **one workflow type, roughly 300 lines, over a database that already exists.** Temporal's value is in durable timers and visibility across many long-running workflows, and there is currently one workflow that completes in eleven seconds. Adopting it now would be adopting the operational cost without the workload.

Constraint 1 is the load-bearing one. Custom workflow engines fail by accretion: a second workflow type, then a third, then retry policies, then timers, and eventually a worse Temporal that one person maintains. Naming the second workflow type as the tripwire is what prevents that.

## Consequences

**Positive**
- Nothing new to operate.
- The decision cycle's deadline and terminal states are exactly what R17 and the audit requirement need, with no framework impedance.
- The data path stays fully decoupled and has no coordinator to fail.
- The saga replays deterministically under `SimulationClock`, so a full decision cycle is testable end to end without a broker or an LLM.

**Negative**
- A saga runner to write, test and maintain.
- Two patterns in the codebase, which must be documented so that new flows are placed deliberately rather than by whichever example was read first.
- No out-of-the-box workflow visibility UI. The saga's state table plus the correlation ID in the event envelope (R01 §4) covers the need, but it is built rather than inherited.

**Neutral**
- The scheduler exists either way.

## Tripwire

Adopt **Temporal** when there are **three or more long-running, human-gated workflow types**. The plausible three are: deployment promotion, quarantine review, and risk-limit change (ADR-0024). All three are P1 or later, so this is a real and reachable condition rather than a theoretical one.

A second tripwire, distinct and earlier: **if any workflow type other than the decision cycle is added to the custom saga runner**, stop and evaluate Temporal rather than extending the runner.

## Related

- ADR-0004 (NATS JetStream) supplies the choreography substrate
- ADR-0035 (clock injection) is what makes the saga replayable
- ADR-0037 (commands vs events) governs scheduled jobs
- `../review/R01_Event_Architecture.md` §13
- `../review/R07_State_Machines.md` §3
- `../review/R17_Performance.md` §2 (decision TTL, finding D3)
- Source: `../00_Master_Architecture.md` (Open Questions)
