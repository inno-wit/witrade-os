# Event Blueprint

**Blueprint deliverable:** B.5
**Canonical source for the 85 event subjects themselves (publisher, consumers, stream, ordering key, idempotency identity):** `../Architecture/generated/15_Event_Catalog_v2.md` §4 — **not restated here.** This document adds the layer between that catalog and running code: producer/consumer interface shape, replay mechanics, and monitoring hooks per stream tier.
**Status:** Blueprint v1.0, 2026-08-04

---

## 1. What already exists and is not repeated

`../Architecture/generated/15_Event_Catalog_v2.md` already specifies, per subject: publisher, consumers, stream assignment, ordering key, idempotency identity, and (§6) retention/replicas/discard policy per stream, plus the full ack/retry/backoff/DLQ policy (§6, `ack_wait`, `max_deliver=5`, backoff ladder, `dlq.<subject>` routing). `../Architecture/freeze/Event_Governance_Matrix.md` independently verified these 85 subjects have one owner, one schema, one version, one lifecycle, one publisher (with one sanctioned exception). **None of this is repeated below.**

---

## 2. Producer interface, one shape for every service

```python
# packages/schemas provides the envelope + payload types.
# Every service's adapters/event_bus.py implements exactly this shape — no service
# hand-rolls its own publish call.

class EventPublisher(Protocol):
    async def publish(
        self,
        subject: str,                    # e.g. "evt.portfolio_construction.candidate.admitted.v1"
        payload: BaseModel,              # a packages/schemas type, never a raw dict
        *,
        correlation_id: str,             # propagated from the triggering command/event
        causation_id: str,               # the specific message that caused this one
        idempotency_key: str,            # per generated/15's stated identity for this subject
    ) -> None: ...
```

**The transactional outbox (ADR-0038) is not optional and is not a service-level choice.** Every service that writes state and publishes an event does so via `packages/kernel`'s `Outbox` helper: the domain write and the outbox row commit in one Postgres transaction; a separate relay process (one per service, or one shared relay reading every service's outbox table — implementation detail, not an architecture decision) publishes from the outbox to NATS and marks rows sent. This is what makes `outbox_unpublished_age_seconds` (the tripwire metric named in `../Architecture/decisions/README.md`) a real, measurable thing rather than an aspiration.

## 3. Consumer interface, one shape for every service

```python
class EventConsumer(Protocol):
    subject_pattern: str                 # e.g. "evt.risk.*.v1"
    durable_name: str                    # per-service durable consumer name, stable across restarts

    async def handle(self, envelope: EventEnvelope, payload: BaseModel) -> None:
        """Must be idempotent on `envelope.idempotency_key` — the framework
        deduplicates before calling handle(), but handle() must still be safe
        to call twice if the dedup store itself is ever rebuilt."""
        ...
```

**`max_deliver=5` with the stated backoff ladder is enforced by the NATS JetStream consumer config, not by application retry loops.** A service's `handle()` either succeeds, raises (triggering the platform-level redelivery), or explicitly nacks — it never implements its own retry-with-sleep, which would fight the platform's own backoff policy.

## 4. Replay mechanics

Building directly on `../Architecture/review/R19_Missing_Components.md` §2 (the Simulation & Replay Harness, C28):

| Replay mode | Mechanism | Guarantee |
|---|---|---|
| **Backtest** | `replay_run_id` set on every message; `env=sim`; Clock (C05) driven by the harness, not wall time | Byte-identical output for the same seed, checked in CI (`Testing_Blueprint.md` §3) |
| **Counterfactual** | Same as backtest, but one input (a model version, a prompt version) swapped via `Resolve(..., as_of)` pinned to a different artefact | Every other input identical — isolates the one variable |
| **What-if** | Current live state, hypothetical proposal injected into BC12/BC6 in `PREVIEW` mode (never `DECIDE`) | Zero production side effects — `env` mismatch is a hard failure if a preview message ever reaches a production consumer |

**A cache miss on an LLM call during replay is a hard error, never a live call** (R19 §2's own non-negotiable property) — implemented as: the LLM Gateway (C17) refuses to make a live API call when `env=sim`, full stop, no fallback.

## 5. Monitoring hooks, per stream tier

| Stream | Alert trigger | Severity |
|---|---|---|
| `CONTROL` (commands) | Any message reaching `dlq.cmd.*` | **P0, pages immediately** — a command failing 5 redeliveries means an order-path or kill-switch action did not land |
| `TRADING` | DLQ landing | P0, pages immediately |
| `DECISION` | DLQ landing | P0, pages immediately |
| `MARKET`, `OPS` | DLQ landing | P2, ticket, not a page |
| Every stream | `outbox_unpublished_age_seconds` p99 > 5s | P1 (per `../Architecture/decisions/README.md`'s own tripwire threshold) |
| Every stream | Consumer lag exceeding 2x the subject's own latency budget | P1 |

## 6. What Phase 11's new subjects (§4.8b) need that pre-existing ones don't

The five `portfolio_construction.*` subjects are new as of this session (`../Architecture/generated/15_Event_Catalog_v2.md` §4.8b). Nothing about their implementation differs from any other `DECISION`-stream subject — no special-casing required. Recorded here only to confirm that check was explicitly run, not assumed.

---

## 7. Related

- `../Architecture/generated/15_Event_Catalog_v2.md` — the canonical 85-subject catalog this blueprint implements
- `../Architecture/freeze/Event_Governance_Matrix.md` — the governance verification this blueprint builds on
- `Schema_Blueprint.md` — the `BaseModel` payload types referenced in §2-3
- `../Architecture/decisions/0038-transactional-outbox-is-mandatory.md` — §2's outbox requirement
- `Testing_Blueprint.md` §3 — where replay determinism becomes a CI-enforced test, not just a design property
