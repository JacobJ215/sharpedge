# Phase 9: Prediction Market Resolution Models & Expansion Beyond Sports — Context

**Gathered:** 2026-03-15
**Status:** Ready for planning
**Source:** docs/NEXT_PHASES_BRIEF.md (Phase 9+ section, line 147)

<domain>
## Phase Boundary

Phase 9 builds a standalone ML resolution model for prediction markets. Today, Kalshi and Polymarket prices are used as *pricing signals* for cross-venue dislocation detection (CrossVenueDislocDetector in packages/venue_adapters). Phase 9 trains models that predict the *actual outcome* — will this binary contract resolve YES or NO?

This requires a new historical data pipeline (resolved market backfill), feature engineering specific to prediction markets (not sports), binary classification models, and Platt calibration against market-implied probability at time of bet. The expansion categories (political, economic, entertainment, crypto, weather) each get a category-specific model and calibration.

This phase does NOT add new user-facing UI. All outputs feed into the existing pm_edge_scanner.py — specifically, replacing the fee-adjusted fallback model_prob with a trained resolution probability, raising edge quality from noise-floor to actionable alpha.

</domain>

<existing_infrastructure>
## What Already Exists

### Transport Clients (packages/data_feeds/)

**KalshiClient** (`packages/data_feeds/src/sharpedge_feeds/kalshi_client.py`):
- Full RSA-PSS-SHA256 signed async httpx client
- `get_markets(status="open"|"closed"|"settled", limit, cursor)` — supports `status=settled` for resolved markets
- `KalshiMarket` dataclass: ticker, event_ticker, title, subtitle, yes_bid, yes_ask, no_bid, no_ask, volume, volume_24h, open_interest, last_price, status, close_time, `result` ("yes"/"no"/None)
- Pagination via cursor param — ready for bulk backfill
- Auth: KALSHI-ACCESS-KEY + optional RSA-PSS signature

**PolymarketClient** (`packages/data_feeds/src/sharpedge_feeds/polymarket_client.py`):
- Async httpx client — Gamma API (metadata), CLOB API (prices), Data API (history)
- `get_markets(active=False, closed=True)` — returns resolved markets
- `PolymarketMarket` dataclass: condition_id, question_id, question, outcomes (list of PolymarketOutcome), volume, volume_24h, liquidity, end_date, active, closed, category, slug
- `PolymarketOutcome`: token_id, outcome ("Yes"/"No"), price (0-1), `winner` (bool|None)
- `get_market_history(condition_id, fidelity=60)` — price trajectory in minutes resolution
- No auth required for public endpoints (Gamma API)

### Venue Adapters (packages/venue_adapters/)

**KalshiAdapter** (`packages/venue_adapters/src/sharpedge_venue_adapters/adapters/kalshi.py`):
- Canonical wrapper over KalshiClient
- `list_markets()` returns `list[CanonicalMarket]`
- Offline mode (api_key=None) returns safe defaults
- `CanonicalMarket` includes: market_id, venue_id, title, category, lifecycle_state, close_time, settlement_state, fee_schedule

**PolymarketAdapter** (`packages/venue_adapters/src/sharpedge_venue_adapters/adapters/polymarket.py`):
- Same pattern as KalshiAdapter
- Wraps PolymarketClient; returns CanonicalMarket list

**MarketCatalog** (`packages/venue_adapters/src/sharpedge_venue_adapters/catalog.py`):
- Lifecycle state machine: PENDING → OPEN → CLOSED → SETTLED
- `SettlementState` enum: UNRESOLVED, RESOLVED_YES, RESOLVED_NO

**SnapshotStore** (`packages/venue_adapters/src/sharpedge_venue_adapters/snapshot_store.py`):
- In-memory + Supabase dual mode (same pattern as SettlementLedger)
- `save(snapshot: MarketStatePacket)` / `replay(market_id) -> list[MarketStatePacket]`
- Used by Phase 6 for market state persistence

### Analytics (packages/analytics/)

**pm_edge_scanner.py** (`packages/analytics/src/sharpedge_analytics/pm_edge_scanner.py`):
- `scan_pm_edges(kalshi_markets, polymarket_markets, model_probs, volume_floor, active_bets)`
- `model_probs: dict[str, float]` — market_id → model probability
- When model_probs[market_id] is absent: falls back to fee-adjusted price (KALSHI_FEE_RATE=0.03)
- Phase 9 replaces this fallback with trained resolution model probability
- `PMEdge` dataclass: platform, market_id, market_title, market_prob, model_prob, edge_pct, alpha_score, alpha_badge, regime, regime_threshold

**pm_regime.py** (`packages/analytics/src/sharpedge_analytics/pm_regime.py`):
- `classify_pm_regime(hours_to_close, hours_since_created, volume_spike_ratio, price_variance)`
- Returns classification with regime state (Discovery/Consensus/NewsCatalyst/ClosingRush) and edge_threshold_pct
- Used by pm_edge_scanner for regime-adjusted edge thresholds

### ML Pipeline (packages/models/)

**CalibrationStore** (`packages/models/src/sharpedge_models/calibration_store.py`):
- Per-sport Platt scaling (sklearn LogisticRegression as calibrator)
- `update(sport, predictions, actuals)` — fits Platt scaler on out-of-sample data
- `confidence_mult` from Brier score → alpha multiplier
- Persists via joblib; dual-mode (in-memory + disk)

**EnsembleManager** (`packages/models/src/sharpedge_models/ensemble_trainer.py`):
- `train(X, y)` → stacking with out-of-fold predictions
- `predict_proba(X)` → calibrated ensemble probability
- Accepts dict[str, np.ndarray] or pd.DataFrame

**WalkForwardBacktester** (`packages/models/src/sharpedge_models/walk_forward.py`):
- Non-overlapping window walk-forward validation
- `quality_badge_from_windows()` → "low"|"medium"|"high"|"excellent"
- Works on any binary classification problem — sport-agnostic

**FeatureAssembler** (`packages/models/src/sharpedge_models/feature_assembler.py`):
- Sports-domain features only: rest_days, PPG, form, injury, weather, travel
- Phase 9 creates `PMFeatureAssembler` alongside this — NOT extending it (different domain)

### Existing Data Storage

- `data/raw/espn/` — sports data (ESPN API)
- `data/processed/` — parquet files from process_historical_data.py
- `data/models/` — trained model artifacts (joblib)
- Phase 9 adds: `data/raw/prediction_markets/` and `data/processed/prediction_markets/`

### Existing Scripts

- `scripts/download_historical_data.py` — ESPN downloader (sports only)
- `scripts/process_historical_data.py` — parquet processor (sports only)
- `scripts/train_models.py` — trains sports ensemble (reusable pattern for PM models)
- `scripts/run_walk_forward.py` — walk-forward backtest orchestrator (reusable)
- `scripts/run_calibration.py` — CalibrationStore update script (reusable)

</existing_infrastructure>

<decisions>
## Implementation Decisions

### API Key Strategy (PREREQ-01)
- KalshiClient already supports unauthenticated market listing (`get_markets` uses `_auth_headers` but public endpoints don't require RSA-PSS signature)
- Resolved market backfill works with API key only (no private key required for GET /markets?status=settled)
- Data pipeline designed to work with sample/mock data when KALSHI_API_KEY absent — `offline mode` returns fixture data
- Polymarket Gamma API is fully public — no auth required for historical resolved market data

### Resolution Model Scope (PREREQ-02)
- Binary resolution only in Phase 9 (simpler) — not price-at-time-of-bet (deferred)
- Each expansion category gets its own feature set and calibration — sports features do NOT transfer
- Multi-outcome Polymarket markets normalized to binary YES/NO (primary outcome vs. field)

### Category Taxonomy (PREREQ-03)
- 5 expansion categories per NEXT_PHASES_BRIEF.md:
  - `political` — AP/FEC resolution signals
  - `economic` — BLS/Fed/BEA releases
  - `entertainment` — ceremony results (Oscars, Grammys)
  - `crypto` — on-chain oracle prices
  - `weather` — NOAA/Weather.gov
- Category detected from Kalshi `event_ticker` prefix and Polymarket `category` field
- Category-specific feature sets defined in Phase 9

### Integration Point (PREREQ-04)
- Phase 9 outputs flow into `pm_edge_scanner.py` via the `model_probs` dict
- A new `PMResolutionPredictor` class (analogous to MLModelManager) builds this dict from trained models
- Scanner unchanged — only `model_probs` source changes from fee-adjusted to ML-predicted

### Dataset Size Assessment
- Kalshi has ~2 years of history (~1000-3000 resolved contracts per category, varies widely)
- Polymarket has more — launched mid-2020, ~5000+ resolved binary markets
- Minimum viable training set: 200 resolved markets per category (confirmed via Phase 9 data pipeline)
- Walk-forward backtesting uses minimum 3 windows of 50+ markets each

### Claude's Discretion
- Exact feature engineering within each category (derived from available fields per client)
- Whether to use a shared RandomForest base + per-category Platt calibration vs. separate models per category
- Storage format for resolved market parquet (column schema)

</decisions>

<deferred>
## Deferred Ideas

- Price-at-time-of-bet resolution models (vs. binary YES/NO) — more complex, deferred
- The Graph subgraph queries for Polymarket on-chain data — REST API sufficient for Phase 9
- Legal/compliance review per market category — documented as prerequisite; plan assumes review done
- Native admin UI for PM resolution model performance — not planned
- Real-time streaming model updates (vs. batch nightly retrain) — deferred

</deferred>

---

*Phase: 09-prediction-market-resolution-models-and-expansion*
*Context gathered: 2026-03-15*
