# 01 — Data Ingestion, contract completion

**Delta against:** `../01_Data_Ingestion.md` (unmodified)
**Adds:** Owns, Invariants, Interfaces, Degraded Mode, SLO, Security Boundary
**Container:** C01 · **Context:** Market Data · **Criticality:** Tier 1 · **Group:** Edge
**Highest-value field for this page (R05 §11):** **Owns.** Which service writes the raw tables is currently ambiguous between ingestion and quality

---

## Owns (exclusive write access)

| Asset | Note |
|---|---|
| `raw_bars` (Iceberg, partitioned by symbol/date) | Append-only. The only writer |
| `raw_ticks` (Iceberg, partitioned by symbol/date) | Append-only. The only writer |
| `raw_documents` (news, calendar payloads, object storage) | Content-addressed by hash |
| `source_health` (Postgres) | Circuit breaker state per source |
| `ingestion_watermarks` (Postgres) | Per-source, per-symbol high-water mark |

**Nobody else writes these.** Page 02's Quality Engine reads raw tables and writes only its own score and quarantine tables. The ambiguity in the source pages (page 01 says it lands data, page 02 says it sits "directly in that pipeline's Validation stage") is resolved here in favour of two services with disjoint write sets.

The corrections rule in page 01's Responsibilities ("never mutate raw data after it's written") is upgraded from a responsibility to invariant 1, because a responsibility is a description and an invariant is a test (ADR-0036).

## Invariants

1. Raw data is immutable once written. A correction is a new row with a new `version` and a new `ingested_at`, never an update. Enforced at the Postgres role level and by Iceberg append-only tables, not by discipline.
2. Every raw row carries `(source, symbol, timeframe, event_time, ingested_at, source_seq)`. `event_time` is business time from the source; `ingested_at` is wall clock. Neither is ever derived from the other.
3. Deduplication is idempotent on `(source, symbol, timeframe, event_time)`. Replaying a source's feed after an outage produces zero new rows.
4. A bar is never emitted before its close time has passed according to the Instrument Master's calendar for that symbol. Emitting an in-progress bar as closed is a look-ahead leak at the earliest possible point in the platform.
5. No text from an external source is ever published on a subject that CORE subscribes to. Documents land in `raw_documents` and are read only by C02.
6. Resampling is deterministic: the same input ticks and the same calendar produce byte-identical bars. Asserted in CI.

Invariant 4 is the one with no equivalent anywhere in pages 00-16, and it depends on C04 existing. Until the Instrument Master is built, bar-close timing is inferred from the timeframe alone, which is wrong across DST transitions and early closes, both of which page 01 names as failure modes without owning the calendar that would detect them.

## Interfaces

| Kind | Signature | Sync | Timeout | Auth |
|---|---|---|---|---|
| Command | `pull(source, symbol, range) -> IngestResult` | Yes | 30s | service (Scheduler), operator |
| Query | `watermark(source, symbol, timeframe) -> Timestamp` | Yes | 10ms | service |
| Query | `source_health() -> [SourceHealth]` | Yes | 50ms | service, operator |
| Command | `replay_source(source, symbol, range, run_id)` | Yes | 30s | operator, audited |
| Adapter | `SourceAdapter` protocol, one implementation per source | — | — | — |

`SourceAdapter` is the plugin seam page 01's Future Expansion asks for ("only the source adapter changes"). Making it a declared protocol rather than a convention is what stops the fifth source being wired in by copy-paste:

```python
class SourceAdapter(Protocol):
    def fetch(self, symbol: str, range: TimeRange, clock: Clock) -> RawBatch: ...
    def normalise(self, batch: RawBatch) -> list[RawBar | RawTick | RawDocument]: ...
    def health(self) -> SourceHealth: ...
```

Every adapter takes the injected `Clock` (ADR-0035). An adapter that reads wall clock directly breaks replay determinism silently, and it is a CI lint failure.

## Degraded Mode

Page 01 has a good circuit breaker and stops short of saying what consumers do while it is open. The behaviour while still broken, which is the state during every real incident:

| Condition | Behaviour |
|---|---|
| One source OPEN, a fallback exists (Databento ↔ Polygon, OHLCV only) | Continue on the fallback. Every bar produced this way is tagged `source_substituted=true`. Downstream must be able to see it happened |
| One source OPEN, no fallback (MT5 tick, news, calendar) | Publish `evt.market_data.source.degraded.v1`, record a **gap marker** in the raw table rather than a silent absence. A gap that is not recorded is indistinguishable from a quiet market |
| MT5 feed lost | The affected account's live execution inputs stop. Other accounts and paper trading continue. Platform Supervisor moves that account to `DEGRADED`, which blocks new entries and leaves exits available |
| Economic calendar stale beyond 6h | **Fail closed.** The News Guard blocks all new entries rather than allowing them. An absent calendar is dangerous, not benign, and page 01 currently treats calendar staleness as best-effort |
| All price sources OPEN | Platform Supervisor moves to `HALTED`. No new entries. Existing broker-side stops remain the protection |

The calendar row is a behaviour change against the source page, which lists news and calendar as "not latency-sensitive, best-effort within the poll interval". That is true of latency and false of staleness: trading into an NFP release because the calendar was six hours stale is exactly the failure the News Guard exists to prevent.

## SLO

| Dimension | Target |
|---|---|
| Availability, market hours | 99.9% per source, measured as "the circuit breaker is CLOSED" |
| MT5 tick to raw storage | p50 < 15ms, p95 < 35ms, p99 < 50ms |
| Bar to queryable | p99 < 2s for real-time symbols |
| Freshness | Watermark lag per active symbol p99 < 1 bar interval |
| Correctness | Zero duplicate `(source, symbol, timeframe, event_time)` rows. Zero unrecorded gaps |
| Calendar coverage | ≥ 30 days forward at all times |

On breach of the p99 tick budget: emit P1, do not drop data. Ingestion never sheds load on the price path; backpressure surfaces as watermark lag, which is observable, rather than as silent loss, which is not.

## Security Boundary

| | |
|---|---|
| **Zone** | DMZ. The only zone with inbound internet |
| **Callers permitted** | Scheduler (C35), Operator via Ops CLI. No CORE service calls it directly |
| **Secrets held** | API keys for Databento, Polygon, the news provider, and the calendar feed. **No broker credentials.** MT5 read access is via the bridge process, which holds its own credential and is a separate trust zone |
| **Trusts** | Transport from paid providers (TLS, contractual). **Trusts no payload text from any source** |
| **Egress** | Outbound to the five named providers only. Denied by default elsewhere |
| **Inbound** | None from the internet. The MT5 push connection is terminal-initiated from the Bridge group |

The distinction that carries the weight: the transport is trusted, the payload text is not. A news provider's TLS certificate proves the bytes came from the provider. It proves nothing about who wrote the article. That is why `raw_documents` is read only by C02, and why invariant 5 exists.

---

## Related

- Source page, unmodified: `../01_Data_Ingestion.md`
- `02_Data_Quality_Engine.contract.md` — the consumer of these raw tables
- `../generated/15_Event_Catalog_v2.md` §4.2 — v2 subjects published here
- `../review/R05_Interface_Contracts.md` §2 — the corrected template
- `../decisions/0036-raw-data-is-immutable-corrections-are-versions.md` — invariant 1
- `../decisions/0035-clock-injection.md` — the adapter clock rule
- `../decisions/0032-untrusted-text-becomes-typed-features-at-an-acl.md` — invariant 5
