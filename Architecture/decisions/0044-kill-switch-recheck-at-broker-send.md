# ADR-0044: The kill switch is re-checked at broker send, not only at token mint

**Status:** Accepted
**Date:** 2026-08-06
**Decided:** 2026-08-06 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** risk, safety, reliability, execution
**Amends:** ADR-0017, ADR-0018 (extends, supersedes neither — see Context)
**Originating RFC:** [RFC-0001](../../governance/RFC/RFC-0001-kill-switch-recheck-at-broker-send.md) (`governance/ADR/ADR_Governance.md` §Numbering)

---

## Context

An independent pre-implementation review (two AI-generated flaw reports adjudicated against source, 2026-08-06) found a real, bounded gap on the order path that neither ADR-0017 nor ADR-0018 closes as written.

**The wording drift.** ADR-0017 states the final kill-switch check happens "before any order is **submitted**" and "the last thing that happens before **the order goes out**" — language that describes the Execution Service (C24), which is what actually submits to the broker. ADR-0018 states the check is re-checked "at token issuance" and must have "no awaitable operation" between the check and **minting** the `AuthorisedOrder` — language that describes the Risk Engine (C21), which is what mints the token. Contract 10 invariant 4 and the Phase B Blueprint both resolved this ambiguity in favour of ADR-0018's reading: the check exists only at mint, inside C21. `Blueprint/API_Blueprint.md`'s `CheckKillSwitch` entry is documented as "in-process within C21, not cross-service," and no kill-switch node exists anywhere in C24's documented send pipeline.

**The gap this leaves.** The `AuthorisedOrder` token minted by C21 is signed, single-use, and TTL-bounded (`valid_until = created_at + min(12s, 0.10 × bar_interval, atr_window)`), then written to an outbox and delivered to C24 as `cmd.execution.place_order.v1` (ADR-0037, ADR-0038). C24's send pipeline verifies the token's signature, TTL, staleness, and idempotency key — and sends. None of those checks read live kill-switch state. If the switch trips after mint and before C24's send (a reconciliation break, a limit breach, an operator trip), the token is still valid by every check C24 performs, and the order reaches the broker with the platform halted. The window is bounded by the token's own TTL, at most ~12 seconds, and applies to at most one entry order (the token is single-use) — this is a stale-authorisation defect, not an unauthorised-order defect, and it does not reopen blocking defects B1 or B2. It is nonetheless a real gap in a fail-closed control, worth closing before any code that could hit it is written.

**A second, related gap surfaced by the same review.** ADR-0018's self-halt heartbeat — the mechanism that makes the kill switch robust to a network partition, and the specific control the Architecture Review Board cited (`WITrade_OS_Architecture_Review_Board_Report_v1.0.md` row R-1) as evidence the switch was "specified to the level of a real state machine, not asserted" — was never carried into the Phase B Blueprint. `Blueprint/Worker_Architecture.md` and `Blueprint/Interface_Definitions.md` name no heartbeat, on either C21 or C24. The freeze's certification of the kill switch rests in part on a control the implementation layer, as currently specified, does not contain.

## Options considered

**A. Leave the check at mint only (status quo).**
*Pros:* nothing to change; matches the current contract and Blueprint.
*Cons:* leaves the mint-to-send window open for as long as the token's TTL, which is exactly the interval a fast-moving incident (the kind that trips the switch) occupies.

**B. Re-check at send, unconditionally for every order.**
*Pros:* closes the window completely, no exceptions.
*Cons:* violates ADR-0019. Exits are the one order type that must never be blocked by an entry-blocking rule, and a halted-but-still-in-position account is the exact scenario ADR-0019 exists to prevent. An unconditional recheck traps the platform in a position during precisely the condition the switch is meant to protect against.

**C. Re-check at send, scoped to `ENTRY` intent only, reading live three-tier state, no awaitable operation between the check and the send.**
*Pros:* closes the window for the only order type it can legally apply to; reuses the exact mechanism ADR-0018 already specifies (three-tier, fail-closed, no-await); consistent with ADR-0019's existing entry/exit asymmetry (`KillSwitchPreCheck` already applies to entries, not exits, per ADR-0019's rule table).
*Cons:* requires C24 to read T2 (Redis) and T3 (Postgres) state, a new network dependency not currently in C24's documented Bridge-zone boundary; intent must be read from authoritative position state, never a caller-supplied field, or the check is trivially bypassable.

## Decision

**Option C.** The kill switch is checked at **both** points on the order path, and both were always intended — this ADR resolves the wording drift rather than changing the underlying design:

1. **At mint (C21), unchanged.** ADR-0018 governs this check exactly as written: last rule evaluated, no awaitable operation before minting, re-checked at issuance.
2. **At send (C24), new.** Immediately before `BrokerAdapter.send`, after signature/TTL/staleness/idempotency checks, C24 performs the same three-tier check ADR-0018 specifies: `HALTED if ANY tier says HALTED OR ANY tier is unreadable`. No awaitable operation between the check and the send.
3. **Scope: `ENTRY` intent only.** The check reads `AuthorisedOrder.intent`, derived from authoritative position state per ADR-0019 rule 4 — never accepted as a caller-supplied field on the command, or the check becomes bypassable by mislabelling an entry as an exit. When `intent == EXIT`, C24 sends regardless of kill-switch state, exactly as ADR-0019 requires.
4. **On halt or unreadable tier (ENTRY only):** drop the token without consuming it (no compare-and-set), never send, emit `evt.execution.aborted.v1` with `reason: kill_switch_recheck`.
5. **Authorisation staleness gets its own field, distinct from decision staleness.** Add `token_expires_at = mint_time + 2s` to the `AuthorisedOrder` schema, alongside the existing `valid_until` (which bounds how old the underlying market/portfolio snapshot may be). `halt_epoch`-style binding was considered and rejected: once C24 holds a live three-tier read for step 2, a generation-counter comparison is strictly subsumed by it, and would require new monotonic-counter infrastructure in Postgres that nothing else in the design calls for.
6. **The self-halt heartbeat applies to every order-capable process, C21 and C24 alike**, exactly as ADR-0018 already states. Its absence from the Phase B Blueprint is a translation gap, not a design decision, and is corrected as part of this ADR (`Blueprint/Worker_Architecture.md`, `Blueprint/Interface_Definitions.md`).
7. **The Bridge zone gains a narrowly-scoped egress path.** C24, in the Bridge zone (Windows VPS), needs read access to VAULT for T2/T3 kill-switch state. `21_Security_Architecture.md`'s zone model is amended to name this explicitly: C24 → VAULT, kill-switch tier reads only, no other VAULT service reachable from Bridge.

## Rationale

ADR-0017 and ADR-0018 are both correct about the mechanism and both incomplete about the location, because they were written to describe the same synchronous, fail-closed check without distinguishing the two hosts a token's lifecycle actually crosses: it is minted in C21 and consumed in C24, on a different machine, after a durable queue hop whose delay is exactly what a kill-switch trip can happen inside. Treating "check before mint" and "check before send" as the same requirement was the error; they are the same *rule* applied at two necessary points, not one point described twice.

Scoping the recheck to `ENTRY` is not a weakening of the control. It is the same asymmetry ADR-0019 already established for the mint-time check, applied consistently at the second point the check now exists. A kill switch that can trap the platform in a position is a switch operators will eventually be afraid to trip aggressively, which ADR-0018's own rationale already identifies as the failure mode ADR-0019 exists to prevent.

The heartbeat correction is included here rather than as a separate ADR because it was found by the same review, for the same underlying reason: a control specified at the Architecture layer and never confirmed present at the Blueprint layer. Recording both in one ADR keeps the causal link visible — a Phase A→B translation gap, not two unrelated findings.

## Consequences

**Positive**
- The mint-to-send window is closed for the order type that matters (entries); exits remain unconditionally deliverable, satisfying ADR-0019.
- The self-halt heartbeat, and therefore partition robustness, now actually exists on both order-capable processes, not just on paper.
- Authorisation staleness (token age) and decision staleness (market/portfolio snapshot age) are now tracked as separate, independently tunable bounds.

**Negative**
- C24 gains a new runtime dependency on VAULT reachability for `ENTRY` sends. An unreachable T2/T3 from Bridge now blocks entries (correctly, per fail-closed) where previously it did not affect C24 at all. This is the intended trade — see ADR-0018's own accepted cost of more frequent, correct halts over any silent fail-open.
- The Bridge→VAULT egress path is a new item in the network segmentation model and must be implemented as narrowly as documented (§7 above), or it becomes a general-purpose hole in a boundary that exists specifically because C24 is the only process holding broker credentials.

**Neutral**
- Latency impact is bounded and small: the recheck is a three-tier read identical in shape to the one C21 already performs at mint, on the hot path only for `ENTRY` orders.

## Tripwire

If the C24 recheck ever fires against an order whose authoritative `intent` is `EXIT`, that is a P0 bug, not a spurious halt — it means ADR-0019 has been violated at the implementation level and the intent-derivation path (rule 4) has a defect. Treat as a fixed-point violation, same severity class as ADR-0019 itself.

If C24→VAULT read latency measurably threatens the send-path SLO (`contracts/11_Execution_Platform.contract.md` §SLO), the fix is a faster or cached read path with heartbeat-driven invalidation, not removing or widening the recheck. Same asymmetry ADR-0018 already accepts.

## Related

- ADR-0017 (kill switch is synchronous, not pub/sub) — the rule this ADR clarifies applies at two points, not one
- ADR-0018 (three-tier fail-closed interlock, self-halt heartbeat) — the mechanism reused unchanged at the second point
- ADR-0019 (exits never blocked) — the fixed point that scopes this ADR's check to `ENTRY`
- ADR-0021 (deadlock/quorum failure resolves to no-trade) — governs the unreadable-tier branch
- ADR-0022 (every entry carries a broker-side hard stop) — bounds the blast radius of any order that does slip through before this ADR's fix lands
- ADR-0025 (fail-closed is the universal default)
- ADR-0037 (commands vs events) — governs the outbox/queue hop between mint and send, untouched by this ADR
- ADR-0038 (transactional outbox) — a dropped, unconsumed token leaves the outbox row acked and the command terminal; no outbox semantics change
- `contracts/11_Execution_Platform.contract.md` — invariant 19, added by this ADR
- `contracts/10_Risk_Portfolio_Platform.contract.md` — the token issuer upstream, unchanged
- `21_Security_Architecture.md` §5 — Bridge zone egress, added by this ADR
- `WITrade_OS_Architecture_Review_Board_Report_v1.0.md` row R-1 (heartbeat cited as audit evidence), row G-2 (recommended exactly this kind of outside technical review before implementation)
- Source: the pre-implementation independent architecture review, 2026-08-06
