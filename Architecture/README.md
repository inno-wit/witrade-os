# WITrade Quant Platform — Architecture

**Type:** Architecture Freeze v1.0, certified 2026-08-04. Implementation Blueprint v1.0 complete in `../Blueprint/`. No code exists yet.
**Date:** 2026-08-03. **Extended 2026-08-04** with pages 17-21 (Phase 11 — Architecture Completion) and ADRs 0041-0043. **Frozen 2026-08-04** — see [`freeze/Architecture_Freeze_v1.md`](freeze/Architecture_Freeze_v1.md) for the certification, [`../Blueprint/`](../Blueprint/) for the implementation-ready translation.

---

## The freeze and the blueprint

The architecture is frozen at v1.0: `freeze/Architecture_Freeze_v1.md` certifies 109 files, 40 containers, 43 ADRs, 85 event subjects, 12 bounded contexts as internally consistent, mechanically verified, and ready to build against — including one real defect (an empty `16_C4_Container_Diagram.md`) found and restored during the freeze audit itself. `freeze/` holds the eight supporting audit documents (`A.1`-`A.8`): cross-reference validation, canonical-source validation, naming standard, interface compliance, event governance, ADR index, documentation audit, and the freeze certification.

`../Blueprint/` translates the frozen architecture into an implementation-ready engineering blueprint: repository layout, package structure, the full 40-service catalog, API/event/schema contracts, interface definitions, worker architecture, deployment mechanics, a testing hierarchy, an observability plan, a bounded-context-ordered engineering roadmap, a technical debt register, a production-readiness checklist, and a final `Engineering_Handoff_Report.md` (planning readiness: 8.8/10; execution readiness: 0/10, correctly, since no code exists yet).

**Recommended entry point for implementation:** `../Blueprint/Engineering_Handoff_Report.md` §13, or `../Blueprint/Engineering_Roadmap.md` in full.

---

## The rule that shapes this directory

> **Pages 00-16 and ROADMAP.md are never modified.**

Every improvement is a **sibling layer**, and every recommendation is stated as a delta against the specific page it affects. The original design intent stays readable, the changes stay traceable, and no correction quietly overwrites the reasoning it corrects.

That rule is why there are six directories instead of one set of edited files. Pages 17-21 do not break the rule: they are **additive new source pages**, not edits to 00-16, following the identical 12-field template those pages use, enriched from day one with the six contract fields (`contracts/` normally retrofits these onto 01-14; 17-21 ship with them already).

---

## The six layers

| Layer | Files | What it is | Read it when |
|---|---|---|---|
| **Source ADD** | `00_*.md` … `21_*.md`, `ROADMAP.md` (+ `.excalidraw`) | The architecture. 17 original pages (00-16, ~1850 lines, frozen 2026-08-03) + 5 completion pages (17-21, added 2026-08-04) | You want the design intent as written |
| [`review/`](review/) | R00-R19 + README | Pre-implementation review of pages 00-16. Findings, scores, 6 blocking defects, 10 document defects | You want to know what is wrong and why, for the original 17 pages |
| [`decisions/`](decisions/) | 0001-0043 + README | 43 ADRs, all `Accepted`, each with a **tripwire**: the observable condition that reverses it | You want to know why a choice was made, or whether it still holds |
| [`generated/`](generated/) | 15v2, 16v2 + README | Regenerated derived pages: **80 event subjects** (from 43), **39 containers** (from 15) | You are wiring services or deciding what to build |
| [`contracts/`](contracts/) | 01-14 `.contract.md` + README | The six missing contract fields per component page: Owns, Invariants, Interfaces, Degraded Mode, SLO, Security Boundary | You are implementing a component from pages 01-14 |
| [`diagrams/`](diagrams/) | 16v2 + SM1-SM9 `.excalidraw` + README | Visual companions: the 39-container model, and all nine formal state machines the source ADD never defined | You want the shape of a component or machine at a glance |

---

## Phase 11 — Architecture Completion (2026-08-04)

Five new source pages closing the gaps named in the review but never given a canonical home: the Evidence Graph as a real subsystem, a Portfolio Construction Engine to resolve capital competition across concurrent signals, the Bounded Context Map as an operational reference rather than a decision record, one Model Registry governing models/prompts/weights alike, and Security Architecture extended with five new threats (T7-T11) surfaced by the other four pages.

| Page | Title | Promotes | New ADR |
|---|---|---|---|
| [17_Evidence_Graph.md](17_Evidence_Graph.md) | Evidence Graph | `review/R09_Evidence_Graph.md` from finding to canonical subsystem (C15) | [0041](decisions/0041-evidence-graph-is-a-first-class-subsystem.md) |
| [18_Portfolio_Construction.md](18_Portfolio_Construction.md) | Portfolio Construction Engine | `review/R19_Missing_Components.md` §12's deferred Strategy Portfolio Manager, for the capital-competition problem specifically | [0043](decisions/0043-portfolio-construction-is-a-twelfth-bounded-context.md) |
| [19_Bounded_Context_Map.md](19_Bounded_Context_Map.md) | Bounded Context Map | `decisions/0010-eleven-bounded-contexts.md` + `review/R03_Domain_Model_DDD.md` into one at-a-glance operational reference, now twelve contexts | — (references 0010, 0043) |
| [20_Model_Registry.md](20_Model_Registry.md) | Model Registry | Page 07's MLflow mention + `review/R19_Missing_Components.md` §8-9 into one governed service | [0042](decisions/0042-model-registry-governance-with-dual-promotion-gates.md) |
| [21_Security_Architecture.md](21_Security_Architecture.md) | Security Architecture | `review/R15_Security.md`, extended with T7-T11 | — (extends existing security ADRs) |

**Governance rule applied to this phase:** one architectural fact, one canonical source. R09, R03 §2/§10, R15, and page 07's MLflow reference are not duplicated by pages 17-21 — each new page states plainly what it promotes to canonical and what stays where it was (R07 §6's SM-5 transition table, for instance, is referenced by page 20 and not redrawn). See `review/R20_Architecture_Freeze.md` for the full audit of this phase against the rest of the directory.

---

## Start here

**First time:** [`review/R00_Executive_Review.md`](review/R00_Executive_Review.md). Findings, scores, prioritised roadmap. Twenty minutes.

**About to write code:** [`generated/16_Container_Model_v2.md`](generated/16_Container_Model_v2.md) §6. The ten-container minimum viable subset in dependency order.

**Implementing a specific component:** its file in [`contracts/`](contracts/), then the source page it deltas against.

**Wondering why something is the way it is:** [`decisions/`](decisions/). Search the register table in its README.

---

## Headline state

| | |
|---|---|
| Overall maturity at review (pages 00-16 only) | 5.3 / 10 |
| **Overall maturity after Phase 11** (pages 00-21 + all six layers) | **7.4 / 10** — see `review/R20_Architecture_Freeze.md` §1 for the six-dimension scored breakdown against R00's own rubric |
| Blocking defects found | **6**, all with a closing ADR |
| Document defects | 10 found at review; **0 net new** introduced by pages 17-21 (audited, see R20 §5) |
| Event subjects: source → regenerated | 43 → **80** |
| Containers: source → regenerated | 15 → **39** (24 new or split, 4 rescoped), **+1** with Phase 11 (C15 Evidence Graph promoted from "listed" to "specified"; BC12's container is new) |
| ADRs written | **43 of 43, all `Accepted`** (40 from the 2026-08-03 review pass, 3 from Phase 11) |
| Open decisions requiring a human | **None** |
| Bounded contexts with no page in the ADD | Still **3** (Reference Data, Portfolio, Identity — unchanged by Phase 11; see `review/R20_Architecture_Freeze.md` §3 M1). Portfolio Construction (BC12) is a *different*, newly-created twelfth context that gained a page in Phase 11 — it does not close this gap |

**Verdict from the review:** a strong Level-1 design document and roughly half an institutional blueprint. The missing half was almost entirely the half that is expensive to add after code exists, which is why it was done before any. **Verdict after Phase 11:** the five highest-priority completion areas identified in the original brief (Evidence Graph, Portfolio Construction, Bounded Context Map, Model Registry, Security) now have canonical pages; what remains before a v1.0 freeze is narrower and is enumerated in full in `review/R20_Architecture_Freeze.md`.

---

## The six blocking defects, and where each is closed

| | Defect | Closed by |
|---|---|---|
| B1 | Broadcast events used as commands on the order path (duplicate live orders) | ADR-0037, `generated/15_Event_Catalog_v2.md` §4.9 |
| B2 | Kill switch lives only in Redis, fails open | ADR-0018, `contracts/10_*.md` invariant 9 |
| B3 | Circular dependency: Committee desks read from Risk and Execution | ADR-0012, `contracts/08_*.md` invariant 1 |
| B4 | Two components both claim authorisation authority | ADR-0011, `contracts/09_*.md` (the verb change) |
| B5 | Untrusted news text reaches an LLM that allocates capital | ADR-0032, `contracts/01_*.md` invariant 5 |
| B6 | DuckDB used as a shared multi-writer database | ADR-0003, `contracts/13_*.md` |

---

## What must not erode

Preserve these. They are the reason the review is an overlay rather than a rewrite, and each is better than most institutional designs manage:

- The **deterministic/AI boundary**. "The AI reasons. It does NOT calculate." The load-bearing constraint of the whole platform.
- **Desk isolation by construction**: six separate API calls, not one mega-prompt.
- **Deadlock resolves to no-trade**, with the asymmetry argued rather than assumed.
- **The kill switch is synchronous and in-process**, and does not auto-liquidate.
- **Quality scoring with a reviewable quarantine**, not silent drops.
- **PBO/DSR gating the learning loop's own proposals**, without exception.
- **Broker truth over internal ledger.**
- **Broker-agnostic adapter from day one**, and **idempotent client-generated order IDs**.

### Eight decisions that are fixed points

These ADRs carry **no reversal tripwire**, deliberately. If a future change proposes reversing one, the change is wrong. Three of them (0015, 0016, 0022) still carry operational tripwires worth monitoring; the decision itself is what is pinned.

| ADR | Fixed point |
|---|---|
| 0015 | Reference data does not become configuration again |
| 0016 | A platform that manages entries and not exits is incomplete |
| 0017 | The kill switch does not become asynchronous |
| 0019 | Exits are never blocked |
| 0022 | Positions do not go unprotected |
| 0023 | The platform does not auto-liquidate |
| 0035 | The clock lint is not suppressed |
| 0037 | Nothing that moves capital is a broadcast event |

### Two metrics that are load-bearing

`per_desk_resolution` (ADR-0028) and `committee_vs_baseline_on_disagreements` (ADR-0027). Together they are the only things that make the AI committee's existence **falsifiable** rather than assumed. Protect them.

---

## Conventions, if you extend this

- No em dashes in prose. Commas, colons, parentheses. (Em dashes appear only as title and list separators.)
- Mermaid for every diagram.
- Every file ends with `## Related`, cross-linking siblings.
- Every recommendation is a delta against a **specific** source page.
- Priority tiers: **P0** (before any code) · **P1** (before live capital) · **P2** · **P3 with tripwire**.
- Every accepted tradeoff carries a written **tripwire**: the observable condition that reverses it.

---

## Next

1. ~~Accept the remaining 39 ADRs.~~ **Done 2026-08-03.** All 40 are `Accepted`. No open forks.
2. ~~Excalidraw diagrams for the new containers and state machines.~~ **Done 2026-08-03.** See [`diagrams/`](diagrams/) — the sixth sibling layer.
3. ~~Complete the five highest-priority architecture gaps: Evidence Graph, Portfolio Construction, Bounded Context Map, Model Registry, Security.~~ **Done 2026-08-04.** Pages 17-21, ADRs 0041-0043. See "Phase 11" above.
4. **Read `review/R20_Architecture_Freeze.md`.** It is the 2026-08-04 audit of the whole directory (all six layers plus Phase 11) against the v1.0 Architecture Freeze checklist — what's authoritative now, what's still genuinely open, and the minimum artefact set required before implementation begins.
5. **Begin implementation.** `review/R19_Missing_Components.md` §14 and `generated/16_Container_Model_v2.md` §6 give the ten-component minimum viable subset in dependency order, starting with the Clock. Not started — check in before beginning, since this is the transition from design-only to code-exists.

---

## Related repos, not to be confused with this one

| Repo | What it is |
|---|---|
| `../Wit-Hedge-fund` | Running code. MT5/Windows, LLM committee |
| `../wit-nautilus` | Linux port over Interactive Brokers |
| `../TradeHub` | WiTrade Terminal, journaling and analytics |
| `../trading-suite` | Source repo for the trading skill pack |

**Decisions in this directory do not automatically apply to any of them.**
