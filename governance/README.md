# WITrade OS Governance

**Scope:** the engineering governance system for WITrade OS, effective from Architecture & Engineering Blueprint v1.0's freeze (2026-08-04) onward.
**Relationship to `../Architecture/` and `../Blueprint/`:** those two directories are the frozen baseline this governance system protects. This directory does not restate their content (`../Architecture/freeze/Canonical_Source_Validation.md`'s one-fact-one-canonical-source rule applies here too) — it defines the process by which that baseline may change.
**Status:** Active, 2026-08-05.

---

## Why this exists

`../Architecture/` and `../Blueprint/` answer "what was designed and why." This directory answers a narrower, forward-looking question: **once implementation starts, how does the design evolve without drifting silently out of sync with the code, or the code drifting silently out of sync with the design.** The freeze certified 109 files, 43 ADRs, and 12 bounded contexts as internally consistent on one date. Governance is what keeps that true on every later date.

## The governing sequence

Every architectural change to WITrade OS, from this point forward, follows one path:

```
RFC -> Architecture Review -> ADR -> Implementation -> Documentation Update -> Release
```

No exceptions. `Policies/Implementation_Change_Control.md` states the rule; `RFC/`, `Review_Board/`, `ADR/` define each stage.

## Folder purposes

| Folder | Purpose |
|---|---|
| [`Architecture_Freeze/`](Architecture_Freeze/) | The frozen-baseline certificate this whole system protects, and any future dated freeze deltas (v1.1, v1.2...) |
| [`RFC/`](RFC/) | The RFC template, authoring guidelines, lifecycle states, and numbering scheme for proposing an architectural change |
| [`ADR/`](ADR/) | Governance rules for how ADRs are numbered, owned, reviewed, approved, and cross-referenced. The ADRs themselves stay in `../Architecture/decisions/` — this folder governs, it does not duplicate |
| [`Review_Board/`](Review_Board/) | The Architecture Review workflow: stages, gates, required reviewers |
| [`Standards/`](Standards/) | The Engineering Constitution, and the Definition of Ready / Definition of Done every unit of work is held to |
| [`Policies/`](Policies/) | Change control, versioning strategy, and documentation-drift prevention |
| [`Templates/`](Templates/) | One index of every template in this governance system, so a template is never duplicated across two locations |
| [`Decision_Log/`](Decision_Log/) | Where implementation-phase ADRs (0044 onward) get numbered and indexed, continuing `../Architecture/decisions/`'s register rather than forking it |
| [`Meeting_Notes/`](Meeting_Notes/) | Architecture Review Board session minutes, dated, append-only |
| [`Roadmap/`](Roadmap/) | The thirteen implementation gates (Gate 0 through Gate 12), each with entry/exit criteria, mapped onto `../Blueprint/Engineering_Roadmap.md`'s already-dependency-justified phase order |

## Root documents

- [`WITrade_OS_Implementation_v1.0_Program_Charter.md`](WITrade_OS_Implementation_v1.0_Program_Charter.md) — the executive document that closes the architecture phase, declares the freeze, and authorises implementation. Start here.
- [`Engineering_Handbook.md`](Engineering_Handbook.md) — the day-to-day reference for how work actually gets done: workflow, branching, review, testing, release, incidents.

## What this system is not

It does not re-litigate anything already decided in `../Architecture/decisions/0001`-`0043`. Those are Accepted and frozen. This system exists for the decisions *ahead*: the ones implementation will surface that the architecture phase, honestly, could not have anticipated (`../Architecture/freeze/Architecture_Freeze_v1.md` §9 says as much: "if Phase B discovers an architectural inconsistency serious enough to require a change to a frozen document, that discovery reopens this freeze with a new ADR").

## Related

- `../Architecture/freeze/Architecture_Freeze_v1.md` — the Phase A certification this governance system protects
- `../Blueprint/Engineering_Handoff_Report.md` — the combined Phase A + Phase B verdict this program charter formally closes out
- `../Blueprint/Engineering_Roadmap.md` — the dependency-justified implementation order `Roadmap/Implementation_Gates.md` maps onto
