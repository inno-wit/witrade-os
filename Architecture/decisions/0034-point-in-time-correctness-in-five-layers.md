# ADR-0034: Point-in-time correctness is enforced by five layers, not by caller discipline

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** correctness, data, backtesting, foundational

---

## Context

Page 03 calls look-ahead leakage **"the single most dangerous failure mode in the whole platform"** and is right. It then states that point-in-time correctness is "enforced at the query layer" without describing a mechanism. That is finding D8.

"Enforced at the query layer" describes an intention. The gap between an intention and a mechanism is where this class of bug lives, and it lives there comfortably because the bug has three properties that defeat ordinary quality practices:

1. **It is silent.** A leaky backtest runs successfully and produces numbers.
2. **It is optimistic.** Leakage makes results look better, never worse, so it never triggers the "these numbers look wrong" instinct.
3. **It is discovered late**, when a validated strategy fails live, by which point there is no way to know which historical results were affected.

There is also a subtlety that a naive `as_of` filter misses entirely: **a bar corrected and backfilled three days later legitimately carries an older business timestamp.** Filtering `WHERE event_time <= as_of` will include it, even though it was not visible at `as_of`. Business-time filtering alone does not reproduce what was knowable.

## Options considered

**A. Caller discipline (status quo).** Every query author is responsible for filtering correctly.
*Pros:* nothing to build.
*Cons:* one forgotten filter, in one query, in one notebook, silently contaminates a result that then justifies a strategy. There is no signal.

**B. One strong mechanism (repository-level filtering).**
*Pros:* a single choke point; simple to explain.
*Cons:* any single layer will eventually be bypassed. A researcher writing an ad-hoc query, a training pipeline reading a Parquet file directly, or a component calling `datetime.now()` all route around it.

**C. Five independent layers, defence in depth.**
*Pros:* each layer catches a different bypass, including the ones nobody anticipated; the adversarial layer catches unknown leakage paths.
*Cons:* more machinery; five things to maintain.

## Decision

**Option C.** Five layers, because any single layer will eventually be bypassed.

| Layer | Mechanism | Catches |
|---|---|---|
| **L1 Type system** | `AsOf` is a distinct type in the shared kernel. Any function reading data takes it explicitly. **There is no `get_features(symbol)` overload without it** | Accidental omission at the call site |
| **L2 Query layer** | The repository filters `WHERE event_time <= as_of` **and pins `snapshot_id`** (ADR-0003). Callers cannot construct a raw query; the repository is the only path | The corrected-bar-backfilled-later case that `as_of` alone misses |
| **L3 Feature registry** | `point_in_time_safe: bool` per feature. Training pipelines **reject** any feature set containing an unsafe feature unless it is explicitly declared a label | Forward-looking features used as inputs |
| **L4 Clock injection** | No `datetime.now()` anywhere (ADR-0035). In `sim`, the clock cannot advance past the simulation's current bar | Code reading wall time inside a backtest |
| **L5 Adversarial test** | A CI test that runs a known-leaky feature through the pipeline and asserts it is caught. Plus a **shuffle test**: randomise labels, retrain, assert performance collapses to chance | Everything the first four missed, including leakage nobody wrote a rule for |

### Additional binding rules

1. **L2 requires both filters.** `event_time <= as_of` **and** a pinned Iceberg snapshot. Either alone is insufficient: the timestamp filter misses late corrections, and the snapshot alone misses future-dated rows within the same snapshot.
2. **The prompt and parameter path is covered too** (ADR-0030). Point-in-time correctness applies to prompts, desk weights, consensus versions and domain parameters, not only to data. This is the leak page 03's treatment does not reach.
3. **The desk memory path is covered too** (ADR-0033). A desk's precedent set in a replay contains only cycles with `as_of` earlier than the replay timestamp.
4. **The determinism test** (ADR-0035, rule 6) is the companion check: two runs of the same simulation with the same seed produce byte-identical output.

## Rationale

**L5 is the one most often skipped and the most valuable**, and it is worth being explicit about why. L1 through L4 each catch a *known* leakage channel. They cannot catch a channel nobody thought of, and the history of this class of bug is a history of channels nobody thought of.

The shuffle test catches all of them at once, by construction. Randomise the labels and retrain: if the model still performs above chance, it is reading the future through some channel, and it does not matter which one. It is the only test that detects unknown leakage paths, and it costs one CI job.

L2's two-part requirement is the specific answer to D8 and is why ADR-0003 is a hard dependency. Snapshot pinning converts "what was visible at time T" from a property the caller must reason about into a property of the storage substrate. `SELECT ... FOR SYSTEM_VERSION AS OF <snapshot>` is a mechanism; "enforced at the query layer" is an aspiration.

L1 deserves note as the cheapest layer with the highest catch rate for the most common error. Making `AsOf` a required parameter with no default means the most frequent mistake (forgetting to pass it) does not compile. It costs one type and some verbosity.

Rule 2 is the extension the ADD does not make at all. Page 03 treats feature-level leakage carefully and leaves the prompt path completely open, which means the Committee's backtests are contaminated even when the data path is perfect. Point-in-time is a property of everything that affects a decision, not just of the numbers.

## Consequences

**Positive**
- Backtest results become trustworthy, which is the precondition for every other validation claim the platform makes (PBO, DSR, walk-forward all assume clean inputs).
- Leakage is caught at the commit that introduces it rather than months later.
- The shuffle test catches unanticipated channels.
- `AsOf` in the type system documents the requirement at every call site.

**Negative**
- Five layers to build and maintain. L5 in particular needs a maintained leaky-feature corpus.
- Verbosity: every data-reading function signature carries `as_of`.
- The repository-only rule constrains ad-hoc research queries, which is genuine friction for exploration. Mitigation: research notebooks may query Iceberg directly **provided** they pin a snapshot, and any result feeding a promotion decision must be reproducible through the repository path.
- The shuffle test is slow (a full retrain). It runs nightly rather than per-commit.

**Neutral**
- All five layers are cheap individually. The cost is remembering that all five are required.

## Tripwire

1. **If the shuffle test ever shows above-chance performance**, stop. Do not investigate the model, investigate the pipeline. There is a leak, and it is in a channel that L1 through L4 do not cover.
2. **If any layer is bypassed to unblock work**, that bypass is a P1 defect with a deadline, not a workaround. Record it in the debt register.
3. **If a strategy that passed validation fails live in a way consistent with over-optimism**, re-run the leakage suite before concluding the market changed. This is the specific diagnosis that is otherwise never made.

## Related

- ADR-0003 (Iceberg) supplies L2's snapshot pinning. **Hard dependency**
- ADR-0035 (clock injection) is L4
- ADR-0030 (prompt registry) extends this to the prompt path
- ADR-0033 (precedent memory) extends it to desk memory
- ADR-0014 (shared kernel) holds the `AsOf` type
- ADR-0036 (immutable raw data) is what makes late corrections traceable
- `../review/R08_Data_Lineage.md` §5
- Document defect D8
- Source: `../03_Feature_Store.md`
