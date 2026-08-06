# 14 — Deployment Pipeline, contract completion

**Delta against:** `../14_Deployment_Pipeline.md` (unmodified)
**Adds:** Owns, Invariants, Interfaces, Degraded Mode, SLO, Security Boundary
**Containers:** CI/CD (GitHub Actions) + C26 Platform Supervisor (mode gating) · **Context:** Delivery / Platform Ops (BC10)
**Highest-value field for this page (R05 §11):** **Invariants.** "A gate bypass is impossible without a logged administrative override"

---

## What page 14 gets right, and must not be lost

- **Gates enforced in CI/CD tooling, not by convention or code review discipline.** A bypass requires an explicit logged administrative override, not a fast-path button. The page names gate bypass under time pressure as its top failure mode and then designs against it, which is the correct order.
- **The PBO/DSR gate applies to changes proposed by Continuous Learning**, explicitly and without exception.
- **`ALLOW_TRADING` off by default**, paper by default, explicit typed confirmation to go live.
- **Shadow mode fed the same live data as production** via a read-only tap, rather than a separate stale source.
- **The single-VPS risk named honestly** rather than assumed away.

The corrections are: make the override mechanically logged rather than procedurally logged, add environments the pipeline needs and does not have, and make rollback a defined operation rather than an assumption.

## Owns

| Asset | Note |
|---|---|
| `releases`, `deployments` (Postgres) | One row per artefact per environment |
| `gate_results` | Every gate evaluation, pass or fail, with the evidence |
| `overrides` | Every administrative bypass, immutable |
| `shadow_runs`, `shadow_comparisons` | |
| Container registry tags | Immutable, digest-addressed |

## Six environments, not four

Page 14's pipeline is Research → CI/CD → Cloud → VPS → MT5 → Dashboard, which conflates environment with host. The environments the platform actually needs:

| Env | Purpose | Broker adapter | Real capital |
|---|---|---|---|
| `dev` | Local development | Simulated | No |
| `sim` | Deterministic historical replay, PBO/DSR generation | Simulated | No |
| `shadow` | Live data, live decisions, **no orders** | Null adapter | No |
| `paper` | Live data, real broker, demo account | MT5 (demo) | No |
| `prod` | Live data, real broker, real account | MT5 (live) | **Yes** |
| `dr` | Standby, warm | MT5 (live), lease-held | Only on failover |

`shadow` and `paper` are different environments doing different jobs, and page 14 has neither as a first-class concept. Shadow proves a change produces the decisions you expected. Paper proves the whole path executes. A change that clears shadow can still fail in paper on order mechanics, and one that clears paper can still be a bad decision.

## Invariants

1. **Every gate is a required status check. A bypass is possible only through a mechanically logged administrative override** that records actor, reason, artefact, gate skipped, and timestamp, immutably. Page 14 states this intent; the invariant is that the override path is the **only** bypass and that it cannot execute without writing its record.
2. No artefact reaches `prod` that did not pass through `sim`, `shadow`, and `paper` in that order. Environment skipping is itself an override.
3. **Every deployment is digest-addressed and immutable.** Tags never move. `latest` does not exist in any manifest.
4. Every deployment is reversible to the previous digest by a single command, with a **tested** rollback path. An untested rollback is not a rollback.
5. `ALLOW_TRADING` is off by default in every environment including `prod`. Enabling it is a separate, audited, typed-confirmation action from deploying.
6. A change touching the order path, risk rules, or limits requires **manual operator approval**, and the approval names the specific change rather than approving a batch.
7. Any change affecting committee behaviour (prompt, model pin, desk weight, consensus strategy) requires a shadow run of at least 24 hours with a recorded comparison before promotion eligibility.
8. **Deployment is blocked while the platform is not in `NORMAL`.** Deploying into a `HALTED` or `RECONCILING` platform is how an incident acquires a second cause.
9. Schema changes deploy before the code that produces them, and consumers upgrade before producers publish a new major. Dual-publish for one full release cycle.
10. **The kill switch is never deployed, restarted, or reconfigured in the same change as anything else.** It has its own release path and its own verification.
11. Every release records the exact commit, dependency hashes, model versions, prompt versions, and limit-set version live at deploy time. **Reconstructing what was running at any past moment is a query, not an investigation.**

Invariant 10 exists because of a specific, plausible sequence: the kill switch is part of the Risk Engine, the Risk Engine is deployed with a routine change, the deployment briefly restarts the service, and during that window the interlock is not answering. Under invariant 9 of the risk contract that means HALTED and is safe, which is precisely why the kill switch must never be the thing that a routine deploy quietly takes with it.

## Interfaces

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Gate | `pbo_dsr_gate(artefact) -> GateResult` | Yes | 4h | CI |
| Gate | `test_gate(commit) -> GateResult` | Yes | 10m | CI |
| Gate | `schema_compat_gate(commit) -> GateResult` | Yes | 2m | CI |
| Gate | `clock_lint_gate(commit) -> GateResult` | Yes | 1m | CI |
| Gate | `shadow_gate(artefact, hours) -> GateResult` | Yes | 48h | CI |
| Command | `promote(artefact, from_env, to_env, approver)` | Yes | 5m | operator for prod-facing |
| Command | `rollback(env, to_digest, actor, reason)` | Yes | 5m | operator, audited |
| Command | `override(gate, artefact, actor, reason)` | Yes | 1s | **operator, immutable record, alerts** |
| Command | `enable_trading(env, actor, typed_confirmation)` | Yes | 1s | operator, audited, separate from deploy |

`override` alerting on execution rather than on review is the detail that makes it work. An override that only appears in a log is an override nobody sees until the post-mortem; one that pages on use is one that gets explained the same day.

The clock lint gate is a one-line CI check that fails the build on any direct `datetime.now()`, `time.time()`, `asyncio.sleep()`, or `pd.Timestamp.now()` outside `platform/clock.py`. It costs almost nothing and permanently protects replay determinism, which erodes within weeks without mechanical enforcement and is invisible for months afterwards (ADR-0035, no tripwire: this lint is never suppressed).

## Degraded Mode

| Condition | Behaviour |
|---|---|
| CI unavailable | **No deployments.** No manual path to production exists. Deploying past an unavailable gate is the same act as bypassing a working one |
| Registry unreachable | Deployment fails, running services unaffected |
| Shadow environment unavailable | Committee-affecting changes cannot promote. Other changes proceed |
| Platform not in `NORMAL` | **All deployment blocked** (invariant 8). Override requires operator plus reason |
| Deployment fails mid-rollout | Auto-rollback to the previous digest, alert. **Never leave a partial rollout in place** |
| VPS unreachable during deploy | Bridge deployment aborts. **The old bridge keeps its lease and keeps running.** A failed deploy must never leave the order path with no live sender |
| Rollback fails | P0 page. `dr` standby is the escalation, gated on a clean reconciliation before it takes the lease |
| Post-deploy reconciliation fails | **Auto-rollback and halt.** A deployment that leaves the book disagreeing with the broker is reverted before anything else is investigated |

The VPS row is the operationally important one. The bridge is the single Windows-bound container and the only holder of broker credentials, so a botched deploy there is the failure with real capital exposure. The lease makes the safe behaviour automatic: a new bridge that cannot start never acquires the lease, and the old one keeps sending.

## SLO

| Dimension | Target |
|---|---|
| CI test gate | p95 < 10 minutes (page 14's target, retained) |
| Full pipeline, `dev` to `paper` | p95 < 2 hours excluding shadow soak |
| Shadow soak | ≥ 24 hours for committee-affecting changes |
| Rollback | **< 5 minutes to previous digest, tested monthly** |
| **Correctness** | **Zero deployments to `prod` without a complete gate record.** Zero moved tags |
| **Correctness** | **Zero overrides without an immutable record and an alert** |
| Correctness | Zero deployments while the platform is not `NORMAL`, absent a recorded override |
| Reconstructability | 100% of past moments reconstructible to exact versions (invariant 11) |
| **Health** | **Override count per quarter. A rising count means the gates are wrong or the process is, and either way it is a finding** |

The override-count SLO is the one that keeps invariant 1 honest over years. A gate that is overridden monthly is not a gate; it is a speed bump with paperwork. Counting the overrides is what turns "we have gates" into a claim that can be checked.

## Security Boundary

| | |
|---|---|
| **Zone** | CI runs outside every production zone. It **pushes artefacts**, it does not reach into production to configure it |
| **Deploy credentials** | Short-lived, issued per deployment via OIDC federation. **No long-lived deploy key exists anywhere** |
| **Secrets in CI** | None that reach production. CI cannot read C38. Services fetch their own secrets at runtime with their own identity |
| **Broker credentials** | Never present in CI, never in an image layer, never in a manifest. Fetched at runtime by the C24 identity only |
| **Approvals** | Prod-facing promotion requires an operator identity from C39 with MFA. **The approver is recorded and cannot be a service account** |
| **Override authority** | Operator only, MFA, immutable record, alert on use |
| **Artefact integrity** | Images signed, digests pinned, SBOM per build. Deployment verifies the signature before starting a container |
| **Single-operator reality** | Dual control means a **delay plus a written justification** rather than a second person. That is weaker than two humans and it is what is available. It is recorded as a known limitation, not presented as equivalent |

The last row is deliberately blunt. Several controls in this architecture assume two people, and there is one. Time-delayed self-approval with a written justification captures most of the value of dual control (it defeats the impulsive change, which is the common failure) and none of the value against a determined mistake by the only person with authority. Writing that down now is what stops it being quietly forgotten and later described as four-eyes approval in a document nobody re-reads.

---

## Related

- Source page, unmodified: `../14_Deployment_Pipeline.md`
- `13_Infrastructure_Platform.contract.md` — the substrate this pipeline deploys onto
- `12_Continuous_Learning.contract.md` — the gate applied to the loop's own proposals
- `../generated/16_Container_Model_v2.md` §5 — the Bridge group and the lease
- `../review/R14_Deployment.md` — 6 environments, 4 deployment tracks, canary by capital, DR
- `../decisions/0035-clock-injection.md` — the clock lint gate, never suppressed
- `../decisions/0024-risk-limits-are-versioned-dual-controlled-artefacts.md` — the dual-control limitation
- `../decisions/0030-prompts-are-versioned-point-in-time-artefacts.md` — invariant 7
