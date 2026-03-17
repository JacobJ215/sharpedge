"""Risk Agent — fractional Kelly sizing, circuit breakers, emit ExecutionEvent."""
from __future__ import annotations

import logging
import os

from sharpedge_trading.config import TradingConfig
from sharpedge_trading.events.bus import EventBus
from sharpedge_trading.events.types import ApprovedEvent, ExecutionEvent

logger = logging.getLogger(__name__)

_MIN_POSITION_PCT = 0.001   # 0.1% of bankroll minimum
_MAX_POSITION_PCT = 0.05    # 5% of bankroll maximum
_PRICE_FLOOR = 0.05
_PRICE_CEILING = 0.95


def _get_bankroll() -> float:
    trading_mode = os.environ.get("TRADING_MODE", "paper")
    if trading_mode == "paper":
        return float(os.environ.get("PAPER_BANKROLL", "10000"))
    return float(os.environ.get("LIVE_BANKROLL", "2000"))


def compute_kelly_size(
    calibrated_prob: float,
    kalshi_price: float,
    bankroll: float,
    kelly_fraction: float,
) -> float:
    """Compute fractional Kelly position size in dollars.

    Binary Kelly: f* = (p*b - q) / b
    where b = (1 - price) / price  (implied odds against YES)
    Fractional Kelly at `kelly_fraction` (e.g. 0.25).
    Clamped to [0.1%, 5%] of bankroll.
    Handles prices near 0 or 1 with floor/ceiling.
    """
    p = max(_PRICE_FLOOR, min(_PRICE_CEILING, calibrated_prob))
    q = 1.0 - p
    price = max(_PRICE_FLOOR, min(_PRICE_CEILING, kalshi_price))
    b = (1.0 - price) / price  # odds against (payout per dollar risked on YES)

    if b <= 0:
        return bankroll * _MIN_POSITION_PCT

    f_star = (p * b - q) / b
    f_fractional = kelly_fraction * f_star
    f_clamped = max(_MIN_POSITION_PCT, min(_MAX_POSITION_PCT, f_fractional))
    return round(f_clamped * bankroll, 2)


def _trading_mode() -> str:
    return os.environ.get("TRADING_MODE", "paper")


async def run_risk_agent(bus: EventBus, config: TradingConfig) -> None:
    """Main risk agent loop."""
    logger.info("Risk agent started")
    while True:
        event = await bus.get_approved()
        await process_approved(event, bus, config)


async def process_approved(
    event: ApprovedEvent,
    bus: EventBus,
    config: TradingConfig,
) -> bool:
    """Process an ApprovedEvent. Returns True if ExecutionEvent was emitted."""
    prediction = event.prediction
    calibrated_prob = prediction.calibrated_probability
    kalshi_price = prediction.research.opportunity.current_price
    bankroll = _get_bankroll()

    size = compute_kelly_size(calibrated_prob, kalshi_price, bankroll, config.kelly_fraction)

    # Determine direction
    direction: str = "yes" if calibrated_prob > kalshi_price else "no"

    execution = ExecutionEvent(
        market_id=event.market_id,
        direction=direction,
        size=size,
        entry_price=kalshi_price,
        trading_mode=_trading_mode(),
    )
    await bus.put_execution(execution)
    logger.info(
        "Execution: %s | direction=%s size=$%.2f entry=%.4f",
        event.market_id, direction, size, kalshi_price,
    )
    return True
