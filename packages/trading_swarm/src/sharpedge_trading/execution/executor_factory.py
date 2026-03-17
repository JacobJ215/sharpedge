"""Factory for selecting the correct executor based on TRADING_MODE."""
from __future__ import annotations

import os

from sharpedge_trading.execution.base_executor import BaseExecutor


def get_executor() -> BaseExecutor:
    """Return PaperExecutor or KalshiExecutor based on TRADING_MODE env var."""
    mode = os.environ.get("TRADING_MODE", "paper")
    if mode == "live":
        from sharpedge_trading.execution.kalshi_executor import KalshiExecutor
        return KalshiExecutor()
    from sharpedge_trading.execution.paper_executor import PaperExecutor
    return PaperExecutor()
