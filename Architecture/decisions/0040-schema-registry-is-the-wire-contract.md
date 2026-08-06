# ADR-0040: The schema registry is the wire contract; Pydantic models are generated from it

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** messaging, contracts, tooling

---

## Context

The event envelope (ADR-0037) carries a `dataschema` field pointing at a schema version. **That field is meaningless without a registry**, and page 15 has none: it describes payloads in prose.

Page 15 also names two failure modes it cannot detect: an **orphan event** (a producer with no consumer) and a **silent gap** (a consumer subscribed to a subject nobody produces). Both are listed as risks with no mechanism, and both are mechanically detectable given a registry.

There is a further question of direction. If Python classes are the source of truth and schemas are generated from them, a Python-side refactor silently changes the wire contract. A developer renaming a field for clarity has made a breaking change to every consumer, and nothing says so.

## Options considered

**A. Prose payload descriptions (status quo).**
*Pros:* readable; already written.
*Cons:* not machine-checkable; drifts from the code immediately; the `dataschema` field has nothing to point at; orphans and gaps are undetectable.

**B. Pydantic models as the source of truth, schemas generated from them.**
*Pros:* one definition; natural in a Python codebase; no generation step in the developer loop.
*Cons:* **a Python refactor is a wire-contract change with no signal.** Renaming a field, tightening a type, or changing a default are all ordinary Python edits and all break consumers. The wire contract becomes an accident of the implementation language.

**C. JSON Schema as the source of truth, Pydantic models generated from it.**
*Pros:* the wire contract is an explicit artefact that must be edited deliberately; compatibility can be checked mechanically between versions; the schemas are language-independent, which matters if any component is ever not Python; human-readable, which matters because they are part of the audit record.
*Cons:* a generation step; two artefacts to keep in sync (mitigated because one is generated); JSON Schema is more verbose than a Pydantic class.

**D. Avro or Protobuf.**
*Pros:* compact wire format; strong schema evolution tooling; a mature registry ecosystem.
*Cons:* the platform is Python-first; payloads are low volume outside the tick stream (which is not on the bus, ADR-0037); **human readability of the audit record matters more than roughly 30% wire savings**; adds a build-time toolchain.

## Decision

**Option C.**

1. **Format: JSON Schema 2020-12.** Chosen over Avro/Protobuf because the platform is Python-first, payloads are low volume, and the audit record's readability outweighs wire efficiency.
2. **Storage: the schemas live in the repo under `contracts/schemas/` and are the source of truth.** They are published to a small registry service (or a versioned MinIO bucket) at build time. **Git is the registry; the service is the runtime cache.**
3. **Generation: Pydantic models are generated *from* the schemas**, never the reverse. This prevents a Python-side refactor from silently changing the wire contract.
4. **Every subject in the envelope's `dataschema` resolves** to a published schema version.

### Compatibility policy

| Change | Allowed within a major version | Requires |
|---|---|---|
| Add an optional field with a default | Yes | Minor bump |
| Add a required field | No | Major bump, new subject `.v2` |
| Remove a field | No | Deprecate for 2 releases, then major bump |
| Widen an enum | No (consumers may switch exhaustively) | Major bump, or add `_other` from day one |
| Narrow a type or tighten a constraint | No | Major bump |
| Rename a field | No | Major bump. **Never rename in place** |
| Change the semantics of an existing field | No, **and this is the dangerous one** | Major bump. If the type is unchanged this is **undetectable by tooling** and must be caught in review |

### Multi-version transition

Producers dual-publish `.v1` and `.v2` for one full release cycle. Consumers migrate. `.v1` is retired only when the registry reports **zero consumers bound to it**, tracked via durable consumer names. This is why durable consumers must be named after the service, never auto-generated (R01 §9).

### CI enforcement

A required build check fails on:

1. A publish call whose subject is not in the registry.
2. **A subject with a producer and no consumer** (orphan event, page 15's own listed failure mode, now caught mechanically).
3. **A subscribe call to a subject with no producer** (silent gap, the other half of the same failure mode).
4. A schema change violating the compatibility table.
5. A subject name violating the naming convention (ADR-0037).
6. A message type published without a declared `idempotency_key` derivation rule.
7. A command subject with more than one registered durable consumer (ADR-0037).

**This mechanises page 15's own "Future Expansion" item and closes finding D10. Pages 15 and 16 become generated artefacts** rather than hand-maintained documents that the ADD itself predicts will rot.

## Rationale

Rule 3 is the substance of this decision. The wire contract is the hardest thing in a distributed system to change, because changing it requires coordinating every producer and consumer. If it is a side effect of Python class definitions, it gets changed casually, by people making changes they correctly believe are internal. Inverting the direction means a wire-contract change requires editing a file whose only purpose is the wire contract, which is exactly the right amount of friction.

The CI checks in rules 2 and 3 deserve emphasis because they catch a class of bug that is otherwise found in production. An orphan event is work being done for nobody. A silent gap is a consumer waiting for a message that will never arrive, and it presents as a component that mysteriously does nothing. Both are trivially detectable once producers and consumers are declared, and undetectable otherwise.

The last row of the compatibility table is called out because it is the one tooling cannot help with. Changing what a field *means* while keeping its type is invisible to every automated check and breaks every consumer. Only review catches it, and only if reviewers know to look.

JSON Schema over Protobuf is a deliberate trade of wire efficiency for readability. The decision records in the audit store (ADR-0039) contain these payloads, and they may need to be read by a human years later, possibly by someone without the codebase. A readable payload is worth more than 30% of a small number of bytes.

## Consequences

**Positive**
- The `dataschema` field means something.
- Wire-contract changes are deliberate and reviewable.
- Orphan events and silent gaps are caught at build time.
- Pages 15 and 16 become generated, so they cannot rot.
- The audit record is human-readable indefinitely.

**Negative**
- A generation step in the build, and generated code in the repo (committed, so that a checkout is buildable without the generator).
- JSON Schema is verbose compared to a Pydantic class.
- A registry service to run, though it is a cache over git and its unavailability is not a trading-path failure.
- Dual-publishing during a major transition is real work per breaking change, which is the correct incentive to avoid breaking changes.

**Neutral**
- Payload size is not a constraint at this volume.

## Tripwire

1. **If tick data ever goes on the bus**, reconsider Protobuf for that stream specifically (ADR-0004's tripwire 4 is the related condition).
2. **If the CI checks are ever disabled to unblock a release**, the registry has become documentation rather than a contract.
3. **If dual-publish transitions become frequent** (more than ~2 per year), the schemas were under-designed initially and more thought is needed up front, not a looser policy.

## Related

- ADR-0037 (commands vs events) defines the subjects this registers
- ADR-0004 (NATS JetStream) is the transport
- ADR-0001 (Python, strict typing) consumes the generated models
- ADR-0039 (audit store) is why readability matters
- `../review/R01_Event_Architecture.md` §7
- Document defect D10
- Source: `../15_Event_Catalog.md`
