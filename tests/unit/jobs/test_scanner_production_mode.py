"""Scanner production mode tests: verify dry_run defaults correctly per KALSHI_LIVE_TRADING env var.

WIRE-03: 2 tests — both GREEN in CI (no external dependencies).

The Kalshi executor config controls dry_run via:
  dry_run = os.environ.get("KALSHI_LIVE_TRADING", "false").lower() != "true"

Default (no env var or any non-"true" value) -> dry_run=True (safe dev mode).
With KALSHI_LIVE_TRADING=true -> dry_run=False (production live trading enabled).
"""
from __future__ import annotations

import pytest
from sharpedge_bot.services.kalshi_executor import get_kalshi_executor_config


def test_scanner_dry_run_defaults_true_without_production_env(monkeypatch) -> None:
    """dry_run defaults to True when KALSHI_LIVE_TRADING is absent (safe dev default).

    Without the explicit live-trading flag, the scanner must never place real orders.
    """
    monkeypatch.delenv("KALSHI_LIVE_TRADING", raising=False)
    cfg = get_kalshi_executor_config()
    assert cfg["dry_run"] is True, (
        "Expected dry_run=True when KALSHI_LIVE_TRADING is not set (safe default in dev/CI)"
    )


def test_scanner_dry_run_false_in_production(monkeypatch) -> None:
    """dry_run is False when KALSHI_LIVE_TRADING=true (production mode).

    In production, live trading is enabled by explicitly setting this flag.
    """
    monkeypatch.setenv("KALSHI_LIVE_TRADING", "true")
    cfg = get_kalshi_executor_config()
    assert cfg["dry_run"] is False, (
        "Expected dry_run=False when KALSHI_LIVE_TRADING=true (production live trading)"
    )
