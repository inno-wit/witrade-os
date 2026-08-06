# Architecture Review Process

**Purpose:** the workflow an RFC moves through between submission and a decision, with gates and required reviewers stated explicitly rather than left implicit.
**Board composition:** WITrade OS is single-operator, single-tenant (ADR-0009). The Architecture Review Board (ARB) is Fredrick Kimeu, acting deliberately in the distinct roles below rather than as one undifferentiated reviewer — the roles exist so each RFC gets evaluated from more than one angle even without a multi-person team, the same discipline `../../Architecture/review/`'s R00-R20 corpus already modeled as a structured multi-pass review rather than one pass.

---

## Stages

### 1. Proposal

The RFC exists in `Draft` (`../RFC/RFC_Lifecycle.md`). Author checks it against `../RFC/RFC_Guidelines.md`'s authoring checklist before submission.

**Gate to pass 1 → 2:** every RFC template section is filled in (no "TBD" left in Problem, Proposed Change, Alternatives, Risks, or Impact).

### 2. Review

The RFC moves to `In Review`. Read against the frozen baseline it claims to change: does the Problem section accurately describe a real gap in `../../Architecture/` or `../../Blueprint/`, not a misreading of it.

**Required reviewer role:** Chief Software Architect — checks internal consistency against the 12 bounded contexts and 43 existing ADRs.

**Gate to pass 2 → 3:** the RFC's claimed "Current Behaviour" is verified accurate by re-reading the cited source document, not assumed correct because the author said so.

### 3. Technical Validation

Does the Proposed Change actually solve the stated Problem, and is it technically sound against the platform's own standing constraints: the deterministic/AI boundary, event-vs-command distinction (ADR-0037), fail-closed default (ADR-0025), point-in-time correctness (ADR-0034).

**Required reviewer role:** Technical Program Manager — checks the Implementation Plan section is sequenced against `../Roadmap/Implementation_Gates.md` correctly (does it depend on a gate that has not yet closed).

**Gate to pass 3 → 4:** no unresolved conflict with an existing Accepted ADR without that ADR being explicitly named as superseded in the RFC.

### 4. Impact Analysis

Full pass over the Impact section: every affected interface, event, API, bounded context, test suite, and runbook named, none silently missed. Cross-checked against `../../Blueprint/Interface_Definitions.md`, `../../Architecture/freeze/Event_Governance_Matrix.md`, and `../../Blueprint/Technical_Debt_Register.md` for whether this RFC touches a context already carrying known debt (e.g., BC2/BC7, TD1).

**Required reviewer role:** Engineering Governance Lead — checks the RFC does not silently touch one of the eight fixed-point ADRs (0015, 0016, 0017, 0019, 0022, 0023, 0035, 0037) without explicitly flagging it as such.

**Gate to pass 4 → 5:** Impact section is complete and every fixed-point-ADR intersection is explicitly disclosed.

### 5. Approval

The RFC's `Approval Status` is set to `Accepted` or `Rejected`, with the `Decision` section filled in (one paragraph, the actual reasoning, not a restatement of the proposal). If Rejected, the RFC closes per `../RFC/RFC_Lifecycle.md`. If Accepted, proceed to stage 6.

**Gate to pass 5 → 6:** a dated decision recorded in both the RFC file and `../Meeting_Notes/`.

### 6. ADR Generation

An Accepted RFC is translated into a new ADR, numbered continuing `../../Architecture/decisions/0001`-`0043` (see `../Decision_Log/README.md`), in the same MADR + Tripwire format every existing ADR uses (`../ADR/ADR_Governance.md`). The ADR is what actually authorises implementation, not the RFC — the RFC is the proposal, the ADR is the record.

**Gate to pass 6 → 7:** ADR Status is `Accepted`, has a `## Tripwire` section (mandatory, per the existing 43/43 standard), and cites the RFC it originated from.

### 7. Implementation Authorisation

Implementation may begin, scoped exactly to what the ADR states. `../Policies/Implementation_Change_Control.md` governs from here.

### 8. Documentation Update

Every document named in the RFC's Impact section is updated to reflect the change: the relevant `../../Architecture/` page or `../../Blueprint/` document, never left to drift (`../Policies/Documentation_Governance.md`).

**Gate to pass 8 → 9:** zero documents named in Impact remain unedited.

### 9. Architecture Freeze Update

If the change is significant enough to affect the certified baseline counts (ADR count, bounded context count, event subject count, container count), a new dated freeze delta is filed in `../Architecture_Freeze/` (e.g., `Architecture_Freeze_v1.1.md`), never an edit to `Architecture_Freeze_Certificate_v1.0.md` in place.

---

## Approval gates, summarised

| Gate | Between stages | Owner |
|---|---|---|
| G1 | Proposal → Review | Author self-check |
| G2 | Review → Technical Validation | Chief Software Architect |
| G3 | Technical Validation → Impact Analysis | Technical Program Manager |
| G4 | Impact Analysis → Approval | Engineering Governance Lead |
| G5 | Approval → ADR Generation | Architecture Review Board (final call) |
| G6 | ADR Generation → Implementation Authorisation | ADR Status verification |
| G7 | Documentation Update → Freeze Update | Change-control closeout |

## Related

- `../RFC/RFC_Lifecycle.md` — the state machine this process drives
- `../ADR/ADR_Governance.md` — stage 6 in full detail
- `../Policies/Implementation_Change_Control.md` — the end-to-end policy this process is the review half of
- `../Meeting_Notes/README.md` — where each session's decisions are minuted
