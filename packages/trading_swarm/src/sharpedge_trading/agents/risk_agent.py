"""Risk Agent — fractional Kelly sizing, circuit breakers, emit ExecutionEvent."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sharpedge_trading.alerts.slack import send_alert
from sharpedge_trading.config import TradingConfig
from sharpedge_trading.events.bus import EventBus
from sharpedge_trading.events.types import ApprovedEvent, ExecutionEvent
from sharpedge_trading.utils import get_bankroll

logger = logging.getLogger(__name__)

_MIN_POSITION_PCT = 0.001   # 0.1% of bankroll minimum
_MAX_POSITION_PCT = 0.05    # 5% of bankroll maximum
_PRICE_FLOOR = 0.05
_PRICE_CEILING = 0.95


@dataclass
class CircuitBreakerState:
    consecutive_losses: int = 0
    daily_loss: float = 0.0
    daily_loss_reset_date: str = ""  # YYYY-MM-DD UTC
    paused_until: datetime | None = None

    def is_paused(self) -> bool:
        if self.paused_until is None:
            return False
        return datetime.now(tz=timezone.utc) < self.paused_until


# Module-level state (resets on daemon restart)
_breaker = CircuitBreakerState()


def check_circuit_breakers(config: TradingConfig) -> tuple[bool, str]:
    """Returns (ok, reason). If not ok, trading should pause."""
    now_date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    if _breaker.daily_loss_reset_date != now_date:
        _breaker.daily_loss = 0.0
        _breaker.daily_loss_reset_date = now_date

    if _breaker.is_paused():
        return False, f"circuit breaker active until {_breaker.paused_until}"

    bankroll = get_bankroll()
    if _breaker.daily_loss / bankroll > config.daily_loss_limit:
        _breaker.paused_until = datetime.now(tz=timezone.utc) + timedelta(hours=24)
        return False, f"daily loss {_breaker.daily_loss:.2f} exceeds {config.daily_loss_limit:.0%}"

    if _breaker.consecutive_losses >= 5:
        _breaker.paused_until = datetime.now(tz=timezone.utc) + timedelta(hours=4)
        send_alert(
            f"CIRCUIT BREAKER triggered — trading halted after "
            f"{_breaker.consecutive_losses} consecutive losses. "
            f"Pausing until {_breaker.paused_until.strftime('%Y-%m-%d %H:%M UTC')}."
        )
        return False, f"5 consecutive losses — pausing 4 hours"

    return True, "ok"


def record_loss(amount: float) -> None:
    """Call after a trade resolves as a loss."""
    _breaker.daily_loss += amount
    _breaker.consecutive_losses += 1
    logger.warning("Loss recorded: $%.2f | consecutive=%d | daily=%.2f",
                   amount, _breaker.consecutive_losses, _breaker.daily_loss)


def record_win() -> None:
    """Call after a trade resolves as a win."""
    _breaker.consecutive_losses = 0


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

    f_star = (p * b - q) / b
    if f_star <= 0:
        # Kelly says no edge in this direction — return minimum position
        return bankroll * _MIN_POSITION_PCT

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
    ok, reason = check_circuit_breakers(config)
    if not ok:
        logger.warning("Circuit breaker ACTIVE for %s: %s", event.market_id, reason)
        return False

    prediction = event.prediction
    calibrated_prob = prediction.calibrated_probability
    kalshi_price = prediction.research.opportunity.current_price
    bankroll = get_bankroll()

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
