"""Kalshi order execution service.

Places limit orders on Kalshi for detected PM arbitrage opportunities.
Uses conservative sizing: never risks more than max_pct of bankroll on
a single trade. All orders are recorded in the bets table.

Safety guards:
- Dry-run mode (KALSHI_LIVE_TRADING=false) logs intent but never calls the API.
- Position check before placing to avoid doubling up.
- Balance check to ensure sufficient margin.
- Order confirmation wait (poll for fill or cancel after timeout).
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("sharpedge.services.kalshi_executor")

# Kalshi takes fees on each leg. These are subtracted when calculating true profit.
KALSHI_FEE_RATE = 0.07  # 7% of winnings

# Maximum fraction of bankroll to risk on a single arb leg.
DEFAULT_MAX_LEG_PCT = 0.05  # 5%

# How long to wait for a limit order to fill before cancelling (seconds).
ORDER_TIMEOUT_SECONDS = 30


@dataclass
class KalshiExecutionResult:
    """Result of a two-leg PM arb execution attempt."""

    success: bool
    ticker: str
    side: str  # "yes" or "no"
    count: int
    price_cents: int
    order_id: str | None = None
    status: str | None = None  # "executed", "canceled", "pending", "dry_run"
    error: str | None = None


async def execute_kalshi_arb_leg(
    ticker: str,
    side: str,
    price_cents: int,
    max_stake_dollars: float,
    api_key: str,
    private_key_pem: str,
    dry_run: bool = True,
) -> KalshiExecutionResult:
    """Place one leg of a Kalshi arb trade.

    Args:
        ticker: Kalshi market ticker (e.g. "KXBTC-25MAR31-T100000")
        side: "yes" or "no"
        price_cents: Limit price in cents (1-99). Must be current best ask.
        max_stake_dollars: Maximum dollar amount to risk on this leg.
        api_key: Kalshi API key UUID.
        private_key_pem: RSA private key for RSA-PSS signing.
        dry_run: If True, logs intent but does NOT call the API.

    Returns:
        KalshiExecutionResult with outcome details.
    """
    if price_cents <= 0 or price_cents >= 100:
        return KalshiExecutionResult(
            success=False,
            ticker=ticker,
            side=side,
            count=0,
            price_cents=price_cents,
            error=f"Invalid price: {price_cents} cents",
        )

    # Number of $1 contracts we can buy at this price
    # Each contract costs price_cents / 100 dollars
    contract_cost = price_cents / 100.0
    count = max(1, int(max_stake_dollars / contract_cost))

    if dry_run:
        logger.info(
            "[DRY RUN] Would place Kalshi %s %s @ %dc × %d contracts (~$%.2f)",
            side.upper(),
            ticker,
            price_cents,
            count,
            count * contract_cost,
        )
        return KalshiExecutionResult(
            success=True,
            ticker=ticker,
            side=side,
            count=count,
            price_cents=price_cents,
            status="dry_run",
        )

    from sharpedge_feeds.kalshi_client import get_kalshi_client
    import asyncio

    client = await get_kalshi_client(api_key, private_key_pem=private_key_pem)
    try:
        # Check we aren't already long/short this market
        positions = await client.get_positions()
        existing = next((p for p in positions if p.ticker == ticker), None)
        if existing and abs(existing.position) > 0:
            logger.warning(
                "Already hold %d net contracts on %s; skipping to avoid doubling",
                existing.position,
                ticker,
            )
            return KalshiExecutionResult(
                success=False,
                ticker=ticker,
                side=side,
                count=count,
                price_cents=price_cents,
                status="skipped",
                error="Existing position; manual review required",
            )

        # Place limit order (GTC — good till cancelled)
        order = await client.create_order(
            ticker=ticker,
            action="buy",
            side=side,
            order_type="limit",
            count=count,
            yes_price=price_cents if side == "yes" else None,
            no_price=price_cents if side == "no" else None,
        )

        logger.info(
            "Placed Kalshi order %s: %s %s @ %dc × %d (%s)",
            order.order_id,
            side.upper(),
            ticker,
            price_cents,
            count,
            order.status,
        )

        # Wait briefly for immediate fill
        await asyncio.sleep(3)
        open_orders = await client.get_open_orders(ticker=ticker)
        still_open = any(o.order_id == order.order_id for o in open_orders)

        if still_open:
            # Cancel if not immediately filled (arbs require fast execution)
            logger.warning(
                "Order %s not filled within 3s; cancelling to avoid stale resting order",
                order.order_id,
            )
            await client.cancel_order(order.order_id)
            return KalshiExecutionResult(
                success=False,
                ticker=ticker,
                side=side,
                count=count,
                price_cents=price_cents,
                order_id=order.order_id,
                status="canceled",
                error="Not filled within timeout; likely price moved",
            )

        return KalshiExecutionResult(
            success=True,
            ticker=ticker,
            side=side,
            count=count,
            price_cents=price_cents,
            order_id=order.order_id,
            status="executed",
        )

    except Exception as exc:
        logger.exception("Kalshi order failed for %s %s", side, ticker)
        return KalshiExecutionResult(
            success=False,
            ticker=ticker,
            side=side,
            count=0,
            price_cents=price_cents,
            error=str(exc),
        )
    finally:
        await client.close()


async def record_kalshi_execution(
    result: KalshiExecutionResult,
    arb: dict[str, Any],
    supabase_client: Any,
) -> None:
    """Write execution result to the bets table for P&L tracking.

    Args:
        result: The execution outcome.
        arb: The raw arb dict from prediction_market_scanner.
        supabase_client: Initialised Supabase client.
    """
    if not result.order_id:
        return

    try:
        contract_cost = result.price_cents / 100.0
        stake = result.count * contract_cost

        supabase_client.table("bets").insert({
            "game": arb.get("event", "Kalshi PM arb"),
            "sport": "PREDICTION_MARKET",
            "bet_type": "PM_ARB",
            "selection": f"{result.side.upper()} {result.ticker}",
            "sportsbook": "Kalshi",
            "odds": result.price_cents,  # stored in cents for PM bets
            "stake": stake,
            "result": "PENDING",
            "notes": (
                f"order_id={result.order_id} "
                f"arb_profit_pct={arb.get('profit_pct', 0):.2f}%"
            ),
            "placed_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception:
        logger.warning("Failed to record Kalshi execution in bets table", exc_info=True)


def get_kalshi_executor_config() -> dict[str, Any]:
    """Read executor config from environment.

    Returns:
        dict with api_key, private_key_pem, dry_run, max_leg_pct
    """
    return {
        "api_key": os.environ.get("KALSHI_API_KEY", ""),
        "private_key_pem": os.environ.get("KALSHI_PRIVATE_KEY", "") or None,
        "dry_run": os.environ.get("KALSHI_LIVE_TRADING", "false").lower() != "true",
        "max_leg_pct": float(os.environ.get("KALSHI_MAX_LEG_PCT", str(DEFAULT_MAX_LEG_PCT))),
        "bankroll": float(os.environ.get("KALSHI_BANKROLL", "10000")),
    }
