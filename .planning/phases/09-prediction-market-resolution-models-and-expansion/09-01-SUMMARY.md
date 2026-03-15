---
phase: 09-prediction-market-resolution-models-and-expansion
plan: "01"
subsystem: prediction-market-models
tags: [tdd, red-stubs, pm-models, api-clients, interface-contracts]
dependency_graph:
  requires: []
  provides:
    - PMFeatureAssembler interface contract (assemble + detect_category)
    - PMResolutionPredictor interface contract (build_model_probs)
    - CoinGeckoClient interface contract (get_price, get_price_change_7d)
    - FECClient interface contract (get_polling_average, get_election_proximity_days)
    - BLSClient interface contract (get_days_since_last_release, get_is_release_imminent)
    - download_pm_historical.py contract (xfail stubs)
    - process_pm_historical.py contract (xfail stubs)
    - train_pm_models.py contract (xfail stubs)
  affects:
    - plans 02-05 implementation targets (locked by these stubs)
tech_stack:
  added: []
  patterns:
    - TDD RED stub pattern — stubs define interface, tests lock contract before implementation
    - pytest.mark.xfail for non-existent scripts (documents contract without requiring script existence)
    - NotImplementedError stub body as explicit plan-gating mechanism
key_files:
  created:
    - packages/models/src/sharpedge_models/pm_feature_assembler.py
    - packages/models/src/sharpedge_models/pm_resolution_predictor.py
    - packages/data_feeds/src/sharpedge_feeds/coingecko_client.py
    - packages/data_feeds/src/sharpedge_feeds/fec_client.py
    - packages/data_feeds/src/sharpedge_feeds/bls_client.py
    - tests/unit/models/test_pm_feature_assembler.py
    - tests/unit/models/test_pm_resolution_predictor.py
    - tests/unit/feeds/test_coingecko_client.py
    - tests/unit/feeds/test_fec_client.py
    - tests/unit/feeds/test_bls_client.py
    - tests/unit/scripts/test_download_pm_historical.py
    - tests/unit/scripts/test_process_pm_historical.py
    - tests/unit/scripts/test_train_pm_models.py
    - tests/unit/feeds/__init__.py
    - tests/unit/scripts/__init__.py
  modified:
    - packages/data_feeds/src/sharpedge_feeds/__init__.py
decisions:
  - detect_category() implemented GREEN in stub (ticker-prefix map + keyword fallback); assemble() deferred to plan 03
  - build_model_probs() returns {} as correct safe default; plan 03 implements model loading
  - Script tests use pytest.mark.xfail (not importorskip) to document exact function signatures as contracts
  - test_flag_on_with_model_returns_probabilities is the single gating RED test for plan 03 implementation
metrics:
  duration_minutes: 5
  completed_date: "2026-03-15"
  tasks_completed: 2
  files_created: 15
  files_modified: 1
---

# Phase 9 Plan 01: RED TDD Stubs — PM Interface Contract Lock Summary

**One-liner:** TDD RED stub phase locking all Phase 9 interface contracts (PMFeatureAssembler, PMResolutionPredictor, 3 API clients, 3 script functions) before any plan 02-05 implementation begins.

---

## What Was Built

Phase 9 plan 01 establishes the TDD contract foundation for all prediction market resolution model work. Five stub modules and 8 test files were created; no production logic was implemented (by design).

### Task 1 — PMFeatureAssembler + PMResolutionPredictor Stubs

**Stub: `pm_feature_assembler.py`**
- `PM_UNIVERSAL_FEATURES` constant (6 features)
- `PM_CATEGORY_EXTRA_FEATURES` mapping (per-category add-on features)
- `CATEGORY_KEYWORDS` and `TICKER_PREFIX_CATEGORY` dicts
- `PMFeatureAssembler.detect_category()` — IMPLEMENTED (ticker-prefix map first, then keyword scan, fallback to "entertainment")
- `PMFeatureAssembler.assemble()` — raises `NotImplementedError("implement in plan 03")`

**Stub: `pm_resolution_predictor.py`**
- `ENABLE_FLAG = "ENABLE_PM_RESOLUTION_MODEL"` module-level constant
- `PM_MODEL_DIR = Path("data/models/pm")` module-level constant
- `PMResolutionPredictor.build_model_probs()` — returns `{}` (correct safe default; missing key → fee-adjusted fallback in `scan_pm_edges`)

**Test results:**
- 18 tests in `test_pm_feature_assembler.py`: 18 passed (6 assemble RED via `pytest.raises(NotImplementedError)`, 12 detect_category GREEN)
- 5 tests in `test_pm_resolution_predictor.py`: 4 passed GREEN, 1 FAILED RED (`test_flag_on_with_model_returns_probabilities`)

### Task 2 — 3 API Clients + Script Contract Stubs

**Stub: `coingecko_client.py`**
- `COINGECKO_BASE` module-level constant
- `CoinGeckoClient.get_price()` and `get_price_change_7d()` — both raise `NotImplementedError`

**Stub: `fec_client.py`**
- `FECClient.get_polling_average()` and `get_election_proximity_days()` — both raise `NotImplementedError`

**Stub: `bls_client.py`**
- `BLS_RELEASE_CALENDAR_URL` module-level constant
- `BLSClient.get_days_since_last_release()` and `get_is_release_imminent()` — both raise `NotImplementedError`

**`__init__.py` update:** Appended exports for `CoinGeckoClient`, `FECClient`, `BLSClient`.

**Script xfail tests (9 total):**
- `test_download_pm_historical.py` — 3 xfail (backfill_kalshi_resolved, backfill_polymarket_resolved, offline fixture mode)
- `test_process_pm_historical.py` — 3 xfail (process_kalshi, process_polymarket, low-data category report)
- `test_train_pm_models.py` — 3 xfail (skip <200, joblib artifact, walk-forward 3-window requirement)

---

## Verification

Full stub check result:

```
36 tests: 35 passed, 1 failed (AssertionError — plan 03 gate)
9 script tests: 9 xfailed
No ImportError in any file
```

All 8 test files collected. 5 stub files importable. No GREEN implementation leaked (only detect_category and safe-default returns are GREEN by design).

---

## Deviations from Plan

None — plan executed exactly as written. detect_category() was explicitly listed as GREEN in the action spec.

---

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | e45a43e | RED stubs — PMFeatureAssembler + PMResolutionPredictor |
| 2 | 108fe71 | RED stubs — 3 API clients + download/process/train script contracts |

---

## Interface Contracts Locked

| Component | Method | Plan to Implement | RED Signal |
|-----------|--------|-------------------|------------|
| PMFeatureAssembler | assemble() | 03 | NotImplementedError |
| PMResolutionPredictor | build_model_probs() | 03 | returns {} (not populated) |
| CoinGeckoClient | get_price, get_price_change_7d | 02 | NotImplementedError |
| FECClient | get_polling_average, get_election_proximity_days | 02 | NotImplementedError |
| BLSClient | get_days_since_last_release, get_is_release_imminent | 02 | NotImplementedError |
| download_pm_historical | backfill_kalshi/polymarket_resolved | 02 | xfail |
| process_pm_historical | process_kalshi, process_polymarket, process_and_report | 04 | xfail |
| train_pm_models | train_category | 04/05 | xfail |

## Self-Check: PASSED

All 10 key files verified present on disk. Both commits (e45a43e, 108fe71) confirmed in git log.
