# RFC Lifecycle

**Purpose:** the states an RFC moves through, who can move it, and what each transition requires.

---

## States

```
Draft -> In Review -> Accepted -> (ADR generated) -> Implemented -> Closed
                    -> Rejected -> Closed
                    -> Withdrawn -> Closed
Accepted -> Superseded (by a later RFC)
```

| State | Meaning | Who sets it |
|---|---|---|
| **Draft** | Author is still writing it. Not yet a review request. | Author |
| **In Review** | Submitted to Architecture Review (`../Review_Board/Architecture_Review_Process.md`). Frozen for editing except in response to reviewer comments. | Author, on submission |
| **Accepted** | Architecture Review approved it. An ADR must now be generated (`../ADR/ADR_Governance.md`) before implementation starts. | Architecture Review Board |
| **Rejected** | Architecture Review declined it. The RFC file stays, with the reasoning, as a permanent record of why — it is not deleted. | Architecture Review Board |
| **Withdrawn** | Author pulled it before a decision, usually because circumstances changed or a better alternative emerged. | Author |
| **Implemented** | The ADR generated from this RFC has been implemented and the relevant documentation updated (`../Policies/Documentation_Governance.md`). | Whoever closes the implementation change control ticket |
| **Superseded** | A later RFC replaces this one's decision. The old RFC is not deleted; it gets a `Superseded by RFC-NNNN` line at the top. | Architecture Review Board, at approval of the superseding RFC |
| **Closed** | Terminal state for Rejected, Withdrawn, or fully Implemented RFCs. No further edits. | Whoever sets the terminal state |

## Rules

1. **No RFC is deleted.** A Rejected or Withdrawn RFC is a record of a decision not to change something, which is itself worth keeping (mirrors `../../Architecture/decisions/README.md`'s own reasoning for why ADRs exist: forgotten reasoning gets re-litigated badly).
2. **No RFC number is reused**, regardless of outcome.
3. **An Accepted RFC is not itself authorisation to implement.** It authorises ADR generation. Implementation begins only once the ADR is Accepted (`../ADR/ADR_Governance.md`) — this is the RFC -> Architecture Review -> **ADR** -> Implementation sequence in full, not a shortcut through it.
4. **A Draft RFC may be edited freely** by its author. Once it enters In Review, further changes go through reviewer comments, not silent edits — the review board is evaluating a fixed document, not a moving target.
5. **Every state transition is dated**, recorded in the RFC's own `Approval Status` field and in `../Meeting_Notes/` if it happened during a review session.

## Timeout

An RFC sitting in Draft with no activity for a full implementation gate cycle (`../Roadmap/Implementation_Gates.md`) should be either submitted or explicitly marked Withdrawn — a single-operator platform has no standing quorum to force this, so it is a discipline, not an enforced timeout. Recorded here as the expectation, not as tooling.

## Related

- `RFC_Template.md`, `RFC_Guidelines.md`, `RFC_Numbering.md`
- `../Review_Board/Architecture_Review_Process.md` — the In Review stage in detail
- `../ADR/ADR_Governance.md` — what happens after Accepted
- `../Policies/Implementation_Change_Control.md` — the full RFC-to-Release chain this lifecycle is one link in
