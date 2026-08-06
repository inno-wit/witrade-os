# R18 — Technical Debt Review

**Deliverable:** 18
**Delta against:** the whole ADD
**Status:** Review v1.0

---

## 1. Framing

Debt identified before implementation is not debt. It is a design choice. The point of this file is to name the places where the current design will accrue debt **if implemented as written**, and to give each one a mitigation that costs far less now than after code exists.

Debt is scored on two axes:

- **Interest rate:** how fast the cost grows with time and code volume.
- **Principal:** what it costs to fix once incurred.

The dangerous quadrant is high interest, high principal. Those are the ones that must be addressed before the first commit.

---

## 2. Debt register

### Critical: high interest, high principal. Fix before implementation.

| # | Debt | Source | Why it compounds | Mitigation | Cost now vs later |
|---|---|---|---|---|---|
| **D1** | **Wire protocol without an envelope, versioning, or schema registry** | Page 15 | Every service written before this exists must be retrofitted. Every stored event lacks correlation, causation, and version fields permanently, so historical forensics is impossible for that period | R01 §4, §7. Freeze the envelope before the first publisher | 2 days now. Weeks later, plus permanently degraded history |
| **D2** | **`datetime.now()` scattered through the codebase** | Absent from the ADD | Every direct clock call breaks replay determinism. The failure is silent: backtests still run, they are just wrong. Discovery typically comes months later, when a strategy that backtested well fails live | ADR-035 plus a CI lint from commit one | 1 hour now. A full audit of every file later, with no way to know which historical backtests were affected |
| **D3** | **Floats for money, price, and quantity** | Not specified anywhere | Rounding errors in position sizing are real losses and are extremely hard to trace. Once floats are pervasive, converting is a full-codebase change with subtle behaviour differences | `Decimal` types in the shared kernel, plus a CI lint banning float in those paths | 2 hours now. A dangerous refactor later |
| **D4** | **Shared DuckDB as a multi-writer database** | Pages 03, 13, 16 | Blocks multi-service deployment entirely. Every day of code written against the wrong storage model is a day of migration | ADR-003, Iceberg | 1 day now. A data migration plus rewriting every write path later |
| **D5** | **Broadcast events used as commands on the order path** | Page 15 | Once services are wired this way, changing the integration primitive means changing every producer and consumer simultaneously. Meanwhile, duplicate orders are possible | R01 §2 | 1 day now. A coordinated rewrite later, with capital at risk in the interim |
| **D6** | **Position state without an owner** | Pages 03, 08, 09, 10, 11, 12 all touch it | Six components each build their own model of a position. They will disagree, and the disagreement surfaces as a risk breach. Consolidating afterwards means changing all six | BC7 Portfolio as an owning context, R03 §7 | 3 days now. A cross-cutting refactor later |
| **D7** | **Desk citations as literal values rather than references** | Page 08 | Changes the desk schema, the validation logic, the evidence model, and the rendering path. Also, every decision recorded before the change has a weaker audit trail | R03 §5 | 1 day now. A committee rewrite later |
| **D8** | **No point-in-time parameter and prompt resolution** | Pages 04, 08, 12 | Every backtest run before this exists is contaminated by parameters tuned after the fact. The results are not merely wrong, they are optimistically wrong, which is the dangerous direction | R04 §5, ADR-030 | 2 days now. Every historical validation result becomes untrustworthy later |

### High: high interest, moderate principal

| # | Debt | Why it compounds | Mitigation |
|---|---|---|---|
| **D9** | **Hand-maintained event catalog and container diagram** | Page 15 predicts its own rot in its Failure Modes section. Documentation that is wrong is worse than absent, because it is trusted | Generate both from code annotations and manifests (R01 §7, R04 §7) |
| **D10** | **No transactional outbox** | Every service that writes state and publishes gains a divergence window. Retrofitting means touching every write path | R01 §8, from the first stateful service |
| **D11** | **Prose failure modes with no detection mechanism** | Every page lists failure modes; almost none say how the failure is detected. Unmonitored failure modes become production surprises | Every failure mode gets a metric and an alert at design time (R12 §3) |
| **D12** | **No `Intent` distinction between entry and exit** | Threading a concept through an existing API is far harder than designing with it | ADR-019 |
| **D13** | **Extension points described in prose, not types** | "A new desk is a new box with zero changes" is true only if `Desk`, `RegimeModel`, `RiskRule` and `BrokerAdapter` are actual interfaces. Otherwise the second implementation reveals the abstraction was wrong | Define the six L4 contracts now (R02 §5), each with 2+ implementations from day one |
| **D14** | **Test data and fixtures unaddressed** | Without realistic, versioned fixtures, tests get written against toy data and miss the cases that matter (gaps, DST, partial fills, requotes) | A fixture library built alongside the first service, including a recorded set of adversarial market conditions |

### Moderate: manageable if addressed before scaling

| # | Debt | Mitigation |
|---|---|---|
| **D15** | Configuration scattered per service | Configuration Service with four distinct kinds (R04 §5) |
| **D16** | No cost attribution per decision | Cost Governor, and record cost in the decision record from the first cycle |
| **D17** | MT5-specific concepts leaking beyond the adapter | The `BrokerAdapter` ACL plus a CI lint (R03 §9). Three implementations from day one is the real defence |
| **D18** | TradeHub code reuse importing TradeHub's data model | ACL-5. Reuse the logic, translate the model |
| **D19** | No fixture for "the broker behaves badly" | A simulated adapter with injectable pathologies: requotes, partial fills, rejections, timeouts, wrong symbols |
| **D20** | Alerting built after the services | Alerts are designed with each service, not retrofitted. A service without an alert is a service nobody watches |
| **D21** | Runbooks written after the first incident | Each P0 alert ships with its runbook. No P0 alert without one |

### Accepted debt (deliberate, with tripwires)

| # | Accepted | Why | Tripwire |
|---|---|---|---|
| A1 | Docker Compose instead of Kubernetes | Operational cost exceeds benefit at 3 hosts and 1 operator | >3 hosts, autoscaling needed, >1 operator, or multi-tenancy |
| A2 | NATS only, no Kafka | Volume does not justify two messaging systems | R13 §4's four conditions |
| A3 | Python throughout, no compiled hot path | 11s budget on a 15m timeframe has enormous headroom | Target timeframe below 1 minute, or p99 order path above 150ms |
| A4 | `networkx` in memory instead of a graph database | Hundreds of cycles per day | Multi-hop cross-cycle queries become routine and Postgres CTEs exceed ~1s |
| A5 | Single-tenant | The platform serves one operator | Productisation. This is an ADR-level fork, not an increment (ADR-009) |
| A6 | No GPU | No workload justifies one | Substantial RL training |
| A7 | Custom saga runner instead of Temporal | One orchestrated flow | Three human-gated long-running workflows |

**Accepted debt with a written tripwire is not debt. It is a scoped decision.** The failure mode is accepting it without the tripwire, which is how a reasonable early choice becomes an unexamined constraint in year three.

---

## 3. The four disciplines that must be mechanical from commit one

Every one of these erodes silently under time pressure and cannot be recovered by later effort. Each costs under a day to enforce mechanically.

| Discipline | Enforcement | Erodes into |
|---|---|---|
| **Clock injection** | CI lint: no `datetime.now`, `time.time`, `asyncio.sleep`, `pd.Timestamp.now` outside `platform/clock.py` | Non-deterministic replay, invisible for months |
| **Decimal for money** | CI lint: no `float` annotation in money/price/quantity paths | Sizing errors that are real losses |
| **No vendor imports outside adapters** | CI lint: no `anthropic`, `mt5`, vendor SDKs outside `adapters/` | Vendor lock-in, untestable code, impossible model upgrades |
| **Schema registry as the source of truth** | CI check: every publish subject is registered; Pydantic models generated from schemas | Wire contract drift between services |

**These four lints are the highest return-on-effort work in the entire implementation.** Half a day each, and each prevents a class of debt that is otherwise permanent.

---

## 4. Debt the architecture actively prevents

Worth recording, because it is what the current design already gets right and what must not be lost during implementation.

| Debt avoided | By |
|---|---|
| A monolithic god-service | Layer decomposition, now sharpened into bounded contexts |
| LLM-computed indicators | The deterministic/AI boundary (page 09's governing rule) |
| Untracked models trained on a laptop | MLflow registry with a promotion gate (page 07) |
| Silent overfitting | PBO/DSR as a hard gate, including for self-generated changes (pages 07, 12) |
| Broker lock-in | The adapter interface from day one, despite one broker (page 11) |
| Silent data corruption | Quality scoring with quarantine rather than silent drops (page 02) |
| Async kill switch with a propagation window | Page 10's synchronous in-process gate |
| Mutable raw data | Page 01's never-mutate rule |
| A learning loop that bypasses validation | Page 12's no-shortcut rule |

Nine avoided debts is a strong result for a pre-code document, and it is the reason this review is an overlay rather than a rewrite.

---

## 5. Debt that will be created during implementation

Predictable pressures, with pre-agreed responses. Writing these down now is what makes it possible to say no later.

| Pressure | Likely shortcut | Pre-agreed response |
|---|---|---|
| First vertical slice is slow | Skip the outbox, publish directly | **No.** It is 30 lines and retrofitting touches every write path |
| Tests are slow | Skip the determinism test in CI | **No.** It is the only proof that backtests are reproducible |
| A limit needs changing urgently during a drawdown | Bypass dual control | **No.** This is precisely the scenario the control exists for (R15 §7) |
| The Committee is expensive | Reduce the desk count permanently | Acceptable **only** as a load-shedding response, never as a permanent config change without a shadow comparison |
| Reconciliation is noisy early on | Raise the tolerance until it stops alerting | **No.** Fix the cause. A silenced reconciliation is no reconciliation |
| The Instrument Master feels like overhead for one symbol | Hardcode the specs | **No.** This is the dependency that makes sizing correct, and hardcoded specs are how a broker spec change silently doubles position size |
| Paper trading feels like a delay | Go from shadow straight to prod | **No.** Paper is the only environment that exercises the real order path without capital (R14 §8) |
| The prompt registry feels like ceremony | Edit prompts in place | **No.** This contaminates every subsequent backtest, invisibly and permanently |

The last one is the most likely to happen and the most damaging, because editing a prompt file feels like editing code rather than like changing a model.

---

## 6. Debt review cadence

| Cadence | Activity |
|---|---|
| Per PR | Do the four lints pass? Does any new failure mode have a metric? Does any new event have a registered schema? |
| Weekly (with the learning review) | Any new entries in the register? Any accepted-debt tripwire met? |
| Quarterly | Walk every ADR tripwire. Walk the accepted-debt table. Review alerts that fired and were not actionable, and delete them |
| Annually | Re-score the six dimensions in R00 §6. The scores are the measure of whether the platform is maturing or accumulating |

The annual re-score is the one that matters over a ten-year horizon: it converts "are we getting better" from a feeling into a number with a history.

---

## 7. Related

- `R00_Executive_Review.md` (§7 roadmap; the P0 items map to D1 through D8)
- `R16_ADR_Register.md` (accepted debt maps to ADRs with tripwires)
- `R14_Deployment.md` (§4 CI gates that enforce the four disciplines)
