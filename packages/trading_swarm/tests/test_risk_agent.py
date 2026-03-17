"""Tests for Risk Agent."""
import pytest
from unittest.mock import patch

from sharpedge_trading.agents.risk_agent import (
    compute_kelly_size,
    process_approved,
)
from sharpedge_trading.config import TradingConfig
from sharpedge_trading.events.bus import EventBus
from sharpedge_trading.events.types import (
    ApprovedEvent,
    OpportunityEvent,
    PredictionEvent,
    ResearchEvent,
    SignalScore,
)
from datetime import timedelta


def _make_config(**overrides) -> TradingConfig:
    return TradingConfig.from_dict({
        "confidence_threshold": "0.03",
        "kelly_fraction": "0.25",
        "max_category_exposure": "0.20",
        "max_total_exposure": "0.40",
        "daily_loss_limit": "0.10",
        "min_liquidity": "500",
        "min_edge": "0.03",
        **overrides,
    })


def _make_approved(calibrated_prob: float = 0.60, kalshi_price: float = 0.45) -> ApprovedEvent:
    opp = OpportunityEvent(
        market_id="MKT-001",
        ticker="TICKER-001",
        category="economic",
        current_price=kalshi_price,
        liquidity=1000.0,
        time_to_resolution=timedelta(hours=24),
        price_momentum=0.20,
        spread_ratio=2.5,
    )
    sig = SignalScore(source="rss_ap", sentiment=0.5, confidence=0.8, age_seconds=60.0)
    research = ResearchEvent(
        market_id="MKT-001",
        opportunity=opp,
        narrative="test",
        signal_scores=[sig],
    )
    pred = PredictionEvent(
        market_id="MKT-001",
        research=research,
        base_probability=0.55,
        calibrated_probability=calibrated_prob,
        edge=0.10,
        confidence_score=0.8,
    )
    return ApprovedEvent(market_id="MKT-001", prediction=pred)


# --- compute_kelly_size ---

def test_kelly_size_standard_case():
    # p=0.60, price=0.45, b=(1-0.45)/0.45=1.222, f*=(0.6*1.222-0.4)/1.222=0.273, 0.25*0.273=0.068
    # clamped to max 5% → 0.05 * 10000 = $500
    size = compute_kelly_size(calibrated_prob=0.60, kalshi_price=0.45, bankroll=10000, kelly_fraction=0.25)
    assert 0.0 < size <= 500.0  # within [0.1%, 5%] bounds


def test_kelly_size_clamps_to_minimum():
    # Very slight edge → tiny Kelly → clamp to min 0.1%
    size = compute_kelly_size(calibrated_prob=0.451, kalshi_price=0.45, bankroll=10000, kelly_fraction=0.25)
    assert size == pytest.approx(10000 * 0.001, abs=0.01)


def test_kelly_size_clamps_to_maximum():
    # Huge edge → large Kelly → clamp to max 5%
    size = compute_kelly_size(calibrated_prob=0.95, kalshi_price=0.10, bankroll=10000, kelly_fraction=0.25)
    assert size == pytest.approx(10000 * 0.05, abs=0.01)


def test_kelly_handles_price_near_zero():
    # price=0.01 → floored to 0.05 to avoid division issues
    size = compute_kelly_size(calibrated_prob=0.60, kalshi_price=0.01, bankroll=10000, kelly_fraction=0.25)
    assert size > 0


def test_kelly_handles_price_near_one():
    size = compute_kelly_size(calibrated_prob=0.50, kalshi_price=0.99, bankroll=10000, kelly_fraction=0.25)
    assert size == pytest.approx(10000 * 0.001, abs=0.01)


# --- process_approved ---

@pytest.mark.asyncio
async def test_process_approved_emits_execution_event():
    bus = EventBus()
    config = _make_config()
    event = _make_approved(calibrated_prob=0.60, kalshi_price=0.45)

    with patch.dict("os.environ", {"TRADING_MODE": "paper", "PAPER_BANKROLL": "10000"}):
        emitted = await process_approved(event, bus, config)

    assert emitted is True
    execution = await bus.get_execution()
    assert execution.market_id == "MKT-001"
    assert execution.direction == "yes"  # calibrated(0.60) > kalshi(0.45)
    assert execution.trading_mode == "paper"
    assert 10.0 <= execution.size <= 500.0  # within [0.1%, 5%] of 10000


@pytest.mark.asyncio
async def test_process_approved_direction_no_when_overpriced():
    bus = EventBus()
    config = _make_config()
    # calibrated=0.35 < kalshi=0.50 → bet NO
    event = _make_approved(calibrated_prob=0.35, kalshi_price=0.50)

    with patch.dict("os.environ", {"TRADING_MODE": "paper", "PAPER_BANKROLL": "10000"}):
        await process_approved(event, bus, config)

    execution = await bus.get_execution()
    assert execution.direction == "no"
