# Versioning Strategy

**Purpose:** one versioning rule per artefact class, so "v1.0" means the same kind of thing wherever it appears in this program.

---

## Architecture and Blueprint

**Whole-document-set versioning, not per-file.** `Architecture & Engineering Blueprint v1.0` is one version number covering all 109 architecture files and 15 blueprint documents as a certified, internally-consistent set (`../Architecture_Freeze/Architecture_Freeze_Certificate_v1.0.md`). A change that would otherwise be a patch to one file instead produces a new whole-set version:

- **Major (v2.0):** a change to a fixed-point ADR, a new or removed bounded context, or any change that invalidates a prior freeze's certified counts in a way that changes the platform's fundamental shape.
- **Minor (v1.1, v1.2...):** an additive change: a new ADR that does not supersede a fixed point, a new page, a closed technical-debt item (e.g., BC2/BC7 finally getting dedicated pages), a new event subject.
- **No patch level.** Architecture documents are not code; a "typo fix" that changes no fact is not a version bump at all (see Documentation Governance for the distinction between a correction and a change).

Every version beyond v1.0 is a **new dated file** in `../Architecture_Freeze/` (`Architecture_Freeze_v1.1.md`, etc.), never an edit to `Architecture_Freeze_Certificate_v1.0.md` in place — this is the same rule `../../Architecture/freeze/Architecture_Freeze_v1.md` §8 already states for the architecture layer itself, inherited unchanged.

## RFCs

Not versioned; numbered (`../RFC/RFC_Numbering.md`). An RFC that needs substantial rework after review is superseded by a new RFC number, never edited into a "v2" of itself while `In Review`.

## ADRs

Not versioned; numbered, with `Status: Superseded` as the mechanism for evolution (`../ADR/ADR_Governance.md`). An ADR is never "ADR-0011 v2" — a changed decision is a new ADR number that supersedes the old one.

## Contracts, Events, Schemas

**Semantic versioning**, per `../../Architecture/decisions/0040-schema-registry-is-the-wire-contract.md`'s existing schema-registry-as-wire-contract decision:

- **Major:** a breaking change to an event's field types, a removed field, or a changed meaning of an existing field.
- **Minor:** an additive, backward-compatible change: a new optional field, a new event subject.
- **Patch:** documentation or description-only changes to a schema, no wire-format change.

Every schema version is registered in the Schema Registry (C37, `../../Architecture/decisions/0040-schema-registry-is-the-wire-contract.md`) at implementation time; this policy states the rule the registry enforces mechanically once it exists.

## APIs

Semantic versioning per endpoint group, following the same major/minor/patch logic as Contracts above. A major API version bump requires an RFC (it is, by definition, a breaking change crossing a bounded-context boundary).

## Documentation

Documentation version tracks the artefact it documents. `../../Blueprint/*.md` documents are versioned identically to the architecture set they describe (whole-set, not per-file) since they are one certified deliverable (`../../Blueprint/Engineering_Handoff_Report.md`).

## Implementation (code)

Deferred to the Engineering Handbook (`../Engineering_Handbook.md` — Release Workflow), since code versioning is a normal software-release concern, not an architecture-governance one. This policy's only claim on code versioning: **a release that includes a breaking change to a contract, event, or API must bump that contract/event/API's own version per this document, independent of the code repository's own release tag.**

## Related

- `../Architecture_Freeze/Architecture_Freeze_Certificate_v1.0.md` — the v1.0 baseline this strategy versions forward from
- `../ADR/ADR_Governance.md`, `../RFC/RFC_Numbering.md` — the numbering (not versioning) schemes for those two artefact classes
- `Implementation_Change_Control.md` — where a version bump is triggered
- `../../Architecture/decisions/0040-schema-registry-is-the-wire-contract.md` — the ADR this contract/event versioning rule implements
