# 03 — Feature Store, contract completion

**Delta against:** `../03_Feature_Store.md` (unmodified)
**Adds:** Owns, Invariants, Interfaces, Degraded Mode, SLO, Security Boundary
**Containers:** C06 Feature Materialiser (offline write) + C07 Feature Serving (online read) · **Context:** Feature Store · **Criticality:** Tier 1 · **Group:** Data
**Highest-value field for this page (R05 §11):** **Interfaces.** `get_features()` is sketched; the full `FeatureView` contract (L4.4) is the train/serve skew boundary

---

## The split this contract assumes

Page 03 describes one component. It is two, and the separation is what makes the rest of this file expressible:

| | C06 Feature Materialiser | C07 Feature Serving |
|---|---|---|
| Path | Offline, batch and event-triggered | Online, per-request |
| Writes | Iceberg feature tables | Nothing durable, cache only |
| Reads | Raw tables + quality verdicts | Iceberg + Redis cache |
| Latency | Seconds to minutes | Sub-50ms |
| Fails to | Stale features, detectable | Cache miss then Iceberg read |

One writer, many readers. That is also what closes B6: page 03 and page 13 use DuckDB as a shared multi-writer database, which it is not. DuckDB stays as an embedded query engine per consumer, reading Iceberg (ADR-0003).

## Owns (exclusive write access)

| Asset | Owner | Note |
|---|---|---|
| `features_*` Iceberg tables, one per category | **C06 only** | Partitioned by symbol/date, snapshot-versioned |
| `feature_definitions` (Postgres, versioned) | C06 | `technical.rsi.v2` and friends, immutable once published |
| `materialisation_runs` (Postgres) | C06 | Run ledger with input snapshot IDs |
| `feature_cache` (Redis) | **C07 only** | Rebuildable, never authoritative |

The writeback path in page 03 ("Regime/SMC/Volatility features are populated by pages 04/05/06") is corrected: pages 04-06 **publish events**, and C06 materialises them into feature tables. The engines do not write feature tables directly. Three writers into one table set is how the definition of a feature quietly diverges from the definition of the event that produced it.

## Invariants

1. **Point-in-time correctness:** `get_features(symbol, tf, as_of)` returns only values computable from data with `event_time <= as_of`, using the feature definition version in force at `as_of`. Enforced at the query layer, never by caller discipline.
2. Every feature row carries `(symbol, timeframe, event_time, as_of, feature_version, quality_flag, source_snapshot_id)`. A row missing any of these is not readable.
3. Feature definitions are immutable once published. A change is a new version. Models keep resolving the version they were trained against.
4. The offline and online paths share one `FeatureView` type and one computation implementation. Two implementations of the same feature is train/serve skew by construction, and no test catches it reliably.
5. Labels are never served on any live path. `Labels` category is readable only with an explicit `purpose="training"` argument, and that argument is unavailable to the serving API.
6. A feature computed from FLAG-quality data carries the flag. The flag propagates through every derived feature (invariant 7 of page 02, continued).
7. Every materialisation run records the Iceberg snapshot ID of every input table. A run that cannot name its inputs is not reproducible and is a failed run.

Invariant 1 is what page 03 calls "the single most dangerous failure mode in the whole platform", and it is correct to call it that. The source page asserts the property and describes the discipline. Invariants 1, 2 and 7 together make it a storage property instead: the `as_of` predicate is in the query layer, the snapshot IDs are pinned, and a violation is a query that fails rather than a number that is quietly wrong.

Invariant 5 exists because forward returns and triple-barrier outcomes are, definitionally, the future. Page 03 notes they are "never served live". A note is not a mechanism; a missing argument is.

## Interfaces

### C07 Feature Serving (online)

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Query | `get_features(symbol, timeframe, as_of, categories) -> FeatureView` | Yes | 50ms | service |
| Query | `get_feature_view_spec(version) -> FeatureViewSpec` | Yes | 10ms | service |
| Query | `freshness(symbol, timeframe) -> {category: Timestamp}` | Yes | 10ms | service, operator |

### C06 Feature Materialiser (offline)

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Command | `materialise(symbol, timeframe, range, categories)` | No | 30m | service (Scheduler) |
| Command | `backfill(definition_version, range, run_id)` | No | 24h | operator, audited |
| Query | `get_features_at(symbol, tf, as_of, categories, purpose)` | Yes | 5s | researcher, training |
| Command | `publish_definition(definition, effective_from, actor)` | Yes | 1s | operator, audited |

### The type both paths share (L4.4)

```python
@dataclass(frozen=True)
class FeatureView:
    symbol: str
    timeframe: str
    as_of: Timestamp
    values: Mapping[str, Decimal | None]     # None means absent, never 0.0
    versions: Mapping[str, str]              # feature name -> definition version
    quality: Mapping[str, QualityFlag]       # PASS | FLAG, per contributing dataset
    staleness: Mapping[str, timedelta]       # per category, age at as_of
    source_snapshot_ids: Mapping[str, str]   # per input table
```

Four details that are the whole point of freezing this type now:

- **`None` is not `0.0`.** A missing RSI and an RSI of zero are different facts, and a model trained on a store that conflates them learns something untrue.
- **`Decimal`, never float.** Price-derived features that go on to size a position cannot carry binary rounding error.
- **`versions` per feature, not per view.** A view mixing v1 and v2 definitions is legal and must be visible.
- **`staleness` is data, not an exception.** Page 03's staleness flag becomes a per-category duration the caller can reason about, rather than a boolean it can ignore.

## Degraded Mode

| Condition | Behaviour |
|---|---|
| One category stale beyond its refresh interval | Serve it with `staleness[cat]` set. **The Risk Engine treats a stale volatility feature as a reason to size at the most conservative level, never at a default** |
| One category entirely absent | Return the view with that category's values as `None`. Never fabricate, never carry forward silently |
| Redis cache unavailable | Serve from Iceberg directly. Latency budget degrades to p99 400ms, emit P1. Correctness is unaffected because the cache is never authoritative |
| Iceberg unavailable | `get_features` fails. Consumers fail closed: no new entries. Exits proceed using broker-side stops, which do not depend on features |
| Materialiser behind by more than one bar interval | Serving reports staleness truthfully. The Committee cycle for that symbol does not convene. **A cycle on stale evidence is worse than no cycle** |
| Definition version missing for an `as_of` | Hard error. Never fall back to the current definition, because that is exactly the look-ahead leak invariant 1 exists to prevent |

The staleness row is the one page 03 leaves open. It says the caller "is required to factor staleness into confidence" and stops. Requirements that cross a service boundary as expectations are not requirements. Stated here: stale volatility means conservative sizing, stale anything means the cycle does not run.

## SLO

| Dimension | Target |
|---|---|
| C07 availability, market hours | 99.95% |
| `get_features` | p50 < 8ms, p95 < 30ms, p99 < 50ms |
| C06 materialisation lag | p99 < 1 bar interval for active symbols |
| Freshness | Zero active `(symbol, timeframe)` pairs stale beyond 2 bar intervals |
| Correctness | **Zero point-in-time violations.** Asserted by a CI test that replays a historical window and fails on any value unavailable at its `as_of` |
| Reproducibility | Two materialisations of the same range from the same snapshot IDs are byte-identical |

The point-in-time CI test is the highest-value single test in the platform. It is the difference between page 03's central claim being true and being believed.

## Security Boundary

| | |
|---|---|
| **Zone** | Data plane, inside CORE. No inbound internet |
| **Callers permitted (C07)** | Quant engines, Model Inference, Evidence Graph, Risk. Read only |
| **Callers permitted (C06)** | Scheduler, Operator. Researchers via `get_features_at` with `purpose="training"` |
| **Secrets held** | Object storage credentials, Postgres credential. No broker credentials, no vendor API keys |
| **Trusts** | Quality verdicts from C03 as authoritative. Raw tables as immutable |
| **Researcher access** | Read-only, `sim`/`dev` only, and cannot call `publish_definition`. A researcher can propose a feature; only an audited operator action publishes one |

The researcher/operator split matters more here than anywhere else in the data plane. Publishing a feature definition changes what every future model is trained on, and doing it without an audit record makes a whole class of model regressions untraceable.

---

## Related

- Source page, unmodified: `../03_Feature_Store.md`
- `02_Data_Quality_Engine.contract.md` — invariant 1 there constrains what is readable here
- `04_Regime_Engine.contract.md`, `05_Volatility_Engine.contract.md`, `06_Market_Structure_Engine.contract.md` — the engines whose events C06 materialises
- `../generated/16_Container_Model_v2.md` §3 — the C06/C07 split
- `../review/R08_Data_Lineage.md` — point-in-time correctness in five layers
- `../decisions/0003-iceberg-analytical-table-format.md` — closes B6
- `../decisions/0034-point-in-time-correctness-in-five-layers.md` — invariants 1, 2, 7
