# ADR-0024: Risk limits are versioned, dual-controlled artefacts, not configuration

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** risk, governance, security

---

## Context

The ADD specifies risk limits (per-trade risk, daily loss, drawdown ladder, exposure caps, correlation limits) without saying where they live or how they change. The default resolution is a configuration file.

**Risk limits in a config file that anyone can edit are not limits.** They are suggestions with a text editor attached.

The threat this addresses is not an attacker. It is threat T4 in the security model: **the operator, under stress, disabling a control that was working.** That is assessed as the highest-likelihood path to a large loss on this platform, higher than credential compromise or supply-chain attack.

The specific scenario is precise and predictable: the account is in a 9% drawdown, the ladder has cut size to 0.25x, a setup appears that looks like the one that will make it back, and the drawdown limit is a number in a YAML file that takes eleven seconds to change. Every dangerous limit change in the history of retail and professional trading is a loosening made during or immediately after a drawdown.

## Options considered

**A. Config file in git.**
*Pros:* version-controlled; reviewed if a PR is used.
*Cons:* a solo operator merges their own PR; the change can be applied by editing the deployed file; no dry run; no cooling period; no point-in-time record of what was in force when a given trade was assessed.

**B. Database table, editable via the dashboard.**
*Pros:* auditable; no deploy needed.
*Cons:* a dashboard button is the fastest possible path to an impulsive change, which is the exact failure mode.

**C. Versioned `LimitSet` aggregate with dual control, mandatory dry run, cooling period, and asymmetric friction.**
*Pros:* limits become artefacts with a lifecycle; every assessment records the version it used; the impulsive change is structurally slowed.
*Cons:* changing a limit becomes a process, which is friction, including when the change is correct and urgent.

## Decision

**Option C.**

1. **`LimitSet` is a versioned aggregate, immutable once published.** A change publishes a new version with an `effective_from`. Never retroactive, never edited in place.
2. **Every `RiskAssessment` records `limit_set_version`.** A post-mortem can prove exactly what was in force.
3. **Dual control** on publication. In a solo-operator context a second person is unavailable, so dual control is implemented as **a delay plus a written justification recorded in the audit log**. Weaker than a second approver, and still effective against the specific failure, because the failure is impulsive rather than reasoned.
4. **Mandatory dry run.** Before publication, replay the last 30 days of proposals against the new limit set and report what would have changed: which trades would newly pass, which would newly fail, and the aggregate P&L delta. **A limit change whose impact is unknown is a limit change nobody should approve.**
5. **Asymmetric friction:**

| Direction | Requirement |
|---|---|
| **Tightening** (any limit made stricter) | Immediate. No dry run required, no cooling period, no justification |
| **Loosening** (any limit made looser) | Dry run + written justification + **cooling period** before `effective_from` |

6. **Cooling period on loosening: minimum 12 hours, and never inside an active drawdown below the 5% rung.** Below that rung, loosening requires the drawdown to recover above it first. This is the specific control for the specific scenario.
7. **Limit changes are audited in the append-only, hash-chained store** (ADR-0039): actor, timestamp, justification, before/after values, dry-run result.
8. **`kelly_fraction` is part of the `LimitSet`** (ADR-0020) and is governed by the same rules.

## Rationale

Rule 5 is the whole decision. Every other rule supports it.

Tightening a limit can only reduce risk, so friction there is pure cost and would train the operator to route around the process. Loosening a limit increases risk, always, and is the only direction in which a mistake is expensive. Making the two directions asymmetric means the process is fast when it is safe and slow when it is not, which is the only shape that survives contact with a real operator.

Rule 6 targets the scenario directly rather than generically. A 12-hour cooling period is enough for the impulse to pass, and the drawdown condition prevents the specific case where the cooling period is waited out while the state that made the change dangerous persists. This is deliberately the most restrictive rule in the platform and it applies at the moment the operator will most resent it, which is the point.

Rule 4 changes the nature of the conversation. "Raise the daily loss limit from 2% to 3%" is a judgement. "Raise the daily loss limit from 2% to 3%, which over the last 30 days would have allowed 7 additional trades with a net result of -1.4R" is a decision with evidence. Most bad limit changes do not survive their own dry run.

Rule 2 is what makes post-mortems possible. Without it, "why was this trade allowed" cannot be answered for any trade older than the last config edit.

## Consequences

**Positive**
- The highest-likelihood path to a large loss gains real friction, applied precisely where it belongs.
- Every historical assessment is explicable against the limits actually in force.
- Limit changes gain evidence, so they can be reviewed and learned from.
- Backtests can resolve the historically correct limit set, closing another point-in-time contamination path (ADR-0034).

**Negative**
- Genuine, urgent, correct loosenings are also slowed. Accepted: an urgent need to loosen a risk limit is almost never genuine, and the cases where it is (a broker changing margin requirements, for instance) can be handled by tightening elsewhere immediately and loosening through the process.
- A dry-run harness to build, which depends on the replay capability (ADR-0035). This makes ADR-0024 a P1 rather than a P0.
- The operator will find this annoying at exactly the moment it is working.

**Neutral**
- Small data volume, Postgres `risk` schema.

## Tripwire

1. **If the cooling period is ever bypassed**, the bypass itself is an audited event requiring a post-hoc written review in the next weekly cycle. There is no silent override.
2. **If loosening requests exceed roughly one per quarter**, the limits were set wrongly at the outset and should be re-derived from the strategy's actual risk profile rather than adjusted repeatedly.
3. **If the dry run is consistently ignored** (changes approved despite an unfavourable dry run), the control has become theatre and needs a stronger form.

## Related

- ADR-0020 (fractional Kelly) is governed by this
- ADR-0011 (Risk as sole authority) records `limit_set_version` on every assessment
- ADR-0039 (audit service) holds the change record
- ADR-0035 (replay) enables the dry run
- `../review/R11_Risk_Architecture.md` §9
- `../review/R15_Security.md` §7 (threat T4)
