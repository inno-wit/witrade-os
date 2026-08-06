# Interface Contracts — WITrade Quant Platform

**Type:** Contract completion overlay on pages 01-14
**Source pages:** unmodified
**Delta against:** the 12-field per-component template applied across pages 01-14
**Date:** 2026-08-03

---

## What this is

The ADD's 12-field template (Purpose, Responsibilities, Inputs, Outputs, Dependencies, Events Published, Events Consumed, Failure Modes, Recovery Strategy, Latency Budget, Technology, Future Expansion) is good and applied consistently across all fourteen component pages. That consistency is a genuine asset and none of it is changed here.

Six fields are missing, and their absence is what keeps the pages **descriptive** rather than **binding**. This directory adds those six per page, as a sibling file rather than an edit, so pages 01-14 stay byte-identical and every addition stays a traceable delta.

| Missing field | What its absence causes |
|---|---|
| **Interfaces** | Every page says what a component does. No page says how to call it. Implementation invents signatures per subsystem |
| **Owns (exclusive)** | Nobody can tell which component may write which table. This is how six components each ended up holding their own idea of a position |
| **Invariants** | Failure Modes describes what can go wrong. Invariants describe what must never be true. Only the second is testable |
| **Degraded Mode** | Recovery Strategy assumes recovery. It does not say how a component behaves **while still broken**, which is its state during every real incident |
| **SLO** | A latency budget without a percentile or an availability target is not measurable (finding D2) |
| **Security Boundary** | No page states who may call it, what secrets it holds, or what it trusts |

**The two that matter most and are hardest to retrofit are Invariants and Degraded Mode.** Everything else can be added after code exists. Those two shape the code.

---

## Files

| Contract | Source page | Containers | Tier | Highest-value field added |
|---|---|---|---|---|
| [01 Data Ingestion](01_Data_Ingestion.contract.md) | `../01_Data_Ingestion.md` | C01 | 1 | **Owns** |
| [02 Data Quality](02_Data_Quality_Engine.contract.md) | `../02_Data_Quality_Engine.md` | C03 | 1 | **Invariants** |
| [03 Feature Store](03_Feature_Store.contract.md) | `../03_Feature_Store.md` | C06, C07 | 1 | **Interfaces** |
| [04 Regime Engine](04_Regime_Engine.contract.md) | `../04_Regime_Engine.md` | C09 | 1 | **Degraded Mode** |
| [05 Volatility Engine](05_Volatility_Engine.contract.md) | `../05_Volatility_Engine.md` | C10 | 1 | **Degraded Mode** |
| [06 Market Structure](06_Market_Structure_Engine.contract.md) | `../06_Market_Structure_Engine.md` | C11 | 1 | **Degraded Mode** |
| [07 ML / RL Layer](07_ML_RL_Model_Layer.contract.md) | `../07_ML_RL_Model_Layer.md` | C12, C13, C14 | 1/2 | **Owns** |
| [08 AI Committee](08_AI_Investment_Committee.contract.md) | `../08_AI_Investment_Committee.md` | C16, C17, C18 | 1 | **Invariants** |
| [09 Decision Intelligence](09_Decision_Intelligence_Layer.contract.md) | `../09_Decision_Intelligence_Layer.md` | C15, C19, C20 | 0/1 | **Interfaces**, plus the verb change |
| [10 Risk & Portfolio](10_Risk_Portfolio_Platform.contract.md) | `../10_Risk_Portfolio_Platform.md` | C21, C22 | **0** | **Security Boundary** |
| [11 Execution](11_Execution_Platform.contract.md) | `../11_Execution_Platform.md` | C23, C24, C25 | **0** | **Degraded Mode** |
| [12 Continuous Learning](12_Continuous_Learning.contract.md) | `../12_Continuous_Learning.md` | C27, C28 | 2 | **Invariants** |
| [13 Infrastructure](13_Infrastructure_Platform.contract.md) | `../13_Infrastructure_Platform.md` | C08, C31, C36-C39 | mixed | **SLO** |
| [14 Deployment](14_Deployment_Pipeline.contract.md) | `../14_Deployment_Pipeline.md` | CI/CD, C26 | — | **Invariants** |

---

## Three rules every file follows

**1. What the source page gets right is stated before what it misses.**
Several of these pages contain decisions better than most institutional designs manage: desk isolation by construction (08), the synchronous kill switch and no auto-liquidation (10), broker-agnostic adapters and idempotent order IDs (11), the no-shortcut PBO/DSR rule (12), gates enforced in tooling rather than by discipline (14), the storage tier boundary (13). Each file names these first, because a contract that only lists gaps invites a future reader to rewrite the parts that were already correct.

**2. Every Degraded Mode row states consumer behaviour, not just component behaviour.**
This is where the source pages stop, and it is the single largest category of addition here. Pages 02, 03, 04, 05 and 06 all say a consumer "is required to" discount stale or flagged data. A requirement that crosses a service boundary as an expectation is not a requirement. Every table below names what the consumer actually does.

**3. Two rules recur across the engine contracts and are worth reading once:**

> **Staleness reduces confidence; it never substitutes a default.** A value returned because nothing better was available is a fabricated input to a capital decision.

> **An unavailable input is an abstention, never a neutral vote.** They differ in the quorum arithmetic, and treating them alike lets a broken engine silently swing a decision.

---

## Where these contracts change behaviour, not just documentation

Most of this directory makes implicit things explicit. Eleven places state something the source pages do not, and each is a behaviour decision:

| Contract | Change |
|---|---|
| 01 | Economic calendar stale beyond 6h **fails closed** and blocks new entries. Page 01 treats calendar as best-effort |
| 02 | Incomplete detector set **caps the score at FLAG**. A dataset never reaches PASS with detectors missing |
| 03 | Stale volatility means **conservative sizing**; stale anything critical means the cycle does not run |
| 04 | The trivial baseline model is **always registered and always scored** |
| 05 | Volatility engine down means **new entries are declined**, never sized on a fixed-lot fallback |
| 06 | A confluence trigger rate of zero for 4 market hours is **P1**, because a silent structure engine looks exactly like a quiet market |
| 07 | **Correlated drift across slots auto-trips the kill switch.** Single-slot drift alerts and never auto-demotes |
| 08 | **Quorum of 4 of 6**, and critical staleness is a **veto** rather than a discount |
| 09 | Decision Record Store unavailable is a **hard stop** on new proposals |
| 10 | Kill switch **fails closed** on any tier being unreachable, and exits are structurally exempt from entry rules |
| 12 | Fewer than 30 closed trades in a window produces a review that generates **no hypotheses** |

---

## Reading order

**Implementing:** 10 → 11 → 09. The capital plane and the layer that feeds it. These three contain every Tier 0 invariant.

**Wiring the data platform:** 01 → 02 → 03. The write-set boundaries are the point; read them together or the ownership resolution does not make sense.

**Working on the committee:** 08, then 09 for what happens to its output, then 12 for what happens to its calibration.

**One file only:** 10. It has the largest concentration of things that are expensive to get wrong.

---

## What still has no contract

The new containers have full contracts in the review rather than here, because they have no source page to be a delta against:

| Container | Contract |
|---|---|
| C04 Instrument & Reference Data Master | `../review/R05_Interface_Contracts.md` §3 |
| C22 Account & Position Ledger | `../review/R05_Interface_Contracts.md` §4 |
| C23 OMS | `../review/R05_Interface_Contracts.md` §5 |
| C17 LLM Gateway | `../review/R05_Interface_Contracts.md` §7 |
| C25 Reconciliation Service | `../review/R05_Interface_Contracts.md` §8 |
| C26 Platform Supervisor | `../review/R05_Interface_Contracts.md` §9 |
| C30 Cost Governor | `../review/R05_Interface_Contracts.md` §10 |

Three bounded contexts still have no page anywhere in the ADD: **Reference Data, Portfolio, Identity.** Their containers are contracted; the contexts are not documented at page level. That remains open.

---

## Related

- `../review/R05_Interface_Contracts.md` — the corrected template and the §11 priority table this directory implements
- `../generated/16_Container_Model_v2.md` — the containers these contracts describe
- `../generated/15_Event_Catalog_v2.md` — the v2 subjects referenced throughout
- `../decisions/README.md` — the ADRs each invariant cites
- Source pages, unmodified: `../01_Data_Ingestion.md` … `../14_Deployment_Pipeline.md`
