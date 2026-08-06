# ADR-0042: One Model Registry governs models, prompts, and desk weights alike, with a dual promotion gate for Tier-0 artefacts

**Status:** Accepted
**Date:** 2026-08-04
**Decided:** 2026-08-04 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** models, governance, mlflow, foundational

---

## Context

Page 07 names MLflow as the model registry for ML and RL artefacts. `../review/R19_Missing_Components.md` §8 separately describes a "Prompt & Policy Registry" for desk prompts and weights, motivated by a distinct and severe finding: replaying a decision from three months ago would otherwise use **today's** prompts, tuned on the outcomes of the very trades being replayed, contaminating every Committee backtest in the optimistic direction. `../review/R07_State_Machines.md` §6 (SM-5) already defines one 13-state lifecycle described as governing "models, prompts, and desk weights alike," which implies a single mechanism, but no page states whether that implication is a deliberate architectural decision or an incidental phrasing.

Two questions need an explicit answer before implementation: is there one registry or two, and what stops an artefact — model or prompt — from reaching `CHAMPION` (live, capital-affecting) status without adequate validation, given that a prompt change is easy to dismiss as "just wording" while carrying the same contamination risk as an unvalidated model.

## Options considered

**A. Two registries: MLflow for models/RL policies, a separate custom Prompt & Policy Registry for prompts and weights.**
*Pros:* matches the literal reading of page 07 (MLflow) versus R19 §8 (a new component); lets prompt versioning be simpler than full MLflow experiment tracking.
*Cons:* two systems enforcing the same SM-5 lifecycle independently can drift — a fix to the shadow-comparison logic applied to one and forgotten in the other is a realistic failure mode in a solo-operated codebase. The "one fact, one canonical source" discipline this whole review runs on argues against duplicating a state machine.

**B. One registry, one `resolve(artefact_kind, slot, as_of)` interface, MLflow as the underlying store for all three artefact kinds, with promotion governance identical across kinds except for a stronger gate on Tier-0 artefacts.**
*Pros:* one state machine, one audit trail, one place to fix a bug in the promotion logic. Directly resolves R19 §8's look-ahead concern for every artefact kind uniformly, not just models.
*Cons:* MLflow is not a natural fit for storing prompt text and diffs; requires a thin domain wrapper so MLflow's API does not leak into BC4/BC5 application code (the same discipline already applied to the broker and LLM Gateway ACLs).

**C. No registry at all for prompts and weights; version them as plain config with git history.**
*Pros:* zero new infrastructure.
*Cons:* git history is not point-in-time queryable by the platform at runtime (`resolve(desk, as_of)` cannot be built on top of `git log`), and does not enforce the shadow-run requirement page 08 already states as mandatory. Rejected outright; this is the status quo R19 §8 identifies as the defect.

## Decision

**Option B.** One Model Registry, `../20_Model_Registry.md`, backed by MLflow, wrapped in a domain interface (`resolve`, `register`, `promote`, `rollback`) that hides the MLflow API from every consuming context. All three artefact kinds — supervised models, RL policies, desk prompts, desk/ranking weights — pass through the identical SM-5 lifecycle. Promoting a **Tier-0** artefact (one whose failure leaves a desk or engine with no fallback) additionally requires a second, distinct sign-off from the Risk Authorisation role, separate from and in addition to the operator's promotion confirmation — a genuinely second approver in a future multi-person setting, and a second, separately-timestamped confirmation with a mandatory cooling period in the current single-operator setting (ADR-0009), mirroring the asymmetric-friction pattern already applied to risk-limit loosening (R15 §7).

## Rationale

Sharing the state machine is the only way to guarantee the look-ahead fix R19 §8 identifies actually applies everywhere it needs to. If prompts had a separate, simpler registry "because they're just text," the exact contamination scenario R19 §8 describes would remain possible for prompts even after models were properly gated — the two-registry option does not close the gap it was proposed to close unless both registries are kept in lockstep by hand, which is a maintenance burden this ADR is designed to remove. The Tier-0 dual-gate is new relative to R19 §8 and is added because the review's own risk taxonomy (`../review/R11_Risk_Architecture.md` RT7, model risk) treats correlated or unvalidated model failure as one of the two most likely large-loss categories for this platform, and a promotion event is exactly the moment that risk is introduced.

## Consequences

**Positive**
- One audit trail answers "what was live at time T" for any artefact kind, with no cross-registry reconciliation required.
- The mandatory-shadow-run rule page 08 already states becomes enforceable in one place rather than needing separate enforcement code for prompts and models.
- The Tier-0 dual gate directly targets RT7 (model risk), the review's own highest-priority completeness gap for page 10.

**Negative**
- MLflow must be wrapped by a domain adapter for prompt/weight storage, which is additional integration work relative to a purpose-built lightweight prompt store.
- The dual-gate adds friction to legitimate Tier-0 promotions, which is the intended cost, not an oversight — see `../review/R15_Security.md` §7's asymmetric-friction principle, extended here from risk limits to model promotions.

**Neutral**
- MLflow's own versioning features are used for the artefact blob and metrics; the SM-5 state and the promotion/rollback audit are owned by this registry's own tables, not by MLflow's built-in stage tags, because MLflow's native stages do not have a Tier-0 dual-gate concept and should not be asked to enforce one.

## Tripwire

1. If a Tier-0 artefact promotion is ever found to have skipped the second confirmation, the gate is not actually enforced in the registry service and this decision has been implemented as policy, not mechanism — treat as a P0 finding, not a process reminder.
2. If prompt/weight versioning volume or query patterns outgrow what the MLflow wrapper handles cleanly (a plausible outcome once desk prompts are tuned frequently), consider promoting the prompt/weight store to its own backing store while keeping the shared `resolve`/`promote`/`rollback` interface — the interface, not the backing store, is the part of this decision that must not change.
3. If the Tier-0 criterion is never actually assigned to any artefact in practice (every model and prompt ends up classified Tier 1/2 to avoid the friction), the classification is being gamed and the criterion needs an objective, not self-assigned, definition.

## Related

- ADR-0030 (prompts are versioned, point-in-time-resolvable registry artefacts) — this ADR generalises 0030's scope from prompts alone to every artefact kind
- ADR-0002 (deterministic/AI separation)
- `../20_Model_Registry.md` — the full specification
- `../review/R07_State_Machines.md` §6 (SM-5, unmodified)
- `../review/R19_Missing_Components.md` §8-9
- `../review/R11_Risk_Architecture.md` §6 (model risk register, RT7)
- Source: `../07_ML_RL_Model_Layer.md`
