---
phase: 03-prediction-market-intelligence
plan: 02
subsystem: analytics
tags: [prediction-markets, kalshi, polymarket, regime-classifier, edge-scanner, alpha-scoring]

requires:
  - phase: 03-01
    provides: pm_regime.py and pm_edge_scanner.py RED stubs; sub-package split of prediction_markets.py
  - phase: 01-quant-engine
    provides: compose_alpha() from sharpedge_models.alpha used for alpha scoring

provides:
  - pm_regime.py — PMRegimeState enum, PMRegimeClassification dataclass, PM_REGIME_THRESHOLDS, PM_REGIME_SCALE, classify_pm_regime()
  - pm_edge_scanner.py — PMEdge dataclass, scan_pm_edges() for Kalshi and Polymarket with volume floor and alpha scoring

affects:
  - 03-03 (PM-04 cross-market correlation builds on PMEdge and scan_pm_edges)
  - value_scanner_job (rank_by_alpha uses getattr(play, 'alpha_score') compatible with PMEdge)

tech-stack:
  added: []
  patterns:
    - "Priority-ordered rule-based regime classification (first match wins) — mirrors sports regime.py"
    - "Fee-adjusted fallback model probability when no external model exists (KALSHI_FEE_RATE=3%)"
    - "Volume USD normalization: Kalshi contracts * mid_price before applying liquidity floor"

key-files:
  created:
    - packages/analytics/src/sharpedge_analytics/pm_regime.py
    - packages/analytics/src/sharpedge_analytics/pm_edge_scanner.py
  modified: []

key-decisions:
  - "classify_pm_regime() uses price_variance parameter name (not price_variance_7d) to match test contract"
  - "scan_pm_edges() accepts active_bets and market_titles kwargs but ignores them — correlation logic deferred to Plan 03"
  - "Fee-adjusted fallback model_prob: market_prob / (1 - 0.03) capped at 1.0 — avoids division errors on high-prob markets"
  - "Kalshi volume floor: contracts * mid_price for USD equivalent (100 contracts * 0.51 = 51 USD, correctly filtered)"

patterns-established:
  - "PMEdge.alpha_score maps from BettingAlpha.alpha; PMEdge.alpha_badge maps from BettingAlpha.quality_badge"
  - "Deferred params accepted as keyword args with None defaults to keep interface forward-compatible"

requirements-completed: [PM-01, PM-02, PM-03]

duration: 10min
completed: 2026-03-14
---

# Phase 3 Plan 02: PM Regime Classifier and Edge Scanner Summary

**5-state PM regime classifier (pm_regime.py) and dual-platform edge scanner (pm_edge_scanner.py) with volume floor, regime-adjusted thresholds, and BettingAlpha scoring — turning 12 of 13 RED stubs GREEN.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-14T04:14:00Z
- **Completed:** 2026-03-14T04:24:46Z
- **Tasks:** 2
- **Files created:** 2

## Accomplishments

- Implemented `classify_pm_regime()` with 5-state priority rule chain (PRE_RESOLUTION → DISCOVERY → NEWS_CATALYST → CONSENSUS → SHARP_DISAGREEMENT)
- Implemented `scan_pm_edges()` handling both Kalshi (volume in contracts, converted to USD) and Polymarket (volume already in USD)
- Wired in `compose_alpha()` from sharpedge_models for alpha score and badge on every qualifying PMEdge
- 8/8 pm_regime tests GREEN, 4/5 pm_edge_scanner tests GREEN (1 test deferred to Plan 03 per spec)
- No regressions in full 69-test suite

## Task Commits

1. **Task 1: Implement pm_regime.py** - `f00e018` (feat)
2. **Task 2: Implement pm_edge_scanner.py** - `5cd1917` (feat)

## Files Created/Modified

- `/Users/revph/sharpedge/packages/analytics/src/sharpedge_analytics/pm_regime.py` — 5-state PM regime classifier with thresholds and scales (110 lines)
- `/Users/revph/sharpedge/packages/analytics/src/sharpedge_analytics/pm_edge_scanner.py` — PMEdge dataclass and scan_pm_edges() for Kalshi + Polymarket (228 lines)

## Decisions Made

- Used `price_variance` as parameter name (not `price_variance_7d`) to exactly match existing test contracts
- Accepted `active_bets` and `market_titles` as no-op kwargs to avoid TypeError on the deferred correlation test — correlation logic goes in Plan 03
- BettingAlpha fields `alpha` → `PMEdge.alpha_score` and `quality_badge` → `PMEdge.alpha_badge` — bridged the naming gap without changing alpha.py
- Fee fallback model_prob capped at `min(market_prob / (1 - fee_rate), 1.0)` to prevent values > 1.0 on near-certain markets

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Parameter name mismatch: price_variance vs price_variance_7d**
- **Found during:** Task 1 (implement pm_regime.py)
- **Issue:** Plan action block shows `price_variance_7d` in function signature but existing tests call `price_variance=...`
- **Fix:** Used `price_variance` as the parameter name to match the locked test contracts (test contracts take priority per TDD)
- **Files modified:** packages/analytics/src/sharpedge_analytics/pm_regime.py
- **Verification:** All 8 test_pm_regime.py tests pass
- **Committed in:** f00e018 (Task 1 commit)

**2. [Rule 2 - Missing Critical] scan_pm_edges must accept deferred correlation kwargs**
- **Found during:** Task 2 (run RED tests)
- **Issue:** `test_correlation_warning_order` calls `scan_pm_edges(active_bets=..., market_titles=...)` which raised TypeError without those params
- **Fix:** Added `active_bets: list | None = None` and `market_titles: dict | None = None` to function signature (ignored in body); correlation logic deferred to Plan 03
- **Files modified:** packages/analytics/src/sharpedge_analytics/pm_edge_scanner.py
- **Verification:** TypeError resolved; 4 of 5 edge scanner tests GREEN; correlation test fails on assertion (expected — Plan 03 will implement it)
- **Committed in:** 5cd1917 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 parameter name bug, 1 missing kwargs for forward-compat)
**Impact on plan:** Both fixes required for correctness. No scope creep — correlation logic not implemented, only interface is forward-compatible.

## Issues Encountered

- `test_correlation_warning_order` is a pre-written RED stub that asserts correlation warning entries exist in the result list — this is PM-04 functionality explicitly deferred to Plan 03. The test remains RED as designed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 03 can immediately implement correlation warning entries — `scan_pm_edges` already accepts `active_bets` and `market_titles` params
- PMEdge.alpha_score is compatible with `rank_by_alpha()`'s `getattr(play, 'alpha_score', None)` pattern
- All PM-01, PM-02, PM-03 requirements delivered

---
*Phase: 03-prediction-market-intelligence*
*Completed: 2026-03-14*
