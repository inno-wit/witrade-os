# RFC Guidelines

**Purpose:** how to write an RFC that an Architecture Review can actually evaluate, and when to write one at all.

---

## When an RFC is required

An RFC is required for any change that would touch a frozen artefact: `../../Architecture/*.md`, any file under `../../Architecture/decisions/`, `../../Architecture/contracts/`, `../../Blueprint/*.md`, or any cross-bounded-context interface, event schema, or API named in those documents.

An RFC is **not** required for:

- Implementation detail inside one service that does not change its published interface, event contract, or invariants.
- Bug fixes that restore documented behaviour (the documented behaviour is the spec; a bug is code disagreeing with an already-Accepted ADR, not a proposal to change one).
- Test additions, refactors that do not cross a bounded-context boundary, documentation typo fixes.

When genuinely unsure, default to writing the RFC. A rejected or unnecessary RFC costs a review cycle. A skipped one that turns out to have been necessary costs an undocumented architectural drift — the exact failure mode this whole governance layer exists to prevent (`../README.md`).

## What makes an RFC good

- **States the problem before the solution.** A proposed change section with no problem section is a solution looking for a justification.
- **Names the specific frozen artefact it touches.** "This changes how BC6 authorises orders" is reviewable. "This improves risk handling" is not.
- **Includes real alternatives.** If the RFC only presents one option, the review board cannot evaluate whether it is the *right* option, only whether it is *acceptable*. At minimum, include "do nothing" and state the cost of doing nothing.
- **Is honest about risk.** `../../Architecture/ROADMAP.md`'s "what must not erode" list (the deterministic/AI boundary, desk isolation, the kill switch's synchronous nature, exits never blocked, and the rest) is the standing checklist every RFC author should run their own proposal against before submitting. An RFC that touches one of the eight fixed-point ADRs (0015, 0016, 0017, 0019, 0022, 0023, 0035, 0037) should say so explicitly in Risks, not let a reviewer discover it.
- **Cites, not restates.** Link to the architecture page, ADR, or blueprint document being changed. Quoting it at length duplicates a canonical source and creates a second place that can drift out of sync (`../../Architecture/freeze/Canonical_Source_Validation.md`).

## Scope discipline

One RFC, one architectural change. An RFC that bundles "add a new bounded context" with "also rename three events for clarity" makes both harder to review and impossible to accept or reject independently. Split it.

## Numbering

See `RFC_Numbering.md`. Numbers are assigned at file creation, not at approval, so a withdrawn or rejected RFC still holds its number permanently (no renumbering, ever — this mirrors the ADR register's own discipline of never reusing a number).

## Authoring checklist before submitting

- [ ] Problem section names a real gap, not a preference
- [ ] At least two alternatives considered, with "do nothing" as a baseline
- [ ] Every claimed fact traces to a cited file, not to memory or assumption
- [ ] Impact section is filled in completely, including "none" where genuinely none
- [ ] Checked against the eight fixed-point ADRs and the "what must not erode" list
- [ ] Filed under the correct bounded context(s) in the RFC index

## Related

- `RFC_Template.md` — the file to copy
- `RFC_Lifecycle.md` — what happens after submission
- `RFC_Numbering.md` — how numbers are assigned
- `../Review_Board/Architecture_Review_Process.md` — the review this feeds into
