# RFC Numbering

**Purpose:** one unambiguous number per RFC, assigned once, never reused, never reordered.

---

## Scheme

`RFC-NNNN`, four digits, zero-padded, starting at `RFC-0001`. Sequential, global (not per bounded context, not per year) — the same discipline `../../Architecture/decisions/` already applies to ADRs 0001-0043, deliberately mirrored rather than reinvented.

## Assignment rule

The number is assigned **at file creation** (when the RFC enters `Draft`), not at approval. This means:

- A Withdrawn or Rejected RFC keeps its number permanently. `RFC-0004` being rejected does not free `0004` for reuse and does not mean the next RFC is `0004` again.
- Numbers are not meaningful as a queue position. `RFC-0012` might reach Accepted before `RFC-0009` does, if `0009` sat longer in review.
- There is no "gap-filling." A range with a Withdrawn RFC in it (e.g., `0004` Withdrawn, `0005` Accepted) is expected and correct, not an error to fix.

## File location and naming

`RFC/RFC-NNNN-short-slug.md`, slug in kebab-case, matching the ADR file-naming convention already established in `../../Architecture/decisions/NNNN-slug.md`.

## Index

`RFC/README.md` (create on first RFC) is the running register: number, title, status, date, bounded context(s) touched — the same shape as `../../Architecture/decisions/README.md`'s own register table, kept current by whoever transitions an RFC's state (`RFC_Lifecycle.md`).

## Relationship to ADR numbering

RFC numbers and ADR numbers are **independent sequences.** An Accepted RFC generates a **new** ADR, continuing the `../../Architecture/decisions/0001`-`0043` sequence from `0044` onward (`../Decision_Log/README.md`). `RFC-0012` becoming `ADR-0044` is normal; the two numbers are not expected to match, and no attempt is made to keep them in sync.

## Related

- `RFC_Lifecycle.md` — when a number is assigned, relative to state
- `RFC_Guidelines.md` — how to write the RFC this number will identify
- `../Decision_Log/README.md` — where the resulting ADR gets its own number
- `../../Architecture/decisions/README.md` — the ADR register this numbering scheme deliberately parallels
