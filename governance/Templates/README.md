# Templates

**Purpose:** one index of every template in this governance system, so a template is never authored twice in two places and drifts out of sync with itself.

---

## The templates, and where each actually lives

| Template | Canonical location | Used for |
|---|---|---|
| RFC | [`../RFC/RFC_Template.md`](../RFC/RFC_Template.md) | Proposing any change to a frozen artefact |
| ADR | `../../Architecture/decisions/` — see any existing file (e.g., [`0043-portfolio-construction-is-a-twelfth-bounded-context.md`](../../Architecture/decisions/0043-portfolio-construction-is-a-twelfth-bounded-context.md)) for the live MADR + Tripwire shape | Recording an architectural decision, numbered `0044` onward per [`../ADR/ADR_Governance.md`](../ADR/ADR_Governance.md) |
| Component contract (6-field) | `../../Architecture/contracts/README.md` | Specifying Interfaces, Owns, Invariants, Degraded Mode, SLO, Security Boundary for a component |
| Meeting minutes | [`../Meeting_Notes/README.md`](../Meeting_Notes/README.md) | Recording an Architecture Review Board session |
| Definition of Ready checklist | [`../Standards/Definition_of_Ready.md`](../Standards/Definition_of_Ready.md) | Entry gate for a unit of work |
| Definition of Done checklist | [`../Standards/Definition_of_Done.md`](../Standards/Definition_of_Done.md) | Exit gate for a bounded context |
| Change control record | [`../Policies/Implementation_Change_Control.md`](../Policies/Implementation_Change_Control.md) | Documenting an implementation change's references (RFC, ADR, affected artefacts) |

## Why this folder holds no template files itself

Every template above already has a natural home: the RFC template belongs next to the RFC lifecycle and numbering rules that govern it, the ADR shape belongs next to the 43 live examples of it, the contract template belongs next to the 14 contracts already written against it. Copying any of them into `Templates/` a second time would violate this program's own one-fact-one-canonical-source rule (`../../Architecture/freeze/Canonical_Source_Validation.md`) — the exact discipline this governance system exists to uphold going forward. This folder is the index, not a second copy.

## Related

- `../README.md` — the full governance folder structure this index sits inside
- `../../Architecture/freeze/Canonical_Source_Validation.md` — the rule this folder's design follows
