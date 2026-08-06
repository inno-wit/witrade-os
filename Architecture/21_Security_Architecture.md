# 21 — Security Architecture

**Diagram:** `21_Security_Architecture.excalidraw`
**Phase:** 11 — Architecture Completion (5 of 5)
**C4 Level:** L2 — Container (cross-cutting trust-boundary view)
**Depends on:** all pages, principally `10_Risk_Portfolio_Platform.md`, `11_Execution_Platform.md`, `17_Evidence_Graph.md`, `20_Model_Registry.md`
**Status:** Canonical operational home for platform security. **Threats T1-T6, and the full prose treatment of secrets, insider controls, data protection, API security, and incident response, remain in `review/R15_Security.md` (unmodified) — this page extends the threat model to T7-T11 (the gaps introduced or clarified by pages 17-20) and states the cross-cutting principles the user's brief asks for explicitly, at the level a decade-long operator needs at a glance.**
**Amended:** 2026-08-06 — §5 gains an explicit Bridge zone and a narrowly-scoped Bridge→VAULT egress rule, added by [ADR-0044](decisions/0044-kill-switch-recheck-at-broker-send.md). The zone model previously named only DMZ/CORE/VAULT/OPS; C24 (Bridge) already existed as a container (`contracts/11_Execution_Platform.contract.md`) but had no entry in the zone model itself, an omission an independent pre-implementation review flagged as a blocker for the kill-switch send-time recheck (invariant 19).

---

## Why this is not user authentication

This page is about capital, not accounts. The asset at risk is the ability to move money at a broker, and the adversaries of interest are the ones who can reach that ability: a compromised credential, a manipulated input to a capital-allocating LLM, a poisoned dependency in the order-sending process, or the platform's own operator under the stress of a drawdown. Security work that starts from a login form misses all four.

## 1. Threat model

**T1-T6 are unchanged, canonical in `review/R15_Security.md` §1, and restated here only by reference:** T1 broker credential compromise, T2 prompt injection via news text, T3 supply chain compromise, T4 insider/operator error under duress, T5 data poisoning, T6 denial of service. Read R15 §1 for vector, impact, likelihood, and priority on each; §5-11 for the full mitigation detail.

Five threats are new since R15, surfaced by pages 17-20 rather than by the original fourteen pages, and are specified here to the full depth the review's format did not use (Detection, Mitigation, Recovery, Residual risk as explicit fields).

### T7 — Evidence graph poisoning (feature/observation corruption reaching the graph as fact)

| Field | Value |
|---|---|
| Attack vector | A compromised or buggy upstream engine (BC4) writes a node with a fabricated or extreme value that is syntactically valid and passes schema validation |
| Risk | A single poisoned node with high `reliability x freshness x quality` can dominate the log-odds propagation (page 17 §5) before any desk reasons over it |
| Likelihood | Low as an attack, medium as an engine bug — this threat matters more for correctness than for adversarial intent |
| Impact | A confidently wrong graph baseline, which the Committee is measured against (`graph_committee_divergence`) — a poisoned baseline corrupts the very metric meant to catch Committee failure |
| Detection | Range and rate-of-change bounds per node type (a regime probability jumping from 0.1 to 0.9 in one bar is flaggable even though both values are individually valid); cross-node consistency checks (`SHARES_MODEL_WITH` nodes diverging sharply is itself a signal) |
| Mitigation | Node-level input validation at graph assembly (page 17's invariant 1, extended with range checks per node type); the `quality` weighting factor already discounts low-quality sources arithmetically |
| Recovery | A sealed graph is immutable (page 17 invariant 3); a poisoned graph is superseded by a corrected one with a `supersedes` link, never patched in place |
| Residual risk | A poisoned value within plausible range from a normally-reliable engine is the hardest case and is caught only by the Committee's own reasoning or by post-hoc Learning review, not by the graph layer itself |

### T8 — Unauthorised or premature model/prompt promotion

| Field | Value |
|---|---|
| Attack vector | An operator (under T4-style duress) or a compromised CI pipeline promotes an artefact to `CHAMPION` without completing `SHADOW_PASSED`, or bypasses the Risk approval gate on a Tier-0 artefact |
| Risk | A capital-allocating artefact goes live with no validated track record |
| Likelihood | Low if the SM-5 gate is enforced in the registry service rather than by discipline; the entire point of page 20 is to make this a service-level impossibility, not a policy |
| Impact | Equivalent to deploying untested code to the order path — potentially severe, bounded by the same downstream gates (BC6 still authorises every order regardless of which model proposed it) |
| Detection | `promote()` is an audited, privileged operation (page 20, BC11); any promotion event without a preceding `SHADOW_PASSED` state in the audit trail is a hard alert, checked continuously not just at review time |
| Mitigation | The state machine is enforced in the registry, not the CI pipeline — `promote()` structurally rejects a call on an artefact not in `SHADOW_PASSED`; the Risk approval gate (page 20 §2) is a second, separately-audited confirmation for Tier 0 |
| Recovery | `rollback()` requires no approval and is always available (page 20 invariant 3) |
| Residual risk | An operator with legitimate `operator` credentials who is willing to falsify the shadow record itself — this reduces to T4/T1 and is covered by the same dual-control and audit-immutability controls, not a new control |

### T9 — Event spoofing and replay-attack confusion (`env` interlock failure)

| Field | Value |
|---|---|
| Attack vector | A simulation, backtest, or replayed event stream is consumed by a production component as if it were live, or a stale/duplicated live event is reprocessed as new |
| Risk | A simulated fill or decision triggers a real order, or a real decision is made twice from one event delivered twice |
| Likelihood | Low with the `env=sim` interlock (`review/R19_Missing_Components.md` §2) correctly enforced; realistic during any manual replay/debugging session if the interlock is bypassed "just to check something" |
| Impact | Duplicate or phantom orders — the same failure class as B1 (broadcast events used as commands), closed for the primary order path by ADR-0037 but re-openable by any component that does not check `env` |
| Detection | Every message tagged with `env`; a mismatch between a consumer's expected `env` and a message's actual `env` is a hard failure, alerted immediately, not silently dropped |
| Mitigation | `env=sim` interlock on every message (R19 §2); idempotent `client_order_id` and single-use `AuthorisedOrder` tokens as the second line of defence (R03 §6 invariant) independent of the `env` tag |
| Recovery | A detected `env` mismatch halts the affected component (fail-closed, ADR-0025), not a silent discard — a silent discard hides the fact that the interlock was nearly bypassed |
| Residual risk | A deliberate, correctly-tagged replay run that is misconfigured to write to the production namespace rather than a separate one — mitigated by the Simulation Harness's separate-namespace requirement (R19 §2), not by the `env` tag alone |

### T10 — Schema and wire-contract manipulation

| Field | Value |
|---|---|
| Attack vector | A publisher ships a payload that technically deserialises but violates the intended schema (a units mismatch, a silently truncated field, a version the consumer does not expect) |
| Risk | Silent misinterpretation downstream — a price in the wrong currency, a probability read as a percentage — which is a data-integrity failure with the same blast radius as a market-risk event but no market-risk trigger to alert on it |
| Likelihood | Low once the Schema Registry (C37, R19 §11) is live and CI-enforced; higher during any manual or emergency out-of-band publish |
| Impact | Wrong-by-construction inputs to sizing or evidence weighting, propagating until the divergence surfaces in reconciliation or P&L |
| Detection | Schema Registry CI checks (R01 §7): orphan events, missing publishers, incompatible schema changes, naming-convention violations, unregistered subjects |
| Mitigation | Pydantic models generated from the registry (ADR-0040), never hand-maintained in parallel; reject, never coerce, at every deserialisation boundary (R15 §9) |
| Recovery | A detected schema violation quarantines the message rather than passing a coerced best-guess (same principle as page 02's quality quarantine) |
| Residual risk | A schema-valid but semantically wrong value (a correctly-typed price in the wrong unit) is not caught by schema validation alone and depends on the range/consistency checks in T7's mitigation |

### T11 — Correlated model drift exploited as a market signal

| Field | Value |
|---|---|
| Attack vector | Not an external attacker — a market condition or a sophisticated counterparty pattern that a live model has not seen, causing multiple related models to degrade together in a way that, if actionable, would be an information edge against the platform |
| Risk | The platform trades confidently on stale collective judgement precisely when the market has moved to a regime none of its models represent |
| Likelihood | Medium — this is a property of any model-driven system operating in adversarial markets, not a rare event |
| Impact | Potentially the platform's largest single-incident loss category, larger than any individually-modelled market risk, because it defeats the models rather than merely moving against a correctly-modelled position |
| Detection | The Model Monitor's correlated-degradation check (page 20 §3) — multiple slots degrading together |
| Mitigation | Platform-scope kill switch on correlated degradation, no operator latency (page 20 §3, R11 §6) — the single control that matters most for this threat |
| Recovery | Manual, dual-control restart per the kill-switch clearance rule (R11 §7) — this is deliberately not an auto-clear condition |
| Residual risk | A drift pattern too gradual to trip any individual model's PSI/hit-rate threshold but real in aggregate — the honest residual, and the reason the weekly BC9 review remains a backstop even with continuous monitoring in place |

## 2. Zero Trust principles, stated explicitly

R15's trust-zone model (DMZ/CORE/VAULT/OPS) already implements Zero Trust; this section names the principles it implements so they survive a future refactor that might otherwise "simplify" the zone boundaries away.

1. **No implicit trust from network location.** Being inside CORE is not a credential. Every service-to-service call authenticates via mTLS regardless of which zone it originates from (R15 §3).
2. **Least privilege by construction, not by configuration.** A service's secret scope is its only access; there is no broader grant sitting unused "in case." The Execution Service holding the only broker credential is the paradigm case (R15 §2 rule 1).
3. **Verify explicitly, every call.** Service identity via mTLS with 24h auto-rotated certificates, never a long-lived shared key (R15 §3).
4. **Assume breach.** The security testing suite includes a fail-closed chaos test that kills each dependency and asserts the platform refuses to trade rather than degrading open (R15 §10) — this is Zero Trust's "assume breach" principle expressed as a CI test rather than a slogan.

## 3. RBAC and service identity, consolidated

| Identity class | Mechanism | Notes |
|---|---|---|
| Human — `operator` | OIDC, MFA mandatory, 15-minute privileged-session TTL | No exceptions, no convenience bypass (R15 §3) |
| Human — `researcher` | OIDC, invalid in prod by attribute, not just role | Prevents a research credential becoming a trading credential |
| Human — `auditor` | OIDC, read-only, output-filtered by role | Sees decisions, never credentials or vendor keys (R15 §9) |
| Service — any BC | mTLS, per-service cert, 24h TTL | Not a shared API key, ever |
| BC11 as the enforcement point | Every privileged action across every context calls into BC11's `authorize()` | Fails closed if BC11 is unreachable (§19 per-context spec) |

## 4. Secrets, encryption, key rotation

Unchanged from R15 §4 and §8: Tier-0 secrets on exactly one host, readable by exactly one process; no secret in an image, artefact, environment variable, log, or git object; the approval-token signing key lives only in the Risk Engine (BC6); quarterly rotation, rehearsed as a drill; disk-level encryption everywhere, MinIO server-side encryption on `decisions` and `raw` buckets. Page 20 adds one artefact class to this scope: **the Model Registry's promotion audit log carries the same immutability requirement as the Decision Record Store** — a promotion record is a decision record.

## 5. Network segmentation

Unchanged from R15 §2: DMZ / CORE / VAULT / OPS, with the rule that carries the most weight — **only the Risk Engine may open a connection to the Execution Service**, enforced at the network layer. BC12 Portfolio Construction (page 18) and the Model Registry (page 20) both sit in CORE and are subject to the identical rule: neither can reach VAULT under any configuration.

**Fifth zone, named explicitly: Bridge.** C24 (Execution Service) runs on a Windows VPS outside DMZ/CORE/VAULT/OPS — it is the only Windows-bound, MT5-adjacent container in the platform (`contracts/11_Execution_Platform.contract.md` §Security Boundary). Bridge's default network posture is outbound-only to the broker endpoint, with no inbound from the internet and no reachability into VAULT, CORE, or OPS.

**One narrow exception, added by ADR-0044:** Bridge → VAULT, **kill-switch tier reads only** (T2 Redis, T3 Postgres), for the send-time kill-switch recheck (contract 11 invariant 19). This is read-only, limited to the two kill-switch tiers, and grants no other VAULT service reachability from Bridge — C24 gains a live read dependency the Architecture already imposes on every order-capable process (ADR-0018's self-halt heartbeat), made explicit here rather than left implicit. This is the only sanctioned Bridge-initiated connection into any other zone; it does not weaken the "only Risk may connect to Execution" rule above, which governs the opposite direction (VAULT/CORE → Bridge) and is unchanged.

## 6. Audit logging and immutable logs

The Decision Record Store (`review/R19_Missing_Components.md` §7) remains the canonical audit mechanism: append-only (DB-role-enforced), hash-chained, content-addressed blobs, queryable by correlation ID, restorable independently of the operational database. Page 20 extends its scope to every model/prompt/weight promotion and rollback; page 18 extends it to every `PortfolioAllocationPlan`, admitted or not — an opportunity-cost record is an audit record.

## 7. Security monitoring, incident response, DR, business continuity

Unchanged from R15 §10-11: the security test suite (secret scanning, dependency/container scanning, the prompt-injection corpus, the authorisation matrix test, the credential-isolation test, the fail-closed chaos suite), and the ten-step compromise runbook (halt, revoke out-of-band, isolate, verify out-of-band, preserve, assess, rotate everything, rebuild from known-good, reconcile, post-mortem). Two additions from pages 17-20:

- **Credential-isolation test, extended:** assert that no process other than Execution can construct a broker client **and** that no process other than the Model Registry can flip an artefact's SM-5 state.
- **Fail-closed chaos suite, extended:** kill the Evidence Graph, the Portfolio Construction Engine, and the Model Registry each in turn; assert the platform refuses to admit new candidates or promote artefacts rather than degrading open, matching the existing assertion for every other dependency.

## 8. Priority summary, extended

| Priority | Controls |
|---|---|
| **P0, before any live capital** | Everything in R15 §12's P0 row, **plus**: the SM-5 promotion gate enforced in the registry service (not CI alone); the `env` interlock hard-failure behaviour (T9); node-level range validation at graph assembly (T7) |
| **P1, before scaling** | Everything in R15 §12's P1 row, **plus**: the correlated-degradation kill-switch trigger tested in the chaos suite (T11); the Schema Registry CI checks live and blocking (T10) |
| **P2** | Everything in R15 §12's P2 row, unchanged |

---

## Related

- `review/R15_Security.md` — T1-T6, and the canonical detail on secrets, insider controls, data protection, API security, and incident response, unmodified
- `17_Evidence_Graph.md` (T7), `18_Portfolio_Construction.md` (T9's namespace isolation, opportunity-cost audit), `20_Model_Registry.md` (T8, T11)
- `review/R19_Missing_Components.md` §2 (Simulation Harness / `env` interlock), §7 (Decision Record Store), §11 (Schema Registry)
- `decisions/0025-fail-closed-is-the-universal-default.md`, `decisions/0037-commands-and-events-are-distinct.md`, `decisions/0040-schema-registry-is-the-wire-contract.md`
- `19_Bounded_Context_Map.md` §BC11 — the identity/governance context enforcing every RBAC check above
- Previous: `20_Model_Registry.md`
- Next: none — pages 17-21 are the final phase; see `README.md` for the Architecture Freeze checklist
