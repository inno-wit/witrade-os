# ADR-0028: Desk confidence is calibrated before use; raw confidence is never a weight

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** ai, statistics, calibration

---

## Context

Page 08 collects a self-reported confidence score from each desk and uses it directly as a vote weight.

**A language model's self-reported confidence is not a probability.** It is an artefact of the token distribution that correlates loosely with correctness and is systematically overconfident, with the degree of overconfidence varying by model, by prompt, by domain, and by how the question is phrased. Using it directly as a weight means the vote is weighted by a quantity with unknown units and an unknown, drifting bias.

The consequence is not merely imprecision. Overconfidence is directionally biased: it inflates conviction, which under any sizing scheme increases position size, which means the error costs capital rather than opportunity.

## Options considered

**A. Use raw confidence directly (status quo).**
*Pros:* nothing to build.
*Cons:* the weight has no units; systematic overconfidence flows straight into sizing; a model upgrade silently changes the whole platform's risk profile because the new model's confidence distribution differs.

**B. Discard confidence entirely, use stance only.**
*Pros:* no calibration needed; immune to the bias.
*Cons:* throws away real information. A desk that is genuinely more certain on some setups than others is telling you something, even if the scale is wrong.

**C. Calibrate per desk against realised outcomes, with heavy shrinkage until enough data exists.**
*Pros:* converts an uncalibrated self-report into an empirical probability; per-desk, so it captures desk-specific bias; produces the diagnostic metrics that reveal whether each desk contributes anything.
*Cons:* requires resolved outcomes to fit against, so it is useless on day one; adds a fitted component that must itself be validated and refitted.

## Decision

**Option C.**

1. **Rename the field.** `conviction_raw`, not `confidence`. The name signals in the type that the number has not been calibrated and must not be used directly. `DeskOpinion.conviction_raw: int` (0-100), explicitly marked as unusable as a weight.
2. **Every desk opinion is recorded with its `conviction_raw` and, once the trade resolves, its outcome.** This dataset is generated automatically and is the input to everything below.
3. **Per desk, fit an isotonic regression** from `conviction_raw` to empirical hit rate. **Isotonic rather than Platt scaling**, because it makes no parametric assumption and monotonicity is the only property that must hold.
4. `conviction_calibrated = isotonic_desk(conviction_raw)`. Only the calibrated value enters pooling (ADR-0027).
5. **Refit weekly, PBO-gated** like any other learned parameter. The Learning loop's no-shortcut rule applies to its own calibration fits.
6. **Until a desk has at least 100 resolved opinions**, use a shrunk prior:

```
conviction_calibrated = 0.5 + 0.3 * (conviction_raw / 100 - 0.5)
```

Heavy shrinkage toward chance, because an uncalibrated desk should barely move the pooled result.

7. **A model version change resets the calibration**, because the confidence distribution is a property of the model, not of the desk. The prompt registry pins the model per prompt version (ADR-0030), so this is detectable rather than silent.

### Metrics produced

| Metric | Meaning | Alert |
|---|---|---|
| **Brier score** per desk | Overall calibration quality | Rising trend over 4 weeks |
| **Reliability diagram** per desk | Where the desk is over- or under-confident | Reviewed weekly, visual |
| **Expected calibration error (ECE)** | Single-number summary | ECE > 0.15 flags the desk for prompt review; > 0.25 floors its weight (ADR-0029 escalation) |
| **Resolution** | Does the desk discriminate at all? | Near-zero means the desk adds nothing |

## Rationale

**Resolution is the metric that matters most and is the one nobody measures.** A desk that outputs "bullish, 70" on every single cycle has *perfect calibration* if it happens to be right 70% of the time, and contributes exactly zero information. Calibration alone cannot detect this; only resolution can. It is the honest test of whether six desks are better than three, and it is the metric that would justify removing a desk.

Rule 1 sounds cosmetic and is not. The single most likely implementation error is passing `confidence` into a weight because the name says it is a confidence. Naming it `conviction_raw` makes the misuse read wrongly at the call site, which is the cheapest form of enforcement available.

Rule 6 is what makes this safe before the data exists. Without it, calibration is a component that does nothing for the first several months and then starts doing something, which is a silent behaviour change. With heavy shrinkage, an uncalibrated committee is deliberately damped: it can express a direction but barely moves the pooled probability, which is the correct epistemic position for a system with no track record.

Rule 7 catches a subtle failure. Upgrading the model changes the confidence distribution while every other component stays the same, so a calibration fitted on the old model systematically misreads the new one. Because the prompt registry pins the model version, this is a detectable event rather than a silent drift.

Isotonic over Platt because there is no reason to assume the raw-to-empirical mapping is sigmoid. Monotonicity is the only assumption that is clearly justified, and isotonic assumes exactly that and nothing more.

## Consequences

**Positive**
- Pooled conviction becomes a real probability, which is the precondition for Kelly sizing (ADR-0020) meaning anything.
- Per-desk bias is measured and corrected rather than assumed away.
- Resolution reveals whether each desk earns its cost, which nothing else can.
- A model upgrade's effect on decision quality becomes measurable rather than invisible.

**Negative**
- Useless until roughly 100 resolved opinions per desk, which at ~10 cycles/day/symbol is a matter of weeks. Handled by the shrunk prior, which is deliberately conservative.
- A fitted component that must itself be validated, refitted and gated. Calibration is learned, so it can overfit, which is why rule 5 applies the PBO gate.
- Outcome labelling requires a defined notion of "was this opinion right," which is non-trivial for a desk that said "long, 60" on a trade that was closed at breakeven by a time exit. The labelling rule must be defined explicitly and versioned like any other domain parameter.

**Neutral**
- No change to the desk prompts. Calibration is entirely downstream.

## Tripwire

1. **If a desk's resolution stays near zero after 300+ resolved opinions**, remove the desk. It is cost with no information.
2. **If ECE stays above 0.15 after calibration**, the desk's raw output is not monotonically related to correctness, and isotonic regression cannot fix that. The prompt needs work, not the calibrator.
3. **If calibration curves differ sharply between desks**, that is expected and fine. If they are all identical, the desks are not independent (ADR-0026's tripwire 2 applies).

## Related

- ADR-0027 (log-odds pooling) consumes the calibrated value. **Hard dependency**
- ADR-0020 (fractional Kelly) consumes the pooled probability
- ADR-0026 (isolated desks) is what makes per-desk calibration meaningful
- ADR-0030 (prompt registry) pins the model version this depends on
- ADR-0029 (Red Team) produces the most valuable calibration dataset
- `../review/R10_Committee_Architecture.md` §5
- Source: `../08_AI_Investment_Committee.md` (W3)
