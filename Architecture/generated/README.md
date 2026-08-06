# Generated Artefacts — WITrade Quant Platform

**Type:** Regenerated cross-cutting reference pages
**Supersedes as working contract:** `../15_Event_Catalog.md`, `../16_C4_Container_Diagram.md`
**Source pages:** unmodified
**Date:** 2026-08-03

---

## What this is

Two of the seventeen source pages are **derived views**, not design decisions: page 15 compiles every component page's event lists into one table, and page 16 compiles every component page's container into one list. Both say so themselves, and both predict their own decay in their Status and Failure Modes sections.

Page 15: *"will need a rebuild pass"*, *"hand-maintained catalogs rot"*.
Page 16: *"diagram/reality drift"*, *"consider generating this diagram's container list programmatically"*.

ADR-0040 promotes those predictions into a requirement: pages 15 and 16 become generated artefacts. This directory holds the v2 regeneration, done by hand for now against the review, and machine-generated later against `contracts/schemas/` and the deployment manifests.

The source pages are not modified. They remain the correct record of what was designed on 2026-08-03 and the traceable baseline every delta is stated against.

---

## Files

| File | Supersedes | Headline change |
|---|---|---|
| [15_Event_Catalog_v2.md](15_Event_Catalog_v2.md) | `../15_Event_Catalog.md` | 43 subjects to **80**. Commands separated from events (closes B1). Envelope, streams, ordering keys, idempotency identities, DLQ policy |
| [16_Container_Model_v2.md](16_Container_Model_v2.md) | `../16_C4_Container_Diagram.md` | 15 containers to **39** (2026-08-03), **40** after Phase 11 (2026-08-04, C40 Portfolio Construction Engine — `../18_Portfolio_Construction.md`). Criticality tiers, owning contexts, deployment groups, trust boundaries, relationship diagram |

---

## The two headline numbers

| | Source page | Regenerated | What the gap is |
|---|---|---|---|
| Event subjects | 43 | 80 | 20 of the 38 additions are position lifecycle, reconciliation, reference data, and platform mode: the four families whose absence shows how entry-biased the source design is |
| Containers | 15 | 39 | 24 new or split, plus 4 of the original 15 materially rescoped. Four of the six capital-plane containers did not exist |

Neither number is a criticism of the source pages. They are compilations, and a compilation cannot contain what its sources omit. The gap is in pages 00-14, and it is why these two pages were the first to need regenerating.

---

## Reading order

If you are implementing, read `16_Container_Model_v2.md` §6 first. It is the ten-container minimum viable subset in dependency order, and it is the shortest useful answer to "what do I build first."

If you are wiring services, read `15_Event_Catalog_v2.md` §4.9 first. The split of `risk.approved` into a command plus an observer event is the single correction that prevents duplicate live orders.

---

## When these become machine-generated

| File | Generated from | Blocked on |
|---|---|---|
| `15_Event_Catalog_v2.md` | `contracts/schemas/` plus the publisher/consumer registry | The schema registry (C37) and the six CI checks in R01 §7 |
| `16_Container_Model_v2.md` | `docker-compose.yml` plus the service registry | Deployment manifests existing |

Until then both are hand-maintained and carry the rot risk their source pages named. The mitigation is the same in both cases: adding a subject or a container means updating the corresponding file in the same commit, not in a later documentation pass.

---

## Related

- `../review/README.md` — the review these regenerations implement
- `../decisions/README.md` — the ADR register, particularly 0037 and 0040
- `../contracts/README.md` — the six missing contract fields retrofitted onto pages 01-14
- Source pages, unmodified: `../15_Event_Catalog.md`, `../16_C4_Container_Diagram.md`
