"""Tests for Risk Agent."""

from datetime import UTC, timedelta
from unittest.mock import patch

import pytest
from sharpedge_trading.agents.risk_agent import (
    _breaker,
    check_circuit_breakers,
    compute_kelly_size,
    process_approved,
    record_loss,
    record_win,
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


def _make_config(**overrides) -> TradingConfig:
    return TradingConfig.from_dict(
        {
            "confidence_threshold": "0.03",
            "kelly_fraction": "0.25",
            "max_category_exposure": "0.20",
            "max_total_exposure": "0.40",
            "daily_loss_limit": "0.10",
            "min_liquidity": "500",
            "min_edge": "0.03",
            **overrides,
        }
    )


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


@pytest.fixture(autouse=True)
def reset_breaker():
    """Reset circuit breaker state before each test."""
    _breaker.consecutive_losses = 0
    _breaker.daily_loss = 0.0
    _breaker.daily_loss_reset_date = ""
    _breaker.paused_until = None
    yield


# --- compute_kelly_size ---


def test_kelly_size_standard_case():
    # p=0.60, price=0.45, b=(1-0.45)/0.45=1.222, f*=(0.6*1.222-0.4)/1.222=0.273, 0.25*0.273=0.068
    # clamped to max 5% → 0.05 * 10000 = $500
    size = compute_kelly_size(
        calibrated_prob=0.60, kalshi_price=0.45, bankroll=10000, kelly_fraction=0.25
    )
    assert 0.0 < size <= 500.0  # within [0.1%, 5%] bounds


def test_kelly_size_clamps_to_minimum():
    # Very slight edge → tiny Kelly → clamp to min 0.1%
    size = compute_kelly_size(
        calibrated_prob=0.451, kalshi_price=0.45, bankroll=10000, kelly_fraction=0.25
    )
    assert size == pytest.approx(10000 * 0.001, abs=0.01)


def test_kelly_size_clamps_to_maximum():
    # Huge edge → large Kelly → clamp to max 5%
    size = compute_kelly_size(
        calibrated_prob=0.95, kalshi_price=0.10, bankroll=10000, kelly_fraction=0.25
    )
    assert size == pytest.approx(10000 * 0.05, abs=0.01)


def test_kelly_handles_price_near_zero():
    # price=0.01 → floored to 0.05 to avoid division issues
    size = compute_kelly_size(
        calibrated_prob=0.60, kalshi_price=0.01, bankroll=10000, kelly_fraction=0.25
    )
    assert size > 0


def test_kelly_handles_price_near_one():
    size = compute_kelly_size(
        calibrated_prob=0.50, kalshi_price=0.99, bankroll=10000, kelly_fraction=0.25
    )
    assert size == pytest.approx(10000 * 0.001, abs=0.01)


def test_kelly_negative_f_star_returns_minimum():
    """When Kelly f* <= 0 (no edge), return minimum position size."""
    # calibrated_prob=0.10, kalshi_price=0.90 → b=(0.10)/0.90=0.111
    # f*=(0.10*0.111 - 0.90)/0.111 → very negative
    size = compute_kelly_size(
        calibrated_prob=0.10, kalshi_price=0.90, bankroll=10000, kelly_fraction=0.25
    )
    assert size == pytest.approx(10000 * 0.001, abs=0.01)


# --- circuit breakers ---


def test_circuit_breakers_ok_by_default():
    config = _make_config()
    with patch.dict("os.environ", {"TRADING_MODE": "paper", "PAPER_BANKROLL": "10000"}):
        ok, reason = check_circuit_breakers(config)
    assert ok is True
    assert reason == "ok"


def test_circuit_breakers_daily_loss_exceeded():
    from datetime import datetime

    config = _make_config(daily_loss_limit="0.10")
    # daily_loss_limit = 10% of bankroll (10000) = $1000; set loss to $1100
    _breaker.daily_loss = 1100.0
    _breaker.daily_loss_reset_date = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    with patch.dict("os.environ", {"TRADING_MODE": "paper", "PAPER_BANKROLL": "10000"}):
        ok, reason = check_circuit_breakers(config)
    assert ok is False
    assert "daily loss" in reason


def test_circuit_breakers_five_consecutive_losses():
    config = _make_config()
    _breaker.consecutive_losses = 5
    with patch.dict("os.environ", {"TRADING_MODE": "paper", "PAPER_BANKROLL": "10000"}):
        ok, reason = check_circuit_breakers(config)
    assert ok is False
    assert "consecutive" in reason


def test_circuit_breakers_paused_until_active():
    from datetime import datetime, timedelta

    config = _make_config()
    _breaker.paused_until = datetime.now(tz=UTC) + timedelta(hours=1)
    with patch.dict("os.environ", {"TRADING_MODE": "paper", "PAPER_BANKROLL": "10000"}):
        ok, reason = check_circuit_breakers(config)
    assert ok is False
    assert "circuit breaker active" in reason


def test_record_loss_updates_state():
    record_loss(200.0)
    assert _breaker.daily_loss == pytest.approx(200.0)
    assert _breaker.consecutive_losses == 1


def test_record_loss_accumulates():
    record_loss(100.0)
    record_loss(150.0)
    assert _breaker.daily_loss == pytest.approx(250.0)
    assert _breaker.consecutive_losses == 2


def test_record_win_resets_consecutive_losses():
    _breaker.consecutive_losses = 3
    _breaker.daily_loss = 300.0
    record_win()
    assert _breaker.consecutive_losses == 0
    assert _breaker.daily_loss == pytest.approx(300.0)  # daily loss not reset by win


def test_daily_loss_resets_on_new_date():
    """Daily loss counter should reset when date changes."""
    config = _make_config()
    _breaker.daily_loss = 500.0
    _breaker.daily_loss_reset_date = "2000-01-01"  # old date → triggers reset
    with patch.dict("os.environ", {"TRADING_MODE": "paper", "PAPER_BANKROLL": "10000"}):
        ok, _reason = check_circuit_breakers(config)
    assert ok is True
    assert _breaker.daily_loss == 0.0


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


@pytest.mark.asyncio
async def test_process_approved_blocked_by_circuit_breaker():
    from datetime import datetime

    bus = EventBus()
    config = _make_config(daily_loss_limit="0.10")
    event = _make_approved()
    _breaker.daily_loss = 1100.0  # exceeds 10% of 10000
    _breaker.daily_loss_reset_date = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    with patch.dict("os.environ", {"TRADING_MODE": "paper", "PAPER_BANKROLL": "10000"}):
        emitted = await process_approved(event, bus, config)

    assert emitted is False


def test_circuit_breaker_sends_slack_alert(monkeypatch):
    """Circuit breaker fires a Slack alert when consecutive losses reach 5."""
    # Reset state
    _breaker.consecutive_losses = 5
    _breaker.paused_until = None

    alerts_sent = []
    monkeypatch.setattr(
        "sharpedge_trading.agents.risk_agent.send_alert",
        lambda text: alerts_sent.append(text),
    )

    config = _make_config()
    with patch.dict("os.environ", {"TRADING_MODE": "paper", "PAPER_BANKROLL": "10000"}):
        ok, reason = check_circuit_breakers(config)

    assert not ok
    assert "consecutive" in reason
    assert len(alerts_sent) == 1
    assert "CIRCUIT BREAKER" in alerts_sent[0]
