#!/usr/bin/env python3
"""Process raw Kalshi + Polymarket parquet into per-category feature DataFrames.

Category-specific add-on features (polling_average, etc.) are 0.0 in batch mode.
Live inference in PMResolutionPredictor uses injected API clients.
"""
import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

UNIVERSAL_FEATURE_COLS = [
    "market_prob", "bid_ask_spread", "last_price", "volume", "open_interest", "days_to_close",
]
MIN_CATEGORY_MARKETS = 200  # locked decision


def _ensure_assembler(assembler: Any = None) -> Any:
    if assembler is not None:
        return assembler
    from sharpedge_models.pm_feature_assembler import PMFeatureAssembler
    return PMFeatureAssembler()


def _build_feature_row(row: pd.Series, assembler: Any) -> dict:
    """Convert a parquet row into a feature dict using the assembler.

    Respects pre-existing 'category' column (Polymarket / test fixtures) before
    falling back to detect_category().
    """
    from sharpedge_models.pm_feature_assembler import PM_CATEGORY_EXTRA_FEATURES
    market = row.to_dict()
    features = assembler.assemble(market)
    category = str(market["category"]) if "category" in market and market["category"] else assembler.detect_category(market)
    out: dict = {col: float(features[i]) if i < len(features) else 0.0 for i, col in enumerate(UNIVERSAL_FEATURE_COLS)}
    for j, extra in enumerate(PM_CATEGORY_EXTRA_FEATURES.get(category, [])):
        idx = 6 + j
        out[extra] = float(features[idx]) if idx < len(features) else 0.0
    out["category"] = category
    return out


def _rows_to_df(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=UNIVERSAL_FEATURE_COLS + ["resolved_yes", "category", "source"])
    df = pd.DataFrame(rows)
    for col in UNIVERSAL_FEATURE_COLS:
        if col not in df.columns:
            df[col] = 0.0
    return df


def _resolved_yes_from_row(row: pd.Series) -> int:
    if "result" in row.index:
        return 1 if str(row.get("result", "no") or "no").strip().lower() == "yes" else 0
    if "resolved_yes" in row.index and row["resolved_yes"] is not None:
        return int(bool(row["resolved_yes"]))
    return 0


def _process_raw(raw_path: Path, assembler: Any, source: str) -> list[dict]:
    rows = []
    for _, row in pd.read_parquet(raw_path).iterrows():
        try:
            out_row = _build_feature_row(row, assembler)
            out_row["resolved_yes"] = _resolved_yes_from_row(row)
            out_row["source"] = source
            rows.append(out_row)
        except Exception as exc:
            logger.warning("%s: skipping row — %s", source, exc)
    return rows


MAX_ROWS_PER_CATEGORY = 10_000  # GBM on 6 features saturates well before this


def _write_categories(result_df: pd.DataFrame, out_dir: Path, append: bool = False) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for category, cat_df in result_df.groupby("category"):
        out_path = out_dir / f"{category}.parquet"
        if append and out_path.exists():
            existing = pd.read_parquet(out_path)
            if len(existing) >= MAX_ROWS_PER_CATEGORY:
                continue  # already have enough for this category
            cat_df = pd.concat([existing, cat_df], ignore_index=True)
        cat_df = cat_df.head(MAX_ROWS_PER_CATEGORY)
        cat_df.to_parquet(out_path, index=False)
        logger.info("wrote %d rows to %s", len(cat_df), out_path)


_CURSOR_FILE = Path("data/raw/prediction_markets/.supabase_cursor")


def _stream_supabase_to_parquets(out_dir: Path, assembler: Any, page_size: int = 500) -> int:
    """Stream resolved_pm_markets from Supabase in cursor-based pages, writing to parquets as we go.

    Uses id-based cursor pagination to avoid offset scans timing out on large tables.
    Saves cursor to disk after each page — re-running resumes from the last position.
    Returns total rows processed in this session.
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not (url and key):
        return 0

    # Load resume cursor if present
    last_id: str | None = None
    resuming = False
    if _CURSOR_FILE.exists():
        saved = _CURSOR_FILE.read_text().strip()
        if saved:
            last_id = saved
            resuming = True
            logger.info("Resuming from cursor: %s", last_id)

    try:
        import sharpedge_db.client as _db_client
        client = _db_client.get_supabase_client()
        total = 0
        out_dir.mkdir(parents=True, exist_ok=True)
        # Only fetch Kalshi rows — Polymarket lacks market_prob/bid_ask_spread/last_price (all null)
        # Only fetch last 2 years — older market dynamics don't generalise to current conditions
        # Only select columns the model actually uses — skip title, market_id, etc.
        from datetime import timezone
        import datetime as _dt
        cutoff = (_dt.datetime.now(timezone.utc) - _dt.timedelta(days=730)).isoformat()
        select_cols = "id,source,category,market_prob,bid_ask_spread,last_price,volume,open_interest,days_to_close,resolved_yes,resolved_at"

        while True:
            query = (
                client.table("resolved_pm_markets")
                .select(select_cols)
                .eq("source", "kalshi")
                .neq("category", "general")
                .gt("resolved_at", cutoff)
                .order("id")
                .limit(page_size)
            )
            if last_id is not None:
                query = query.gt("id", last_id)
            response = query.execute()
            batch = response.data or []
            if not batch:
                break
            rows = []
            for record in batch:
                try:
                    row = pd.Series(record)
                    out_row = _build_feature_row(row, assembler)
                    out_row["resolved_yes"] = _resolved_yes_from_row(row)
                    out_row["source"] = str(record.get("source", "unknown"))
                    rows.append(out_row)
                except Exception as exc:
                    logger.warning("supabase: skipping row id=%s — %s", record.get("id"), exc)
            if rows:
                chunk_df = _rows_to_df(rows)
                # Always append — parquets may already have data from a prior session
                _write_categories(chunk_df, out_dir, append=True)
            last_id = batch[-1]["id"]
            total += len(batch)
            _CURSOR_FILE.write_text(last_id)  # persist cursor after each page
            logger.info("Fetched %d rows (session total: %d, cursor: %s)", len(batch), total, last_id)
            if len(batch) < page_size:
                break

        # Done — clear cursor so next run starts fresh
        if _CURSOR_FILE.exists():
            _CURSOR_FILE.unlink()
        logger.info("Streaming complete. Cursor cleared.")
        return total
    except Exception as exc:
        logger.warning("Supabase streaming failed (cursor saved at %s): %s", last_id, exc)
        return total if 'total' in dir() else 0


def _get_resolved_pm_from_supabase() -> list[dict]:
    """Return all rows from resolved_pm_markets via Supabase SELECT, or [] if unavailable."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not (url and key):
        return []
    try:
        import sharpedge_db.client as _db_client
        client = _db_client.get_supabase_client()
        response = client.table("resolved_pm_markets").select("*").limit(1000).execute()
        return response.data or []
    except Exception as exc:
        logger.warning("Supabase query failed: %s", exc)
        return []


def _process_supabase_df(df: pd.DataFrame, out_dir: Path, assembler: Any) -> None:
    """Process a DataFrame sourced from Supabase resolved_pm_markets and write per-category parquets."""
    rows = []
    for _, row in df.iterrows():
        try:
            out_row = _build_feature_row(row, assembler)
            out_row["resolved_yes"] = _resolved_yes_from_row(row)
            out_row["source"] = str(row.get("source", "unknown"))
            rows.append(out_row)
        except Exception as exc:
            logger.warning("supabase: skipping row — %s", exc)
    if rows:
        result_df = _rows_to_df(rows)
        _write_categories(result_df, out_dir)


def process_kalshi(raw_path: Path, out_dir: Path | None = None, assembler: Any = None) -> pd.DataFrame:
    """Read kalshi_resolved.parquet → flat feature DataFrame. Optionally writes per-category parquets."""
    rows = _process_raw(Path(raw_path), _ensure_assembler(assembler), "kalshi")
    result_df = _rows_to_df(rows)
    if out_dir is not None and len(result_df) > 0:
        _write_categories(result_df, Path(out_dir), append=False)
    return result_df


def process_polymarket(raw_path: Path, out_dir: Path | None = None, assembler: Any = None) -> pd.DataFrame:
    """Read polymarket_resolved.parquet → flat feature DataFrame. Appends to existing per-category parquets."""
    rows = _process_raw(Path(raw_path), _ensure_assembler(assembler), "polymarket")
    result_df = _rows_to_df(rows)
    if out_dir is not None and len(result_df) > 0:
        _write_categories(result_df, Path(out_dir), append=True)
    return result_df


def process_and_report(raw_path: Path, report_path: Path) -> None:
    """Process raw parquet and write per-category skip report JSON."""
    rows = _process_raw(Path(raw_path), _ensure_assembler(), "kalshi")
    report: list[dict] = []
    if rows:
        for category, cat_df in pd.DataFrame(rows).groupby("category"):
            count = len(cat_df)
            entry: dict = {"category": str(category), "skipped": count < MIN_CATEGORY_MARKETS, "market_count": count}
            if count < MIN_CATEGORY_MARKETS:
                entry["reason"] = "insufficient_data"
            report.append(entry)
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(json.dumps(report, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Process raw Kalshi + Polymarket parquets for PM model training.")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/prediction_markets"))
    parser.add_argument("--out-dir", type=Path, default=Path("data/processed/prediction_markets"))
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    assembler = _ensure_assembler()

    if os.environ.get("SUPABASE_URL") and not args.offline:
        # Live mode: stream from Supabase in cursor-based pages to avoid timeout/OOM
        total = _stream_supabase_to_parquets(args.out_dir, assembler)
        if total:
            logger.info("Processed %d rows from Supabase resolved_pm_markets", total)
        else:
            logger.warning("No rows returned from Supabase resolved_pm_markets")
    else:
        # Fallback mode: read from parquet files
        kalshi_path = args.raw_dir / "kalshi_resolved.parquet"
        polymarket_path = args.raw_dir / "polymarket_resolved.parquet"
        if kalshi_path.exists():
            df = process_kalshi(kalshi_path, args.out_dir, assembler)
            logger.info("Processed Kalshi: %d rows", len(df))
        else:
            logger.warning("kalshi_resolved.parquet not found at %s", kalshi_path)
        if polymarket_path.exists():
            df = process_polymarket(polymarket_path, args.out_dir, assembler)
            logger.info("Processed Polymarket: %d rows", len(df))
        else:
            logger.warning("polymarket_resolved.parquet not found at %s", polymarket_path)


if __name__ == "__main__":
    main()
