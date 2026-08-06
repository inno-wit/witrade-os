# ADR-0029: A Red Team desk and a deterministic CRO Gate outrank the pooled committee

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** ai, risk, deliberation

---

## Context

Page 08's committee has six desks, each reasoning from its own evidence slice toward a stance. **Nobody argues against acting.**

This is a structural bias, not a prompt problem. Each desk is asked "what does your evidence imply," and evidence that implies nothing produces a `flat` stance rather than an objection. The aggregation then combines six views that were each formed by looking for a reason to act. The result systematically underweights the case for doing nothing, and doing nothing is the correct answer most of the time.

Page 08 lists an adversarial second pass under Future Expansion, to be evaluated "once desk-level calibration is stable." **That ordering is backwards.** The Red Team is what *produces* the most valuable calibration data, because it is the only component whose accuracy is directly measurable: when it objected strongly and was overruled, did the objection turn out to matter?

Separately, there is no component that can veto a trade on policy grounds. The Risk Engine asks "does the portfolio permit this," which is a different question from "is this the kind of trade we do." A sufficiently persuasive committee can currently talk itself into a trade that violates no portfolio limit and that the operator would never take.

## Options considered

**A. Prompt the six desks to consider counter-arguments.**
*Pros:* free; no new component.
*Cons:* a desk asked to argue both sides does neither well, and its stance still has to be one value. The counter-argument becomes decoration in the rationale rather than a force on the outcome.

**B. Red Team desk only.**
*Pros:* supplies genuine adversarial pressure and the calibration dataset.
*Cons:* it is still an LLM. A persuasive committee can out-argue it, and there is still no hard floor on what the platform will do.

**C. Red Team desk (LLM) plus a CRO Gate (deterministic).**
*Pros:* adversarial reasoning where reasoning helps, and hard policy conditions where reasoning is a liability; the two catch different classes of bad trade.
*Cons:* two new components; the CRO Gate deliberately duplicates one Risk Engine rule.

## Decision

**Option C.**

### Red Team Desk (LLM, sees everything)

| Property | Value |
|---|---|
| Input | The **full** evidence graph, the majority stance, and every desk's rationale |
| Task | Construct the strongest available case that this trade is wrong. **Not a devil's advocate exercise:** it must cite specific evidence |
| Output | `{objection_strength: 0-100, objections: [Citation], scenario: str, historical_precedent: [PrecedentNode]}` |
| Effect | Objection strength above threshold forces `DEADLOCKED`. Below threshold it reduces pooled conviction proportionally (the `red_team_penalty` in ADR-0027) |
| Scoring | Tracked separately: when the Red Team objected strongly and was overruled, what happened? |

**The Red Team is deliberately exempt from the isolation rule** that governs the six desks (ADR-0026). Isolation exists to make each desk's reasoning traceable to one deterministic source. The Red Team's job is precisely to find cross-source contradiction, which requires seeing across sources. Different job, different constraint.

**The Red Team is a mandatory quorum participant** (ADR-0021 rule 4). If it is unavailable, quorum is not met regardless of how many other desks returned.

### CRO Gate (deterministic, no LLM)

Hard conditions that veto regardless of committee conviction:

| Condition | Rationale |
|---|---|
| Any critical-severity stale evidence node | Do not act on a picture you know is broken |
| Conviction below floor after Red Team adjustment | A marginal trade is not worth the transaction cost or the tail risk |
| Regime confidence below floor | If you do not know what market you are in, do not take a directional view |
| High-impact event within the blackout window | **Deliberately duplicates the Risk Engine's news guard** |
| Correlation with the existing book above threshold | Adding a seventh correlated position is one position, not seven |
| Cumulative same-direction exposure at cap | |
| Post-drawdown cooling period active | The best-looking signals often appear during drawdowns, which is exactly when judgement is worst |

### Precedence

**Risk Engine > CRO Gate > Red Team > pooled committee > individual desk.**

Deterministic layers always outrank reasoned ones. This extends page 09's governing rule to conflict resolution.

### Escalation

| Condition | Action |
|---|---|
| Red Team objection ≥ 80 **and** pooled conviction ≥ 80 | Notify, do not block. Record as `HIGH_CONFLICT` and track outcomes separately |
| Proposal conviction ≥ 95 | **Always notify.** Near-certainty is more often a bug than an insight |

## Rationale

The Red Team's value is not that it will often be right. It is that it produces **the single most valuable calibration dataset the platform generates**: a labelled record of strong objections that were overruled, with outcomes. Nothing else in the architecture generates a comparable signal, because every other component's output is confounded with the decision that followed it.

Reversing page 08's ordering follows directly. Waiting for calibration to be stable before adding the Red Team means waiting for stability while withholding the component that most accelerates it.

The CRO Gate exists because **some conditions should not be arguable.** A persuasive committee is a risk, not an asset, when the platform's own policy says no. Deterministic conditions cannot be talked around, cannot be gradually eroded by a drifting prompt, and are testable without an LLM.

The deliberate duplication of the news blackout is correct redundancy rather than an oversight. Trading into a high-impact release is among the most reliably catastrophic mistakes available, and two independent implementations of the most commonly-catastrophic rule is a reasonable use of duplication. If the two disagree, that disagreement is itself an alert.

The post-drawdown cooling condition is the behavioural one. Signal quality genuinely does look best during drawdowns, partly because volatility is elevated and partly because the operator wants it to. Making the pause a deterministic gate rather than a discipline is what makes it hold.

## Consequences

**Positive**
- Structural bias toward action is countered by a component whose job is the opposite.
- A directly measurable calibration signal, available from day one.
- Hard policy conditions that a persuasive committee cannot argue around.
- `would_change_mind_if` from each desk plus the Red Team's scenario gives the OMS concrete invalidation conditions for the resulting position (ADR-0016).

**Negative**
- One more LLM call per cycle (~8k tokens, larger context than a desk). Included in the cost model.
- The Red Team's own calibration must be tracked, or a persistently over-objecting Red Team suppresses good trades. Its objection threshold is a versioned domain parameter (ADR-0030).
- The CRO Gate's floors are more parameters to tune, each with overfitting risk. They go in the `LimitSet` (ADR-0024) and are governed accordingly.

**Neutral**
- The six desks are unchanged.

## Tripwire

1. **If Red Team objections above threshold, when overruled, are right less than chance** over 100+ cases, the Red Team is noise and its penalty term should be removed pending a redesign.
2. **If the CRO Gate vetoes more than ~20% of proposals**, either the floors are too tight or the committee is producing proposals it should not. Diagnose which before adjusting either.
3. **If the CRO Gate and the Risk Engine's news guard ever disagree**, one of them has a bug. This is a P1 alert, and it is the reason the duplication is worth having.

## Related

- ADR-0027 (pooling) consumes `red_team_penalty`
- ADR-0028 (calibration) is accelerated by the Red Team's dataset
- ADR-0021 (quorum) makes the Red Team mandatory
- ADR-0026 (isolated desks) is the rule the Red Team is exempt from, deliberately
- ADR-0011 (Risk Engine sole authority) sits above the CRO Gate
- `../review/R10_Committee_Architecture.md` §4, §9, §11
- Source: `../08_AI_Investment_Committee.md` (W6)
