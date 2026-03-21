"""Integration tests — end-to-end pipeline from scan to Supabase."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from sharpedge_trading.config import TradingConfig
from sharpedge_trading.events.bus import EventBus
from sharpedge_trading.events.types import (
    ApprovedEvent,
    ExecutionEvent,
    OpportunityEvent,
    PredictionEvent,
    ResearchEvent,
    ResolutionEvent,
    SignalScore,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config() -> TradingConfig:
    return TradingConfig.from_dict(
        {
            "confidence_threshold": "0.03",
            "kelly_fraction": "0.25",
            "max_category_exposure": "0.20",
            "max_total_exposure": "0.40",
            "daily_loss_limit": "0.10",
            "min_liquidity": "500",
            "min_edge": "0.03",
        }
    )


@pytest.fixture(autouse=True)
def reset_pm_state():
    """Reset post-mortem module-level state before/after every test."""
    import sharpedge_trading.agents.post_mortem_agent as pm_module

    pm_module._auto_adjustment_count = 0
    pm_module._auto_learning_paused = False
    pm_module._loss_counts = {}
    yield
    pm_module._auto_adjustment_count = 0
    pm_module._auto_learning_paused = False
    pm_module._loss_counts = {}


# ---------------------------------------------------------------------------
# Primary integration test: full pipeline → paper_trades in Supabase
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_pipeline_paper_trade_reaches_supabase(config: TradingConfig) -> None:
    """
    Verify: OpportunityEvent → ResearchEvent → PredictionEvent → ApprovedEvent
            → ExecutionEvent → paper_trades written to Supabase
            → monitor detects settlement → ResolutionEvent
            → post-mortem records WIN (record_win called, not record_loss)

    Uses a real EventBus.  Agents are simulated by manually pumping events
    through the bus — this isolates each stage and confirms queue correctness.
    """
    bus = EventBus()

    # ------------------------------------------------------------------
    # Stage 1: Scan emits OpportunityEvent
    # ------------------------------------------------------------------
    opp = OpportunityEvent(
        market_id="NASDAQ-2025-Q2",
        ticker="NASDAQ-2025-Q2",
        category="economic",
        current_price=0.45,
        liquidity=1500.0,
        time_to_resolution=timedelta(days=7),
        price_momentum=0.20,  # > 15% threshold
        spread_ratio=2.5,  # > 2x threshold
    )
    await bus.put_opportunity(opp)

    # ------------------------------------------------------------------
    # Stage 2: Research agent consumes opportunity, emits ResearchEvent
    # ------------------------------------------------------------------
    received_opp = await bus.get_opportunity()
    assert received_opp.market_id == "NASDAQ-2025-Q2"

    research = ResearchEvent(
        market_id=received_opp.market_id,
        opportunity=received_opp,
        narrative="Strong economic indicators suggest YES outcome likely.",
        signal_scores=[
            SignalScore(source="rss", sentiment=0.75, confidence=0.8, age_seconds=120),
            SignalScore(source="polymarket", sentiment=0.70, confidence=0.9, age_seconds=60),
        ],
    )
    await bus.put_research(research)

    # ------------------------------------------------------------------
    # Stage 3: Prediction agent consumes research, emits PredictionEvent
    # ------------------------------------------------------------------
    received_research = await bus.get_research()
    assert received_research.opportunity.market_id == "NASDAQ-2025-Q2"

    prediction = PredictionEvent(
        market_id=received_research.market_id,
        research=received_research,
        base_probability=0.62,
        calibrated_probability=0.62,  # edge = 0.62 - 0.45 - 0.001 = 0.169 > 3%
        edge=0.169,
        confidence_score=0.75,
    )
    await bus.put_prediction(prediction)

    # ------------------------------------------------------------------
    # Stage 4: Portfolio manager consumes prediction, emits ApprovedEvent
    # ------------------------------------------------------------------
    received_prediction = await bus.get_prediction()
    assert received_prediction.edge > 0.03

    approved = ApprovedEvent(
        market_id=received_prediction.market_id,
        prediction=received_prediction,
    )
    await bus.put_approved(approved)

    # ------------------------------------------------------------------
    # Stage 5: Risk agent consumes approved, emits ExecutionEvent
    # ------------------------------------------------------------------
    received_approved = await bus.get_approved()
    assert received_approved.market_id == "NASDAQ-2025-Q2"

    execution = ExecutionEvent(
        market_id="NASDAQ-2025-Q2",
        direction="yes",
        size=25.0,
        entry_price=0.45,
        trading_mode="paper",
    )
    await bus.put_execution(execution)

    # ------------------------------------------------------------------
    # Stage 6: PaperExecutor writes to paper_trades Supabase table
    # ------------------------------------------------------------------
    from sharpedge_trading.execution.paper_executor import PaperExecutor

    received_execution = await bus.get_execution()
    mock_paper_client = MagicMock()
    mock_paper_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    mock_paper_client.table.return_value.upsert.return_value.execute.return_value.data = [
        {"id": "trade-001"}
    ]

    with patch(
        "sharpedge_trading.execution.paper_executor._get_supabase_client",
        return_value=mock_paper_client,
    ):
        executor = PaperExecutor(supabase_url="https://fake.supabase.co", supabase_key="fake-key")
        trade_id = await executor.execute(received_execution)

    assert trade_id is not None
    # Verify paper_trades table was written
    mock_paper_client.table.assert_any_call("paper_trades")

    # ------------------------------------------------------------------
    # Stage 7: Monitor detects settlement → emits ResolutionEvent
    # ------------------------------------------------------------------
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": "pos-001",
            "market_id": "NASDAQ-2025-Q2",
            "size": 25.0,
            "entry_price": 0.45,
            "trading_mode": "paper",
        }
    ]
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = (
        MagicMock()
    )

    mock_kalshi = MagicMock()
    mock_kalshi.get_market.return_value = {"status": "finalized", "result": "yes"}

    from sharpedge_trading.agents.monitor_agent import monitor_once

    with patch(
        "sharpedge_trading.agents.monitor_agent._get_supabase_client", return_value=mock_supabase
    ):
        count = await monitor_once(bus, mock_kalshi)

    assert count == 1
    resolution = await asyncio.wait_for(bus.get_resolution(), timeout=5.0)
    assert resolution.market_id == "NASDAQ-2025-Q2"
    assert resolution.actual_outcome is True
    assert resolution.pnl > 0

    # ------------------------------------------------------------------
    # Stage 8: Post-mortem records the WIN
    # ------------------------------------------------------------------
    from sharpedge_trading.agents.post_mortem_agent import process_resolution

    with patch("sharpedge_trading.agents.post_mortem_agent.record_win") as mock_win:
        with patch("sharpedge_trading.agents.post_mortem_agent.record_loss") as mock_loss:
            await process_resolution(resolution, config, bankroll=10000.0)

    mock_win.assert_called_once()
    mock_loss.assert_not_called()


# ---------------------------------------------------------------------------
# Loss path: ResolutionEvent (loss) → trade_post_mortems written to Supabase
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_loss_writes_post_mortem_to_supabase(config: TradingConfig) -> None:
    """Verify: loss ResolutionEvent → trade_post_mortems row inserted."""
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
    mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock()

    resolution = ResolutionEvent(
        trade_id="trade-loss-001",
        market_id="CRYPTO-BTC-100K",
        actual_outcome=False,
        pnl=-30.0,
        position_size=100.0,
        trading_mode="paper",
    )

    from sharpedge_trading.agents.post_mortem_agent import process_resolution

    with patch(
        "sharpedge_trading.agents.post_mortem_agent._get_supabase_client",
        return_value=mock_supabase,
    ), patch(
        "sharpedge_trading.agents.post_mortem_agent._apply_learning_update", return_value=False
    ), patch(
        "sharpedge_trading.agents.post_mortem_agent._fetch_research_data",
        return_value=(0.70, 0.05),
    ), patch("sharpedge_trading.agents.post_mortem_agent.record_loss"):
        await process_resolution(resolution, config, bankroll=10000.0)

    # Verify trade_post_mortems was written
    mock_supabase.table.assert_any_call("trade_post_mortems")
    insert_calls = [
        call for call in mock_supabase.table.call_args_list if call.args == ("trade_post_mortems",)
    ]
    assert len(insert_calls) >= 1


# ---------------------------------------------------------------------------
# Event bus routing: each event type uses its own isolated queue
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_bus_routes_events_through_correct_queues() -> None:
    """Verify each event type uses its own isolated queue."""
    bus = EventBus()

    opp = OpportunityEvent(
        market_id="MKT-001",
        ticker="MKT-001",
        category="economic",
        current_price=0.5,
        liquidity=1000.0,
        time_to_resolution=timedelta(days=1),
        price_momentum=0.2,
        spread_ratio=2.5,
    )
    resolution = ResolutionEvent(
        trade_id="t-001",
        market_id="MKT-001",
        actual_outcome=True,
        pnl=50.0,
        trading_mode="paper",
    )

    await bus.put_opportunity(opp)
    await bus.put_resolution(resolution)

    got_opp = await bus.get_opportunity()
    got_res = await bus.get_resolution()

    assert got_opp.market_id == "MKT-001"
    assert isinstance(got_opp, OpportunityEvent)
    assert got_res.pnl == 50.0
    assert isinstance(got_res, ResolutionEvent)
