# ADR-0032: Untrusted external text is converted to typed features at an ACL and never reaches a desk

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** security, ai, prompt-injection

---

## Context

The current architecture has a live, unmitigated path from attacker-influencable text to a component that allocates capital. This is blocking defect B5 and threat T2 in the security model.

Trace it: page 01 ingests article text. Page 03 places it in the Macro category of the Feature Store. Page 08 gives the Macro Desk that category. **Nothing sanitises it at any point.**

The threat is concrete rather than theoretical:

- Paid press-release syndication is cheap and widely available. An attacker can place text into a legitimate wire service for a small fee.
- The text is then ingested by anyone consuming that wire, including this platform.
- A crafted payload in that text reaches an LLM whose output influences position direction and size.
- The manipulation is **plausibly deniable and hard to detect after the fact**, because the desk's rationale will look like ordinary reasoning about a news item.

The likelihood is assessed as medium and rising. The impact is a manipulated position.

## Options considered

**A. Prompt-level defence.** Instruct the desk to ignore instructions embedded in the news text.
*Pros:* trivial to implement.
*Cons:* prompt-level defences against prompt injection have no proof of correctness and are repeatedly defeated. Relying on a model to reliably distinguish data from instruction, inside its own context window, is relying on the exact property that injection exploits.

**B. Input filtering.** Scan article text for instruction-like patterns and reject or strip.
*Pros:* catches naive attempts.
*Cons:* an arms race with no terminating condition. Encoding, homoglyphs, indirection and natural-language phrasing all defeat pattern matching. It also produces false positives on legitimate articles containing quoted instructions.

**C. Architectural: raw text never reaches a desk.** An anti-corruption layer converts prose into typed, bounded features. The desk's context contains numbers and enums only.
*Pros:* the attack surface is removed rather than defended. There is no code path from prose to a desk, so there is nothing to inject into.
*Cons:* information loss (nuance in an article is compressed to a few typed fields); the extraction step is itself an LLM call and must be isolated; a closed entity vocabulary must be maintained.

## Decision

**Option C, with four further layers as defence in depth.**

### ACL-2: the untrusted-text anti-corruption layer

```
Raw article text
  -> Source reputation tier lookup (from BC2 configuration, NOT from the article)
  -> Structural strip: markup, control characters, zero-width characters,
     homoglyphs, anything resembling instruction syntax
  -> Length clamp
  -> Constrained extraction (isolated model call: no tools, no memory,
     no platform context, hard output schema)
  -> Typed output ONLY:
       { sentiment:   float[-1, 1],
         entities:    [enum from a closed vocabulary],
         event_type:  enum,
         confidence:  float,
         source_tier: enum }
  -> Feature Store, Macro category
```

### Binding rules

1. **Raw text is archived for audit but is never read by any component other than this ACL.** Enforced by storage segregation: the raw text bucket is readable by exactly one service identity.
2. **The extraction call runs with no tools, no memory, no platform context, and a hard output schema.** It cannot be induced to do anything because it can do nothing. Its worst case is producing wrong typed values, not executing an instruction.
3. **Any extraction whose output fails schema validation is discarded and the article is quarantined**, not passed through with defaults. Defaults on a security boundary are a bypass.
4. **`source_tier` comes from configuration keyed by provider and publisher, never from the article's own claims about itself.** An article asserting its own authority is exactly the payload shape being defended against.
5. **The Macro Desk's context contains only the typed output.** There is no code path from prose to a desk. This is verified by a test, not by inspection.

### Defence in depth (R15 §5)

| Layer | Control |
|---|---|
| **L1 Architectural** | The ACL above. **This layer alone defeats the threat**; the rest are depth |
| **L2 Extraction isolation** | No tools, no memory, no context, schema-clamped, range-checked |
| **L3 Source tiering** | Tier from configuration; low-tier sources weighted down in the evidence graph regardless of content |
| **L4 Gateway inspection** | The LLM Gateway rejects any evidence payload containing instruction-like patterns and raises P1. Should never fire after L1; **if it fires, L1 has a hole** |
| **L5 Structural blast radius** | A successful injection can move at most **one desk's** opinion. Quorum, pooling, the Red Team, the CRO Gate and the deterministic Risk Engine all sit downstream (ADR-0026, ADR-0021) |

6. **A prompt-injection test suite runs on every build**: a corpus of injection attempts against the ACL, every one of which must be neutralised to typed output.

## Rationale

The decisive property of Option C is that it **removes the attack surface rather than defending it.** Options A and B both accept that attacker-controlled text will reach a model and try to make that safe. There is no known way to make that safe, and the research consensus is that there will not be one soon. Option C declines the premise.

The information-loss objection deserves a direct answer: what a desk can actually use from a news article is roughly "how negative, about what, of what kind, how reliable." A desk cannot act on nuance it cannot cite (ADR-0013 makes citations references to typed evidence nodes), so the typed representation is close to the full usable content already. The loss is smaller than it first appears and is a fair price.

L4 is worth keeping even though L1 should make it unreachable, precisely **because** it should be unreachable: it is a canary. A firing L4 is evidence that L1 has a hole, which is information no other control provides.

L5 is a genuine and unplanned security property of the committee architecture (R15 §5). Page 08 chose six isolated desks for decision-quality reasons; the effect is that any single compromised input channel is bounded to one sixth of the deliberation, downstream of a quorum requirement and a deterministic risk gate. This is an argument for ADR-0026 that has nothing to do with reasoning quality, and it should be preserved deliberately.

Rule 4 is the one most easily got wrong. A tier field derived from anything the article says about itself, including its claimed source, its dateline, or its formatting, is attacker-controlled. It must come from a lookup keyed on the delivery channel.

## Consequences

**Positive**
- The prompt-injection path to capital allocation is closed architecturally.
- The Macro Desk's inputs become typed, bounded, and testable, which also makes them backtestable and replayable in a way prose never was.
- Source reliability becomes an explicit, weightable property of the evidence graph.
- The test suite makes the defence verifiable on every build.

**Negative**
- Real information loss from prose to typed features. Accepted, and partly mitigated by the fact that citations must reference typed nodes anyway.
- The extraction call is an additional LLM cost per article and an additional latency step in ingestion (off the decision path, so it does not affect the cycle budget).
- The closed entity vocabulary and the event-type enum must be maintained. A new event type appearing in the world requires a schema change, and until then it is `other`, which must be handled rather than dropped.

**Neutral**
- Raw text is still archived, so nothing is lost for audit or for future reprocessing.

## Tripwire

1. **If L4 ever fires**, L1 has a hole. Treat as a P1 security incident and audit the ACL path, not the gateway.
2. **If the entity vocabulary requires more than roughly one addition per quarter**, the closed-vocabulary approach may be too rigid for the news source in use, and the extraction schema needs redesign, not relaxation.
3. **If the prompt-injection test suite is ever skipped or allowed to fail**, this ADR is not in force.

## Related

- ADR-0026 (isolated desks) supplies the L5 blast-radius bound
- ADR-0002 (deterministic/AI separation) is the general principle
- ADR-0013 (citations as references) means desks cannot cite prose anyway
- ADR-0031 (LLM Gateway) hosts L4
- ADR-0021 (quorum) is downstream containment
- `../review/R15_Security.md` §5 (threat T2)
- `../review/R03_Domain_Model_DDD.md` §9 (ACL-2)
- Blocking defect B5
