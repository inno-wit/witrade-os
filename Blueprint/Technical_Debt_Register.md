# Technical Debt Register

**Blueprint deliverable:** B.13
**Consolidates:** every disclosed gap from `../Architecture/freeze/*` (Phase A) plus the risks named per-phase in `Engineering_Roadmap.md` §2, in one register rather than scattered across nine files — the single-list discipline `../Architecture/freeze/Architecture_Freeze_v1.md` §8 rule 4 already commits to.
**Status:** Blueprint v1.0, 2026-08-04
**Amended:** 2026-08-06 — §6's kill-switch CI-lint row widened by [ADR-0044](../Architecture/decisions/0044-kill-switch-recheck-at-broker-send.md) to cover the new C24 send-time check, not only the original C21 mint-time check.

---

## 1. Known risks (architecture-level, inherited from the freeze)

| # | Risk | Source | Priority | Mitigation |
|---|---|---|---|---|
| TD1 | BC2 (Reference Data), BC7 (Portfolio) have no dedicated architecture page | `../Architecture/freeze/Architecture_Freeze_v1.md` §6 item 12 | P1 | Write the two pages before implementation starts on either context specifically (Phases 4 and 10) |
| TD2 | No standalone data dictionary | `../Architecture/freeze/Canonical_Source_Validation.md` §1 row 8 | P2 | Generate from the Schema Registry once C37 exists |
| TD3 | `../Architecture/generated/15`/`16` remain hand-maintained | `../Architecture/freeze/Architecture_Audit_Report.md` §3 | P2 | Machine-generate once C37 and deployment manifests exist |
| TD4 | No Testing Strategy / Version field on any architecture page | `../Architecture/freeze/Interface_Compliance_Report.md` §4 | P2 | Addressed at implementation level by `Testing_Blueprint.md`; architecture-page retrofit deferred to a v1.1 pass |
| TD5 | 23 loose backtick citations in pre-2026-08-04 review files | `../Architecture/freeze/Architecture_Cross_Reference_Report.md` §2.2 | P3 | Normalise opportunistically at next substantive edit of each file |
| TD6 | `../Architecture/review/R06_Sequence_Diagrams.md` W6 predates the Tier-0 dual-gate; W12 not yet filed there | `../Architecture/freeze/Canonical_Source_Validation.md` §4 | P2 | Fold both into R06 at the next sequence-diagram review pass |
| TD7 | No running "superseded by" index across the six documentation layers | `../Architecture/freeze/Architecture_Audit_Report.md` §4 | P3 | Candidate for v1.1 — one file, one line per promotion |
| TD8 | No file-integrity check existed before this freeze (the page-16 incident) | `../Architecture/freeze/Architecture_Cross_Reference_Report.md` §0 | **P1** | **Now closed at the implementation level** — `Testing_Blueprint.md` §6 wires the cross-reference/integrity linter into CI |

## 2. Deferred decisions (explicit, from the ADR register)

| # | Deferred item | ADR | Tripwire that reopens it |
|---|---|---|---|
| DD1 | Multi-tenancy | ADR-0009 | DSR > 0.95 confidence on live returns, 200+ cycles, PBO < 0.5 |
| DD2 | Kafka/Redpanda over NATS JetStream | (P3 table, `../Architecture/review/R00_Executive_Review.md`) | Replay-from-genesis becomes routine, retention >90 days, or cross-partition ordering needed |
| DD3 | Compiled hot path (Rust/C++) | Same | Target timeframe drops below 1 minute, or p99 order path exceeds 50% of budget |
| DD4 | Kubernetes over Docker Compose | ADR-0008 | More than ~15 containers needing orchestration beyond Compose, or more than one node |
| DD5 | Temporal.io over custom DAG runner | `../Architecture/00_Master_Architecture.md` | Workflow complexity exceeds ~10 types or needs human-in-the-loop long timers |
| DD6 | Strategy Portfolio Manager (cross-strategy allocation) | `../Architecture/review/R19_Missing_Components.md` §12, superseded for single-strategy capital competition by BC12 | A second strategy actually exists |
| DD7 | Exit Committee (reasoning-based exit management) | Same file | OMS rule-based management proven, enough recorded counterfactuals to evaluate reasoning against rules |

## 3. Future refactors, named and scoped

| # | Refactor | Trigger | Scope if triggered |
|---|---|---|---|
| FR1 | Evidence Graph storage promotion (`networkx` in-memory → Postgres CTE → dedicated graph store) | Cross-cycle multi-hop queries become routine, CTE latency >1s | `../Architecture/17_Evidence_Graph.md` §"Technology" already specifies the staged path |
| FR2 | Ensemble model slots (multiple simultaneous champions) | Enough validated models exist per slot to blend | `../Architecture/20_Model_Registry.md` §"Future Expansion" — the `slot` concept already accommodates this without a schema change |
| FR3 | Cross-symbol confluence detection in the Evidence Graph | Instrument Master's cluster map is live and proven | `../Architecture/17_Evidence_Graph.md` §"Future Expansion" |
| FR4 | Portfolio-level Kelly optimisation across correlated candidates simultaneously | BC12 proven stable with per-candidate fractional Kelly | `../Architecture/18_Portfolio_Construction.md` §"Future Expansion" |

## 4. Scalability risks

| Risk | Where it bites first | Mitigation status |
|---|---|---|
| No admission-control algorithm implemented for the Committee/Cost Governor beyond naming the container | Phase 8 (highest LLM-spend phase) | Named in `../Architecture/freeze/R20` and `../Architecture/freeze/Architecture_Freeze_v1.md` §1 as residual — Phase 8's acceptance criteria in `Engineering_Roadmap.md` requires the Cost Governor wired before the first live call |
| No proven horizontal-scaling test for any service | All phases | `Testing_Blueprint.md` §1 includes Load as a standing test level, run before any capacity-affecting change |

## 5. Operational risks

Directly inherited from `../Architecture/review/R11_Risk_Architecture.md` §10 — duplicate orders, split brain, stale decisions, config errors, broken deploys, replayed events, silent component failure, ledger corruption, credential compromise, operator error under stress. **Not restated here** (canonical source rule) — every one already has a named control in that section, and `Testing_Blueprint.md` §1's Chaos level is where each control gets exercised.

## 6. Architecture risks

| Risk | Mitigation |
|---|---|
| BC12 could be miscoded to call BC6's internals directly, silently reopening the authorisation-authority question ADR-0043 closes | `Testing_Blueprint.md` §4's credential-isolation test extension, CI-enforced, every commit |
| A future engineer "cleans up" the synchronous kill-switch check into an async pattern for consistency — **at either check point**: the original mint-time check in C21 (ADR-0018), or the send-time check in C24 added by ADR-0044 (contract 11 invariant 19) | ADR-0017's own Tripwire section: "none" — a fixed point, and the CI lint from `../Architecture/decisions/0035` (Clock injection) pattern should be extended to flag any `await` inserted after **either** kill-switch check, not only the C21 one. The C24 check is the newer and less battle-tested of the two, so it is the more likely site for this mistake |
| A future engineer applies the C24 kill-switch recheck (invariant 19) **unconditionally**, without the `intent == ENTRY` scope, silently violating ADR-0019 | `Testing_Blueprint.md` §4.2 — named entry, required test (`test_trip_between_mint_and_send_does_not_block_exit`), and a code-review checklist item: any diff touching the C24 check must show the `ENTRY` guard in the same diff |
| Model/prompt Tier-0 dual-gate bypassed under deployment pressure | `Testing_Blueprint.md` §1 Security level, the authorisation-matrix test, extended per `../Architecture/21_Security_Architecture.md` §7 to cover promotion specifically |

## 7. Priority summary

| Priority | Count | Items |
|---|---:|---|
| P0 | 0 | None — the freeze certified zero blocking items |
| P1 | 2 | TD1, TD8 (TD8 now closed at implementation level, tracked as resolved) |
| P2 | 4 | TD2, TD3, TD4, TD6 |
| P3 | 2 | TD5, TD7 |

---

## 8. Related

- `../Architecture/freeze/Architecture_Freeze_v1.md` §6, §8 — the source items this register consolidates
- `Engineering_Roadmap.md` §2 — the per-phase risks this register's §1/§6 draw from
- `Production_Readiness.md` — where P1 items become explicit go/no-go gates
