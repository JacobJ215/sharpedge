---
phase: 06-multi-venue-quant-infrastructure
plan: 03
subsystem: venue-adapters
tags: [kalshi, polymarket, clob, prediction-markets, adapters, protocol]

requires:
  - phase: 06-02
    provides: VenueAdapter Protocol, CanonicalMarket, CanonicalOrderBook, VenueCapability, MarketLifecycleState dataclasses
  - phase: data_feeds
    provides: KalshiClient (KalshiConfig), PolymarketClient (PolymarketConfig) transport layer

provides:
  - KalshiAdapter wrapping KalshiClient — satisfies VenueAdapter protocol structurally
  - PolymarketAdapter wrapping PolymarketClient — read-only CLOB adapter
  - adapters/__init__.py re-exporting both adapters

affects:
  - 06-04 (quote normalization will consume both adapters)
  - 06-05 (microstructure modeling consumes orderbook from adapters)
  - 06-06 (dislocation detection consumes both adapters for cross-venue comparison)

tech-stack:
  added: []
  patterns:
    - "Structural protocol conformance: concrete class with matching method signatures, no inheritance from Protocol"
    - "Offline-safe adapters: all async methods return empty defaults when api_key=None or import fails"
    - "Transport config wrapping: KalshiConfig/PolymarketConfig constructed inside adapter to isolate auth logic"
    - "Tuple-typed bids/asks for frozen CanonicalOrderBook dataclass compatibility"

key-files:
  created:
    - packages/venue_adapters/src/sharpedge_venue_adapters/adapters/__init__.py
    - packages/venue_adapters/src/sharpedge_venue_adapters/adapters/kalshi.py
    - packages/venue_adapters/src/sharpedge_venue_adapters/adapters/polymarket.py
  modified: []

key-decisions:
  - "KalshiConfig wrapping inside KalshiAdapter preserves RSA-PSS signing logic in transport layer — adapter never touches auth"
  - "PolymarketConfig() default no-arg construction enables read-only mode without credentials"
  - "get_historical_snapshots() raises NotImplementedError in KalshiAdapter; returns [] in PolymarketAdapter (per plan spec)"
  - "CanonicalOrderBook bids/asks passed as tuple() not list to satisfy frozen dataclass constraint"

patterns-established:
  - "Adapter offline mode: wrap client construction in try/except ImportError; guard async methods with None check"
  - "Binary market bid/ask: yes_bid=YES_price, yes_ask=1-NO_price for complement-based spread"

requirements-completed:
  - VENUE-03
  - VENUE-04

duration: 3min
completed: 2026-03-14
---

# Phase 06 Plan 03: Canonical Venue Adapters Summary

**KalshiAdapter and PolymarketAdapter implemented as structural VenueAdapter Protocol implementations, wrapping transport-layer clients without duplicating auth or parsing logic, with offline-safe fallbacks throughout.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-14T16:20:44Z
- **Completed:** 2026-03-14T16:23:32Z
- **Tasks:** 2
- **Files modified:** 3 created

## Accomplishments

- KalshiAdapter satisfies `isinstance(adapter, VenueAdapter)` check; `execution_supported=True`, `read_only=False`; offline mode (api_key=None) returns empty lists without raising
- PolymarketAdapter satisfies `isinstance(adapter, VenueAdapter)` check; `read_only=True`, `maker_rewards=True`; PolymarketConfig() default construction enables no-credential read-only mode
- All 22 tests GREEN across test_venue_adapter_protocol, test_market_catalog, test_kalshi_adapter, test_polymarket_adapter

## Task Commits

Each task was committed atomically:

1. **Task 1: KalshiAdapter wrapping KalshiClient** - `7c6ac5a` (feat)
2. **Task 2: PolymarketAdapter wrapping PolymarketClient** - `16f028d` (feat)

## Files Created/Modified

- `packages/venue_adapters/src/sharpedge_venue_adapters/adapters/__init__.py` - Re-exports KalshiAdapter and PolymarketAdapter
- `packages/venue_adapters/src/sharpedge_venue_adapters/adapters/kalshi.py` - KalshiAdapter: protocol-conformant wrapper, offline-safe, 7% taker fee, NotImplementedError on historical snapshots
- `packages/venue_adapters/src/sharpedge_venue_adapters/adapters/polymarket.py` - PolymarketAdapter: read-only CLOB wrapper, YES/NO price spread mapping, empty historical snapshots

## Decisions Made

- KalshiAdapter wraps `KalshiConfig(api_key=api_key)` rather than passing api_key directly — KalshiClient requires a KalshiConfig object (not a plain string)
- PolymarketClient requires `PolymarketConfig()` at construction — instantiated with default args for offline/read-only mode
- `CanonicalOrderBook.bids/asks` passed as `tuple()` since the frozen dataclass rejects mutable `list` assignment
- `get_historical_snapshots()` signature matches Protocol exactly: `(market_id, start_utc, end_utc)` — plan's description used different args but Protocol is authoritative

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] PolymarketClient requires PolymarketConfig — not no-arg**
- **Found during:** Task 2 (PolymarketAdapter test run)
- **Issue:** Plan stated "PolymarketClient() — no required constructor args" but actual client requires `config: PolymarketConfig`
- **Fix:** Imported `PolymarketConfig` alongside `PolymarketClient`; constructed `PolymarketClient(config=PolymarketConfig())` using defaults
- **Files modified:** adapters/polymarket.py
- **Verification:** 5 tests GREEN after fix
- **Committed in:** 16f028d (Task 2 commit)

**2. [Rule 3 - Blocking] KalshiClient requires KalshiConfig — not api_key string**
- **Found during:** Task 1 review of kalshi_client.py
- **Issue:** Plan stated "KalshiClient(api_key=api_key)" but actual signature is `KalshiClient(config: KalshiConfig)`
- **Fix:** Imported `KalshiConfig`; constructed `KalshiConfig(api_key=api_key)` then `KalshiClient(config=config)`
- **Files modified:** adapters/kalshi.py
- **Verification:** 6 tests GREEN
- **Committed in:** 7c6ac5a (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 - blocking constructor signature mismatches)
**Impact on plan:** Both fixes required for functional adapters; no scope changes.

## Issues Encountered

- Protocol's `get_historical_snapshots` signature uses `(market_id, start_utc, end_utc)` while plan description used `(market_id)` — Protocol signature is authoritative; implemented with `(market_id, start_utc, end_utc)` to satisfy structural check.

## Next Phase Readiness

- Both adapters ready for Wave 3 consumption (quote normalization, microstructure, dislocation detection)
- KalshiAdapter.get_orderbook() wires to live Kalshi REST when api_key is set; no RSA-PSS signing yet (read-only orderbook endpoint is public)
- PolymarketAdapter.get_orderbook() queries CLOB by token_id — downstream consumers should pass token_id not condition_id

---
*Phase: 06-multi-venue-quant-infrastructure*
*Completed: 2026-03-14*
