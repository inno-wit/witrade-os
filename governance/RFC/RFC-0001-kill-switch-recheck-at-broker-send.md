# RFC-0001: Re-check the kill switch at broker send, not only at token mint

**Status:** Accepted
**Author:** Fredrick Kimeu
**Date:** 2026-08-06
**Numbering:** RFC-0001, the first RFC filed under this governance system (`RFC_Numbering.md`)
**Reviewers:** Fredrick Kimeu, sole operator (`../ADR/ADR_Governance.md` §Ownership) — see **Review process actually used** below for why this is not a gap
**Related ADRs:** ADR-0017, ADR-0018, ADR-0019, ADR-0021, ADR-0022, ADR-0025, ADR-0037, ADR-0038 (generates ADR-0044)
**Related bounded contexts:** BC6 (Risk Authorisation, C21), BC8 (Order Execution, C24) — cross-cutting between them

---

## Problem

The frozen architecture specifies the kill switch as checked synchronously at two conceptually distinct moments — before an order is *submitted* (ADR-0017) and before the `AuthorisedOrder` token is *minted* (ADR-0018) — without distinguishing that these are different operations, on different hosts (C21 mints, C24 submits), separated by a durable queue hop. Contract 10 invariant 4 and the Phase B Blueprint resolved the ambiguity in favour of mint-only: `Blueprint/API_Blueprint.md` documented `CheckKillSwitch` as "in-process within C21, not cross-service," and C24's documented send pipeline contains no kill-switch node at all. The `AuthorisedOrder` token, once minted, is checked at C24 only for signature, TTL, staleness, and idempotency — never for current kill-switch state.

## Motivation

If the kill switch trips after a token is minted but before C24 sends it — a reconciliation break, a limit breach, an operator trip, arriving in the up-to-~12-second window the token's own TTL allows — the order still reaches the broker. This is exactly the failure mode ADR-0017/0018 exist to prevent, left open at the one seam neither ADR's wording actually covers. Left unresolved, this gap ships silently the first time Risk + Execution is implemented, because nothing in the current contract or Blueprint would prompt an implementer to add the check — the documented interface says the opposite (check is C21-only).

A related, causally connected gap: ADR-0018's self-halt heartbeat — cited by the Architecture Review Board (`../../Architecture/WITrade_OS_Architecture_Review_Board_Report_v1.0.md` row R-1) as the reason the kill switch passed audit — was specified at the Architecture layer but never carried into the Phase B Blueprint. `Blueprint/Worker_Architecture.md` and `Blueprint/Interface_Definitions.md` name no heartbeat, on either C21 or C24.

## Background

Found by an independent pre-implementation review conducted 2026-08-06: two AI-generated flaw reports (framed differently — one describing an architecture that turned out not to match the actual documented design, one describing the real architecture accurately but proposing unimplementable fix parameters), adjudicated against primary source text by a third, independent pass rather than trusted on either report's own summary. Full adjudication published as an HTML report; findings F1-F8 therein map directly to this RFC's Proposed Change. See `../../Architecture/decisions/0044-kill-switch-recheck-at-broker-send.md` §Context for the full account, which this RFC does not restate (one-fact-one-canonical-source, `../../Architecture/freeze/Canonical_Source_Validation.md`).

## Current Behaviour

- ADR-0018: kill switch checked synchronously at C21, immediately before minting `AuthorisedOrder`, no awaitable operation in between. Correct and unchanged by this RFC.
- Contract 11 (`../../Architecture/contracts/11_Execution_Platform.contract.md`), invariants 1-18: C24 verifies token signature, TTL, staleness, and idempotency before sending. No kill-switch check.
- `Blueprint/API_Blueprint.md`: `CheckKillSwitch` documented as C21-only.
- `Blueprint/Worker_Architecture.md`, `Blueprint/Interface_Definitions.md`: no self-halt heartbeat on any process.
- `../../Architecture/21_Security_Architecture.md` §5: zone model names DMZ/CORE/VAULT/OPS; C24's "Bridge" zone (already named in contract 11) has no entry in the zone model itself, and no egress path into VAULT exists for any purpose.

## Proposed Change

1. Add a kill-switch re-check as the final step of C24's send pipeline, immediately before `BrokerAdapter.send`, no awaitable operation in the gap — same three-tier fail-closed rule as ADR-0018.
2. Scope the re-check to `ENTRY` intent only, with intent derived from authoritative position state (ADR-0019 rule 4), never a caller-supplied field. `EXIT` orders bypass the re-check entirely.
3. On halt or unreadable tier (`ENTRY` only): drop the token unconsumed, never send, emit `evt.execution.aborted.v1` reason `kill_switch_recheck`.
4. Add `token_expires_at = mint_time + 2s` to `AuthorisedOrder`, distinct from `valid_until`. Do not add `halt_epoch`/generation-counter binding — redundant once the live re-check exists.
5. Restore the self-halt heartbeat (ADR-0018) on both C21 and C24 in the Blueprint layer.
6. Name a fifth security zone, Bridge, in the zone model, with one narrow exception: Bridge → VAULT, kill-switch tier reads only.
7. Correct `Blueprint/API_Blueprint.md`'s `CheckKillSwitch` row, which otherwise directly contradicts item 1.
8. Add two hard-gate chaos tests (trip between mint and send, for `ENTRY` and `EXIT` separately) and a named Technical Debt Register entry for the most likely implementation mistake (applying the re-check unconditionally, which would violate ADR-0019).

Full mechanism, rationale, and Tripwire: `../../Architecture/decisions/0044-kill-switch-recheck-at-broker-send.md`.

## Alternatives

**A. Do nothing; rely on the mint-time check alone.** Rejected — leaves the window this RFC exists to close; it is the status quo the review found insufficient.

**B. Bind the token to a `halt_epoch`/generation counter instead of re-checking live state at send.** Considered directly. Rejected: once C24 must hold a live three-tier read for the re-check anyway (item 1), an epoch comparison is strictly subsumed by it and adds a second mechanism, plus new monotonic-counter infrastructure in Postgres nothing else in the design calls for.

**C. Re-check unconditionally, for every order regardless of intent.** Rejected: violates ADR-0019 (a fixed point — exits must never be blocked by an entry-blocking rule) and fails the existing correctness SLO in contract 11.

**D (chosen). Re-check at send, scoped to `ENTRY`, plus restore the dropped heartbeat, plus a mint-anchored token TTL.** Closes the real gap, respects every constraining fixed-point ADR, reuses ADR-0018's existing mechanism rather than inventing a new one.

## Tradeoffs

Gains: closes a real, if bounded (~12s, single entry order), stale-authorisation window; makes the self-halt heartbeat's partition defence actually present in the implementation layer, not just the architecture layer. Costs: C24 gains a new runtime dependency on VAULT reachability for entries (an unreachable T2/T3 now blocks entries from Bridge, correctly, where previously it did not); a new, narrowly-scoped network egress path must be built and kept narrow or it becomes a general hole in the boundary that exists specifically to isolate broker credentials.

## Risks

If the Bridge→VAULT egress is implemented more broadly than "kill-switch tier reads only," it weakens the credential-isolation boundary contract 11's Security Boundary section calls the reason C24's isolation "is worth more than any single control inside C24." If the `ENTRY`/`EXIT` intent scoping is implemented as an unconditional check (the single most likely mistake — see item 8, and `Blueprint/Technical_Debt_Register.md`'s named entry), it silently violates ADR-0019, a fixed point, during exactly the emergency condition that ADR exists to survive. Both risks are named explicitly in ADR-0044's Tripwire section and mitigated by required tests, not left as prose.

Blast radius: BC6 (Risk, C21) and BC8 (Order Execution, C24) only. No change to any other bounded context's behaviour.

## Impact

- **Affected interfaces:** `KillSwitchService` (adds `heartbeat_age_seconds()`), `ExecutionService.submit()` (internal recheck, no signature change) — `Blueprint/Interface_Definitions.md`
- **Affected events:** none new; `evt.execution.aborted.v1` gains a new `reason` value (`kill_switch_recheck`), not a schema change
- **Affected APIs:** `CheckKillSwitch` row in `Blueprint/API_Blueprint.md` (documentation correction, not a new endpoint)
- **Affected bounded contexts:** BC6, BC8
- **Affected tests:** `Blueprint/Testing_Blueprint.md` §4.1 chaos suite (new), §4.2 named risk entry (new)
- **Affected runbooks:** none — `evt.execution.aborted.v1` already routes through the existing alerting path
- **Breaking change?** No. Additive: a new invariant, a new schema field with a default, a new worker, a new zone-model entry. No existing interface signature changes, no existing behaviour for `EXIT` orders changes.

## Migration

Nothing is implemented yet (`../../Architecture/ROADMAP.md`). No migration path required — this RFC changes the specification implementation has not yet been built against, which is the cheapest possible moment to make this change.

## Open Questions

None blocking ADR generation. Deferred, non-blocking, tracked in `../../Blueprint/Technical_Debt_Register.md` and the freeze delta (§ below): whether `token_expires_at`'s 2s default needs tuning once real send-path latency is measured against contract 11's SLO — explicitly a post-implementation tripwire (ADR-0044 §Tripwire), not an open question blocking this RFC.

## Approval Status

`Accepted`, 2026-08-06.

## Reviewers

Fredrick Kimeu — approve, 2026-08-06.

**Review process actually used, stated plainly:** this RFC was not run through a multi-person Architecture Review Board — per `../ADR/ADR_Governance.md` §Ownership, Fredrick Kimeu is the sole decider of record for this platform (ADR-0009), exactly as all 43 original architecture-phase ADRs were "decided and accepted in the same pass" by one person. What substitutes for the Review/Technical-Validation/Impact-Analysis stages (`../Review_Board/Architecture_Review_Process.md` §Stages 2-4) here is the independent adversarial review this RFC's Background section cites: claims re-derived from primary source text by a reviewer with no stake in the original two flaw reports being right, rather than either report's summary taken on faith. That is a substantively different check than self-approval, even though the formal sign-off is still one person — the same distinction the original Architecture Review Board report (`../../Architecture/WITrade_OS_Architecture_Review_Board_Report_v1.0.md`) itself draws between "self-graded" and "independently checked."

## Decision

**Accepted.** The gap is real and bounded; the fix is additive, respects every constraining fixed-point ADR (0017, 0019, 0022), and is small enough to land before any Risk/Execution code is written — the correct time to make this change, per `Implementation_Change_Control.md`'s reasoning that undocumented drift accumulates unnoticed precisely when a change looks small and obviously correct. Generates ADR-0044.

## Implementation Plan

Formalised immediately as ADR-0044 (`../../Architecture/decisions/0044-kill-switch-recheck-at-broker-send.md`), Accepted the same day. Lands in the first Risk + Execution vertical slice, per `Roadmap/Implementation_Gates.md` — before any code that could hit the window this RFC closes. No separate implementation gate needed; this is a pre-implementation specification change, not a change to running code.

---

## Related

- `../../Architecture/decisions/0044-kill-switch-recheck-at-broker-send.md` — the ADR this RFC generates
- `../ADR/ADR_Governance.md` — the process this RFC's acceptance triggers
- `../Architecture_Freeze/Architecture_Freeze_v1.1.md` — the whole-set version delta this RFC's acceptance triggers (`Versioning_Strategy.md`, Minor bump)
- `../../Architecture/WITrade_OS_Architecture_Review_Board_Report_v1.0.md` §16 — G-2 partial-closure log entry citing this RFC's originating review
