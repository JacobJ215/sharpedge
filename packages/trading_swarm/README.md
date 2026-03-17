# SharpEdge Trading Swarm

Autonomous multi-agent trading daemon for Kalshi prediction markets. Scans markets, researches signals, predicts edge, manages risk, executes paper (then live) trades, and learns from losses — all without human intervention per trade.

---

## Table of Contents

- [Architecture](#architecture)
- [Agents](#agents)
- [Setup](#setup)
- [Configuration](#configuration)
- [Running](#running)
- [Paper Mode & Promotion Gate](#paper-mode--promotion-gate)
- [Database](#database)
- [Signal Sources](#signal-sources)
- [Circuit Breakers](#circuit-breakers)
- [Learning Loop](#learning-loop)
- [Testing](#testing)

---

## Architecture

The daemon is a standalone Python asyncio process (`daemon.py`) that chains agents together via typed `asyncio.Queue` channels. No Redis or external message broker required.

```
[Scan Agent]          every 5 min — scans all active Kalshi markets
     ↓ OpportunityEvent
[Research Agents]     parallel, one per opportunity
     ↓ ResearchEvent
[Prediction Agent]    Phase 9 RF model + Claude LLM calibration
     ↓ PredictionEvent  (only if edge > 3%)
[Portfolio Manager]   cross-market exposure check (Supabase advisory lock)
     ↓ ApprovedEvent
[Risk Agent]          fractional Kelly sizing + circuit breakers
     ↓ ExecutionEvent
[Execution Layer]     PaperExecutor | KalshiExecutor  (env-flag)
     ↓
[Monitor Agent]       polls every 60 sec until settlement
     ↓ ResolutionEvent
[Post-Mortem Agent]   structured loss attribution → bounded learning update
```

All agents run as concurrent `asyncio.Task`s inside a single `asyncio.TaskGroup`. The `EventBus` has six typed queues — one per stage — so each agent reads only its own input and writes only its own output.

---

## Agents

### Scan Agent
- Polls Kalshi every 5 minutes for all open markets
- Filters by: minimum liquidity $500, time-to-resolution 1 hr – 30 days
- Anomaly detection (requires 7-day price history): price momentum spike > 15% vs. 24h baseline, spread widening > 2× baseline
- If Kalshi API is down: logs error, skips cycle, daemon continues

### Research Agent
- Spawns one coroutine per `OpportunityEvent`, up to 5 concurrent
- Fetches signals from AP/Reuters RSS, Polymarket consensus price, Reddit (PRAW), Twitter/X (optional)
- Signal freshness rules: signals older than `time_to_resolution / 2` discarded; signals older than 1 hour get 50% confidence penalty
- Claude API (`claude-sonnet-4-6`) summarises headlines into a narrative + sentiment score
- On LLM timeout (10s): falls back to base RF probability, no position blocked

### Prediction Agent
- Loads Phase 9 RandomForest models (`data/models/pm/{category}.joblib`)
- Five categories: `political`, `economic`, `crypto`, `entertainment`, `weather`
- LLM calibrator adjusts base RF probability by ±10% max
- Edge gate: only emits `PredictionEvent` if `|calibrated_prob - kalshi_price| - 0.001 > 3%`
- Startup: validates all 5 model files exist; live mode refuses to start without them

### Portfolio Manager
- Checks cross-market exposure before approving any trade
- Hard limits: 5% per market, 20% per category, 40% total open exposure
- Correlation check: blocks multiple positions resolving on the same event series
- Uses Supabase advisory lock to prevent race conditions between concurrent research agents

### Risk Agent
- Fractional Kelly sizing: `f* = (p × b - q) / b`, then `size = 0.25 × f* × bankroll`
- Position size clamped to `[0.1%, 5%]` of bankroll regardless of Kelly output
- Enforces circuit breakers before every trade (see [Circuit Breakers](#circuit-breakers))

### Execution Layer
Two implementations behind an abstract `BaseExecutor` interface, selected by `TRADING_MODE` env var:

| Mode | Executor | Writes to |
|------|----------|-----------|
| `paper` (default) | `PaperExecutor` | `paper_trades` table |
| `live` | `KalshiExecutor` | `live_trades` table + real Kalshi order |

Both use timestamp-based idempotency keys to prevent duplicate fills on retry.

`PaperExecutor` slippage model: `slippage = spread/2 + (position_size / total_market_volume) × 0.001`

### Monitor Agent
- Polls `open_positions` table every 60 seconds
- Checks Kalshi settlement status via `GET /markets/{ticker}`
- On settlement: computes P&L, emits `ResolutionEvent`, marks position as `settled`
  - YES win: `pnl = size × (1 - entry_price)`
  - NO loss: `pnl = -size × entry_price`

### Post-Mortem Agent
- Triggers on every `ResolutionEvent` where `pnl < 0`
- Classifies loss into four attribution dimensions:
  | Dimension | Condition |
  |-----------|-----------|
  | Model error | `\|calibrated_prob - outcome\| > 0.30` |
  | Signal error | LLM calibration pushed probability in wrong direction |
  | Sizing error | Position > 3% of bankroll |
  | Variance | `calibrated_prob < 0.35` and lost (legitimate low-prob outcome) |
- Fetches `calibrated_prob` from `trade_research_log` by `trade_id` (falls back to 0.5)
- Writes attribution scores + LLM narrative to `trade_post_mortems`
- See [Learning Loop](#learning-loop)

---

## Setup

### Prerequisites

- Python 3.12+
- `uv` (recommended) or `pip`
- Docker + Docker Compose (for containerised deployment)

### Install

```bash
cd packages/trading_swarm
uv sync
```

### Database

Run migration `007_trading_swarm.sql` in the Supabase SQL Editor:

```
packages/database/src/sharpedge_db/migrations/007_trading_swarm.sql
```

This creates all 7 required tables. The migration is idempotent — safe to re-run.

---

## Configuration

All configuration is via environment variables. Copy `.env.example` to `.env` and fill in values. **Never commit `.env`.**

### Required

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key (not anon key) |
| `ANTHROPIC_API_KEY` | Claude API key (for LLM calibration) |
| `KALSHI_API_KEY` | Kalshi API key UUID |
| `KALSHI_PRIVATE_KEY_PEM` | PEM-encoded RSA private key for Kalshi request signing |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `TRADING_MODE` | `paper` | `paper` or `live` |
| `KALSHI_ENV` | `prod` | `demo` or `prod` |
| `PAPER_BANKROLL` | `10000` | Starting virtual bankroll ($) |
| `LIVE_BANKROLL` | `2000` | Starting real bankroll ($) |
| `MODEL_DIR` | `data/models/pm` | Path to `.joblib` model files |
| `ENABLE_TWITTER_SIGNALS` | `false` | Enable Twitter/X signal source |
| `TWITTER_BEARER_TOKEN` | — | Required if `ENABLE_TWITTER_SIGNALS=true` |
| `REDDIT_CLIENT_ID` | — | Reddit API credentials (PRAW) |
| `REDDIT_CLIENT_SECRET` | — | Reddit API credentials (PRAW) |

### Runtime config (in Supabase `trading_config` table)

These are loaded at startup from Supabase and adjusted by the learning loop. Hard bounds enforced.

| Key | Default | Bounds | Adjusted by |
|-----|---------|--------|-------------|
| `confidence_threshold` | 0.03 | [0.01, 0.10] | Model errors |
| `kelly_fraction` | 0.25 | [0.10, 0.50] | Sizing errors |
| `max_category_exposure` | 0.20 | [0.10, 0.50] | — |
| `max_total_exposure` | 0.40 | [0.20, 0.60] | — |
| `daily_loss_limit` | 0.10 | [0.05, 0.20] | — |

---

## Running

### Docker (recommended)

```bash
# Paper mode (default)
docker compose up trading-swarm

# Live mode — only after passing promotion gate
TRADING_MODE=live docker compose up trading-swarm

# Rebuild after code changes
docker compose build trading-swarm && docker compose up trading-swarm
```

Logs are written to stdout (JSON driver with 50 MB rotation). Follow them:

```bash
docker compose logs -f trading-swarm
```

### Direct (development)

```bash
cd packages/trading_swarm
uv run python -m sharpedge_trading.daemon
```

### Demo environment (safe for testing)

Set `KALSHI_ENV=demo` to hit the Kalshi demo API. No real money, no real orders.

---

## Paper Mode & Promotion Gate

The daemon starts in **paper mode** by default. It runs the full pipeline identically to live mode, but all trades are simulated via `PaperExecutor` against a virtual $10,000 bankroll.

### Switching to live mode

Set `TRADING_MODE=live`. The daemon validates all promotion gate requirements at startup before accepting live mode. If any check fails, it prints a per-requirement report and exits.

| Requirement | Threshold | Rationale |
|-------------|-----------|-----------|
| Min paper trading period | ≥ 30 days | Regime coverage |
| Min resolved trades | ≥ 50 trades | Statistical significance |
| Min days between first and last trade | ≥ 10 days | Prevents clustering |
| Expected value | EV > 0 | Basic profitability |
| Sharpe ratio | > 0.5 | Risk-adjusted consistency |
| Win rate | > 45% | Execution sanity check |
| Max drawdown | < 20% of $10,000 | Downside protection |
| ECE calibration | ECE < 10% | Phase 9 model validity |

Live mode starts with a $2,000 real bankroll (20% of paper bankroll — conservative initial sizing while validating live execution).

---

## Database

Seven tables, all created by `007_trading_swarm.sql`:

| Table | Written by | Read by |
|-------|-----------|---------|
| `paper_trades` | `PaperExecutor` | Promotion gate, monitor agent |
| `live_trades` | `KalshiExecutor` | Monitor agent |
| `open_positions` | Both executors | Monitor agent, portfolio manager |
| `trade_post_mortems` | Post-mortem agent | — |
| `trading_config` | Post-mortem agent, humans | All agents (at startup) |
| `circuit_breaker_state` | Risk agent | Risk agent |
| `trade_research_log` | Prediction agent | Post-mortem agent |

All tables have Row Level Security enabled. Service role key required.

---

## Signal Sources

| Source | Category | Cost | Rate limit | Flag |
|--------|----------|------|-----------|------|
| AP/Reuters RSS | All | Free | — | Always on |
| Polymarket price | All | Free | — | Always on |
| BLS economic data | Economics | Free | — | Always on |
| FEC filings | Politics | Free | — | Always on |
| CoinGecko | Crypto | Free | — | Always on |
| Reddit (PRAW) | All | Free | 100 req/min | Always on |
| Twitter/X (Tweepy) | All | $100/mo | 500K tokens/mo | `ENABLE_TWITTER_SIGNALS=true` |

**Signal freshness rules:**
- Signals older than `time_to_resolution / 2` → discarded entirely
- Signals older than 1 hour → 50% confidence penalty

Twitter has exponential backoff on 429 errors and falls back to Reddit + authoritative sources if unavailable.

---

## Circuit Breakers

The Risk Agent checks circuit breakers before every trade. All breaker state is persisted to `circuit_breaker_state` in Supabase.

| Trigger | Pause duration | Action |
|---------|---------------|--------|
| Daily loss > 10% of bankroll | 24 hours | No new positions |
| 5 consecutive losses | 4 hours | No new positions + post-mortem on all 5 |
| Total open exposure > 40% | Until positions resolve | No new positions |
| Kalshi API error rate > 20% in 5 min | Until recovery | No new positions |

---

## Learning Loop

The Post-Mortem Agent automatically adjusts parameters after repeated losses of the same type. All adjustments are bounded and logged.

**Trigger:** 3+ losses of the same attribution type (counter tracked in memory, resets on process restart).

| Attribution type | Adjustment | Bounds |
|-----------------|-----------|--------|
| Model error | Raise `confidence_threshold` by +0.005 | max 0.10 |
| Signal error | Reduce offending source weight by 10% | min weight 0.1 |
| Sizing error | Reduce `kelly_fraction` by -0.02 | min 0.10 |
| Variance | No adjustment (legitimate outcome) | — |

**Auto-pause gate:** After 5 consecutive auto-adjustments of any type, auto-learning is paused and a flag is written to `trading_config` (`auto_learning_paused = 1`). Manual review required — set `auto_learning_paused = 0` in Supabase to resume.

---

## Testing

### Unit + integration tests (184 tests, always run)

```bash
cd packages/trading_swarm
uv run pytest tests/ --ignore=tests/contract -q
```

All 184 tests use mocked dependencies — no credentials required.

### Smoke tests (8 tests, always run)

Verify component wiring, import resolution, and error handling without external APIs:

```bash
uv run pytest tests/smoke/ -v
```

### Contract tests (12 tests, require credentials)

Hit real APIs. Skipped automatically if credentials are missing. Run after setting up `.env`:

```bash
uv run pytest tests/contract/ -v
```

What each contract test validates:

| File | Validates |
|------|-----------|
| `test_kalshi_contract.py` | Kalshi API response shape, price normalization, `scan_once()` end-to-end |
| `test_anthropic_contract.py` | Claude API returns float in [0.05, 0.95], respects ±10% cap |
| `test_supabase_contract.py` | All 4 tables exist with expected schema, inserts + cleanup |

### Run everything

```bash
uv run pytest tests/ -q
# Expected: 184 passed, 12 skipped (contract tests without credentials)
```
