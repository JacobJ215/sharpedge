---
phase: 09-prediction-market-resolution-models-and-expansion
plan: "05"
subsystem: prediction-market-models
tags: [prediction-markets, ml-inference, feature-flag, joblib, sklearn, pm-resolution-predictor]
dependency_graph:
  requires:
    - phase: 09-03
      provides: PMFeatureAssembler.assemble() + detect_category()
    - phase: 09-04
      provides: data/models/pm/{category}.joblib trained artifacts
  provides:
    - PMResolutionPredictor.build_model_probs() — ENABLE_PM_RESOLUTION_MODEL-gated dict[str, float]
  affects:
    - pm_edge_scanner.scan_pm_edges() — model_probs source changes from fee-adjusted to ML-predicted
tech_stack:
  added: []
  patterns:
    - ENABLE_PM_RESOLUTION_MODEL feature flag gates all ML inference
    - Lazy per-category model loading — each category loaded once per predictor instance
    - try/except wraps joblib.load and predict_proba — missing files and inference errors return None/{}
    - market_id resolution priority: ticker -> condition_id -> market_id (Kalshi-first, Polymarket-second)
key_files:
  created: []
  modified:
    - packages/models/src/sharpedge_models/pm_resolution_predictor.py
    - tests/unit/models/test_pm_resolution_predictor.py
decisions:
  - "Removed model_path.exists() pre-check — try/except on joblib.load handles FileNotFoundError identically, enables patch('joblib.load') in tests without real files"
  - "market_id resolution uses ticker -> condition_id -> market_id fallback chain to support both Kalshi (ticker) and Polymarket (condition_id) plus test fixtures (market_id)"
  - "PMFeatureAssembler imported at module level (not inside method) — required for mock.patch in integration tests"
requirements:
  - PM-RES-02
  - PM-INT-01
metrics:
  duration_minutes: 15
  completed_date: "2026-03-15"
  tasks_completed: 1
  files_created: 0
  files_modified: 2
---

# Phase 9 Plan 05: PMResolutionPredictor Implementation Summary

**One-liner:** ENABLE_PM_RESOLUTION_MODEL-gated per-category joblib inference class connecting trained PM models to scan_pm_edges() via dict[str, float] model_probs.

---

## What Was Built

Implemented the full `PMResolutionPredictor` class in `packages/models/src/sharpedge_models/pm_resolution_predictor.py`, replacing the plan 01 stub that returned `{}` unconditionally.

### PMResolutionPredictor — Final Implementation

**Constructor (`__init__`):**
- `model_dir` — defaults to `Path("data/models/pm")`; accepts `tmp_path` in tests
- `assembler` — defaults to `PMFeatureAssembler()` (offline, no API clients); injectable for testing
- `_models: dict[str, Any]` — lazy-loaded cache, one entry per category

**`_is_enabled() -> bool`:**
- Returns `True` only when `ENABLE_PM_RESOLUTION_MODEL` is `"true"` or `"1"` (case-insensitive)

**`_load_model(category) -> Any | None`:**
- Calls `joblib.load(model_dir / f"{category}.joblib")`
- Wraps in try/except — `FileNotFoundError` and any other exception return `None`
- No pre-existence check (`Path.exists()`) — enables `patch("joblib.load")` in tests without real files on disk

**`_predict_market(market, model) -> float | None`:**
- Calls `assembler.assemble(market)` to produce feature vector
- Calls `model.predict_proba(features.reshape(1, -1))[0][1]` — probability of YES (positive class, index 1)
- Wraps in try/except — returns `None` on any error

**`build_model_probs(markets) -> dict[str, float]`:**
- Returns `{}` immediately when `_is_enabled()` is False
- Iterates markets, calls `detect_category()` per market
- Lazy-loads model on first encounter of each category (`_models[category] = _load_model(category)`)
- Skips markets whose category has no model (`None`)
- Resolves market_id via `ticker -> condition_id -> market_id` priority chain
- Skips markets with no resolvable ID
- Collects valid predictions into `result`; returns after all markets processed

### Integration Test Added

Added `test_integration_with_scan_pm_edges` to `tests/unit/models/test_pm_resolution_predictor.py`:
- Creates `PMResolutionPredictor(model_dir=tmp_path)` with pre-injected `_models["crypto"] = mock_model`
- Calls `build_model_probs([crypto_market_with_ticker])` → verifies `"KXBTC-26Q1-T100"` in result with prob in (0, 1)
- Passes result to `scan_pm_edges(kalshi_markets=[], polymarket_markets=[], model_probs=model_probs)` → verifies no exception, returns list

---

## Test Results

### PMResolutionPredictor unit tests (6/6 GREEN):

```
tests/unit/models/test_pm_resolution_predictor.py::test_flag_off_returns_empty PASSED
tests/unit/models/test_pm_resolution_predictor.py::test_no_exceptions_on_missing_models PASSED
tests/unit/models/test_pm_resolution_predictor.py::test_flag_on_missing_model_file_returns_empty_for_category PASSED
tests/unit/models/test_pm_resolution_predictor.py::test_skipped_category_not_in_output PASSED
tests/unit/models/test_pm_resolution_predictor.py::test_flag_on_with_model_returns_probabilities PASSED
tests/unit/models/test_pm_resolution_predictor.py::test_integration_with_scan_pm_edges PASSED
6 passed in 1.91s
```

### Full Phase 9 regression (88/88 GREEN + 6 XPASS):

```
82 passed, 6 xpassed, 1 warning in 4.79s
```

All Phase 9 test files collected:
- `tests/unit/models/test_pm_feature_assembler.py` — 18 passed
- `tests/unit/models/test_pm_resolution_predictor.py` — 6 passed
- `tests/unit/feeds/test_coingecko_client.py` — passed
- `tests/unit/feeds/test_fec_client.py` — passed
- `tests/unit/feeds/test_bls_client.py` — passed
- `tests/unit/scripts/` — 6 xpassed (process + train contracts)

### Flag-off verification:

```
Flag-off path: PASS (returns empty dict)
```

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed Path.exists() pre-check in _load_model()**
- **Found during:** Task 1 (test design analysis)
- **Issue:** Plan spec included `if model_dir / f"{category}.joblib" does not exist: return None` before `joblib.load`. However, `test_flag_on_with_model_returns_probabilities` patches `joblib.load` globally without creating a real file — the existence check would short-circuit before the patch was ever reached, keeping the test RED.
- **Fix:** Removed existence check; wrapped `joblib.load` in try/except only. `FileNotFoundError` is caught and returns `None`, identical behavior to the plan spec. Test suite passes correctly.
- **Files modified:** `packages/models/src/sharpedge_models/pm_resolution_predictor.py`
- **Commit:** 24767ad

---

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1    | 24767ad | feat(09-05): implement PMResolutionPredictor ENABLE_PM_RESOLUTION_MODEL-gated inference |

---

## Success Criteria — VERIFIED

- [x] ENABLE_PM_RESOLUTION_MODEL unset -> build_model_probs() returns {}
- [x] ENABLE_PM_RESOLUTION_MODEL=true, model present -> returns dict with market_id -> float in (0,1)
- [x] ENABLE_PM_RESOLUTION_MODEL=true, model absent -> returns {} (no exception)
- [x] scan_pm_edges() called with build_model_probs() output does not raise
- [x] pm_edge_scanner.py is NOT modified (scanner unchanged)
- [x] All Phase 9 test files pass GREEN (82 passed, 6 xpassed)
- [x] PMResolutionPredictor file under 150 lines (118 lines)

---

## Self-Check: PASSED

Files verified present:
- `packages/models/src/sharpedge_models/pm_resolution_predictor.py` — FOUND
- `tests/unit/models/test_pm_resolution_predictor.py` — FOUND

Commit `24767ad` confirmed in git log.

---

*Phase: 09-prediction-market-resolution-models-and-expansion*
*Status: COMPLETE*
*Completed: 2026-03-15*
