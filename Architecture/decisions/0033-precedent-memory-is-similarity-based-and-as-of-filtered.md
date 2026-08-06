# ADR-0033: Precedent memory is similarity-based and `as_of`-filtered

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** ai, correctness, leakage

---

## Context

Page 08 gives each desk "the last N committee cycles for this symbol" as memory. That design has two independent defects.

**Defect 1: recency is uninformative.** The last N cycles are the N most recent, not the N most relevant. On a quiet afternoon they are N near-identical `NO_ACTION` cycles, which teach the desk nothing except that nothing has been happening. The genuinely instructive precedent (the last time this exact confluence appeared in this regime) is almost never in the recent window, because informative setups are rare by definition.

**Defect 2: it is a replay leak.** In a replay of a historical period, "the last N cycles" resolved against the live store returns cycles that occurred *after* the replayed timestamp. The desk is shown the future. This is the same class of contamination as the prompt-versioning leak (ADR-0030) and is equally silent: the backtest runs, produces plausible numbers, and is optimistically wrong.

Defect 2 is the serious one. Defect 1 makes the feature useless; defect 2 makes it actively harmful.

## Options considered

**A. Recency memory (status quo).**
*Pros:* trivial to implement.
*Cons:* both defects.

**B. No memory at all.** Each cycle is stateless.
*Pros:* no leak; simple; genuinely defensible.
*Cons:* discards a real signal. "The last four times this setup appeared in this regime it failed" is information a human would use and that the platform has recorded.

**C. Similarity-based retrieval over the evidence graph, hard-filtered by `as_of`.**
*Pros:* precedents are relevant rather than merely recent; the leak is closed by the same filter that governs data; the retrieval is itself a measurable component.
*Cons:* a similarity function to define and tune, which is a new place to overfit; retrieval cost per cycle.

## Decision

**Option C.**

1. **Precedents are retrieved by similarity over the sealed evidence graph**, not by recency. Similarity is computed over the structural signature of the graph (which node kinds are present, their bucketed values, the regime, the session), not over free text.
2. **A hard `as_of` filter applies.** `retrieve(signature, as_of, k)` returns only cycles with `as_of` strictly earlier than the current cycle's `as_of`. **This is enforced in the repository, not by the caller** (ADR-0034, L2).
3. **Precedents carry their outcome**, so a precedent is `{signature_distance, stance_taken, outcome, as_of}`. A precedent whose trade has not yet resolved is included with `outcome: unresolved` and must not be presented as evidence of anything.
4. **Precedents are `PrecedentNode` values in the desk input** (R10 §3), not free text in the prompt. They are citable like any other evidence node (ADR-0013).
5. **k is small (default 5) and versioned** as a domain parameter (ADR-0030). More precedents is not better; it dilutes.
6. **The similarity function is versioned and point-in-time resolvable.** Changing it changes every historical retrieval, so a backtest must use the function that was live at the time.
7. **Retrieval is measured.** Track whether cycles that received precedents produce better-calibrated opinions than cycles that did not. If they do not, the feature is cost with no benefit.

## Rationale

Rule 2 is the correctness fix and is non-negotiable. Without it, every Committee backtest is contaminated through a channel that page 03's careful feature-level treatment does not touch, and the contamination is invisible. It is the same failure as ADR-0030's, arriving through a different door, which is why ADR-0034 treats point-in-time as a five-layer property of *everything* that affects a decision rather than a property of data.

Rule 1 is the usefulness fix. The value of a precedent is entirely in its relevance. Structural similarity over the evidence graph is available essentially for free, because the graph is already sealed and content-addressed, and it directly answers the question a human would ask: "have I seen this shape before, and what happened?"

Rule 3 matters more than it looks. Presenting an unresolved precedent without marking it as unresolved lets a desk infer an outcome that does not exist yet. Marking it explicitly means the desk can note the precedent's existence without concluding from it.

Rule 4 keeps precedents inside the citation discipline. A precedent that arrives as prose in the prompt is a number the desk can misquote; a `PrecedentNode` is a reference it can cite (ADR-0013).

Rule 7 exists because this feature is genuinely optional. It is plausible that precedents add nothing measurable, and the honest response to that would be Option B. Measuring it is what makes that decision available rather than a matter of taste.

## Consequences

**Positive**
- The replay leak is closed by the same mechanism as the data path.
- Precedents become relevant rather than merely recent, which is the difference between a useful signal and noise.
- Precedents are citable, so a desk's use of one is traceable.
- The feature's value becomes measurable, so it can be removed if it does not earn its cost.

**Negative**
- A similarity function to define, tune and version. It is a new place to overfit, and it is governed by the same PBO gate as any other learned component.
- Retrieval cost per cycle: a vector or structural lookup against the decision store. Small, but on the critical path and therefore budgeted.
- Early on there are no precedents at all, so the feature contributes nothing for the first months. That is correct behaviour and should not be papered over with weak matches: below a similarity threshold, return nothing rather than the closest available.

**Neutral**
- Storage is already required for the decision record.

## Tripwire

1. **If cycles with precedents are not better calibrated than cycles without**, after 200+ resolved decisions, remove the feature (Option B). It is cost and complexity with no measured benefit.
2. **If the similarity threshold is repeatedly lowered** to return more matches, the feature is being forced to produce output it does not have. Returning nothing is the correct behaviour.
3. **If any retrieval path is found that does not go through the `as_of`-filtered repository**, treat it as a P1 leakage defect and re-run the affected validations.

## Related

- ADR-0034 (point-in-time in five layers) is the general principle
- ADR-0030 (prompt registry) is the sibling leak through the prompt path
- ADR-0013 (citations) governs how precedents are referenced
- `../review/R09_Evidence_Graph.md` supplies the structural signature used for similarity
- `../review/R10_Committee_Architecture.md` §3 (W5)
- `../review/R08_Data_Lineage.md` §5 (the LLM memory leak)
- Source: `../08_AI_Investment_Committee.md`
