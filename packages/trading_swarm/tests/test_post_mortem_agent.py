"""Tests for Post-Mortem Agent."""
import pytest
from unittest.mock import MagicMock, patch

from sharpedge_trading.agents.post_mortem_agent import (
    _classify_attribution,
    _apply_learning_update,
    process_resolution,
)
from sharpedge_trading.agents.post_mortem_agent import (
    _auto_adjustment_count,
    _auto_learning_paused,
    _loss_counts,
)
import sharpedge_trading.agents.post_mortem_agent as pm_module
from sharpedge_trading.config import TradingConfig
from sharpedge_trading.events.types import ResolutionEvent


@pytest.fixture(autouse=True)
def reset_pm_state():
    """Reset auto-learning state between tests."""
    pm_module._auto_adjustment_count = 0
    pm_module._auto_learning_paused = False
    pm_module._loss_counts = {}
    yield
    pm_module._auto_adjustment_count = 0
    pm_module._auto_learning_paused = False
    pm_module._loss_counts = {}


def _make_config() -> TradingConfig:
    return TradingConfig.from_dict({
        "confidence_threshold": "0.03",
        "kelly_fraction": "0.25",
        "max_category_exposure": "0.20",
        "max_total_exposure": "0.40",
        "daily_loss_limit": "0.10",
        "min_liquidity": "500",
        "min_edge": "0.03",
    })


def _make_loss_event(pnl: float = -50.0) -> ResolutionEvent:
    return ResolutionEvent(
        trade_id="trade-001",
        market_id="MKT-001",
        actual_outcome=False,
        pnl=pnl,
        trading_mode="paper",
    )


# --- _classify_attribution ---

def test_classify_model_error_when_prediction_very_wrong():
    event = _make_loss_event()
    # calibrated_prob=0.70 but outcome=0.0 → |0.70 - 0.0| = 0.70 > 0.30
    attr = _classify_attribution(event, calibrated_prob=0.70, position_size_pct=0.02)
    assert attr["model_error_score"] == 1.0


def test_classify_no_model_error_when_prediction_close():
    event = _make_loss_event()
    # calibrated_prob=0.20 → |0.20 - 0.0| = 0.20 ≤ 0.30
    attr = _classify_attribution(event, calibrated_prob=0.20, position_size_pct=0.02)
    assert attr["model_error_score"] == 0.0


def test_classify_sizing_error_when_position_too_large():
    event = _make_loss_event()
    attr = _classify_attribution(event, calibrated_prob=0.50, position_size_pct=0.05)
    assert attr["sizing_error_score"] == 1.0


def test_classify_no_sizing_error_for_small_position():
    event = _make_loss_event()
    attr = _classify_attribution(event, calibrated_prob=0.50, position_size_pct=0.02)
    assert attr["sizing_error_score"] == 0.0


def test_classify_variance_for_low_probability_loss():
    event = _make_loss_event()
    # calibrated_prob=0.20 < 0.35 and outcome=False → variance
    attr = _classify_attribution(event, calibrated_prob=0.20, position_size_pct=0.02)
    assert attr["variance_score"] == 1.0


# --- _apply_learning_update ---

def test_apply_learning_skips_when_paused():
    pm_module._auto_learning_paused = True
    config = _make_config()
    attribution = {"model_error_score": 1.0, "signal_error_score": 0.5, "sizing_error_score": 0.0, "variance_score": 0.0}
    result = _apply_learning_update(attribution, config)
    assert result is False


def test_apply_learning_pauses_after_max_adjustments():
    config = _make_config()
    attribution = {"model_error_score": 1.0, "signal_error_score": 0.0, "sizing_error_score": 0.0, "variance_score": 0.0}

    mock_client = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()

    with patch("sharpedge_trading.agents.post_mortem_agent._get_supabase_client", return_value=mock_client):
        with patch("sharpedge_trading.agents.post_mortem_agent.load_config", return_value=config):
            # Pre-seed counts so every call triggers (2, 5, 8, 11, 14 → after increment: 3,6,9,12,15)
            for i in range(5):
                pm_module._loss_counts["model_error"] = 3 * i + 2  # next increment = multiple of 3
                _apply_learning_update(attribution, config)

    assert pm_module._auto_learning_paused is True
    assert pm_module._auto_adjustment_count >= 5


def test_apply_learning_does_not_adjust_before_3_losses():
    """Adjustment should not fire on 1st or 2nd model_error loss."""
    config = _make_config()
    attribution = {"model_error_score": 1.0, "signal_error_score": 0.0, "sizing_error_score": 0.0, "variance_score": 0.0}
    mock_client = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()

    with patch("sharpedge_trading.agents.post_mortem_agent._get_supabase_client", return_value=mock_client):
        with patch("sharpedge_trading.agents.post_mortem_agent.load_config", return_value=config):
            result1 = _apply_learning_update(attribution, config)  # 1st loss
            result2 = _apply_learning_update(attribution, config)  # 2nd loss

    assert result1 is False  # no adjustment yet
    assert result2 is False  # still no adjustment
    mock_client.table.return_value.upsert.assert_not_called()


def test_apply_learning_adjusts_on_3rd_loss():
    """Adjustment fires on 3rd loss of same type."""
    config = _make_config()
    attribution = {"model_error_score": 1.0, "signal_error_score": 0.0, "sizing_error_score": 0.0, "variance_score": 0.0}
    mock_client = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()

    with patch("sharpedge_trading.agents.post_mortem_agent._get_supabase_client", return_value=mock_client):
        with patch("sharpedge_trading.agents.post_mortem_agent.load_config", return_value=config):
            _apply_learning_update(attribution, config)  # 1st
            _apply_learning_update(attribution, config)  # 2nd
            result3 = _apply_learning_update(attribution, config)  # 3rd — should fire

    assert result3 is True
    mock_client.table.return_value.upsert.assert_called()


def test_auto_learning_pause_writes_supabase_flag():
    """When auto-learning pauses (5 consecutive adjustments), flag is written to Supabase."""
    config = _make_config()
    attribution = {"model_error_score": 1.0, "signal_error_score": 0.0, "sizing_error_score": 0.0, "variance_score": 0.0}
    mock_client = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()

    written_keys = []

    def capture_upsert(data, **kwargs):
        written_keys.append(data.get("key"))
        return MagicMock()

    mock_client.table.return_value.upsert.side_effect = capture_upsert

    # Pre-seed loss count so every call fires (model_error at 2, so next is 3rd → fires)
    pm_module._loss_counts = {"model_error": 2}
    # Pre-seed adjustment count to 4 so 5th adjustment triggers pause
    pm_module._auto_adjustment_count = 4

    with patch("sharpedge_trading.agents.post_mortem_agent._get_supabase_client", return_value=mock_client):
        with patch("sharpedge_trading.agents.post_mortem_agent.load_config", return_value=config):
            _apply_learning_update(attribution, config)

    assert pm_module._auto_learning_paused is True
    assert "auto_learning_paused" in written_keys


# --- process_resolution ---

@pytest.mark.asyncio
async def test_process_resolution_records_win():
    event = ResolutionEvent(
        trade_id="t1", market_id="MKT-001",
        actual_outcome=True, pnl=25.0, trading_mode="paper",
    )
    config = _make_config()
    with patch("sharpedge_trading.agents.post_mortem_agent.record_win") as mock_win:
        with patch("sharpedge_trading.agents.post_mortem_agent.record_loss") as mock_loss:
            await process_resolution(event, config, bankroll=10000.0)
    mock_win.assert_called_once()
    mock_loss.assert_not_called()


@pytest.mark.asyncio
async def test_process_resolution_records_loss_and_writes_post_mortem():
    event = _make_loss_event(pnl=-50.0)
    config = _make_config()

    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock()

    with patch("sharpedge_trading.agents.post_mortem_agent.record_loss") as mock_loss:
        with patch("sharpedge_trading.agents.post_mortem_agent._get_supabase_client", return_value=mock_client):
            with patch("sharpedge_trading.agents.post_mortem_agent._apply_learning_update", return_value=False):
                await process_resolution(event, config, bankroll=10000.0)

    mock_loss.assert_called_once_with(50.0)
    mock_client.table.assert_called()


@pytest.mark.asyncio
async def test_process_resolution_skips_post_mortem_when_no_supabase():
    event = _make_loss_event()
    config = _make_config()

    with patch("sharpedge_trading.agents.post_mortem_agent.record_loss"):
        with patch("sharpedge_trading.agents.post_mortem_agent._get_supabase_client", return_value=None):
            with patch("sharpedge_trading.agents.post_mortem_agent._apply_learning_update", return_value=False) as mock_update:
                await process_resolution(event, config, bankroll=10000.0)

    # Should still attempt learning update even without Supabase for post-mortem
    mock_update.assert_called_once()
