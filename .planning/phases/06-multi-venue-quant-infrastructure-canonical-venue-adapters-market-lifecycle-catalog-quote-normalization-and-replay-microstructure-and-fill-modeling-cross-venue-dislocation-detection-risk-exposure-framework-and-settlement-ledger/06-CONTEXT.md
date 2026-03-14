# Phase 6: Multi-Venue Quant Infrastructure — Context

**Gathered:** 2026-03-14
**Status:** Ready for planning
**Source:** PRD Express Path (user proposal — Event Markets Quant Enhancement Proposal)

<domain>
## Phase Boundary

Phase 6 extends SharpEdge v2 with a canonical multi-venue quant infrastructure layer covering:
- Canonical venue adapter contracts (Kalshi CLOB, Polymarket CLOB, sportsbook multi-book)
- Market catalog and lifecycle management (open / suspended / resolved / cancelled states)
- Cross-venue quote normalization (American, decimal, implied-probability representations)
- Historical snapshot storage for deterministic replay
- Market microstructure modeling (spread/depth, fill-hazard, queue-aware estimation)
- Cross-venue dislocation detection (consensus deviation, stale-quote detection)
- Risk/exposure framework (exposure book, correlation buckets, venue concentration caps)
- Settlement ledger (PnL, fee decomposition, deterministic replay, reconciliation)

**NOT in Phase 6 scope:**
- FinnAI code imports (no FinnAI reuse)
- Execution automation on any venue (read-only and simulation only)
- Full paper trading / shadow-decision mode (later phase)
- Anything already implemented in Phases 1–5 (Kalshi/Polymarket basic scanning, Platt calibration, walk-forward, EV/alpha/regime, Monte Carlo)

**Depends on:** Phase 5 (model pipeline must be stable before adding venue/risk layers on top)

</domain>

<decisions>
## Implementation Decisions

### Architectural Principles (ALL LOCKED)
- EV-first decisioning, not heuristic confidence-only scoring
- Explicit cost modeling: fees, spread, slippage, and liquidity at every decision point
- Calibration of probabilities before any capital allocation decision
- Deterministic replay: every market-state snapshot must be replayable from stored events
- Thin transport layers: heavy modeling isolated behind stable typed contracts
- Explicit risk budgets, exposure limits, and promotion gates before any production use
- No OHLCV-only bar-series assumptions — these are event markets, not price charts

### Venue Scope (LOCKED)
- Kalshi: binary event contracts, exchange-style CLOB, venue API, fee-aware EV
- Polymarket: CLOB market data, outcome mapping, wallet/auth abstraction, reward metadata
- Sportsbooks: read-only odds ingestion FIRST, then line shopping, then no-vig normalization
- Sportsbook execution is explicitly OUT OF SCOPE for Phase 6 (legal/operational constraints)

### Canonical Adapter Contract (LOCKED interface, flexible implementation)
Each adapter must expose:
- `listMarkets()`, `getMarketDetails()`, `getOrderBook()`, `getTrades()`
- `getHistoricalSnapshots()`, `getFeesAndLimits()`, `getSettlementState()`
- Capability flags: `read_only`, `streaming_quotes`, `streaming_orderbook`, `execution_supported`, `maker_rewards`, `settlement_feed`
- `placeOrder()` / `cancelOrder()` only for Kalshi (already partially built), NOT sportsbooks

### Bounded Contexts to Implement (LOCKED scope)
1. **Market Catalog & Lifecycle** — Event, Market, Outcome, MarketLifecycleState, VenueContractRef
2. **Venue Connectivity** — VenueAdapter, VenueCapability, VenueAuthContext, VenueFeeSchedule, VenueRateLimitPolicy
3. **Market Data & Quote Normalization** — CanonicalQuote, CanonicalOrderBook, CanonicalOddsSnapshot, MarketStatePacket
4. **Probability & Pricing** — NoVigBook, PricingDecision, EdgeEstimate (builds on Phase 1/5, no duplication)
5. **Risk, Exposure & Portfolio Construction** — ExposureBook, RiskLimit, CorrelationBucket, AllocationDecision
6. **Settlement & Ledger** — LedgerEntry, PositionLot, SettlementEvent, PayoutRecord, ReconciliationReport

NOT implementing in Phase 6:
- Research & Feature Engineering bounded context (covered by Phase 5)
- Execution & Order Strategy (read-only only, execution deferred)
- API/Operator Tools surface (Phase 4 already handles this)

### Quant Models to Add (LOCKED)
- **Fair Probability Engine enhancement**: multi-outcome no-vig normalization, consensus blending across venues — builds on Phase 1's ev_calculator.py, extends not replaces
- **Market Microstructure Model**: spread/depth modeling, fill-hazard estimation, passive vs. aggressive execution comparison — NEW
- **Cross-Venue Dislocation Model**: consensus deviation scoring, stale-quote detection, paired exposure checks — NEW
- **Event-State & Time-To-Resolution Model**: hazard-style event-time features, regime by market phase — NEW
- **Allocation & Exposure Model**: fractional Kelly variants, drawdown-aware throttles, venue concentration caps — NEW (Monte Carlo from Phase 1 is foundational, this is decision layer on top)

### Settlement & Replay (LOCKED)
- Event-sourced settlement replay must be deterministic
- Fee and rebate decomposition required
- Pre-trade vs. post-trade attribution tracking
- Calibration drift and execution drift decomposition

### Model Governance (LOCKED before any model moves to decisioning)
- Time-correct train/val/test splits required
- Walk-forward evidence required (Phase 5 provides the backtester)
- Calibration reports required
- Cost and fee sensitivity analysis required
- Venue-specific drift monitoring required

### Starting Point (LOCKED)
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

</decisions>

<specifics>
## Specific Ideas from Proposal

**Sportsbook priority research areas:**
- No-vig consensus construction across books
- Closing-line-value benchmarking (Phase 1 has CLV — extend to cross-book)
- Stale-line detection
- Market family calibration by league, sport, and bet type

**Kalshi priority research areas:**
- Binary market calibration by category and time-to-close
- Spread and depth dynamics near information shocks
- Passive quote viability after fees
- Fill-probability estimation from order book state

**Polymarket priority research areas:**
- Midpoint quality and reward-aware quoting
- Fragmentation and cross-market consistency
- Liquidity dynamics during event clustering
- Settlement and reward attribution quality

**Cross-venue dislocation detection:**
- Venue spread decomposition
- Stale quote detection
- Consensus deviation scoring
- Paired or basket exposure checks across related outcomes

**Allocation model specifics:**
- Fractional Kelly or capped Kelly variants (not pure Kelly — too aggressive)
- Drawdown-aware throttles
- Venue concentration caps
- Correlated-outcome netting

</specifics>

<deferred>
## Deferred (Explicitly Out of Scope for Phase 6)

- Sportsbook execution automation (legal/operational constraints — later phase)
- Paper trading / shadow-decision mode (Phase 5 of proposal = later SharpEdge phase)
- Research & Feature Engineering bounded context (covered by Phase 5)
- Operator review workflows / alert system changes (Phase 4 API layer handles)
- Full Research & Feature Engineering pipeline (walk-forward already in Phase 5)
- FinnAI code reuse (explicitly forbidden by proposal)

</deferred>

---

*Phase: 06-multi-venue-quant-infrastructure*
*Context gathered: 2026-03-14 via PRD Express Path (user inline proposal)*
