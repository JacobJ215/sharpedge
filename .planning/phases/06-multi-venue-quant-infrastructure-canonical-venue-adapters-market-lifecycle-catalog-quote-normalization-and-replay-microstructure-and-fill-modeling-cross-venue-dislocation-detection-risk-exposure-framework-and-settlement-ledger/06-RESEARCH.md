# Phase 6: Multi-Venue Quant Infrastructure — Research

**Researched:** 2026-03-14
**Domain:** Multi-venue event market data adapters, microstructure modeling, risk/exposure framework, settlement ledger
**Confidence:** HIGH (architecture patterns), MEDIUM (Polymarket CLOB specifics), HIGH (sportsbook API)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Architectural Principles (ALL LOCKED)
- EV-first decisioning, not heuristic confidence-only scoring
- Explicit cost modeling: fees, spread, slippage, and liquidity at every decision point
- Calibration of probabilities before any capital allocation decision
- Deterministic replay: every market-state snapshot must be replayable from stored events
- Thin transport layers: heavy modeling isolated behind stable typed contracts
- Explicit risk budgets, exposure limits, and promotion gates before any production use
- No OHLCV-only bar-series assumptions — these are event markets, not price charts

#### Venue Scope (LOCKED)
- Kalshi: binary event contracts, exchange-style CLOB, venue API, fee-aware EV
- Polymarket: CLOB market data, outcome mapping, wallet/auth abstraction, reward metadata
- Sportsbooks: read-only odds ingestion FIRST, then line shopping, then no-vig normalization
- Sportsbook execution is explicitly OUT OF SCOPE for Phase 6 (legal/operational constraints)

#### Canonical Adapter Contract (LOCKED interface, flexible implementation)
Each adapter must expose:
- `listMarkets()`, `getMarketDetails()`, `getOrderBook()`, `getTrades()`
- `getHistoricalSnapshots()`, `getFeesAndLimits()`, `getSettlementState()`
- Capability flags: `read_only`, `streaming_quotes`, `streaming_orderbook`, `execution_supported`, `maker_rewards`, `settlement_feed`
- `placeOrder()` / `cancelOrder()` only for Kalshi (already partially built), NOT sportsbooks

#### Bounded Contexts to Implement (LOCKED scope)
1. **Market Catalog & Lifecycle** — Event, Market, Outcome, MarketLifecycleState, VenueContractRef
2. **Venue Connectivity** — VenueAdapter, VenueCapability, VenueAuthContext, VenueFeeSchedule, VenueRateLimitPolicy
3. **Market Data & Quote Normalization** — CanonicalQuote, CanonicalOrderBook, CanonicalOddsSnapshot, MarketStatePacket
4. **Probability & Pricing** — NoVigBook, PricingDecision, EdgeEstimate (builds on Phase 1/5, no duplication)
5. **Risk, Exposure & Portfolio Construction** — ExposureBook, RiskLimit, CorrelationBucket, AllocationDecision
6. **Settlement & Ledger** — LedgerEntry, PositionLot, SettlementEvent, PayoutRecord, ReconciliationReport

#### Quant Models to Add (LOCKED)
- **Fair Probability Engine enhancement**: multi-outcome no-vig normalization, consensus blending across venues — builds on Phase 1's ev_calculator.py, extends not replaces
- **Market Microstructure Model**: spread/depth modeling, fill-hazard estimation, passive vs. aggressive execution comparison — NEW
- **Cross-Venue Dislocation Model**: consensus deviation scoring, stale-quote detection, paired exposure checks — NEW
- **Event-State & Time-To-Resolution Model**: hazard-style event-time features, regime by market phase — NEW
- **Allocation & Exposure Model**: fractional Kelly variants, drawdown-aware throttles, venue concentration caps — NEW

#### Settlement & Replay (LOCKED)
- Event-sourced settlement replay must be deterministic
- Fee and rebate decomposition required
- Pre-trade vs. post-trade attribution tracking
- Calibration drift and execution drift decomposition

#### Model Governance (LOCKED before any model moves to decisioning)
- Time-correct train/val/test splits required
- Walk-forward evidence required (Phase 5 provides the backtester)
- Calibration reports required
- Cost and fee sensitivity analysis required
- Venue-specific drift monitoring required

#### Starting Point (LOCKED)
- Domain contracts and adapter interfaces FIRST
- No UI work before domain layer is locked
- No execution automation before research loop is validated
- Sportsbook adapter is read-only only

### Claude's Discretion
- Exact file/module layout within existing `packages/` and `apps/` structure
- Whether to create a new `packages/venue_adapters/` or extend `packages/data_feeds/`
- Internal data structures for MarketStatePacket beyond the interface contract
- Test framework choices (use existing pytest infrastructure)
- Whether CorrelationBucket reuses Phase 3's pm_correlation.py or is a separate implementation
- Specific Polymarket CLOB API endpoints and auth flow details

### Deferred Ideas (OUT OF SCOPE)
- Sportsbook execution automation (legal/operational constraints — later phase)
- Paper trading / shadow-decision mode (Phase 5 of proposal = later SharpEdge phase)
- Research & Feature Engineering bounded context (covered by Phase 5)
- Operator review workflows / alert system changes (Phase 4 API layer handles)
- Full Research & Feature Engineering pipeline (walk-forward already in Phase 5)
- FinnAI code reuse (explicitly forbidden by proposal)
</user_constraints>

---

## Summary

Phase 6 adds the institutional-grade multi-venue infrastructure layer that Phases 1–5 deliberately deferred. The core design question is whether to extend `packages/data_feeds/` or create a new `packages/venue_adapters/` package. **Recommendation: create `packages/venue_adapters/`** — the existing `packages/data_feeds/` is a transport client layer (httpx-based wire clients), whereas Phase 6 adds a domain abstraction layer (typed contracts, normalization, lifecycle, risk). These are different bounded contexts. The existing `kalshi_client.py` and `polymarket_client.py` become the transport tier that the new adapters wrap.

Phase 5 builds the CalibrationStore, EnsembleManager, and walk-forward backtester. Phase 6 is the decisioning layer ON TOP: it adds canonical market state, multi-venue price normalization, exposure accounting, and settlement replay. The two phases do not overlap if Phase 6 imports Phase 5 artifacts (confidence_mult from CalibrationStore, simulate_bankroll from monte_carlo) without re-implementing them.

The six bounded contexts map naturally to six modules within `packages/venue_adapters/`. Each stays under 500 lines by keeping the interface contract in one file and the implementation in another. The settlement ledger is the only component that needs append-only persistence; a simple Supabase table with an insert-only policy (no UPDATE/DELETE) satisfies the deterministic replay requirement without introducing a dedicated event sourcing library.

**Primary recommendation:** Create `packages/venue_adapters/` with six sub-modules matching the six bounded contexts. Use The Odds API for sportsbook ingestion (unified endpoint, no per-book auth). Wrap existing `kalshi_client.py` and `polymarket_client.py` behind the canonical `VenueAdapter` protocol. Implement Shin method for multi-outcome no-vig (the `shin` PyPI package exists but the codebase already has Shin implemented in `no_vig.py` — extend that, do not add a dependency). Use fractional Kelly (half-Kelly, quarter-Kelly) already present in `ev_calculator.py` as the allocation base, add drawdown throttle on top.

---

## Integration Points with Phases 1–5

This is the most critical planning input. Phase 6 must extend, never re-implement.

### What Phase 6 Reuses (Do Not Duplicate)

| Existing Module | Location | What Phase 6 Uses |
|-----------------|----------|-------------------|
| `kalshi_client.py` | `packages/data_feeds/` | Transport tier wrapped behind `VenueAdapter` |
| `polymarket_client.py` | `packages/data_feeds/` | Transport tier wrapped behind `VenueAdapter` |
| `no_vig.py` | `packages/models/` | `devig_shin`, `devig_power`, `calculate_consensus_fair_odds`, `calculate_no_vig` — extend for N-outcome |
| `ev_calculator.py` | `packages/models/` | `calculate_ev`, `EVCalculation`, Kelly fractions — allocation model delegates to these |
| `monte_carlo.py` | `packages/models/` | `simulate_bankroll` — ruin probability feeds exposure throttle |
| `alpha.py` | `packages/models/` | `compose_alpha`, `BettingAlpha` — Phase 6 EdgeEstimate feeds alpha score, does not replace it |
| `calibration_store.py` | `packages/models/` | `confidence_mult` — Phase 6 allocation model reads this, does not recalibrate |
| `pm_correlation.py` | `packages/agent_pipeline/` | CorrelationBucket references Phase 3 entity-correlation patterns (can extend, not replace) |
| `clv.py` | `packages/models/` | CLV benchmark for cross-book line shopping |

### What Phase 6 Adds New

| New Module | Bounded Context | Location (recommendation) |
|------------|----------------|--------------------------|
| `venue_adapters/protocol.py` | Venue Connectivity | `packages/venue_adapters/` |
| `venue_adapters/kalshi_adapter.py` | Venue Connectivity | wraps `kalshi_client.py` |
| `venue_adapters/polymarket_adapter.py` | Venue Connectivity | wraps `polymarket_client.py` |
| `venue_adapters/odds_api_adapter.py` | Venue Connectivity | wraps The Odds API |
| `venue_adapters/catalog.py` | Market Catalog & Lifecycle | |
| `venue_adapters/normalization.py` | Market Data & Quote Normalization | |
| `venue_adapters/microstructure.py` | Probability & Pricing | |
| `venue_adapters/dislocation.py` | Cross-Venue Dislocation | |
| `venue_adapters/exposure.py` | Risk, Exposure & Portfolio Construction | |
| `venue_adapters/ledger.py` | Settlement & Ledger | |

---

## Standard Stack

### Core (existing, already in workspace)

| Library | Version | Purpose | Role in Phase 6 |
|---------|---------|---------|-----------------|
| httpx | >=0.27 | async HTTP client | transport tier (already in data_feeds) |
| pydantic | >=2.0 | validation at system boundaries | canonical quote/orderbook validation |
| numpy | latest | numerical operations | fill-hazard, microstructure calcs |
| scipy | latest | optimization | Shin solver, Kelly variants |
| pytest | latest | test framework | all RED stubs |

### New Dependencies to Add (Phase 6 only)

| Library | Version | Purpose | Why Not Hand-Roll |
|---------|---------|---------|-------------------|
| `the-odds-api` (via httpx, no client library needed) | REST v4 | Sportsbook odds ingestion | No official Python client; direct httpx is sufficient and already in stack |

No new major dependencies are required. The Odds API is a pure REST API callable with the existing httpx client. Polymarket's `py-clob-client` PyPI package EXISTS but adds Polygon/EIP-712 signing complexity that is not needed for read-only market data access — the existing `polymarket_client.py` already handles CLOB read endpoints correctly. Do not add `py-clob-client` unless Polymarket trading is scoped in.

### Installation

```bash
# No new packages needed — all capabilities available in current workspace
uv sync --all-packages
```

If The Odds API key management needs a dedicated env var:
```bash
# .env (never committed)
ODDS_API_KEY=your_key_here
```

---

## Architecture Patterns

### Recommended Package Structure

```
packages/venue_adapters/
├── pyproject.toml                    # depends on sharpedge-feeds, sharpedge-models
├── src/
│   └── sharpedge_venue_adapters/
│       ├── __init__.py
│       ├── protocol.py              # VenueAdapter Protocol, VenueCapability, typed contracts (<500 lines)
│       ├── catalog.py               # MarketCatalog, lifecycle state machine (<500 lines)
│       ├── normalization.py         # CanonicalQuote, CanonicalOrderBook, odds converters (<500 lines)
│       ├── microstructure.py        # FillHazardModel, SpreadDepthMetrics (<500 lines)
│       ├── dislocation.py           # DislocScore, stale-quote detection (<500 lines)
│       ├── exposure.py              # ExposureBook, AllocationDecision, RiskLimit (<500 lines)
│       ├── ledger.py                # LedgerEntry, SettlementEvent, replay (<500 lines)
│       └── adapters/
│           ├── __init__.py
│           ├── kalshi.py            # KalshiAdapter implements VenueAdapter (<300 lines)
│           ├── polymarket.py        # PolymarketAdapter implements VenueAdapter (<300 lines)
│           └── odds_api.py          # OddsApiAdapter implements VenueAdapter (read-only) (<300 lines)
└── tests/
    └── ...
```

### Pattern 1: VenueAdapter as a Structural Protocol

**What:** Use `typing.Protocol` (structural subtyping) for the canonical adapter interface. Any class that implements the required methods satisfies the contract without explicit inheritance.

**When to use:** This pattern lets each venue implementation stand alone (no base class coupling), and lets tests substitute a mock with just the methods exercised by that test.

```python
# Source: typing.Protocol (Python 3.8+ stdlib)
# packages/venue_adapters/src/sharpedge_venue_adapters/protocol.py
from typing import Protocol, runtime_checkable
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class VenueCapability:
    read_only: bool
    streaming_quotes: bool
    streaming_orderbook: bool
    execution_supported: bool
    maker_rewards: bool
    settlement_feed: bool

@runtime_checkable
class VenueAdapter(Protocol):
    venue_id: str
    capabilities: VenueCapability

    async def list_markets(self, status: str = "open") -> list["CanonicalMarket"]: ...
    async def get_market_details(self, market_id: str) -> "CanonicalMarket | None": ...
    async def get_orderbook(self, market_id: str) -> "CanonicalOrderBook": ...
    async def get_trades(self, market_id: str, since: datetime | None = None) -> list["CanonicalTrade"]: ...
    async def get_historical_snapshots(self, market_id: str) -> list["MarketStatePacket"]: ...
    async def get_fees_and_limits(self) -> "VenueFeeSchedule": ...
    async def get_settlement_state(self, market_id: str) -> "SettlementState | None": ...
```

### Pattern 2: MarketLifecycleState as an Enum State Machine

**What:** Each market has an explicit lifecycle: `OPEN -> SUSPENDED -> CLOSED -> SETTLED | CANCELLED`. State transitions are validated before writes to prevent catalog corruption.

**When to use:** All venue-specific status strings are mapped to the canonical enum on ingestion, so downstream code never branches on venue-specific strings.

```python
from enum import Enum

class MarketLifecycleState(Enum):
    OPEN = "open"
    SUSPENDED = "suspended"
    CLOSED = "closed"          # trading halted, result pending
    SETTLED = "settled"        # result confirmed, payouts complete
    CANCELLED = "cancelled"    # void — stakes returned

VALID_TRANSITIONS: dict[MarketLifecycleState, set[MarketLifecycleState]] = {
    MarketLifecycleState.OPEN: {MarketLifecycleState.SUSPENDED, MarketLifecycleState.CLOSED, MarketLifecycleState.CANCELLED},
    MarketLifecycleState.SUSPENDED: {MarketLifecycleState.OPEN, MarketLifecycleState.CLOSED, MarketLifecycleState.CANCELLED},
    MarketLifecycleState.CLOSED: {MarketLifecycleState.SETTLED, MarketLifecycleState.CANCELLED},
    MarketLifecycleState.SETTLED: set(),    # terminal
    MarketLifecycleState.CANCELLED: set(),  # terminal
}
```

### Pattern 3: CanonicalQuote — Unified Probability Representation

**What:** All venue prices are normalized to a `CanonicalQuote` that carries both the raw venue representation AND the probability representation. Odds conversions are already implemented in `no_vig.py` — import, do not duplicate.

```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class CanonicalQuote:
    venue_id: str
    market_id: str
    outcome_id: str
    # Raw venue price (varies by venue type)
    raw_bid: float          # Kalshi: cents/100; Polymarket: 0-1 USDC; Sportsbook: American int
    raw_ask: float
    raw_format: str         # "probability", "american", "decimal", "cents"
    # Canonical probability (always 0.0–1.0, no-vig-adjusted)
    fair_prob: float        # derived via devig (power method default)
    mid_prob: float         # (bid_prob + ask_prob) / 2, NOT devigged — shows market price
    spread_prob: float      # ask_prob - bid_prob
    # Cost metadata
    maker_fee_rate: float   # e.g. 0.0 for Kalshi maker, 0.07 for Kalshi taker
    taker_fee_rate: float
    timestamp_utc: str      # ISO-8601 with timezone
```

### Pattern 4: Append-Only Settlement Ledger

**What:** Every financial event (fill, fee, rebate, settlement, adjustment) is an immutable `LedgerEntry` inserted to Supabase with `GENERATED ALWAYS AS IDENTITY`. No UPDATE or DELETE operations. Replay is achieved by filtering all entries for a position chronologically and summing.

**Why not the `eventsourcing` PyPI library:** It adds 15+ indirect dependencies and enforces an aggregate/repository abstraction that conflicts with the existing Supabase-first pattern. The Supabase insert-only pattern IS event sourcing at the level of complexity this phase needs.

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

LedgerEventType = Literal[
    "FILL", "FEE", "REBATE", "SETTLEMENT", "ADJUSTMENT", "POSITION_OPENED", "POSITION_CLOSED"
]

@dataclass(frozen=True)
class LedgerEntry:
    # Surrogate ID assigned by DB (GENERATED ALWAYS AS IDENTITY)
    entry_id: int | None         # None before insert
    event_type: LedgerEventType
    venue_id: str
    market_id: str
    position_lot_id: str         # UUID for a specific fill lot
    amount_usdc: float           # positive = credit, negative = debit
    fee_component: float         # isolated fee portion (0 if not FEE event)
    rebate_component: float      # isolated rebate (0 if not REBATE event)
    price_at_event: float        # canonical probability at event time
    occurred_at: datetime        # venue-reported event time (UTC)
    recorded_at: datetime        # when SharpEdge wrote this entry (UTC)
    notes: str = ""
```

### Pattern 5: Fill-Hazard Model for Binary Event Markets

**What:** Estimate fill probability of a limit order at price p given observed orderbook depth d(p) and time-to-event TTR. This is NOT machine learning — it is a closed-form hazard estimate that can be computed in <1ms.

**Core insight:** For binary event markets (Kalshi, Polymarket), fill probability at a limit price is primarily a function of: (1) spread to best ask (distance from best), (2) volume depth at the price level, and (3) time-urgency (passive orders near resolution often go unfilled as market makers widen spreads).

```python
import math

def fill_hazard_estimate(
    limit_price_prob: float,   # where we want to buy (in probability units)
    best_ask_prob: float,       # current best ask
    depth_at_price: int,        # contracts available at or better than limit_price
    ttr_hours: float,           # time-to-resolution in hours
    taker_fee_rate: float,      # e.g. 0.07 for Kalshi
) -> float:
    """Returns estimated fill probability [0, 1].

    Model: exponential decay in distance from best ask, discounted by
    inverse time-to-resolution (passive orders near resolution fill rarely).
    """
    distance = abs(limit_price_prob - best_ask_prob)
    if distance < 1e-6:
        return 0.95  # at-the-market, near-certain fill

    depth_factor = min(1.0, depth_at_price / 100.0)     # normalize to 100 contracts
    urgency_factor = 1.0 / (1.0 + math.exp(-ttr_hours))  # sigmoid: low TTR = low fill prob
    passive_discount = math.exp(-5.0 * distance)          # exponential decay

    return min(0.95, passive_discount * depth_factor * urgency_factor)
```

**Confidence: MEDIUM** — this is a simplified model appropriate for Phase 6. Academic papers (Avellaneda-Stoikov, Gueant) provide more rigorous market-maker models but require calibration data not yet available.

### Pattern 6: Cross-Venue Dislocation Detection

**What:** For a given underlying event, compute consensus probability from all available venues (weighted by inverse spread as a liquidity proxy), then score each venue by its deviation from consensus.

```python
@dataclass(frozen=True)
class DislocScore:
    market_id: str                   # canonical event identifier (cross-venue)
    venue_id: str
    venue_mid_prob: float            # this venue's current mid price
    consensus_prob: float            # weighted consensus across all venues
    disloc_bps: float                # deviation in basis points (|venue - consensus| * 10000)
    is_stale: bool                   # True if quote older than stale_threshold_seconds
    stale_threshold_seconds: int = 300

def compute_consensus(
    quotes: list[CanonicalQuote],
    stale_threshold_seconds: int = 300,
) -> float:
    """Inverse-spread-weighted consensus probability."""
    weights = []
    probs = []
    for q in quotes:
        if q.spread_prob < 1e-6:
            continue
        w = 1.0 / q.spread_prob      # tighter spread = higher weight
        weights.append(w)
        probs.append(q.mid_prob)
    if not weights:
        return sum(q.mid_prob for q in quotes) / len(quotes)
    total = sum(weights)
    return sum(p * w / total for p, w in zip(probs, weights))
```

### Pattern 7: Fractional Kelly with Drawdown Throttle

**What:** Extend the existing `size_position` node's half-Kelly with: (1) venue concentration cap (max X% of exposure on any single venue), (2) correlated-outcome netting (reduce position when correlated exposure exists), (3) drawdown throttle (scale down when current drawdown exceeds threshold).

**Integration:** Phase 6's `AllocationDecision` calls `simulate_bankroll` from `monte_carlo.py` (already implemented). It does NOT re-implement Monte Carlo.

```python
@dataclass(frozen=True)
class AllocationDecision:
    market_id: str
    venue_id: str
    kelly_full: float           # from ev_calculator.calculate_ev
    kelly_half: float           # standard half-Kelly starting point
    venue_concentration_cap: float   # max fraction on this venue
    correlation_discount: float      # multiplier [0, 1] from CorrelationBucket
    drawdown_throttle: float         # multiplier [0, 1] based on current drawdown
    recommended_fraction: float      # kelly_half * min(caps and discounts)
    ruin_probability: float          # from monte_carlo.simulate_bankroll

def apply_drawdown_throttle(
    current_drawdown: float,   # current drawdown as fraction (e.g. 0.15 = 15% DD)
    dd_threshold: float = 0.10,
    dd_max: float = 0.25,
) -> float:
    """Returns multiplier in [0.25, 1.0]. Full at threshold, quarter at max."""
    if current_drawdown <= dd_threshold:
        return 1.0
    slope = (current_drawdown - dd_threshold) / (dd_max - dd_threshold)
    return max(0.25, 1.0 - 0.75 * min(1.0, slope))
```

### Anti-Patterns to Avoid

- **Duplicating odds conversion logic:** `no_vig.py` already has `american_to_implied`, `implied_to_american`, `american_to_decimal`. Import these; never re-implement.
- **Building a custom event sourcing framework:** Supabase insert-only for `LedgerEntry` is sufficient. The `eventsourcing` PyPI package is overpowered and adds significant dependency weight.
- **Parsing Kalshi cent prices directly:** `kalshi_client.py` already converts cents → float probability in `_parse_market`. The adapter should use the parsed `KalshiMarket` objects, not raw API responses.
- **Using the `py-clob-client` PyPI package for read-only Polymarket data:** The existing `polymarket_client.py` already handles all read endpoints correctly. `py-clob-client` adds EIP-712/Polygon signing complexity that is only needed for order placement.
- **Putting the catalog in-memory only:** The MarketCatalog must write to Supabase for lifecycle state to survive restarts and support deterministic replay.

---

## Venue API Details

### Kalshi API (HIGH confidence — existing client works)

| Property | Value |
|----------|-------|
| Base URL | `https://trading-api.kalshi.com/trade-api/v2` |
| Auth (public) | None required for market data |
| Auth (trading) | `KALSHI-ACCESS-KEY` + `KALSHI-ACCESS-TIMESTAMP` + `KALSHI-ACCESS-SIGNATURE` (RSA-PSS-SHA256) |
| Rate limits | Basic tier: 20 read/sec, 10 write/sec |
| Orderbook endpoint | `GET /trade-api/v2/markets/{ticker}/orderbook` |
| Prices | `yes_bid`, `yes_ask`, `no_bid`, `no_ask` in cents (0–99), already parsed to float in `kalshi_client.py` |
| Fee rate | 7% of winnings (`KALSHI_FEE_RATE = 0.07` in `kalshi_executor.py`) |
| Contract resolution | `result` field: `"yes"`, `"no"`, or `None` (unsettled) |

**Phase 6 gap in existing client:** `kalshi_client.py` has no `get_historical_snapshots()` or `get_settlement_state()`. These need to be added to the `KalshiAdapter` wrapper (not to `kalshi_client.py` itself).

**Kalshi historical data endpoint (MEDIUM confidence):** `GET /trade-api/v2/markets/{ticker}/candlesticks` or similar — verify against current Kalshi docs before implementing. The existing client does not expose this.

### Polymarket CLOB API (MEDIUM confidence)

| Property | Value |
|----------|-------|
| Gamma API base | `https://gamma-api.polymarket.com` |
| CLOB API base | `https://clob.polymarket.com` |
| Auth (read) | No authentication required for orderbook, prices, spreads |
| Auth (trading) | L1: EIP-712 private key; L2: HMAC-SHA256 derived credentials |
| Rate limit | ~100 requests/minute (public endpoints) |
| Orderbook endpoint | `GET /book?token_id={token_id}` |
| Market list | Gamma API: `GET /markets?active=true&limit=100` |
| Price format | USDC (0.0 to 1.0 float), matching probability directly |
| Rewards | Maker rewards metadata in market data — relevant to reward-aware quoting |

**Phase 6 gap in existing client:** `polymarket_client.py` uses `hmac.new()` which should be `hmac.new()` — verify this works (MEDIUM confidence, could be `hmac.new` is not standard; should be `hmac.HMAC()` or `hmac.new()`). The `_build_auth_headers` method uses timestamp-only HMAC, which may not match current Polymarket L2 spec. Phase 6 should verify auth for any trading endpoints before implementing, but read-only endpoints need no auth fix.

**Polymarket token_id vs condition_id distinction:** Each market has one `condition_id` but multiple `token_id`s (one per outcome). The CLOB orderbook is queried by `token_id`, not `condition_id`. The existing `polymarket_client.py` captures `token_id` in `PolymarketOutcome.token_id` — the adapter must use this correctly.

### The Odds API — Sportsbook Line Shopping (HIGH confidence)

| Property | Value |
|----------|-------|
| Base URL | `https://api.the-odds-api.com/v4` |
| Auth | Query param: `?apiKey={ODDS_API_KEY}` |
| Rate limit | No per-second limit documented; quota-based (credits per request) |
| Sports endpoint | `GET /sports` — no quota cost |
| Odds endpoint | `GET /sports/{sport_key}/odds?regions=us&markets=h2h,spreads,totals&bookmakers=draftkings,fanduel,betmgm,pinnacle` |
| Supported books | DraftKings, FanDuel, BetMGM, Caesars, Pinnacle, BetRivers, Unibet, Bovada, William Hill US |
| Odds format | `?oddsFormat=american` returns American odds as integers |
| Quota cost | 1 credit per market-bookmaker combination per request |
| Historical odds | `GET /sports/{sport_key}/odds-history` — 10 credits/market, PAID plans only |
| Response structure | `[{id, sport_key, home_team, away_team, commence_time, bookmakers: [{key, markets: [{key: "spreads", outcomes: [{name, price, point}]}]}]}]` |

**Pinnacle is the sharp-book reference:** Use Pinnacle odds as the consensus benchmark for no-vig calculation when available. The existing `find_ev_opportunities()` in `no_vig.py` already implements this logic — the `OddsApiAdapter` feeds into it.

**Rate limit management:** The Odds API is credit-based. A dedicated `VenueRateLimitPolicy` dataclass should track remaining credits (returned in `X-Requests-Remaining` response header) and implement backoff when credits are low.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-outcome devigging | Custom Shin solver | `no_vig.py` `devig_shin()` — already implemented with scipy brentq | Edge cases in N-outcome normalization are already handled |
| Odds conversion (American/decimal/probability) | Custom converters | `no_vig.py` `american_to_implied()`, `implied_to_american()`, `american_to_decimal()` | Already tested, imported into new package |
| Kelly sizing | Custom formula | `ev_calculator.py` `EVCalculation.kelly_half` + `size_position.py` | Already calibrated with edge floor |
| Bankroll ruin simulation | Custom Monte Carlo | `monte_carlo.py` `simulate_bankroll()` | Thread-safe, 2000 paths, already tested |
| Append-only event store | Custom event sourcing framework | Supabase insert-only policy (no UPDATE/DELETE on ledger table) | Simpler, consistent with existing Supabase pattern |
| Kalshi RSA-PSS signing | Custom crypto | `kalshi_client.py` `_rsa_pss_sign()` | Already implemented with `cryptography` package |
| PM correlation scoring | Custom correlation | Phase 3's `pm_correlation.py` `compute_entity_correlation()` | CorrelationBucket can delegate to this |
| CLV tracking | Custom closing-line calc | `clv.py` `calculate_clv()` | Already handles American odds CLV |

**Key insight:** Phase 6's value is the integration layer and the NEW bounded contexts (microstructure, dislocation, exposure, ledger). Avoid the trap of rebuilding what Phases 1–5 already delivered correctly.

---

## Common Pitfalls

### Pitfall 1: Kalshi vs. Polymarket Price Units
**What goes wrong:** Kalshi API returns prices in cents (integer 0–99), while Polymarket uses float 0.0–1.0. Code that mixes these without normalization produces nonsensical probabilities.
**Why it happens:** Both markets express binary YES probability but with different representations.
**How to avoid:** The `CanonicalQuote.raw_format` field explicitly tracks the source format. `KalshiAdapter` converts cents→probability in `list_markets()` using the existing `_parse_market()` method (which divides by 100). `PolymarketAdapter` passes float prices through unchanged.
**Warning signs:** Any probability outside [0, 1] in a CanonicalQuote is a unit bug.

### Pitfall 2: Multi-Outcome Shin Method vs. Two-Way Shin
**What goes wrong:** The existing `devig_shin()` in `no_vig.py` only handles two-outcome markets (binary YES/NO). Sportsbook markets often have three outcomes (home/draw/away in soccer) or N outcomes (championship futures). Applying two-way Shin to a three-outcome market produces incorrect results.
**Why it happens:** The two-way solver optimizes a scalar z; the N-outcome Shin requires an iterative root-finding for a different equation.
**How to avoid:** Extend `no_vig.py` with `devig_shin_n_outcome(odds_list: list[int]) -> list[float]`. The algorithm: iterate Newton's method on `sum(shin_fair(implied_i, z)) = 1` for N outcomes. The `shin` PyPI package (github.com/mberk/shin) has a reference implementation — do not import it, use it as a reference for the N-outcome extension.

### Pitfall 3: Stale Quote Window Miscalibration
**What goes wrong:** A quote is flagged as "stale" if its timestamp is >5 minutes old, but different venues update at different cadences. Kalshi CLOB updates in seconds; The Odds API updates every 30–60 seconds for pre-game lines; sportsbooks may not update lines for hours during low-activity periods.
**Why it happens:** Single global stale threshold applied across venues.
**How to avoid:** `VenueFeeSchedule` should include `expected_quote_refresh_seconds` per venue. `DislocScore.stale_threshold_seconds` should default to the venue-specific value, not a global constant.

### Pitfall 4: Ledger Replay Without UTC-Aware Timestamps
**What goes wrong:** Replaying settlement events in chronological order fails or produces wrong PnL if some timestamps are timezone-naive.
**Why it happens:** Supabase returns timestamps as UTC strings, but Python `datetime.fromisoformat()` on timestamps WITHOUT timezone info creates naive datetimes that compare incorrectly with aware datetimes.
**How to avoid:** All `LedgerEntry` timestamps must use `datetime.now(timezone.utc)`. Parse Supabase strings with `.replace("Z", "+00:00")` (same pattern already used in `kalshi_client.py` and `polymarket_client.py`). This is a known issue from STATE.md (`datetime.utcnow()` was already fixed in Phase 1).

### Pitfall 5: ExposureBook State During Concurrent Scanning
**What goes wrong:** Two concurrent scan jobs (Kalshi scanner + Polymarket scanner) read `ExposureBook.open_positions` simultaneously and both conclude there is capacity for a new position — resulting in double-exposure.
**Why it happens:** ExposureBook is shared state without a write lock.
**How to avoid:** ExposureBook reads come from Supabase (Supabase is the source of truth for open positions), and position capacity checks use a row-level advisory lock or an optimistic update with a unique constraint. In practice for Phase 6 (read-only / simulation), this matters only when recording simulated allocations — ensure the ledger insert is atomic.

### Pitfall 6: The Odds API Credit Exhaustion
**What goes wrong:** A bug in the scanner loop calls the odds endpoint hundreds of times, exhausting the daily/monthly credit quota.
**Why it happens:** The Odds API returns remaining credits in `X-Requests-Remaining` header but clients often ignore it.
**How to avoid:** `OddsApiAdapter` MUST read and log `X-Requests-Remaining` after every response. Implement a circuit-breaker: if remaining credits drop below 50, pause and alert. Track remaining credits in a module-level variable that persists across calls within a process lifetime.

### Pitfall 7: VenueAdapter Protocol Drift
**What goes wrong:** One adapter (e.g., `OddsApiAdapter`) omits a method required by `VenueAdapter` Protocol, causing silent `AttributeError` at runtime instead of a type error at import time.
**Why it happens:** Python `Protocol` with `@runtime_checkable` only checks for method existence, not signature compatibility.
**How to avoid:** Write a test for each adapter that calls `isinstance(adapter, VenueAdapter)` — this checks structural conformance. Add a smoke test that calls every protocol method on a real or mock adapter.

---

## No-Vig Normalization — Multi-Outcome Extension

The existing `no_vig.py` implements two-way (binary) devigging. Phase 6 needs N-outcome for:
- **Sportsbooks:** three-way markets (soccer home/draw/away), futures (N teams), player props
- **Polymarket:** multi-outcome markets with 3+ outcome tokens

**Recommended algorithm for N-outcome Shin (MEDIUM confidence — verified against mberk/shin reference):**

```python
def devig_shin_n(implied_probs: list[float]) -> list[float]:
    """N-outcome Shin devig. Returns fair probs summing to 1.0.

    Algorithm: find z in (0, 1) such that sum of shin_fair(q_i, z) = 1
    where shin_fair(q, z) = (sqrt(z^2 + 4*(1-z)*q^2) - z) / (2*(1-z))
    """
    from scipy.optimize import brentq
    import math

    def shin_fair(q: float, z: float) -> float:
        return (math.sqrt(z**2 + 4 * (1 - z) * q**2) - z) / (2 * (1 - z))

    def objective(z: float) -> float:
        return sum(shin_fair(q, z) for q in implied_probs) - 1.0

    total = sum(implied_probs)
    if abs(total - 1.0) < 1e-6:
        return implied_probs  # already sums to 1, no vig

    try:
        z = brentq(objective, 1e-6, 0.5 - 1e-6, xtol=1e-10)
        fair_probs = [shin_fair(q, z) for q in implied_probs]
        # Normalize for floating point safety
        s = sum(fair_probs)
        return [p / s for p in fair_probs]
    except ValueError:
        # Fallback: multiplicative
        return [q / total for q in implied_probs]
```

This goes into `no_vig.py` as `devig_shin_n_outcome()` — do not create a new module for it.

---

## Module Layout Decision: New Package vs. Extend data_feeds

**Recommendation: Create `packages/venue_adapters/`** (Claude's Discretion)

**Rationale:**
1. `packages/data_feeds/` is a transport layer — raw wire protocol clients with no domain modeling. Adding domain contracts (MarketCatalog, ExposureBook, LedgerEntry) to it would violate single-responsibility and push the file toward 500-line limits.
2. A new package makes the dependency graph explicit: `venue_adapters` depends on `data_feeds` (for transport), `models` (for devigging/EV/kelly), and `analytics` (for regime). `data_feeds` does NOT depend on `venue_adapters`.
3. The uv workspace pattern already supports this — adding a new `packages/venue_adapters/pyproject.toml` follows the existing pattern for `data_feeds`, `models`, `agent_pipeline`.

**Counter-argument considered:** Adding a new package adds a small amount of boilerplate (pyproject.toml, __init__.py, src layout). This is acceptable given the 6-bounded-context scope. A single module added to `data_feeds` would be a wrong-level abstraction.

**CorrelationBucket:** Use Phase 3's `compute_entity_correlation()` from `pm_correlation.py` as a primitive inside `exposure.py`. Do not re-implement entity correlation. Import it. If the function's interface is not stable, wrap it.

---

## State of the Art

| Old Approach | Current Approach (Phase 6) | When Changed | Impact |
|--------------|---------------------------|--------------|--------|
| Per-venue price fetching in scanner | Canonical adapter protocol, all venues same interface | Phase 6 | Scanner loops become venue-agnostic |
| Two-way Shin in no_vig.py | N-outcome Shin extension | Phase 6 | Sportsbook futures and 3-way markets supported |
| Half-Kelly capped at 25% (size_position) | Fractional Kelly + drawdown throttle + venue concentration cap | Phase 6 | More conservative in correlated/high-drawdown conditions |
| No fill modeling | Fill-hazard estimate from orderbook depth + TTR | Phase 6 | Cost model includes fill probability, not just fee rate |
| No settlement record | Append-only LedgerEntry in Supabase | Phase 6 | Deterministic replay, PnL decomposition |
| Scanner ignores market lifecycle | MarketCatalog tracks state machine (OPEN/SUSPENDED/SETTLED) | Phase 6 | Stale market detection, correct lifecycle-aware scanning |

**Deprecated/outdated for Phase 6:**
- `kalshi_executor.py` passes `api_key` and `private_key_pem` directly to `execute_kalshi_arb_leg()`. Phase 6 `KalshiAdapter` should use `VenueAuthContext` dataclass to hold credentials instead. The executor file stays for actual order execution (which is in scope only for Kalshi); Phase 6 wraps it.

---

## Open Questions

1. **Kalshi historical snapshots endpoint**
   - What we know: `GET /trade-api/v2/markets/{ticker}/candlesticks` likely exists; `kalshi_client.py` does not call it
   - What's unclear: Exact endpoint path, required params, whether it's available on Basic tier
   - Recommendation: Implement `get_historical_snapshots()` in `KalshiAdapter` with a try/except that degrades gracefully to empty list if endpoint returns 404 or 403; log the failure

2. **Polymarket CLOB L2 auth signature correctness**
   - What we know: Existing `polymarket_client.py` uses `hmac.new()` — this is `hmac.new()` which is the correct call but the signature body (timestamp-only) may be incomplete vs. current Polymarket L2 spec
   - What's unclear: Current Polymarket L2 signature spec as of 2026 (timestamp + method + path?)
   - Recommendation: For Phase 6, all Polymarket operations are read-only; read endpoints require no L2 auth. Defer auth verification to when Polymarket trading is scoped. Flag in `PolymarketAdapter` docstring.

3. **Supabase schema for MarketCatalog and LedgerEntry**
   - What we know: Existing schema has `bets` table (from `kalshi_executor.py` usage); no `market_catalog` or `ledger_entries` table exists
   - What's unclear: Whether `scripts/schema.sql` already defines these tables (not checked)
   - Recommendation: Phase 6 Wave 0 must include schema migration for `market_catalog`, `market_snapshots`, and `ledger_entries` tables

4. **The Odds API coverage of Pinnacle**
   - What we know: The Odds API documentation lists Pinnacle as a supported bookmaker
   - What's unclear: Whether Pinnacle data is available on the free/starter tier or requires a paid plan
   - Recommendation: Test with a free-tier API key during Wave 0; if Pinnacle is gated, fall back to using DraftKings + FanDuel consensus as sharp reference

---

## Validation Architecture

`nyquist_validation` is `true` in `.planning/config.json` — this section is required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, used in all Phases 1–5) |
| Config file | `pyproject.toml` (each package) |
| Quick run command | `pytest packages/venue_adapters/tests/ -x -q` |
| Full suite command | `pytest packages/ -x -q` |

### Bounded Context → Test Map

| Bounded Context | Behavior | Test Type | Automated Command |
|-----------------|----------|-----------|-------------------|
| VenueAdapter Protocol | KalshiAdapter, PolymarketAdapter, OddsApiAdapter all pass `isinstance(x, VenueAdapter)` | unit | `pytest tests/test_protocol.py -x` |
| MarketCatalog | Lifecycle state machine rejects invalid transitions | unit | `pytest tests/test_catalog.py::test_invalid_transition -x` |
| MarketCatalog | OPEN→SETTLED transition records timestamp | unit | `pytest tests/test_catalog.py::test_settle_records_time -x` |
| CanonicalQuote | Kalshi cents→probability conversion round-trips | unit | `pytest tests/test_normalization.py::test_kalshi_price_conv -x` |
| CanonicalQuote | Polymarket 0–1 float passes through unchanged | unit | `pytest tests/test_normalization.py::test_polymarket_price_pass -x` |
| N-outcome Shin | devig_shin_n_outcome() sums to 1.0 for 3-way market | unit | `pytest tests/test_no_vig_n.py::test_three_way_shin_sums -x` |
| N-outcome Shin | Falls back to multiplicative when solver fails | unit | `pytest tests/test_no_vig_n.py::test_shin_fallback -x` |
| FillHazardModel | fill_hazard_estimate() returns 0.95 for at-market order | unit | `pytest tests/test_microstructure.py::test_fill_at_market -x` |
| FillHazardModel | fill_hazard_estimate() decreases as distance from best ask increases | unit | `pytest tests/test_microstructure.py::test_fill_distance_decay -x` |
| DislocScore | consensus_prob() correct for 3-venue weighted average | unit | `pytest tests/test_dislocation.py::test_consensus_weighted -x` |
| DislocScore | stale quote detection returns is_stale=True for old timestamp | unit | `pytest tests/test_dislocation.py::test_stale_detection -x` |
| ExposureBook | venue_concentration_cap correctly limits allocation fraction | unit | `pytest tests/test_exposure.py::test_venue_cap -x` |
| AllocationDecision | drawdown throttle returns 1.0 below threshold | unit | `pytest tests/test_exposure.py::test_throttle_below_dd -x` |
| AllocationDecision | drawdown throttle returns 0.25 at max drawdown | unit | `pytest tests/test_exposure.py::test_throttle_at_max_dd -x` |
| LedgerEntry | insert produces positive amount for SETTLEMENT credit | unit | `pytest tests/test_ledger.py::test_settlement_credit -x` |
| LedgerEntry | replay of 3 entries (FILL + FEE + SETTLEMENT) produces correct net PnL | unit | `pytest tests/test_ledger.py::test_replay_net_pnl -x` |
| KalshiAdapter | list_markets() returns CanonicalMarket list (mocked httpx) | unit | `pytest tests/adapters/test_kalshi_adapter.py -x` |
| PolymarketAdapter | get_orderbook() returns CanonicalOrderBook (mocked httpx) | unit | `pytest tests/adapters/test_polymarket_adapter.py -x` |
| OddsApiAdapter | list_markets() populates bookmaker list (mocked httpx) | unit | `pytest tests/adapters/test_odds_api_adapter.py -x` |
| OddsApiAdapter | circuit-breaker triggers when X-Requests-Remaining < 50 | unit | `pytest tests/adapters/test_odds_api_adapter.py::test_circuit_breaker -x` |

### Sampling Rate

- **Per task commit:** `pytest packages/venue_adapters/tests/ -x -q`
- **Per wave merge:** `pytest packages/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps (must exist before implementation)

- [ ] `packages/venue_adapters/tests/test_protocol.py` — VenueAdapter structural conformance
- [ ] `packages/venue_adapters/tests/test_catalog.py` — MarketCatalog lifecycle tests
- [ ] `packages/venue_adapters/tests/test_normalization.py` — CanonicalQuote price unit tests
- [ ] `packages/venue_adapters/tests/test_no_vig_n.py` — N-outcome Shin extension tests
- [ ] `packages/venue_adapters/tests/test_microstructure.py` — FillHazardModel tests
- [ ] `packages/venue_adapters/tests/test_dislocation.py` — DislocScore and consensus tests
- [ ] `packages/venue_adapters/tests/test_exposure.py` — ExposureBook and AllocationDecision tests
- [ ] `packages/venue_adapters/tests/test_ledger.py` — LedgerEntry and replay tests
- [ ] `packages/venue_adapters/tests/adapters/test_kalshi_adapter.py` — KalshiAdapter with mocked httpx
- [ ] `packages/venue_adapters/tests/adapters/test_polymarket_adapter.py` — PolymarketAdapter with mocked httpx
- [ ] `packages/venue_adapters/tests/adapters/test_odds_api_adapter.py` — OddsApiAdapter with mocked httpx
- [ ] `packages/venue_adapters/pyproject.toml` — new workspace package declaration
- [ ] Schema migration SQL for `market_catalog`, `market_snapshots`, `ledger_entries` tables

---

## Sources

### Primary (HIGH confidence)
- Kalshi official docs / existing `kalshi_client.py` — rate limits (20 read/sec Basic tier), RSA-PSS auth, endpoint paths verified against working client code
- Existing codebase: `no_vig.py`, `ev_calculator.py`, `monte_carlo.py`, `alpha.py`, `calibration_store.py`, `polymarket_client.py`, `kalshi_client.py` — all read directly
- The Odds API V4 official docs (`https://the-odds-api.com/liveapi/guides/v4/`) — endpoints, auth, supported books, quota model

### Secondary (MEDIUM confidence)
- Polymarket CLOB API docs (`https://docs.polymarket.com/developers/CLOB/introduction`) — auth model, base URLs, read vs. trading endpoint distinction
- Polymarket py-clob-client GitHub (`https://github.com/Polymarket/py-clob-client`) — Python client method names for orderbook, prices, trades
- Kalshi rate limit docs (`https://docs.kalshi.com/getting_started/rate_limits`) — tier table (Basic 20/10, Advanced 30/30, Premier 100/100, Prime 400/400)
- mberk/shin GitHub reference implementation — N-outcome Shin algorithm structure

### Tertiary (LOW confidence, flag for validation)
- Kalshi historical candlestick endpoint — not verified against current API docs, may not exist on Basic tier
- Polymarket L2 HMAC auth signature body format (timestamp-only vs. timestamp+method+path) — not confirmed for current API version

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies are existing workspace packages or plain REST calls
- Venue adapter protocol: HIGH — Python Protocol pattern is stable, well-tested pattern
- Kalshi API details: HIGH — working client in codebase validates against actual API
- Polymarket API details: MEDIUM — read endpoints confirmed, auth for trading not validated
- The Odds API: HIGH — official docs clearly specify v4 endpoints, quota model, supported books
- N-outcome Shin math: MEDIUM — algorithm structure confirmed from reference implementation, not tested against live data
- Fill-hazard model: MEDIUM — simplified closed-form model appropriate for Phase 6, not calibrated against actual fill data
- Settlement ledger pattern: HIGH — Supabase insert-only is a well-understood pattern consistent with existing codebase

**Research date:** 2026-03-14
**Valid until:** 2026-06-14 (90 days — Kalshi/Polymarket API versions may change; The Odds API bookmaker list changes more frequently)
