---
phase: 06-multi-venue-quant-infrastructure
plan: "04"
subsystem: devig-and-sportsbook-adapter
tags:
  - devig
  - shin
  - sportsbook
  - odds-api
  - venue-adapter
dependency_graph:
  requires:
    - 06-02
  provides:
    - devig_shin_n_outcome in sharpedge_models.no_vig
    - OddsApiAdapter in sharpedge_venue_adapters.adapters.odds_api
    - InsufficientCreditsError in sharpedge_venue_adapters.adapters.odds_api
  affects:
    - packages/models/src/sharpedge_models/no_vig.py
    - packages/venue_adapters/src/sharpedge_venue_adapters/adapters/odds_api.py
    - packages/venue_adapters/src/sharpedge_venue_adapters/adapters/__init__.py
tech_stack:
  added:
    - scipy.optimize.brentq (already workspace dep; used in devig_shin_n_outcome)
    - httpx (already workspace dep; used in OddsApiAdapter)
  patterns:
    - Shin z-parameter brentq solver for N-outcome devigging
    - Credit-guard pattern: _check_credits() before every API call
    - Structural typing via @runtime_checkable Protocol
key_files:
  created:
    - packages/venue_adapters/src/sharpedge_venue_adapters/adapters/odds_api.py
  modified:
    - packages/models/src/sharpedge_models/no_vig.py
    - packages/venue_adapters/src/sharpedge_venue_adapters/adapters/__init__.py
decisions:
  - devig_shin_n_outcome falls back to multiplicative normalization when brentq raises ValueError — ensures function never crashes on edge-case input
  - OddsApiAdapter._check_credits() guard fires before each API call (not only list_markets) — future-proofing for additional endpoints
  - remaining_credits starts as None (not 0) to distinguish "never called" from "zero credits"
  - OddsApiAdapter yes_bid/yes_ask use min/max implied probs across bookmakers — conservative spread estimate; mid_prob deferred to caller
metrics:
  duration_seconds: 100
  completed_date: "2026-03-14"
  tasks_completed: 2
  files_created: 1
  files_modified: 2
---

# Phase 6 Plan 04: N-Outcome Shin Devig and OddsApiAdapter Summary

**One-liner:** N-outcome Shin brentq devig (devig_shin_n_outcome) and read-only OddsApiAdapter with X-Requests-Remaining credit tracking and InsufficientCreditsError circuit breaker.

---

## What Was Built

### Task 1 — devig_shin_n_outcome() in no_vig.py

Extended `packages/models/src/sharpedge_models/no_vig.py` with `devig_shin_n_outcome(implied_probs: list[float]) -> list[float]`:

- Generalizes two-outcome `devig_shin()` to N>=2 outcomes (soccer three-way, futures markets)
- Algorithm: `brentq` finds z in (0, 1) such that `sum(shin_fair(q_i, z)) == 1.0` where `shin_fair(q, z) = (sqrt(z**2 + 4*(1-z)*q**2) - z) / (2*(1-z))`
- No-vig passthrough: if `sum(implied_probs)` is within 1e-6 of 1.0, returns unchanged
- Fallback: multiplicative normalization when brentq raises ValueError
- Raises ValueError for empty input or probabilities outside (0, 1)
- All 6 tests in `test_no_vig_n_outcome.py` GREEN

### Task 2 — OddsApiAdapter in adapters/odds_api.py

Created `packages/venue_adapters/src/sharpedge_venue_adapters/adapters/odds_api.py`:

- `OddsApiAdapter` satisfies `VenueAdapter` Protocol via structural typing (`@runtime_checkable`)
- `venue_id = "odds_api"`, `capabilities.read_only = True`, `capabilities.execution_supported = False`
- `remaining_credits: int | None = None` — starts None, updated from `X-Requests-Remaining` header after each API call
- `InsufficientCreditsError(Exception)` raised when `remaining_credits < 50`
- `list_markets(sport_key="basketball_nba")` calls The Odds API v4 `/sports/{sport_key}/odds` endpoint, parses bookmaker h2h odds into `CanonicalMarket` list; gracefully returns `[]` on HTTP error
- `get_trades`, `get_historical_snapshots` return `[]`; `get_settlement_state` returns `None`
- `get_orderbook` returns empty `CanonicalOrderBook` with current timestamp
- `get_fees_and_limits` returns `VenueFeeSchedule(venue_id="odds_api", maker_fee_rate=0.0, taker_fee_rate=0.0, expected_quote_refresh_seconds=60)`
- `adapters/__init__.py` updated to export `OddsApiAdapter` and `InsufficientCreditsError`
- All 5 tests in `test_sportsbook_adapter.py` GREEN

---

## Test Results

| Test File | Tests | Status |
|-----------|-------|--------|
| test_no_vig_n_outcome.py | 6/6 | GREEN |
| test_sportsbook_adapter.py | 5/5 | GREEN |
| **Total** | **11/11** | **GREEN** |

---

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | caa7c1a | feat(06-04): add devig_shin_n_outcome() — N-outcome Shin devig extension |
| 2 | d3bb7a8 | feat(06-04): implement OddsApiAdapter with credit tracking and circuit breaker |

---

## Deviations from Plan

None - plan executed exactly as written.

---

## Self-Check: PASSED

Files verified:
- FOUND: packages/models/src/sharpedge_models/no_vig.py (devig_shin_n_outcome appended)
- FOUND: packages/venue_adapters/src/sharpedge_venue_adapters/adapters/odds_api.py (created)
- FOUND: packages/venue_adapters/src/sharpedge_venue_adapters/adapters/__init__.py (updated)

Commits verified:
- FOUND: caa7c1a
- FOUND: d3bb7a8
