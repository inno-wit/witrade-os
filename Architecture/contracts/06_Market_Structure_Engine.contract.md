# 06 — Market Structure Engine, contract completion

**Delta against:** `../06_Market_Structure_Engine.md` (unmodified)
**Adds:** Owns, Invariants, Interfaces, Degraded Mode, SLO, Security Boundary
**Container:** C11 · **Context:** Quant Research · **Criticality:** Tier 1 · **Group:** Quant
**Highest-value field for this page (R05 §11):** **Degraded Mode.** Also the page with the most consequential ownership gap: grid parameters have no owner

---

## Owns (exclusive write access)

| Asset | Note |
|---|---|
| `structure_snapshots` (Postgres + published to Iceberg via C06) | Per `(symbol, timeframe, as_of, detector_version)` |
| `order_blocks`, `fair_value_gaps`, `liquidity_zones` (Postgres) | With mitigation status and the timeframe it was assessed on |
| `structure_confidence` (Postgres) | Composite score with its component breakdown |
| **Not owned:** grid parameters | See below. These belong to the Instrument Master (C04) |

**The grid parameter correction.** Page 06 names "grid math drift" as a failure mode and says parameters are "stored as versioned per-symbol config" without saying where or who versions them. Versioned config with no owner is a constant with extra steps. Grid step, shift, and thin/thick thresholds are per-symbol instrument characteristics, which makes them reference data: they live in the Instrument Master alongside tick size and contract size, effective-dated, and this engine reads them through `get_spec(symbol, as_of)`.

That placement also fixes the point-in-time hole. A grid parameter changed in March must not silently reshape a confluence score computed for a January bar during a replay.

## Invariants

1. This engine reports **facts, never rules**. It publishes per-timeframe structure. It does not apply the top-down bias rule. Page 06 states this correctly and it is preserved verbatim as an invariant: enforcing Daily plus 4H alignment is the SMC Desk's job.
2. Mitigation status is always computed from the finest available timeframe, and every mitigation record names the timeframe it was assessed on. An unmitigated OB assessed only on 4H data is a different claim from one assessed on 5m data, and the difference is exactly the intrabar-fill blind spot page 06 identifies.
3. Point-in-time: structure at `as_of` uses only bars with `event_time <= as_of`, and the detector version, swing length, and grid parameters in force at `as_of`.
4. Swing length is resolved from the previous bar's regime, never the current one.
5. Every structure object carries `(detected_at, detector_version, timeframe, mitigation_assessed_on, price_level)` and price levels are `Decimal`.
6. Confluence confidence is reproducible: the same bars, parameters, and detector version produce the identical score. Asserted in CI, because this score gates committee cycles and a non-reproducible trigger makes every replay diverge from the live run.
7. `smartmoneyconcepts` is one `StructureDetector` implementation behind an interface, never a direct import in engine logic.

Invariant 7 is cheap now and expensive later. The library is a hard dependency in the source design, and it is a third-party package making judgement calls (what counts as a swing, what counts as displacement) that this platform may eventually want to own or replace. An interface with one implementation costs an afternoon; extracting one from a hard dependency after twelve months of accumulated behaviour does not.

## Interfaces

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Query | `get_structure(symbol, timeframe, as_of) -> StructureSnapshot` | Yes | 30ms | service |
| Query | `get_structure_mtf(symbol, timeframes, as_of) -> {tf: StructureSnapshot}` | Yes | 100ms | service |
| Query | `get_confluence(symbol, timeframe, as_of) -> ConfluenceScore` | Yes | 20ms | service |
| Query | `is_invalidated(position_id, as_of) -> InvalidationVerdict` | Yes | 30ms | service (OMS) |
| Command | `recompute(symbol, timeframes, range, run_id)` | No | 5m | Scheduler, operator |
| Adapter | `StructureDetector` protocol | — | — | — |

`is_invalidated` is new and has no counterpart in the source page. It exists because the OMS needs structure-invalidation exits ("the thesis that justified this position is no longer true"), and that question cannot be answered by a consumer reading raw structure output: it requires knowing which structural features the entry was predicated on. The verdict carries the specific invalidated feature and the bar that invalidated it, so the exit is explainable rather than a threshold firing.

`ConfluenceScore` carries the component breakdown, not just the composite. The five-way confluence rule in page 06 is the platform's primary committee trigger, and a trigger whose reasons are not recorded cannot be evaluated afterwards.

## Degraded Mode

| Condition | Engine behaviour | **Consumer behaviour, previously unstated** |
|---|---|---|
| Finest timeframe unavailable for mitigation | Compute mitigation on the coarsest available, set `mitigation_assessed_on` and `mitigation_degraded=true` | SMC Desk **discounts unmitigated-OB and unmitigated-FVG evidence specifically**. Those are the claims the blind spot falsifies. Other structure evidence stands |
| One timeframe of a multi-timeframe request missing | Return the rest, name the missing timeframes | SMC Desk **cannot apply the top-down bias rule and abstains**. It does not approximate the rule with fewer timeframes |
| Grid parameters unresolvable for a symbol | Compute confluence **without** the grid component, set `grid_missing=true` | Confluence threshold is not met by the remaining four factors alone unless it would have been met without the grid. Never impute a grid level |
| Staleness beyond `max_staleness` | Serve with `confidence=0` | SMC Desk abstains |
| Detector throws on one timeframe | Serve other timeframes, record the failure | As per row 2 |
| Engine process down | Nothing served | SMC Desk abstains. **Committee cycles triggered by confluence stop firing entirely**, which is the quiet consequence worth stating: the platform does not halt, it simply stops proposing trades, and that can go unnoticed for hours without an alert on trigger rate |

The last row is the failure mode the source page cannot express, because page 06 describes what the engine does and not what its silence means. A structure engine that is down produces no errors anywhere: it produces an absence of triggers, which looks identical to a quiet market. The mitigation is an SLO on trigger rate, not on availability.

## SLO

| Dimension | Target |
|---|---|
| Availability, market hours | 99.9% |
| `get_structure` | p50 < 8ms, p95 < 20ms, p99 < 30ms |
| Recompute per symbol per timeframe | p99 < 500ms; five-timeframe top-down < 2s total |
| Freshness | Zero active `(symbol, timeframe)` pairs stale beyond 2 bar intervals |
| Correctness | Confluence score reproducibility 100%. Zero structure objects without `mitigation_assessed_on` |
| **Liveness** | **Confluence trigger rate per symbol stays within its 30-day band. A rate of zero for more than 4 market hours is P1** |

The liveness SLO is the one that catches the silent failure. Every other number here measures the engine when it answers. That one measures whether it is answering at all.

## Security Boundary

| | |
|---|---|
| **Zone** | CORE. No inbound internet, no broker credentials, no vendor keys |
| **Callers permitted** | Evidence Graph (C15), OMS (C23, invalidation only), Feature Materialiser (C06), Operator |
| **Secrets held** | Postgres credential only |
| **Trusts** | Feature Store bars with their quality flags. Instrument Master specs including grid parameters |
| **Privileged actions** | Publishing detector parameters (swing length bounds, confluence thresholds) is operator-only and audited. **Confluence thresholds gate committee cycles, so lowering one silently increases how often the platform considers trading** |
| **Third-party code** | `smartmoneyconcepts` runs behind the `StructureDetector` interface, pinned by version, with no network access |

The threshold note deserves emphasis because the change is so easy to make and so hard to see. Nothing about lowering a confluence threshold looks like a risk change. It does not touch a limit, a size, or a stop. It just makes the platform trade more often, which is the same thing.

---

## Related

- Source page, unmodified: `../06_Market_Structure_Engine.md`
- `04_Regime_Engine.contract.md` — the plugin pattern this engine shares
- `../review/R05_Interface_Contracts.md` §3 — the Instrument Master that now owns grid parameters
- `../review/R05_Interface_Contracts.md` §5 — the OMS consumer of `is_invalidated`
- `../decisions/0015-reference-data-is-a-bounded-context.md` — why grid parameters moved
- `../decisions/0016-oms-owns-order-and-position-lifecycle.md` — structure-invalidation exits
