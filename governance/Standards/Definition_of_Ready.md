# Definition of Ready

**Purpose:** the checklist a unit of engineering work must pass before implementation starts on it. Scoped to one service, one bounded context, or one gate deliverable (`../Roadmap/Implementation_Gates.md`).

---

## A unit of work is Ready when:

### Architectural grounding
- [ ] The frozen `../../Architecture/` page(s) and `../../Blueprint/` document(s) it implements are named explicitly, not assumed.
- [ ] Every ADR it depends on is `Accepted` (check `../../Architecture/freeze/ADR_Index.md` or, for implementation-phase ADRs, `../Decision_Log/README.md`).
- [ ] If it requires new architectural decisions, those have already cleared the RFC → Architecture Review → ADR chain (`../Review_Board/Architecture_Review_Process.md`) — work does not start mid-design.

### Contract clarity
- [ ] The component's six-field contract exists (Interfaces, Owns, Invariants, Degraded Mode, SLO, Security Boundary — `../../Architecture/contracts/`).
- [ ] Every event it publishes or consumes is a governed subject in `../../Architecture/freeze/Event_Governance_Matrix.md`, or its addition has already gone through Event governance.
- [ ] Every synchronous interface it exposes or calls is defined in `../../Blueprint/Interface_Definitions.md`.

### Dependency readiness
- [ ] Every upstream bounded context or gate this work depends on has actually closed (`../Roadmap/Implementation_Gates.md` entry criteria for the relevant gate), not merely "mostly done."
- [ ] `packages/kernel` and `packages/schemas` (`../../Blueprint/Repository_Architecture.md`) already contain every shared type this work needs, or their addition is itself scoped as a prerequisite task.

### Testability
- [ ] Acceptance criteria are stated as a test that can pass or fail, not a subjective judgement call.
- [ ] The relevant test level(s) from `../../Blueprint/Testing_Blueprint.md`'s 12-level hierarchy are identified for this work specifically.
- [ ] If the work touches a safety-critical path (kill switch, authorisation, exit handling — `../../Architecture/ROADMAP.md`'s "what must not erode"), the specific chaos/fail-closed test it must pass is named up front, not discovered during review.

### Risk disclosure
- [ ] Known technical debt intersecting this work is checked against `../../Blueprint/Technical_Debt_Register.md` and either resolved first or explicitly accepted as a carried risk.
- [ ] If this work touches one of the eight fixed-point ADRs (0015, 0016, 0017, 0019, 0022, 0023, 0035, 0037), that intersection is flagged before work starts, not found during code review.

### Scope
- [ ] The unit of work is scoped to one gate's deliverable list (`../Roadmap/Implementation_Gates.md`), not spanning multiple gates in a way that makes partial completion ambiguous.

## What Ready is not

Ready does not mean "fully specified down to every line of code." Implementation detail inside a service's private boundary is expected to be worked out during implementation, not pre-decided (Engineering Constitution principle 1 governs the architectural boundary, not the internals). Ready means the *interface* the work must honour, and the *test* that proves it honoured it, are both settled before the first line is written.

## Related

- `Definition_of_Done.md` — the matching exit checklist
- `Engineering_Constitution.md` — the sixteen principles this checklist operationalises
- `../Roadmap/Implementation_Gates.md` — the gate-level entry criteria this checklist applies per unit of work within
- `../../Blueprint/Testing_Blueprint.md` — the test hierarchy referenced above
