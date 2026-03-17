# SharpEdge Trading Swarm — Design Spec

**Date:** 2026-03-16
**Status:** Approved (v2 — reviewer issues addressed)
**Author:** Collaborative brainstorm

---

## Goal

Build a fully autonomous multi-agent trading swarm that continuously scans Kalshi prediction markets, researches signals, predicts edge, manages risk, executes paper (then live) orders, monitors positions, and learns from losses — all without human intervention per trade.

---

## Architecture

### Approach: Event-Driven Pipeline

A standalone Python daemon (`packages/trading_swarm/`) communicates via `asyncio.Queue` chains. No Redis required. Agents are decoupled through typed event objects. The daemon shares existing monorepo packages (`kalshi_client`, `polymarket_client`, Phase 9 PM resolution models, BLS/FEC/CoinGecko clients) without duplicating them.

### Pipeline Flow

```
[Scan Agent]          — every 5 min, scans all active Kalshi markets
     ↓ OpportunityEvent
[Research Agents]     — parallel, one per opportunity
     ↓ ResearchEvent
[Prediction Agent]    — Phase 9 RF model + Claude LLM calibration
     ↓ PredictionEvent (only if edge > 3%)
[Portfolio Manager]   — cross-market exposure check (Supabase advisory lock)
     ↓ ApprovedEvent
[Risk Agent]          — fractional Kelly sizing + circuit breakers
     ↓ ExecutionEvent
[Execution Layer]     — PaperExecutor | KalshiExecutor (env-flag)
     ↓
[Monitor Agent]       — polls every 60 sec until settlement
     ↓ ResolutionEvent
[Post-Mortem Agent]   — structured loss attribution → bounded learning update
```

---

## Agent Specifications

### 1. Scan Agent

- **Trigger:** Every 5 minutes via asyncio loop
- **Input:** Kalshi API — all active markets
- **Filters:**
  - Minimum liquidity: $500
  - Time to resolution: 1 hour – 30 days
  - Anomaly detection: price momentum spike > 15% vs. 24h baseline, spread widening > 2× baseline
  - Requires 7-day price history before anomaly detection activates (new markets excluded)
- **Output:** `OpportunityEvent` per flagged market
- **Failover:** If Kalshi API is down, log error, skip cycle, do not pause daemon
- **Builds on:** existing `pm_edge_scanner.py`

### 2. Research Agent

- **Trigger:** One spawned per `OpportunityEvent`, run in parallel
- **Signal freshness:** Any signal older than `time_to_resolution / 2` is discarded; signals older than 1 hour receive a 50% confidence penalty
- **Signal sources (by priority weight):**
  1. **Authoritative (high weight):** BLS client, FEC client, CoinGecko client, AP/Reuters RSS feeds — if source unavailable, log WARN and reweight remaining sources upward
  2. **Cross-venue consensus (high weight):** Polymarket price for same event
  3. **Reddit (medium weight):** PRAW, free tier, 100 req/min, `asyncio.Semaphore(10)` to cap concurrent requests
  4. **Twitter/X (medium weight, optional):** Tweepy, feature-flagged via `ENABLE_TWITTER_SIGNALS=true/false`, `asyncio.Semaphore(5)` for rate limiting, exponential backoff on 429, fallback to Reddit + authoritative if unavailable
- **Processing:** Claude API (`claude-sonnet-4-6`) summarizes headlines + Polymarket/Kalshi dislocation into sentiment score. On LLM timeout (10s) or error: fall back to base RF probability with zero calibration adjustment (no position blocked).
- **Output:** `ResearchEvent` with narrative summary, per-source sentiment scores, and signal age metadata

### 3. Prediction Agent

- **Startup validation:** At daemon start, verifies `data/models/pm/{category}.joblib` exists for all 5 categories. Missing models → log WARNING. Live mode refuses to start if any category model missing.
- **Input:** `ResearchEvent`
- **Model:** Phase 9 RandomForest resolution model (`pm_resolution_predictor.py`, `ENABLE_PM_RESOLUTION_MODEL=true`). Fallback: market implied probability if model file absent.
- **LLM calibration:** Claude API adjusts base RF probability by ±10% max based on research narrative. Interface: `LLMCalibrator.calibrate(base_prob, narrative) -> float`. Timeout: 10s, 2 retries, then return `base_prob` unchanged.
- **Edge calculation:** `edge = |calibrated_prob - kalshi_price| - transaction_fee` (Kalshi fee ≈ 0.1%)
- **Gate:** Only emits `PredictionEvent` if `edge > 3%` and confidence above `confidence_threshold` (loaded from `trading_config`, default 0.03, bounds [0.01, 0.10])
- **Output:** `PredictionEvent` with predicted probability, edge, confidence score, and research artifact snapshot (stored to `trade_research_log`)

### 4. Portfolio Manager

- **Input:** `PredictionEvent`
- **Concurrency:** Uses Supabase row-level advisory lock on `open_positions` during check + write to prevent race conditions between concurrent research agents. Lock timeout: 2s, retry once.
- **Checks:**
  - Max exposure per market: 5% of bankroll
  - Max exposure per category: 20% of bankroll
  - Max total open exposure: 40% of bankroll
  - Correlation flag: detects multiple open positions resolving on same underlying event
- **Output:** `ApprovedEvent` or logged drop with reason

### 5. Risk Agent

- **Input:** `ApprovedEvent`
- **Kelly formula:** Standard binary Kelly: `f* = (p × b - q) / b` where `p = calibrated_prob`, `q = 1 - p`, `b = (1 - kalshi_price) / kalshi_price` (implied odds against). Fractional Kelly at 0.25×: `size = 0.25 × f* × bankroll`. Clamped to `[0.1%, 5%]` of bankroll regardless of Kelly output. Handles price near 0 or 1 with floor at `min(price, 0.05)` and ceiling at `max(price, 0.95)`.
- **Circuit breakers (auto-pause, logged to `circuit_breaker_state`):**
  - Daily loss > 10% of bankroll → pause 24 hours
  - 5 consecutive losses → pause 4 hours, trigger post-mortem on all 5
  - Total open exposure > 40% → no new positions until some resolve
  - Kalshi API error rate > 20% in 5 minutes → pause until recovery
- **Output:** `ExecutionEvent` with approved position size

### 6. Execution Layer

Abstract `BaseExecutor` interface with two implementations:

- **`PaperExecutor`** (default):
  - Simulates fills at current Kalshi mid-price
  - Slippage model: `slippage = spread/2 + (position_size / total_market_volume) × 0.001`
  - Tracks virtual $10,000 bankroll
  - Writes to `paper_trades` Supabase table
  - Uses idempotency key (`market_id + timestamp`) to prevent duplicate fills

- **`KalshiExecutor`** (live):
  - Places real orders via Kalshi REST API
  - Same interface as PaperExecutor
  - Activated by `TRADING_MODE=live`
  - Uses idempotency key for duplicate protection

Controlled by `TRADING_MODE=paper|live` env var. No code changes required to switch.

### 7. Monitor Agent

- **Trigger:** Polls every 60 seconds for each open position (reduced from 10 min to avoid missing quick-settling markets)
- **Input:** `open_positions` Supabase table (status = 'open')
- **Action:** Checks Kalshi settlement status via REST API
- **Output:** `ResolutionEvent` with actual P&L on settlement; updates `open_positions.status` to 'settled'

### 8. Post-Mortem Agent

- **Trigger:** Every `ResolutionEvent` for a loss
- **Attribution dimensions:**
  1. **Model error** — predicted probability significantly wrong vs. outcome (|calibrated_prob - outcome| > 0.3)
  2. **Signal error** — research narrative sentiment contradicted by outcome
  3. **Sizing error** — Kelly fraction too aggressive (position > 3% of bankroll and lost)
  4. **Variance** — legitimate low-probability outcome (calibrated_prob < 0.35 and lost)
- **Output:** Written to `trade_post_mortems` Supabase table
- **Learning loop (bounded):** After 3+ losses of same attribution type → auto-adjust within hard bounds:
  - Model errors → raise `confidence_threshold` by 0.005, max 0.10
  - Signal errors → reduce offending source weight by 10%, min weight 0.1
  - Sizing errors → reduce `kelly_fraction` by 0.02, min 0.10
  - All adjustments logged. After 5 consecutive auto-adjustments of any kind → pause auto-learning and alert (log + Supabase flag). Manual review required to resume.
  - Updates persisted to `trading_config` table, reloaded at next cycle

---

## Paper Trading & Promotion Gate

### Paper Mode (Default)

- Virtual bankroll: $10,000
- All trades simulated via `PaperExecutor`
- Full pipeline runs identically to live mode

### Promotion Gate

Before `TRADING_MODE=live` is accepted, daemon validates at startup:

| Requirement | Threshold | Rationale |
|---|---|---|
| Minimum paper trading period | 30 days | Regime coverage |
| Minimum resolved trades | 50 trades | Statistical significance |
| Min days between first and last trade | 10 days | Prevents clustering |
| Expected value | Positive (EV > 0) | Basic profitability |
| Sharpe ratio | > 0.5 | Risk-adjusted consistency |
| Win rate | > 45% | Execution sanity check |
| Max drawdown | < 20% of starting bankroll | Downside protection |
| Phase 9 calibration | Expected vs. actual outcome distribution within 10% ECE | Model validity |

If gate fails, daemon prints a per-requirement report and refuses to start in live mode.

### Live Mode

- Starts with $2,000 real bankroll (20% of paper bankroll — conservative initial sizing while validating live execution)
- `KalshiExecutor` replaces `PaperExecutor`
- All other agents and logic identical

---

## Signal Sources

| Source | Category | Cost | Weight | Flag |
|---|---|---|---|---|
| BLS client | Economics | Free (existing) | High | Always on |
| FEC client | Politics | Free (existing) | High | Always on |
| CoinGecko client | Crypto | Free (existing) | High | Always on |
| AP/Reuters RSS | All | Free | High | Always on |
| Polymarket price | All | Free (existing) | High | Always on |
| Reddit (PRAW) | All | Free | Medium | Always on |
| Twitter/X (Tweepy) | All | $100/mo | Medium | `ENABLE_TWITTER_SIGNALS` |

All signals are timestamped at fetch time. Staleness rules applied per Research Agent spec above.

---

## Data Model (Supabase)

### `paper_trades`
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `market_id` | text | |
| `direction` | text | 'yes' \| 'no' |
| `size` | numeric | dollars |
| `entry_price` | numeric | 0-1 |
| `exit_price` | numeric | 0-1, null until settled |
| `pnl` | numeric | null until settled |
| `confidence_score` | numeric | at time of trade |
| `category` | text | political \| economic \| crypto \| entertainment \| weather |
| `trading_mode` | text | 'paper' \| 'live' |
| `opened_at` | timestamptz | |
| `resolved_at` | timestamptz | null until settled |
| `actual_outcome` | boolean | null until settled |

### `open_positions`
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `market_id` | text | |
| `size` | numeric | |
| `entry_price` | numeric | |
| `expected_resolution_time` | timestamptz | |
| `trading_mode` | text | |
| `status` | text | 'open' \| 'settling' \| 'settled' |
| `opened_at` | timestamptz | |

### `trade_post_mortems`
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `trade_id` | uuid FK → paper_trades | |
| `model_error_score` | numeric | 0-1 |
| `signal_error_score` | numeric | 0-1 |
| `sizing_error_score` | numeric | 0-1 |
| `variance_score` | numeric | 0-1 |
| `llm_narrative` | text | |
| `created_at` | timestamptz | |

### `trading_config`
| Column | Type | Notes |
|---|---|---|
| `key` | text PK | |
| `value` | text | stored as string, parsed at load |
| `updated_at` | timestamptz | |
| `updated_by` | text | 'post_mortem_agent' \| 'human' |

Default keys and bounds:
- `confidence_threshold`: 0.03, bounds [0.01, 0.10]
- `kelly_fraction`: 0.25, bounds [0.10, 0.50]
- `max_category_exposure`: 0.20, bounds [0.10, 0.50]
- `max_total_exposure`: 0.40, bounds [0.20, 0.60]
- `daily_loss_limit`: 0.10, bounds [0.05, 0.20]

### `circuit_breaker_state`
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `breaker_type` | text | 'daily_loss' \| 'consecutive_losses' \| 'exposure' \| 'api_error' |
| `triggered_at` | timestamptz | |
| `resume_at` | timestamptz | |
| `consecutive_loss_count` | int | running counter, reset on win |
| `daily_loss_amount` | numeric | reset at midnight UTC |

### `trade_research_log` (optional, for post-mortem debugging)
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `trade_id` | uuid FK → paper_trades | |
| `signal_breakdown` | jsonb | per-source sentiment scores |
| `rf_probability` | numeric | base Phase 9 model output |
| `llm_adjustment` | numeric | delta applied by LLM calibrator |
| `final_edge` | numeric | |
| `created_at` | timestamptz | |

---

## File Structure

```
packages/trading_swarm/
  src/sharpedge_trading/
    events/
      types.py              # all event dataclasses
      bus.py                # asyncio.Queue wrapper
    agents/
      scan_agent.py
      research_agent.py
      prediction_agent.py
      portfolio_manager.py
      risk_agent.py
      monitor_agent.py
      post_mortem_agent.py
    execution/
      base_executor.py      # abstract interface
      paper_executor.py
      kalshi_executor.py
    signals/
      reddit_client.py
      twitter_client.py     # feature-flagged
      news_rss_client.py
      llm_calibrator.py     # Claude API wrapper with timeout + fallback
    config.py               # loads trading_config from Supabase at startup
    daemon.py               # main entry point, startup validation
  tests/
    test_scan_agent.py
    test_prediction_agent.py
    test_risk_agent.py
    test_paper_executor.py
    test_post_mortem_agent.py
    test_portfolio_manager.py
    test_llm_calibrator.py
    test_integration_pipeline.py
  pyproject.toml
```

---

## Dependencies Added

| Package | Purpose | Cost |
|---|---|---|
| `praw` | Reddit API | Free |
| `tweepy` | Twitter/X API | Free (API key required) |
| `httpx` | Async HTTP for RSS/news | Free |

All other dependencies (Claude API, Kalshi client, Polymarket client, Phase 9 models, BLS/FEC/CoinGecko clients) already exist in the monorepo.

---

## Testing Strategy

- **Unit tests:** All agents tested with mocks (London School TDD). No live API calls.
- **LLM calibrator:** Tested with mock Claude responses including timeout and error cases.
- **Paper executor:** Tested against fixed virtual bankroll fixture including slippage model.
- **Circuit breakers:** Logic unit-tested in isolation, including bound enforcement.
- **Portfolio manager:** Concurrency tested with simulated race conditions.
- **Integration test:** Full pipeline with mock Kalshi response, verifies trade reaches `paper_trades` in Supabase test schema, post-mortem writes to `trade_post_mortems`.

---

## Key Improvements Over Original Design

1. **Feature-flagged Twitter** — optional, cost-aware, rate-limited with fallback
2. **Phase 9 RF models reused** — no rebuilding prediction layer from scratch; startup validation ensures models exist
3. **Portfolio Manager** — prevents silent correlated over-exposure with advisory locking
4. **Single smart Post-Mortem Agent** — structured attribution replaces 5 undifferentiated agents; bounded auto-adjustment prevents runaway config drift
5. **Paper execution as first-class concept** — with hardened promotion gate (50 trades, Sharpe, win rate, ECE)
6. **Kalshi vs Polymarket separation** — Kalshi is REST API execution, Polymarket is data/consensus only
7. **Signal freshness enforcement** — time-decay and staleness discarding prevent stale signal trades
8. **LLM calibrator with fallback** — Claude API with 10s timeout, returns base RF prob on failure (no position blocked)
9. **Bounded learning loop** — hard min/max on all auto-adjustable parameters; manual review gate after 5 consecutive adjustments
10. **Proper Kelly formula** — standard binary Kelly with clamped output, handles edge cases near 0/1
