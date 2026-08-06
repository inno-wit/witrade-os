# Decision Log

**Purpose:** the index of implementation-phase ADRs (`0044` onward), continuing `../../Architecture/decisions/`'s register rather than forking it into a second, competing list.
**Canonical ADR register:** [`../../Architecture/decisions/README.md`](../../Architecture/decisions/README.md). This file cross-links to it; it does not restate the 43 architecture-phase entries already there.

---

## Why a second index exists at all

`../../Architecture/decisions/README.md` is the register for the frozen architecture phase, 0001-0043, closed 2026-08-04. It stays exactly as it is — per the freeze rule, it is not edited to absorb implementation-phase decisions. This log is where `0044` onward gets tracked, with one additional column the architecture-phase register did not need: **originating RFC**, since every implementation-phase ADR is expected to trace back through `../RFC/` and `../Review_Board/Architecture_Review_Process.md` (`../ADR/ADR_Governance.md`).

## Register

| # | Title | Originating RFC | Priority | Status | File |
|---|---|---|---|---|---|
| 0044 | The kill switch is re-checked at broker send, scoped to `ENTRY`, not only at token mint | [RFC-0001](../RFC/RFC-0001-kill-switch-recheck-at-broker-send.md) | P0 | Accepted, 2026-08-06 | [`../../Architecture/decisions/0044-kill-switch-recheck-at-broker-send.md`](../../Architecture/decisions/0044-kill-switch-recheck-at-broker-send.md) |

Update this table on every new ADR, per `../ADR/ADR_Governance.md`. New rows go at the bottom; numbers are never reused or reordered (`../RFC/RFC_Numbering.md`'s sibling rule for ADRs).

## Quarterly tripwire review

Inherits `../../Architecture/decisions/README.md`'s own stated rule: the quarterly tripwire review cannot begin until at least one quarter of live operation exists. `../../Architecture/freeze/ADR_Index.md` §5 is its dated starting point for the 43 architecture-phase ADRs; this log is the starting point for any implementation-phase ADR added since.

## Related

- `../../Architecture/decisions/README.md` — the canonical architecture-phase register (0001-0043)
- `../ADR/ADR_Governance.md` — numbering, lifecycle, and ownership rules this log follows
- `../RFC/RFC_Numbering.md` — the independent numbering sequence that feeds this log's "Originating RFC" column
