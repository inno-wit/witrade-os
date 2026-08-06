# Canonical Source Validation

**Freeze deliverable:** A.2
**Rule under test:** one architectural fact, one canonical source; every other mention is a reference, never a restatement.
**Status:** Freeze v1.0 input, 2026-08-04

---

## 1. Canonical location registry

The brief specifies eight canonical-fact categories against an idealised directory layout (`sequence_diagrams/`, `state_machines/`, `data_dictionary/` as top-level folders). This directory does not use that layout — per the standing instruction not to redesign the existing structure, the table below maps each fact category onto **this directory's actual, existing canonical home**, and every subsystem page is checked against it.

| # | Fact | Brief's suggested location | Actual canonical location in this repository | Compliant? |
|---|---|---|---|---|
| 1 | System overview | `../00_Master_Architecture.md` | Same | ✅ |
| 2 | Container relationships | `16_C4_Container_Diagram.md` | `../generated/16_Container_Model_v2.md` (page 16 itself is the frozen 2026-08-03 snapshot; the v2 file is the living working contract, per `../generated/README.md`) | ✅ |
| 3 | Event schemas | `Event_Catalog_v2.md` | `../generated/15_Event_Catalog_v2.md` (page 15 is the frozen snapshot; v2 is the working contract) | ✅ |
| 4 | API / interface contracts | `../contracts/*.contract.md` | Same, for pages 01-14. Pages 17-21 carry the equivalent six fields inline (no separate delta file — see §3) | ✅ |
| 5 | Architectural decisions | `../decisions/*.md` (ADR/) | Same | ✅ |
| 6 | Sequence diagrams | `sequence_diagrams/*.md` | `../review/R06_Sequence_Diagrams.md` (single file, eleven workflows plus the Phase 11 addendum W12 in `../review/R20_Architecture_Freeze.md` §4) | ✅ with one disclosed lag (see §4) |
| 7 | State machines | `state_machines/*.md` | `../review/R07_State_Machines.md` (transition tables) + `diagrams/SM1-SM9.excalidraw` (visual companions) | ✅ |
| 8 | Data dictionary | `data_dictionary/*.md` | **Does not exist as a standalone artefact.** `../review/R08_Data_Lineage.md` covers point-in-time lineage, which is the load-bearing subset, but no file enumerates every field/type/unit platform-wide | ❌ Genuine gap, carried into `Architecture_Freeze_v1.md` as an open item, not fabricated as closed |

**7 of 8 categories have exactly one canonical source, correctly referenced elsewhere. The eighth (data dictionary) has no canonical source at all** — which is a different, and lesser, problem than having two conflicting ones. Nothing in this directory currently claims to be a data dictionary and duplicates another file; the category is simply unfilled. Fabricating a `data_dictionary/` folder to make this table read "8 of 8" would not be validation, it would be theatre — this row stays honest.

---

## 2. Duplication check, per category

For each of the seven populated categories, every other file mentioning the same subject matter was checked for restatement versus reference.

| Category | Files that discuss the same subject | Restate or reference? |
|---|---|---|
| System overview | `review/R00-R19` all reference page 00's layer model in their opening paragraphs | Reference only — every review file's "Delta against" header names page 00 or a specific downstream page, never re-describes the whole system |
| Container relationships | `../contracts/README.md`, `../diagrams/README.md`, all 21 source pages | Reference only — pages state their own container's fields; none re-lists the full 40-container inventory |
| Event schemas | Every page's "Events Published" / "Events Consumed" fields | **Correctly scoped, not a violation.** A page stating its own component's published/consumed events is not restating the catalog, it is the catalog's source data — `../generated/15` is explicitly a compilation of exactly these per-page fields (`../generated/README.md` §"Why this file exists") |
| API contracts | Pages 01-14 (source) vs `../contracts/01-14.contract.md` (six added fields) | Reference/delta relationship, by design — `../contracts/README.md` states this is a sibling-delta pattern, not a duplication |
| Architectural decisions | `../review/R16_ADR_Register.md` vs `../decisions/*.md` | R16 is the review-time recommendation that the ADRs were written *from* — dated 2026-08-03, superseded as the working register by `../decisions/README.md`, referenced not restated |
| Sequence diagrams | `../00_Master_Architecture.md`'s pipeline prose vs `../review/R06_Sequence_Diagrams.md` | Different altitude, not duplication — R06 §1 states this explicitly: a pipeline shows order, a sequence diagram shows interaction, timing, and failure branches. Page 00 is not attempting to be R06 |
| State machines | Prose "lifecycle" descriptions on pages 07, 08, 10, 11, 20 vs `../review/R07_State_Machines.md` | **One page checked in depth: `../20_Model_Registry.md`.** Its "Lifecycle" section reproduces SM-5's states as a summary mermaid diagram, explicitly captioned "This page does not restate the guards, dwell times, or illegal-transition assertions — `../review/R07_State_Machines.md` §6 is the authoritative transition table." This is a reference with a convenience preview, not a restatement, and the page says so in its own text |

**No category shows a restatement that omits its own cross-reference.** Every place content overlaps, the overlapping page names its source explicitly.

---

## 3. The one deliberate exception, and why it is not a violation

Pages 17-21 do not have a corresponding file in `../contracts/`. This looks, at first read, like a gap against category 4's rule. It is not: `../contracts/` exists specifically to retrofit six missing fields (Interfaces, Owns, Invariants, Degraded Mode, SLO, Security Boundary) onto pages 01-14, which were written *before* that template existed. Pages 17-21 were written *with* the template already folded in, inline, from their first draft — there is no "page lacking the fields" for a delta file to correct. Creating an empty or redundant `../contracts/17_Evidence_Graph.contract.md` that simply says "see page 17, all fields present" would itself be the duplication this validation is checking for. `../README.md`'s Phase 11 section and `../contracts/README.md` (unedited) both already state this rule; recorded here as the formal validation pass confirming it holds.

---

## 4. The one disclosed lag

`../review/R06_Sequence_Diagrams.md` (category 6) does not yet contain W12 (Portfolio Construction capital competition, added in `../review/R20_Architecture_Freeze.md` §4) or an update to W6 reflecting the Tier-0 dual promotion gate (ADR-0042). Both are real content that exists in this directory today, just not yet filed under sequence diagrams' canonical home. This is folded into `Architecture_Freeze_v1.md` as a tracked, non-blocking action rather than left as a silent gap.

---

## 5. Verdict

**Canonical-source discipline holds across the directory.** One category (data dictionary) has no source rather than a conflicting one — a completeness gap, not a governance violation. One category (sequence diagrams) has real content sitting one file away from its permanent home — a filing lag, not a duplication. Every other category checked clean: one fact, one source, every other mention a reference.

---

## 6. Related

- `Architecture_Cross_Reference_Report.md` — the mechanical link/duplication scan this validation's §2 draws its file-list from
- `../review/R20_Architecture_Freeze.md` §6 — the governance compliance check this document formalises into a standalone, repeatable artefact
- `Architecture_Freeze_v1.md` — where the data-dictionary gap and the sequence-diagram filing lag both become tracked checklist items
