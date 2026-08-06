# ADR-0027: Log-odds pooling with dependence discounting replaces the weighted vote

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** ai, deliberation, statistics

---

## Context

Page 08 aggregates desk opinions with a **weighted vote** using tunable per-desk weights. It also acknowledges that desk opinions are correlated, and monitors that correlation via the Learning loop. It does not correct for it.

Three problems follow:

1. **A weighted vote is not a probability operation.** Summing weighted stances produces a number with no units and no interpretation. It cannot be compared to a base rate, cannot be calibrated, and cannot be combined with anything else meaningfully.
2. **Correlated evidence is double-counted.** If the Regime Desk and the Volatility Desk both read nodes derived from the same fitted GARCH model, their agreement is partly an artefact of a shared input, not independent confirmation. A vote counts it twice at full weight.
3. **The prior is implicitly 0.5.** A vote starting from a tie assumes the market is a coin flip conditional on nothing, which is both false and discards known structure (base rates differ by regime and by session).

The correlation problem is the serious one. It biases the result in the direction of overconfidence, and it does so most strongly when several desks agree, which is exactly when the platform is most likely to act.

## Options considered

**A. Weighted vote (status quo).**
*Pros:* simple, intuitive, already specified.
*Cons:* the three problems above. Its output is not a probability, so nothing downstream can use it quantitatively.

**B. Simple log-odds pooling (naive Bayes).**
*Pros:* produces a real probability; combines evidence multiplicatively, which is correct for independent sources; comparable to a base rate.
*Cons:* assumes independence, which is known to be false here. Naive Bayes with correlated inputs is systematically overconfident, which makes the problem worse than the vote in the agreement case.

**C. Log-odds pooling with an explicit dependence discount and a measured prior.**
*Pros:* correct primitive, correlation handled explicitly, prior grounded in measured base rates, output is a usable probability.
*Cons:* the independence estimate must come from somewhere and is itself an approximation; more moving parts to explain and test.

## Decision

**Option C.**

```
pooled_logodds(LONG) =
    prior_logodds(LONG | regime, session)
  + SUM over desks d:
        w_d * independence_d * logodds(conviction_calibrated_d | stance_d)
  - red_team_penalty
```

| Term | Source |
|---|---|
| `prior_logodds` | **Measured base rate** of profitable long setups in this regime and session. **Not 0.5** |
| `conviction_calibrated_d` | From the calibration layer (ADR-0028). **Never `conviction_raw`** |
| `w_d` | Learned desk weight, PBO-gated. Page 08's existing mechanism, retained |
| `independence_d` | Derived from the evidence graph's `SHARES_MODEL_WITH` structure (R09 §4). Two desks citing nodes that share a fitted model are each discounted |
| `red_team_penalty` | Proportional to Red Team objection strength (ADR-0029) |

### Dispersion, made explicit

Deadlock is currently "disagreement beyond a configurable threshold." The measure is the **weighted standard deviation of per-desk log-odds contributions**, and four shapes are distinguished rather than two:

| Dispersion | \|mean\| | Meaning | Outcome |
|---|---|---|---|
| High | High | Confident desks in genuine conflict | `DEADLOCKED` |
| Low | Low | Everyone agrees there is nothing here | `NO_ACTION`. Healthy, should be the most common outcome |
| Low | High | Genuine consensus | Proceed |
| High | Low | Desks disagree and cancel out | `NO_ACTION`, **tracked separately** |

Page 08 conflates rows 2 and 4 as "no trade." They are diagnostically very different: row 2 is the system working, row 4 is the desks behaving as noise. A rising row-4 rate is the signal that the committee is not adding information.

### The baseline comparison

A **deterministic graph baseline** (log-odds propagation over the evidence graph with no LLM, R09 §5) is computed on every cycle. Two metrics are tracked permanently:

- **Agreement rate** between the baseline and the pooled committee.
- **Conditional accuracy** when they agree versus when they disagree.

**If the committee never beats the baseline on the disagreement cases, the LLM layer is expensive decoration** and should be reduced to a Red Team plus the CRO Gate. This is the test that makes the committee's existence falsifiable.

## Rationale

Log-odds is the correct primitive because combining independent evidence is multiplicative in probability space, which is additive in log-odds space. That is not an aesthetic preference; it is what makes the output a probability that can be compared to a base rate, fed to a Kelly calculation (ADR-0020), and scored with a Brier score.

The dependence discount is the substantive fix. Page 08 identifies the correlation and monitors it, which surfaces the problem without correcting it. Deriving `independence_d` from the evidence graph's shared-model structure makes the correction **arithmetic rather than procedural**: two desks reading the same underlying model are automatically discounted, with no human deciding when it matters.

The measured prior matters more than it appears. Long setups in a trending regime during the London session have a different base rate from long setups in a ranging regime overnight, and that difference is knowable from history. Starting every cycle at 0.5 throws it away and forces the desks to recover it, which they will do inconsistently.

**The baseline comparison is the most important part of this ADR and is easy to skip.** Without it, there is no way to know whether six LLM calls per cycle are buying anything over a deterministic graph computation. With it, the question is answered continuously and the answer determines whether the committee is worth its cost. No version of the current architecture can run this test.

## Consequences

**Positive**
- The pooled output is a probability with a meaning, usable by Kelly sizing and scoreable by Brier.
- Correlated agreement no longer inflates confidence.
- Known base-rate structure is used rather than discarded.
- Four diagnostic outcomes instead of two.
- The committee's value becomes empirically falsifiable.

**Negative**
- More complex than a vote, and harder to explain to oneself at 2am. Mitigated because every term is individually loggable and the decision record stores all of them.
- `independence_d` is an approximation derived from graph structure, not a measured correlation. It is directionally right and imprecise. Better than 1.0 for every desk, which is what the vote assumes.
- Requires the calibration layer (ADR-0028) to exist first. Until it does, the shrunk prior applies and pooling is heavily damped, which is correct behaviour for an uncalibrated committee.

**Neutral**
- Desk weights are retained unchanged, with their PBO gate.

## Tripwire

1. **If the committee does not beat the baseline on disagreement cases over 200+ resolved decisions**, reduce the LLM layer to Red Team plus CRO Gate. This is a real, budgeted decision, not a rhetorical one.
2. **If the row-4 rate (high dispersion, low mean) rises above ~25%**, the desks are producing noise and the prompts or the evidence slices need work.
3. **If `independence_d` is near 1.0 for every desk** across a large sample, the shared-model structure is not being captured and the discount is doing nothing.

## Related

- ADR-0028 (calibration) is a hard dependency: pooling raw conviction is meaningless
- ADR-0029 (Red Team) supplies the penalty term
- ADR-0026 (isolated desks) is what makes partial independence achievable at all
- ADR-0021 (quorum, dispersion-driven deadlock)
- `../review/R10_Committee_Architecture.md` §6
- `../review/R09_Evidence_Graph.md` §4, §5
- Source: `../08_AI_Investment_Committee.md` (W4)
