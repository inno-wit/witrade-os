# Definition of Done

**Purpose:** the checklist a bounded context (or a service within one) must pass before it is considered complete, for the lifetime of this program. Applies uniformly across all 12 bounded contexts (`../../Architecture/19_Bounded_Context_Map.md`) — no context gets a lighter bar because it shipped early or a heavier one because it shipped late.

---

## A bounded context is Done when:

### Implementation matches design
- [ ] Every container/service listed for this bounded context in `../../Blueprint/Service_Catalog.md` is implemented and deployed per its stated scaling strategy.
- [ ] Every invariant in the component's contract (`../../Architecture/contracts/`) is enforced in code, with a test proving the enforcement, not merely documented.
- [ ] Every event this context publishes matches its governed schema exactly (`../../Architecture/freeze/Event_Governance_Matrix.md`); every event it consumes is handled per its documented failure mode.

### Testing (per `../../Blueprint/Testing_Blueprint.md`'s 12 levels)
- [ ] Unit, integration, and contract tests exist and pass in CI for every component in this context.
- [ ] If this context sits on a safety-critical path, the fail-closed chaos suite passes for every one of its documented degraded-mode transitions.
- [ ] If this context touches point-in-time correctness (feature serving, evidence graph, ledger), the look-ahead-bias / replay-determinism test passes: byte-identical output across two runs with the same seed.
- [ ] Zero known regressions in dependent contexts caused by this context's own test suite.

### Observability
- [ ] `GET /healthz` and `GET /readyz` implemented for every service in this context (`../../Blueprint/Service_Catalog.md` §1).
- [ ] Prometheus `/metrics` emitting the four golden signals plus this context's own domain SLI.
- [ ] Structured logging with `correlation_id`/`causation_id` propagated on every event this context touches (ADR-0037).
- [ ] Every tripwire metric this context owns (`../../Architecture/decisions/README.md`'s tripwire table) is instrumented and has a dashboard panel (`../../Blueprint/Observability_Blueprint.md`).
- [ ] A runbook exists for every P0/P1 alert this context can raise.

### Documentation
- [ ] `../../Architecture/` and `../../Blueprint/` reflect the as-built system, not the as-designed one, wherever implementation revealed a difference (via the RFC/ADR chain, per `../Policies/Documentation_Governance.md`).
- [ ] The Technical Debt Register (`../../Blueprint/Technical_Debt_Register.md`) is updated: closed items removed or marked resolved, new debt discovered during implementation added.

### Security
- [ ] Every P0 control from `../../Architecture/21_Security_Architecture.md` §8 relevant to this context is live.
- [ ] Credential isolation verified, if this context touches secrets or broker access.
- [ ] Secrets scanning clean across the context's code, history, and any built images.

### Deployment
- [ ] The context's services pass their promotion gates through `dev -> ci -> paper` per `../../Blueprint/Deployment_Blueprint.md`, with rollback tested, not merely planned.
- [ ] Blue/green (stateless services) or lease-handover (singleton services) verified for every service in this context.

### Governance
- [ ] Every ADR this context's implementation generated is `Accepted` and cross-referenced (`../ADR/ADR_Governance.md`).
- [ ] No change to a frozen artefact happened outside the RFC → Review → ADR chain (spot-checked via the cross-reference linter's audit trail).

## Gate-level Done versus context-level Done

A bounded context can be internally Done by this checklist while its gate (`../Roadmap/Implementation_Gates.md`) is not yet closed, if the gate's exit criteria include something beyond this context alone (e.g., a cross-context integration test). Gate exit criteria are the authoritative closing condition for a *phase*; this document is the authoritative closing condition for a *context*.

## `prod` is a separate, later bar

This Definition of Done governs `paper`-environment completeness. Promotion from `paper` to `prod` is a distinct, later gate, governed by `../../Blueprint/Production_Readiness.md`'s full 15-category checklist — a context can be Done here and still not be cleared for live capital.

## Related

- `Definition_of_Ready.md` — the matching entry checklist
- `Engineering_Constitution.md` — the principles this checklist operationalises
- `../Roadmap/Implementation_Gates.md` — gate-level exit criteria, which include but exceed this per-context checklist
- `../../Blueprint/Production_Readiness.md` — the further bar for live capital, beyond this document's scope
