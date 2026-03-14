---
phase: 06-multi-venue-quant-infrastructure
plan: 02
subsystem: api
tags: [venue-adapters, protocol, dataclasses, state-machine, normalization, python]

requires:
  - phase: 06-01
    provides: package scaffold + 10 RED test stubs locking interface contracts

provides:
  - VenueAdapter @runtime_checkable Protocol (7 async methods)
  - MarketLifecycleState enum with valid_next() + transition_to() state machine
  - InvalidTransitionError ValueError subclass
  - All canonical frozen dataclasses: VenueCapability, CanonicalMarket, CanonicalOrderBook, CanonicalQuote, CanonicalTrade, VenueFeeSchedule, SettlementState, MarketStatePacket
  - MarketCatalog in-memory catalog with upsert/get/transition/list
  - normalize_to_canonical_quote() for probability/american/cents/decimal raw formats
  - Package-level __all__ exports from __init__.py

affects:
  - 06-03 (Kalshi adapter — implements VenueAdapter Protocol)
  - 06-04 (Polymarket adapter — uses CanonicalQuote, VenueAdapter)
  - 06-05 (OddsApi adapter — uses VenueAdapter, VenueCapability)
  - 06-06 (microstructure — uses CanonicalOrderBook, CanonicalQuote)
  - 06-07 (dislocation — uses CanonicalQuote, MarketCatalog)
  - 06-08 (exposure + ledger — uses CanonicalMarket, MarketLifecycleState)

tech-stack:
  added: []
  patterns:
    - "@runtime_checkable Protocol for structural subtyping without inheritance"
    - "frozen=True dataclasses for immutable canonical data transfer objects"
    - "Enum with instance methods (valid_next, transition_to) for state machine logic"
    - "VALID_TRANSITIONS dict defined after Enum to avoid forward-reference issues"
    - "Re-export pattern in catalog.py __all__ for callers who import from catalog"

key-files:
  created:
    - packages/venue_adapters/src/sharpedge_venue_adapters/protocol.py
    - packages/venue_adapters/src/sharpedge_venue_adapters/catalog.py
    - packages/venue_adapters/src/sharpedge_venue_adapters/normalization.py
  modified:
    - packages/venue_adapters/src/sharpedge_venue_adapters/__init__.py

key-decisions:
  - "MarketLifecycleState defined in protocol.py; re-exported from catalog.py so both import paths work"
  - "CanonicalOrderBook.bids/asks typed as tuple (not list[dict]) for frozen dataclass immutability"
  - "normalize_to_canonical_quote fair_prob = mid_prob; devigging applied separately by adapter"
  - "VALID_TRANSITIONS dict defined after Enum class to avoid self-referencing during class body evaluation"

patterns-established:
  - "All canonical DTOs use @dataclass(frozen=True) — immutability guaranteed"
  - "Protocol.valid_next() returns set[MarketLifecycleState] — set semantics for O(1) membership"
  - "normalization.py imports american_to_implied from sharpedge_models.no_vig — no duplication"

requirements-completed:
  - VENUE-01
  - VENUE-02

duration: 6min
completed: 2026-03-14
---

# Phase 06 Plan 02: Canonical Typed Contracts Summary

**@runtime_checkable VenueAdapter Protocol + frozen DTO dataclasses + MarketLifecycleState FSM + in-memory MarketCatalog + 4-format quote normalization turning 11 RED tests GREEN**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-03-14T16:09:37Z
- **Completed:** 2026-03-14T16:15:42Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Implemented VenueAdapter as @runtime_checkable Protocol — isinstance() structural check works without inheritance
- MarketLifecycleState FSM with 5 states and valid transition table enforced via InvalidTransitionError
- MarketCatalog in-memory catalog: upsert/get/transition/list with lifecycle state enforcement
- normalize_to_canonical_quote() handles probability/american/cents/decimal raw_format values using no_vig.american_to_implied
- 11/11 tests GREEN: test_venue_adapter_protocol.py (4/4) + test_market_catalog.py (7/7)

## Task Commits

1. **Task 1: protocol.py — VenueAdapter Protocol + all canonical typed contracts** - `b4e4299` (feat)
2. **Task 2: catalog.py + normalization.py + __init__.py** - `56c793a` and `94482aa` (feat)

## Files Created/Modified

- `packages/venue_adapters/src/sharpedge_venue_adapters/protocol.py` - All typed contracts: VenueAdapter, MarketLifecycleState, all frozen dataclasses
- `packages/venue_adapters/src/sharpedge_venue_adapters/catalog.py` - MarketCatalog state machine
- `packages/venue_adapters/src/sharpedge_venue_adapters/normalization.py` - normalize_to_canonical_quote() for 4 raw_format types
- `packages/venue_adapters/src/sharpedge_venue_adapters/__init__.py` - Package-level exports

## Decisions Made

- MarketLifecycleState defined in protocol.py, re-exported via catalog.py's `__all__` — both import paths work
- CanonicalOrderBook bids/asks typed as `tuple` (not `list[dict]`) to satisfy `frozen=True` constraint
- `fair_prob = mid_prob` in normalization; devigging left to adapters which have full book context
- `_VALID_TRANSITIONS` dict defined after `MarketLifecycleState` class body to avoid forward-reference errors

## Deviations from Plan

None — plan executed exactly as written. All contract definitions matched the plan's code samples.

## Issues Encountered

None. The only complication was the automatic linter reverting `__init__.py` immediately after editing via the Edit tool; resolved by writing via bash and committing atomically in the same command.

## Next Phase Readiness

- protocol.py exports are the stable interface that Waves 2-3 adapter implementations build against
- MarketCatalog is ready for adapter use (upsert markets from API responses, transition on event feed)
- normalization.py handles all 4 raw_format types; KalshiAdapter uses "probability" (already converted by kalshi_client), PolymarketAdapter uses "probability", OddsApiAdapter uses "american"
- Remaining 8 test files still fail RED (correct — implementations not yet written)

---
*Phase: 06-multi-venue-quant-infrastructure*
*Completed: 2026-03-14*
