# ADR-0021: Deadlock and quorum failure resolve to no-trade

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** ai, safety, deliberation

---

## Context

Page 08 specifies that a deadlocked committee resolves to no-trade, and explicitly justifies the asymmetry: the cost of a missed trade is an opportunity cost, the cost of a bad trade is a realised loss. That reasoning is correct and is recorded here so it survives.

Page 08 also handles abstention by excluding the abstaining desk from the vote. **That handling has a gap the ADD does not name: there is no quorum.**

Consider a partial LLM outage in which four of six desks time out and abstain. Two desks return, both long, both confident. Under page 08's rule the four abstentions are excluded and the remaining two are unanimous. The system produces a confident-looking unanimous decision derived from a third of its intended evidence, with nothing in the output indicating that this happened.

This is precisely the failure mode a partial outage produces, and the current design would trade through it.

## Options considered

**A. Deadlock resolves to no-trade; abstentions excluded; no quorum (status quo).**
*Pros:* simple; maximises the number of cycles that produce a decision.
*Cons:* a partial outage silently produces high-confidence decisions from minimal evidence. The failure is invisible in the output.

**B. Any abstention aborts the cycle.**
*Pros:* trivially safe.
*Cons:* far too brittle. A single desk timing out on a slow API call kills an otherwise complete deliberation. In practice this would trade rarely and for arbitrary reasons.

**C. Deadlock resolves to no-trade, plus an explicit quorum with abstention accounting.**
*Pros:* tolerates isolated failures; refuses to decide when too much of the evidence base is missing; the reason is recorded either way.
*Cons:* a quorum threshold to choose, and it is a judgement call.

## Decision

**Option C.**

1. **Deadlock resolves to `NO_ACTION`.** Preserved from page 08, with the asymmetry argument recorded below.
2. **Quorum: at least K desks must return a valid opinion, default K = 4 of 6.** Below quorum the cycle terminates `NO_ACTION` with reason `QUORUM_NOT_MET`. It does not proceed on the surviving desks.
3. **Quorum is counted on *valid* opinions**, not on responses. A schema violation (ADR-0013), a hard timeout, or a gateway error all count as abstentions.
4. **The Red Team desk and the CRO Gate are not optional participants** (ADR-0029). If the Red Team desk is unavailable, quorum is not met regardless of how many other desks returned. A committee with no adversarial input is not the committee that was designed.
5. **Every terminal state is recorded with its reason**, and the terminal states are exhaustive: `PROPOSAL_ISSUED`, `NO_ACTION`, `DEADLOCKED`, `EXPIRED`, `ABORTED`. A cycle is never reopened; a revision is a new cycle with a `supersedes` link.
6. **`NO_ACTION` is a first-class outcome that is published and learned from.** `evt.committee.cycle.deadlocked.v1` and the `NO_ACTION` reason feed the Learning loop. A rising deadlock rate is a signal about the evidence or the desks, not noise to be suppressed.
7. **A cycle whose evidence graph contains a node with `staleness.severity == critical` cannot issue a proposal.** It terminates `NO_ACTION`. Page 08 makes this a soft requirement ("required to be discounted"); it is a hard invariant here.

## Rationale

**The asymmetry argument, recorded in full:** a missed trade costs the expected value of that trade, which is bounded, non-negative in expectation only, and immediately replaceable by the next setup. A bad trade costs realised capital, and capital lost compounds against every future opportunity. When the system cannot form a coherent view, the two errors are not symmetric, and defaulting to inaction is correct.

There is a second argument that page 08 does not make and that matters more over time: **deadlock is information.** A committee that cannot agree is telling you the setup is genuinely ambiguous. Forcing a decision through a tiebreak discards that signal and replaces it with an arbitrary one. Rule 6 preserves it.

The quorum threshold of 4 of 6 is a judgement, and the reasoning is: two abstentions is a plausible transient (one slow API call, one schema retry), while three is a pattern that indicates something is wrong with the LLM path or the evidence. Trading on half the intended evidence is not a degraded decision, it is a different decision made by a different system.

Rule 4 exists because quorum by count alone has a hole: five desks agreeing without the Red Team is exactly the configuration most likely to produce a confident wrong answer, and it satisfies a naive 4-of-6 count.

Rule 7 closes the corresponding evidence-side hole. A quorum of desks reasoning confidently over critically stale evidence is the same failure with a different cause.

## Consequences

**Positive**
- A partial LLM outage produces no trades rather than under-informed trades.
- The reason for every non-decision is recorded and learnable.
- Ambiguity is preserved as a signal rather than resolved arbitrarily.
- The interaction between infrastructure failure and decision quality becomes visible.

**Negative**
- More cycles terminate without a proposal, including some that would have been correct. Accepted: the missed-trade cost is the cheaper error.
- The quorum threshold is a judgement that will need tuning against observed abstention rates.
- A persistently unavailable desk silently reduces trading frequency. This needs a metric (`desk_abstention_rate` per desk) and an alert, or it will be mistaken for a quiet market.

**Neutral**
- The deadlock rate becomes a monitored quantity, which it should be regardless.

## Tripwire

1. **Deadlock rate above 40% sustained** means the consensus mechanism or the evidence base is the problem, not the market. Investigate before loosening the rule, and never loosen it as the first response.
2. **`QUORUM_NOT_MET` above 5% of cycles** means the LLM path is unreliable enough to be an infrastructure problem. Fix the path, do not lower K.
3. **K itself** may be revisited once there are enough cycles to measure whether decisions made at exactly K desks are systematically worse than those made at 6. That is a real empirical question and the data will exist.

## Related

- ADR-0029 (Red Team desk and CRO Gate) supplies the mandatory participants
- ADR-0026 (six isolated desks) is what makes abstention independent per desk
- ADR-0013 (citations) supplies the schema violations counted as abstentions
- ADR-0025 (fail-closed) is the same principle applied platform-wide
- `../review/R03_Domain_Model_DDD.md` §4 (the quorum gap)
- `../review/R10_Committee_Architecture.md`
- Source: `../08_AI_Investment_Committee.md` (this ADR preserves its decision and closes a gap)
