"""Shared utilities for the trading swarm."""

from __future__ import annotations

import os


def get_bankroll() -> float:
    """Read current bankroll from environment."""
    trading_mode = os.environ.get("TRADING_MODE", "paper")
    if trading_mode == "paper":
        return float(os.environ.get("PAPER_BANKROLL", "10000"))
    return float(os.environ.get("LIVE_BANKROLL", "2000"))
