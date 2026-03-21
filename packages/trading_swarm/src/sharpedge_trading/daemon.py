"""SharpEdge Trading Daemon — entry point, startup validation, promotion gate."""

from __future__ import annotations

import asyncio
import contextlib
import datetime
import logging
import os
import sys
from dataclasses import dataclass, field

import numpy as np

import sharpedge_trading.alerts.slack as _slack
from sharpedge_trading.agents.monitor_agent import run_monitor_agent
from sharpedge_trading.agents.portfolio_manager import run_portfolio_manager
from sharpedge_trading.agents.post_mortem_agent import run_post_mortem_agent
from sharpedge_trading.agents.prediction_agent import (
    run_prediction_agent,
    validate_models_at_startup,
)
from sharpedge_trading.agents.research_agent import run_research_agent
from sharpedge_trading.agents.risk_agent import run_risk_agent
from sharpedge_trading.agents.scan_agent import run_scan_agent
from sharpedge_trading.config import TradingConfig, load_config
from sharpedge_trading.events.bus import EventBus
from sharpedge_trading.execution.executor_factory import get_executor
from sharpedge_trading.utils import get_bankroll

logger = logging.getLogger(__name__)


class StartupError(RuntimeError):
    """Raised by run_daemon() when startup validation fails."""


# Gate check state — resets on daemon restart (acceptable per design spec)
_gate_announced: bool = False
_GATE_CHECK_INTERVAL: int = 86400  # 24 hours


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class PromotionGateResult:
    """Result of the paper → live promotion gate check."""

    passed: bool
    checks: dict[str, tuple[bool, str]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Kalshi client helpers
# ---------------------------------------------------------------------------


class _KalshiStub:
    """Stub Kalshi client for environments where the real client is unavailable."""

    def get_market(self, market_id: str) -> dict:
        return {}

    def get_markets(self) -> list:
        return []

    def create_order(self, **kwargs) -> dict:
        raise RuntimeError("KalshiStub cannot execute real orders")


def _build_kalshi_client():
    """Build Kalshi client from env vars. Returns a mock-able client object."""
    try:
        from sharpedge_feeds.kalshi_client import KalshiClient, KalshiConfig  # type: ignore[import]

        config = KalshiConfig(
            api_key=os.environ.get("KALSHI_API_KEY", ""),
            private_key_pem=os.environ.get("KALSHI_PRIVATE_KEY_PEM"),
        )
        return KalshiClient(config=config)
    except Exception as exc:
        logger.warning("Could not build KalshiClient: %s — using stub", exc)
        return _KalshiStub()


# ---------------------------------------------------------------------------
# Supabase helper
# ---------------------------------------------------------------------------


def _get_supabase_client():
    """Build and return a Supabase client, or None if unavailable."""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        return None
    try:
        from supabase import create_client  # type: ignore[import]

        return create_client(url, key)
    except Exception as exc:
        logger.warning("Failed to create Supabase client: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------


def _compute_max_drawdown(pnl_series: list[float], starting_bankroll: float = 10_000.0) -> float:
    """Return maximum drawdown in dollars over pnl_series."""
    equity = starting_bankroll
    peak = starting_bankroll
    max_dd = 0.0
    for pnl in pnl_series:
        equity += pnl
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
    return max_dd


def _compute_ece(confidence_scores: list[float], outcomes: list[bool], n_bins: int = 10) -> float:
    """Compute Expected Calibration Error (ECE)."""
    if not confidence_scores:
        return 1.0
    arr_conf = np.array(confidence_scores)
    arr_out = np.array(outcomes, dtype=float)
    total = len(arr_conf)
    ece = 0.0
    for i in range(n_bins):
        low = i / n_bins
        high = (i + 1) / n_bins
        mask = (arr_conf >= low) & (arr_conf < high)
        if i == n_bins - 1:
            mask = (arr_conf >= low) & (arr_conf <= high)
        count = int(mask.sum())
        if count == 0:
            continue
        avg_conf = float(arr_conf[mask].mean())
        avg_out = float(arr_out[mask].mean())
        ece += (count / total) * abs(avg_conf - avg_out)
    return ece


# ---------------------------------------------------------------------------
# Promotion gate
# ---------------------------------------------------------------------------


def check_promotion_gate(client=None) -> PromotionGateResult:
    """Check all paper→live promotion gate criteria against Supabase paper_trades.

    Args:
        client: Optional pre-built Supabase client (used for testing).

    Returns:
        PromotionGateResult with per-check results and overall pass/fail.
    """

    def _fail_all(reason: str = "Supabase unavailable") -> PromotionGateResult:
        checks = {
            name: (False, reason)
            for name in (
                "min_period",
                "min_trades",
                "min_trade_spread",
                "positive_ev",
                "sharpe_ratio",
                "win_rate",
                "max_drawdown",
                "ece_calibration",
            )
        }
        return PromotionGateResult(passed=False, checks=checks)

    if client is None:
        client = _get_supabase_client()

    if client is None:
        return _fail_all()

    try:
        response = (
            client.table("paper_trades")
            .select("pnl,actual_outcome,confidence_score,opened_at,resolved_at")
            .eq("trading_mode", "paper")
            .not_.is_("resolved_at", "null")
            .execute()
        )
        trades = response.data or []
    except Exception as exc:
        logger.warning("Supabase query failed: %s", exc)
        return _fail_all()

    checks: dict[str, tuple[bool, str]] = {}

    if not trades:
        return _fail_all("No resolved paper trades found")

    # Parse timestamps
    def _parse_ts(ts_str: str) -> datetime.datetime:
        # Handle ISO strings with or without timezone
        try:
            return datetime.datetime.fromisoformat(ts_str)
        except ValueError:
            # Strip trailing Z and parse
            return datetime.datetime.fromisoformat(ts_str.rstrip("Z"))

    resolved_ats = []
    for t in trades:
        with contextlib.suppress(Exception):
            resolved_ats.append(_parse_ts(t["resolved_at"]))

    if not resolved_ats:
        return _fail_all()

    first_ts = min(resolved_ats)
    last_ts = max(resolved_ats)
    period_days = (last_ts - first_ts).total_seconds() / 86_400.0

    # 1. min_period: ≥ 30 days
    ok = period_days >= 30.0
    checks["min_period"] = (ok, f"period={period_days:.1f}d (need ≥30)")

    # 2. min_trades: ≥ 50 resolved
    n = len(trades)
    ok = n >= 50
    checks["min_trades"] = (ok, f"trades={n} (need ≥50)")

    # 3. min_trade_spread: ≥ 10 days between first and last
    ok = period_days >= 10.0
    checks["min_trade_spread"] = (ok, f"spread={period_days:.1f}d (need ≥10)")

    # Collect pnl
    pnl_list = [float(t["pnl"]) for t in trades]
    pnl_arr = np.array(pnl_list)

    # 4. positive_ev: mean(pnl) > 0
    mean_pnl = float(np.mean(pnl_arr))
    ok = mean_pnl > 0.0
    checks["positive_ev"] = (ok, f"mean_pnl={mean_pnl:.4f} (need >0)")

    # 5. sharpe_ratio: mean/std > 0.5
    std_pnl = float(np.std(pnl_arr))
    if std_pnl > 0.0:
        sharpe = mean_pnl / std_pnl
        ok = sharpe > 0.5
        checks["sharpe_ratio"] = (ok, f"sharpe={sharpe:.4f} (need >0.5)")
    else:
        checks["sharpe_ratio"] = (False, "std(pnl)=0 — cannot compute sharpe")

    # 6. win_rate: count(pnl > 0) / total > 0.45
    wins = int((pnl_arr > 0).sum())
    win_rate = wins / len(pnl_arr)
    ok = win_rate > 0.45
    checks["win_rate"] = (ok, f"win_rate={win_rate:.4f} (need >0.45)")

    # 7. max_drawdown: < $2,000 (20% of $10,000)
    max_dd = _compute_max_drawdown(pnl_list, starting_bankroll=10_000.0)
    ok = max_dd < 2_000.0
    checks["max_drawdown"] = (ok, f"max_dd=${max_dd:.2f} (need <$2000)")

    # 8. ece_calibration: ECE < 0.10
    conf_scores = [float(t.get("confidence_score", 0.5)) for t in trades]
    outcomes = [bool(t.get("actual_outcome", False)) for t in trades]
    ece = _compute_ece(conf_scores, outcomes)
    ok = ece < 0.10
    checks["ece_calibration"] = (ok, f"ece={ece:.4f} (need <0.10)")

    passed = all(ok for ok, _ in checks.values())
    return PromotionGateResult(passed=passed, checks=checks)


# ---------------------------------------------------------------------------
# Execution helper
# ---------------------------------------------------------------------------


async def _run_execution(bus: EventBus, executor) -> None:
    """Consume ExecutionEvents from the bus and execute them."""
    logger.info("Execution agent started")
    while True:
        event = await bus.get_execution()
        try:
            trade_id = await executor.execute(event)
            if trade_id:
                logger.info("Executed trade: %s", trade_id)
        except Exception as exc:
            logger.error("Execution failed: %s", exc)


# ---------------------------------------------------------------------------
# Gate check agent
# ---------------------------------------------------------------------------


async def _run_gate_check(config: TradingConfig) -> None:
    """Daily promotion gate check — alerts on first pass and daily status."""
    global _gate_announced
    logger.info("Gate check agent started")
    while True:
        result = check_promotion_gate()
        n_pass = sum(1 for ok, _ in result.checks.values() if ok)
        n_total = len(result.checks)
        lines = [
            f"  [{'PASS' if ok else 'FAIL'}] {name}: {reason}"
            for name, (ok, reason) in result.checks.items()
        ]
        detail = "\n".join(lines)

        if result.passed:
            if not _gate_announced:
                _slack.send_alert(
                    f"PROMOTION GATE PASSED \u2705 \u2014 SharpEdge is ready for live trading.\n{detail}"
                )
                _gate_announced = True
                logger.info("Promotion gate PASSED \u2014 Slack alert sent")
            else:
                logger.info("Gate check: PASSED (alert already sent this session)")
        else:
            _slack.send_alert(f"Daily gate check: {n_pass}/{n_total} checks passing.\n{detail}")
            logger.info("Gate check: %d/%d passing", n_pass, n_total)

        await asyncio.sleep(_GATE_CHECK_INTERVAL)


# ---------------------------------------------------------------------------
# Main daemon
# ---------------------------------------------------------------------------


async def run_daemon() -> None:
    """Main daemon entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("SharpEdge Trading Daemon starting")

    trading_mode = os.environ.get("TRADING_MODE", "paper")

    # Validate models at startup
    models_ok = validate_models_at_startup()
    if trading_mode == "live" and not models_ok:
        logger.error("Live mode refused: missing required model files")
        raise StartupError("Live mode refused: missing required model files")

    # Promotion gate for live mode
    if trading_mode == "live":
        result = check_promotion_gate()
        if not result.passed:
            logger.error("Promotion gate FAILED — cannot start in live mode")
            for name, (ok, reason) in result.checks.items():
                status = "PASS" if ok else "FAIL"
                logger.error("  [%s] %s: %s", status, name, reason)
            raise StartupError("Promotion gate failed — cannot start in live mode")
        logger.info("Promotion gate passed — starting live mode")

    # Load config
    config = load_config()
    logger.info("Config loaded: %s", config)

    # Get executor
    executor = get_executor()

    # Build Kalshi client
    kalshi_client = _build_kalshi_client()

    # Build LLM calibrator for prediction agent
    from sharpedge_trading.signals.llm_calibrator import LLMCalibrator

    calibrator = LLMCalibrator()

    # Wire event bus
    bus = EventBus()

    # Start all agents as concurrent tasks
    async with asyncio.TaskGroup() as tg:
        tg.create_task(run_scan_agent(bus, config, kalshi_client), name="scan")
        tg.create_task(run_research_agent(bus), name="research")
        tg.create_task(run_prediction_agent(bus, config, calibrator), name="prediction")
        tg.create_task(run_portfolio_manager(bus, config), name="portfolio")
        tg.create_task(run_risk_agent(bus, config), name="risk")
        tg.create_task(_run_execution(bus, executor), name="execution")
        tg.create_task(run_monitor_agent(bus, kalshi_client), name="monitor")
        tg.create_task(run_post_mortem_agent(bus, config, get_bankroll()), name="post_mortem")
        tg.create_task(_run_gate_check(config), name="gate_check")


def main() -> None:
    """CLI entry point."""
    try:
        asyncio.run(run_daemon())
    except StartupError:
        sys.exit(1)


if __name__ == "__main__":
    main()
