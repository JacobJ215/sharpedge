"""Portfolio Manager — cross-market exposure checks before approving trades."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from sharpedge_trading.config import TradingConfig
from sharpedge_trading.events.bus import EventBus
from sharpedge_trading.events.types import ApprovedEvent, PredictionEvent

logger = logging.getLogger(__name__)


@dataclass
class ExposureState:
    total_exposure: float = 0.0
    category_exposure: dict[str, float] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.category_exposure is None:
            self.category_exposure = {}


def _get_bankroll() -> float:
    """Read current bankroll from env (paper mode) or Supabase (live).

    Returns virtual $10,000 for paper mode. In live mode, reads from config.
    """
    trading_mode = os.environ.get("TRADING_MODE", "paper")
    if trading_mode == "paper":
        return float(os.environ.get("PAPER_BANKROLL", "10000"))
    return float(os.environ.get("LIVE_BANKROLL", "2000"))


def _fetch_exposure(supabase_url: str, supabase_key: str) -> ExposureState:
    """Fetch open positions from Supabase and compute current exposure."""
    try:
        from supabase import create_client  # type: ignore[import]

        client = create_client(supabase_url, supabase_key)
        response = client.table("open_positions").select("size,category,trading_mode").eq(
            "status", "open"
        ).execute()
        rows = response.data or []

        trading_mode = os.environ.get("TRADING_MODE", "paper")
        state = ExposureState()
        for row in rows:
            if row.get("trading_mode") != trading_mode:
                continue
            size = float(row.get("size", 0))
            cat = row.get("category", "unknown")
            state.total_exposure += size
            state.category_exposure[cat] = state.category_exposure.get(cat, 0.0) + size
        return state
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch exposure from Supabase: %s — assuming zero exposure", exc)
        return ExposureState()


def check_exposure(
    event: PredictionEvent,
    config: TradingConfig,
    bankroll: float,
    state: ExposureState,
) -> tuple[bool, str]:
    """Check portfolio exposure limits. Returns (approved, reason)."""
    category = event.research.opportunity.category

    # Estimate position size (conservative: 5% of bankroll max per market)
    estimated_size = bankroll * 0.05

    # Per-market cap
    if estimated_size / bankroll > config.max_category_exposure:
        return False, f"estimated size exceeds max_category_exposure ({config.max_category_exposure:.0%})"

    # Category cap
    cat_exposure = state.category_exposure.get(category, 0.0)
    if (cat_exposure + estimated_size) / bankroll > config.max_category_exposure:
        return False, (
            f"category {category} exposure would reach "
            f"{(cat_exposure + estimated_size) / bankroll:.1%} "
            f"(limit {config.max_category_exposure:.0%})"
        )

    # Total cap
    if (state.total_exposure + estimated_size) / bankroll > config.max_total_exposure:
        return False, (
            f"total exposure would reach "
            f"{(state.total_exposure + estimated_size) / bankroll:.1%} "
            f"(limit {config.max_total_exposure:.0%})"
        )

    return True, "approved"


async def run_portfolio_manager(bus: EventBus, config: TradingConfig) -> None:
    """Main portfolio manager loop."""
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    logger.info("Portfolio manager started")

    while True:
        event = await bus.get_prediction()
        bankroll = _get_bankroll()
        state = _fetch_exposure(supabase_url, supabase_key)

        approved, reason = check_exposure(event, config, bankroll, state)
        if not approved:
            logger.info("DROPPED %s: %s", event.market_id, reason)
            continue

        approved_event = ApprovedEvent(
            market_id=event.market_id,
            prediction=event,
        )
        await bus.put_approved(approved_event)
        logger.info("APPROVED %s", event.market_id)
