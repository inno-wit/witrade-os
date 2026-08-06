# ADR Index

**Freeze deliverable:** A.6
**Method:** every ADR file's `**Status:**` line extracted mechanically (not read from `../decisions/README.md`'s own summary, which is checked independently below rather than trusted), plus a mechanical check that every file has a `## Tripwire` section.
**Status:** Freeze v1.0 input, 2026-08-04

---

## 1. Classification

| Status | Count | Files |
|---|---:|---|
| **Accepted** | **43** | 0001-0043, all of them |
| Superseded | 0 | — |
| Deprecated | 0 | — |
| Proposed | 0 | — |
| Merged | 0 | — |

**43 of 43 files, verified by extracting the literal `**Status:**` line from every file, not by reading the register's own claim.** `../decisions/README.md`'s stated "43 of 43 written, 43 of 43 Accepted" is independently confirmed true, not merely repeated. A directory-wide search for "supersed" across `../decisions/` returned matches in 7 files, each checked individually (§2) — none is an actual supersession, all are either forward-looking process language (ADR-0009's stated gate for a future multi-tenancy ADR) or a reference to an ADR superseding a *review finding*, not another ADR (ADR-0043 superseding `../review/R19_Missing_Components.md` §12's deferred design, which is expected and correct — the review layer is exactly what ADRs are meant to supersede as they get written).

---

## 2. The "supersede" mentions, individually cleared

| File | What it actually says | Real supersession? |
|---|---|---|
| `../decisions/0005-choreography-with-one-orchestrated-saga.md` | Domain-object `supersedes` link pattern for a superseded *decision cycle*, not this ADR | No |
| `../decisions/0008-docker-compose-over-kubernetes.md` | Generic process language | No |
| `../decisions/0009-single-operator-single-tenant.md` | States multi-tenancy, if it ever happens, requires "a superseding ADR and a project" — a rule this ADR imposes on a hypothetical future ADR, not evidence this one has been superseded | No |
| `../decisions/0021-deadlock-and-quorum-failure-resolve-to-no-trade.md` | Generic process language | No |
| `../decisions/0030-prompts-are-versioned-point-in-time-artefacts.md` | Prompt-versioning's own `supersedes` field for prompt artefacts, unrelated to ADR status | No |
| `../decisions/0036-raw-data-is-immutable-corrections-are-versions.md` | Data-correction `supersedes` link, unrelated to ADR status | No |
| `../decisions/0043-portfolio-construction-is-a-twelfth-bounded-context.md` | States this ADR supersedes `../review/R19_Missing_Components.md` §12 (a **review finding**, correctly) | No — this is the intended relationship between the decisions layer and the review layer |

---

## 3. Register, by domain

Same grouping as `../decisions/README.md`, restated here as the freeze-certified index rather than duplicated content — counts independently verified, not copied.

| Domain | ADRs | Count | All Accepted? |
|---|---|---:|---|
| Foundational | 0001-0009 | 9 | ✅ |
| Domain and boundaries | 0010-0016 | 7 | ✅ |
| Safety and risk | 0017-0025 | 9 | ✅ |
| AI and decision | 0026-0033 | 8 | ✅ |
| Data and lineage | 0034-0040 | 7 | ✅ |
| **Architecture completion (2026-08-04)** | 0041-0043 | 3 | ✅ |

---

## 4. Priority distribution

Extracted from `../decisions/README.md`'s register table (P0/P1 tags), cross-checked against each ADR's own content for consistency (an ADR tagged P1 whose own Context section describes a capital-loss-blocking scenario would be a red flag; none found).

| Priority | Count | What it means |
|---|---:|---|
| **P0** | 25 | Must exist before implementation starts — constrains code that would otherwise be written wrong |
| P1 | 18 | Before live capital |
| P2 | 0 (folded into P1 or P0 at acceptance time) | — |

**25 of 43 ADRs are P0.** This is the single most load-bearing number in this index for sequencing implementation: `../../Blueprint/Engineering_Roadmap.md` treats "every P0 ADR this bounded context depends on is Accepted" as a hard entry gate per phase, and per §1 above, all 25 already are.

---

## 5. Tripwire coverage

| Check | Result |
|---|---|
| Every ADR has a `## Tripwire` section | ✅ **43 of 43**, verified by mechanical scan, zero missing |
| ADRs with an explicit "no reversal tripwire" (fixed points) | 8, per `../decisions/README.md`: 0015, 0016, 0017, 0019, 0022, 0023, 0035, 0037 |
| ADRs with a genuine, monitorable tripwire | 35 |
| Tripwire metrics named but not yet instrumentable (no code exists) | All of them — this is the correct, expected state pre-implementation, not a gap. `../decisions/README.md`'s own "Tripwire metrics to instrument" table (17 metrics) is the punch list `../../Blueprint/Observability_Blueprint.md` inherits directly |

**The quarterly tripwire review `../decisions/README.md` calls for cannot begin until at least one quarter of live operation exists.** Recorded here so the first quarterly review, whenever it happens, has this index as its dated starting point rather than needing to reconstruct which ADRs even have a tripwire.

---

## 6. What this index adds beyond `../decisions/README.md`

`../decisions/README.md` is the canonical register (`Canonical_Source_Validation.md` §1 row 5). This index is the **freeze-time certification** that the register's own claims are true, checked mechanically rather than asserted, dated 2026-08-04, and it adds two things the register does not itself state: the "supersede"-mention clearance (§2) and the explicit tripwire-coverage percentage (§5, 100%).

---

## 7. Related

- `../decisions/README.md` — the canonical, living register this index certifies
- `Architecture_Freeze_v1.md` — where "43/43 Accepted, 100% tripwire coverage" becomes a checked freeze-gate line item
- `../../Blueprint/Engineering_Roadmap.md` — where the 25 P0 ADRs become implementation entry gates per bounded context
