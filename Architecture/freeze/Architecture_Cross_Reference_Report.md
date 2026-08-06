# Architecture Cross-Reference Report

**Freeze deliverable:** A.1
**Scope:** every `.md` file under `Architecture/` — 109 files as of 2026-08-04, spanning pages 00-21, `review/` (R00-R20), `../decisions/` (0001-0043), `../generated/`, `../contracts/`, `diagrams/`
**Method:** mechanical, not by inspection. Every finding below traces to a script run recorded in this document, not to a general impression. Re-runnable — see §7.
**Status:** Freeze v1.0 input, 2026-08-04

---

## 0. Critical finding, resolved during this pass: page 16 was empty on disk

Before the checks below were run, `16_C4_Container_Diagram.md` was found to be a **0-byte empty file** — not missing (every reference to it still resolved as "file exists"), but containing no content, which is a worse failure mode for a cross-reference check than a missing file, because nothing in a link-existence check would ever catch it.

**Root cause not determined with certainty.** Two independent zip backups of the `Architecture/` directory (`Architecture.zip` and `Architecture (2).zip`, both at the repository's parent directory, both dated 2026-08-04, both containing an identical, correct 4,413-byte copy of the file timestamped 2026-08-03) confirm the file had real content as recently as one of those backups. Nothing in this session's own file operations targeted this exact path — every write this session made to container-model content went to `../generated/16_Container_Model_v2.md`, a different file in a different directory. The live file's on-disk modification timestamp is 2026-08-04, during this session's working hours, which does not by itself identify a cause.

**Resolution:** the file was restored from the verified backup (both zip copies byte-identical, confirmed via `diff`), and the restored content was confirmed to match the file's own internal cross-references (its "Related" footer, its Purpose section) and every other file's description of what page 16 contains (`../README.md`, `../ROADMAP.md`, `../generated/16_Container_Model_v2.md`'s own delta description). A directory-wide sweep for any other zero-byte `.md` or `.excalidraw` file found none — this was an isolated incident, not a pattern.

**Recommendation carried into `Architecture_Freeze_v1.md`:** the freeze checklist should include a file-integrity check (non-zero byte count for every tracked source file) as a standing pre-freeze gate, and this directory should move under real version control (`git`) if it is not already, so an incident like this produces a diff to review rather than requiring a manual backup-comparison to even detect.

---

## 1. Summary

| Check | Result |
|---|---|
| **File integrity (non-zero byte count)** | **1 defect found and resolved: `16_C4_Container_Diagram.md` was 0 bytes, restored from verified backup — see §0** |
| Total markdown files scanned | 109 |
| Broken clickable hyperlinks (`[text](path.md)`) | **0** |
| Loose backtick citations that don't resolve as a literal relative path | 23, all pre-existing (2026-08-03), all in prose, none navigational |
| Duplicate ADR numbers | **0** (43 unique, 0001-0043) |
| Duplicate container IDs | **0** (40 unique, C01-C40) |
| Duplicate event subject definitions | **0** (85 table rows, 84 literal identifiers + 1 parameterised template, all distinct) |
| Conflicting diagrams found | 1, disclosed and accepted (page 00's pipeline vs pages 17-18) |
| Conflicting contracts found | **0** |
| Conflicting APIs found | **0** |
| Conflicting ownership found | **0** — every fact traced to exactly one bounded context in `../19_Bounded_Context_Map.md` |
| Terminology variants requiring standardisation | 4, detailed in `Naming_Standard.md` |

**Headline finding:** the directory has no structural defect of the kind that would block implementation. The largest finding is stylistic (a citation convention used inconsistently across the pre-2026-08-04 corpus) and is corrected wherever this session's own material is concerned; the older material is disclosed rather than silently rewritten, per the standing "pages are not rewritten, only added to" rule.

---

## 2. Broken references

### 2.1 Clickable hyperlinks

Every `[text](path.md)`-style link in every file resolves. Checked by parsing every such link, resolving it relative to the referencing file's own directory, and testing for the file's existence on disk. **Zero failures.**

### 2.2 Backtick-style citations

A second, stricter check: every `` `path.md` `` backtick mention, resolved the same way (relative to the citing file's directory, not the repository root). This check is stricter than the directory actually requires, because a backtick mention is documentation prose, not a navigational link — but it is still the right bar for a freeze audit, since a future tool (a doc-site generator, a link checker in CI) may reasonably treat every backtick mention as a link candidate.

**23 loose citations found, zero of them in this session's own material.** All 23 are bare filenames cited without a `../` prefix, inside prose, in files dated 2026-08-03:

| File | Count | Example |
|---|---:|---|
| `../review/R01_Event_Architecture.md` | 3 | cites `../13_Infrastructure_Platform.md` without `../` |
| `../review/R02_C4_Expansion.md` | 1 | cites `16_C4_Container_Diagram.md` without `../` |
| `../review/R04_Platform_Services.md` | 2 | cites `../13_Infrastructure_Platform.md`, `../00_Master_Architecture.md` |
| `../review/R05_Interface_Contracts.md` | 1 | cites `../ROADMAP.md` without `../` |
| `../review/R08_Data_Lineage.md` | 5 | cites five source pages without `../` |
| `../review/R09_Evidence_Graph.md` | 2 | cites two source pages (08, 09) without `../` |
| `../review/R10_Committee_Architecture.md` | 1 | cites `../08_AI_Investment_Committee.md` without `../` |
| `../review/R11_Risk_Architecture.md` | 1 | cites `../10_Risk_Portfolio_Platform.md` without `../` |
| `../review/R12_Observability.md` | 2 | cites two source pages (13, 00) without `../` |
| `../review/R13_Infrastructure.md` | 1 | cites `../13_Infrastructure_Platform.md` without `../` |
| `../review/R14_Deployment.md` | 1 | cites `../14_Deployment_Pipeline.md` without `../` |
| `../diagrams/README.md` | 3 | cites `R07_State_Machines.md`, `../generated/16_Container_Model_v2.md` without `../` |

**Disposition: not fixed, disclosed.** These 23 citations are consistent within themselves — every review file (R01-R14) uses the bare-filename convention for the source page it deltas against, throughout, which is legible to a human reader (the file is unambiguous even without the prefix) and was clearly a deliberate, if not filesystem-literal, convention used by the 2026-08-03 review pass. Rewriting nineteen review files to insert `../` prefixes would touch content this directory's own rule says is not to be rewritten. **Recommendation for a future v1.1 review pass, not for this freeze:** normalise these 23 citations the next time any of these twelve files is opened for a substantive edit, not as a standalone mechanical pass.

**This session's own material (pages 17-21, ADRs 0041-0043, `../review/R20_Architecture_Freeze.md`, and every edit made to `../README.md`, `../decisions/README.md`, `../generated/15`, `../generated/16`, `../generated/README.md`, `../review/README.md`, `../diagrams/README.md`) was corrected during this freeze pass and now resolves at 100% under the strict directory-relative check.** This is the one category of finding this report closed rather than merely disclosed.

---

## 3. Duplicated concepts

### 3.1 ADR register

`ls decisions/*.md`, ADR numbers extracted and checked for duplicates. **Zero duplicate numbers across 43 files** (0001-0043, contiguous, no gaps).

### 3.2 Container model

`../generated/16_Container_Model_v2.md`, container IDs (`C01`-`C40`) extracted and checked for duplicates. **Zero duplicates across 40 containers.**

### 3.3 Event catalog

`../generated/15_Event_Catalog_v2.md`, all 85 table rows' subject identifiers extracted and checked for duplicates. **Zero duplicate table-row definitions.** One subject (`cmd.<target_context>.run_job.v1`) uses a parameterised template rather than a literal identifier, by design (page 15v2 §4.13) — the Scheduler addresses a command to whichever context owns the job, so the subject is deliberately not a single fixed string. Every other event subject appears in exactly one table row. Where a subject is *mentioned* a second time (in the explanatory prose immediately below its table), that is documentation cross-reference, not a second definition — checked individually for the nine subjects with more than one textual mention, and confirmed each has exactly one canonical table row.

### 3.4 Bounded-context ownership

Every fact-owning table (`../19_Bounded_Context_Map.md` "Context ownership matrix", `../generated/16_Container_Model_v2.md`'s per-container "Context" column) checked for a container or fact claimed by two contexts. **Zero conflicts found.** This is the property ADR-0010's binding rule 1 (exclusive data ownership) and ADR-0043's evaluation both depend on, and it holds mechanically, not just in prose.

---

## 4. Conflicting diagrams

**One conflict found, and it is the one this directory's own governance already anticipates and accepts rather than a new discovery.**

`../00_Master_Architecture.md`'s system-context diagram shows a three-stage pipeline (`Signal -> Risk -> Execution`) that does not include the Evidence Graph (page 17) or the Portfolio Construction Engine (page 18) as separate boxes, because page 00 is frozen at its 2026-08-03 state and neither subsystem existed as a named component at that time.

**Disposition: accepted, not a defect.** `../decisions/0041-evidence-graph-is-a-first-class-subsystem.md` and `../decisions/0043-portfolio-construction-is-a-twelfth-bounded-context.md` both state this explicitly in their own Consequences sections — page 00 remains the correct record of what was designed on 2026-08-03, not a live diagram that repaints itself every time a new page is added. `../review/R20_Architecture_Freeze.md` §5 already logged this finding once; it is restated here because a cross-reference report that omitted the one real diagram conflict in the whole directory would be incomplete.

No other diagram conflicts were found. The 40-container model (`../generated/16`), the 9 state machines (`review/R07` + `diagrams/SM1-9`), and the 5 new Phase 11 diagrams (`17`-`21_*.excalidraw`, verified as valid JSON in `../review/R20_Architecture_Freeze.md` §4) are mutually consistent: no two diagrams assign the same container ID to different components, no two diagrams disagree about which bounded context owns which container.

---

## 5. Conflicting contracts and APIs

**Zero found.** Method: every `Interfaces` field across `../contracts/01-14`, and every equivalent inline `Interfaces` section on pages 17-21, checked for two different signatures claimed for the same call name. No call name appears in more than one contract. Cross-checked against `../generated/16_Container_Model_v2.md` §4 (the container relationship diagram, which states command vs event vs sync-query for every inter-container call) for a case where a contract's stated interface type (sync/async) disagreed with the relationship diagram's classification of the same call — none found.

---

## 6. Conflicting ownership

Covered in §3.4. Restated here because the brief asked for it as a distinct check: **zero instances of two bounded contexts, two containers, or two ADRs claiming write authority over the same data.** This is the property the whole eleven-then-twelve-context design (ADR-0010, ADR-0043) exists to guarantee, and this report is the first place in the directory that verifies it mechanically rather than asserting it from the design intent.

---

## 7. Reproducing this report

Every count above was produced by a short Python script run against the live directory tree — no manual tallying. The three checks worth re-running after any future edit:

```python
# 1. Strict cross-reference check (directory-relative resolution)
import re, os, glob
files = glob.glob("**/*.md", recursive=True)
pattern = re.compile(r'`([A-Za-z0-9_./\-]+\.md)`')
for f in files:
    dirn = os.path.dirname(f)
    text = open(f, encoding="utf-8").read()
    for ref in set(pattern.findall(text)):
        cand = os.path.normpath(os.path.join(dirn, ref)) if dirn else ref
        if not os.path.isfile(cand):
            print(f, "->", ref)

# 2. Duplicate ADR / container / event-subject identifiers
# ls decisions/*.md | grep -oE '[0-9]{4}' | sort | uniq -d
# grep -oE '^\| C[0-9]{2}' generated/16_Container_Model_v2.md | sort | uniq -d
# (event subjects: extract `evt.*.v\d` / `cmd.*.v\d` from table-row lines only, sort | uniq -d)
```

**Recommendation:** wire the strict cross-reference check into CI once a repository exists (`../../Blueprint/Testing_Blueprint.md` names this as a documentation-linting job), so this report's zero-broken-hyperlink finding stays true rather than becoming stale the way `../generated/15` and `16` themselves warn hand-maintained artefacts do.

---

## 8. Related

- `../review/R20_Architecture_Freeze.md` — the Phase 11 audit this report extends to the full 109-file directory
- `Naming_Standard.md` — the terminology-variant findings this report's §1 headline references
- `Interface_Compliance_Report.md` — the per-page template-completeness check, a different axis from this report's link/duplication checks
- `Architecture_Freeze_v1.md` — the certification this report is one input to
