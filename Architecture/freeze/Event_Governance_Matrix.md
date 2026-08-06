# Event Governance Matrix

**Freeze deliverable:** A.5
**Canonical source this matrix validates, not duplicates:** `../generated/15_Event_Catalog_v2.md` — every subject's full row (publisher, consumers, stream, ordering key, idempotency identity) lives there. This document is the **governance check** run against that catalog, summarised per bounded context, not a second copy of the 85 rows.
**Status:** Freeze v1.0 input, 2026-08-04

---

## 1. The six properties checked

Per the brief: every event exists once, has one owner, one schema, one version, one lifecycle, one publisher. Checked mechanically against all 85 subject rows in `../generated/15_Event_Catalog_v2.md`.

| Property | Method | Result |
|---|---|---|
| **Exists once** | Subject identifiers extracted from every table row, checked for duplicates | ✅ 85 rows, 85 distinct identifiers (84 literal + 1 parameterised template, `cmd.<target_context>.run_job.v1` — see `Architecture_Cross_Reference_Report.md` §3.3) |
| **One schema** | Every row's idempotency-identity column (`{field, field, ...}`) checked for a subject defined with two different field sets across two rows | ✅ No subject appears in more than one row, so no subject has two schemas |
| **One version** | Version suffix (`.v1`, `.v2`, ...) extracted from every subject | ✅ **All 85 subjects are `.v1`.** No subject has shipped a `.v2` yet, and none should before code exists — this is the expected, correct state pre-implementation, not a gap |
| **One lifecycle** | Every subject's `Kind` (Command `C` vs Event `E`) checked for consistency | ✅ 7 commands, 78 events, no subject is classified as both a command in one place and an event in another |
| **One publisher** | Publisher column extracted per subject, checked for more than one distinct publishing context | 🟡 **2 of 85 subjects list more than one publisher-side actor.** Both checked individually — see §2. Neither is a violation; one is a parsing nuance, one is a documented, intentional design exception |
| **One owner (bounded context)** | Every subject's owning context cross-checked against `../19_Bounded_Context_Map.md`'s ownership matrix | ✅ Every subject traces to exactly one of the fourteen owner labels used in `../generated/15_Event_Catalog_v2.md` §4.1-4.14 and §4.8b, each of which maps to exactly one bounded context |

**5 of 6 properties hold with zero exceptions. The sixth (one publisher) holds with one real, intentional, and correctly-designed exception**, detailed below rather than glossed over.

---

## 2. The two multi-actor subjects, examined individually

### `evt.market_data.bar.ingested.v1` — not a violation, a parsing nuance

Listed as published by "Ingestion, all sources." Read in context (`../generated/15_Event_Catalog_v2.md` line 92), this describes **one publishing container** (C01, the Ingestion Service) whose input side aggregates multiple upstream vendors (MT5, Databento, Polygon). "All sources" qualifies which market-data feeds the one publisher normalises, not which contexts are allowed to emit this subject. **Single publisher, confirmed.**

### `cmd.platform.halt.v1` — a real, intentional, documented exception

Listed as published by "Risk Engine, Operator" — genuinely two distinct actors, both of whom may legitimately issue this command. This is not an oversight: it is the direct implementation of the asymmetric-friction principle stated in `../review/R15_Security.md` §3 and repeated throughout the risk architecture (`../review/R11_Risk_Architecture.md` §7) — **stopping the platform is deliberately easier than starting it**, so both the automated Risk Engine and a human Operator carry independent authority to trip the kill switch, with no confirmation required. Clearing it afterward is the asymmetric counterpart and requires dual control (a different subject, `cmd.platform.resume.v1`, correctly single-publisher: Operator only).

**Governance ruling: this is a sanctioned exception to single-publisher, not a defect.** It is recorded here explicitly so a future automated governance linter has a documented allow-list entry rather than perpetually re-flagging a false positive, and so no one "fixes" it into single-publisher and quietly removes the safety property it exists to provide.

---

## 3. Ownership summary, by bounded context

One row per owning context (matching `../generated/15_Event_Catalog_v2.md`'s own §4.1-4.14 plus §4.8b), stating subject count and confirming single ownership. Full subject lists remain in the catalog; this table is the governance summary, not a restatement.

| Bounded context | Owning container(s) | Subject count | Single-owner confirmed |
|---|---|---|---|
| BC2 Reference Data | Instrument Master (C04) | 4 | ✅ |
| BC1 Market Data | Ingestion (C01), Quality (C03) | 9 | ✅ |
| BC3 Feature Engineering | Feature Serving (C06/C07) | 2 | ✅ |
| BC4 Market Intelligence | Regime/Vol/Structure/Model (C09-C14) | 13 | ✅ |
| BC5 Deliberation | Committee (C16), Decision Saga (C19), Evidence Graph (C15), Record Store (C20) | 5 | ✅ |
| **BC12 Portfolio Construction** | **Portfolio Construction Engine (C40) — Phase 11** | **5** | ✅ |
| BC6 Risk Authorisation | Risk Engine (C21) | 9 | ✅ (1 sanctioned exception, §2) |
| BC8 Order Execution | Execution Service (C24), OMS (C23) | 8 | ✅ |
| BC7 Portfolio | Position Ledger (C22) | 11 | ✅ |
| BC7/BC8 Reconciliation | Reconciliation Service (C25) | 3 | ✅ |
| BC10 Platform Operations | Platform Supervisor (C26), Scheduler (C35), Saga runner | 6 | ✅ |
| BC10/BC9 Cost, Observability, Learning, Delivery | Cost Governor, Observability, Learning Service, CI/CD | 10 | ✅ |

**Total: 85 subjects, 12 owning bounded-context groupings, zero cross-context claims.** This table's row count (12 groupings) is lower than the 14 sections in `../generated/15_Event_Catalog_v2.md` because two of that file's sections (§4.9 Risk, §4.12 Reconciliation) are each single-context and combine cleanly here; none of the collapsing hides a real ownership conflict — verified by checking that every collapsed pair shares one owning context.

---

## 4. What this validates that `../generated/15` alone does not state explicitly

`../generated/15_Event_Catalog_v2.md` is the catalog. It does not, in its own text, assert "no subject is duplicated" or "no subject has two publishers" as a checked, dated fact — those properties are implied by its structure but never stated as a pass/fail result. This document is that pass/fail result, run once, dated, and reproducible (the same Python-based extraction method as `Architecture_Cross_Reference_Report.md` §7).

---

## 5. Related

- `../generated/15_Event_Catalog_v2.md` — the canonical catalog this matrix validates
- `Architecture_Cross_Reference_Report.md` §3.3 — the duplicate-subject mechanical check this document's §1 row 1 restates as a governance property
- `../19_Bounded_Context_Map.md` — the ownership model §3's grouping is checked against
- `../review/R15_Security.md` §3, `../review/R11_Risk_Architecture.md` §7 — the asymmetric-friction design that makes §2's kill-switch exception intentional, not accidental
