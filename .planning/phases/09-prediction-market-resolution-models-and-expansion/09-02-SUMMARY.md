---
phase: 09-prediction-market-resolution-models-and-expansion
plan: "02"
subsystem: prediction-market-models
tags: [tdd, green-implementation, pm-data, api-clients, download-script]
dependency_graph:
  requires:
    - 09-01 (RED stubs for CoinGeckoClient, FECClient, BLSClient, download_pm_historical)
  provides:
    - CoinGeckoClient implementation (get_price, get_price_change_7d with offline fallback)
    - FECClient implementation (polling average + election proximity days)
    - BLSClient implementation (static cadence dict + imminence detection)
    - download_pm_historical.py (backfill_kalshi_resolved + backfill_polymarket_resolved)
    - kalshi_sample.json fixture (50 rows, 5 category prefixes)
  affects:
    - PMFeatureAssembler (plan 03) — CoinGeckoClient.get_price() provides underlying_asset_price feature
    - train_pm_models.py (plan 04) — kalshi_resolved.parquet + polymarket_resolved.parquet training data
tech_stack:
  added: []
  patterns:
    - Synchronous httpx for CoinGeckoClient (training-time feature fetch, not async)
    - Offline env-var pattern (COINGECKO_OFFLINE, FEC_OFFLINE, BLS_OFFLINE) for CI/test safety
    - Static cadence dict instead of live BLS calendar parsing (sufficient for ML feature engineering)
    - asyncio.gather() for concurrent Kalshi + Polymarket backfill in main()
    - _market_to_dict() helper for dataclass/mock duality in backfill_kalshi_resolved
key_files:
  created:
    - scripts/download_pm_historical.py
    - data/raw/prediction_markets/fixtures/kalshi_sample.json
  modified:
    - packages/data_feeds/src/sharpedge_feeds/coingecko_client.py
    - packages/data_feeds/src/sharpedge_feeds/fec_client.py
    - packages/data_feeds/src/sharpedge_feeds/bls_client.py
    - tests/unit/feeds/test_coingecko_client.py
    - tests/unit/feeds/test_fec_client.py
    - tests/unit/feeds/test_bls_client.py
    - tests/unit/scripts/test_download_pm_historical.py
decisions:
  - CoinGeckoClient uses synchronous httpx (not async) — feature fetch at training time is synchronous
  - FECClient.get_election_proximity_days is pure datetime math — no network call
  - BLSClient uses static RELEASE_CADENCE_DAYS dict not live BLS calendar — sufficient for feature engineering
  - Unknown BLS series explicitly returns (30, False) not computed approximation
  - _market_to_dict() handles both dataclass (production) and MagicMock (tests) to avoid asdict() TypeError
  - 50-row kalshi_sample.json has balanced yes/no results (alternating) for unbiased fixture training
  - Polymarket offline uses synthetic fixture not JSON file (Polymarket is public; fixture sufficient for test isolation)
metrics:
  duration_minutes: 21
  completed_date: "2026-03-15"
  tasks_completed: 2
  files_created: 2
  files_modified: 7
---

# Phase 9 Plan 02: Download Pipeline + 3 API Clients Summary

**One-liner:** Synchronous CoinGecko/FEC/BLS clients with offline env-var flags and async Kalshi+Polymarket backfill script with 50-row category-balanced fixture.

---

## What Was Built

### Task 1 — 3 Lightweight API Clients (GREEN implementation)

**CoinGeckoClient** (`packages/data_feeds/src/sharpedge_feeds/coingecko_client.py`, 84 lines):
- `get_price(coin_id)` → calls `/simple/price?ids={coin_id}&vs_currencies=usd`; returns `float`; 0.0 on any error
- `get_price_change_7d(coin_id)` → calls same endpoint with `price_change_percentage=7d`; parses `usd_7d_change`
- Offline: `COINGECKO_OFFLINE=true` env var or `offline=True` constructor arg → returns 0.0 without network
- Optional `api_key` arg for CoinGecko Pro API (sent as `x-cg-pro-api-key` header)

**FECClient** (`packages/data_feeds/src/sharpedge_feeds/fec_client.py`, 92 lines):
- `get_polling_average(race_id)` → FEC presidential coverage endpoint (best-effort); normalizes candidate contribution counts to [0, 1]; returns 0.0 on any error or offline
- `get_election_proximity_days(election_date_str)` → pure `datetime.strptime` + `date.today()` math; returns `max(0, delta.days)`; 365 on parse error
- No API key required (FEC public API)

**BLSClient** (`packages/data_feeds/src/sharpedge_feeds/bls_client.py`, 101 lines):
- `RELEASE_CADENCE_DAYS = {"CPI": 30, "PPI": 30, "NFP": 30, "GDP": 90}` static dict
- `get_days_since_last_release(series)` → uses today's day-of-month (monthly) or day-of-year % 90 (GDP) as approximation; unknown series → 30
- `get_is_release_imminent(series, threshold_days=3)` → `cadence - days_since <= threshold_days`; unknown series → False

**Test results:** 33 tests passing GREEN (11 CoinGecko, 11 FEC, 11 BLS).

### Task 2 — download_pm_historical.py + Fixture

**Script** (`scripts/download_pm_historical.py`, 246 lines):
- `backfill_kalshi_resolved(out_dir, offline)`: cursor-based pagination on settled markets; offline/no-key → loads `data/raw/prediction_markets/fixtures/kalshi_sample.json` (50 rows); saves to `out_dir/kalshi_resolved.parquet`
- `backfill_polymarket_resolved(out_dir, offline)`: offset-based pagination on closed markets; offline → 50-row synthetic fixture; saves to `out_dir/polymarket_resolved.parquet`
- `_normalize_polymarket_outcome(market)`: 2-outcome → check "Yes" winner; 3+-outcome → check any non-"No" winner
- `_market_to_dict(market)`: handles dataclass (production) and non-dataclass (test mock) objects
- `main()`: `argparse` with `--out-dir` and `--offline`; runs both backfills via `asyncio.gather()`

**Fixture** (`data/raw/prediction_markets/fixtures/kalshi_sample.json`):
- 50 rows: 10 each for KXPOL, KXFED, KXBTC, KXENT, KXWTH event_ticker prefixes
- Alternating "yes"/"no" results per category for balanced labels
- All KalshiMarket fields present (ticker, event_ticker, title, yes_bid, yes_ask, volume, open_interest, last_price, close_time, result)

**Test results:** 13 tests passing GREEN (offline, parquet write, mocked live, normalization, fixture).

---

## Verification

```
46 tests: 46 passed (feeds + download script)
python -c "from sharpedge_feeds.coingecko_client import CoinGeckoClient; ..." → all 3 clients importable
50 fixture rows, prefixes: ['KXBTC', 'KXENT', 'KXFED', 'KXPOL', 'KXWTH']
python scripts/download_pm_historical.py --offline → Kalshi: 50 rows, Polymarket: 50 rows
```

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] BLSClient unknown series cadence lookup**
- **Found during:** Task 1 test run
- **Issue:** `get_days_since_last_release("UNKNOWN")` fell through to `_DEFAULT_CADENCE = 30` and used `today.day` (=14) instead of returning the safe default 30
- **Fix:** Added explicit `if series_upper not in RELEASE_CADENCE_DAYS: return 30` check before computing approximation; same guard added in `get_is_release_imminent` to prevent imminence being True on unknown series
- **Files modified:** `packages/data_feeds/src/sharpedge_feeds/bls_client.py`
- **Commit:** included in 3996081

**2. [Rule 1 - Bug] dataclasses.asdict() on MagicMock in backfill_kalshi_resolved**
- **Found during:** Task 2 test run
- **Issue:** `pd.DataFrame([asdict(m) for m in all_markets])` raised `TypeError: asdict() should be called on dataclass instances` when market objects were `MagicMock` (test context)
- **Fix:** Extracted `_market_to_dict()` helper that uses `dataclasses.is_dataclass()` to branch between `dataclasses.asdict()` (production) and `getattr`-based field extraction (mocks/non-dataclass)
- **Files modified:** `scripts/download_pm_historical.py`
- **Commit:** included in cc6af74

---

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 3996081 | feat(09-02): implement CoinGeckoClient, FECClient, BLSClient |
| 2 | cc6af74 | feat(09-02): implement download_pm_historical.py + kalshi fixture |

---

## Interface Contracts Delivered

| Component | Method | Status |
|-----------|--------|--------|
| CoinGeckoClient | get_price() | GREEN |
| CoinGeckoClient | get_price_change_7d() | GREEN |
| FECClient | get_polling_average() | GREEN |
| FECClient | get_election_proximity_days() | GREEN |
| BLSClient | get_days_since_last_release() | GREEN |
| BLSClient | get_is_release_imminent() | GREEN |
| download_pm_historical | backfill_kalshi_resolved() | GREEN |
| download_pm_historical | backfill_polymarket_resolved() | GREEN |

## Self-Check: PASSED
