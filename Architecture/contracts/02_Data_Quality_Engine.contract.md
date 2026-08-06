# 02 — Data Quality Engine, contract completion

**Delta against:** `../02_Data_Quality_Engine.md` (unmodified)
**Adds:** Owns, Invariants, Interfaces, Degraded Mode, SLO, Security Boundary
**Container:** C03 · **Context:** Market Data · **Criticality:** Tier 1 · **Group:** Edge
**Highest-value field for this page (R05 §11):** **Invariants.** "A REJECT dataset never reaches the Feature Store" must be a testable invariant, not a routing description

---

## Owns (exclusive write access)

| Asset | Note |
|---|---|
| `quality_scores` (Postgres) | One row per `(dataset_id, scorer_version)` |
| `detector_results` (Postgres) | Per-detector output, kept for the weekly false-positive audit |
| `quarantine` (Postgres) | REJECT datasets held for review, never deleted by policy |
| `quarantine_reviews` (Postgres) | Operator decisions, with actor and reason |
| `detector_thresholds` (Postgres, versioned) | Regime-aware thresholds, effective-dated |

**This engine writes no raw data and no feature data.** It reads page 01's raw tables and writes only its own verdict. That disjoint write set is what makes "the only place trust gets decided" (page 02's own Purpose) enforceable rather than aspirational.

## Invariants

1. **A dataset scored REJECT is never readable by the Feature Store.** Enforced by the materialiser's query predicate and by a Postgres grant, not by routing convention. This is the invariant the source page most needs and states only as a flow description.
2. Every dataset reaching the Feature Store carries a score and a `scorer_version`. An unscored dataset is not "presumed good"; it is not readable at all.
3. Detectors never mutate data. They return `(triggered, severity, detail)` and nothing else. A detector that repairs a bar is a bug, because the repair would be invisible to the audit trail.
4. Quarantined data is never deleted by a retention policy. It leaves quarantine only by an operator decision, recorded with actor and reason.
5. Scoring is deterministic: the same bars, the same thresholds, and the same `scorer_version` produce the same score. Asserted in CI. Without this, a replayed backtest can silently disagree with the live run about which data was usable.
6. The regime input used by the threshold logic is always `as_of` the **previous** bar close, never the current one. Page 02 states this cross-dependency carefully in prose; here it is a testable predicate.
7. FLAG is propagated, never absorbed. A flagged dataset that becomes an unflagged feature is a defect.

Invariant 7 addresses a real gap. Page 02 says downstream consumers "are required to" discount flagged data. Nothing enforced that, and the requirement crossed a service boundary as an expectation. Here the flag is carried in the feature row itself, so a consumer cannot fail to see it without ignoring a field.

## Interfaces

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Command | `score(dataset_ref) -> QualityVerdict` | Yes | 150ms | service (Ingestion) |
| Query | `get_verdict(dataset_id) -> QualityVerdict` | Yes | 20ms | service |
| Query | `quarantined(since, symbol?) -> [QuarantineEntry]` | Yes | 200ms | service, operator |
| Command | `release_from_quarantine(dataset_id, reason, actor)` | Yes | 1s | operator, audited |
| Command | `publish_thresholds(thresholds, effective_from, actor)` | Yes | 1s | operator, audited |
| Adapter | `Detector` protocol, one per detector | — | — | — |

```python
class Detector(Protocol):
    name: str
    version: str
    def run(self, window: BarWindow, ctx: DetectorContext) -> DetectorResult: ...
    # DetectorResult = (triggered: bool, severity: float, detail: str)
```

`DetectorContext` carries the previous-bar regime, the instrument spec, and the calendar. Passing it explicitly rather than letting detectors reach for their own inputs is what keeps invariant 6 true, and it is what makes each detector unit-testable in isolation, which the eighth detector will need.

## Degraded Mode

| Condition | Behaviour |
|---|---|
| One detector throws or times out | Score with the remaining detectors, record `detectors_missing=[...]`, and **cap the score at FLAG**. A dataset never reaches PASS with an incomplete detector set |
| The regime input is stale or unavailable | Fall back to the unconditional (long-run) thresholds and set `thresholds_degraded=true`. Never skip the spread and flash-crash detectors |
| Postgres unavailable | **Fail closed:** no dataset is scored, therefore no dataset becomes readable by the Feature Store. Ingestion continues writing raw data, and the backlog is scored on recovery |
| False-positive storm (quarantine rate > 20% over 15 minutes) | Auto-raise P1, keep quarantining. Do not auto-relax thresholds. The operator releases in bulk after review |
| Scorer version mismatch mid-run | Hard error. A dataset partially scored by two versions is not a dataset |

The false-positive storm row is deliberately conservative and is the opposite of the tempting behaviour. During a genuine flash crash, detectors fire correctly and the platform quarantines a lot of real data. Auto-relaxing thresholds at that moment would admit the worst data of the year at the moment it matters most. Quarantining too much is recoverable in an afternoon; trading on bad data is not.

## SLO

| Dimension | Target |
|---|---|
| Availability, market hours | 99.9% |
| Detector suite, parallel | p50 < 40ms, p95 < 80ms, p99 < 100ms |
| Scorer aggregation | p99 < 10ms |
| Freshness | Zero unscored datasets older than 60s during market hours |
| Correctness | Zero REJECT datasets readable by the Feature Store (this is the number that matters) |
| Quality | False-positive rate on quarantine < 5%, measured at the weekly review |

The correctness line is the SLO for this service. The latency numbers describe the pipeline; the zero describes the contract.

## Security Boundary

| | |
|---|---|
| **Zone** | DMZ. Reads raw data, writes verdicts, never reaches CORE directly |
| **Callers permitted** | Ingestion (C01) for `score`, Feature Materialiser (C06) for `get_verdict`, Operator for quarantine actions |
| **Secrets held** | None beyond the Postgres credential |
| **Trusts** | Raw table contents as *bytes faithfully recorded*, never as *values known to be correct*. That distinction is this service's whole purpose |
| **Privileged actions** | `release_from_quarantine` and `publish_thresholds` are operator-only and audited. Releasing bad data is the highest-consequence action available here, and it is a human decision by design |

Threshold publication is audited for a specific reason: quietly loosening a threshold is functionally identical to releasing bad data, but it applies to every future dataset instead of one. It is the change most likely to be made under incident pressure and least likely to be reviewed afterwards.

---

## Related

- Source page, unmodified: `../02_Data_Quality_Engine.md`
- `01_Data_Ingestion.contract.md` — the producer of the raw tables read here
- `03_Feature_Store.contract.md` — the consumer that invariant 1 constrains
- `../generated/15_Event_Catalog_v2.md` §4.3 — v2 subjects
- `../decisions/0025-fail-closed-is-the-universal-default.md` — the Postgres-unavailable row
- `../decisions/0034-point-in-time-correctness-in-five-layers.md` — invariant 6
