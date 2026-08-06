# Naming Standard

**Freeze deliverable:** A.3
**Method:** every subsystem name in the brief's list, plus the names that scan revealed as genuine variants, counted by file-occurrence across all 109 markdown files (`grep -rl`), then read in context to separate true drift from legitimate altitude differences (a bounded-context name is not the same thing as a container name is not the same thing as a page title, and all three can legitimately differ for the same subject).
**Status:** Freeze v1.0 input, 2026-08-04

---

## 1. How to read this document

A name appearing in more than one form is not automatically a defect. Three different, all-correct things can share a subject: the **page title** (what the ADD calls it), the **bounded context name** (what the DDD model calls it, per `../19_Bounded_Context_Map.md`), and the **container name** (what the deployable service is called, per `../generated/16_Container_Model_v2.md`). Page 10 is titled "Risk & Portfolio Management"; its bounded context is "Risk Authorisation" (BC6); its container is "Risk Engine" (C21). All three are correct and all three answer a different question. This document's job is to catch **accidental** drift — two names for the same thing at the same altitude — not to flatten a model that has legitimate layers.

---

## 2. Canonical names table

One row per subsystem named in the brief. **Canonical** is the name this freeze adopts going forward for prose at the "subsystem" altitude (the level pages 00-21 titles and everyday references operate at). Bounded-context and container names are unchanged by this table — see §1.

| # | Subsystem | Canonical name (this freeze) | Variants found | Occurrences | Verdict |
|---|---|---|---|---|---|
| 1 | The AI committee | **AI Investment Committee** | (none — checked explicitly, see §3.1) | 20 files, 100% consistent | ✅ Already standard |
| 2 | The reasoning-over-evidence layer | **Decision Intelligence** | "Decision Intelligence Layer" (page 09's exact title) | 20 vs 10 | Legitimate — "Layer" is the page-title form, "Decision Intelligence" the shorthand. Not drift, a formal/informal pair |
| 3 | The graph subsystem | **Evidence Graph** | (none) | 32 files, 100% consistent | ✅ Already standard |
| 4 | Pages 04-07 collectively | **Quant Research Platform** | "Research Platform" (shorthand, drops "Quant") | 23 vs 24 | **Real minor drift.** "Research Platform" alone is used almost as often as the full name and is ambiguous against "Learning Platform" / "Continuous Learning" (a different subsystem, page 12). **Standardise on "Quant Research Platform" at first mention per document; "the Research Platform" is acceptable shorthand only after that first mention in the same file** |
| 5 | The capital-competition engine | **Portfolio Construction Engine** | "Portfolio Construction" (shorthand, drops "Engine") | 8 vs 18 | Legitimate — matches pattern in row 2. "Portfolio Construction" is the bounded-context-adjacent short form; "Engine" is the full container-level name. **Not to be confused with "Portfolio" alone (BC7, the ledger) — see §3.2, the one naming risk this freeze treats as more than cosmetic** |
| 6 | Page 10 / BC6 | **Risk Platform** (this freeze's adopted umbrella term, matching the brief's own usage) | "Risk & Portfolio Management" (page 10's literal title, frozen, unmodified), "Risk Management" (page 00's usage), "Risk Authorisation" (BC6's DDD name) | 4 / 7 / 16 / 16 | **Genuine three-way drift, but each variant is anchored to a different, correct altitude — see §3.3 for the resolution, which is not "pick one" |
| 7 | Order/broker interaction | **Execution Platform** | "Execution Engine" (page 00's original title), "Execution Service" (the container name, C24) | 14 / 7 / 17 | Same pattern as row 6 — see §3.3 |
| 8 | The registry unifying models/prompts/weights | **Model Registry** | (none) | 18 files, 100% consistent | ✅ Already standard (this is Phase 11's own coinage, checked for self-consistency during drafting) |
| 9 | Metrics/logs/traces/alerts | **Observability** (as the subject; "Monitoring & Observability" is page 13's section title) | "Monitoring & Observability" (2 files, page 00 and page 13 headers only) | 2 vs the general term "Observability" used throughout `../review/R12_Observability.md` and elsewhere | Legitimate — "Monitoring & Observability" is a section heading in exactly the two places that need one; every other mention correctly uses the shorter "Observability" |
| 10 | FastAPI/Redis/DuckDB/etc. | **Infrastructure Platform** | (checked: no competing variant found — "Infrastructure" alone is used generically but never as a conflicting subsystem name) | 6 files use the full term | ✅ No action needed |

---

## 3. The three findings that matter

### 3.1 AI Investment Committee — a false alarm worth recording

A naive substring search for "Investment Committee" returns the same 20 files as "AI Investment Committee," which briefly looked like a second, un-prefixed variant. Checked line-by-line: **every occurrence of "Investment Committee" in the directory is immediately preceded by "AI."** Zero real variance. Recorded here so a future automated linter doesn't need to rediscover this — the substring check alone is not sufficient evidence of drift, a same-context recheck is required.

### 3.2 "Portfolio" vs "Portfolio Construction" — the one naming risk worth active mitigation

This is not a documentation-consistency finding, it is a **comprehension-risk finding**, and it is the same risk that produced a real, disclosed self-correction during Phase 11 (`../review/R20_Architecture_Freeze.md` §"self-correction," `../review/README.md` line 31): **BC7 ("Portfolio," the position ledger) and BC12 ("Portfolio Construction," the capital-allocation engine) share a word and nothing else.** No file in the current directory conflates them (checked: zero matches for a BC7/BC12 cross-reference error, per `Architecture_Cross_Reference_Report.md` §3.4). But the naming itself invites the mistake, and it will recur as new engineers onboard.

**Recommendation, not a rename:** page 07 (BC7) is frozen and its bounded-context name ("Portfolio") is set by ADR-0010, which is immutable once accepted. Renaming BC7 is out of scope for a "no new features, no redesign" freeze. Instead: **§4 below mandates that every package, service, and API path for BC7 uses the word "ledger" or "book" in its identifier, never bare "portfolio," reserving "portfolio" as a bare term for BC12 in code identifiers specifically** — the documentation names stay as designed (ADR-0010 is not touched), but the code-level naming this freeze hands off to implementation actively avoids the collision the prose names create. See `../../Blueprint/Package_Blueprint.md` for the applied naming (`ledger-service` for BC7, `portfolio-construction-service` for BC12).

### 3.3 Risk and Execution — three correct names is not drift, it's altitude

Rows 6 and 7 both show the same shape: a page title, a looser page-00-era shorthand, and a precise DDD/container name, all in real use. The fix here is not consolidation, it's **documenting the altitude rule explicitly so a future writer doesn't "fix" it into one name and lose information**:

| Altitude | Risk example | Execution example | When to use it |
|---|---|---|---|
| Page title (frozen, exact) | "Risk & Portfolio Management" | "Execution Platform" (page 11's actual title) | Citing the page itself: "see page 10" |
| Prose/umbrella term | "Risk Platform" | "Execution Platform" | General discussion, not citing a specific artefact |
| Bounded context (DDD) | "Risk Authorisation" (BC6) | "Order Execution" (BC8) | Domain-model discussion, `../19_Bounded_Context_Map.md` context |
| Container (deployable) | "Risk Engine" (C21) | "Execution Service" (C24) | Implementation, deployment, `../generated/16` discussion |

**This table, not a single canonical string, is the naming standard for these two subsystems.** A linter checking "is this the right name" should check "is this the right name for this altitude," not "does this match one approved string."

---

## 4. Standard going forward

1. Use the Canonical name column (§2) at first mention in any new document; shorthand is acceptable after that.
2. For Risk and Execution specifically, use §3.3's altitude table rather than picking one string.
3. Never use bare "Portfolio" for BC12 in a code identifier, service name, or API path (§3.2) — reserve it for BC7. In prose, "Portfolio Construction (Engine)" is sufficiently disambiguated already and needs no further restriction.
4. This document is descriptive of the state at freeze time, not a rename mandate — no existing frozen page (00-16, ROADMAP.md) or Accepted ADR is edited to conform to it.

---

## 5. Related

- `Architecture_Cross_Reference_Report.md` §1 — the terminology-variant count this document expands into full findings
- `../19_Bounded_Context_Map.md` — the bounded-context names §3.3's table cites
- `../generated/16_Container_Model_v2.md` — the container names §3.3's table cites
- `../../Blueprint/Package_Blueprint.md` — where §3.2's code-level naming mitigation is actually applied
