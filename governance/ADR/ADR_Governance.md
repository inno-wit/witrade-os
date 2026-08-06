# ADR Governance

**Purpose:** the rules governing how ADRs are numbered, owned, reviewed, approved, and cross-referenced, going forward from the v1.0 freeze.
**The ADRs themselves live in `../../Architecture/decisions/`, not here.** This document governs that directory's growth from `0044` onward; it does not duplicate the 43 existing records. One fact, one canonical source (`../../Architecture/freeze/Canonical_Source_Validation.md`).
**Format:** unchanged from the existing standard — lightweight MADR plus a mandatory `## Tripwire` section, exactly as established in `../../Architecture/decisions/README.md` and verified 43/43 compliant in `../../Architecture/freeze/ADR_Index.md`.

---

## Lifecycle

| Status | Meaning |
|---|---|
| **Proposed** | Drafted, not yet reviewed. New state going forward — all 43 existing ADRs skipped this because architecture-phase ADRs were decided and accepted in the same pass; implementation-phase ADRs, arriving from RFCs one at a time, go through it properly. |
| **Accepted** | Reviewed, approved, in force. Implementation may proceed against it. |
| **Superseded** | A later ADR replaces this one's decision. The old ADR is never deleted or edited — a `Superseded by ADR-NNNN` line is added at the top, and the new ADR's Context section names what it supersedes and why. |
| **Deprecated** | The decision no longer applies (e.g., the component it governed was removed) but was not replaced by a new decision. |
| **Rejected** | Proposed and declined. Kept, not deleted, as a record of a considered and declined option. |
| **Merged** | Folded into another ADR because two proposals turned out to be the same decision viewed from two angles. |

Transitions: `Proposed -> Accepted | Rejected`, `Accepted -> Superseded | Deprecated`. No other transitions are valid — an ADR does not go from `Superseded` back to `Accepted`; if the old decision is correct again, a new ADR restating it is written instead, so the historical record of "we tried reversing this and reverted" stays intact.

## Numbering

Continues the existing sequence: **`0044` is the next ADR number.** Global, sequential, never reused, never reordered — identical rule to `../RFC/RFC_Numbering.md`. Numbers are assigned when an ADR is created (state `Proposed`), not at `Accepted`.

Every ADR generated from an Accepted RFC (`../Review_Board/Architecture_Review_Process.md` stage 6) must state, in its Context section, which RFC it originated from (`Originating RFC: RFC-NNNN`).

## Ownership

Same as the existing 43: **Fredrick Kimeu**, sole decider of record, per ADR-0009's single-operator architecture. The `Deciders:` field is filled in even though it names one person, for consistency with the existing register and to keep the field meaningful if the platform ever crosses ADR-0009's own tripwire into a multi-operator model.

## Review

An ADR generated from an RFC has already passed the four review stages in `../Review_Board/Architecture_Review_Process.md` (Review, Technical Validation, Impact Analysis, Approval) before it is written. Writing the ADR is not itself a review step — it is the formal record of a review already completed. An ADR written **without** a preceding RFC (permitted only for genuinely small, non-architectural clarifications — see `../Policies/Implementation_Change_Control.md` §"Fast path") still requires the same Tripwire discipline and still gets logged in `../Decision_Log/README.md`.

## Approval

An ADR is `Accepted` only when:

1. It has a `## Tripwire` section (mandatory, no exception — the mechanical check `../../Architecture/freeze/ADR_Index.md` §5 ran against all 43 existing ADRs applies identically going forward).
2. It cites every existing ADR it touches, supersedes, or depends on.
3. If it supersedes an existing Accepted ADR, that ADR is updated with a `Superseded by ADR-NNNN` header line — the one place an existing "frozen" ADR file is touched post-freeze, and only ever to add this one line, never to alter its original content.

## Cross-References

- An ADR that changes behaviour specified in a `../../Architecture/*.md` page or a `../../Blueprint/*.md` document must name that document explicitly, so `../Policies/Documentation_Governance.md`'s update obligation has an unambiguous target.
- An ADR that touches an event subject, interface, or API must name it by its canonical identifier (event subject string, interface name) as it appears in `../../Architecture/freeze/Event_Governance_Matrix.md` / `../../Blueprint/Interface_Definitions.md` / `../../Blueprint/API_Blueprint.md`, not a paraphrase.
- Bidirectional linking: the new ADR links back to the ADR(s) it affects, and — since existing frozen ADRs are otherwise not edited — the affected ADR gets its one-line `Superseded by` addition where applicable, or is left untouched with the new ADR carrying the relationship instead.

## Repository Standards

- File location: `../../Architecture/decisions/NNNN-slug.md`, unchanged.
- The running register `../../Architecture/decisions/README.md` is updated with every new ADR — same file, same table shape, extended not replaced.
- `../Decision_Log/README.md` (this governance system's own index) tracks implementation-phase ADRs (`0044`+) specifically, cross-linking back to the canonical register rather than forking it.
- Quarterly tripwire review: `../../Architecture/decisions/README.md`'s own stated intent ("cannot begin until at least one quarter of live operation exists," per `../../Architecture/freeze/ADR_Index.md` §5) is inherited unchanged by this governance system. The first quarterly review uses `ADR_Index.md` as its dated starting point.

## Related

- `../../Architecture/decisions/README.md` — the canonical, living ADR register
- `../../Architecture/freeze/ADR_Index.md` — the freeze-time certification this governance system extends
- `../RFC/RFC_Lifecycle.md`, `../RFC/RFC_Numbering.md` — how an ADR is born, from RFC to Accepted
- `../Review_Board/Architecture_Review_Process.md` — the review stages an ADR-generating RFC already passed
- `../Decision_Log/README.md` — where implementation-phase ADRs are indexed going forward
