# ADR-0030: Prompts are versioned registry artefacts with point-in-time resolution

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** ai, correctness, backtesting, leakage

---

## Context

Page 08 makes desk weights tunable by the Learning loop and prompts implicitly editable. Page 12 proposes revising desk prompts based on trade outcomes. **Nothing versions either with an effective date.**

The consequence is a look-ahead bias vector that page 03's careful feature-level treatment does not cover, because it operates through the **prompt** rather than through the data:

> Replay a decision from three months ago. The desks use **today's** prompts, which were tuned on the outcomes of the very trades being replayed.

Every Committee backtest is therefore contaminated, in the optimistic direction, and the contamination is invisible. The backtest runs. It produces plausible numbers. It is wrong, and it is wrong in the direction that makes a strategy look better than it is, which is the direction that costs money.

The same applies to desk weights, consensus strategy versions, and the LLM memory path: page 08 gives each desk "last N committee cycles for this symbol," and in a replay that memory must contain only cycles that occurred before the replayed timestamp.

This is precisely the class of leak that page 03 treats seriously for features and that nothing treats for anything else.

## Options considered

**A. Prompts in code, versioned by git.**
*Pros:* no new component; prompts are reviewed like code; git history exists.
*Cons:* resolution by git SHA requires knowing which SHA was deployed at a historical timestamp and checking out that tree to run a backtest. Nobody will do this. In practice every backtest runs against `HEAD`, silently.

**B. Prompts in a config file, reloaded at runtime.**
*Pros:* changeable without a deploy.
*Cons:* strictly worse than A. Edited in place, so history is destroyed, and there is not even a git record.

**C. A Prompt & Policy Registry: versioned artefacts with effective dates and point-in-time resolution.**
*Pros:* `resolve(desk, as_of)` returns what was actually live at that time; prompts get the same lifecycle as models (shadow, evaluation, promotion); the contamination is closed mechanically.
*Cons:* a new component; prompt changes become a promotion process rather than an edit, which is slower.

## Decision

**Option C.** A **Prompt & Policy Registry** (container C18) holding every artefact whose version affects a decision.

### Scope: it holds more than prompts

| Artefact | Why it belongs here |
|---|---|
| Desk prompts | Tuned on outcomes; the primary leak |
| Desk weight sets | Tuned by Learning (page 08) |
| Consensus strategy version | Log-odds pooling parameters, dependence discounts |
| Evidence edge-rule tables | Domain knowledge, versioned (R09 §5) |
| OMS management policies | Trailing rules, breakeven multiples (ADR-0016) |
| Domain parameters | Swing length, GARCH window, quality thresholds (R04 §5) |

**The rule: anything whose value affects a decision and that changes over time is a registry artefact, not a config file and not a constant.**

### Record shape

```
{version, hash, effective_from, effective_to, model_pin, eval_scores, promoted_by, supersedes}
```

### Rules

1. **`resolve(artefact, as_of)` is the only accessor.** There is no "get the current prompt" call available to the committee. Even a live cycle resolves against its own `as_of`, so live and replay use the identical code path.
2. **Artefacts are immutable.** A change publishes a new version with a new `effective_from`. Nothing is ever edited in place.
3. **`model_pin` is part of the artefact.** A prompt is validated against a specific model version. A model upgrade with the same prompt is a **new artefact version**, because the behaviour changed even though the text did not.
4. **Changes take the full model lifecycle** (R07 §6): shadow run, evaluation against a held-out set, then promotion. This makes page 08's mandatory-shadow-run rule enforceable rather than procedural.
5. **Every decision record stores the resolved versions it used.** A post-mortem can prove which prompt produced which opinion.
6. **The desk memory path is `as_of`-filtered.** A desk's precedent set in a replay contains only cycles with `as_of < replay_timestamp` (ADR-0033).
7. **The registry is a blocking dependency.** If it is unreachable, no cycle is convened (ADR-0025). Falling back to a default or cached prompt would silently reintroduce the contamination.

## Rationale

The failure this closes has three properties that together make it the worst kind of bug: it is **silent** (nothing errors), **optimistic** (results look better, not worse), and **discovered late** (when a validated strategy fails live). Those are exactly the properties of the look-ahead bias that page 03 correctly treats as the platform's most dangerous failure mode. The only difference is the channel.

Rule 1 is what makes it structural rather than procedural. If a "get current prompt" call exists, it will be used, because it is simpler and because in a live cycle "current" and "as of now" are the same thing. Removing the call means live and replay are the same code path, and the replay case cannot be got wrong separately.

Rule 3 is the subtle one that most implementations miss. A prompt is not an artefact on its own; a prompt evaluated against a different model is a different artefact. Treating a model upgrade as invisible to the prompt registry means a backtest resolves the right text against the wrong behaviour.

Rule 4 has a second benefit beyond correctness: it makes prompt changes **slow enough to be deliberate.** Prompts are the easiest thing in the platform to change and the hardest to evaluate. Without a lifecycle they get tweaked constantly on the basis of a handful of recent outcomes, which is overfitting with extra steps.

## Consequences

**Positive**
- Committee backtests become valid. Without this they are not merely imprecise, they are systematically optimistic.
- The prompt-mediated leakage path is closed by the same mechanism as the data path.
- Prompt changes gain evaluation, shadow validation and a rollback path (a pointer flip).
- A post-mortem can reproduce exactly what a desk was asked.

**Negative**
- Prompt iteration is slower. This is partly the point and partly a real cost during early development, when rapid prompt iteration is genuinely valuable. Mitigation: `dev` and `sim` may resolve against an uncommitted working version, clearly flagged, and **any evaluation result produced that way is not admissible** as validation evidence.
- A new component that is a blocking dependency for the committee.
- Storage of every historical prompt version, which is trivial in size.

**Neutral**
- Postgres `registry` schema (ADR-0007). Small, relational, versioned.

## Tripwire

1. **Any backtest producing results without recorded artefact versions is invalid.** If this happens, the resolution path has been bypassed and it is a P1 defect, not a reporting gap.
2. If prompt versions accumulate faster than roughly one per desk per month, prompts are being tuned reactively rather than tested, and the promotion gate is too weak.
3. If the working-version escape hatch in `dev`/`sim` is ever used to produce a number that reaches a decision about live capital, remove the escape hatch.

## Related

- ADR-0034 (point-in-time correctness) is the general principle; this is its prompt-path instance
- ADR-0035 (clock injection) is the time-path instance
- ADR-0003 (Iceberg snapshots) is the data-path instance
- ADR-0026 (isolated desks) is what makes per-desk versioning meaningful
- ADR-0033 (precedent memory, `as_of`-filtered)
- `../review/R19_Missing_Components.md` §8
- `../review/R08_Data_Lineage.md` §5 (the LLM memory leak)
- `../review/R04_Platform_Services.md` §5
