"""Abstract BaseExecutor interface for paper and live trading."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sharpedge_trading.events.types import ExecutionEvent


class BaseExecutor(ABC):
    """Abstract executor — implement for paper or live trading."""

    @abstractmethod
    async def execute(self, event: ExecutionEvent) -> str | None:
        """Execute a trade. Returns trade_id on success, None on failure.

        Must be idempotent: calling twice with the same event must not
        produce duplicate fills.
        """
