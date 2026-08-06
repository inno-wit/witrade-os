# Engineering Handbook

**Purpose:** the day-to-day reference for how work actually gets done on WITrade OS, once implementation starts. Where `Standards/Engineering_Constitution.md` states principles and `Roadmap/Implementation_Gates.md` states phase-level gates, this handbook states the concrete, weekly-use mechanics.
**Status:** Active from Program Charter ratification, 2026-08-05.

---

## 1. Development Workflow

1. Confirm the work item passes `Standards/Definition_of_Ready.md` before starting.
2. If the work touches a frozen artefact, confirm an `Accepted` ADR already authorises it (`ADR/ADR_Governance.md`) — implementation does not start mid-RFC.
3. Branch (see §2), implement against the six-field contract and any interface/event schema already governed.
4. Every service change ships with health checks, metrics, logging, tracing from its first commit (`../Blueprint/Service_Catalog.md` §1) — not a follow-up task.
5. Confirm the work item passes `Standards/Definition_of_Done.md` before requesting review.

## 2. Branching Strategy

- `main` — always deployable to `dev`. Never force-pushed, never rewritten.
- `feature/<gate>-<slug>` — one branch per unit of work, scoped to one gate's deliverable (`Roadmap/Implementation_Gates.md`).
- No long-lived branches spanning more than one gate. A branch that outlives its gate is a signal the work was scoped too large — split it.
- Merges to `main` are squash-merged with a commit message citing the ADR (if any) and the gate.

## 3. Code Review Process

- No implementation code merges without at least one review pass against `Standards/Engineering_Constitution.md`'s sixteen principles, specifically: does this change import across a `services/*` boundary (principle 16, CI-enforced), does it introduce an undocumented breaking change (principle 6), does it add observability (principle 10).
- Any PR touching `../Architecture/` or `../Blueprint/` requires the authorising ADR number in the PR description; missing it is a hard rejection (`Policies/Implementation_Change_Control.md`).
- Any PR touching a fixed-point ADR's territory (0015, 0016, 0017, 0019, 0022, 0023, 0035, 0037) gets a second, explicit read against that ADR's own text before approval, regardless of how small the diff looks.

## 4. Architecture Compliance

- The cross-service import linter and the cross-reference/documentation-integrity linter (`../Blueprint/Testing_Blueprint.md` §6) run on every commit, not just at merge time.
- A build that edits a frozen document's content without a corresponding ADR reference fails, by design (`Policies/Implementation_Change_Control.md`).
- See the Architecture Compliance Checklist, §11 below, for the pre-release version of this check.

## 5. Testing Requirements

- Every one of the 12 levels in `../Blueprint/Testing_Blueprint.md` is wired into CI; a level that exists only as a manual step does not count as implemented.
- Safety-critical paths (kill switch, authorisation, exit handling) require their named chaos/fail-closed test passing before merge, not before release.
- Point-in-time correctness (Feature Store, Evidence Graph, Ledger) requires the look-ahead-bias / replay-determinism test as a permanent CI gate, per `../Blueprint/Engineering_Roadmap.md` Phase 5's stated risk mitigation.

## 6. Documentation Requirements

- Every change satisfying `Policies/Documentation_Governance.md`'s trigger table updates the named documents in the same PR, not a follow-up.
- Release notes are written at release time, not reconstructed afterward from commit history.

## 7. Release Workflow

1. All gate-relevant acceptance criteria met (`Roadmap/Implementation_Gates.md`).
2. Contract/event/API version bumps applied per `Policies/Versioning_Strategy.md` for any breaking change in this release.
3. Promotion through environments per `../Blueprint/Deployment_Blueprint.md`: `dev -> ci -> paper`, and only `paper -> prod` once Gate 12 (`Roadmap/Implementation_Gates.md`) and `../Blueprint/Production_Readiness.md`'s full checklist are satisfied for the specific service being promoted.
4. Rollback plan confirmed working (not merely written) before any `prod`-bound release — blue/green for stateless services, lease handover tested for singleton services (Risk, Execution, Ledger, OMS, Reconciliation, Scheduler).
5. Release notes published, documentation updated, `Templates/README.md`'s change-control record closed.

## 8. Incident Reporting

- Any incident touching a safety-critical path (kill switch, unprotected position, authorisation bypass-shaped bug) is written up regardless of whether it reached `prod` — a `paper`-environment near-miss on one of these paths is exactly the kind of signal `../Architecture/ROADMAP.md`'s "what must not erode" list exists to protect.
- Incident write-up references the runbook that was or should have been followed (`../Blueprint/Observability_Blueprint.md`), and closes with either a confirmation the runbook worked or an RFC to fix the runbook.
- A P0/P1 incident whose root cause is an architectural gap (not an implementation bug) triggers an RFC, not just a patch — the distinction from `Policies/Documentation_Governance.md`'s "correction versus change" applies here too.

## 9. Operational Handover

- Single-operator platform (ADR-0009): "handover" here means handover across time (a future self resuming after a gap), not across people. Every runbook, dashboard, and this handbook itself is written assuming the reader has forgotten the last six months of context, per the same reasoning `../Architecture/decisions/README.md` gives for why ADRs exist at all.
- If ADR-0009's tripwire is ever crossed (multi-tenancy becomes real), a genuine multi-person handover process is itself an RFC-worthy addition to this handbook, not an assumption baked in now.

## 10. Architecture Compliance Checklist (pre-release)

- [ ] Every change in this release traces to an `Accepted` ADR, or is fast-path-eligible per `Policies/Implementation_Change_Control.md`.
- [ ] Every affected document from `Policies/Documentation_Governance.md`'s trigger table is updated.
- [ ] No cross-`services/*` import exists that the linter did not already catch (spot-check).
- [ ] No fixed-point ADR (0015, 0016, 0017, 0019, 0022, 0023, 0035, 0037) was touched without an explicit, reviewed exception.
- [ ] `../Blueprint/Technical_Debt_Register.md` reflects this release's actual state: closed items removed, new debt logged.
- [ ] Version bumps applied per `Policies/Versioning_Strategy.md` wherever a contract, event, or API changed.

## Related

- `Standards/Engineering_Constitution.md` — the principles this handbook operationalises day to day
- `Roadmap/Implementation_Gates.md` — the phase-level structure this handbook's release workflow plugs into
- `Policies/Implementation_Change_Control.md`, `Policies/Documentation_Governance.md`, `Policies/Versioning_Strategy.md` — the three policies this handbook's workflow enforces
- `../Blueprint/Testing_Blueprint.md`, `../Blueprint/Deployment_Blueprint.md`, `../Blueprint/Observability_Blueprint.md` — the implementation-level detail this handbook references rather than restates
