---
phase: 03-prediction-market-intelligence
plan: "01"
subsystem: analytics
tags: [prediction-markets, refactor, tdd, sub-package, red-tests]
dependency_graph:
  requires: []
  provides:
    - sharpedge_analytics.prediction_markets (sub-package)
    - tests/unit/analytics/test_pm_edge_scanner.py (RED)
    - tests/unit/analytics/test_pm_regime.py (RED)
    - tests/unit/analytics/test_pm_correlation.py (RED)
  affects:
    - packages/analytics/src/sharpedge_analytics/prediction_markets/
    - tests/unit/analytics/
tech_stack:
  added: []
  patterns:
    - Sub-package split with backward-compatible __init__.py re-exports
    - TDD RED phase — import-failing stubs define Wave 1 contracts
key_files:
  created:
    - packages/analytics/src/sharpedge_analytics/prediction_markets/__init__.py
    - packages/analytics/src/sharpedge_analytics/prediction_markets/fees.py
    - packages/analytics/src/sharpedge_analytics/prediction_markets/types.py
    - packages/analytics/src/sharpedge_analytics/prediction_markets/arbitrage.py
    - tests/unit/analytics/test_pm_edge_scanner.py
    - tests/unit/analytics/test_pm_regime.py
    - tests/unit/analytics/test_pm_correlation.py
  modified:
    - packages/analytics/src/sharpedge_analytics/prediction_markets.py (deleted — replaced by sub-package)
decisions:
  - "fees.py holds Platform enum, PlatformFees, PLATFORM_FEES, fee helper functions, and price conversion utilities (one cohesive concern)"
  - "types.py holds MarketOutcome and CanonicalEvent only — PredictionMarketArbitrage moved to arbitrage.py where it belongs with the functions that create it"
  - "__init__.py re-exports private helpers (_kalshi_fee_formula, _check_arb_direction) to preserve any callers that import them directly"
  - "RED stubs use plain def test_ functions with pytest fixtures and MagicMock — no unittest.TestCase or asyncio"
metrics:
  duration_seconds: 265
  completed_date: "2026-03-14T04:15:22Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 7
  files_modified: 0
  files_deleted: 1
---

# Phase 3 Plan 01: Prediction Markets Sub-Package Split + RED Tests Summary

**One-liner:** Split 614-line prediction_markets.py monolith into 4-module sub-package (fees/types/arbitrage/__init__) and scaffold 19 RED test stubs defining PM scanner, regime, and correlation contracts.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Split prediction_markets.py into sub-package | 0d61f89 | fees.py, types.py, arbitrage.py, __init__.py created; prediction_markets.py deleted |
| 2 | Write RED test stubs for PM-01/02/03/04 | f8ef627 | test_pm_edge_scanner.py, test_pm_regime.py, test_pm_correlation.py |

---

## What Was Built

### Task 1: Sub-Package Split

The 614-line `prediction_markets.py` was split into a proper sub-package with clear separation of concerns:

- **fees.py** (135 lines): `Platform` enum, `PlatformFees` dataclass, Kalshi fee formulas, `PLATFORM_FEES` dict, price/probability converters, `calculate_fee_adjusted_price()`
- **types.py** (70 lines): `MarketOutcome`, `CanonicalEvent` dataclasses
- **arbitrage.py** (409 lines): `PredictionMarketArbitrage`, `find_cross_platform_arbitrage()`, `_check_arb_direction()`, `detect_probability_gap()`, `MarketCorrelationNetwork`, `calculate_sizing_instructions()`
- **__init__.py** (48 lines): Explicit re-exports of all public symbols — backward compatible with all existing callers

57 existing tests remain green after the split.

### Task 2: RED Test Stubs

Three test files covering Wave 1 contracts:

**test_pm_edge_scanner.py** (5 tests, PM-01 + PM-02):
- Kalshi market → PMEdge with edge_pct > 0 and platform == "kalshi"
- Polymarket market → PMEdge with edge_pct > 0 and platform == "polymarket"
- Volume floor filter removes low-liquidity markets (volume < 500)
- PMEdge has alpha_score (float, not None) and alpha_badge (non-empty string)
- Correlation warning entry precedes its correlated PMEdge in result list

**test_pm_regime.py** (8 tests, PM-03):
- PRE_RESOLUTION when hours_to_close < 24
- DISCOVERY when market age < 48h
- NEWS_CATALYST on volume_spike_ratio >= 4.0 (not PRE_RESOLUTION/DISCOVERY)
- CONSENSUS on low price_variance, no spike
- SHARP_DISAGREEMENT as default high-variance state
- DISCOVERY edge_threshold_pct == 2.0
- PRE_RESOLUTION edge_threshold_pct == 5.0
- PRE_RESOLUTION priority beats DISCOVERY when both conditions met

**test_pm_correlation.py** (6 tests, PM-04):
- Exact text match → 1.0 correlation
- Shared entity "Celtics" → correlation > 0.5
- Different entities → correlation < 0.1
- Shared entity → bet appears in detect_correlated_positions result
- Below threshold (0.6) → empty result list
- Stopwords ("will", "the", "win") excluded → no false correlation

All 19 tests fail with `ModuleNotFoundError` — no implementation exists yet.

---

## Verification Results

```
# Existing suite green:
57 passed, 1 warning in 6.14s

# Backward compat:
python -c "from sharpedge_analytics.prediction_markets import PLATFORM_FEES" → OK

# RED stubs confirmed:
3 errors (ImportError) in 2.06s — all three modules missing as expected

# Line counts (all < 500):
  48 __init__.py
 135 fees.py
  70 types.py
 409 arbitrage.py

# Monolith removed:
ls prediction_markets.py → No such file or directory
```

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Self-Check: PASSED

Files confirmed to exist:
- packages/analytics/src/sharpedge_analytics/prediction_markets/__init__.py: FOUND
- packages/analytics/src/sharpedge_analytics/prediction_markets/fees.py: FOUND
- packages/analytics/src/sharpedge_analytics/prediction_markets/types.py: FOUND
- packages/analytics/src/sharpedge_analytics/prediction_markets/arbitrage.py: FOUND
- tests/unit/analytics/test_pm_edge_scanner.py: FOUND
- tests/unit/analytics/test_pm_regime.py: FOUND
- tests/unit/analytics/test_pm_correlation.py: FOUND

Commits confirmed:
- 0d61f89: refactor(03-01): split prediction_markets.py into sub-package
- f8ef627: test(03-01): add RED stubs for PM-01/02/03/04 behaviors
