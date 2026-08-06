# ADR-0026: Six isolated desks with separate API calls, not one multi-persona prompt

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** ai, deliberation, security

---

## Context

Page 08 specifies six committee desks, each invoked as a **separate API call** with its own prompt and its own context, rather than one prompt asking a model to adopt six personas in sequence.

That is the correct decision, and it is the one most likely to be reversed on cost grounds. The argument for reversal writes itself: six calls cost six times as much as one, six calls take longer than one, and a single well-structured prompt can produce six labelled sections that look identical in the output.

The output looks identical. The reasoning is not, and neither is the failure behaviour.

## Options considered

**A. One prompt, six personas.** A single call asks the model to respond as each desk in turn.
*Pros:* one sixth the cost; one round trip; the personas can reference each other, which superficially resembles debate.
*Cons:* the personas are not independent. Within a single generation, each subsequent section is conditioned on the preceding ones, so opinions **correlate by construction.** The model anchors on its first stated position and rationalises. Six "independent" opinions that are actually one opinion restated six times is worse than one opinion, because the agreement is read as confirmation. A single malformed response loses all six. And a successful prompt injection reaches every desk at once.

**B. Six separate calls, isolated context.**
*Pros:* genuine independence, so agreement is evidence; per-desk failure isolation, so one timeout costs one abstention; per-desk prompt versioning, evaluation and calibration; bounded blast radius for any single compromised input.
*Cons:* six times the token cost; six times the rate-limit pressure; higher latency unless parallelised.

**C. Multiple models, one desk each.**
*Pros:* even stronger independence; decorrelates model-specific biases.
*Cons:* multiplies calibration and evaluation work by the number of models; different models have different schema-compliance rates (ADR-0013); operationally heavier without a demonstrated benefit at this stage.

## Decision

**Option B**, with Option C left open as a future refinement.

1. **Six desks, six separate API calls**, issued **in parallel**, each with its own prompt, its own context, and its own timeout (8s).
2. **No desk sees another desk's output.** Not in its context, not in a shared scratchpad, not through a conversational history. Isolation is by construction, not by instruction.
3. **Every desk receives the same sealed evidence graph** (ADR-0002) plus its own role prompt. The only difference between desks is the prompt and the desk-specific weighting of evidence.
4. **A desk failure is isolated.** A timeout, a schema violation or a gateway error costs exactly one abstention and counts against quorum (ADR-0021). It never invalidates the cycle.
5. **Each desk's prompt is independently versioned, evaluated and calibrated** (ADR-0030, ADR-0028). A prompt change to one desk is a change to one desk.
6. **All six calls go through the LLM Gateway** (ADR-0031), which enforces the budget, the timeout, and the redaction policy.
7. **Cost is managed by admission control, not by merging desks.** The Cost Governor triages before an expensive cycle is convened (R17 §6). If a cycle is not worth six calls, it should not be convened at all.

## Rationale

**Independence is the entire point of a committee.** The reason six opinions are more informative than one is that their errors are less than perfectly correlated. Within a single generation, correlation is structurally near-total: the model conditions each persona on what it has already written, anchors on its first position, and produces a consensus that reflects one line of reasoning wearing six labels. That does not merely fail to add information, it actively misleads, because unanimity is read as strength of evidence.

Rule 7 is the answer to the cost objection, and it is the right answer because it addresses the real question. The problem "six calls are expensive" has two possible solutions: make each cycle cheaper, or run fewer cycles. Merging desks takes the first and destroys the property that justifies the design. Admission control takes the second and preserves it. A triage tier that convenes the full committee only for setups that pass a cheap deterministic filter reduces cost by reducing cycles, which is strictly better.

There is a **security property here that page 08 did not set out to provide** (R15 §5, L5): a successful prompt injection through any single input channel can move at most one desk's opinion. Quorum, pooling, the Red Team desk, the CRO Gate and the deterministic Risk Engine all sit downstream. Under Option A, one injection reaches all six personas in a single context, and the blast radius is the whole committee. This is an argument for the multi-desk design that has nothing to do with decision quality.

Failure isolation is the third argument and is the one that shows up soonest in practice. Under Option A, one malformed generation loses the entire cycle. Under Option B, it costs one abstention, and the cycle proceeds if quorum holds.

## Consequences

**Positive**
- Desk opinions are genuinely independent, so agreement carries information.
- One desk failing costs one abstention.
- Per-desk prompt versioning, evaluation and calibration are possible at all.
- Injection blast radius is bounded to one desk.
- Adding a seventh desk is a new box with zero changes to consensus, which is the extensibility property page 08 correctly claims.

**Negative**
- Six times the token cost per cycle. Managed by admission control, not by merging.
- Six times the rate-limit pressure. The gateway must handle this, and a rate-limit error is an abstention.
- Latency is the slowest of six parallel calls plus overhead, rather than one call. Budgeted in R17.
- Six prompts to maintain, evaluate and version rather than one.

**Neutral**
- All six use the same model today. ADR-0033 and Option C remain available.

## Tripwire

1. **Cost:** if committee cost becomes a binding constraint, the response is admission control (fewer cycles), never merging desks. If admission control is already tight and cost still binds, reduce the **number of desks** with a measured justification, keeping each one isolated. Never merge.
2. **Independence check:** measure pairwise agreement between desks. If two desks agree above ~90% across a few hundred cycles, they are not contributing independent information and one should be redesigned or removed. This is a real and cheap measurement that also validates the premise of this ADR.
3. **Toward Option C:** if calibration shows a systematic model-specific bias affecting all six desks identically, that is the signal to introduce a second model.

## Related

- ADR-0002 (deterministic/AI separation) supplies the sealed evidence graph
- ADR-0021 (quorum) is what makes per-desk failure isolation meaningful
- ADR-0028 (calibration), ADR-0030 (prompt registry) depend on per-desk versioning
- ADR-0031 (LLM Gateway), ADR-0032 (text ACL)
- `../review/R10_Committee_Architecture.md`
- `../review/R15_Security.md` §5 (L5 blast radius)
- Source: `../08_AI_Investment_Committee.md` (this ADR preserves its decision)
