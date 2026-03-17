# Phase 9: Research Findings — Prediction Market Resolution Models

**Gathered:** 2026-03-15
**Scope:** Kalshi/Polymarket historical data APIs, feature engineering for PM resolution, prerequisite gaps, reuse opportunities

---

## 1. Kalshi Historical Data API

### Resolved Markets Endpoint

**Endpoint:** `GET /trade-api/v2/markets?status=settled`

The existing `KalshiClient.get_markets(status="settled")` call works without modification. Key points:

- `status` accepts: `"open"`, `"closed"`, `"settled"` (settled = fully resolved with payout)
- `result` field on `KalshiMarket`: `"yes"` | `"no"` | `None` (None = unresolved)
- Pagination: `cursor` param, returned from previous response's `cursor` field
- Rate limit: ~10 requests/second for authenticated, ~2 req/sec for unauthenticated
- History depth: ~2 years from launch date (approx. 2022-11)

### Available Fields for Feature Engineering

From `KalshiMarket` (already parsed by client):
```
ticker              — unique contract identifier (encodes category, date, strike)
event_ticker        — parent event group (e.g., "KXFED", "KXBTC", "KXNFL")
title               — human-readable question
subtitle            — additional context
yes_bid / yes_ask   — spread at capture time
volume              — total volume in contracts
volume_24h          — 24h contracts (proxy for recency of activity)
open_interest       — outstanding contracts (proxy for conviction)
last_price          — final mid price before settlement
close_time          — datetime when market closes for new orders
result              — "yes" | "no" (resolution label)
```

### Feature Engineering Approach for Kalshi

Fields derivable from `ticker` pattern (e.g., `KXFED-26MAR19-T0.25`):
- `category` — prefix before `-` (KXFED, KXBTC, KXNFL, etc.)
- `days_to_close_at_creation` — strike date in ticker vs. event_ticker creation date
- `strike_value` — numeric threshold embedded in ticker (e.g., T0.25 = 25 bps)

Temporal features (computed at backfill time):
- `price_30d` — yes_bid/yes_ask mid at T-30 days (requires SnapshotStore replay or market history)
- `price_7d` — mid at T-7 days
- `price_1d` — mid at T-1 day (last_price often serves as T-0 proxy)
- `volume_spike_ratio` — volume_24h / volume * 7 (weekly velocity)

Category-specific features:
- **Political**: `days_to_election`, `poll_margin` (external, not in API — set to 0.0 if unavailable)
- **Economic**: `days_to_release_date` (derivable from ticker date), `consensus_estimate` (not in API — 0.0)
- **Crypto**: `price_volatility_7d` (not in API — requires external data — 0.0 fallback)
- **Weather**: `forecast_confidence` (not in API — 0.0 fallback)
- **Entertainment**: `days_to_ceremony`, `nominee_count` (derivable from multi-outcome structure)

**Pitfall:** Many category-specific features require external data sources not currently in the codebase. Phase 9 uses 0.0 fallback for all external category features. This is documented inline and can be upgraded in Phase 10 when external feeds are wired.

### Backfill Strategy

```python
# Paginate all settled markets — cursor-based loop
async def backfill_kalshi_resolved(client: KalshiClient, out_dir: Path):
    cursor = None
    all_markets = []
    while True:
        batch = await client.get_markets(status="settled", limit=100, cursor=cursor)
        if not batch:
            break
        all_markets.extend(batch)
        cursor = batch[-1].ticker  # Kalshi cursor is the last ticker seen
        if len(batch) < 100:
            break
    # Save as parquet
    df = pd.DataFrame([asdict(m) for m in all_markets])
    df.to_parquet(out_dir / "kalshi_resolved.parquet")
```

Estimated fetch time: ~30 minutes for full 2-year backfill at 2 req/sec (unauthenticated).

---

## 2. Polymarket Historical Data API

### Resolved Markets Endpoint

**Endpoint:** `GET https://gamma-api.polymarket.com/markets?active=false&closed=true`

The existing `PolymarketClient.get_markets(active=False, closed=True)` call works without modification. Key points:

- Returns all closed (resolved) markets — `winner` field on `PolymarketOutcome` is `True` for the winning outcome
- `closed=True` + `active=False` is the correct filter for resolved markets
- Pagination: `offset` param (integer, no cursor)
- No authentication required — Gamma API is fully public
- History depth: ~5+ years from launch (mid-2020)
- Rate limit: documented as 10 req/sec, practical ~5 req/sec

### Available Fields for Feature Engineering

From `PolymarketMarket` (already parsed by client):
```
condition_id        — primary unique key (used as market_id in pm_edge_scanner)
question            — human-readable question
outcomes            — list of PolymarketOutcome (token_id, outcome, price, winner)
volume              — total lifetime volume in USD
volume_24h          — 24h USD volume (proxy for activity at capture time)
liquidity           — current liquidity (proxy for market depth)
end_date            — settlement datetime
category            — category string ("Politics", "Crypto", "Sports", etc.)
slug                — URL-friendly identifier
```

From `PolymarketOutcome`:
```
token_id            — ERC-1155 token ID on Polygon (unique per outcome)
outcome             — "Yes" / "No" or custom label
price               — current probability (0-1)
winner              — True if this outcome won, False/None if not
```

### Price History

`PolymarketClient.get_market_history(condition_id, fidelity=60)` returns price points at specified minute intervals. Use for T-30d, T-7d, T-1d features.

### Normalization for Multi-Outcome Markets

Polymarket has multi-outcome markets (e.g., "Who wins the election?" with 5+ candidates). Strategy:
- If market has exactly 2 outcomes (Yes/No) → use directly
- If market has 3+ outcomes → treat the highest-volume outcome as "Yes" proxy, sum of rest as "No"
- Label: `resolved_yes = 1 if any(o.winner for o in outcomes if o.outcome.lower() != "no") else 0`

### The Graph Subgraph (Deferred)

Polymarket on-chain data is also available via The Graph protocol subgraph at:
`https://api.thegraph.com/subgraphs/name/polymarket/matic-markets`

This provides on-chain settlement records and trading history. Deferred to Phase 10 — REST API is sufficient for Phase 9 feature engineering.

### Backfill Strategy

```python
async def backfill_polymarket_resolved(client: PolymarketClient, out_dir: Path):
    all_markets = []
    offset = 0
    while True:
        batch = await client.get_markets(active=False, closed=True, limit=100, offset=offset)
        if not batch:
            break
        all_markets.extend([m for m in batch if any(o.winner is not None for o in m.outcomes)])
        offset += len(batch)
        if len(batch) < 100:
            break
    df = pd.DataFrame([{...}])  # flatten outcomes to binary label
    df.to_parquet(out_dir / "polymarket_resolved.parquet")
```

---

## 3. Prerequisite Gaps Before Phase 9 Can Start

### Gap 1: API Key Availability (KALSHI_API_KEY)

**Status:** KalshiClient supports unauthenticated GET requests. Public endpoint `GET /markets?status=settled` does not require RSA-PSS signing.

**Resolution:** Phase 9 data pipeline degrades gracefully — if `KALSHI_API_KEY` absent from env, backfill script uses fixture data (`data/raw/prediction_markets/fixtures/kalshi_sample.json`). Fixture contains 50 synthetic resolved markets covering all 5 categories.

### Gap 2: Minimum Dataset Size

**Status:** Dataset size is an output of the backfill script, not a prerequisite.

**Resolution:** After backfill, `scripts/assess_pm_dataset.py` reports market count per category and flags categories below 200 (minimum viable). Models for sub-threshold categories are not trained — `PMResolutionPredictor` returns `None` for those categories, falling back to fee-adjusted probability in pm_edge_scanner.

### Gap 3: Legal/Compliance Review

**Status:** This is a human-only prerequisite for production deployment. The plan assumes review is in progress.

**Resolution:** All model training and feature engineering can proceed before legal clearance. The `PMResolutionPredictor` is gated behind a `ENABLE_PM_RESOLUTION_MODEL=true` env var. Default is `false` — scanner uses fee-adjusted fallback until explicitly enabled.

### Gap 4: Polymarket Category Field Reliability

**Status:** Polymarket `category` field is inconsistent across API versions (sometimes empty, sometimes wrong).

**Resolution:** Category inference from `question` text using a simple keyword map (e.g., "will bitcoin", "crypto", "ETH" → `crypto`). Fallback category: `"other"` — trained as a catch-all model.

---

## 4. Reuse vs. Build-New Analysis

### Directly Reusable (no modification)

| Component | Reuse | Notes |
|-----------|-------|-------|
| `KalshiClient` | Fully reusable | `get_markets(status="settled")` works now |
| `PolymarketClient` | Fully reusable | `get_markets(closed=True)` works now |
| `CalibrationStore` | Fully reusable | Works on any binary prediction problem |
| `WalkForwardBacktester` | Fully reusable | Not sports-specific |
| `EnsembleManager` | Fully reusable | Binary classification only |
| `compose_alpha()` | Fully reusable | Works on any float edge score |
| `pm_edge_scanner.scan_pm_edges()` | Fully reusable | Only `model_probs` source changes |
| `pm_regime.classify_pm_regime()` | Fully reusable | Market-agnostic |

### Needs Extension (modify existing)

| Component | Extension | Notes |
|-----------|-----------|-------|
| `scan_pm_edges()` | No code change | Only `model_probs` dict contents change |
| `scripts/run_calibration.py` | Add PM calibration path | Add `--mode pm` flag |
| `scripts/run_walk_forward.py` | Add PM data path | Add `--data-dir` argument |

### Build New (Phase 9 only)

| Component | Location | Description |
|-----------|----------|-------------|
| `scripts/download_pm_historical.py` | `scripts/` | Kalshi + Polymarket resolved market backfill |
| `scripts/process_pm_historical.py` | `scripts/` | Parquet processor — PM feature engineering |
| `PMFeatureAssembler` | `packages/models/src/sharpedge_models/pm_feature_assembler.py` | PM-specific feature vector (not sports) |
| `PMResolutionPredictor` | `packages/models/src/sharpedge_models/pm_resolution_predictor.py` | Category-based model inference |
| `scripts/train_pm_models.py` | `scripts/` | Trains per-category binary classifiers |
| `scripts/assess_pm_dataset.py` | `scripts/` | Dataset size assessment per category |
| `tests/` stubs for above | various | RED stubs per TDD pattern |

---

## 5. Standard Stack for Phase 9

All of the following are already in the workspace Python environment:

```
scikit-learn    — RandomForestClassifier (base model), LogisticRegression (Platt calibration)
pandas          — parquet I/O, DataFrame feature engineering
pyarrow         — parquet backend
joblib          — model persistence (same as CalibrationStore)
pytest          — test framework
pytest-asyncio  — async test support
httpx           — already used by KalshiClient / PolymarketClient
```

No new dependencies required for Phase 9.

---

## 6. Architecture Pattern

```
Backfill                    Feature Eng                Model Train
────────────────────────    ───────────────────────    ────────────────────
download_pm_historical.py → process_pm_historical.py → train_pm_models.py
  └─ KalshiClient              └─ PMFeatureAssembler      └─ EnsembleManager (per category)
  └─ PolymarketClient          └─ category detection      └─ CalibrationStore (per category)
  └─ data/raw/pm/              └─ data/processed/pm/      └─ data/models/pm/

Inference
──────────────────────────────────────────────────────────────────────
PMResolutionPredictor.predict(markets) → model_probs: dict[str, float]
  └─ loads data/models/pm/{category}.joblib
  └─ calls PMFeatureAssembler.assemble(market)
  └─ returns {market_id: probability}
  └─ fed to existing scan_pm_edges(model_probs=...)
```

---

*Research complete: 2026-03-15*
*No new dependencies required. Backfill works with existing transport clients.*
