# SharpEdge Trading Swarm — Design Spec

**Date:** 2026-03-16
**Status:** Approved
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
[Prediction Agent]    — Phase 9 RF model + LLM calibration
     ↓ PredictionEvent (only if edge > 3%)
[Portfolio Manager]   — cross-market exposure check
     ↓ ApprovedEvent
[Risk Agent]          — fractional Kelly sizing + circuit breakers
     ↓ ExecutionEvent
[Execution Layer]     — PaperExecutor | KalshiExecutor (env-flag)
     ↓
[Monitor Agent]       — polls every 10 min until settlement
     ↓ ResolutionEvent
[Post-Mortem Agent]   — structured loss attribution → learning update
```

---

## Agent Specifications

### 1. Scan Agent

- **Trigger:** Every 5 minutes via asyncio loop
- **Input:** Kalshi API — all active markets
- **Filters:**
  - Minimum liquidity: $500
  - Time to resolution: 1 hour – 30 days
  - Anomaly detection: price momentum spikes, spread widening vs. 24h baseline
- **Output:** `OpportunityEvent` per flagged market
- **Builds on:** existing `pm_edge_scanner.py`

### 2. Research Agent

- **Trigger:** One spawned per `OpportunityEvent`, run in parallel
- **Signal sources (by priority weight):**
  1. **Authoritative (high weight):** BLS client, FEC client, CoinGecko client, AP/Reuters RSS feeds
  2. **Cross-venue consensus (high weight):** Polymarket price for same event
  3. **Reddit (medium weight):** PRAW, free tier, 100 req/min
  4. **Twitter/X (medium weight, optional):** Tweepy, feature-flagged via `ENABLE_TWITTER_SIGNALS=true/false`, requires paid API key ($100/month Basic)
- **Processing:** LLM (existing Claude copilot tools) summarizes headlines + Polymarket/Kalshi dislocation into sentiment score
- **Output:** `ResearchEvent` with narrative summary + per-source sentiment scores

### 3. Prediction Agent

- **Input:** `ResearchEvent`
- **Model:** Phase 9 RandomForest resolution model for the market's category (political, economic, crypto, entertainment, weather)
- **Calibration:** LLM adjusts base RF probability using research narrative
- **Edge calculation:** `edge = |model_prob - kalshi_price| - transaction_fee`
- **Gate:** Only emits `PredictionEvent` if `edge > 3%` and confidence above `confidence_threshold` (loaded from `trading_config`)
- **Output:** `PredictionEvent` with predicted probability, edge, and confidence score

### 4. Portfolio Manager

- **Input:** `PredictionEvent`
- **Checks:**
  - Max exposure per market: 5% of bankroll
  - Max exposure per category: 20% of bankroll
  - Max total open exposure: 40% of bankroll
  - Correlation flag: detects multiple open positions resolving on same underlying event
- **Output:** `ApprovedEvent` or silent drop with log entry

### 5. Risk Agent

- **Input:** `ApprovedEvent`
- **Sizing:** Fractional Kelly at 0.25×: `size = 0.25 × (edge / (1 - kalshi_price)) × bankroll`
- **Circuit breakers (auto-pause):**
  - Daily loss > 10% of bankroll → pause 24 hours
  - 5 consecutive losses → pause 4 hours, trigger post-mortem on all 5
  - Total open exposure > 40% → no new positions until some resolve
  - Kalshi API error rate > 20% in 5 minutes → pause until recovery
- **Output:** `ExecutionEvent` with approved position size

### 6. Execution Layer

Abstract `BaseExecutor` interface with two implementations:

- **`PaperExecutor`** (default):
  - Simulates fills at current Kalshi mid-price
  - Tracks virtual $10,000 bankroll
  - Writes to `paper_trades` Supabase table
  - Estimates slippage for realism

- **`KalshiExecutor`** (live):
  - Places real orders via Kalshi REST API
  - Same interface as PaperExecutor
  - Activated by `TRADING_MODE=live`

Controlled by `TRADING_MODE=paper|live` env var. No code changes required to switch.

### 7. Monitor Agent

- **Trigger:** Polls every 10 minutes for each open position
- **Input:** `open_positions` Supabase table
- **Action:** Checks Kalshi settlement status
- **Output:** `ResolutionEvent` with actual P&L on settlement

### 8. Post-Mortem Agent

- **Trigger:** Every `ResolutionEvent` for a loss
- **Attribution dimensions:**
  1. **Model error** — predicted probability significantly wrong vs. outcome
  2. **Signal error** — research narrative contradicted by outcome
  3. **Sizing error** — Kelly fraction too aggressive for actual edge
  4. **Variance** — legitimate low-probability outcome, no system fault
- **Output:** Written to `trade_post_mortems` Supabase table
- **Learning loop:** After 3+ losses of same attribution type → auto-adjust:
  - Model errors → raise `confidence_threshold`
  - Signal errors → reduce weight of offending signal source
  - Sizing errors → reduce `kelly_fraction`
  - Updates persisted to `trading_config` table, reloaded at next cycle

---

## Paper Trading & Promotion Gate

### Paper Mode (Default)

- Virtual bankroll: $10,000
- All trades simulated via `PaperExecutor`
- Full pipeline runs identically to live mode

### Promotion Gate

Before `TRADING_MODE=live` is accepted, daemon validates at startup:

| Requirement | Threshold |
|---|---|
| Minimum paper trading period | 30 days |
| Minimum resolved trades | 20 trades |
| Expected value | Positive across all closed trades |
| Max drawdown | < 20% of starting bankroll |

If gate fails, daemon prints a report and refuses to start in live mode.

### Live Mode

- Starts with $2,000 real bankroll
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

---

## Data Model (Supabase)

### `paper_trades`
Columns: `id`, `market_id`, `direction`, `size`, `entry_price`, `exit_price`, `pnl`, `category`, `trading_mode`, `timestamp`

### `open_positions`
Columns: `id`, `market_id`, `size`, `entry_price`, `expected_resolution_time`, `trading_mode`, `opened_at`

### `trade_post_mortems`
Columns: `id`, `trade_id`, `model_error_score`, `signal_error_score`, `sizing_error_score`, `variance_score`, `llm_narrative`, `created_at`

### `trading_config`
Columns: `key`, `value`, `updated_at`
Keys: `confidence_threshold` (default: 0.03), `kelly_fraction` (default: 0.25), `max_category_exposure` (default: 0.20), `max_total_exposure` (default: 0.40), `daily_loss_limit` (default: 0.10)

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
    config.py               # loads trading_config from Supabase at startup
    daemon.py               # main entry point
  tests/
    test_scan_agent.py
    test_prediction_agent.py
    test_risk_agent.py
    test_paper_executor.py
    test_post_mortem_agent.py
  pyproject.toml
```

---

## Dependencies Added

| Package | Purpose | Cost |
|---|---|---|
| `praw` | Reddit API | Free |
| `tweepy` | Twitter/X API | Free (API key required) |
| `httpx` | Async HTTP for RSS/news | Free |

All other dependencies already exist in the monorepo.

---

## Testing Strategy

- **Unit tests:** All agents tested with mocks (London School TDD). No live API calls.
- **Paper executor:** Tested against fixed virtual bankroll fixture.
- **Circuit breakers:** Logic unit-tested in isolation.
- **Integration test:** Full pipeline with mock Kalshi response, verifies trade reaches `paper_trades` in Supabase test schema.

---

## Key Improvements Over Original Design

1. **No Twitter dependency at start** — feature-flagged, optional, cost-aware
2. **Phase 9 RF models reused** — no rebuilding prediction layer from scratch
3. **Portfolio Manager added** — prevents silent correlated over-exposure
4. **Single smart Post-Mortem Agent** — structured attribution replaces 5 undifferentiated agents
5. **Paper execution as first-class concept** — with promotion gate before live
6. **Kalshi vs Polymarket separation** — Kalshi is REST API execution, Polymarket is data/consensus only
7. **Self-adjusting thresholds** — learning loop updates live config, not code
