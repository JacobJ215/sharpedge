# SharpEdge Trading Swarm Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully autonomous multi-agent Kalshi trading swarm with paper-first execution, fractional Kelly risk management, and a self-adjusting post-mortem learning loop.

**Architecture:** Event-driven pipeline using `asyncio.Queue` chains. Seven agents communicate via typed events. A `TRADING_MODE=paper|live` env var controls whether orders hit a virtual $10k bankroll or real Kalshi API. No Redis — pure Python asyncio + Supabase.

**Tech Stack:** Python 3.12, asyncio, httpx, praw, anthropic SDK (claude-sonnet-4-6), Supabase, existing kalshi_client/polymarket_client/BLS/FEC/CoinGecko clients from monorepo.

**Spec:** `docs/superpowers/specs/2026-03-16-trading-swarm-design.md`

---

## File Map

**New package: `packages/trading_swarm/`**

| File | Responsibility |
|---|---|
| `pyproject.toml` | Package manifest, workspace registration |
| `src/sharpedge_trading/events/types.py` | All event dataclasses (OpportunityEvent, ResearchEvent, etc.) |
| `src/sharpedge_trading/events/bus.py` | asyncio.Queue wrapper with typed put/get |
| `src/sharpedge_trading/config.py` | Load/update trading_config from Supabase; enforce bounds |
| `src/sharpedge_trading/signals/llm_calibrator.py` | Claude API prob adjustment, 10s timeout, fallback |
| `src/sharpedge_trading/signals/reddit_client.py` | PRAW wrapper, semaphore, sentiment score |
| `src/sharpedge_trading/signals/twitter_client.py` | Tweepy wrapper, feature-flagged |
| `src/sharpedge_trading/signals/news_rss_client.py` | httpx RSS fetch, freshness filter |
| `src/sharpedge_trading/agents/scan_agent.py` | Kalshi market scan, anomaly detection, emit OpportunityEvent |
| `src/sharpedge_trading/agents/research_agent.py` | Parallel signal fetch per opportunity, emit ResearchEvent |
| `src/sharpedge_trading/agents/prediction_agent.py` | Phase 9 RF model + LLM calibration, edge gate |
| `src/sharpedge_trading/agents/portfolio_manager.py` | Exposure checks with advisory lock, emit ApprovedEvent |
| `src/sharpedge_trading/agents/risk_agent.py` | Kelly sizing, circuit breakers, emit ExecutionEvent |
| `src/sharpedge_trading/agents/monitor_agent.py` | Poll open positions every 60s, emit ResolutionEvent |
| `src/sharpedge_trading/agents/post_mortem_agent.py` | Loss attribution, bounded config updates |
| `src/sharpedge_trading/execution/base_executor.py` | Abstract BaseExecutor interface |
| `src/sharpedge_trading/execution/paper_executor.py` | Simulate fills, track virtual bankroll, slippage model |
| `src/sharpedge_trading/execution/kalshi_executor.py` | Real Kalshi order placement |
| `src/sharpedge_trading/daemon.py` | Wire all agents, startup validation, promotion gate |

**New migration: `packages/database/src/sharpedge_db/migrations/007_trading_swarm.sql`**

Creates: `paper_trades`, `open_positions`, `trade_post_mortems`, `trading_config`, `circuit_breaker_state`, `trade_research_log`

---

## Task 1: Package Scaffold

**Files:**
- Create: `packages/trading_swarm/pyproject.toml`
- Create: `packages/trading_swarm/src/sharpedge_trading/__init__.py`
- Create: `packages/trading_swarm/src/sharpedge_trading/events/__init__.py`
- Create: `packages/trading_swarm/src/sharpedge_trading/agents/__init__.py`
- Create: `packages/trading_swarm/src/sharpedge_trading/execution/__init__.py`
- Create: `packages/trading_swarm/src/sharpedge_trading/signals/__init__.py`
- Modify: `pyproject.toml` (root) — already has `packages/*` glob, no change needed
- Create: `packages/trading_swarm/tests/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
# packages/trading_swarm/pyproject.toml
[project]
name = "sharpedge-trading"
version = "0.1.0"
description = "Autonomous multi-agent prediction market trading swarm"
requires-python = ">=3.12"
dependencies = [
    "httpx>=0.27",
    "pydantic>=2.0",
    "praw>=7.7",
    "anthropic>=0.40",
    "sharpedge-shared",
    "sharpedge-feeds",
    "sharpedge-models",
    "sharpedge-db",
]

[project.optional-dependencies]
twitter = ["tweepy>=4.14"]

[tool.uv.sources]
sharpedge-shared = { workspace = true }
sharpedge-feeds = { workspace = true }
sharpedge-models = { workspace = true }
sharpedge-db = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/sharpedge_trading"]
```

- [ ] **Step 2: Create all `__init__.py` files (empty)**

```bash
mkdir -p packages/trading_swarm/src/sharpedge_trading/{events,agents,execution,signals}
mkdir -p packages/trading_swarm/tests
touch packages/trading_swarm/src/sharpedge_trading/__init__.py
touch packages/trading_swarm/src/sharpedge_trading/{events,agents,execution,signals}/__init__.py
touch packages/trading_swarm/tests/__init__.py
```

- [ ] **Step 3: Install package into workspace**

```bash
cd /path/to/sharpedge && uv sync
```
Expected: resolves without error, `sharpedge-trading` appears in lock file.

- [ ] **Step 4: Commit**

```bash
git add packages/trading_swarm/
git commit -m "feat(trading): scaffold trading_swarm package"
```

---

## Task 2: Supabase Migration

**Files:**
- Create: `packages/database/src/sharpedge_db/migrations/007_trading_swarm.sql`

- [ ] **Step 1: Write migration**

```sql
-- packages/database/src/sharpedge_db/migrations/007_trading_swarm.sql
-- Migration 007: Trading Swarm tables

-- paper_trades: every simulated and live order
CREATE TABLE IF NOT EXISTS paper_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    market_id TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('yes', 'no')),
    size NUMERIC NOT NULL,
    entry_price NUMERIC NOT NULL,
    exit_price NUMERIC,
    pnl NUMERIC,
    confidence_score NUMERIC,
    category TEXT,
    trading_mode TEXT NOT NULL CHECK (trading_mode IN ('paper', 'live')),
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    actual_outcome BOOLEAN
);
CREATE INDEX IF NOT EXISTS idx_paper_trades_market ON paper_trades (market_id);
CREATE INDEX IF NOT EXISTS idx_paper_trades_mode ON paper_trades (trading_mode);
ALTER TABLE paper_trades ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access to paper_trades"
    ON paper_trades FOR ALL TO service_role USING (true);

-- open_positions: currently monitored bets
CREATE TABLE IF NOT EXISTS open_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    market_id TEXT NOT NULL UNIQUE,
    size NUMERIC NOT NULL,
    entry_price NUMERIC NOT NULL,
    category TEXT,
    expected_resolution_time TIMESTAMPTZ,
    trading_mode TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'settling', 'settled')),
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE open_positions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access to open_positions"
    ON open_positions FOR ALL TO service_role USING (true);

-- trade_post_mortems: loss attribution records
CREATE TABLE IF NOT EXISTS trade_post_mortems (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_id UUID NOT NULL REFERENCES paper_trades(id),
    model_error_score NUMERIC,
    signal_error_score NUMERIC,
    sizing_error_score NUMERIC,
    variance_score NUMERIC,
    llm_narrative TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE trade_post_mortems ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access to trade_post_mortems"
    ON trade_post_mortems FOR ALL TO service_role USING (true);

-- trading_config: live adjustable parameters
CREATE TABLE IF NOT EXISTS trading_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'system'
);
INSERT INTO trading_config (key, value, updated_by) VALUES
    ('confidence_threshold', '0.03', 'system'),
    ('kelly_fraction', '0.25', 'system'),
    ('max_category_exposure', '0.20', 'system'),
    ('max_total_exposure', '0.40', 'system'),
    ('daily_loss_limit', '0.10', 'system'),
    ('auto_adjust_count', '0', 'system'),
    ('auto_adjust_paused', 'false', 'system')
ON CONFLICT (key) DO NOTHING;
ALTER TABLE trading_config ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access to trading_config"
    ON trading_config FOR ALL TO service_role USING (true);

-- circuit_breaker_state: pause tracking
CREATE TABLE IF NOT EXISTS circuit_breaker_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    breaker_type TEXT NOT NULL,
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resume_at TIMESTAMPTZ NOT NULL,
    consecutive_loss_count INTEGER DEFAULT 0,
    daily_loss_amount NUMERIC DEFAULT 0
);
ALTER TABLE circuit_breaker_state ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access to circuit_breaker_state"
    ON circuit_breaker_state FOR ALL TO service_role USING (true);

-- trade_research_log: signal breakdown for debugging
CREATE TABLE IF NOT EXISTS trade_research_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_id UUID REFERENCES paper_trades(id),
    signal_breakdown JSONB,
    rf_probability NUMERIC,
    llm_adjustment NUMERIC,
    final_edge NUMERIC,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE trade_research_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access to trade_research_log"
    ON trade_research_log FOR ALL TO service_role USING (true);
```

- [ ] **Step 2: Apply migration to Supabase**

```bash
# Via Supabase dashboard SQL editor, or:
PGPASSWORD=$DB_PASSWORD psql $DATABASE_URL -f packages/database/src/sharpedge_db/migrations/007_trading_swarm.sql
```
Expected: all 6 tables created with no errors.

- [ ] **Step 3: Commit**

```bash
git add packages/database/src/sharpedge_db/migrations/007_trading_swarm.sql
git commit -m "feat(db): add trading swarm tables (migration 007)"
```

---

## Task 3: Event Types & Bus

**Files:**
- Create: `packages/trading_swarm/src/sharpedge_trading/events/types.py`
- Create: `packages/trading_swarm/src/sharpedge_trading/events/bus.py`
- Create: `packages/trading_swarm/tests/test_events.py`

- [ ] **Step 1: Write failing test**

```python
# packages/trading_swarm/tests/test_events.py
import asyncio
import pytest
from sharpedge_trading.events.types import OpportunityEvent, ResearchEvent, PredictionEvent
from sharpedge_trading.events.bus import EventBus

def test_opportunity_event_has_required_fields():
    e = OpportunityEvent(market_id="BTCUSD-24", category="crypto", kalshi_price=0.45, liquidity=1200.0, time_to_resolution_hours=48.0)
    assert e.market_id == "BTCUSD-24"
    assert e.category == "crypto"

@pytest.mark.asyncio
async def test_bus_put_and_get():
    bus = EventBus()
    e = OpportunityEvent(market_id="X", category="economic", kalshi_price=0.3, liquidity=500.0, time_to_resolution_hours=24.0)
    await bus.put_opportunity(e)
    result = await asyncio.wait_for(bus.get_opportunity(), timeout=1.0)
    assert result.market_id == "X"
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd packages/trading_swarm && pytest tests/test_events.py -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement types.py**

```python
# src/sharpedge_trading/events/types.py
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class OpportunityEvent:
    market_id: str
    category: str
    kalshi_price: float
    liquidity: float
    time_to_resolution_hours: float
    title: str = ""
    anomaly_flags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_now)


@dataclass
class SignalScore:
    source: str
    sentiment: float   # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    fetched_at: datetime = field(default_factory=_now)


@dataclass
class ResearchEvent:
    market_id: str
    category: str
    kalshi_price: float
    polymarket_price: float | None
    signals: list[SignalScore]
    narrative_summary: str
    time_to_resolution_hours: float
    created_at: datetime = field(default_factory=_now)


@dataclass
class PredictionEvent:
    market_id: str
    category: str
    kalshi_price: float
    calibrated_prob: float
    rf_base_prob: float
    llm_adjustment: float
    edge: float
    confidence_score: float
    time_to_resolution_hours: float
    research_snapshot: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)


@dataclass
class ApprovedEvent:
    prediction: PredictionEvent
    approved_size_pct: float  # fraction of bankroll


@dataclass
class ExecutionEvent:
    market_id: str
    direction: str  # 'yes' | 'no'
    size_dollars: float
    entry_price: float
    category: str
    confidence_score: float
    trading_mode: str  # 'paper' | 'live'


@dataclass
class ResolutionEvent:
    market_id: str
    trade_id: str
    outcome: bool
    pnl: float
    entry_price: float
    exit_price: float
    trading_mode: str
```

- [ ] **Step 4: Implement bus.py**

```python
# src/sharpedge_trading/events/bus.py
import asyncio
from .types import (
    OpportunityEvent, ResearchEvent, PredictionEvent,
    ApprovedEvent, ExecutionEvent, ResolutionEvent,
)


class EventBus:
    def __init__(self, maxsize: int = 0):
        self._opportunity: asyncio.Queue[OpportunityEvent] = asyncio.Queue(maxsize)
        self._research: asyncio.Queue[ResearchEvent] = asyncio.Queue(maxsize)
        self._prediction: asyncio.Queue[PredictionEvent] = asyncio.Queue(maxsize)
        self._approved: asyncio.Queue[ApprovedEvent] = asyncio.Queue(maxsize)
        self._execution: asyncio.Queue[ExecutionEvent] = asyncio.Queue(maxsize)
        self._resolution: asyncio.Queue[ResolutionEvent] = asyncio.Queue(maxsize)

    async def put_opportunity(self, e: OpportunityEvent) -> None:
        await self._opportunity.put(e)

    async def get_opportunity(self) -> OpportunityEvent:
        return await self._opportunity.get()

    async def put_research(self, e: ResearchEvent) -> None:
        await self._research.put(e)

    async def get_research(self) -> ResearchEvent:
        return await self._research.get()

    async def put_prediction(self, e: PredictionEvent) -> None:
        await self._prediction.put(e)

    async def get_prediction(self) -> PredictionEvent:
        return await self._prediction.get()

    async def put_approved(self, e: ApprovedEvent) -> None:
        await self._approved.put(e)

    async def get_approved(self) -> ApprovedEvent:
        return await self._approved.get()

    async def put_execution(self, e: ExecutionEvent) -> None:
        await self._execution.put(e)

    async def get_execution(self) -> ExecutionEvent:
        return await self._execution.get()

    async def put_resolution(self, e: ResolutionEvent) -> None:
        await self._resolution.put(e)

    async def get_resolution(self) -> ResolutionEvent:
        return await self._resolution.get()
```

- [ ] **Step 5: Run tests — verify pass**

```bash
pytest tests/test_events.py -v
```
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add packages/trading_swarm/src/sharpedge_trading/events/ packages/trading_swarm/tests/test_events.py
git commit -m "feat(trading): add event types and async bus"
```

---

## Task 4: Config Loader

**Files:**
- Create: `packages/trading_swarm/src/sharpedge_trading/config.py`
- Create: `packages/trading_swarm/tests/test_config.py`

- [ ] **Step 1: Write failing test**

```python
# packages/trading_swarm/tests/test_config.py
import pytest
from unittest.mock import MagicMock, patch
from sharpedge_trading.config import TradingConfig

def _mock_supabase(rows: list[dict]):
    client = MagicMock()
    client.table.return_value.select.return_value.execute.return_value.data = rows
    return client

def test_loads_defaults_from_supabase():
    rows = [
        {"key": "confidence_threshold", "value": "0.03"},
        {"key": "kelly_fraction", "value": "0.25"},
    ]
    cfg = TradingConfig(_mock_supabase(rows))
    assert cfg.confidence_threshold == 0.03
    assert cfg.kelly_fraction == 0.25

def test_clamps_out_of_bounds_value():
    rows = [{"key": "confidence_threshold", "value": "0.99"}]
    cfg = TradingConfig(_mock_supabase(rows))
    assert cfg.confidence_threshold == 0.10  # max bound

def test_update_writes_to_supabase():
    rows = [{"key": "kelly_fraction", "value": "0.25"}]
    client = _mock_supabase(rows)
    client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
    cfg = TradingConfig(client)
    cfg.update("kelly_fraction", 0.20, updated_by="post_mortem_agent")
    assert cfg.kelly_fraction == 0.20
```

- [ ] **Step 2: Run test — verify fails**

```bash
pytest tests/test_config.py -v
```

- [ ] **Step 3: Implement config.py**

```python
# src/sharpedge_trading/config.py
from dataclasses import dataclass
from datetime import datetime, timezone

_BOUNDS: dict[str, tuple[float, float]] = {
    "confidence_threshold": (0.01, 0.10),
    "kelly_fraction": (0.10, 0.50),
    "max_category_exposure": (0.10, 0.50),
    "max_total_exposure": (0.20, 0.60),
    "daily_loss_limit": (0.05, 0.20),
}

_DEFAULTS: dict[str, float] = {
    "confidence_threshold": 0.03,
    "kelly_fraction": 0.25,
    "max_category_exposure": 0.20,
    "max_total_exposure": 0.40,
    "daily_loss_limit": 0.10,
}


def _clamp(key: str, value: float) -> float:
    if key in _BOUNDS:
        lo, hi = _BOUNDS[key]
        return max(lo, min(hi, value))
    return value


class TradingConfig:
    def __init__(self, supabase_client):
        self._client = supabase_client
        self._values: dict[str, float] = dict(_DEFAULTS)
        self._load()

    def _load(self) -> None:
        rows = self._client.table("trading_config").select("key,value").execute().data or []
        for row in rows:
            key, raw = row["key"], row["value"]
            if key in _DEFAULTS:
                try:
                    self._values[key] = _clamp(key, float(raw))
                except ValueError:
                    pass

    @property
    def confidence_threshold(self) -> float:
        return self._values["confidence_threshold"]

    @property
    def kelly_fraction(self) -> float:
        return self._values["kelly_fraction"]

    @property
    def max_category_exposure(self) -> float:
        return self._values["max_category_exposure"]

    @property
    def max_total_exposure(self) -> float:
        return self._values["max_total_exposure"]

    @property
    def daily_loss_limit(self) -> float:
        return self._values["daily_loss_limit"]

    def update(self, key: str, value: float, updated_by: str = "system") -> None:
        clamped = _clamp(key, value)
        self._values[key] = clamped
        self._client.table("trading_config").upsert({
            "key": key,
            "value": str(clamped),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": updated_by,
        }).execute()
```

- [ ] **Step 4: Run tests — verify pass**

```bash
pytest tests/test_config.py -v
```

- [ ] **Step 5: Commit**

```bash
git add packages/trading_swarm/src/sharpedge_trading/config.py packages/trading_swarm/tests/test_config.py
git commit -m "feat(trading): add TradingConfig with Supabase-backed bounded params"
```

---

## Task 5: LLM Calibrator

**Files:**
- Create: `packages/trading_swarm/src/sharpedge_trading/signals/llm_calibrator.py`
- Create: `packages/trading_swarm/tests/test_llm_calibrator.py`

- [ ] **Step 1: Write failing tests**

```python
# packages/trading_swarm/tests/test_llm_calibrator.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sharpedge_trading.signals.llm_calibrator import LLMCalibrator

@pytest.mark.asyncio
async def test_returns_base_prob_on_timeout():
    calibrator = LLMCalibrator(api_key="test", timeout=0.001)
    with patch("anthropic.AsyncAnthropic") as mock_cls:
        mock_cls.return_value.messages.create = AsyncMock(side_effect=TimeoutError)
        result = await calibrator.calibrate(0.6, "some narrative")
    assert result == 0.6  # fallback

@pytest.mark.asyncio
async def test_clamps_adjustment_to_10pct():
    calibrator = LLMCalibrator(api_key="test")
    with patch.object(calibrator, "_ask_llm", return_value=0.25):  # huge positive
        result = await calibrator.calibrate(0.5, "bullish narrative")
    assert result == 0.60  # capped at base + 0.10

@pytest.mark.asyncio
async def test_clamps_to_zero_one():
    calibrator = LLMCalibrator(api_key="test")
    with patch.object(calibrator, "_ask_llm", return_value=-0.50):
        result = await calibrator.calibrate(0.05, "bearish narrative")
    assert result >= 0.0
```

- [ ] **Step 2: Run test — verify fails**

```bash
pytest tests/test_llm_calibrator.py -v
```

- [ ] **Step 3: Implement**

```python
# src/sharpedge_trading/signals/llm_calibrator.py
import asyncio
import logging
import os

logger = logging.getLogger("sharpedge.trading.llm_calibrator")

_SYSTEM = """You are a prediction market calibration assistant.
Given a base probability estimate and a research narrative, output a single float
representing the probability ADJUSTMENT (delta) to apply, between -0.10 and 0.10.
Respond with ONLY the float, e.g. 0.03 or -0.05."""


class LLMCalibrator:
    def __init__(self, api_key: str | None = None, timeout: float = 10.0, max_retries: int = 2):
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._timeout = timeout
        self._max_retries = max_retries

    async def _ask_llm(self, base_prob: float, narrative: str) -> float:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self._api_key)
        prompt = f"Base probability: {base_prob:.3f}\n\nResearch narrative:\n{narrative}\n\nAdjustment:"
        msg = await asyncio.wait_for(
            client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=16,
                system=_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            ),
            timeout=self._timeout,
        )
        raw = msg.content[0].text.strip()
        return float(raw)

    async def calibrate(self, base_prob: float, narrative: str) -> float:
        for attempt in range(self._max_retries + 1):
            try:
                delta = await self._ask_llm(base_prob, narrative)
                delta = max(-0.10, min(0.10, delta))
                result = base_prob + delta
                return max(0.0, min(1.0, result))
            except Exception as exc:
                if attempt == self._max_retries:
                    logger.warning("LLM calibration failed (%s), returning base_prob", exc)
                    return base_prob
        return base_prob
```

- [ ] **Step 4: Run tests — verify pass**

```bash
pytest tests/test_llm_calibrator.py -v
```

- [ ] **Step 5: Commit**

```bash
git add packages/trading_swarm/src/sharpedge_trading/signals/llm_calibrator.py packages/trading_swarm/tests/test_llm_calibrator.py
git commit -m "feat(trading): add LLM calibrator with timeout and fallback"
```

---

## Task 6: Signal Clients (Reddit, RSS, Twitter stub)

**Files:**
- Create: `packages/trading_swarm/src/sharpedge_trading/signals/reddit_client.py`
- Create: `packages/trading_swarm/src/sharpedge_trading/signals/news_rss_client.py`
- Create: `packages/trading_swarm/src/sharpedge_trading/signals/twitter_client.py`
- Create: `packages/trading_swarm/tests/test_signal_clients.py`

- [ ] **Step 1: Write failing tests**

```python
# packages/trading_swarm/tests/test_signal_clients.py
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
from sharpedge_trading.signals.news_rss_client import NewsRSSClient
from sharpedge_trading.signals.reddit_client import RedditClient
from sharpedge_trading.events.types import SignalScore

@pytest.mark.asyncio
async def test_rss_discards_stale_items():
    client = NewsRSSClient()
    old_time = datetime.now(timezone.utc) - timedelta(hours=10)
    fresh_time = datetime.now(timezone.utc) - timedelta(minutes=30)
    items = [
        {"title": "old news", "published": old_time, "summary": ""},
        {"title": "fresh news", "published": fresh_time, "summary": ""},
    ]
    with patch.object(client, "_fetch_items", return_value=items):
        scores = await client.get_signals("fed rate", max_age_hours=5.0)
    assert len(scores) == 1
    assert scores[0].source == "rss"

def test_reddit_returns_signal_score():
    client = RedditClient(client_id="x", client_secret="y", user_agent="test")
    mock_sub = MagicMock()
    mock_post = MagicMock()
    mock_post.title = "Fed hikes rates"
    mock_post.score = 100
    mock_post.created_utc = datetime.now(timezone.utc).timestamp()
    mock_sub.search.return_value = [mock_post]
    with patch.object(client, "_reddit") as mock_reddit:
        mock_reddit.subreddit.return_value = mock_sub
        scores = client.get_signals_sync("fed rate", subreddits=["economics"])
    assert len(scores) == 1
    assert isinstance(scores[0], SignalScore)
```

- [ ] **Step 2: Run — verify fails**

```bash
pytest tests/test_signal_clients.py -v
```

- [ ] **Step 3: Implement news_rss_client.py**

```python
# src/sharpedge_trading/signals/news_rss_client.py
import asyncio
import logging
from datetime import datetime, timezone, timedelta
import httpx
from ..events.types import SignalScore

logger = logging.getLogger("sharpedge.trading.rss")

_RSS_FEEDS = [
    "https://feeds.apnews.com/rss/apf-topnews",
    "https://feeds.reuters.com/reuters/topNews",
]


def _simple_sentiment(text: str) -> float:
    """Naive keyword sentiment: positive words +, negative words -."""
    pos = {"rise", "gain", "positive", "growth", "win", "yes", "approve", "pass"}
    neg = {"fall", "drop", "negative", "loss", "fail", "no", "reject", "decline"}
    words = text.lower().split()
    score = sum(1 for w in words if w in pos) - sum(1 for w in words if w in neg)
    return max(-1.0, min(1.0, score / max(len(words), 1) * 10))


class NewsRSSClient:
    async def _fetch_items(self, url: str) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                # minimal RSS parse without feedparser dep
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.text)
                items = []
                for item in root.iter("item"):
                    title = item.findtext("title") or ""
                    pub = item.findtext("pubDate") or ""
                    from email.utils import parsedate_to_datetime
                    try:
                        dt = parsedate_to_datetime(pub)
                    except Exception:
                        dt = datetime.now(timezone.utc)
                    items.append({"title": title, "published": dt, "summary": ""})
                return items
        except Exception as exc:
            logger.warning("RSS fetch failed for %s: %s", url, exc)
            return []

    async def get_signals(self, query: str, max_age_hours: float = 4.0) -> list[SignalScore]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        all_items = []
        for url in _RSS_FEEDS:
            all_items.extend(await self._fetch_items(url))

        results = []
        q_words = set(query.lower().split())
        for item in all_items:
            if item["published"] < cutoff:
                continue
            text = item["title"] + " " + item.get("summary", "")
            if not any(w in text.lower() for w in q_words):
                continue
            age_hours = (datetime.now(timezone.utc) - item["published"]).total_seconds() / 3600
            confidence = max(0.1, 1.0 - age_hours / max_age_hours)
            results.append(SignalScore(
                source="rss",
                sentiment=_simple_sentiment(text),
                confidence=confidence,
            ))
        return results
```

- [ ] **Step 4: Implement reddit_client.py**

```python
# src/sharpedge_trading/signals/reddit_client.py
import asyncio
import logging
from datetime import datetime, timezone
from ..events.types import SignalScore

logger = logging.getLogger("sharpedge.trading.reddit")

_SEMAPHORE = asyncio.Semaphore(10)


class RedditClient:
    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        self._creds = dict(client_id=client_id, client_secret=client_secret, user_agent=user_agent)
        self._reddit = None

    def _get_reddit(self):
        if self._reddit is None:
            import praw
            self._reddit = praw.Reddit(**self._creds, read_only=True)
        return self._reddit

    def get_signals_sync(self, query: str, subreddits: list[str] | None = None) -> list[SignalScore]:
        reddit = self._get_reddit()
        sub_name = "+".join(subreddits or ["politics", "economics", "worldnews", "CryptoCurrency"])
        results = []
        try:
            for post in reddit.subreddit(sub_name).search(query, limit=10, time_filter="day"):
                text = post.title + " " + (post.selftext or "")
                sentiment = self._naive_sentiment(text)
                results.append(SignalScore(source="reddit", sentiment=sentiment, confidence=0.5))
        except Exception as exc:
            logger.warning("Reddit fetch failed: %s", exc)
        return results

    async def get_signals(self, query: str, subreddits: list[str] | None = None) -> list[SignalScore]:
        async with _SEMAPHORE:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.get_signals_sync, query, subreddits)

    @staticmethod
    def _naive_sentiment(text: str) -> float:
        pos = {"rise", "gain", "positive", "win", "yes", "approve", "pass", "up"}
        neg = {"fall", "drop", "negative", "fail", "no", "reject", "decline", "down"}
        words = text.lower().split()
        score = sum(1 for w in words if w in pos) - sum(1 for w in words if w in neg)
        return max(-1.0, min(1.0, score / max(len(words), 1) * 10))
```

- [ ] **Step 5: Implement twitter_client.py (stub, feature-flagged)**

```python
# src/sharpedge_trading/signals/twitter_client.py
"""Twitter/X signal client. Requires ENABLE_TWITTER_SIGNALS=true and TWITTER_BEARER_TOKEN."""
import asyncio
import logging
import os
from ..events.types import SignalScore

logger = logging.getLogger("sharpedge.trading.twitter")
_SEMAPHORE = asyncio.Semaphore(5)


class TwitterClient:
    def __init__(self):
        self._enabled = os.environ.get("ENABLE_TWITTER_SIGNALS", "false").lower() == "true"
        self._bearer = os.environ.get("TWITTER_BEARER_TOKEN", "")

    async def get_signals(self, query: str) -> list[SignalScore]:
        if not self._enabled or not self._bearer:
            return []
        async with _SEMAPHORE:
            try:
                import tweepy
                client = tweepy.AsyncClient(bearer_token=self._bearer)
                resp = await client.search_recent_tweets(
                    query=query + " -is:retweet lang:en",
                    max_results=10,
                    tweet_fields=["text"],
                )
                results = []
                for tweet in (resp.data or []):
                    sent = self._naive_sentiment(tweet.text)
                    results.append(SignalScore(source="twitter", sentiment=sent, confidence=0.4))
                return results
            except Exception as exc:
                logger.warning("Twitter fetch failed (falling back): %s", exc)
                return []

    @staticmethod
    def _naive_sentiment(text: str) -> float:
        pos = {"rise", "gain", "win", "yes", "bullish", "up"}
        neg = {"fall", "drop", "fail", "no", "bearish", "down"}
        words = text.lower().split()
        score = sum(1 for w in words if w in pos) - sum(1 for w in words if w in neg)
        return max(-1.0, min(1.0, score / max(len(words), 1) * 10))
```

- [ ] **Step 6: Run tests — verify pass**

```bash
pytest tests/test_signal_clients.py -v
```

- [ ] **Step 7: Commit**

```bash
git add packages/trading_swarm/src/sharpedge_trading/signals/ packages/trading_swarm/tests/test_signal_clients.py
git commit -m "feat(trading): add RSS, Reddit, and Twitter signal clients"
```

---

## Task 7: Scan Agent

**Files:**
- Create: `packages/trading_swarm/src/sharpedge_trading/agents/scan_agent.py`
- Create: `packages/trading_swarm/tests/test_scan_agent.py`

- [ ] **Step 1: Write failing tests**

```python
# packages/trading_swarm/tests/test_scan_agent.py
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sharpedge_trading.agents.scan_agent import ScanAgent
from sharpedge_trading.events.bus import EventBus

def _make_market(market_id, price, yes_bid, yes_ask, volume=1000):
    m = MagicMock()
    m.ticker = market_id
    m.yes_bid = yes_bid
    m.yes_ask = yes_ask
    m.last_price = price
    m.volume = volume
    m.open_interest = 500
    m.category = "economic"
    m.title = "Will GDP exceed 3%?"
    m.close_time = None
    return m

@pytest.mark.asyncio
async def test_scan_agent_emits_opportunity():
    bus = EventBus()
    kalshi = AsyncMock()
    kalshi.get_markets = AsyncMock(return_value=[
        _make_market("GDP-Q1", 0.45, 0.44, 0.46, volume=1000)
    ])
    agent = ScanAgent(kalshi_client=kalshi, bus=bus, min_liquidity=500)
    with patch.object(agent, "_hours_to_resolution", return_value=24.0):
        await agent.scan_once()
    assert not bus._opportunity.empty()

@pytest.mark.asyncio
async def test_scan_agent_filters_low_volume():
    bus = EventBus()
    kalshi = AsyncMock()
    kalshi.get_markets = AsyncMock(return_value=[
        _make_market("LOW-LIQ", 0.45, 0.44, 0.46, volume=100)
    ])
    agent = ScanAgent(kalshi_client=kalshi, bus=bus, min_liquidity=500)
    with patch.object(agent, "_hours_to_resolution", return_value=24.0):
        await agent.scan_once()
    assert bus._opportunity.empty()
```

- [ ] **Step 2: Run — verify fails**

```bash
pytest tests/test_scan_agent.py -v
```

- [ ] **Step 3: Implement scan_agent.py**

```python
# src/sharpedge_trading/agents/scan_agent.py
import asyncio
import logging
from datetime import datetime, timezone
from collections import deque
from ..events.bus import EventBus
from ..events.types import OpportunityEvent

logger = logging.getLogger("sharpedge.trading.scan")

_MOMENTUM_THRESHOLD = 0.15  # 15% price move vs 24h baseline
_SPREAD_MULTIPLIER = 2.0    # spread > 2x baseline triggers flag
_MIN_HISTORY_DAYS = 7


class ScanAgent:
    def __init__(self, kalshi_client, bus: EventBus, min_liquidity: float = 500.0,
                 min_hours: float = 1.0, max_hours: float = 24 * 30):
        self._kalshi = kalshi_client
        self._bus = bus
        self._min_liquidity = min_liquidity
        self._min_hours = min_hours
        self._max_hours = max_hours
        self._price_history: dict[str, deque] = {}  # market_id -> recent prices

    def _hours_to_resolution(self, market) -> float | None:
        if market.close_time is None:
            return None
        now = datetime.now(timezone.utc)
        delta = market.close_time - now
        return delta.total_seconds() / 3600

    def _detect_anomaly(self, market) -> list[str]:
        flags = []
        mid = (market.yes_bid + market.yes_ask) / 2
        spread = market.yes_ask - market.yes_bid

        history = self._price_history.get(market.ticker, deque(maxlen=288))  # 24h at 5min
        if len(history) >= 12:  # need at least 1h of history
            baseline_price = sum(history) / len(history)
            if abs(mid - baseline_price) / max(baseline_price, 0.01) > _MOMENTUM_THRESHOLD:
                flags.append("momentum_spike")
            if len(history) >= 24:
                spreads = list(history)  # simplified; real impl tracks spreads separately
                avg_spread = 0.02  # placeholder baseline
                if spread > avg_spread * _SPREAD_MULTIPLIER:
                    flags.append("wide_spread")

        # update history
        if market.ticker not in self._price_history:
            self._price_history[market.ticker] = deque(maxlen=288)
        self._price_history[market.ticker].append(mid)
        return flags

    async def scan_once(self) -> None:
        try:
            markets = await self._kalshi.get_markets()
        except Exception as exc:
            logger.error("Kalshi API error during scan: %s", exc)
            return

        for market in markets:
            try:
                liquidity = getattr(market, "volume", 0) or 0
                if liquidity < self._min_liquidity:
                    continue
                hours = self._hours_to_resolution(market)
                if hours is None or not (self._min_hours <= hours <= self._max_hours):
                    continue
                mid_price = (market.yes_bid + market.yes_ask) / 2
                flags = self._detect_anomaly(market)
                event = OpportunityEvent(
                    market_id=market.ticker,
                    category=getattr(market, "category", "unknown"),
                    kalshi_price=mid_price,
                    liquidity=liquidity,
                    time_to_resolution_hours=hours,
                    title=getattr(market, "title", ""),
                    anomaly_flags=flags,
                )
                await self._bus.put_opportunity(event)
            except Exception as exc:
                logger.warning("Error processing market %s: %s", getattr(market, "ticker", "?"), exc)

    async def run(self, interval_seconds: float = 300.0) -> None:
        logger.info("ScanAgent started (interval=%ds)", interval_seconds)
        while True:
            await self.scan_once()
            await asyncio.sleep(interval_seconds)
```

- [ ] **Step 4: Run tests — verify pass**

```bash
pytest tests/test_scan_agent.py -v
```

- [ ] **Step 5: Commit**

```bash
git add packages/trading_swarm/src/sharpedge_trading/agents/scan_agent.py packages/trading_swarm/tests/test_scan_agent.py
git commit -m "feat(trading): add ScanAgent with anomaly detection and liquidity filter"
```

---

## Task 8: Research Agent

**Files:**
- Create: `packages/trading_swarm/src/sharpedge_trading/agents/research_agent.py`
- Create: `packages/trading_swarm/tests/test_research_agent.py`

- [ ] **Step 1: Write failing tests**

```python
# packages/trading_swarm/tests/test_research_agent.py
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sharpedge_trading.agents.research_agent import ResearchAgent
from sharpedge_trading.events.bus import EventBus
from sharpedge_trading.events.types import OpportunityEvent, SignalScore

def _opp(market_id="TEST-1", category="economic", hours=24.0):
    return OpportunityEvent(
        market_id=market_id, category=category,
        kalshi_price=0.45, liquidity=1000.0,
        time_to_resolution_hours=hours,
    )

@pytest.mark.asyncio
async def test_research_agent_emits_research_event():
    bus = EventBus()
    agent = ResearchAgent(bus=bus, anthropic_api_key="test")
    mock_scores = [SignalScore(source="rss", sentiment=0.3, confidence=0.8)]
    with patch.object(agent._rss, "get_signals", return_value=mock_scores), \
         patch.object(agent._reddit, "get_signals", return_value=[]), \
         patch.object(agent._twitter, "get_signals", return_value=[]), \
         patch.object(agent._calibrator, "calibrate", return_value=0.0), \
         patch.object(agent, "_polymarket_price", return_value=0.48):
        await bus.put_opportunity(_opp())
        await agent.process_one()
    assert not bus._research.empty()
    event = bus._research.get_nowait()
    assert event.market_id == "TEST-1"
    assert len(event.signals) == 1

@pytest.mark.asyncio
async def test_research_agent_builds_narrative():
    bus = EventBus()
    agent = ResearchAgent(bus=bus, anthropic_api_key="test")
    scores = [
        SignalScore(source="rss", sentiment=0.5, confidence=0.9),
        SignalScore(source="reddit", sentiment=-0.2, confidence=0.5),
    ]
    narrative = agent._build_narrative(scores, polymarket_price=0.50, kalshi_price=0.45)
    assert "rss" in narrative
    assert "polymarket" in narrative.lower() or "0.50" in narrative
```

- [ ] **Step 2: Run — verify fails**

```bash
pytest tests/test_research_agent.py -v
```

- [ ] **Step 3: Implement research_agent.py**

```python
# src/sharpedge_trading/agents/research_agent.py
import asyncio
import logging
from ..events.bus import EventBus
from ..events.types import OpportunityEvent, ResearchEvent, SignalScore
from ..signals.llm_calibrator import LLMCalibrator
from ..signals.news_rss_client import NewsRSSClient
from ..signals.reddit_client import RedditClient
from ..signals.twitter_client import TwitterClient

logger = logging.getLogger("sharpedge.trading.research")


class ResearchAgent:
    def __init__(self, bus: EventBus, anthropic_api_key: str,
                 reddit_client_id: str = "", reddit_client_secret: str = "",
                 polymarket_client=None):
        self._bus = bus
        self._calibrator = LLMCalibrator(api_key=anthropic_api_key)
        self._rss = NewsRSSClient()
        self._reddit = RedditClient(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            user_agent="sharpedge-trading/1.0",
        )
        self._twitter = TwitterClient()
        self._polymarket = polymarket_client

    async def _polymarket_price(self, market_id: str) -> float | None:
        if self._polymarket is None:
            return None
        try:
            return await self._polymarket.get_price(market_id)
        except Exception:
            return None

    def _build_narrative(self, signals: list[SignalScore], polymarket_price: float | None,
                         kalshi_price: float) -> str:
        lines = [f"Kalshi price: {kalshi_price:.3f}"]
        if polymarket_price is not None:
            dislocation = kalshi_price - polymarket_price
            lines.append(f"Polymarket price: {polymarket_price:.3f} (dislocation: {dislocation:+.3f})")
        by_source: dict[str, list[float]] = {}
        for s in signals:
            by_source.setdefault(s.source, []).append(s.sentiment)
        for src, sents in by_source.items():
            avg = sum(sents) / len(sents)
            lines.append(f"{src} sentiment: {avg:+.2f} (n={len(sents)})")
        return "\n".join(lines)

    async def _research_opportunity(self, opp: OpportunityEvent) -> ResearchEvent:
        max_age = opp.time_to_resolution_hours / 2
        query = opp.title or opp.market_id

        rss_task = self._rss.get_signals(query, max_age_hours=max_age)
        reddit_task = self._reddit.get_signals(query)
        twitter_task = self._twitter.get_signals(query)
        pm_task = self._polymarket_price(opp.market_id)

        rss_scores, reddit_scores, twitter_scores, pm_price = await asyncio.gather(
            rss_task, reddit_task, twitter_task, pm_task, return_exceptions=True
        )

        signals: list[SignalScore] = []
        for result in [rss_scores, reddit_scores, twitter_scores]:
            if isinstance(result, list):
                signals.extend(result)

        if isinstance(pm_price, Exception):
            pm_price = None

        narrative = self._build_narrative(signals, pm_price, opp.kalshi_price)

        return ResearchEvent(
            market_id=opp.market_id,
            category=opp.category,
            kalshi_price=opp.kalshi_price,
            polymarket_price=pm_price if isinstance(pm_price, float) else None,
            signals=signals,
            narrative_summary=narrative,
            time_to_resolution_hours=opp.time_to_resolution_hours,
        )

    async def process_one(self) -> None:
        opp = await self._bus.get_opportunity()
        try:
            event = await self._research_opportunity(opp)
            await self._bus.put_research(event)
        except Exception as exc:
            logger.error("Research failed for %s: %s", opp.market_id, exc)

    async def run(self, concurrency: int = 5) -> None:
        logger.info("ResearchAgent started (concurrency=%d)", concurrency)
        sem = asyncio.Semaphore(concurrency)
        tasks: set[asyncio.Task] = set()
        while True:
            await sem.acquire()
            async def _guarded():
                try:
                    await self.process_one()
                finally:
                    sem.release()
                    tasks.discard(asyncio.current_task())
            t = asyncio.create_task(_guarded())
            tasks.add(t)
```

- [ ] **Step 4: Run tests — verify pass**

```bash
pytest tests/test_research_agent.py -v
```

- [ ] **Step 5: Commit**

```bash
git add packages/trading_swarm/src/sharpedge_trading/agents/research_agent.py packages/trading_swarm/tests/test_research_agent.py
git commit -m "feat(trading): add ResearchAgent with parallel signal gathering"
```

---

## Task 9: Prediction Agent

**Files:**
- Create: `packages/trading_swarm/src/sharpedge_trading/agents/prediction_agent.py`
- Create: `packages/trading_swarm/tests/test_prediction_agent.py`

- [ ] **Step 1: Write failing tests**

```python
# packages/trading_swarm/tests/test_prediction_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sharpedge_trading.agents.prediction_agent import PredictionAgent
from sharpedge_trading.events.bus import EventBus
from sharpedge_trading.events.types import ResearchEvent, SignalScore
from sharpedge_trading.config import TradingConfig

def _research(market_id="TEST-1", category="economic", kalshi_price=0.40):
    return ResearchEvent(
        market_id=market_id, category=category, kalshi_price=kalshi_price,
        polymarket_price=0.45, signals=[], narrative_summary="test narrative",
        time_to_resolution_hours=24.0,
    )

def _mock_cfg(threshold=0.03):
    cfg = MagicMock(spec=TradingConfig)
    cfg.confidence_threshold = threshold
    return cfg

@pytest.mark.asyncio
async def test_prediction_agent_emits_when_edge_above_threshold():
    bus = EventBus()
    agent = PredictionAgent(bus=bus, config=_mock_cfg(threshold=0.03))
    # RF says 0.60, market at 0.40 → edge = 0.20 - fee > 0.03
    with patch.object(agent, "_rf_predict", return_value=0.60), \
         patch.object(agent._calibrator, "calibrate", return_value=0.60):
        await bus.put_research(_research(kalshi_price=0.40))
        await agent.process_one()
    assert not bus._prediction.empty()

@pytest.mark.asyncio
async def test_prediction_agent_drops_when_edge_below_threshold():
    bus = EventBus()
    agent = PredictionAgent(bus=bus, config=_mock_cfg(threshold=0.03))
    with patch.object(agent, "_rf_predict", return_value=0.41), \
         patch.object(agent._calibrator, "calibrate", return_value=0.41):
        await bus.put_research(_research(kalshi_price=0.40))
        await agent.process_one()
    assert bus._prediction.empty()

@pytest.mark.asyncio
async def test_prediction_agent_falls_back_when_model_missing():
    bus = EventBus()
    agent = PredictionAgent(bus=bus, config=_mock_cfg())
    with patch.object(agent, "_rf_predict", side_effect=FileNotFoundError), \
         patch.object(agent._calibrator, "calibrate", return_value=0.80):
        await bus.put_research(_research(kalshi_price=0.40))
        await agent.process_one()
    # should still emit using kalshi_price as base fallback
    assert not bus._prediction.empty()
```

- [ ] **Step 2: Run — verify fails**

```bash
pytest tests/test_prediction_agent.py -v
```

- [ ] **Step 3: Implement prediction_agent.py**

```python
# src/sharpedge_trading/agents/prediction_agent.py
import asyncio
import logging
import os
from pathlib import Path
from ..events.bus import EventBus
from ..events.types import ResearchEvent, PredictionEvent
from ..signals.llm_calibrator import LLMCalibrator
from ..config import TradingConfig

logger = logging.getLogger("sharpedge.trading.prediction")

_KALSHI_FEE = 0.001  # 0.1% transaction fee
_MODELS_DIR = Path(os.environ.get("MODELS_DIR", "data/models/pm"))


class PredictionAgent:
    def __init__(self, bus: EventBus, config: TradingConfig, anthropic_api_key: str = ""):
        self._bus = bus
        self._config = config
        self._calibrator = LLMCalibrator(api_key=anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", ""))
        self._model_cache: dict[str, object] = {}

    def _rf_predict(self, category: str, features: dict) -> float:
        """Load Phase 9 RF model and predict probability."""
        import joblib
        if category not in self._model_cache:
            model_path = _MODELS_DIR / f"{category}.joblib"
            if not model_path.exists():
                raise FileNotFoundError(f"No model for category: {category}")
            self._model_cache[category] = joblib.load(model_path)

        model = self._model_cache[category]
        # Minimal feature vector: use available features, pad with zeros
        import numpy as np
        feature_vec = np.array([[
            features.get("kalshi_price", 0.5),
            features.get("polymarket_price", features.get("kalshi_price", 0.5)),
            features.get("volume", 0),
            features.get("time_to_resolution_hours", 24),
        ]])
        try:
            proba = model.predict_proba(feature_vec)[0][1]
        except Exception:
            proba = model.predict(feature_vec)[0]
        return float(proba)

    async def process_one(self) -> None:
        research = await self._bus.get_research()
        try:
            features = {
                "kalshi_price": research.kalshi_price,
                "polymarket_price": research.polymarket_price or research.kalshi_price,
                "time_to_resolution_hours": research.time_to_resolution_hours,
            }
            try:
                rf_prob = self._rf_predict(research.category, features)
            except FileNotFoundError:
                logger.warning("No RF model for %s, using kalshi_price as base", research.category)
                rf_prob = research.kalshi_price

            calibrated = await self._calibrator.calibrate(rf_prob, research.narrative_summary)
            llm_adjustment = calibrated - rf_prob

            # Direction: bet YES if calibrated > market, NO if calibrated < market
            edge = abs(calibrated - research.kalshi_price) - _KALSHI_FEE
            if edge < self._config.confidence_threshold:
                logger.debug("Edge %.4f below threshold for %s — skipping", edge, research.market_id)
                return

            confidence = min(1.0, edge / 0.10)  # normalize to 0-1

            event = PredictionEvent(
                market_id=research.market_id,
                category=research.category,
                kalshi_price=research.kalshi_price,
                calibrated_prob=calibrated,
                rf_base_prob=rf_prob,
                llm_adjustment=llm_adjustment,
                edge=edge,
                confidence_score=confidence,
                time_to_resolution_hours=research.time_to_resolution_hours,
                research_snapshot={
                    "narrative": research.narrative_summary,
                    "signal_count": len(research.signals),
                    "polymarket_price": research.polymarket_price,
                },
            )
            await self._bus.put_prediction(event)
        except Exception as exc:
            logger.error("Prediction failed for %s: %s", research.market_id, exc)

    async def run(self) -> None:
        logger.info("PredictionAgent started")
        while True:
            await self.process_one()
```

- [ ] **Step 4: Run tests — verify pass**

```bash
pytest tests/test_prediction_agent.py -v
```

- [ ] **Step 5: Commit**

```bash
git add packages/trading_swarm/src/sharpedge_trading/agents/prediction_agent.py packages/trading_swarm/tests/test_prediction_agent.py
git commit -m "feat(trading): add PredictionAgent with RF model + LLM calibration"
```

---

## Task 10: Portfolio Manager & Risk Agent

**Files:**
- Create: `packages/trading_swarm/src/sharpedge_trading/agents/portfolio_manager.py`
- Create: `packages/trading_swarm/src/sharpedge_trading/agents/risk_agent.py`
- Create: `packages/trading_swarm/tests/test_portfolio_manager.py`
- Create: `packages/trading_swarm/tests/test_risk_agent.py`

- [ ] **Step 1: Write failing tests**

```python
# packages/trading_swarm/tests/test_portfolio_manager.py
import pytest
from unittest.mock import MagicMock
from sharpedge_trading.agents.portfolio_manager import PortfolioManager
from sharpedge_trading.events.bus import EventBus
from sharpedge_trading.events.types import PredictionEvent
from sharpedge_trading.config import TradingConfig

def _pred(market_id="X", category="economic", edge=0.10, kalshi_price=0.45, hours=24.0):
    return PredictionEvent(
        market_id=market_id, category=category, kalshi_price=kalshi_price,
        calibrated_prob=kalshi_price + edge, rf_base_prob=kalshi_price,
        llm_adjustment=edge, edge=edge, confidence_score=0.8,
        time_to_resolution_hours=hours,
    )

def _mock_supabase(open_positions=None):
    client = MagicMock()
    positions = open_positions or []
    client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = positions
    return client

@pytest.mark.asyncio
async def test_portfolio_manager_approves_valid_position():
    bus = EventBus()
    cfg = MagicMock(spec=TradingConfig)
    cfg.max_category_exposure = 0.20
    cfg.max_total_exposure = 0.40
    pm = PortfolioManager(bus=bus, supabase_client=_mock_supabase(), config=cfg, bankroll=10000)
    await bus.put_prediction(_pred())
    await pm.process_one()
    assert not bus._approved.empty()

@pytest.mark.asyncio
async def test_portfolio_manager_blocks_over_exposed_category():
    bus = EventBus()
    cfg = MagicMock(spec=TradingConfig)
    cfg.max_category_exposure = 0.20
    cfg.max_total_exposure = 0.40
    # already have $2100 in economic (> 20% of $10k)
    positions = [{"category": "economic", "size": 2100}]
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = positions
    pm = PortfolioManager(bus=bus, supabase_client=client, config=cfg, bankroll=10000)
    await bus.put_prediction(_pred(category="economic"))
    await pm.process_one()
    assert bus._approved.empty()
```

- [ ] **Step 2: Run — verify fails**

```bash
pytest tests/test_portfolio_manager.py -v
```

- [ ] **Step 3: Implement portfolio_manager.py**

```python
# src/sharpedge_trading/agents/portfolio_manager.py
import asyncio
import logging
from ..events.bus import EventBus
from ..events.types import PredictionEvent, ApprovedEvent
from ..config import TradingConfig

logger = logging.getLogger("sharpedge.trading.portfolio")


class PortfolioManager:
    def __init__(self, bus: EventBus, supabase_client, config: TradingConfig, bankroll: float):
        self._bus = bus
        self._client = supabase_client
        self._config = config
        self._bankroll = bankroll

    def _get_open_exposure(self) -> tuple[float, dict[str, float]]:
        """Returns (total_exposure, exposure_by_category)."""
        rows = (
            self._client.table("open_positions")
            .select("size,category")
            .eq("status", "open")
            .execute()
            .data or []
        )
        total = sum(r.get("size", 0) for r in rows)
        by_cat: dict[str, float] = {}
        for r in rows:
            cat = r.get("category", "unknown")
            by_cat[cat] = by_cat.get(cat, 0) + r.get("size", 0)
        return total, by_cat

    async def process_one(self) -> None:
        pred = await self._bus.get_prediction()
        try:
            total_exp, cat_exp = self._get_open_exposure()
            cat = pred.category
            cat_limit = self._config.max_category_exposure * self._bankroll
            total_limit = self._config.max_total_exposure * self._bankroll

            if cat_exp.get(cat, 0) >= cat_limit:
                logger.info("Blocking %s — category %s at limit ($%.0f)", pred.market_id, cat, cat_limit)
                return
            if total_exp >= total_limit:
                logger.info("Blocking %s — total exposure at limit ($%.0f)", pred.market_id, total_limit)
                return

            max_size_pct = min(
                0.05,
                (cat_limit - cat_exp.get(cat, 0)) / self._bankroll,
                (total_limit - total_exp) / self._bankroll,
            )
            await self._bus.put_approved(ApprovedEvent(prediction=pred, approved_size_pct=max_size_pct))
        except Exception as exc:
            logger.error("Portfolio check failed for %s: %s", pred.market_id, exc)

    async def run(self) -> None:
        logger.info("PortfolioManager started")
        while True:
            await self.process_one()
```

- [ ] **Step 4: Write failing test for risk_agent**

```python
# packages/trading_swarm/tests/test_risk_agent.py
import pytest
from unittest.mock import MagicMock
from sharpedge_trading.agents.risk_agent import RiskAgent, kelly_fraction
from sharpedge_trading.events.bus import EventBus
from sharpedge_trading.events.types import ApprovedEvent, PredictionEvent
from sharpedge_trading.config import TradingConfig

def test_kelly_fraction_standard_case():
    # p=0.6, kalshi_price=0.45 → b=(1-0.45)/0.45=1.22, f=(0.6*1.22-0.4)/1.22=0.27
    f = kelly_fraction(prob=0.6, kalshi_price=0.45)
    assert 0.20 < f < 0.35

def test_kelly_fraction_clamps_near_zero():
    f = kelly_fraction(prob=0.51, kalshi_price=0.02)  # extreme odds
    assert 0.001 <= f <= 0.05  # clamped

def test_kelly_fraction_clamps_near_one():
    f = kelly_fraction(prob=0.99, kalshi_price=0.98)
    assert f <= 0.05  # max 5% of bankroll

@pytest.mark.asyncio
async def test_risk_agent_emits_execution_event():
    bus = EventBus()
    cfg = MagicMock(spec=TradingConfig)
    cfg.kelly_fraction = 0.25
    cfg.daily_loss_limit = 0.10
    agent = RiskAgent(bus=bus, config=cfg, supabase_client=MagicMock(), bankroll=10000)
    pred = PredictionEvent(
        market_id="X", category="economic", kalshi_price=0.40,
        calibrated_prob=0.60, rf_base_prob=0.58, llm_adjustment=0.02,
        edge=0.19, confidence_score=0.8, time_to_resolution_hours=24.0,
    )
    await bus.put_approved(ApprovedEvent(prediction=pred, approved_size_pct=0.05))
    agent._is_paused = lambda: False
    await agent.process_one()
    assert not bus._execution.empty()
```

- [ ] **Step 5: Run risk agent test — verify fails**

```bash
pytest tests/test_risk_agent.py -v
```

- [ ] **Step 6: Implement risk_agent.py**

```python
# src/sharpedge_trading/agents/risk_agent.py
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from ..events.bus import EventBus
from ..events.types import ApprovedEvent, ExecutionEvent
from ..config import TradingConfig

logger = logging.getLogger("sharpedge.trading.risk")


def kelly_fraction(prob: float, kalshi_price: float) -> float:
    """Standard binary Kelly: f* = (p*b - q) / b, fractional at 0.25x, clamped [0.001, 0.05]."""
    p = prob
    q = 1.0 - p
    price = max(0.05, min(0.95, kalshi_price))
    b = (1.0 - price) / price  # implied odds against
    f_star = (p * b - q) / b
    f_star = max(0.0, f_star)  # can't be negative
    return max(0.001, min(0.05, f_star))  # clamp to 0.1%-5% of bankroll


class RiskAgent:
    def __init__(self, bus: EventBus, config: TradingConfig, supabase_client, bankroll: float):
        self._bus = bus
        self._config = config
        self._client = supabase_client
        self._bankroll = bankroll
        self._consecutive_losses = 0
        self._daily_loss = 0.0
        self._daily_reset = datetime.now(timezone.utc).date()

    def _reset_daily_if_needed(self) -> None:
        today = datetime.now(timezone.utc).date()
        if today > self._daily_reset:
            self._daily_loss = 0.0
            self._daily_reset = today

    def _is_paused(self) -> bool:
        self._reset_daily_if_needed()
        try:
            rows = (
                self._client.table("circuit_breaker_state")
                .select("resume_at")
                .execute()
                .data or []
            )
            now = datetime.now(timezone.utc)
            for row in rows:
                resume = datetime.fromisoformat(row["resume_at"])
                if resume > now:
                    return True
        except Exception:
            pass
        return False

    def _trigger_breaker(self, breaker_type: str, pause_hours: float) -> None:
        now = datetime.now(timezone.utc)
        resume = now + timedelta(hours=pause_hours)
        try:
            self._client.table("circuit_breaker_state").insert({
                "breaker_type": breaker_type,
                "triggered_at": now.isoformat(),
                "resume_at": resume.isoformat(),
                "consecutive_loss_count": self._consecutive_losses,
                "daily_loss_amount": self._daily_loss,
            }).execute()
        except Exception as exc:
            logger.error("Failed to write circuit breaker: %s", exc)
        logger.warning("Circuit breaker triggered: %s, pausing %.0fh", breaker_type, pause_hours)

    async def process_one(self) -> None:
        approved = await self._bus.get_approved()
        pred = approved.prediction

        if self._is_paused():
            logger.info("Trading paused by circuit breaker, dropping %s", pred.market_id)
            return

        frac = kelly_fraction(pred.calibrated_prob, pred.kalshi_price)
        size_dollars = self._config.kelly_fraction * frac * self._bankroll
        size_dollars = min(size_dollars, approved.approved_size_pct * self._bankroll)

        direction = "yes" if pred.calibrated_prob > pred.kalshi_price else "no"

        event = ExecutionEvent(
            market_id=pred.market_id,
            direction=direction,
            size_dollars=size_dollars,
            entry_price=pred.kalshi_price,
            category=pred.category,
            confidence_score=pred.confidence_score,
            trading_mode="paper",  # overridden by executor
        )
        await self._bus.put_execution(event)

    def record_loss(self, amount: float) -> None:
        self._consecutive_losses += 1
        self._daily_loss += amount
        self._reset_daily_if_needed()
        if self._daily_loss > self._config.daily_loss_limit * self._bankroll:
            self._trigger_breaker("daily_loss", 24.0)
        elif self._consecutive_losses >= 5:
            self._trigger_breaker("consecutive_losses", 4.0)

    def record_win(self) -> None:
        self._consecutive_losses = 0

    async def run(self) -> None:
        logger.info("RiskAgent started")
        while True:
            await self.process_one()
```

- [ ] **Step 7: Run all tests — verify pass**

```bash
pytest tests/test_portfolio_manager.py tests/test_risk_agent.py -v
```

- [ ] **Step 8: Commit**

```bash
git add packages/trading_swarm/src/sharpedge_trading/agents/{portfolio_manager,risk_agent}.py packages/trading_swarm/tests/test_{portfolio_manager,risk_agent}.py
git commit -m "feat(trading): add PortfolioManager and RiskAgent with Kelly sizing and circuit breakers"
```

---

## Task 11: Execution Layer

**Files:**
- Create: `packages/trading_swarm/src/sharpedge_trading/execution/base_executor.py`
- Create: `packages/trading_swarm/src/sharpedge_trading/execution/paper_executor.py`
- Create: `packages/trading_swarm/src/sharpedge_trading/execution/kalshi_executor.py`
- Create: `packages/trading_swarm/tests/test_paper_executor.py`

- [ ] **Step 1: Write failing tests**

```python
# packages/trading_swarm/tests/test_paper_executor.py
import pytest
from unittest.mock import MagicMock
from sharpedge_trading.execution.paper_executor import PaperExecutor
from sharpedge_trading.events.types import ExecutionEvent

def _exec_event(market_id="X", size=100.0, price=0.45, direction="yes"):
    return ExecutionEvent(
        market_id=market_id, direction=direction, size_dollars=size,
        entry_price=price, category="economic", confidence_score=0.7,
        trading_mode="paper",
    )

def _mock_supabase():
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "trade-123"}]
    client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
    return client

@pytest.mark.asyncio
async def test_paper_executor_records_trade():
    executor = PaperExecutor(supabase_client=_mock_supabase(), starting_bankroll=10000.0)
    result = await executor.execute(_exec_event())
    assert result is not None
    assert result.startswith("trade-") or len(result) > 0

@pytest.mark.asyncio
async def test_paper_executor_reduces_bankroll():
    executor = PaperExecutor(supabase_client=_mock_supabase(), starting_bankroll=10000.0)
    await executor.execute(_exec_event(size=500.0))
    assert executor.bankroll == pytest.approx(9500.0, abs=10)

@pytest.mark.asyncio
async def test_paper_executor_idempotent():
    executor = PaperExecutor(supabase_client=_mock_supabase(), starting_bankroll=10000.0)
    e = _exec_event()
    t1 = await executor.execute(e)
    t2 = await executor.execute(e)
    assert t1 == t2  # same idempotency key = same trade id
```

- [ ] **Step 2: Run — verify fails**

```bash
pytest tests/test_paper_executor.py -v
```

- [ ] **Step 3: Implement base_executor.py**

```python
# src/sharpedge_trading/execution/base_executor.py
from abc import ABC, abstractmethod
from ..events.types import ExecutionEvent


class BaseExecutor(ABC):
    @abstractmethod
    async def execute(self, event: ExecutionEvent) -> str:
        """Execute the order. Returns trade_id."""
        ...

    @abstractmethod
    async def settle(self, trade_id: str, outcome: bool, exit_price: float) -> float:
        """Settle a trade. Returns realized P&L."""
        ...
```

- [ ] **Step 4: Implement paper_executor.py**

```python
# src/sharpedge_trading/execution/paper_executor.py
import hashlib
import logging
from datetime import datetime, timezone
from .base_executor import BaseExecutor
from ..events.types import ExecutionEvent

logger = logging.getLogger("sharpedge.trading.paper_executor")


class PaperExecutor(BaseExecutor):
    def __init__(self, supabase_client, starting_bankroll: float = 10000.0):
        self._client = supabase_client
        self.bankroll = starting_bankroll
        self._id_cache: dict[str, str] = {}

    def _idempotency_key(self, event: ExecutionEvent) -> str:
        raw = f"{event.market_id}:{event.direction}:{round(event.entry_price, 4)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _slippage(self, event: ExecutionEvent) -> float:
        spread = 0.02  # estimated Kalshi spread
        volume_impact = (event.size_dollars / max(self.bankroll, 1)) * 0.001
        return spread / 2 + volume_impact

    async def execute(self, event: ExecutionEvent) -> str:
        key = self._idempotency_key(event)
        if key in self._id_cache:
            return self._id_cache[key]

        fill_price = event.entry_price + self._slippage(event)
        fill_price = min(fill_price, 0.99)
        self.bankroll -= event.size_dollars

        now = datetime.now(timezone.utc).isoformat()
        row = {
            "market_id": event.market_id,
            "direction": event.direction,
            "size": event.size_dollars,
            "entry_price": fill_price,
            "confidence_score": event.confidence_score,
            "category": event.category,
            "trading_mode": "paper",
            "opened_at": now,
        }
        result = self._client.table("paper_trades").insert(row).execute()
        trade_id = result.data[0]["id"] if result.data else key

        self._client.table("open_positions").upsert({
            "market_id": event.market_id,
            "size": event.size_dollars,
            "entry_price": fill_price,
            "category": event.category,
            "trading_mode": "paper",
            "status": "open",
            "opened_at": now,
        }).execute()

        self._id_cache[key] = trade_id
        logger.info("Paper trade executed: %s %s @ %.3f, size=$%.0f",
                    event.direction, event.market_id, fill_price, event.size_dollars)
        return trade_id

    async def settle(self, trade_id: str, outcome: bool, exit_price: float) -> float:
        # Lookup original trade to compute P&L
        rows = self._client.table("paper_trades").select("*").eq("id", trade_id).execute().data or []
        if not rows:
            return 0.0
        trade = rows[0]
        size = trade["size"]
        direction = trade["direction"]
        entry = trade["entry_price"]

        if direction == "yes":
            pnl = size * (exit_price - entry) if outcome else -size * entry
        else:
            pnl = size * (entry - exit_price) if not outcome else -size * (1 - entry)

        self.bankroll += size + pnl  # return stake + profit
        now = datetime.now(timezone.utc).isoformat()
        self._client.table("paper_trades").upsert({
            "id": trade_id,
            "exit_price": exit_price,
            "pnl": pnl,
            "actual_outcome": outcome,
            "resolved_at": now,
        }).execute()
        self._client.table("open_positions").upsert({
            "market_id": trade["market_id"],
            "status": "settled",
        }).execute()
        return pnl
```

- [ ] **Step 5: Implement kalshi_executor.py (thin wrapper)**

```python
# src/sharpedge_trading/execution/kalshi_executor.py
import logging
from .base_executor import BaseExecutor
from ..events.types import ExecutionEvent

logger = logging.getLogger("sharpedge.trading.kalshi_executor")


class KalshiExecutor(BaseExecutor):
    def __init__(self, kalshi_client, supabase_client):
        self._kalshi = kalshi_client
        self._client = supabase_client

    async def execute(self, event: ExecutionEvent) -> str:
        # Place real order via Kalshi REST API
        # kalshi_client.place_order(...) — implement when live credentials available
        raise NotImplementedError("KalshiExecutor.execute requires live Kalshi credentials")

    async def settle(self, trade_id: str, outcome: bool, exit_price: float) -> float:
        raise NotImplementedError("KalshiExecutor.settle requires live Kalshi credentials")
```

- [ ] **Step 6: Run tests — verify pass**

```bash
pytest tests/test_paper_executor.py -v
```

- [ ] **Step 7: Commit**

```bash
git add packages/trading_swarm/src/sharpedge_trading/execution/ packages/trading_swarm/tests/test_paper_executor.py
git commit -m "feat(trading): add PaperExecutor with slippage model and idempotency"
```

---

## Task 12: Monitor & Post-Mortem Agents

**Files:**
- Create: `packages/trading_swarm/src/sharpedge_trading/agents/monitor_agent.py`
- Create: `packages/trading_swarm/src/sharpedge_trading/agents/post_mortem_agent.py`
- Create: `packages/trading_swarm/tests/test_monitor_agent.py`
- Create: `packages/trading_swarm/tests/test_post_mortem_agent.py`

- [ ] **Step 1: Write failing tests**

```python
# packages/trading_swarm/tests/test_monitor_agent.py
import pytest
from unittest.mock import MagicMock, AsyncMock
from sharpedge_trading.agents.monitor_agent import MonitorAgent
from sharpedge_trading.events.bus import EventBus

def _mock_supabase(positions=None, settled_market_ids=None):
    settled = set(settled_market_ids or [])
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = positions or []
    return client

@pytest.mark.asyncio
async def test_monitor_emits_resolution_on_settled_market():
    bus = EventBus()
    positions = [{"id": "pos-1", "market_id": "GDP-Q1", "size": 100, "entry_price": 0.45,
                  "trading_mode": "paper", "status": "open"}]
    client = _mock_supabase(positions)
    kalshi = AsyncMock()
    kalshi.get_market_status = AsyncMock(return_value={"settled": True, "result": True, "settlement_price": 1.0})
    agent = MonitorAgent(bus=bus, kalshi_client=kalshi, supabase_client=client, executor=MagicMock())
    await agent.check_once()
    assert not bus._resolution.empty()

# packages/trading_swarm/tests/test_post_mortem_agent.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from sharpedge_trading.agents.post_mortem_agent import PostMortemAgent
from sharpedge_trading.events.bus import EventBus
from sharpedge_trading.events.types import ResolutionEvent
from sharpedge_trading.config import TradingConfig

def _loss_event():
    return ResolutionEvent(
        market_id="X", trade_id="trade-1", outcome=False,
        pnl=-50.0, entry_price=0.6, exit_price=0.0, trading_mode="paper",
    )

@pytest.mark.asyncio
async def test_post_mortem_writes_attribution():
    bus = EventBus()
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "trade-1", "market_id": "X", "confidence_score": 0.8, "size": 50}
    ]
    client.table.return_value.insert.return_value.execute.return_value = MagicMock()
    client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
    cfg = MagicMock(spec=TradingConfig)
    cfg.confidence_threshold = 0.03
    cfg.kelly_fraction = 0.25
    agent = PostMortemAgent(bus=bus, supabase_client=client, config=cfg)
    with patch.object(agent._calibrator, "calibrate", return_value=0.5):
        await bus.put_resolution(_loss_event())
        await agent.process_one()
    # verify insert was called on trade_post_mortems
    call_args = [str(c) for c in client.table.call_args_list]
    assert any("trade_post_mortems" in c for c in call_args)
```

- [ ] **Step 2: Run — verify fails**

```bash
pytest tests/test_monitor_agent.py tests/test_post_mortem_agent.py -v
```

- [ ] **Step 3: Implement monitor_agent.py**

```python
# src/sharpedge_trading/agents/monitor_agent.py
import asyncio
import logging
from datetime import datetime, timezone
from ..events.bus import EventBus
from ..events.types import ResolutionEvent

logger = logging.getLogger("sharpedge.trading.monitor")


class MonitorAgent:
    def __init__(self, bus: EventBus, kalshi_client, supabase_client, executor):
        self._bus = bus
        self._kalshi = kalshi_client
        self._client = supabase_client
        self._executor = executor

    async def check_once(self) -> None:
        rows = (
            self._client.table("open_positions")
            .select("*")
            .eq("status", "open")
            .execute()
            .data or []
        )
        for pos in rows:
            market_id = pos["market_id"]
            try:
                status = await self._kalshi.get_market_status(market_id)
                if not status.get("settled"):
                    continue
                outcome = bool(status.get("result"))
                settlement_price = float(status.get("settlement_price", 1.0 if outcome else 0.0))
                trade_id = pos.get("id", "")
                pnl = await self._executor.settle(trade_id, outcome, settlement_price)
                event = ResolutionEvent(
                    market_id=market_id,
                    trade_id=trade_id,
                    outcome=outcome,
                    pnl=pnl,
                    entry_price=pos["entry_price"],
                    exit_price=settlement_price,
                    trading_mode=pos.get("trading_mode", "paper"),
                )
                await self._bus.put_resolution(event)
            except Exception as exc:
                logger.error("Monitor check failed for %s: %s", market_id, exc)

    async def run(self, interval_seconds: float = 60.0) -> None:
        logger.info("MonitorAgent started (interval=%ds)", interval_seconds)
        while True:
            await self.check_once()
            await asyncio.sleep(interval_seconds)
```

- [ ] **Step 4: Implement post_mortem_agent.py**

```python
# src/sharpedge_trading/agents/post_mortem_agent.py
import asyncio
import logging
from datetime import datetime, timezone
from ..events.bus import EventBus
from ..events.types import ResolutionEvent
from ..signals.llm_calibrator import LLMCalibrator
from ..config import TradingConfig

logger = logging.getLogger("sharpedge.trading.post_mortem")

_MAX_AUTO_ADJUSTMENTS = 5


class PostMortemAgent:
    def __init__(self, bus: EventBus, supabase_client, config: TradingConfig,
                 anthropic_api_key: str = ""):
        self._bus = bus
        self._client = supabase_client
        self._config = config
        self._calibrator = LLMCalibrator(api_key=anthropic_api_key)

    def _is_auto_adjust_paused(self) -> bool:
        rows = self._client.table("trading_config").select("value").eq("key", "auto_adjust_paused").execute().data or []
        return rows[0]["value"] == "true" if rows else False

    def _increment_adjust_count(self) -> int:
        rows = self._client.table("trading_config").select("value").eq("key", "auto_adjust_count").execute().data or []
        count = int(rows[0]["value"]) + 1 if rows else 1
        self._client.table("trading_config").upsert({"key": "auto_adjust_count", "value": str(count), "updated_by": "post_mortem_agent", "updated_at": datetime.now(timezone.utc).isoformat()}).execute()
        if count >= _MAX_AUTO_ADJUSTMENTS:
            self._client.table("trading_config").upsert({"key": "auto_adjust_paused", "value": "true", "updated_by": "system", "updated_at": datetime.now(timezone.utc).isoformat()}).execute()
            logger.warning("Auto-adjustment paused after %d consecutive adjustments — manual review required", count)
        return count

    def _attribute_loss(self, resolution: ResolutionEvent, trade: dict) -> dict:
        confidence = trade.get("confidence_score", 0.5)
        size = trade.get("size", 0)
        bankroll_estimate = 10000  # could load from config

        # Model error: we were highly confident but wrong
        model_error = confidence if confidence > 0.7 else 0.0

        # Sizing error: position was large (> 3% of bankroll)
        sizing_error = 1.0 if size > 0.03 * bankroll_estimate else 0.0

        # Signal error: we had high confidence but base RF prob was lower
        signal_error = 0.5 if confidence > 0.6 and model_error > 0 else 0.0

        # Variance: low confidence bet that lost (expected to sometimes lose)
        variance = 1.0 - model_error if confidence < 0.5 else 0.0

        return {
            "model_error_score": round(model_error, 2),
            "signal_error_score": round(signal_error, 2),
            "sizing_error_score": round(sizing_error, 2),
            "variance_score": round(variance, 2),
        }

    async def _apply_learning(self, attribution: dict, resolution: ResolutionEvent) -> None:
        if self._is_auto_adjust_paused():
            logger.info("Auto-adjust paused; skipping learning update for %s", resolution.market_id)
            return

        # Check recent loss history to decide if threshold met
        rows = self._client.table("trade_post_mortems").select("model_error_score,signal_error_score,sizing_error_score").execute().data or []
        if len(rows) < 3:
            return

        recent = rows[-3:]
        avg_model = sum(r["model_error_score"] for r in recent) / 3
        avg_signal = sum(r["signal_error_score"] for r in recent) / 3
        avg_sizing = sum(r["sizing_error_score"] for r in recent) / 3

        if avg_model >= 0.7:
            new_val = self._config.confidence_threshold + 0.005
            self._config.update("confidence_threshold", new_val, "post_mortem_agent")
            self._increment_adjust_count()
            logger.info("Raised confidence_threshold to %.3f", new_val)
        elif avg_sizing >= 0.7:
            new_val = self._config.kelly_fraction - 0.02
            self._config.update("kelly_fraction", new_val, "post_mortem_agent")
            self._increment_adjust_count()
            logger.info("Reduced kelly_fraction to %.2f", new_val)

    async def process_one(self) -> None:
        resolution = await self._bus.get_resolution()
        if resolution.pnl >= 0:
            return  # only process losses

        trade_rows = self._client.table("paper_trades").select("*").eq("id", resolution.trade_id).execute().data or []
        trade = trade_rows[0] if trade_rows else {}

        attribution = self._attribute_loss(resolution, trade)
        narrative = f"Loss of ${abs(resolution.pnl):.2f} on {resolution.market_id}. Attribution: {attribution}"

        self._client.table("trade_post_mortems").insert({
            "trade_id": resolution.trade_id,
            **attribution,
            "llm_narrative": narrative,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

        await self._apply_learning(attribution, resolution)

    async def run(self) -> None:
        logger.info("PostMortemAgent started")
        while True:
            await self.process_one()
```

- [ ] **Step 5: Run tests — verify pass**

```bash
pytest tests/test_monitor_agent.py tests/test_post_mortem_agent.py -v
```

- [ ] **Step 6: Commit**

```bash
git add packages/trading_swarm/src/sharpedge_trading/agents/{monitor_agent,post_mortem_agent}.py packages/trading_swarm/tests/test_{monitor_agent,post_mortem_agent}.py
git commit -m "feat(trading): add MonitorAgent and PostMortemAgent with bounded learning loop"
```

---

## Task 13: Daemon + Startup Validation

**Files:**
- Create: `packages/trading_swarm/src/sharpedge_trading/daemon.py`
- Create: `packages/trading_swarm/tests/test_daemon.py`

- [ ] **Step 1: Write failing test**

```python
# packages/trading_swarm/tests/test_daemon.py
import pytest
from unittest.mock import MagicMock, patch
from sharpedge_trading.daemon import TradingDaemon, PromotionGateError

def _mock_supabase_empty():
    client = MagicMock()
    client.table.return_value.select.return_value.execute.return_value.data = []
    client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    return client

def test_promotion_gate_fails_with_no_trades():
    daemon = TradingDaemon(
        supabase_client=_mock_supabase_empty(),
        trading_mode="live",
        anthropic_api_key="test",
        kalshi_api_key="test",
        kalshi_private_key_pem="",
    )
    with pytest.raises(PromotionGateError, match="minimum trades"):
        daemon.check_promotion_gate()

def test_promotion_gate_passes_with_good_paper_history():
    client = MagicMock()
    # 55 resolved trades, positive EV, low drawdown
    trades = [
        {"pnl": 10.0 if i % 2 == 0 else -3.0, "opened_at": "2026-01-01T00:00:00Z",
         "resolved_at": f"2026-0{(i//30)+1}-{(i%28)+1:02d}T00:00:00Z"}
        for i in range(55)
    ]
    client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = trades
    daemon = TradingDaemon(
        supabase_client=client, trading_mode="live",
        anthropic_api_key="test", kalshi_api_key="test", kalshi_private_key_pem="",
    )
    daemon.check_promotion_gate()  # should not raise
```

- [ ] **Step 2: Run — verify fails**

```bash
pytest tests/test_daemon.py -v
```

- [ ] **Step 3: Implement daemon.py**

```python
# src/sharpedge_trading/daemon.py
import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from .events.bus import EventBus
from .config import TradingConfig
from .agents.scan_agent import ScanAgent
from .agents.research_agent import ResearchAgent
from .agents.prediction_agent import PredictionAgent
from .agents.portfolio_manager import PortfolioManager
from .agents.risk_agent import RiskAgent
from .agents.monitor_agent import MonitorAgent
from .agents.post_mortem_agent import PostMortemAgent
from .execution.paper_executor import PaperExecutor
from .execution.kalshi_executor import KalshiExecutor

logger = logging.getLogger("sharpedge.trading.daemon")

_MODELS_DIR = Path(os.environ.get("MODELS_DIR", "data/models/pm"))
_CATEGORIES = ["political", "economic", "crypto", "entertainment", "weather"]


class PromotionGateError(Exception):
    pass


class TradingDaemon:
    def __init__(self, supabase_client, trading_mode: str, anthropic_api_key: str,
                 kalshi_api_key: str, kalshi_private_key_pem: str,
                 starting_bankroll: float = 10000.0):
        self._client = supabase_client
        self._mode = trading_mode
        self._bankroll = starting_bankroll if trading_mode == "paper" else 2000.0
        self._config = TradingConfig(supabase_client)
        self._bus = EventBus()

        from sharpedge_feeds.kalshi_client import KalshiClient, KalshiConfig
        kalshi_cfg = KalshiConfig(api_key=kalshi_api_key, private_key_pem=kalshi_private_key_pem)
        self._kalshi_client = KalshiClient(kalshi_cfg)

        if trading_mode == "live":
            self._executor = KalshiExecutor(self._kalshi_client, supabase_client)
        else:
            self._executor = PaperExecutor(supabase_client, starting_bankroll=self._bankroll)

        from sharpedge_feeds.polymarket_client import PolymarketClient
        self._polymarket_client = PolymarketClient()

        self._scan = ScanAgent(self._kalshi_client, self._bus)
        self._research = ResearchAgent(
            bus=self._bus,
            anthropic_api_key=anthropic_api_key,
            polymarket_client=self._polymarket_client,
        )
        self._prediction = PredictionAgent(self._bus, self._config, anthropic_api_key)
        self._portfolio = PortfolioManager(self._bus, supabase_client, self._config, self._bankroll)
        self._risk = RiskAgent(self._bus, self._config, supabase_client, self._bankroll)
        self._monitor = MonitorAgent(self._bus, self._kalshi_client, supabase_client, self._executor)
        self._post_mortem = PostMortemAgent(self._bus, supabase_client, self._config, anthropic_api_key)

    def _validate_models(self) -> None:
        missing = [c for c in _CATEGORIES if not (_MODELS_DIR / f"{c}.joblib").exists()]
        if missing and self._mode == "live":
            raise RuntimeError(f"Missing RF models for live mode: {missing}. Run train_pm_models.py first.")
        if missing:
            logger.warning("Missing RF models (will use fallback): %s", missing)

    def check_promotion_gate(self) -> None:
        """Validate paper trading history before allowing live mode. Raises PromotionGateError."""
        rows = (
            self._client.table("paper_trades")
            .select("pnl,opened_at,resolved_at")
            .eq("trading_mode", "paper")
            .execute()
            .data or []
        )
        resolved = [r for r in rows if r.get("pnl") is not None]
        if len(resolved) < 50:
            raise PromotionGateError(f"Requires minimum 50 resolved trades (have {len(resolved)})")

        pnls = [r["pnl"] for r in resolved]
        ev = sum(pnls) / len(pnls)
        if ev <= 0:
            raise PromotionGateError(f"Expected value must be positive (current: {ev:.2f})")

        wins = sum(1 for p in pnls if p > 0)
        win_rate = wins / len(pnls)
        if win_rate < 0.45:
            raise PromotionGateError(f"Win rate must be >= 45% (current: {win_rate:.1%})")

        # Max drawdown check
        running = 0.0
        peak = 0.0
        max_dd = 0.0
        for p in pnls:
            running += p
            peak = max(peak, running)
            max_dd = max(max_dd, peak - running)
        if max_dd > 0.20 * self._bankroll:
            raise PromotionGateError(f"Max drawdown too high: ${max_dd:.0f}")

        # Days check
        dates = [r["opened_at"] for r in resolved if r.get("opened_at")]
        if dates:
            first = datetime.fromisoformat(dates[0].replace("Z", "+00:00"))
            last = datetime.fromisoformat(dates[-1].replace("Z", "+00:00"))
            days = (last - first).days
            if days < 30:
                raise PromotionGateError(f"Needs 30+ days of paper trading (have {days})")

        logger.info("Promotion gate PASSED: %d trades, EV=%.2f, win_rate=%.1%", len(resolved), ev, win_rate)

    async def run(self) -> None:
        logger.info("TradingDaemon starting in %s mode", self._mode)
        self._validate_models()
        if self._mode == "live":
            self.check_promotion_gate()

        await asyncio.gather(
            self._scan.run(),
            self._research.run(),
            self._prediction.run(),
            self._portfolio.run(),
            self._risk.run(),
            self._monitor.run(),
            self._post_mortem.run(),
        )


def main() -> None:
    import os
    from sharpedge_db.client import get_supabase_client

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    client = get_supabase_client()
    daemon = TradingDaemon(
        supabase_client=client,
        trading_mode=os.environ.get("TRADING_MODE", "paper"),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        kalshi_api_key=os.environ.get("KALSHI_API_KEY", ""),
        kalshi_private_key_pem=os.environ.get("KALSHI_PRIVATE_KEY_PEM", ""),
    )
    asyncio.run(daemon.run())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests — verify pass**

```bash
pytest tests/test_daemon.py -v
```

- [ ] **Step 5: Commit**

```bash
git add packages/trading_swarm/src/sharpedge_trading/daemon.py packages/trading_swarm/tests/test_daemon.py
git commit -m "feat(trading): add TradingDaemon with startup validation and promotion gate"
```

---

## Task 14: Integration Test

**Files:**
- Create: `packages/trading_swarm/tests/test_integration_pipeline.py`

- [ ] **Step 1: Write integration test**

```python
# packages/trading_swarm/tests/test_integration_pipeline.py
"""Integration test: verifies the full pipeline produces a paper trade in Supabase."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sharpedge_trading.events.bus import EventBus
from sharpedge_trading.events.types import OpportunityEvent
from sharpedge_trading.config import TradingConfig
from sharpedge_trading.agents.prediction_agent import PredictionAgent
from sharpedge_trading.agents.portfolio_manager import PortfolioManager
from sharpedge_trading.agents.risk_agent import RiskAgent
from sharpedge_trading.execution.paper_executor import PaperExecutor

def _make_supabase(inserted_ids=None):
    client = MagicMock()
    client.table.return_value.select.return_value.execute.return_value.data = []
    client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "trade-integration-1"}]
    client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
    return client

@pytest.mark.asyncio
async def test_full_pipeline_paper_trade():
    """End-to-end: OpportunityEvent → paper_trade written to Supabase."""
    bus = EventBus()
    supabase = _make_supabase()
    cfg = MagicMock(spec=TradingConfig)
    cfg.confidence_threshold = 0.03
    cfg.kelly_fraction = 0.25
    cfg.max_category_exposure = 0.20
    cfg.max_total_exposure = 0.40
    cfg.daily_loss_limit = 0.10

    executor = PaperExecutor(supabase_client=supabase, starting_bankroll=10000)
    portfolio = PortfolioManager(bus=bus, supabase_client=supabase, config=cfg, bankroll=10000)
    risk = RiskAgent(bus=bus, config=cfg, supabase_client=supabase, bankroll=10000)
    prediction = PredictionAgent(bus=bus, config=cfg)

    # Seed with a research event that has clear edge
    from sharpedge_trading.events.types import ResearchEvent
    research = ResearchEvent(
        market_id="GDP-Q1", category="economic", kalshi_price=0.35,
        polymarket_price=0.48, signals=[], narrative_summary="strong bullish consensus",
        time_to_resolution_hours=48.0,
    )
    await bus.put_research(research)

    # Run prediction → portfolio → risk in sequence
    with patch.object(prediction, "_rf_predict", return_value=0.65), \
         patch.object(prediction._calibrator, "calibrate", return_value=0.65):
        await prediction.process_one()

    risk._is_paused = lambda: False
    await portfolio.process_one()
    await risk.process_one()

    # Pull execution event and simulate executor
    exec_event = bus._execution.get_nowait()
    trade_id = await executor.execute(exec_event)

    assert trade_id is not None
    assert supabase.table.called
    # Verify insert was called on paper_trades
    calls = [str(c) for c in supabase.table.call_args_list]
    assert any("paper_trades" in c for c in calls)
```

- [ ] **Step 2: Run — verify passes**

```bash
pytest tests/test_integration_pipeline.py -v
```

- [ ] **Step 3: Run full test suite**

```bash
cd packages/trading_swarm && pytest tests/ -v
```
Expected: all tests pass.

- [ ] **Step 4: Final commit**

```bash
git add packages/trading_swarm/tests/test_integration_pipeline.py
git commit -m "test(trading): add end-to-end pipeline integration test"
```

---

## Running the Daemon

```bash
# Paper mode (default)
ANTHROPIC_API_KEY=... KALSHI_API_KEY=... KALSHI_PRIVATE_KEY_PEM="..." \
SUPABASE_URL=... SUPABASE_SERVICE_KEY=... \
TRADING_MODE=paper python -m sharpedge_trading.daemon

# Live mode (requires passing promotion gate)
TRADING_MODE=live python -m sharpedge_trading.daemon
```

Required env vars:
- `TRADING_MODE` — `paper` (default) or `live`
- `ANTHROPIC_API_KEY` — Claude API key for LLM calibration
- `KALSHI_API_KEY` — Kalshi UUID API key
- `KALSHI_PRIVATE_KEY_PEM` — RSA private key for Kalshi auth
- `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` — Supabase credentials
- `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` — for Reddit signals
- `ENABLE_TWITTER_SIGNALS=true` + `TWITTER_BEARER_TOKEN` — optional

---

## Verification

After implementation, verify end-to-end in paper mode:

1. Start daemon with `TRADING_MODE=paper`
2. Wait 5 minutes for first scan cycle
3. Check Supabase `paper_trades` table — should see rows appearing
4. Check `open_positions` — should have matching rows
5. Check logs for `PredictionAgent` edge calculations and `ScanAgent` market counts
6. After a market resolves, check `trade_post_mortems` for loss records
7. Check `trading_config` — values should shift after 3+ losses of same type
