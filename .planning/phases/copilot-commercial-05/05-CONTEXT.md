# Copilot Commercial Phase 5 — Context

**Phase:** copilot-commercial-05  
**Source:** `.planning/COPILOT-COMMERCIAL-ROADMAP.md` Phase 5

## Boundary

PM questions should not require pasting opaque tickers for **read** workflows: list/top edges, regime explanation, correlation vs sportsbook exposure. **Writes / order placement** stay **out of copilot** until explicit product HITL exists — tools return “use in-app execution” messaging only.

## Decisions

- Reuse **`sharpedge_analytics`** (`scan_pm_edges`, `classify_pm_regime`, `detect_correlated_positions` / `compute_entity_correlation`) with **hard row caps** (e.g. ≤10 edges, ≤5 warnings).
- Reuse feed clients patterns from existing **`get_prediction_market_edge`** (`Kalshi` / `Polymarket` async) — consider shared `pm_feed_helpers` in agent_pipeline to avoid duplication.
- **No** `place_pm_order` tool in this phase.

## Canonical refs

- `packages/analytics/src/sharpedge_analytics/pm_edge_scanner.py`
- `packages/analytics/src/sharpedge_analytics/pm_regime.py`
- `packages/analytics/src/sharpedge_analytics/pm_correlation.py`
- `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py` (`get_prediction_market_edge`)
