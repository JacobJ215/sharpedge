---
phase: 03-prediction-market-intelligence
plan: "03"
subsystem: analytics
tags: [pm-correlation, value-scanner, copilot-tools, pm-04]
dependency_graph:
  requires:
    - 03-01  # pm_edge_scanner.py base
    - 03-02  # pm_regime.py + scan_pm_edges implementation
  provides:
    - pm_correlation.py (PM-04 token-based correlation detection)
    - value_scanner_job.py PM scan section (PM edges in unified alert queue)
    - tools.py get_prediction_market_edge real implementation (replaces stub)
  affects:
    - apps/bot/src/sharpedge_bot/jobs/value_scanner_job.py
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py
    - packages/analytics/src/sharpedge_analytics/pm_edge_scanner.py
tech_stack:
  added: []
  patterns:
    - Token-overlap entity correlation (min-denominator formula, no NLP library)
    - CorrelationWarning dataclass inserted into mixed scan result list
    - lazy import pattern for async clients inside sync copilot tool
key_files:
  created:
    - packages/analytics/src/sharpedge_analytics/pm_correlation.py
  modified:
    - apps/bot/src/sharpedge_bot/jobs/value_scanner_job.py
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py
    - packages/analytics/src/sharpedge_analytics/pm_edge_scanner.py
decisions:
  - "compute_entity_correlation uses min-denominator (not max) so single shared entity in short title yields > 0.5"
  - "DEFAULT_STOPWORDS includes 'title', 'championship', 'game', 'series' to avoid false positives in PM context"
  - "CorrelationWarning dataclass added to pm_edge_scanner (not a separate module) to keep the mixed-list contract in one place"
  - "PM scan placed BEFORE the sports early-return so PM edges queue even when no sports value plays exist"
  - "get_prediction_market_edge uses ThreadPoolExecutor fallback when event loop is already running"
metrics:
  duration_minutes: 15
  completed_date: "2026-03-14"
  tasks_completed: 2
  files_created: 1
  files_modified: 3
---

# Phase 3 Plan 03: PM Correlation + End-to-End PM Intelligence Summary

**One-liner:** Token-based portfolio correlation (PM-04) wired into value_scanner_job and copilot tool, making PM intelligence end-to-end live with CorrelationWarning alerts before correlated PM edges.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement pm_correlation.py | f25b978 | packages/analytics/src/sharpedge_analytics/pm_correlation.py (created) |
| 2 | Wire PM scanning + update copilot tool | 3857d1a | value_scanner_job.py, tools.py, pm_edge_scanner.py |

## Decisions Made

1. **min-denominator formula** — `compute_entity_correlation` divides by `min(|tokens_a|, |tokens_b|)` instead of `max`. This ensures a single shared entity in a short title yields > 0.5, matching test expectations for partial-match cases like "Lakers vs Celtics" vs "Celtics win title".

2. **Extended DEFAULT_STOPWORDS** — Added "title", "championship", "game", "series" to prevent common PM/sports vocabulary from driving false positive correlations.

3. **CorrelationWarning in pm_edge_scanner** — The `CorrelationWarning` dataclass lives in `pm_edge_scanner.py` alongside `PMEdge`. When `active_bets` is passed to `scan_pm_edges`, correlation warnings are inserted before their correlated edge in the returned list (mixed `list[PMEdge | CorrelationWarning]`). This satisfies the `test_correlation_warning_order` RED stub.

4. **PM scan before early-return** — The PM scan block runs before the `if not all_value_plays: return` check so PM edges are always queued even on quiet sports nights.

5. **Lazy client imports in tools.py** — `get_kalshi_client` and `get_polymarket_client` are imported inside the async inner function to avoid module-load-time overhead and to prevent circular imports.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_correlation_warning_order was already a RED stub in test_pm_edge_scanner.py**
- **Found during:** Task 2 (running analytics tests after Task 1)
- **Issue:** The test expected `scan_pm_edges` itself to return `CorrelationWarning` objects when `active_bets` is passed — the plan had the correlation logic only in `value_scanner_job.py`. These are contradictory.
- **Fix:** Added `CorrelationWarning` dataclass to `pm_edge_scanner.py` and implemented correlation insertion inside `scan_pm_edges` when `active_bets` is non-empty. The `value_scanner_job.py` PM scan also calls `detect_correlated_positions` independently for its own warning queue.
- **Files modified:** packages/analytics/src/sharpedge_analytics/pm_edge_scanner.py
- **Commit:** 3857d1a

**2. [Rule 3 - Blocking] scan_pm_edges signature uses separate kalshi_markets/polymarket_markets (not platform flag)**
- **Found during:** Task 2 planning
- **Issue:** Plan's interface spec showed `scan_pm_edges(markets=..., platform="kalshi")` but the actual implementation uses `scan_pm_edges(kalshi_markets=..., polymarket_markets=...)`.
- **Fix:** Used actual signature throughout value_scanner_job.py and tools.py.
- **Commit:** 3857d1a

## Test Results

```
76 passed, 2 warnings
```

All Phase 3 test files GREEN:
- tests/unit/analytics/test_pm_correlation.py — 6 passed
- tests/unit/analytics/test_pm_edge_scanner.py — 5 passed (including test_correlation_warning_order)
- tests/unit/analytics/test_pm_regime.py — 11 passed
- Full suite: 76 passed, no failures

## Self-Check: PASSED

- [x] packages/analytics/src/sharpedge_analytics/pm_correlation.py exists
- [x] apps/bot/src/sharpedge_bot/jobs/value_scanner_job.py contains scan_pm_edges (line 22, 136)
- [x] packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py contains scan_pm_edges (real impl, line 291)
- [x] Commit f25b978 exists (Task 1)
- [x] Commit 3857d1a exists (Task 2)
- [x] value_scanner_job.py: 362 lines (under 450 limit)
- [x] tools.py: 446 lines (under 500 limit)
- [x] pm_correlation.py: 89 lines (under 120 limit)
