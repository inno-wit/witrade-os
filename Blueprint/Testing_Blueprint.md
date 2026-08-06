# Testing Blueprint

**Blueprint deliverable:** B.10
**Fills the gap named in:** `../Architecture/freeze/Interface_Compliance_Report.md` §4 — no page has a standalone "Testing Strategy" field. This document is where that gap gets a real, implementation-level home, per that report's own recommendation.
**Status:** Blueprint v1.0, 2026-08-04
**Amended:** 2026-08-06 — §4.1 and §4.2 added by [ADR-0044](../Architecture/decisions/0044-kill-switch-recheck-at-broker-send.md): two hard-gate chaos tests for the mint-to-send kill-switch hand-off window, and a named entry for the ADR-0019 exit-path trap.

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

### 4.1 Mint-to-send hand-off window, added by ADR-0044

The existing chaos suite is dependency-kill shaped — it tests what happens when a store is unreachable. It does not test a state *transition* during an in-flight operation, which is the axis contract 11 invariant 19 actually protects. Both cases below are a **hard gate before live capital** (`../Architecture/decisions/0044-kill-switch-recheck-at-broker-send.md`), not merely nightly chaos:

```python
# tests/chaos/test_kill_switch_handoff.py

async def test_trip_between_mint_and_send_blocks_entry():
    """Kill switch trips after C21 mints the token, before C24 sends. Entry must not reach the broker."""
    token = await risk_service.decide(entry_proposal)          # AuthorisedOrder, intent=ENTRY, minted while clear
    await kill_switch.trip(scope="platform", reason="chaos_test")
    result = await execution_service.submit(token)              # C24's send-time recheck (invariant 19) must catch this
    assert result.state in ("REJECTED", "UNKNOWN") or result is None
    assert broker_adapter.send.call_count == 0                  # zero broker sends, the correctness SLO
    assert not await token_store.is_consumed(token.authorisation_id)  # dropped unconsumed, not compare-and-set'd

async def test_trip_between_mint_and_send_does_not_block_exit():
    """Same trip, but the order is an exit. Must still reach the broker — this is the ADR-0019 fixed point."""
    token = await risk_service.authorise_exit(exit_proposal)    # AuthorisedOrder, intent derived as EXIT from BC7 state
    await kill_switch.trip(scope="platform", reason="chaos_test")
    result = await execution_service.submit(token)
    assert result.state in ("SUBMITTED", "ACKNOWLEDGED", "FILLED")
    assert broker_adapter.send.call_count == 1                  # the send must happen despite the halt
```

**The second test is the one that matters more.** It is what stops a future engineer from "fixing" the first test into an unconditional recheck that silently violates ADR-0019 — the single most likely implementation bug in this area (§4.2 below). A chaos suite that only asserts the entry case would pass under exactly that regression.

### 4.2 Named entry: the ADR-0019 exit-path trap

Recorded explicitly rather than left as an implicit consequence of §4.1, because it is the most likely way an engineer breaks contract 11 invariant 19 while believing they are hardening it: applying the kill-switch recheck **unconditionally**, without the `intent == ENTRY` scope, "for safety." That reasoning is intuitive and wrong — an unconditional recheck traps the platform in a position during precisely the halt condition ADR-0019 exists to survive, and fails the existing correctness SLO (`contracts/11_Execution_Platform.contract.md` §SLO): *zero exits blocked by an entry-blocking rule.*

- **Guard:** `test_trip_between_mint_and_send_does_not_block_exit` (§4.1) is a required, named test in the invariant-19 test file, not folded into a generic parametrised case where it could be silently skipped or weakened.
- **Code review checklist item:** any diff touching the C24 send-path kill-switch check must show the `intent == ENTRY` guard in the same diff, or it is rejected on sight, independent of what the tests currently say — tests can be wrong or incomplete; the invariant text (contract 11, invariant 19) is the source of truth.
- **Provenance:** found during the same pre-implementation review that produced ADR-0044 (finding F6), not discovered in production. Recorded here so it stays a known trap rather than being rediscovered live.

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
