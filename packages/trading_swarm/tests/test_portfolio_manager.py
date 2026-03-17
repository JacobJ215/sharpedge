"""Tests for Portfolio Manager."""
import pytest
from unittest.mock import patch

from sharpedge_trading.agents.portfolio_manager import (
    ExposureState,
    check_exposure,
    _get_bankroll,
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


def _make_prediction(category: str = "economic", kalshi_price: float = 0.45) -> PredictionEvent:
    opp = OpportunityEvent(
        market_id="MKT-001",
        ticker="TICKER-001",
        category=category,
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
    return PredictionEvent(
        market_id="MKT-001",
        research=research,
        base_probability=0.55,
        calibrated_probability=0.55,
        edge=0.10,
        confidence_score=0.8,
    )


# --- _get_bankroll ---

def test_get_bankroll_paper_default():
    with patch.dict("os.environ", {"TRADING_MODE": "paper", "PAPER_BANKROLL": "10000"}):
        assert _get_bankroll() == 10000.0


def test_get_bankroll_live():
    with patch.dict("os.environ", {"TRADING_MODE": "live", "LIVE_BANKROLL": "2000"}):
        assert _get_bankroll() == 2000.0


# --- check_exposure ---

def test_check_exposure_approves_clean_state():
    config = _make_config()
    event = _make_prediction()
    state = ExposureState(total_exposure=0.0, category_exposure={})
    approved, reason = check_exposure(event, config, bankroll=10000.0, state=state)
    assert approved is True
    assert reason == "approved"


def test_check_exposure_rejects_total_cap():
    config = _make_config(max_total_exposure="0.40")
    event = _make_prediction()
    # total_exposure already at 38% → adding 5% would exceed 40%
    state = ExposureState(total_exposure=3800.0, category_exposure={})
    approved, reason = check_exposure(event, config, bankroll=10000.0, state=state)
    assert approved is False
    assert "total exposure" in reason


def test_check_exposure_rejects_category_cap():
    config = _make_config(max_category_exposure="0.20")
    event = _make_prediction(category="economic")
    # economic at 18% → adding 5% would exceed 20%
    state = ExposureState(total_exposure=1800.0, category_exposure={"economic": 1800.0})
    approved, reason = check_exposure(event, config, bankroll=10000.0, state=state)
    assert approved is False
    assert "economic" in reason


def test_check_exposure_allows_different_category():
    config = _make_config(max_category_exposure="0.20")
    event = _make_prediction(category="crypto")
    # economic full, but crypto empty
    state = ExposureState(total_exposure=1000.0, category_exposure={"economic": 1800.0})
    approved, reason = check_exposure(event, config, bankroll=10000.0, state=state)
    assert approved is True
