"""Real-time prediction market arbitrage stream runner.

Connects Kalshi and Polymarket WebSocket feeds, auto-discovers matched
market pairs via Jaccard similarity, and logs every fee-adjusted arb
opportunity that exceeds the configured threshold.

Usage:
    uv run python scripts/run_arb_stream.py           # auto-discover pairs
    uv run python scripts/run_arb_stream.py --pairs   # use MANUAL_PAIRS below

Required environment variables:
    KALSHI_API_KEY          UUID from Kalshi dashboard
    KALSHI_PRIVATE_KEY_PATH Path to RSA private key PEM file
                            (OR set KALSHI_PRIVATE_KEY_PEM with the raw PEM string)

Optional environment variables:
    KALSHI_ENV              "prod" (default) or "demo"
    MIN_GAP_PCT             Minimum net profit % to alert (default: 2.0)
    BANKROLL                Total bankroll in USD for sizing (default: 10000)
    MAX_BET_PCT             Max fraction of bankroll per arb (default: 0.05)
    STALENESS_THRESHOLD_S   Stale tick cutoff in seconds (default: 5)
    ENABLE_POLY_EXECUTION   "true" to attempt live Poly orders (default: false)
    ENABLE_EXECUTION        "true" to shadow-execute arbs (default: false — log only)

Monitoring:
    All opportunities are logged at INFO level. Set LOG_LEVEL=DEBUG
    for verbose tick-level output.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

# ── Path setup ───────────────────────────────────────────────────────────────
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _pkg in ("data_feeds", "analytics"):
    _src = os.path.join(_root, "packages", _pkg, "src")
    if os.path.isdir(_src) and _src not in sys.path:
        sys.path.insert(0, _src)

from sharpedge_analytics.prediction_markets.realtime_scanner import (  # noqa: E402
    RealtimeArbScanner,
    LiveArbOpportunity,
    MarketPair,
    build_scanner_from_matched_markets,
    shadow_execute_arb,
)
from sharpedge_feeds.kalshi_client import KalshiClient, KalshiConfig  # noqa: E402
from sharpedge_feeds.kalshi_stream import KalshiStreamClient  # noqa: E402
from sharpedge_feeds.polymarket_client import PolymarketClient, PolymarketConfig  # noqa: E402
from sharpedge_feeds.polymarket_stream import PolymarketStreamClient  # noqa: E402
from sharpedge_feeds.polymarket_clob_orders import PolymarketCLOBOrderClient  # noqa: E402

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("sharpedge.arb_stream")

# ── Manual pairs (used with --pairs flag) ────────────────────────────────────
# Add known pairs here for time-sensitive events where you want the scanner
# running before auto-discovery can complete. Format:
#   (description, kalshi_ticker, polymarket_yes_token, polymarket_no_token_or_None)
MANUAL_PAIRS: list[tuple[str, str, str, str | None]] = [
    # Example (replace with real tickers/tokens):
    # ("Chiefs win Super Bowl", "KXNFL-26-KC", "0xabc123...", "0xdef456..."),
]


# ── Config from environment ──────────────────────────────────────────────────

def _load_kalshi_config() -> KalshiConfig:
    api_key = os.environ.get("KALSHI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "KALSHI_API_KEY is required. Set it to your Kalshi API key UUID."
        )

    pem: str | None = None
    pem_path = os.environ.get("KALSHI_PRIVATE_KEY_PATH", "")
    pem_str = os.environ.get("KALSHI_PRIVATE_KEY_PEM", "")
    if pem_path:
        with open(os.path.expanduser(pem_path)) as f:
            pem = f.read()
    elif pem_str:
        pem = pem_str
    else:
        logger.warning(
            "No KALSHI_PRIVATE_KEY_PATH or KALSHI_PRIVATE_KEY_PEM set — "
            "requests will be unsigned (public endpoints only)"
        )

    return KalshiConfig(
        api_key=api_key,
        private_key_pem=pem,
        environment=os.environ.get("KALSHI_ENV", "prod"),
    )


def _scanner_params() -> dict:
    return {
        "min_gap_pct": float(os.environ.get("MIN_GAP_PCT", "2.0")),
        "bankroll": float(os.environ.get("BANKROLL", "10000")),
        "max_bet_pct": float(os.environ.get("MAX_BET_PCT", "0.05")),
        "staleness_threshold_s": float(os.environ.get("STALENESS_THRESHOLD_S", "5")),
    }


# ── Opportunity handler ──────────────────────────────────────────────────────

def _log_opportunity(opp: LiveArbOpportunity) -> None:
    legs = opp.sizing.get("instructions", [])
    logger.info(
        "ARB DETECTED  %-40s  net=%.2f%%  gross=%.2f%%  stake=$%.0f  profit=$%.2f",
        opp.description[:40],
        opp.net_profit_pct,
        opp.gross_profit_pct,
        opp.sizing.get("total_stake", 0),
        opp.sizing.get("guaranteed_profit", 0),
    )
    for leg in legs:
        logger.info(
            "  └─ %-12s BUY %-3s @ %.4f  $%.0f  (%d contracts)",
            leg["platform"].upper(),
            leg["side"],
            leg["price"],
            leg["amount"],
            leg["contracts"],
        )


async def _write_arb_to_supabase(opp: LiveArbOpportunity) -> None:
    """Upsert detected arb opportunity to pm_arbitrage_opportunities via Supabase REST."""
    import httpx

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        return  # Supabase not configured — skip silently

    legs = opp.sizing.get("instructions", [])
    stake_yes = next((leg["amount"] for leg in legs if leg.get("side") == "YES"), None)
    stake_no = next((leg["amount"] for leg in legs if leg.get("side") == "NO"), None)

    payload = {
        "canonical_event_id": opp.canonical_id,
        "event_description": opp.description,
        "event_type": "prediction_market",
        "buy_yes_platform": opp.buy_yes_platform,
        "buy_yes_price": opp.buy_yes_price,
        "buy_no_platform": opp.buy_no_platform,
        "buy_no_price": opp.buy_no_price,
        "gross_gap_pct": opp.gross_profit_pct,
        "gross_profit_pct": opp.gross_profit_pct,
        "net_profit_pct": opp.net_profit_pct,
        "stake_yes": stake_yes,
        "stake_no": stake_no,
        "guaranteed_return": opp.sizing.get("guaranteed_profit"),
        "estimated_window_seconds": opp.estimated_window_seconds,
        "is_active": True,
        "expired_at": None,
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{url}/rest/v1/pm_arbitrage_opportunities",
                json=payload,
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Prefer": "resolution=merge-duplicates,return=minimal",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code not in (200, 201):
                logger.debug("Supabase write status %s for %s", resp.status_code, opp.canonical_id)
    except Exception as exc:
        logger.debug("Supabase write failed: %s", exc)


def make_arb_handler(
    kalshi_client: KalshiClient,
    poly_clob: PolymarketCLOBOrderClient,
    execute: bool,
):
    async def handle_arb(opp: LiveArbOpportunity) -> None:
        _log_opportunity(opp)
        await _write_arb_to_supabase(opp)
        if not execute:
            return
        try:
            result = await shadow_execute_arb(opp, kalshi_client, poly_clob)
            logger.info(
                "  └─ EXECUTED  ids=%s",
                [str(r) for r in result.get("order_ids", [])],
            )
        except Exception as exc:
            logger.error("  └─ EXECUTE ERROR: %s", exc)

    return handle_arb


# ── Main ─────────────────────────────────────────────────────────────────────

async def run(use_manual_pairs: bool = False) -> None:
    kalshi_cfg = _load_kalshi_config()
    params = _scanner_params()
    execute = os.environ.get("ENABLE_EXECUTION", "false").lower() == "true"

    logger.info(
        "Starting arb stream | env=%s  min_gap=%.1f%%  bankroll=$%.0f  "
        "staleness=%ss  execution=%s  poly_live=%s",
        kalshi_cfg.environment,
        params["min_gap_pct"],
        params["bankroll"],
        int(params["staleness_threshold_s"]),
        "ON" if execute else "OFF (log only)",
        os.environ.get("ENABLE_POLY_EXECUTION", "false"),
    )

    # HTTP clients (for market discovery)
    kalshi_http = KalshiClient(kalshi_cfg)
    poly_http = PolymarketClient(PolymarketConfig())

    # WebSocket stream clients
    kalshi_stream = KalshiStreamClient(kalshi_cfg)
    poly_stream = PolymarketStreamClient()

    # Order placement client (shadow by default)
    poly_clob = PolymarketCLOBOrderClient()

    # Build scanner
    scanner = RealtimeArbScanner(**params)
    scanner.on_arb(make_arb_handler(kalshi_http, poly_clob, execute))

    if use_manual_pairs:
        if not MANUAL_PAIRS:
            logger.error(
                "No MANUAL_PAIRS defined in run_arb_stream.py — "
                "edit the MANUAL_PAIRS list or run without --pairs to use auto-discovery"
            )
            return
        for i, (desc, k_ticker, p_yes, p_no) in enumerate(MANUAL_PAIRS):
            scanner.register_pair(MarketPair(
                canonical_id=f"manual_{i}_{k_ticker}",
                description=desc,
                kalshi_ticker=k_ticker,
                polymarket_yes_token=p_yes,
                polymarket_no_token=p_no,
            ))
        scanner.wire(kalshi_stream, poly_stream)
        logger.info("Manual mode: %d pairs registered", len(MANUAL_PAIRS))
    else:
        logger.info("Auto-discovering market pairs via Jaccard similarity...")
        n = await scanner.discover_and_wire(
            kalshi_http, poly_http, kalshi_stream, poly_stream
        )
        if n == 0:
            logger.warning(
                "No matched pairs found. Either no overlapping markets are open "
                "or similarity threshold is too high. "
                "Try --pairs with manually specified tickers."
            )

    logger.info("Streams starting. Press Ctrl+C to stop.")
    try:
        await asyncio.gather(
            kalshi_stream.run(),
            poly_stream.run(),
        )
    except asyncio.CancelledError:
        pass
    finally:
        await kalshi_stream.stop()
        await poly_stream.stop()
        logger.info("Streams stopped at %s", datetime.now(timezone.utc).strftime("%H:%M:%S UTC"))


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="SharpEdge real-time arb stream")
    parser.add_argument(
        "--pairs", action="store_true",
        help="Use MANUAL_PAIRS instead of auto-discovery"
    )
    args = parser.parse_args()

    try:
        asyncio.run(run(use_manual_pairs=args.pairs))
    except KeyboardInterrupt:
        pass
    except RuntimeError as exc:
        logger.error("Startup failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
