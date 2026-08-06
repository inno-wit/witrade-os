# ADR-0001: Python as the primary implementation language

**Status:** Accepted
**Date:** 2026-08-03
**Decided:** 2026-08-03 by Fredrick Kimeu
**Deciders:** Fredrick Kimeu
**Tags:** foundational, stack

---

## Context

The ADD assumes Python throughout without stating it as a decision. Every component (ingestion, quantitative engines, committee, risk, execution, learning) is described in terms of a Python ecosystem, and page 13 selects FastAPI, DuckDB, MLflow and the MT5 Python bridge, all of which presuppose it.

The choice is worth recording for one reason: **it is the decision most likely to be second-guessed on performance grounds by someone who has not measured anything.** A trading platform written in Python attracts the observation that "real trading systems are written in C++," and that observation is correct for a class of system this is not.

The relevant facts about this platform:

- The target timeframe is 15 minutes. The decision cycle has an end-to-end budget of roughly 11 seconds, of which the LLM committee accounts for the overwhelming majority.
- The order path budget is measured in hundreds of milliseconds, dominated by an RPC to the broker.
- The instrument universe is one to five symbols.
- There is one operator, who is fluent in Python and not in C++.
- The quantitative stack (HMM, GARCH, scikit-learn, pandas, PyTorch) is Python-native. So is the Anthropic SDK.

## Options considered

**A. Python throughout.**
*Pros:* one language; the entire quant, ML and LLM ecosystem is native; the operator is fluent; fastest iteration, which is the dominant constraint on a solo project; FastAPI/Pydantic give typed contracts and OpenAPI for free.
*Cons:* GIL constrains CPU-bound concurrency; latency floor is milliseconds not microseconds; runtime type errors unless discipline is enforced; packaging and dependency management require care.

**B. Rust or C++ for the hot path, Python for research.**
*Pros:* microsecond latency; no GIL; compile-time guarantees on the capital path.
*Cons:* two languages, two build systems, two test suites, two deployment stories, for one person; a serialisation boundary between them that becomes a source of bugs; the latency gained is invisible at a 15-minute timeframe; the operator would be writing the safety-critical path in their weaker language, which is a net safety loss.

**C. Go for services, Python for research.**
*Pros:* good concurrency, simple deployment, decent ecosystem.
*Cons:* same two-language cost as B, with a much weaker quant ecosystem, and no latency benefit that this platform can use.

## Decision

**Option A.** Python 3.12+ throughout, with the following non-negotiable disciplines, because the cons of Option A are all mitigable and all become expensive if mitigated late:

1. **Strict typing.** `mypy --strict` (or `pyright` strict) in CI, on every package. No `Any` on a domain type, no untyped public function.
2. **Pydantic v2** for every boundary type: wire messages, API request/response, config. Domain value objects are frozen dataclasses.
3. **`Decimal` for money, quantity and price. Never `float`.** A float rounding error in position sizing is a real loss, and it is silent.
4. **Async by default** for I/O, `asyncio` throughout. CPU-bound work (model fitting, backtests) runs in a separate process pool, never on the event loop.
5. **Locked, hashed dependencies** (`uv` or `poetry` with a lockfile and hashes). Pinned image digests, not tags (R13 §8).
6. **One escape hatch is pre-approved:** a numerically hot inner loop may be Numba, Cython or a Rust extension **behind a Python interface**, decided case by case with a measurement attached. This is not a language change; it is an optimisation with a benchmark.

## Rationale

The binding constraint on this platform is not latency, it is **whether it gets built and whether it is correct.** One operator, one language, and the strongest quant and LLM ecosystem in existence is the configuration that maximises both.

The latency argument does not apply at this timeframe. A 15-minute bar strategy whose decision cycle already spends eight seconds waiting for six LLM calls does not benefit from shaving microseconds off an indicator calculation. The order path is dominated by a network round trip to the broker, which is identical in every language.

The GIL objection is real but misdirected: the platform's concurrency is I/O-bound (network, disk, broker, LLM), which is exactly what `asyncio` handles well. The genuinely CPU-bound work (fitting a GARCH model, running a backtest) is batch work that runs in its own process and is not on any latency budget.

The disciplines in points 1 through 3 are what make this decision defensible rather than merely convenient. Untyped Python at this scale becomes unmaintainable, and floats in financial arithmetic are a category of bug that no test suite reliably catches. Both are cheap to enforce from commit one and expensive to retrofit.

## Consequences

**Positive**
- One language, one toolchain, one test suite, one deployment story.
- The quant, ML and LLM ecosystems are native, with no FFI boundary.
- Iteration speed, which is the dominant constraint on a solo project.
- FastAPI gives typed HTTP with OpenAPI generation at no cost.

**Negative**
- The latency floor is milliseconds. Recorded, accepted, and tripwired below.
- Strict typing must be enforced from the start; retrofitting `mypy --strict` onto an existing codebase is a multi-week project nobody does.
- Dependency supply chain requires active management (R15).

**Neutral**
- The MT5 bridge must run on Windows regardless of language (R13 §7). This constraint is not Python's.

## Tripwire

Revisit if **either** becomes true:

1. **The target timeframe drops below 1 minute.** Sub-minute strategies change the latency calculus materially.
2. **p99 on the order path exceeds 50% of its budget** and profiling attributes the excess to Python execution rather than to network or broker time.

The response to either is Option B applied narrowly: a compiled hot path behind the existing `BrokerAdapter` and `RiskRule` interfaces, not a rewrite. The interfaces in R02 §5 are what make that possible, which is a further reason to freeze them now.

## Related

- ADR-0014 (shared kernel) covers the typed primitives named here
- ADR-0008 (Docker Compose) shares the "right size for one operator" reasoning
- `../review/R13_Infrastructure.md` §1
- `../review/R17_Performance.md`
- `../review/R00_Executive_Review.md` (P3 tripwires)
- Source: `../13_Infrastructure_Platform.md`
