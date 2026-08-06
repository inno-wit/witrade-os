# ADR-0020: Fractional Kelly is a platform default, not a per-trade tunable

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** risk, sizing

---

## Context

Page 10 specifies fractional Kelly sizing and, importantly, makes it a **standing platform default that the Committee cannot override.** The conviction score from deliberation feeds the edge estimate; it does not set the size directly.

That is the correct decision and it is recorded because it will be under pressure. The pressure has a predictable shape: a high-conviction setup appears, the committee is unanimous, every desk is at 90 confidence, and the sizing chain produces a position that feels small relative to the certainty. The obvious fix is to let conviction scale the size more aggressively, or to add a manual override for exceptional setups.

Both are the same mistake, and it is the mistake that ends accounts.

## Options considered

**A. Committee sets size directly.** Conviction maps to a position size.
*Pros:* responsive to the strength of the signal; intuitive.
*Cons:* an LLM's self-reported confidence is not a calibrated probability (ADR-0028), and mapping it to capital means an uncalibrated number is sizing positions. It also puts a probabilistic component in direct control of exposure, which contradicts ADR-0002.

**B. Full Kelly.** Size at the mathematically growth-optimal fraction.
*Pros:* maximises long-run log growth if the edge estimate is exact.
*Cons:* the edge estimate is never exact. Full Kelly is extremely sensitive to overestimation, and the loss function is asymmetric: overestimating edge by 2x at full Kelly produces a large probability of ruin, while underestimating costs only growth rate. With an edge estimated from a limited sample on a single instrument, the estimate is noisy, and full Kelly on a noisy estimate is a blow-up mechanism.

**C. Fractional Kelly as a fixed platform parameter, overlaid on volatility targeting, capping only.**
*Pros:* dramatically reduces sensitivity to edge misestimation; the growth cost is modest while the ruin-risk reduction is large; discretion is removed from sizing, which is where discretion does the most damage.
*Cons:* leaves growth on the table when the edge estimate happens to be accurate; feels too conservative during a good run, which is exactly when the pressure to change it arrives.

## Decision

**Option C.**

1. **`kelly_fraction` is a platform-level versioned parameter** (default 0.25, quarter Kelly), held in the `LimitSet` (ADR-0024). It is **not** a per-trade input, not a strategy parameter, and not settable by the Committee.
2. **Volatility targeting comes first. Kelly is an overlay that can only reduce.** The sizing chain is monotonically reducing at every step (R11 §3, phase 2):

```
size_0 = volatility_target_size(risk_budget, atr_or_forecast_vol, instrument_spec)
size_1 = min(size_0, fractional_kelly_size(edge_estimate, kelly_fraction))
size_2 = min(size_1, exposure_headroom)
size_3 = min(size_2, correlation_adjusted_headroom)
size_4 = min(size_3, drawdown_scalar * size_3)
size_5 = min(size_4, liquidity_cap)
size_6 = min(size_5, hard_max_position)
size_7 = round_to_lot_step(size_6, instrument_spec)
if size_7 < instrument_spec.min_lot: REJECT
```

3. **Monotonic reduction is an invariant.** No step may increase size. This makes the chain trivially safe to extend: a new constraint can only ever make the position smaller, so adding one can never introduce an over-sizing bug.
4. **Conviction feeds the edge estimate, bounded.** The Committee's conviction enters `fractional_kelly_size` through a **calibrated** probability (ADR-0028), and its influence is bounded: conviction can reduce size below the volatility target, and cannot raise it above.
5. **Changing `kelly_fraction` is a `LimitSet` change**, which means versioned, dry-run, dual-controlled, with a cooling period on any loosening (ADR-0024).
6. **There is no per-trade override.** Not for the operator, not for the Committee, not for a flag. An exceptional setup gets the same sizing chain as every other setup.

## Rationale

The mathematics of Kelly are asymmetric in a way that decides this. Betting **above** the optimal fraction reduces long-run growth *and* increases ruin probability. Betting **below** it reduces growth only. Since the edge estimate is uncertain, and since the cost of overestimating is categorically worse than the cost of underestimating, the rational response to estimation uncertainty is to bet a fraction of the estimate. Quarter Kelly retains roughly 75% of the growth rate of full Kelly at a small fraction of the drawdown, which is a good trade for any operator who intends to still be trading in ten years.

Rule 6 is the load-bearing one and is a **behavioural** control rather than a mathematical one. The trades that feel most certain are not reliably the trades that work best, and a size override used on the highest-conviction ideas concentrates capital precisely where overconfidence is greatest. Removing discretion from sizing removes the single most reliable way for a good strategy to produce a bad outcome.

Rule 3 deserves emphasis as an engineering property. A sizing chain where every step can only reduce is one where adding a constraint is always safe. A chain where any step can increase requires reasoning about the interaction of every pair of steps, and that reasoning will eventually be wrong.

Rule 4 constrains the Committee's influence to the direction where being wrong is cheap. Conviction lowering a size costs opportunity; conviction raising it costs capital.

## Consequences

**Positive**
- Sizing is deterministic, reproducible and auditable. The same inputs always produce the same size.
- Ruin risk from edge misestimation is dramatically reduced.
- The sizing chain is safely extensible.
- The single most damaging discretionary lever is unavailable.

**Negative**
- Growth is left on the table when the edge estimate is accurate. Accepted deliberately.
- Sizing will feel too small during good runs, which is exactly when the pressure to change it arrives. Rule 5 is what makes changing it slow enough to think about.
- The edge estimate must come from somewhere real. A fabricated or poorly calibrated edge input makes the Kelly overlay theatre. This is why ADR-0028 (calibration) is a dependency rather than an enhancement.

**Neutral**
- `kelly_fraction` remains tunable at the platform level, through governance.

## Tripwire

Revisit `kelly_fraction` (the value, not the design) if **both**:

1. At least 200 trades have been recorded with calibrated edge estimates, and
2. Realised calibration shows the edge estimate is systematically **conservative** (the Brier decomposition shows under-confidence, not just accuracy).

Both conditions, not either. A good run is not evidence of a conservative estimate. Below 200 trades the estimate of the estimate is too noisy to act on, which is the same reasoning that produced fractional Kelly in the first place.

**No tripwire exists for rule 6.** The per-trade override does not come back.

## Related

- ADR-0028 (calibration) supplies the edge estimate this depends on
- ADR-0024 (limit governance) governs changing the fraction
- ADR-0015 (instrument specs) supplies lot step and minimum lot
- ADR-0002 (deterministic/AI separation) is why the Committee does not size
- `../review/R11_Risk_Architecture.md` §3 phase 2
- Source: `../10_Risk_Portfolio_Platform.md` (this ADR preserves its decision)
