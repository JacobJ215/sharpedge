"""Smoke tests — verify the daemon initializes and runs one cycle without crashing.

These tests use real imports and component construction but mock external I/O.
They catch import errors, missing __init__ wiring, and startup crashes.
"""

import os
from unittest.mock import MagicMock, patch

import pytest


def test_daemon_imports_cleanly():
    """All daemon imports resolve without error."""
    import sharpedge_trading.daemon as daemon_module

    assert hasattr(daemon_module, "run_daemon")
    assert hasattr(daemon_module, "check_promotion_gate")
    assert hasattr(daemon_module, "StartupError")


def test_all_agent_modules_import():
    """All agent modules import cleanly (no missing dependencies at import time)."""
    modules = [
        "sharpedge_trading.agents.scan_agent",
        "sharpedge_trading.agents.research_agent",
        "sharpedge_trading.agents.prediction_agent",
        "sharpedge_trading.agents.portfolio_manager",
        "sharpedge_trading.agents.risk_agent",
        "sharpedge_trading.agents.monitor_agent",
        "sharpedge_trading.agents.post_mortem_agent",
    ]
    for mod in modules:
        __import__(mod)  # raises ImportError if broken


def test_executor_factory_returns_paper_executor_by_default():
    """get_executor() returns PaperExecutor when TRADING_MODE is not set."""
    os.environ.pop("TRADING_MODE", None)
    from sharpedge_trading.execution.executor_factory import get_executor
    from sharpedge_trading.execution.paper_executor import PaperExecutor

    executor = get_executor()
    assert isinstance(executor, PaperExecutor)


def test_executor_factory_returns_kalshi_executor_for_live():
    """get_executor() returns KalshiExecutor when TRADING_MODE=live."""
    os.environ["TRADING_MODE"] = "live"
    try:
        from sharpedge_trading.execution.executor_factory import get_executor
        from sharpedge_trading.execution.kalshi_executor import KalshiExecutor

        executor = get_executor()
        assert isinstance(executor, KalshiExecutor)
    finally:
        os.environ.pop("TRADING_MODE", None)


@pytest.mark.asyncio
async def test_scan_once_survives_kalshi_api_error():
    """scan_once() logs error and returns 0 if Kalshi API fails — does not raise."""
    from sharpedge_trading.agents.scan_agent import scan_once
    from sharpedge_trading.config import TradingConfig
    from sharpedge_trading.events.bus import EventBus

    bus = EventBus()
    config = TradingConfig.defaults()

    broken_client = MagicMock()
    broken_client.get_markets.side_effect = Exception("Connection refused")

    result = await scan_once(bus, config, broken_client)
    assert result == 0, "scan_once should return 0 on API failure, not raise"


@pytest.mark.asyncio
async def test_promotion_gate_fails_fast_without_supabase():
    """check_promotion_gate() returns a failed result when Supabase is unavailable."""
    from sharpedge_trading.daemon import check_promotion_gate

    with patch("sharpedge_trading.daemon._get_supabase_client", return_value=None):
        result = check_promotion_gate()
    assert not result.passed
    assert all(not ok for ok, _ in result.checks.values())


@pytest.mark.asyncio
async def test_run_daemon_raises_startup_error_for_live_mode_without_models():
    """run_daemon() raises StartupError in live mode when model files are missing."""
    from sharpedge_trading.daemon import StartupError, run_daemon

    os.environ["TRADING_MODE"] = "live"
    try:
        with patch("sharpedge_trading.daemon.validate_models_at_startup", return_value=False):
            with pytest.raises(StartupError, match="missing required model files"):
                await run_daemon()
    finally:
        os.environ.pop("TRADING_MODE", None)


@pytest.mark.asyncio
async def test_run_daemon_raises_startup_error_if_promotion_gate_fails():
    """run_daemon() raises StartupError in live mode when promotion gate fails."""
    from sharpedge_trading.daemon import PromotionGateResult, StartupError, run_daemon

    os.environ["TRADING_MODE"] = "live"
    failed_gate = PromotionGateResult(
        passed=False,
        checks={"min_trades": (False, "Only 5 trades")},
    )
    try:
        with patch("sharpedge_trading.daemon.validate_models_at_startup", return_value=True):
            with patch("sharpedge_trading.daemon.check_promotion_gate", return_value=failed_gate):
                with pytest.raises(StartupError, match="Promotion gate failed"):
                    await run_daemon()
    finally:
        os.environ.pop("TRADING_MODE", None)
