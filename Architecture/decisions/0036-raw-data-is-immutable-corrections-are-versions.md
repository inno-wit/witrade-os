# ADR-0036: Raw data is immutable; corrections are new versions with downstream backfill

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** data, correctness, lineage

---

## Context

Page 01 states the rule that raw ingested data is never mutated. That is correct and is preserved here.

What the ADD does not specify is **what happens when the data was wrong.** Vendors correct bars. Databento and Polygon both republish corrected data, sometimes days later. A bad tick is filtered, a session boundary is restated, a split or dividend adjustment is revised. This is normal, expected, and frequent.

Without a defined procedure, the two obvious responses are both wrong:

- **Overwrite the bad bar.** This violates page 01's rule, destroys the record of what the platform actually saw when it made a decision, and makes every historical backtest silently non-reproducible.
- **Ignore the correction.** Then every future computation uses data known to be wrong.

There is a third problem the ADD does not raise at all: a correction invalidates **everything computed downstream of it.** A corrected bar changes the ATR, which changes the volatility estimate, which changes the position size the platform would have taken. Nothing currently identifies what needs recomputing.

## Options considered

**A. Overwrite in place.**
*Pros:* simple; one row per bar; queries stay simple.
*Cons:* destroys the audit record; a decision made on the old value becomes inexplicable; every historical backtest silently changes results when a correction lands, with no signal.

**B. Append a corrected row, let queries take the latest.**
*Pros:* history preserved; simple write path.
*Cons:* a naive `event_time <= as_of` filter picks up the correction even though it was not visible at `as_of`. This is precisely the case that defeats business-time filtering alone (ADR-0034, L2).

**C. Immutable versions with explicit supersession, snapshot-pinned reads, and lineage-driven backfill.**
*Pros:* both "what we saw then" and "what is true now" are answerable; the correct one is selected by which snapshot is pinned; the blast radius of a correction is computable.
*Cons:* two timestamps and a snapshot to reason about; a backfill procedure to build.

## Decision

**Option C.**

1. **Raw data is append-only and immutable.** A correction is a **new version** of the record, never an edit. It carries `supersedes: <original_record_id>` and its own ingestion timestamp.
2. **Every record carries two times:** `event_time` (business time, e.g. bar close, which the correction preserves) and `ingested_at` (when the platform received it, which the correction does not).
3. **Point-in-time reads pin an Iceberg snapshot** (ADR-0003, ADR-0034 L2). A read pinned to a snapshot taken before the correction landed sees the original value. **This is the mechanism**: it is not the timestamp filter that excludes the correction, it is the snapshot.
4. **A correction emits `evt.market_data.bar.corrected.v1`** carrying the record identity, both versions, and the magnitude of the change.
5. **Downstream impact is computed from lineage** (R08). The correction event triggers an impact analysis that identifies every derived artefact computed from the affected record: features, regime estimates, volatility forecasts, structure snapshots, model training sets, backtest results.
6. **Backfill is explicit and versioned, never silent.** Recomputed artefacts are new versions with their own `effective_from`. The originals are retained, because a decision made on the original data must remain explicable.
7. **A correction affecting a period containing live decisions is a P1 alert**, not a routine job. It means the platform traded on data now known to be wrong, and that is a finding for the Learning loop, not a maintenance task.
8. **Backtest results computed on superseded data are marked stale**, and the mark is visible wherever the result is displayed. A validation result standing on corrected inputs is not evidence.

## Rationale

The two questions that must both be answerable are:

- **"What did the platform see when it made this decision?"** Required for audit, post-mortem and explainability. Answered by the pinned snapshot.
- **"What is the best current understanding of what happened?"** Required for training and research. Answered by the latest snapshot.

Option A can answer only the second. Option B answers the second and appears to answer the first while getting it subtly wrong, which is worse than not answering it. Only Option C answers both, and it does so with a mechanism (snapshot isolation) rather than a discipline.

Rule 3 is why ADR-0003 is a hard dependency here. Without snapshot isolation, distinguishing "visible at time T" from "true about time T" requires every query to reason about `ingested_at` correctly, and one query that does not is a silent contamination.

Rule 5 is the part that does not exist in the ADD in any form. A correction with no impact analysis means the platform knows a bar was wrong and has no idea what conclusions were built on it. Lineage turns "some models may be affected" into a list.

Rule 7 reframes what a correction is. In a data-warehouse context it is maintenance. Here, a corrected bar in a period where the platform took positions means it traded on bad data, and the interesting question is whether the decision would have differed. That is a Learning input, and it is a use of the counterfactual replay capability (ADR-0035) that justifies building it.

Rule 8 prevents the quiet failure where a strategy was validated on data that has since been corrected, and the validation is still cited.

## Consequences

**Positive**
- The audit record survives corrections intact.
- Both questions above are answerable, by mechanism.
- The blast radius of a correction is computable rather than guessed.
- A correction during a live period becomes a learning signal rather than a silent event.
- Vendor data quality becomes measurable: correction frequency and magnitude per source feed the source scoring on page 02.

**Negative**
- More storage. Trivial relative to the value, and superseded versions compact well.
- Two timestamps plus a snapshot to reason about. Mitigated because the repository is the only read path (ADR-0034 L2) and it encapsulates all three.
- A backfill procedure to build and test. It must be exercised at least once before live capital, because a backfill first attempted after a real correction will be wrong.
- Reprocessing cost when a widely-used bar is corrected, which can cascade through several derived layers.

**Neutral**
- Page 01's rule is preserved unchanged. This ADR supplies the procedure it implies.

## Tripwire

1. **If corrections are frequent enough that backfill becomes a routine burden** (say more than weekly), the data source's quality is the problem. Escalate to the vendor or add a source, rather than optimising the backfill.
2. **If a correction is ever applied by overwriting**, the immutability guarantee is void for every record, because there is no longer any basis for trusting that a given row is what was originally received.
3. **If the backfill procedure has not been exercised in six months**, run a drill against a synthetic correction. An untested backfill is a hypothesis.

## Related

- ADR-0003 (Iceberg) supplies snapshot isolation. **Hard dependency**
- ADR-0034 (point-in-time in five layers) is what corrections would otherwise defeat
- ADR-0035 (clock injection) enables the counterfactual replay in rule 7
- ADR-0039 (Journal as an audit service) holds the decision records that must remain explicable
- `../review/R08_Data_Lineage.md` §6 (O1, vendor data correction)
- Source: `../01_Data_Ingestion.md` (this ADR supplies the procedure its rule implies)
