# RFC-NNNN: <title>

**Status:** Draft
**Author:** <name>
**Date:** <YYYY-MM-DD>
**Numbering:** assigned per `RFC_Numbering.md` at the moment this file is created, not at approval
**Reviewers:** <names, or "unassigned">
**Related ADRs:** <existing ADR numbers this touches, if any>
**Related bounded contexts:** <BC1-BC12, or "cross-cutting">

---

## Problem

What is broken, missing, or newly true that the frozen architecture (`../../Architecture/`, `../../Blueprint/`) does not already answer. One paragraph, stated as a problem, not as a solution in disguise.

## Motivation

Why this problem is worth solving now, specifically. What happens if it is left unresolved through the next implementation phase.

## Background

Relevant history: which ADR, which architecture page, which prior RFC (if any) is adjacent to this one. Link, do not restate — this repository's one-fact-one-canonical-source rule (`../../Architecture/freeze/Canonical_Source_Validation.md`) applies to RFCs too.

## Current Behaviour

What the frozen baseline currently specifies or does (cite the exact page/ADR/service), even if "current behaviour" means "the architecture does not yet address this."

## Proposed Change

The change, precisely enough that a reviewer could evaluate it without asking you to fill in gaps live. Include the affected bounded context(s), interfaces, events, and any new/changed types.

## Alternatives

At least two genuinely considered alternatives, including "do nothing." State why each was not chosen. An RFC with only one option is not a decision, it is an announcement.

## Tradeoffs

What the proposed change gives up in exchange for what it gains. Every real tradeoff, not a token one.

## Risks

What could go wrong if this is accepted and implemented as written. Include the blast radius (which bounded contexts, which safety-critical paths per `../../Architecture/ROADMAP.md`'s "what must not erode" list).

## Impact

- **Affected interfaces:** <list, or "none">
- **Affected events:** <list, or "none">
- **Affected APIs:** <list, or "none">
- **Affected bounded contexts:** <list>
- **Affected tests:** <list of test suites/levels per `../../Blueprint/Testing_Blueprint.md`>
- **Affected runbooks:** <list, or "none">
- **Breaking change?** <yes/no, and to whom>

## Migration

If this changes something already implemented, the concrete migration path. If nothing is implemented yet, state that explicitly rather than leaving this section blank.

## Open Questions

Anything genuinely unresolved that should not block Architecture Review from starting, but must be resolved before ADR generation.

## Approval Status

`Draft` / `In Review` / `Accepted` / `Rejected` / `Withdrawn` — see `RFC_Lifecycle.md`.

## Reviewers

Who reviewed this RFC and their verdict (approve / request changes / reject), dated.

## Decision

The Architecture Review Board's final decision and one-paragraph reasoning. Left blank until Architecture Review closes.

## Implementation Plan

Once Accepted: which gate (`../Roadmap/Implementation_Gates.md`) this lands in, the ADR number that will formalise it, and the rough sequencing relative to other in-flight work.

---

## Related

- `RFC_Guidelines.md` — how to write one of these well
- `RFC_Lifecycle.md` — what happens to this document after submission
- `../Review_Board/Architecture_Review_Process.md` — the review this RFC feeds into
- `../ADR/ADR_Governance.md` — where an Accepted RFC becomes a numbered decision
