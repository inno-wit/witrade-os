# Documentation Governance

**Purpose:** the rule that no implementation change lands without its documentation updated in the same change, stated as a policy rather than left as an expectation.

---

## The rule

**No documentation drift is permitted.** Every implementation change that touches a frozen artefact must update, in the same change (not a follow-up ticket), every one of the following that applies:

| Document class | Location | Updated when |
|---|---|---|
| Architecture | `../../Architecture/*.md` | The change alters a component's purpose, responsibilities, inputs, outputs, dependencies, or failure modes |
| Blueprint | `../../Blueprint/*.md` | The change alters repository layout, service catalog, deployment, testing, or observability plan |
| RFC | `../RFC/` | Status transition only (`../RFC/RFC_Lifecycle.md`) — the RFC itself is not rewritten post-acceptance |
| ADR | `../../Architecture/decisions/` | A new ADR is added, or an existing one gets its `Superseded by` line (`../ADR/ADR_Governance.md`) |
| Contracts | `../../Architecture/contracts/`, and at implementation time `witrade/contracts/` | The six-field contract (Interfaces, Owns, Invariants, Degraded Mode, SLO, Security Boundary) changes |
| Event Catalog | `../../Architecture/freeze/Event_Governance_Matrix.md`, `../../Blueprint/Event_Blueprint.md` | Any event subject's schema, owner, or publisher changes |
| API Catalog | `../../Blueprint/API_Blueprint.md` | Any endpoint is added, changed, or removed |
| Testing Documentation | `../../Blueprint/Testing_Blueprint.md` | A new test level, suite, or CI gate is added |
| Runbooks | `../../Blueprint/Observability_Blueprint.md`'s operational set | A new P0/P1 alert exists, or an existing runbook's steps change |
| Release Notes | Per `../Engineering_Handbook.md` release workflow | Every release, without exception |

## Why "in the same change," not a follow-up

A follow-up documentation ticket is the single most common way governance systems decay: the code ships, the ticket gets deprioritised, and six months later the documentation describes a system that no longer exists. `../../Architecture/freeze/Architecture_Cross_Reference_Report.md` and the freeze's own zero-broken-hyperlinks, zero-duplicate-fact discipline exist precisely because this platform's design intent is meant to survive a decade of single-operator maintenance (`../../Architecture/decisions/README.md`'s stated reasoning for why ADRs exist at all). A documentation debt that is allowed to accrue even briefly tends not to get repaid.

## Enforcement

1. **Change control:** `Implementation_Change_Control.md`'s "Affected Documents" field is not optional, and a change control record cannot close with an affected document left unedited.
2. **CI:** the cross-reference/integrity linter (`../../Blueprint/Testing_Blueprint.md` §6, closing TD8) checks link resolution and duplicate-fact detection on every commit that touches `../../Architecture/` or `../../Blueprint/`.
3. **Review:** a pull request touching a frozen artefact's *behaviour* without a corresponding documentation diff is rejected at code review (`../Engineering_Handbook.md`), the same way a PR without a linked ADR is rejected under `Implementation_Change_Control.md`.

## Corrections versus changes

Not every documentation edit is a "change" requiring the full RFC chain. A **correction** — fixing a typo, a broken link, a citation format inconsistency (e.g., TD5's 23 loose backtick citations, `../../Blueprint/Technical_Debt_Register.md`) — restates an already-true fact more accurately and does not require an ADR. A **change** alters what is claimed to be true and always requires one. When genuinely ambiguous, treat it as a change — the cost of an unnecessary ADR is far lower than the cost of an undocumented architectural drift disguised as a "typo fix."

## Related

- `Implementation_Change_Control.md` — the change-control record this policy's obligations attach to
- `Versioning_Strategy.md` — the version bump a documentation change may trigger
- `../../Blueprint/Technical_Debt_Register.md` — TD5, TD7, examples of documentation debt this policy exists to prevent accumulating further
- `../Engineering_Handbook.md` — code review and release workflow, where this policy is enforced day to day
