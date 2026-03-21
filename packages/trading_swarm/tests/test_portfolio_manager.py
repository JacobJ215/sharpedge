"""Tests for Portfolio Manager."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from sharpedge_trading.agents.portfolio_manager import (
    ExposureState,
    _acquire_advisory_lock,
    _release_advisory_lock,
    check_exposure,
)
from sharpedge_trading.config import TradingConfig
from sharpedge_trading.events.types import (
    OpportunityEvent,
    PredictionEvent,
    ResearchEvent,
    SignalScore,
)
from sharpedge_trading.utils import get_bankroll


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


def _make_prediction(
    category: str = "economic", kalshi_price: float = 0.45, ticker: str = "TICKER-001"
) -> PredictionEvent:
    opp = OpportunityEvent(
        market_id="MKT-001",
        ticker=ticker,
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


# --- get_bankroll ---


def test_get_bankroll_paper_default():
    with patch.dict("os.environ", {"TRADING_MODE": "paper", "PAPER_BANKROLL": "10000"}):
        assert get_bankroll() == 10000.0


def test_get_bankroll_live():
    with patch.dict("os.environ", {"TRADING_MODE": "live", "LIVE_BANKROLL": "2000"}):
        assert get_bankroll() == 2000.0


# --- ExposureState defaults ---


def test_exposure_state_defaults():
    state = ExposureState()
    assert state.total_exposure == 0.0
    assert state.category_exposure == {}
    assert state.correlated_series == []


def test_exposure_state_instances_are_independent():
    # Verify field(default_factory=dict) — each instance gets its own dict
    s1 = ExposureState()
    s2 = ExposureState()
    s1.category_exposure["foo"] = 1.0
    assert "foo" not in s2.category_exposure


# --- check_exposure ---


def test_check_exposure_approves_clean_state():
    config = _make_config()
    event = _make_prediction()
    state = ExposureState(total_exposure=0.0)
    approved, reason = check_exposure(event, config, bankroll=10000.0, state=state)
    assert approved is True
    assert reason == "approved"


def test_check_exposure_rejects_total_cap():
    config = _make_config(max_total_exposure="0.40")
    event = _make_prediction()
    # total_exposure already at 38% → adding 5% would exceed 40%
    state = ExposureState(total_exposure=3800.0)
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
    approved, _reason = check_exposure(event, config, bankroll=10000.0, state=state)
    assert approved is True


# --- correlation flag ---


def test_check_exposure_rejects_correlated_series():
    config = _make_config()
    # Ticker "ECON-CPI-2026" → series "ECON-CPI"
    event = _make_prediction(ticker="ECON-CPI-2026")
    state = ExposureState(total_exposure=0.0, correlated_series=["ECON-CPI"])
    approved, reason = check_exposure(event, config, bankroll=10000.0, state=state)
    assert approved is False
    assert "ECON-CPI" in reason


def test_check_exposure_allows_different_series():
    config = _make_config()
    # Ticker "ECON-JOBS-2026" → series "ECON-JOBS", not "ECON-CPI"
    event = _make_prediction(ticker="ECON-JOBS-2026")
    state = ExposureState(total_exposure=0.0, correlated_series=["ECON-CPI"])
    approved, _reason = check_exposure(event, config, bankroll=10000.0, state=state)
    assert approved is True


# --- advisory lock ---


def test_acquire_advisory_lock_no_supabase_returns_true():
    """Without Supabase credentials, lock should succeed (fail open)."""
    result = _acquire_advisory_lock("", "")
    assert result is True


def test_acquire_advisory_lock_supabase_exception_fails_open():
    """If Supabase raises, lock should fail open (return True)."""
    with patch("builtins.__import__", side_effect=Exception("no supabase")):
        # patch via sys.modules so the local import fails
        pass
    # Simpler: patch create_client inside supabase module
    import sys

    fake_supabase = MagicMock()
    fake_supabase.create_client.side_effect = Exception("conn refused")
    with patch.dict(sys.modules, {"supabase": fake_supabase}):
        result = _acquire_advisory_lock("http://fake-url", "fake-key")
    assert result is True


def test_acquire_advisory_lock_retry_path():
    """Simulate first lock call returns False, second returns True."""
    import sys

    mock_client = MagicMock()
    # First call returns False, second returns True
    mock_client.rpc.return_value.execute.side_effect = [
        MagicMock(data=False),
        MagicMock(data=True),
    ]
    fake_supabase = MagicMock()
    fake_supabase.create_client.return_value = mock_client
    with patch.dict(sys.modules, {"supabase": fake_supabase}):
        first = _acquire_advisory_lock("http://fake-url", "fake-key")
        second = _acquire_advisory_lock("http://fake-url", "fake-key")
    assert first is False
    assert second is True


def test_release_advisory_lock_no_supabase_is_noop():
    """Release with empty credentials should not raise."""
    _release_advisory_lock("", "")  # must not raise
