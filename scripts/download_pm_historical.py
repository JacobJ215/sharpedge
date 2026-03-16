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

import pandas as pd

from sharpedge_feeds.kalshi_client import KalshiClient, KalshiConfig
from sharpedge_feeds.polymarket_client import PolymarketClient, PolymarketConfig

FIXTURE_DIR = Path(__file__).parent.parent / "data/raw/prediction_markets/fixtures"
DEFAULT_OUT = Path(__file__).parent.parent / "data/raw/prediction_markets"

_KALSHI_KEY_ENV = "KALSHI_API_KEY"
_KALSHI_PRIV_ENV = "KALSHI_PRIVATE_KEY_PEM"


def _market_to_dict(market: object) -> dict:
    """Convert a market object (dataclass or mock) to a plain dict."""
    if dataclasses.is_dataclass(market) and not isinstance(market, type):
        return dataclasses.asdict(market)
    # Fallback for non-dataclass objects (e.g. MagicMock in tests)
    fields = [
        "ticker", "event_ticker", "title", "yes_bid", "yes_ask",
        "volume", "open_interest", "last_price", "close_time", "result",
    ]
    return {f: getattr(market, f, None) for f in fields}


def _is_kalshi_offline(offline: bool) -> bool:
    """Return True if KALSHI_API_KEY is absent or offline flag is set."""
    return offline or not os.environ.get(_KALSHI_KEY_ENV, "").strip()


_UPSERT_BATCH_SIZE = 500


def _get_supabase_client():
    """Return a Supabase client if SUPABASE_URL and SUPABASE_SERVICE_KEY are set, else None."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if url and key:
        from supabase import create_client
        return create_client(url, key)
    return None


def _batch_upsert(supabase, rows: list[dict]) -> None:
    """Upsert rows in batches to avoid connection timeouts on large datasets."""
    for i in range(0, len(rows), _UPSERT_BATCH_SIZE):
        batch = rows[i : i + _UPSERT_BATCH_SIZE]
        supabase.table("resolved_pm_markets").upsert(
            batch, on_conflict="market_id,source"
        ).execute()
        print(f"  upserted {min(i + _UPSERT_BATCH_SIZE, len(rows))}/{len(rows)} rows", end="\r")


def _detect_category(market: object) -> str:
    """Detect PM category from Kalshi event_ticker prefix."""
    event_ticker = str(getattr(market, "event_ticker", "") or "")
    prefix = event_ticker[:4].upper()
    mapping = {
        "KXPO": "politics",
        "KXFE": "economics",
        "KXBT": "crypto",
        "KXEN": "entertainment",
        "KXWT": "weather",
    }
    for k, v in mapping.items():
        if prefix.startswith(k[:4]):
            return v
    return "general"


def _build_kalshi_row(market: object) -> dict:
    """Build canonical resolved_pm_markets row from a Kalshi market object."""
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
        "resolved_at": getattr(market, "close_time", None),
    }


def _build_polymarket_row(market: object, resolved_yes: int) -> dict:
    """Build canonical resolved_pm_markets row from a Polymarket market object."""
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
        "resolved_at": getattr(market, "end_date", None),
    }


async def backfill_kalshi_resolved(
    out_dir: Path = DEFAULT_OUT,
    offline: bool = False,
) -> pd.DataFrame:
    """Fetch resolved Kalshi markets and save to parquet.

    Args:
        out_dir: Directory where kalshi_resolved.parquet will be written.
        offline: If True (or KALSHI_API_KEY absent), load fixture data instead.

    Returns:
        DataFrame with columns matching KalshiMarket fields.
        Saves to out_dir/kalshi_resolved.parquet.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if _is_kalshi_offline(offline):
        fixture_path = FIXTURE_DIR / "kalshi_sample.json"
        rows = json.loads(fixture_path.read_text())
        df = pd.DataFrame(rows)
        out_path = out_dir / "kalshi_resolved.parquet"
        df.to_parquet(out_path, index=False)
    else:
        api_key = os.environ[_KALSHI_KEY_ENV]
        private_key_pem = os.environ.get(_KALSHI_PRIV_ENV)
        config = KalshiConfig(api_key=api_key, private_key_pem=private_key_pem)
        client = KalshiClient(config=config)

        # Preflight: fail fast if Kalshi auth is broken
        try:
            await client.get_markets(status="settled", limit=1)
        except Exception as exc:
            sys.exit(
                f"ERROR: Kalshi preflight failed — {exc}\n"
                f"Set KALSHI_API_KEY and KALSHI_PRIVATE_KEY_PEM in your environment."
            )

        all_markets = []
        cursor: str | None = None
        while True:
            batch = await client.get_markets(
                status="settled", limit=100, cursor=cursor
            )
            if not batch:
                break
            all_markets.extend(batch)
            # KalshiClient returns empty list when no more pages
            if len(batch) < 100:
                break
            # Advance cursor from last market ticker for pagination
            cursor = batch[-1].ticker

        if not all_markets:
            df = pd.DataFrame(
                columns=[
                    "ticker", "event_ticker", "title", "yes_bid", "yes_ask",
                    "volume", "open_interest", "last_price", "close_time", "result",
                ]
            )
        else:
            df = pd.DataFrame([_market_to_dict(m) for m in all_markets])

        # Supabase upsert path (live mode)
        supabase = _get_supabase_client()
        if supabase is not None:
            rows_to_upsert = [_build_kalshi_row(m) for m in all_markets]
            _batch_upsert(supabase, rows_to_upsert)
        else:
            # Fallback: write parquet when no Supabase configured
            out_path = out_dir / "kalshi_resolved.parquet"
            df.to_parquet(out_path, index=False)

    return df


async def backfill_polymarket_resolved(
    out_dir: Path = DEFAULT_OUT,
    offline: bool = False,
) -> pd.DataFrame:
    """Fetch resolved Polymarket markets and save to parquet.

    Normalizes multi-outcome markets to a binary resolved_yes label:
    - 2 outcomes: resolved_yes = 1 if "Yes" outcome is winner
    - 3+ outcomes: resolved_yes = 1 if any non-"No" outcome is winner

    Args:
        out_dir: Directory where polymarket_resolved.parquet will be written.
        offline: If True, return synthetic 50-row fixture DataFrame.

    Returns:
        DataFrame with columns [condition_id, question, volume, liquidity,
        end_date, category, resolved_yes].
        Saves to out_dir/polymarket_resolved.parquet.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if offline:
        df = _build_polymarket_fixture()
        out_path = out_dir / "polymarket_resolved.parquet"
        df.to_parquet(out_path, index=False)
    else:
        client = PolymarketClient(config=PolymarketConfig())
        all_markets = []
        offset = 0
        while True:
            batch = await client.get_markets(
                active=False, closed=True, limit=100, offset=offset
            )
            if not batch:
                break
            all_markets.extend(batch)
            if len(batch) < 100:
                break
            offset += 100

        # Volume filter: exclude markets with volume <= 100
        all_markets = [m for m in all_markets if getattr(m, "volume", 0) > 100]

        if not all_markets:
            df = pd.DataFrame(
                columns=[
                    "condition_id", "question", "volume", "liquidity",
                    "end_date", "category", "resolved_yes",
                ]
            )
        else:
            rows = []
            for m in all_markets:
                resolved_yes = _normalize_polymarket_outcome(m)
                rows.append(
                    {
                        "condition_id": m.condition_id,
                        "question": m.question,
                        "volume": m.volume,
                        "liquidity": m.liquidity,
                        "end_date": m.end_date,
                        "category": m.category if hasattr(m, "category") else "general",
                        "resolved_yes": resolved_yes,
                    }
                )
            df = pd.DataFrame(rows)

        # Supabase upsert path (live mode)
        supabase = _get_supabase_client()
        if supabase is not None:
            rows_to_upsert = [
                _build_polymarket_row(m, _normalize_polymarket_outcome(m))
                for m in all_markets
            ]
            _batch_upsert(supabase, rows_to_upsert)
        else:
            # Fallback: write parquet when no Supabase configured
            out_path = out_dir / "polymarket_resolved.parquet"
            df.to_parquet(out_path, index=False)

    return df


def _normalize_polymarket_outcome(market: object) -> int:
    """Normalize market outcomes to binary 0/1 resolved_yes label.

    Args:
        market: PolymarketMarket with .outcomes list.

    Returns:
        1 if resolved YES, 0 if resolved NO, 0 if indeterminate.
    """
    outcomes = getattr(market, "outcomes", [])
    winners = [o for o in outcomes if getattr(o, "winner", None) is True]
    if not winners:
        return 0
    if len(outcomes) == 2:
        return 1 if any(getattr(w, "outcome", "").lower() == "yes" for w in winners) else 0
    # 3+ outcomes: any non-"No" winner counts as resolved_yes
    return 1 if any(getattr(w, "outcome", "").lower() != "no" for w in winners) else 0


def _build_polymarket_fixture() -> pd.DataFrame:
    """Build synthetic 50-row Polymarket fixture for offline/test mode."""
    categories = ["crypto", "politics", "sports", "entertainment", "economics"]
    rows = []
    for i in range(50):
        cat = categories[i % len(categories)]
        resolved = i % 2  # alternating 0/1 for balanced labels
        rows.append(
            {
                "condition_id": f"0x{i:04x}{'ab' * 14}",
                "question": f"Synthetic {cat} market question #{i + 1}?",
                "volume": float(10000 + i * 2500),
                "liquidity": float(500 + i * 100),
                "end_date": f"2024-{(i % 12) + 1:02d}-15",
                "category": cat,
                "resolved_yes": resolved,
            }
        )
    return pd.DataFrame(rows)


async def _run(args: argparse.Namespace) -> None:
    """Run both backfill tasks concurrently."""
    out_dir = Path(args.out_dir)
    kalshi_df, poly_df = await asyncio.gather(
        backfill_kalshi_resolved(out_dir=out_dir, offline=args.offline),
        backfill_polymarket_resolved(out_dir=out_dir, offline=args.offline),
    )
    print(f"Kalshi: {len(kalshi_df)} rows → {out_dir}/kalshi_resolved.parquet")
    print(f"Polymarket: {len(poly_df)} rows → {out_dir}/polymarket_resolved.parquet")


def main() -> None:
    """Entry point for CLI usage."""
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
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
