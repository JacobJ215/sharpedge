---
phase: 06-multi-venue-quant-infrastructure
plan: 01
subsystem: venue-adapters
tags: [tdd, red-stubs, package-scaffold, interface-contracts, wave-0]
dependency_graph:
  requires: []
  provides:
    - packages/venue_adapters uv workspace package
    - RED test stubs for VENUE-01 through SETTLE-01 (10 requirements)
    - Locked interface contracts for all Phase 6 implementation waves
  affects:
    - packages/models/src/sharpedge_models/no_vig.py (devig_shin_n_outcome to be added)
tech_stack:
  added:
    - sharpedge-venue-adapters package (hatchling build, pytest asyncio_mode=auto)
  patterns:
    - TDD London School RED-first: all test files fail at import time
    - src layout matching packages/data_feeds pattern
    - uv workspace member with workspace = true sources
key_files:
  created:
    - packages/venue_adapters/pyproject.toml
    - packages/venue_adapters/src/sharpedge_venue_adapters/__init__.py
    - packages/venue_adapters/tests/__init__.py
    - packages/venue_adapters/tests/conftest.py
    - packages/venue_adapters/tests/test_venue_adapter_protocol.py
    - packages/venue_adapters/tests/test_market_catalog.py
    - packages/venue_adapters/tests/test_kalshi_adapter.py
    - packages/venue_adapters/tests/test_polymarket_adapter.py
    - packages/venue_adapters/tests/test_sportsbook_adapter.py
    - packages/venue_adapters/tests/test_no_vig_n_outcome.py
    - packages/venue_adapters/tests/test_microstructure.py
    - packages/venue_adapters/tests/test_dislocation.py
    - packages/venue_adapters/tests/test_exposure_book.py
    - packages/venue_adapters/tests/test_settlement_ledger.py
  modified: []
decisions:
  - "Package scaffold follows packages/data_feeds src layout for consistency"
  - "devig_shin_n_outcome test imports from sharpedge_models.no_vig (correct location per research)"
  - "VenueCapability is frozen dataclass; protocol imports will fail until Wave 1"
  - "test_no_vig_n_outcome.py imports directly from sharpedge_models (not venue_adapters) since it extends existing no_vig.py"
metrics:
  duration_minutes: 3
  completed_date: "2026-03-14"
  tasks_completed: 2
  files_created: 14
  files_modified: 0
---

# Phase 06 Plan 01: RED Stubs — Phase 6 Wave 0 Interface Contracts Summary

**One-liner:** Package scaffold + 10 RED test stubs locking all Phase 6 interface contracts (VENUE-01 through SETTLE-01) before any implementation begins.

---

## What Was Built

### Task 1: Package Scaffold (commit 33f8cde)

Created `packages/venue_adapters/` as a uv workspace member:

- `pyproject.toml`: declares `sharpedge-venue-adapters` with dependencies on sharpedge-feeds, sharpedge-models, sharpedge-shared
- `src/sharpedge_venue_adapters/__init__.py`: empty package, importable from workspace venv
- `tests/__init__.py`: empty test init

`uv sync --all-packages` confirmed: `sharpedge-venue-adapters==0.1.0` registered as workspace member.

Verification: `uv run python -c "import sharpedge_venue_adapters"` — OK.

### Task 2: RED Test Stubs — Wave 0 Contracts (commit 005836c)

Wrote 11 files (conftest + 10 test files). All 10 test files fail at collection time with `ModuleNotFoundError` — the correct RED state.

| File | Requirement | What It Locks |
|------|-------------|---------------|
| test_venue_adapter_protocol.py | VENUE-01 | VenueAdapter Protocol, VenueCapability, CanonicalMarket, VenueFeeSchedule, SettlementState |
| test_market_catalog.py | VENUE-02 | MarketLifecycleState machine, InvalidTransitionError, MarketCatalog.upsert/get/transition |
| test_kalshi_adapter.py | VENUE-03 | KalshiAdapter wraps kalshi_client, satisfies VenueAdapter protocol, execution_supported=True |
| test_polymarket_adapter.py | VENUE-04 | PolymarketAdapter read_only=True, maker_rewards=True, CanonicalQuote.raw_format |
| test_sportsbook_adapter.py | VENUE-05 | OddsApiAdapter read_only=True, remaining_credits, InsufficientCreditsError at <50 credits |
| test_no_vig_n_outcome.py | PRICE-01 | devig_shin_n_outcome: N-outcome Shin devig, sums to 1.0, reduces implied probs |
| test_microstructure.py | MICRO-01 | fill_hazard_estimate, SpreadDepthMetrics, compute_spread_depth |
| test_dislocation.py | DISLO-01 | compute_consensus (inverse-spread-weighted), score_dislocation, DislocScore, stale flag |
| test_exposure_book.py | RISK-01 | ExposureBook, apply_drawdown_throttle, compute_allocation, venue concentration cap |
| test_settlement_ledger.py | SETTLE-01 | LedgerEntry frozen, replay_position_pnl, UTC-aware timestamps enforced |

---

## Verification

```
10 errors in 15.25s  (all ModuleNotFoundError — correct RED state)
10 test files exist (ls tests/test_*.py | wc -l == 10)
import sharpedge_venue_adapters → OK
```

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Self-Check: PASSED

All 14 created files verified present on disk. Both task commits (33f8cde, 005836c) confirmed in git log.
