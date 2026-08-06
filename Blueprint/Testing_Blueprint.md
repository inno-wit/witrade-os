# Testing Blueprint

**Blueprint deliverable:** B.10
**Fills the gap named in:** `../Architecture/freeze/Interface_Compliance_Report.md` §4 — no page has a standalone "Testing Strategy" field. This document is where that gap gets a real, implementation-level home, per that report's own recommendation.
**Status:** Blueprint v1.0, 2026-08-04

---

## 1. The testing hierarchy

| Level | Scope | Owner | Runs |
|---|---|---|---|
| **Unit** | One function/rule/aggregate in isolation | The package that owns it (`Package_Blueprint.md` §1's `tests/unit/`) | Every commit |
| **Contract** | A service's `api/` DTOs match `packages/schemas` exactly | The package | Every commit |
| **Integration** | Cross-service flow over the real event bus (`docker-compose.ci.yml`) | Whichever bounded context initiates the flow | Every commit |
| **Replay** | Deterministic re-run of a historical decision cycle, same seed twice, byte-identical output | `quant/simulation_harness` (C28) | Every commit (a subset), nightly (full sweep) |
| **Simulation** | Full backtest against pinned Iceberg snapshots, PBO/DSR-gated | `quant/simulation_harness` (C28) | On-demand, before any model/strategy promotion |
| **Historical** | Backtest across multiple regime periods (`../Architecture/review/R11_Risk_Architecture.md` §4's stress scenarios) | `quant/simulation_harness` (C28) | Weekly, and before any risk-parameter change |
| **Load** | Sustained tick throughput, order-path latency under volume | Platform team | Before any capacity-affecting change |
| **Chaos** | Kill each dependency in turn, assert fail-closed, not degrade-open | Whichever service owns the dependency | Every commit (`../Architecture/21_Security_Architecture.md` §7's extended chaos suite) |
| **Security** | Secret scan, dependency scan, prompt-injection corpus, authorisation matrix, credential isolation | Platform/security | Every commit |
| **Performance** | p50/p95/p99 against every stated SLO (`Service_Catalog.md`) | The owning service | Nightly |
| **Acceptance** | End-to-end: bar close → journalled trade (`../Architecture/review/R06_Sequence_Diagrams.md` W1) against the paper environment | Cross-team | Before every `paper` → `prod` promotion |
| **Regression** | Every closed defect (`../Architecture/freeze/Architecture_Cross_Reference_Report.md`'s page-16 incident, for example) gets a permanent test that would have caught it | Whoever fixed it | Every commit, forever |

## 2. Ownership rule

**A test lives in the same package as the code it tests, with one exception: cross-context tests (integration, replay, chaos, acceptance) live in the top-level `tests/` directory** (`Repository_Architecture.md` §2), because they by definition span more than one bounded context and no single package should own an assertion about another package's behaviour.

## 3. Replay determinism, the platform's signature test

Directly implements `../Architecture/review/R19_Missing_Components.md` §2's non-negotiable properties:

```python
# tests/replay/test_determinism.py

async def test_backtest_is_byte_identical_across_two_runs(seed: int, period: tuple):
    run_1 = await simulation_harness.run_backtest(period, seed)
    run_2 = await simulation_harness.run_backtest(period, seed)
    assert content_hash(run_1) == content_hash(run_2)   # page 17's canonical-serialisation invariant, tested directly

async def test_llm_cache_miss_during_replay_is_a_hard_error():
    with pytest.raises(ReplayCacheMissError):
        await simulation_harness.run_counterfactual(decision_id, override={"model_version": "unrecorded"})

async def test_env_mismatch_halts_the_consumer():
    envelope = EventEnvelope(env="sim", ...)
    with pytest.raises(EnvironmentMismatchError):
        await production_consumer.handle(envelope, payload)  # T9, Architecture/21_Security_Architecture.md
```

## 4. The fail-closed chaos suite, extended per Phase 11

Directly implements `../Architecture/21_Security_Architecture.md` §7's stated extension: the credential-isolation test and the fail-closed chaos suite both gain new assertions for the Evidence Graph, Portfolio Construction, and Model Registry — killing each in turn and asserting the platform refuses to admit new candidates or promote artefacts, matching the existing assertion pattern for every pre-Phase-11 dependency.

## 5. CI wiring

Every level in §1 maps to a named stage in `Deployment_Blueprint.md` §3's CI pipeline. No test level exists outside that pipeline — a test that only runs "when someone remembers to" is a test that will stop running.

## 6. The one linter this blueprint adds that didn't exist before this freeze

`../Architecture/freeze/Architecture_Cross_Reference_Report.md` §7 ships a reusable cross-reference-validation script. **Wired into CI's `lint` stage (§3 above) as a standing job**, so a future broken link or duplicate ADR number is caught the same day it's introduced, not discovered at the next freeze audit months later.

---

## 7. Related

- `Deployment_Blueprint.md` §3 — the CI pipeline this hierarchy is wired into
- `../Architecture/review/R19_Missing_Components.md` §2 — the Simulation Harness §3's tests exercise
- `../Architecture/21_Security_Architecture.md` §7, §10 — the security and chaos suites §4 extends
- `../Architecture/freeze/Interface_Compliance_Report.md` §4 — the gap this document closes at the implementation level
