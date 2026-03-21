"""Tests for daemon.py — London School TDD, all external deps mocked."""

from __future__ import annotations

import asyncio
import contextlib
import datetime
from unittest.mock import MagicMock, patch

import pytest
from sharpedge_trading.agents.prediction_agent import validate_models_at_startup
from sharpedge_trading.config import TradingConfig
from sharpedge_trading.daemon import (
    PromotionGateResult,
    _compute_ece,
    _compute_max_drawdown,
    _run_gate_check,
    check_promotion_gate,
)

# ---------------------------------------------------------------------------
# _compute_max_drawdown
# ---------------------------------------------------------------------------


def test_max_drawdown_flat():
    # All wins, no drawdown
    result = _compute_max_drawdown([10.0, 20.0, 30.0])
    assert result == 0.0


def test_max_drawdown_all_losses():
    result = _compute_max_drawdown([-100.0, -100.0, -100.0])
    assert abs(result - 300.0) < 0.01


def test_max_drawdown_peak_then_trough():
    # Up 500, then down 300 → drawdown = 300
    result = _compute_max_drawdown([500.0, -300.0])
    assert abs(result - 300.0) < 0.01


def test_max_drawdown_empty():
    result = _compute_max_drawdown([])
    assert result == 0.0


def test_max_drawdown_single_win():
    result = _compute_max_drawdown([100.0])
    assert result == 0.0


def test_max_drawdown_recovery():
    # Down 200, then back up 200 — max drawdown is still 200
    result = _compute_max_drawdown([-200.0, 200.0])
    assert abs(result - 200.0) < 0.01


# ---------------------------------------------------------------------------
# _compute_ece
# ---------------------------------------------------------------------------


def test_ece_perfect_calibration():
    # All confidence 0.9, all outcomes True — ECE = |0.9 - 1.0| = 0.1
    confs = [0.9] * 10
    outcomes = [True] * 10
    ece = _compute_ece(confs, outcomes)
    # ECE of 0.1 is the theoretical minimum for this bucket (confidence 0.9, outcome 1.0)
    assert ece < 0.15


def test_ece_worst_case():
    # All confidence 0.9, all outcomes False
    confs = [0.9] * 10
    outcomes = [False] * 10
    ece = _compute_ece(confs, outcomes)
    assert ece > 0.5


def test_ece_empty_returns_one():
    assert _compute_ece([], []) == 1.0


def test_ece_mixed_calibration():
    # 0.3 confidence, 0.3 win rate — reasonably calibrated
    confs = [0.3] * 10
    outcomes = [True] * 3 + [False] * 7
    ece = _compute_ece(confs, outcomes)
    assert ece < 0.05


# ---------------------------------------------------------------------------
# Trade factory helper
# ---------------------------------------------------------------------------


def _make_trades(
    n: int = 55,
    win_rate: float = 0.6,
    spread_days: int = 35,
    calibrated: bool = True,
) -> list[dict]:
    """Build a list of fake resolved trade dicts.

    When calibrated=True, confidence_score matches actual_outcome closely
    so that ECE < 0.10 for the gate check.
    """
    base = datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC)
    trades = []
    for i in range(n):
        ts = (base + datetime.timedelta(days=i * spread_days / n)).isoformat()
        is_win = i < int(n * win_rate)
        pnl = 50.0 if is_win else -30.0
        # Use well-calibrated confidence: 0.95 for wins, 0.05 for losses
        # → ECE ≈ win_rate*|0.95-1.0| + (1-win_rate)*|0.05-0.0| which is near 0.05
        conf = (
            0.95
            if (is_win and calibrated)
            else (0.05 if calibrated else (0.70 if is_win else 0.30))
        )
        trades.append(
            {
                "pnl": pnl,
                "actual_outcome": is_win,
                "confidence_score": conf,
                "opened_at": ts,
                "resolved_at": ts,
            }
        )
    return trades


def _mock_client(trades: list[dict]) -> MagicMock:
    """Build a MagicMock Supabase client that returns the given trades.

    The Supabase query chain is:
      client.table(...).select(...).eq(...).not_.is_(...).execute()
    Note: `.not_` is attribute access (not a call), so we use `.not_.is_`
    rather than `.not_.return_value.is_`.
    """
    mock = MagicMock()
    (
        mock.table.return_value.select.return_value.eq.return_value.not_.is_.return_value.execute.return_value.data
    ) = trades
    return mock


# ---------------------------------------------------------------------------
# check_promotion_gate
# ---------------------------------------------------------------------------


def test_promotion_gate_passes_with_good_data():
    trades = _make_trades(n=60, win_rate=0.65, spread_days=40)
    mock_client = _mock_client(trades)

    with patch("sharpedge_trading.daemon._get_supabase_client", return_value=mock_client):
        result = check_promotion_gate(client=mock_client)

    assert result.passed, f"Gate failed: {result.checks}"


def test_promotion_gate_fails_with_too_few_trades():
    trades = _make_trades(n=20, win_rate=0.65, spread_days=40)
    mock_client = _mock_client(trades)

    with patch("sharpedge_trading.daemon._get_supabase_client", return_value=mock_client):
        result = check_promotion_gate(client=mock_client)

    assert not result.passed
    assert not result.checks["min_trades"][0]


def test_promotion_gate_fails_with_bad_sharpe():
    # All losses → sharpe < 0
    trades = _make_trades(n=60, win_rate=0.0, spread_days=40)
    mock_client = _mock_client(trades)

    with patch("sharpedge_trading.daemon._get_supabase_client", return_value=mock_client):
        result = check_promotion_gate(client=mock_client)

    assert not result.passed


def test_promotion_gate_fails_when_supabase_unavailable():
    with patch("sharpedge_trading.daemon._get_supabase_client", return_value=None):
        result = check_promotion_gate()

    assert not result.passed
    # All checks should fail
    for name, (ok, _) in result.checks.items():
        assert not ok, f"Expected {name} to fail but passed"


def test_promotion_gate_result_is_dataclass():
    result = PromotionGateResult(passed=True, checks={"foo": (True, "ok")})
    assert result.passed
    assert result.checks["foo"] == (True, "ok")


def test_promotion_gate_fails_insufficient_period():
    # Only 5 days spread — fails min_period
    trades = _make_trades(n=60, win_rate=0.65, spread_days=5)
    mock_client = _mock_client(trades)

    with patch("sharpedge_trading.daemon._get_supabase_client", return_value=mock_client):
        result = check_promotion_gate(client=mock_client)

    assert not result.passed
    assert not result.checks["min_period"][0]


def test_promotion_gate_fails_low_win_rate():
    # 35% win rate — below the 45% threshold
    trades = _make_trades(n=60, win_rate=0.35, spread_days=40)
    mock_client = _mock_client(trades)

    with patch("sharpedge_trading.daemon._get_supabase_client", return_value=mock_client):
        result = check_promotion_gate(client=mock_client)

    assert not result.checks["win_rate"][0]


def test_promotion_gate_checks_all_keys():
    trades = _make_trades(n=60, win_rate=0.65, spread_days=40)
    mock_client = _mock_client(trades)

    with patch("sharpedge_trading.daemon._get_supabase_client", return_value=mock_client):
        result = check_promotion_gate(client=mock_client)

    expected_keys = {
        "min_period",
        "min_trades",
        "min_trade_spread",
        "positive_ev",
        "sharpe_ratio",
        "win_rate",
        "max_drawdown",
        "ece_calibration",
    }
    assert set(result.checks.keys()) == expected_keys


# ---------------------------------------------------------------------------
# validate_models_at_startup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gate_check_sends_passed_alert_on_first_pass(monkeypatch):
    """Gate check sends PASSED alert when gate passes for the first time."""
    import sharpedge_trading.daemon as daemon_mod

    # Reset module flag
    daemon_mod._gate_announced = False

    passed_result = PromotionGateResult(
        passed=True,
        checks={"min_trades": (True, "trades=60 (need >=50)")},
    )
    alerts_sent = []

    monkeypatch.setattr("sharpedge_trading.daemon.check_promotion_gate", lambda: passed_result)
    monkeypatch.setattr(
        "sharpedge_trading.alerts.slack.send_alert",
        lambda text: alerts_sent.append(text),
    )

    config = TradingConfig.defaults()
    task = asyncio.create_task(_run_gate_check(config))
    await asyncio.sleep(0.05)
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task

    assert len(alerts_sent) == 1
    assert "PASSED" in alerts_sent[0]


@pytest.mark.asyncio
async def test_gate_check_suppresses_duplicate_passed_alert(monkeypatch):
    """Gate check does NOT re-send PASSED alert if gate already announced."""
    import sharpedge_trading.daemon as daemon_mod

    daemon_mod._gate_announced = True  # Already announced

    passed_result = PromotionGateResult(
        passed=True,
        checks={"min_trades": (True, "trades=60 (need >=50)")},
    )
    alerts_sent = []

    monkeypatch.setattr("sharpedge_trading.daemon.check_promotion_gate", lambda: passed_result)
    monkeypatch.setattr(
        "sharpedge_trading.alerts.slack.send_alert",
        lambda text: alerts_sent.append(text),
    )

    config = TradingConfig.defaults()
    task = asyncio.create_task(_run_gate_check(config))
    await asyncio.sleep(0.05)
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task

    assert len(alerts_sent) == 0  # No duplicate


@pytest.mark.asyncio
async def test_gate_check_sends_status_when_not_passed(monkeypatch):
    """Gate check sends daily status when gate has not yet passed."""
    import sharpedge_trading.daemon as daemon_mod

    daemon_mod._gate_announced = False

    not_passed_result = PromotionGateResult(
        passed=False,
        checks={
            "min_trades": (False, "trades=12 (need >=50)"),
            "min_period": (True, "period=35.0d (need >=30)"),
        },
    )
    alerts_sent = []

    monkeypatch.setattr("sharpedge_trading.daemon.check_promotion_gate", lambda: not_passed_result)
    monkeypatch.setattr(
        "sharpedge_trading.alerts.slack.send_alert",
        lambda text: alerts_sent.append(text),
    )

    config = TradingConfig.defaults()
    task = asyncio.create_task(_run_gate_check(config))
    await asyncio.sleep(0.05)
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task

    assert len(alerts_sent) == 1
    assert "1/2" in alerts_sent[0]
    assert "[FAIL] min_trades" in alerts_sent[0]
    assert "[PASS] min_period" in alerts_sent[0]


# ---------------------------------------------------------------------------
# validate_models_at_startup
# ---------------------------------------------------------------------------


def test_validate_models_returns_false_when_models_missing():
    with patch("sharpedge_trading.agents.prediction_agent._model_path") as mock_path:
        mock_path.return_value.exists.return_value = False
        result = validate_models_at_startup()
    assert result is False


def test_validate_models_returns_true_when_all_present():
    with patch("sharpedge_trading.agents.prediction_agent._model_path") as mock_path:
        mock_path.return_value.exists.return_value = True
        result = validate_models_at_startup()
    assert result is True
