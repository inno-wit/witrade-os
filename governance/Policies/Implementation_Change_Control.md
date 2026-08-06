# Implementation Change Control

**Purpose:** the rule that no implementation may modify architecture directly, and what an implementation change must reference to be legitimate.

---

## The rule

**No implementation change may alter architecture directly.** Every implementation change that touches a frozen artefact must trace back through the governance chain: `RFC -> Architecture Review -> ADR -> Implementation -> Documentation Update -> Release`. A pull request that changes cross-context behaviour with no RFC or ADR behind it is out of process, regardless of how small or obviously correct it looks — smallness and obviousness are exactly the conditions under which undocumented drift accumulates unnoticed (`../README.md`'s stated reason this system exists).

## What every implementation change must reference

| Reference | Required when |
|---|---|
| **RFC** | The change originated from one (almost all cross-context changes) |
| **ADR** | Always, for any change to frozen behaviour — this is the actual authorisation, not the RFC |
| **Affected Documents** | Every `../../Architecture/*.md` or `../../Blueprint/*.md` file the change touches |
| **Affected Interfaces** | Any interface in `../../Blueprint/Interface_Definitions.md` whose contract changes |
| **Affected Events** | Any event subject in `../../Architecture/freeze/Event_Governance_Matrix.md` whose schema, owner, or publisher changes |
| **Affected APIs** | Any endpoint in `../../Blueprint/API_Blueprint.md` |
| **Affected Bounded Contexts** | Named explicitly by BC number (BC1-BC12) |
| **Affected Tests** | The test suite(s), by level, per `../../Blueprint/Testing_Blueprint.md` |
| **Affected Runbooks** | Any runbook in `../../Blueprint/Observability_Blueprint.md`'s operational set |

A change control record with any of the above left blank is incomplete, not "not applicable" by default — "none" must be stated explicitly, the same discipline the RFC template already enforces (`../RFC/RFC_Template.md`).

## Fast path (small, non-architectural changes)

Not every code change needs an RFC. The fast path applies when **all** of the following hold:

1. The change does not alter any published interface, event schema, or API contract.
2. The change does not cross a bounded-context boundary.
3. The change does not touch any of the eight fixed-point ADRs (0015, 0016, 0017, 0019, 0022, 0023, 0035, 0037).
4. The change restores documented behaviour (a bug fix) rather than proposing new behaviour.

Fast-path changes still require: a linked ADR if they establish a new implementation-level convention worth remembering (e.g., a naming pattern), otherwise just a normal code review per `../Engineering_Handbook.md`. When in doubt whether a change qualifies for the fast path, it does not — default to the full RFC path (`../RFC/RFC_Guidelines.md`).

## Enforcement

- **CI-level:** the cross-reference/integrity linter already specified in `../../Blueprint/Testing_Blueprint.md` §6 (built to close TD8, `../../Blueprint/Technical_Debt_Register.md`) is the mechanical backstop — it fails a build that edits a frozen document's content without a corresponding new ADR reference in the same change.
- **Review-level:** every pull request that touches `../../Architecture/` or `../../Blueprint/` requires the ADR number in its description; a reviewer (per `../Engineering_Handbook.md`'s code review process) rejects a PR missing one.
- **Freeze-level:** `../Review_Board/Architecture_Review_Process.md` stage 9 — a change significant enough to move a certified baseline count (ADR count, bounded context count, event/container counts) triggers a new dated freeze delta in `../Architecture_Freeze/`.

## What this policy does not cover

Changes entirely inside one service's private implementation, invisible outside that service's published interface. Those follow ordinary code review (`../Engineering_Handbook.md`), not this policy — treating every internal refactor as an architectural change would make the governance system itself the bottleneck it exists to prevent becoming.

## Related

- `../RFC/RFC_Lifecycle.md`, `../Review_Board/Architecture_Review_Process.md`, `../ADR/ADR_Governance.md` — the three stages this policy sits downstream of
- `Documentation_Governance.md` — the update obligation this policy's "Affected Documents" field feeds
- `Versioning_Strategy.md` — how a change's version bump is determined once it clears this policy
- `../../Blueprint/Technical_Debt_Register.md` — TD8, the CI-level enforcement this policy relies on
