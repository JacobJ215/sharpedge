"""Portfolio Manager — cross-market exposure checks before approving trades."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

from sharpedge_trading.config import TradingConfig
from sharpedge_trading.events.bus import EventBus
from sharpedge_trading.events.types import ApprovedEvent, PredictionEvent
from sharpedge_trading.utils import get_bankroll

logger = logging.getLogger(__name__)

_MAX_MARKET_EXPOSURE_PCT = 0.05  # 5% per individual market — module level constant


@dataclass
class ExposureState:
    total_exposure: float = 0.0
    category_exposure: dict[str, float] = field(default_factory=dict)
    correlated_series: list[str] = field(default_factory=list)  # series tickers of open positions


def _fetch_exposure(supabase_url: str, supabase_key: str) -> ExposureState:
    """Fetch open positions from Supabase and compute current exposure."""
    try:
        from supabase import create_client  # type: ignore[import]

        client = create_client(supabase_url, supabase_key)
        response = client.table("open_positions").select("size,category,trading_mode,ticker,market_id").eq(
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
            ticker = row.get("ticker", row.get("market_id", ""))
            if ticker:
                series = "-".join(ticker.split("-")[:2])
                if series not in state.correlated_series:
                    state.correlated_series.append(series)
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

    # Per-market cap: estimated size must not exceed 5% of bankroll
    if estimated_size / bankroll > _MAX_MARKET_EXPOSURE_PCT:
        return False, f"estimated size {estimated_size:.2f} exceeds 5% per-market limit"

    # Correlation flag: detect markets resolving on same underlying event (same series prefix)
    incoming_series = "-".join(event.research.opportunity.ticker.split("-")[:2]) if event.research.opportunity.ticker else ""
    if incoming_series and incoming_series in state.correlated_series:
        return False, f"correlated position already open in series {incoming_series}"

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


def _acquire_advisory_lock(supabase_url: str, supabase_key: str, lock_id: int = 1234567) -> bool:
    """Try to acquire a PostgreSQL advisory lock. Returns True if acquired."""
    if not supabase_url or not supabase_key:
        return True  # no Supabase, proceed without lock
    try:
        from supabase import create_client  # type: ignore[import]
        client = create_client(supabase_url, supabase_key)
        result = client.rpc("pg_try_advisory_lock", {"key": lock_id}).execute()
        return bool(result.data)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Advisory lock unavailable: %s — proceeding without lock", exc)
        return True  # fail open (don't block trading on lock failure)


def _release_advisory_lock(supabase_url: str, supabase_key: str, lock_id: int = 1234567) -> None:
    if not supabase_url or not supabase_key:
        return
    try:
        from supabase import create_client  # type: ignore[import]
        client = create_client(supabase_url, supabase_key)
        client.rpc("pg_advisory_unlock", {"key": lock_id}).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to release advisory lock: %s", exc)


async def run_portfolio_manager(bus: EventBus, config: TradingConfig) -> None:
    """Main portfolio manager loop."""
    import asyncio
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    logger.info("Portfolio manager started")

    while True:
        event = await bus.get_prediction()
        bankroll = get_bankroll()
        state = _fetch_exposure(supabase_url, supabase_key)

        # Try advisory lock with one retry
        lock_acquired = _acquire_advisory_lock(supabase_url, supabase_key)
        if not lock_acquired:
            await asyncio.sleep(2)  # 2s timeout
            lock_acquired = _acquire_advisory_lock(supabase_url, supabase_key)
            if not lock_acquired:
                logger.warning("Could not acquire advisory lock for %s — dropping", event.market_id)
                continue

        try:
            approved, reason = check_exposure(event, config, bankroll, state)
            if not approved:
                logger.info("DROPPED %s: %s", event.market_id, reason)
                continue
            approved_event = ApprovedEvent(market_id=event.market_id, prediction=event)
            await bus.put_approved(approved_event)
            logger.info("APPROVED %s", event.market_id)
        finally:
            _release_advisory_lock(supabase_url, supabase_key)
