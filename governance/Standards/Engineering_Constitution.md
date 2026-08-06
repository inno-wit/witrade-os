# WITrade OS Engineering Constitution

**Purpose:** the principles every implementation decision is held to, for the lifetime of this project. Where a principle conflicts with expedience, the principle wins — that is what makes it a constitution rather than a preference.
**Status:** Ratified alongside Architecture & Engineering Blueprint v1.0, 2026-08-05.

---

## 1. Architecture First

No code is written against an unspecified design. Every service, event, and interface implemented traces to a page in `../../Architecture/` or a document in `../../Blueprint/`. If the trace does not exist, the design work happens first, through an RFC (`../RFC/`), not retroactively documented after the code is already running.

## 2. Contracts Before Code

A component's six-field contract (Interfaces, Owns, Invariants, Degraded Mode, SLO, Security Boundary — `../../Architecture/contracts/README.md`) exists before its implementation begins. A contract written after the code exists tends to describe what the code happens to do, not what it should do.

## 3. Events Are APIs

An event subject is a public contract with the same seriousness as an HTTP endpoint. It has one owner, one schema, one version, and cannot change in a breaking way without the same governance an API change requires (`Versioning_Strategy.md`). `../../Architecture/freeze/Event_Governance_Matrix.md`'s 85-of-85 governed-subject discipline is not a freeze-time artefact, it is the standing rule.

## 4. Single Source of Truth

One fact, one canonical source (`../../Architecture/freeze/Canonical_Source_Validation.md`). A fact stated in two places is a fact that will eventually disagree with itself. This applies to documentation, to configuration, and to code: a type defined twice, a business rule encoded in two services, a constant duplicated across files, are all instances of the same failure mode.

## 5. Documentation Is Code

Documentation changes go through the same review discipline as code changes (`../Policies/Documentation_Governance.md`). It is versioned, reviewed, and required to pass CI (the cross-reference linter) before merge. Documentation that is easier to skip than code is documentation that will be skipped.

## 6. No Silent Breaking Changes

Every breaking change to a contract, event, schema, or API is announced by a major version bump (`../Policies/Versioning_Strategy.md`) and an ADR. "Silent" here means specifically: a change a consumer could not have detected by reading the version number alone.

## 7. Backward Compatibility

Additive by default. A new field is optional unless there is a stated reason it cannot be. A consumer built against version N of a contract continues to work against version N+1 unless the change is explicitly major.

## 8. Review Before Merge

No change to a frozen artefact merges without passing the Architecture Review gates (`../Review_Board/Architecture_Review_Process.md`). No implementation code merges without passing code review (`../Engineering_Handbook.md`).

## 9. Automated Testing Required

Every level in `../../Blueprint/Testing_Blueprint.md`'s 12-level hierarchy is wired into CI, not run manually and trusted to have happened. A test that only exists as a step in someone's memory does not count as coverage.

## 10. Observability By Default

Every service ships with health checks, metrics, structured logging, and tracing from its first commit (`../../Blueprint/Service_Catalog.md` §1's cross-cutting policy), not retrofitted once something breaks in production.

## 11. Security By Design

Threat modelling (`../../Architecture/21_Security_Architecture.md`) happens at design time, not as a pre-launch audit. Credential isolation, secrets management, and the prompt-injection corpus (`../../Blueprint/Production_Readiness.md` §3) are entry criteria for the phases that need them, not exit criteria bolted on afterward.

## 12. Explainability Before Automation

Every automated decision the platform makes is citable back to a deterministic input (ADR-0013, the Evidence Graph). A decision that cannot be explained is not shipped merely because it performs well in backtest.

## 13. Deterministic Before AI

The AI reasons, it does not calculate (ADR-0002, restated throughout `../../Architecture/ROADMAP.md` as the platform's single most load-bearing constraint). Any number the committee cites traces to a deterministic Python output. This principle has no tripwire, matching the ADR that establishes it.

## 14. Evidence Before Decisions

No trade recommendation is made without a citation chain into the Evidence Graph (ADR-0013, ADR-0041). A desk asserting a number it cannot trace is a defect, not a stylistic issue.

## 15. Risk Before Execution

The Risk Engine is the sole authorisation authority (ADR-0011). No execution path exists that bypasses it, including for testing, debugging, or manual override convenience — a manual override is itself a Risk-Engine-mediated action, never a side channel.

## 16. Implementation Must Match Blueprint

`../../Blueprint/Repository_Architecture.md`, `Package_Blueprint.md`, and `Service_Catalog.md` are not suggestions. The cross-service import linter (`Repository_Architecture.md` §3) enforcing "no service imports another service" is a constitutional rule expressed as a CI gate, not a style preference.

---

## What happens when a principle and a deadline conflict

The principle wins. A single-operator platform has no external stakeholder demanding a shortcut, which means the only pressure to violate one of these sixteen principles is self-imposed urgency — precisely the pressure this constitution exists to resist. If a genuine case exists for an exception, it goes through the RFC process like any other architectural proposal (`../RFC/`), and if accepted, it is recorded as an ADR, not taken quietly.

## Related

- `../README.md` — the governance system this constitution is the philosophical root of
- `Definition_of_Ready.md`, `Definition_of_Done.md` — this constitution made checkable, per unit of work
- `../../Architecture/ROADMAP.md` — "what must not erode," the architecture-specific list this constitution generalises into engineering-wide principles
- `../Engineering_Handbook.md` — where these principles become day-to-day workflow
