"""Download resolved Kalshi and Polymarket markets for PM resolution model training.

Backfills historical resolved prediction market data to parquet files used
by process_pm_historical.py and train_pm_models.py (plans 04-05).

Usage:
    python scripts/download_pm_historical.py [--out-dir PATH] [--offline]

Output:
    data/raw/prediction_markets/kalshi_resolved.parquet
    data/raw/prediction_markets/polymarket_resolved.parquet
"""

import argparse
import asyncio
import dataclasses
import json
import os
import sys
from pathlib import Path

import httpx
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from sharpedge_feeds.kalshi_client import KalshiClient, KalshiConfig
from sharpedge_feeds.polymarket_client import PolymarketClient, PolymarketConfig

FIXTURE_DIR = Path(__file__).parent.parent / "data/raw/prediction_markets/fixtures"
DEFAULT_OUT = Path(__file__).parent.parent / "data/raw/prediction_markets"

_KALSHI_KEY_ENV = "KALSHI_API_KEY"
_KALSHI_PRIV_ENV = "KALSHI_PRIVATE_KEY_PEM"
_KALSHI_PRIV_PATH_ENV = "KALSHI_PRIVATE_KEY_PATH"

# Network errors that warrant a retry
_NET_ERRORS = (
    httpx.ReadTimeout,
    httpx.ReadError,
    httpx.RemoteProtocolError,
    httpx.ConnectError,
    httpx.ConnectTimeout,
)

_MAX_RETRIES = 5              # attempts per page/batch
_POLY_CONCURRENCY = 5        # simultaneous Polymarket page fetches
_POLY_PAGE_BATCH = 20        # pages queued per round (concurrency gates to _POLY_CONCURRENCY)
_UPSERT_BATCH_SIZE = 200     # rows per Supabase upsert call (smaller = less timeout risk)
_UPSERT_MAX_RETRIES = 4      # retry attempts for Supabase upsert on timeout
_KALSHI_STREAM_EVERY = 1_000 # upsert to Supabase every N Kalshi markets collected
_KALSHI_CURSOR_FILE = Path(__file__).parent.parent / "data/raw/prediction_markets/.kalshi_cursor"


def _load_kalshi_private_key() -> str | None:
    """Load Kalshi private key from file path or inline PEM env var."""
    path = os.environ.get(_KALSHI_PRIV_PATH_ENV, "").strip()
    if path:
        return Path(path).read_text()
    pem = os.environ.get(_KALSHI_PRIV_ENV, "").strip()
    if pem:
        pem = pem.replace("\\n", "\n")
        if "END" not in pem:
            print(
                "WARNING: KALSHI_PRIVATE_KEY_PEM appears truncated.\n"
                "  Set KALSHI_PRIVATE_KEY_PATH=/path/to/kalshi.pem instead.",
                file=sys.stderr,
            )
            return None
        return pem
    return None


def _is_kalshi_offline(offline: bool) -> bool:
    return offline or not os.environ.get(_KALSHI_KEY_ENV, "").strip()


def _get_supabase_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if url and key:
        from supabase import create_client, ClientOptions
        return create_client(url, key, options=ClientOptions(postgrest_client_timeout=60))
    return None


def _dedup_rows(rows: list[dict]) -> list[dict]:
    seen: dict[tuple, dict] = {}
    for row in rows:
        seen[(row["market_id"], row["source"])] = row
    return list(seen.values())


def _batch_upsert(supabase, rows: list[dict]) -> None:
    import time as _time
    rows = _dedup_rows(rows)
    total = len(rows)
    for i in range(0, total, _UPSERT_BATCH_SIZE):
        batch = rows[i : i + _UPSERT_BATCH_SIZE]
        client = supabase  # may be replaced with a fresh client on retry
        for attempt in range(_UPSERT_MAX_RETRIES):
            try:
                client.table("resolved_pm_markets").upsert(
                    batch, on_conflict="market_id,source"
                ).execute()
                break
            except Exception as exc:
                if attempt == _UPSERT_MAX_RETRIES - 1:
                    raise
                wait = 5 * (2 ** attempt)
                print(f"\n  upsert error ({type(exc).__name__}), retry {attempt+1}/{_UPSERT_MAX_RETRIES} in {wait}s...")
                _time.sleep(wait)
                # Recreate client — broken HTTP/2 connections are not reusable
                fresh = _get_supabase_client()
                if fresh is not None:
                    client = fresh
        print(f"  upserted {min(i + _UPSERT_BATCH_SIZE, total)}/{total} rows", end="\r")
    print()


def _market_to_dict(market: object) -> dict:
    if dataclasses.is_dataclass(market) and not isinstance(market, type):
        return dataclasses.asdict(market)
    fields = [
        "ticker", "event_ticker", "title", "yes_bid", "yes_ask",
        "volume", "open_interest", "last_price", "close_time", "result",
    ]
    return {f: getattr(market, f, None) for f in fields}


def _detect_category(market: object) -> str:
    event_ticker = str(getattr(market, "event_ticker", "") or "")
    prefix = event_ticker[:4].upper()
    mapping = {"KXPO": "politics", "KXFE": "economics", "KXBT": "crypto",
               "KXEN": "entertainment", "KXWT": "weather"}
    for k, v in mapping.items():
        if prefix.startswith(k):
            return v
    return "general"


def _dt_to_iso(value) -> str | None:
    """Convert datetime to ISO 8601 string for JSON serialization."""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _build_kalshi_row(market: object) -> dict:
    yes_bid = getattr(market, "yes_bid", None) or 0
    yes_ask = getattr(market, "yes_ask", None) or 0
    return {
        "market_id": getattr(market, "ticker", None),
        "source": "kalshi",
        "title": getattr(market, "title", None),
        "category": _detect_category(market),
        "market_prob": (yes_bid + yes_ask) / 2,
        "bid_ask_spread": yes_ask - yes_bid,
        "last_price": getattr(market, "last_price", None),
        "volume": getattr(market, "volume", None),
        "open_interest": getattr(market, "open_interest", None),
        "days_to_close": None,
        "resolved_yes": 1 if str(getattr(market, "result", None) or "no").lower() == "yes" else 0,
        "resolved_at": _dt_to_iso(getattr(market, "close_time", None)),
    }


def _build_polymarket_row(market: object, resolved_yes: int) -> dict:
    return {
        "market_id": getattr(market, "condition_id", None),
        "source": "polymarket",
        "title": getattr(market, "question", None),
        "category": getattr(market, "category", "general"),
        "market_prob": None,
        "bid_ask_spread": None,
        "last_price": None,
        "volume": getattr(market, "volume", None),
        "open_interest": getattr(market, "liquidity", None),
        "days_to_close": None,
        "resolved_yes": resolved_yes,
        "resolved_at": _dt_to_iso(getattr(market, "end_date", None)),
    }


async def _retry_get(coro_fn, label: str):
    """Call coro_fn() with exponential backoff on network errors and 5xx responses."""
    for attempt in range(_MAX_RETRIES):
        try:
            return await coro_fn()
        except _NET_ERRORS as exc:
            if attempt == _MAX_RETRIES - 1:
                raise
            wait = min(5 * (2 ** attempt), 60)  # 5 10 20 40 60
            print(f"\n{type(exc).__name__} on {label}, retry {attempt + 1}/{_MAX_RETRIES} in {wait}s...")
            await asyncio.sleep(wait)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code < 500:
                raise  # 4xx errors are caller bugs — don't retry
            if attempt == _MAX_RETRIES - 1:
                raise
            wait = min(5 * (2 ** attempt), 60)
            print(f"\n{exc.response.status_code} on {label}, retry {attempt + 1}/{_MAX_RETRIES} in {wait}s...")
            await asyncio.sleep(wait)


async def backfill_kalshi_resolved(
    out_dir: Path = DEFAULT_OUT,
    offline: bool = False,
    max_pages: int | None = None,
) -> pd.DataFrame:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if _is_kalshi_offline(offline):
        fixture_path = FIXTURE_DIR / "kalshi_sample.json"
        rows = json.loads(fixture_path.read_text())
        df = pd.DataFrame(rows)
        df.to_parquet(out_dir / "kalshi_resolved.parquet", index=False)
        return df

    api_key = os.environ[_KALSHI_KEY_ENV]
    private_key_pem = _load_kalshi_private_key()
    config = KalshiConfig(api_key=api_key, private_key_pem=private_key_pem)
    client = KalshiClient(config=config)

    try:
        await _retry_get(
            lambda: client.get_markets(status="settled", limit=1),
            "Kalshi preflight",
        )
    except Exception as exc:
        sys.exit(
            f"ERROR: Kalshi preflight failed — {exc}\n"
            f"Set KALSHI_API_KEY and KALSHI_PRIVATE_KEY_PATH in your environment."
        )

    supabase = _get_supabase_client()
    all_markets = []
    pending: list = []          # markets buffered for next stream upsert
    seen_tickers: set[str] = set()
    page = 0

    # Resume from saved cursor if available
    cursor: str | None = None
    if _KALSHI_CURSOR_FILE.exists():
        saved = _KALSHI_CURSOR_FILE.read_text().strip()
        if saved:
            cursor = saved
            print(f"  Kalshi: resuming from saved cursor (page ~{saved[:12]}...)")

    while True:
        batch, next_cursor = await _retry_get(
            lambda c=cursor: client.get_markets_page(status="settled", limit=100, cursor=c),
            f"Kalshi page {page}",
        )
        if not batch:
            break
        new = [m for m in batch if m.ticker not in seen_tickers]
        seen_tickers.update(m.ticker for m in new)
        all_markets.extend(new)
        pending.extend(new)
        page += 1
        print(f"  Kalshi: {len(all_markets)} markets (page {page})...", end="\r")

        # Stream upsert + save cursor every _KALSHI_STREAM_EVERY markets
        if supabase is not None and len(pending) >= _KALSHI_STREAM_EVERY:
            _batch_upsert(supabase, [_build_kalshi_row(m) for m in pending])
            pending.clear()
            # Persist cursor so a crash here can resume from this point
            if next_cursor:
                _KALSHI_CURSOR_FILE.parent.mkdir(parents=True, exist_ok=True)
                _KALSHI_CURSOR_FILE.write_text(next_cursor)

        # Stop when API signals no more pages or page cap reached
        if next_cursor is None or len(batch) < 100:
            break
        if max_pages is not None and page >= max_pages:
            print(f"\n  Kalshi: page cap {max_pages} reached — stopping early.")
            break
        cursor = next_cursor

    # Flush remaining buffer
    if supabase is not None and pending:
        _batch_upsert(supabase, [_build_kalshi_row(m) for m in pending])
        pending.clear()

    # Clean up cursor file — download finished successfully
    if _KALSHI_CURSOR_FILE.exists():
        _KALSHI_CURSOR_FILE.unlink()

    print(f"  Kalshi: {len(all_markets)} markets collected.  ")

    df = pd.DataFrame([_market_to_dict(m) for m in all_markets]) if all_markets else pd.DataFrame(
        columns=["ticker", "event_ticker", "title", "yes_bid", "yes_ask",
                 "volume", "open_interest", "last_price", "close_time", "result"]
    )

    if supabase is None:
        df.to_parquet(out_dir / "kalshi_resolved.parquet", index=False)

    return df


async def backfill_polymarket_resolved(
    out_dir: Path = DEFAULT_OUT,
    offline: bool = False,
) -> pd.DataFrame:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if offline:
        df = _build_polymarket_fixture()
        df.to_parquet(out_dir / "polymarket_resolved.parquet", index=False)
        return df

    client = PolymarketClient(config=PolymarketConfig())
    supabase = _get_supabase_client()
    all_markets: list = []
    seen_ids: set[str] = set()
    pending: list = []
    offset = 0

    # Sequential fetching — Polymarket rate-limits concurrent requests with empty responses
    while True:
        batch = await _retry_get(
            lambda o=offset: client.get_markets(active=False, closed=True, limit=100, offset=o),
            f"Polymarket offset {offset}",
        )
        if not batch:
            break
        new = [m for m in batch if m.condition_id not in seen_ids]
        seen_ids.update(m.condition_id for m in new)
        all_markets.extend(new)
        pending.extend(new)
        print(f"  Polymarket: {len(all_markets)} markets (offset {offset})...", end="\r")

        # Stream upsert every 1000 markets
        if supabase is not None and len(pending) >= 1000:
            rows_pending = [_build_polymarket_row(m, _normalize_polymarket_outcome(m)) for m in pending]
            _batch_upsert(supabase, rows_pending)
            pending.clear()

        if len(batch) < 100:
            break
        offset += 100

    print(f"  Polymarket: {len(all_markets)} markets collected.  ")

    # Volume filter
    all_markets = [m for m in all_markets if getattr(m, "volume", 0) > 100]

    if not all_markets:
        df = pd.DataFrame(columns=[
            "condition_id", "question", "volume", "liquidity",
            "end_date", "category", "resolved_yes",
        ])
    else:
        rows = []
        for m in all_markets:
            resolved_yes = _normalize_polymarket_outcome(m)
            rows.append({
                "condition_id": m.condition_id,
                "question": m.question,
                "volume": m.volume,
                "liquidity": m.liquidity,
                "end_date": m.end_date,
                "category": m.category if hasattr(m, "category") else "general",
                "resolved_yes": resolved_yes,
            })
        df = pd.DataFrame(rows)

    # Flush remaining buffer
    if supabase is not None:
        if pending:
            rows_pending = [_build_polymarket_row(m, _normalize_polymarket_outcome(m)) for m in pending]
            _batch_upsert(supabase, rows_pending)
    else:
        df.to_parquet(out_dir / "polymarket_resolved.parquet", index=False)

    return df


def _normalize_polymarket_outcome(market: object) -> int:
    outcomes = getattr(market, "outcomes", [])
    winners = [o for o in outcomes if getattr(o, "winner", None) is True]
    if not winners:
        return 0
    if len(outcomes) == 2:
        return 1 if any(getattr(w, "outcome", "").lower() == "yes" for w in winners) else 0
    return 1 if any(getattr(w, "outcome", "").lower() != "no" for w in winners) else 0


def _build_polymarket_fixture() -> pd.DataFrame:
    categories = ["crypto", "politics", "sports", "entertainment", "economics"]
    rows = []
    for i in range(50):
        cat = categories[i % len(categories)]
        rows.append({
            "condition_id": f"0x{i:04x}{'ab' * 14}",
            "question": f"Synthetic {cat} market question #{i + 1}?",
            "volume": float(10000 + i * 2500),
            "liquidity": float(500 + i * 100),
            "end_date": f"2024-{(i % 12) + 1:02d}-15",
            "category": cat,
            "resolved_yes": i % 2,
        })
    return pd.DataFrame(rows)


async def _run(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    supabase_configured = bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_KEY"))
    dest = "Supabase" if supabase_configured else str(out_dir)

    # Sequential: finish Kalshi before starting Polymarket so they don't
    # compete for network and a Kalshi failure doesn't cancel Polymarket mid-run.
    if args.skip_kalshi:
        print("=== Kalshi === (skipped)")
    else:
        print("=== Kalshi ===")
        kalshi_df = await backfill_kalshi_resolved(out_dir=out_dir, offline=args.offline, max_pages=args.kalshi_max_pages)
        print(f"Kalshi: {len(kalshi_df)} rows → {dest}\n")

    print("=== Polymarket ===")
    poly_df = await backfill_polymarket_resolved(out_dir=out_dir, offline=args.offline)
    print(f"Polymarket: {len(poly_df)} rows → {dest}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download resolved Kalshi and Polymarket markets to parquet."
    )
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT),
        help="Output directory for parquet files (default: data/raw/prediction_markets/)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use fixture data instead of live API calls (auto-detected if KALSHI_API_KEY absent).",
    )
    parser.add_argument(
        "--kalshi-max-pages",
        type=int,
        default=None,
        metavar="N",
        help="Stop Kalshi after N pages (100 markets/page). Omit for full history.",
    )
    parser.add_argument(
        "--skip-kalshi",
        action="store_true",
        help="Skip Kalshi entirely and only fetch Polymarket.",
    )
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
