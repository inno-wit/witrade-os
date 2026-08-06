# 15 — Event Catalog

**Diagram:** `15_Event_Catalog.excalidraw`
**Type:** Cross-cutting reference (not a phase page)
**Depends on:** All of pages 00-14 — this catalog is compiled from their individual "Events Published / Events Consumed" sections
**Status:** Draft — will need a rebuild pass once pages 01-14 exist for real code and event names get validated against actual implementation

---

## Purpose

Every component page in this ADD lists its own Events Published and Events Consumed. This page is the single rolled-up table — it's what makes the Event Bus in page 00 actually implementable: a NATS subject naming scheme, one row per event, every publisher and every consumer in one place so nobody has to cross-reference fourteen pages to answer "who listens to `risk.rejected`?"

## Naming Convention

`{layer}.{entity}.{action}` — lowercase, dot-namespaced, matching NATS subject hierarchy conventions (`risk.>` subscribes to every Risk Management event).

## Full Catalog

| Event | Publisher | Consumer(s) | Payload (summary) |
|---|---|---|---|
| `job.scheduled` | Orchestration Scheduler (00) | Data Ingestion (01), any scheduled job | `{ job_id, trigger_type }` |
| `workflow.started` / `.failed` / `.completed` | Workflow Engine (00) | Monitoring (13) | `{ workflow_id, dag_step }` |
| `data.tick.received` | Data Ingestion (01) — MT5 only | Internal (price-updater pattern), not broadcast | `{ symbol, price, timestamp }` |
| `data.bar.received` | Data Ingestion (01), all sources | Data Quality Engine (02) | `{ source, symbol, timeframe, ohlcv }` |
| `data.source.degraded` | Data Ingestion (01) circuit breaker | Monitoring (13) | `{ source, reason }` |
| `data.quality.scored` | Data Quality Engine (02) | Feature Store (03) | `{ dataset_id, score, detector_breakdown }` |
| `data.quality.rejected` | Data Quality Engine (02) | Monitoring (13), quarantine table | `{ dataset_id, reason }` |
| `feature.updated` | Feature Store (03) | Regime (04), Volatility (05), Structure (06), ML/RL (07) | `{ symbol, timeframe, category, as_of }` |
| `feature.backfilled` | Feature Store (03) | Quant Research engines (04-07), on historical recompute | `{ symbol, category, version, range }` |
| `regime.updated` | Regime Engine (04) | Feature Store (03, writeback), AI Committee Regime Desk (08), Volatility Engine (05) | `{ symbol, state, probabilities, confidence }` |
| `regime.shift.detected` | Regime Engine (04) | AI Committee (08), Data Quality Engine (02, threshold tuning) | `{ symbol, from_state, to_state }` |
| `volatility.updated` | Volatility Engine (05) | Feature Store (03), AI Committee Volatility Desk (08), Risk Management (10) | `{ symbol, atr, forecast, realized, percentile, tail_risk }` |
| `volatility.regime_shift` | Volatility Engine (05) | AI Committee (08) | `{ symbol, recalibration_reason }` |
| `structure.updated` | Structure/SMC Engine (06) | Feature Store (03), AI Committee SMC Desk (08) | `{ symbol, timeframe, bos, choch, obs, fvgs, confidence }` |
| `structure.confluence.detected` | Structure Engine (06) | AI Committee (08) — this is a primary trigger for a committee cycle | `{ symbol, timeframe, confluence_count }` |
| `model.trained` | ML/RL Model Layer (07) | MLflow Registry, Continuous Learning (12) | `{ model_id, metrics }` |
| `model.promoted` | ML/RL Model Layer (07) | Model consumers (08) | `{ model_id, version, slot }` |
| `model.prediction` | ML/RL Model Layer (07) | AI Committee desks (08, as context) | `{ model_id, prediction, confidence }` |
| `committee.convened` | AI Investment Committee (08) | Monitoring (13), Explainability (09) | `{ symbol, trigger_reason }` |
| `committee.desk.completed` | AI Investment Committee (08) | Consensus Engine (internal to 08) | `{ desk, stance, confidence }` |
| `committee.recommendation` | AI Investment Committee (08) | Decision Intelligence (09) | `{ direction, size_hint, confidence, reasoning_trace }` |
| `committee.deadlock` | Conflict Resolver (08) | Monitoring (13), Continuous Learning (12, desk-calibration signal) | `{ symbol, conflicting_desks }` |
| `evidence.graph.built` | Decision Intelligence (09) | Explainability, audit/replay tooling | `{ decision_id, node_count }` |
| `decision.made` | Decision Intelligence (09) | Risk Management (10) | `{ decision_id, verdict, lineage_ref }` |
| `decision.explained` | Decision Intelligence (09) | Dashboard (Users, 00), Journal (11) | `{ decision_id, explanation_text }` |
| `risk.approved` | Risk Management (10) | Execution Engine (11) | `{ decision_id, approved_size, sl, tp }` |
| `risk.rejected` | Risk Management (10) | Monitoring (13), Continuous Learning (12) | `{ decision_id, stage, reason }` |
| `risk.killswitch.triggered` | Risk Management (10) | Monitoring (13) — highest-priority page alert | `{ reason, triggered_by }` |
| `risk.killswitch.cleared` | Risk Management (10) | Monitoring (13) | `{ cleared_by, timestamp }` |
| `order.sent` | Execution Engine (11) | Monitoring (13) | `{ order_id, symbol, size }` |
| `order.filled` | Execution Engine (11) | Risk Management (10, portfolio state update), Journal (11), Continuous Learning (12) | `{ order_id, fill_price, fill_size }` |
| `order.rejected` | Execution Engine (11) — broker-side rejection | Monitoring (13), Risk Management (10) | `{ order_id, broker_reason }` |
| `execution.slippage.recorded` | Execution Engine (11) | Risk Management Kill Switch (10), RL simulator calibration (07) | `{ order_id, expected_price, actual_price, slippage_bps }` |
| `alert.triggered` | Monitoring (13, cross-cutting) | Operator dashboard/paging | `{ severity, source_event, message }` |
| `learning.review.completed` | Continuous Learning (12) | Monitoring (13) | `{ review_id, period }` |
| `learning.hypothesis.generated` | Continuous Learning (12) | Experiment Queue (internal to 12) | `{ hypothesis_id, evidence }` |
| `learning.change.validated` | Continuous Learning (12) | Deployment pipeline (14, promotion trigger) | `{ change_id, target: model\|desk_weight, pbo_result }` |
| `deploy.started` / `.promoted` / `.rolled_back` | Deployment Pipeline (14) | Monitoring (13) | `{ deploy_id, environment, artifact }` |
| `shadow.run.completed` | Deployment Pipeline (14) | Deployment gate (14), Continuous Learning (12) | `{ shadow_id, comparison_result }` |

## Inputs

The individual "Events Published" / "Events Consumed" sections of pages 00-14 — this table has no independent source of truth beyond those pages; if they diverge, the component page wins and this catalog needs a sync pass.

## Outputs

A single lookup reference used by: NATS subject configuration (Infrastructure, page 13), Monitoring's subscription list (page 13), and any new component being designed (check this table before inventing a new event name that might already exist in a different namespace).

## Dependencies

Every page 00-14.

## Failure Modes

- **Drift** — a page's code implementation changes an event's payload or name without this catalog being updated, and the catalog silently becomes wrong documentation (worse than no documentation).
- **Orphan events** — an event is published but nothing actually consumes it (dead weight) or an event is expected to be consumed but nothing publishes it (silent gap).

## Recovery Strategy

- This catalog should be regenerated or diffed against actual NATS subject usage once real code exists — treat the table above as the **design-time contract**, not a guarantee of current implementation state. Flagged explicitly in the Status field above.
- A future CI check (page 14) could statically verify every subscribed subject in code has a corresponding publisher, catching orphan events before they ship — noted as Future Expansion, not yet built.

## Future Expansion

- Auto-generate this table from code annotations (e.g., a decorator on publisher/consumer functions) once the codebase exists, rather than hand-maintaining it — hand-maintained catalogs rot.
- Add payload JSON Schema definitions per event (currently summarized in prose) once each page's exact data contracts are finalized.

---

## Related

- Previous: `14_Deployment_Pipeline.md`
- Next: `16_C4_Container_Diagram.md`
