# API Blueprint

**Blueprint deliverable:** B.4
**Grounded in:** `../Architecture/generated/15_Event_Catalog_v2.md` §7 ("What is deliberately not an event" — the platform's real synchronous-call surface), `../Architecture/19_Bounded_Context_Map.md`'s Interfaces columns, `../Architecture/21_Security_Architecture.md` §3 (RBAC)
**Status:** Blueprint v1.0, 2026-08-04
**Amended:** 2026-08-06 — `CheckKillSwitch` row corrected per [ADR-0044](../Architecture/decisions/0044-kill-switch-recheck-at-broker-send.md). It previously read "in-process within C21, not cross-service," which an independent review found was being taken to mean the check exists only in C21 — foreclosing the C24 recheck this ADR adds. Both calls remain local, in-process method calls; there are now two of them, in two different processes.

---

## 1. Three API surfaces, not one

This platform is event-driven internally by design (ADR-0004, ADR-0037). REST/gRPC exists only where the architecture already specifies a synchronous call. Inventing a generic CRUD API surface on top of an event-sourced, event-driven platform would contradict the architecture rather than implement it. Three real surfaces:

1. **Internal synchronous queries** — the handful of calls the architecture itself names as sync (read models with a timeout), gRPC between services.
2. **Operator/Admin API** — privileged actions a human takes (kill switch, limit changes, model promotion), REST via the API Gateway (C32), OIDC + MFA (BC11).
3. **Health/Metrics/Config APIs** — one uniform pattern per service, already specified in `Service_Catalog.md` §1.

---

## 2. Internal synchronous queries (gRPC, service-to-service)

The complete list — nothing else in this platform is a synchronous call, by design (ADR-0037: everything else is a command or an event).

| Call | From → To | Timeout | On timeout | Source |
|---|---|---|---|---|
| `GetPortfolioSnapshot` | BC5, BC12 → BC7 (Ledger, C22) | Async read model (cached, not a live call) | Serve last-known, marked stale | `../Architecture/19_Bounded_Context_Map.md` |
| `GetPortfolioSnapshot` (sync) | BC6 (Risk) → BC7 (Ledger, C22) | **30ms** | Reject the trade, fail closed | `../Architecture/generated/15` §7 |
| `GetBudgetSnapshot` | BC12 (C40) → BC6 (Risk, C21) | **30ms** (same pattern) | Admit nothing that cycle, fail closed | `../Architecture/18_Portfolio_Construction.md` |
| `CheckKillSwitch` | In-process within C21 (at token mint) **and** in-process within C24 (immediately before broker send, `ENTRY` intent only) — two independent local calls, not cross-service | 10ms | HALT, fail closed | `../Architecture/generated/15` §7, ADR-0018, ADR-0044 |
| `Resolve` (artefact) | BC4, BC5, BC12 → Model Registry (C12-14, C18) | 10ms p99 | Serve last-resolved, marked stale | `../Architecture/20_Model_Registry.md` |
| `GetSpec` / `IsTradable` | Any → Instrument Master (C04) | 10ms p99, cached | Fail closed (no trade without a valid spec) | `review/R19` §4 |
| `Authorize` | Any privileged action → Identity (C39) | 15ms p99 | Fail closed, no override possible | `../Architecture/21_Security_Architecture.md` §3 |

**Protocol: gRPC, not REST, for all seven.** Internal, low-latency, typed (protobuf generated from `packages/schemas`), no need for browser-callable semantics. A REST internal API would add a serialisation cost these budgets (as low as 10ms) cannot spare.

**Every call above is fail-closed on timeout, no exception.** This is not a per-call decision, it is ADR-0025 (fail-closed is the universal default) applied literally at the API layer.

---

## 3. Operator / Admin API (REST, via API Gateway C32)

The privileged operations named in `../Architecture/21_Security_Architecture.md` §3, each a real endpoint.

| Path | Method | Auth | Confirmation | Rate limit |
|---|---|---|---|---|
| `/admin/kill-switch/trip` | `POST` | Any authenticated identity, no MFA required (asymmetric friction — stopping is easy) | None | None (must never be rate-limited) |
| `/admin/kill-switch/clear` | `POST` | `operator` + MFA, **dual control** | Typed confirmation, second approver | 1/hour |
| `/admin/limits` | `POST` (new version) | `operator` + MFA, dual control | Mandatory dry-run report attached, cooling period before effective | 1/day |
| `/admin/models/{slot}/promote` | `POST` | `operator` + MFA (+ Risk sign-off if Tier 0, ADR-0042) | Typed confirmation | 10/day |
| `/admin/models/{slot}/rollback` | `POST` | `operator` + MFA | **No confirmation required** (asymmetric friction) | None |
| `/admin/reconciliation/force-release` | `POST` | `operator` + MFA, dual control | Typed confirmation, logged loudly | 1/day |
| `/admin/mode` | `GET` | `auditor` or higher | — | Standard |
| `/admin/mode` | `PUT` (set mode) | `operator` + MFA | Typed confirmation | 5/hour |

**Every mutating call is idempotency-keyed** (a double-submitted "halt" is one halt — `../Architecture/review/R15_Security.md` §9) and **audited before it is forwarded**, not after, so a call that crashes mid-execution is still on the record.

### Response shape, uniform

```json
{
  "status": "accepted | rejected | error",
  "reason": "string, present on rejected/error",
  "correlation_id": "ULID, always present",
  "audit_id": "ULID, present once the action is recorded"
}
```

### Error taxonomy

| HTTP status | Meaning |
|---|---|
| `400` | Malformed request — reject, never coerce (`../Architecture/review/R15_Security.md` §9) |
| `401` / `403` | Not authenticated / not authorised for this specific action |
| `409` | Idempotency key conflict — the same action was already accepted |
| `423` | Locked — a dual-control action awaiting the second approver |
| `503` | A dependency this endpoint fails closed on is unreachable (never `200` with a degraded body for a privileged action) |

---

## 4. Read-only APIs (dashboard-facing, via C32)

| Path | Purpose | Role required |
|---|---|---|
| `/api/decisions/{id}` | Render a decision card / full trace (`../Architecture/17_Evidence_Graph.md` §"Explainability") | `auditor` sees full trace; `viewer` sees one-line/decision-card only |
| `/api/portfolio/plan` | Current `PortfolioAllocationPlan` (`../Architecture/18_Portfolio_Construction.md`) | `viewer`+ |
| `/api/risk/dashboard` | Live exposure, drawdown, headroom (`review/R11` §12) | `viewer`+ |
| `/api/models/{slot}` | Current SM-5 state, shadow comparison (`../Architecture/20_Model_Registry.md`) | `viewer`+ |

**Output filtering by role is enforced at this layer**, not left to the client — `../Architecture/review/R15_Security.md` §9's rule ("an `auditor` sees decisions, not credentials or vendor keys") is a server-side filter, never a client-side hide.

---

## 5. Versioning

REST: URL path version (`/v1/admin/...`), bumped on any breaking response-shape change, old version kept live for one deprecation cycle. gRPC: protobuf field addition only (never remove/renumber a field), matching the schema registry's own `.v1`/`.v2` discipline (`Schema_Blueprint.md`).

---

## 6. Related

- `Schema_Blueprint.md` — the DTOs referenced throughout this document
- `Interface_Definitions.md` — the Python-level interface signatures behind each internal query in §2
- `../Architecture/21_Security_Architecture.md` §3 — the RBAC model every endpoint in §3-4 enforces
- `../Architecture/generated/15_Event_Catalog_v2.md` §7 — the canonical source for §2's sync-call list
