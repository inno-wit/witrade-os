# ADR-0008: Docker Compose over Kubernetes

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** infrastructure, operations

---

## Context

The corrected architecture specifies **39 containers** across 2 to 3 hosts (R02 §3), up from the 15 listed in page 16. Thirty-nine containers is comfortably past the number at which people reach for Kubernetes by reflex.

The relevant facts:

- **2 to 3 hosts**, not a fleet. Two Linux (37 containers) and one to two Windows (the MT5 terminal plus the execution bridge, which cannot be containerised on Linux, R13 §7).
- **One operator**, who is also the trader and the developer.
- **No autoscaling requirement.** Load is driven by bar closes, which are perfectly predictable. There is no traffic spike to absorb.
- **No multi-tenancy** (ADR-0009).
- Deployment is human-gated (page 14), not continuous.

Note: R13 §8 references this decision as "ADR-009". The register in R16 §3 assigns 008 to orchestration and 009 to tenancy, and this file follows the register.

## Options considered

**A. Docker Compose.**
*Pros:* trivial to operate and reason about; profiles map cleanly onto the six environments; health checks, restart policies, resource limits and dependency ordering are all supported; the entire deployment is a readable file; a laptop can run the full stack, which makes `dev` real.
*Cons:* no self-healing across hosts; no rolling deploy primitive; multi-host requires either Swarm or manual placement; secret handling is weaker.

**B. Kubernetes (k3s or managed).**
*Pros:* the industry standard; self-healing; rolling deploys and readiness gates; declarative and auditable; horizontal scaling; strong secret handling; a large ecosystem.
*Cons:* a substantial operational surface (control plane, CNI, ingress, storage classes, RBAC) for one person; the failure modes require real expertise to diagnose under stress, which is precisely when they will be encountered; it does not solve the Windows host, so a second deployment mechanism is needed anyway; the primary benefits (autoscaling, multi-host scheduling, multi-tenancy) are all things this platform does not need.

**C. Nomad.**
*Pros:* considerably simpler than Kubernetes; genuinely handles Windows workloads, which is a real advantage here; single binary.
*Cons:* smaller ecosystem; still a scheduler to operate; the Windows benefit is thin when there is exactly one Windows workload that is pinned to its host by an MT5 terminal login.

## Decision

**Option A: Docker Compose**, with a defined tripwire to Kubernetes.

Requirements that hold **regardless** of orchestrator, and which are the substance of this decision:

| Requirement | Reason |
|---|---|
| **Resource limits on every container** | One runaway backtest must not starve the Risk Engine. This is a correctness requirement, not tidiness |
| **Restart policy `unless-stopped` for stateless, `on-failure` with a limit for stateful** | A crash-looping ledger service must stop and alert, not restart forever and mask the fault |
| **Health checks wired to real readiness endpoints** | A container that is up but not ready must not receive traffic (R12 §7) |
| **Explicit dependency ordering** | Postgres and NATS before everything; Instrument Master before Risk; Ledger before Risk |
| **Separate networks per trust zone** | The capital segment is not reachable from the edge (R02 §2) |
| **Pinned image digests, never tags** | `:latest` in a trading system is how an unreviewed change reaches production |
| **One Compose profile per environment** | `dev`, `sim`, `shadow`, `paper`, `prod`. Paper must be structurally identical to prod, not a subset |

The Windows host runs the bridge as a Windows Service via `nssm` (page 14's existing choice, which is correct) and is deployed by its own pipeline. This split is unavoidable and is not an argument for either orchestrator.

## Rationale

Container **count** is the wrong metric. What justifies an orchestrator is **host count, scheduling need, and operator count**, and all three point the same way here: 2 to 3 hosts with fixed placement, no autoscaling, one operator.

Thirty-nine containers on two Linux hosts with static placement is a Compose problem. Compose has resource limits, health checks, restart policies, dependency ordering and network segmentation, which is the full list of what this platform actually requires from an orchestrator.

The decisive argument against Kubernetes is not its setup cost, which is a one-off. It is that its **failure modes require expertise to diagnose under stress.** A solo operator debugging a CNI issue or a stuck finalizer at 3am, while positions are open, is a materially worse outcome than the self-healing was ever going to be worth. Operational complexity that only one person can resolve, who is also the person trading, is a risk concentrated in exactly the wrong place.

Kubernetes also does not remove the Windows problem. The MT5 terminal is pinned to a host by its broker login and cannot be scheduled. A second deployment mechanism is needed either way, so the "one orchestrator for everything" benefit does not materialise.

Nomad is the closest call and would be a reasonable choice. It is rejected as an unnecessary component: it would be a scheduler operated for a workload with nothing to schedule.

## Consequences

**Positive**
- The full stack runs on a laptop, so `dev` is a real environment rather than an approximation.
- The whole deployment is a readable file that one person can hold in their head.
- Nothing to learn beyond Docker.
- Debugging is `docker logs` and `docker exec`, which work under stress.

**Negative**
- No automatic cross-host failover. Mitigated where it matters: the Execution bridge failover is handled by the leader lease (R13 §7), which is a better mechanism than a scheduler restart anyway because it is correctness-aware.
- No rolling-deploy primitive. Blue/green for stateless services is scripted rather than declarative (R14). Acceptable given human-gated deployment.
- Secret handling is weaker. Addressed separately by SOPS plus age (ADR-0031 adjacent, R04 §4), not by the orchestrator.
- Multi-host Compose means manual placement. At 2 to 3 hosts this is a config file, not a problem.

**Neutral**
- Container images, health endpoints and resource limits are identical under either choice, so the migration path stays open. Nothing in the application layer knows which orchestrator runs it.

## Tripwire

Migrate to **Kubernetes (k3s first)** when **any** of these becomes true:

1. **More than 3 hosts** need coordinated scheduling.
2. **Horizontal autoscaling** becomes necessary (i.e. load stops being bar-close-driven and predictable).
3. **More than one person** operates the platform.
4. **Multi-tenancy arrives** (ADR-0009 is superseded).

Condition 3 is the most likely and the most often overlooked. Compose's weaknesses (manual placement, scripted deploys, weak secret handling) are all cheap for one person and expensive for a team.

## Related

- ADR-0009 (single-tenant) shares tripwire condition 4
- ADR-0001 (Python) shares the "right size for one operator" reasoning
- `../review/R13_Infrastructure.md` §7, §8
- `../review/R14_Deployment.md`
- `../review/R18_Technical_Debt.md` A1
- Source: `../13_Infrastructure_Platform.md`, `../14_Deployment_Pipeline.md`
