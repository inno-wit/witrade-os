# Meeting Notes

**Purpose:** dated, append-only minutes of Architecture Review Board sessions. Never edited after the fact — a correction is a new dated entry referencing the one it corrects, the same discipline every other artefact in this governance system follows.

---

## When a session gets minuted

Any time an RFC moves through `../Review_Board/Architecture_Review_Process.md` stages 2-5 (Review, Technical Validation, Impact Analysis, Approval), or any time a gate (`../Roadmap/Implementation_Gates.md`) closes with a required-review sign-off. A session with no RFC or gate decision in it (a working session, a research spike) does not need a minuted entry here — this folder is a decision record, not a general work log (`../../Architecture/decisions/README.md`'s stated rationale for why ADRs exist applies to why this folder exists: undocumented reasoning gets re-litigated badly).

## Entry format

One file per session: `YYYY-MM-DD-short-slug.md`. Minimum contents:

```markdown
# ARB Session — YYYY-MM-DD

**Attendees:** (role: person — single-operator platform, so this is the role(s) acted in, per `../Review_Board/Architecture_Review_Process.md`)
**RFCs/Gates discussed:** RFC-NNNN, Gate N

## Decisions

- RFC-NNNN: Accepted / Rejected / Withdrawn — one-line reasoning, full reasoning lives in the RFC's own Decision section
- Gate N: closed / not closed — what's outstanding if not closed

## Action items

- [ ] ...
```

## Index

| Date | Session | RFCs/Gates | Outcome |
|---|---|---|---|
| — | *(none yet — first entry created at the first post-charter Architecture Review session)* | | |

## Related

- `../Review_Board/Architecture_Review_Process.md` — the process these sessions execute
- `../RFC/RFC_Lifecycle.md` — the state transitions these sessions record
- `../Decision_Log/README.md` — where an Accepted RFC's resulting ADR gets logged, separate from this session record
