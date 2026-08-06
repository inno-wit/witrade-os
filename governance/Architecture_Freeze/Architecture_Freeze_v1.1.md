# Architecture Freeze Delta — v1.1

## STATUS: ACCEPTED, ADDITIVE (Minor)

This is a **new dated delta file**, not an edit to `Architecture_Freeze_Certificate_v1.0.md`, per that certificate's own §Definition of Frozen rule 3 and `../Policies/Versioning_Strategy.md`'s whole-set versioning rule. The v1.0 certificate stays exactly as written; this document records what changed since it, and why the change is Minor rather than Major.

---

## Version

**v1.1**, ratified 2026-08-06. Supersedes nothing in v1.0 — purely additive per `../Policies/Versioning_Strategy.md`: no fixed-point ADR touched, no bounded context added or removed, no certified baseline count invalidated in a way that changes the platform's fundamental shape.

## Trigger

`../RFC/RFC-0001-kill-switch-recheck-at-broker-send.md`, Accepted 2026-08-06, generating `../../Architecture/decisions/0044-kill-switch-recheck-at-broker-send.md` (ADR-0044). Full governance chain followed: RFC → (adversarial independent review, in place of a multi-person Architecture Review Board — see RFC-0001 §Reviewers for why this is a substantive rather than a nominal check) → ADR → Documentation Update, all in this change, per `../Policies/Implementation_Change_Control.md`. No implementation exists yet, so the Implementation and Release stages do not apply.

## What changed

A single, bounded gap in the order-execution kill-switch flow, found and closed before any code exists: the `AuthorisedOrder` token, once minted by C21, was never re-checked against live kill-switch state before C24 sent it to the broker — a window bounded by the token's own TTL (~12s), affecting at most one single-use entry order. Full account: ADR-0044 §Context.

## Baseline deltas from v1.0

| Class | v1.0 | v1.1 | Change |
|---|---|---|---|
| Total Accepted ADRs | 43 | **44** | +1 (ADR-0044, implementation-phase — the architecture-phase register `../../Architecture/decisions/README.md` covering 0001-0043 is itself extended in place per `../ADR/ADR_Governance.md` §Repository Standards, not forked; `../Decision_Log/README.md` separately indexes implementation-phase ADRs 0044+) |
| P0 ADRs | 25 | **26** | +1 (ADR-0044 is P0) |
| Fixed-point ADRs (no reversal tripwire) | 8 | 8 | Unchanged. ADR-0044 has real, monitorable tripwires (P0-bug and SLO conditions) — it is not a fixed point |
| Contract 11 (Execution Platform) invariants | 18 | **19** | +1 (invariant 19, kill-switch send-time recheck) |
| Security zones named | 4 (DMZ/CORE/VAULT/OPS) | **5** | +1 (Bridge, named explicitly with a narrow VAULT egress exception — `../../Architecture/21_Security_Architecture.md` §5) |
| RFCs filed | 0 (governance system had none yet) | **1** | RFC-0001, Accepted |
| Bounded contexts | 12 | 12 | Unchanged |
| Event subjects governed | 85 | 85 | Unchanged — `evt.execution.aborted.v1` gains a new `reason` value, not a new subject |
| Chaos test cases (hand-off window) | 0 | **2** | `Blueprint/Testing_Blueprint.md` §4.1, hard gate before live capital |

## Files touched

**New files:**
- `../../Architecture/decisions/0044-kill-switch-recheck-at-broker-send.md` — ADR-0044
- `RFC-0001-kill-switch-recheck-at-broker-send.md` (in `../RFC/`) — the originating RFC
- `../RFC/README.md` — RFC register, created on first RFC per `../RFC/RFC_Numbering.md`
- This file

**Amended in place** (each carries its own dated `**Amended:**` header line citing ADR-0044, per `../Policies/Documentation_Governance.md`'s "same change, not a follow-up" rule — content changed, original per-file version label unaffected since Architecture/Blueprint documents are versioned whole-set, not per-file):
- `../../Architecture/decisions/README.md` — register extended to 44/44, two new tripwire metrics
- `../../Architecture/contracts/11_Execution_Platform.contract.md` — invariant 19, SLO row, Security Boundary network row, Related section
- `../../Architecture/21_Security_Architecture.md` — §5, Bridge zone named with VAULT egress exception
- `../../Architecture/WITrade_OS_Architecture_Review_Board_Report_v1.0.md` — §16 appended (append-only resolution log; original findings, including G-2's row, left as written)
- `../../Blueprint/Worker_Architecture.md` — self-halt heartbeat worker, C21 + C24
- `../../Blueprint/Interface_Definitions.md` — `KillSwitchService.heartbeat_age_seconds()`, `ExecutionService.submit()` internal-recheck note
- `../../Blueprint/API_Blueprint.md` — `CheckKillSwitch` row corrected (was C21-only, now names both check points)
- `../../Blueprint/Schema_Blueprint.md` — `AuthorisedOrder.token_expires_at`, `halt_epoch` explicitly rejected and recorded as such
- `../../Blueprint/Testing_Blueprint.md` — §4.1 (two chaos tests), §4.2 (named exit-path-trap entry)
- `../../Blueprint/Technical_Debt_Register.md` — §6 kill-switch CI-lint row widened to cover both check points; new row for the exit-path-trap risk
- `../Decision_Log/README.md` — ADR-0044 register row

**Not touched:** any of the 43 original ADR files' own content (only the new register rows reference them); any fixed-point ADR; the v1.0 certificate itself.

## Gate check (`../Review_Board/Architecture_Review_Process.md` §9)

This change moves a certified baseline count (ADR count 43→44, P0 count 25→26), which is exactly the condition that triggers this delta filing rather than a silent absorption into v1.0's certified numbers. All documents named in RFC-0001's Impact section are edited in this same change — zero deferred to a follow-up (`../Policies/Documentation_Governance.md` gate).

## Approval Authority

**Fredrick Kimeu** — same sole approval authority as the v1.0 certificate (`Architecture_Freeze_Certificate_v1.0.md` §Approval Authority), unchanged by ADR-0009.

## Related

- `Architecture_Freeze_Certificate_v1.0.md` — the baseline this delta extends, left unedited
- `../RFC/RFC-0001-kill-switch-recheck-at-broker-send.md` — the RFC that triggered this delta
- `../../Architecture/decisions/0044-kill-switch-recheck-at-broker-send.md` — the ADR this delta certifies as part of the baseline
- `../Decision_Log/README.md` — implementation-phase ADR index, now non-empty
- `../Policies/Versioning_Strategy.md` — the Minor/Major rule this delta's version number follows
