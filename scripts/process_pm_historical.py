#!/usr/bin/env python3
"""Process raw Kalshi + Polymarket parquet into per-category feature DataFrames.

Category-specific add-on features (polling_average, etc.) are 0.0 in batch mode.
Live inference in PMResolutionPredictor uses injected API clients.
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UNIVERSAL_FEATURE_COLS = [
    "market_prob",
    "bid_ask_spread",
    "last_price",
    "volume",
    "open_interest",
    "days_to_close",
]

MIN_CATEGORY_MARKETS = 200  # locked decision: skip below this threshold


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_assembler(assembler: Any = None) -> Any:
    """Return provided assembler or create a default offline assembler."""
    if assembler is not None:
        return assembler
    from sharpedge_models.pm_feature_assembler import PMFeatureAssembler
    return PMFeatureAssembler()


def _build_feature_row(row: pd.Series, assembler: Any) -> dict:
    """Convert a parquet row into a feature dict using the assembler.

    If the row already has a 'category' column, uses that directly.
    Otherwise detects category via assembler.detect_category().
    """
    market = row.to_dict()
    features = assembler.assemble(market)
    # Honour pre-existing category column (Polymarket / test fixtures)
    category = str(market["category"]) if "category" in market and market["category"] else assembler.detect_category(market)

    out: dict = {}
    for i, col in enumerate(UNIVERSAL_FEATURE_COLS):
        out[col] = float(features[i]) if i < len(features) else 0.0

    # Add-on features (indices 6-7) stored as named columns when present
    from sharpedge_models.pm_feature_assembler import PM_CATEGORY_EXTRA_FEATURES
    extra_names = PM_CATEGORY_EXTRA_FEATURES.get(category, [])
    for j, extra_col in enumerate(extra_names):
        idx = 6 + j
        out[extra_col] = float(features[idx]) if idx < len(features) else 0.0

    out["category"] = category
    return out


def _rows_to_dataframe(rows: list[dict]) -> pd.DataFrame:
    """Build flat DataFrame with all universal feature columns present."""
    if not rows:
        return pd.DataFrame(columns=UNIVERSAL_FEATURE_COLS + ["resolved_yes", "category", "source"])
    df = pd.DataFrame(rows)
    # Guarantee all universal columns exist even if assembler returned shorter vector
    for col in UNIVERSAL_FEATURE_COLS:
        if col not in df.columns:
            df[col] = 0.0
    return df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def process_kalshi(
    raw_path: Path,
    out_dir: Path | None = None,
    assembler: Any = None,
) -> pd.DataFrame:
    """Read kalshi_resolved.parquet and return a flat feature DataFrame.

    Optionally writes per-category parquets to out_dir when provided.

    Args:
        raw_path: Path to kalshi_resolved.parquet.
        out_dir: Directory for output {category}.parquet files. If None, no
            files are written (useful for testing).
        assembler: PMFeatureAssembler instance. If None, created in offline mode.

    Returns:
        pd.DataFrame with universal feature columns plus resolved_yes, category, source.
    """
    raw_path = Path(raw_path)
    assembler = _ensure_assembler(assembler)

    df = pd.read_parquet(raw_path)
    rows = []
    for _, row in df.iterrows():
        try:
            out_row = _build_feature_row(row, assembler)
            # resolved_yes: 1 if result == "yes", else 0
            result_val = str(row.get("result", "no") or "no").strip().lower()
            out_row["resolved_yes"] = 1 if result_val == "yes" else 0
            out_row["source"] = "kalshi"
            rows.append(out_row)
        except Exception as exc:
            logger.warning("process_kalshi: skipping row — %s", exc)

    result_df = _rows_to_dataframe(rows)

    if out_dir is not None and len(result_df) > 0:
        out_dir = Path(out_dir)
        for category, cat_df in result_df.groupby("category"):
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{category}.parquet"
            cat_df.to_parquet(out_path, index=False)
            logger.info("process_kalshi: wrote %d rows to %s", len(cat_df), out_path)

    return result_df


def process_polymarket(
    raw_path: Path,
    out_dir: Path | None = None,
    assembler: Any = None,
) -> pd.DataFrame:
    """Read polymarket_resolved.parquet and return a flat feature DataFrame.

    Polymarket data already has resolved_yes and category columns from plan 02.
    Uses 'category' column first; falls back to detect_category() on question text.
    Appends to existing {category}.parquet files when out_dir provided (mixes
    Kalshi and Polymarket data per category).

    Args:
        raw_path: Path to polymarket_resolved.parquet.
        out_dir: Directory for output {category}.parquet files. If None, no
            files are written (useful for testing).
        assembler: PMFeatureAssembler instance. If None, created in offline mode.

    Returns:
        pd.DataFrame with universal feature columns plus resolved_yes, category, source.
    """
    raw_path = Path(raw_path)
    assembler = _ensure_assembler(assembler)

    df = pd.read_parquet(raw_path)
    rows = []
    for _, row in df.iterrows():
        try:
            out_row = _build_feature_row(row, assembler)

            # resolved_yes may already be present in polymarket parquet
            if "resolved_yes" in row.index and row["resolved_yes"] is not None:
                raw_yes = row["resolved_yes"]
                if isinstance(raw_yes, bool):
                    out_row["resolved_yes"] = int(raw_yes)
                else:
                    out_row["resolved_yes"] = int(bool(raw_yes))
            else:
                out_row["resolved_yes"] = 0

            out_row["source"] = "polymarket"
            rows.append(out_row)
        except Exception as exc:
            logger.warning("process_polymarket: skipping row — %s", exc)

    result_df = _rows_to_dataframe(rows)

    if out_dir is not None and len(result_df) > 0:
        out_dir = Path(out_dir)
        for category, cat_df in result_df.groupby("category"):
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{category}.parquet"
            if out_path.exists():
                existing = pd.read_parquet(out_path)
                cat_df = pd.concat([existing, cat_df], ignore_index=True)
            cat_df.to_parquet(out_path, index=False)
            logger.info("process_polymarket: wrote %d rows to %s", len(cat_df), out_path)

    return result_df


def process_and_report(raw_path: Path, report_path: Path) -> None:
    """Process a raw parquet and write per-category skip report.

    Supports both Kalshi-format (with 'result' column) and pre-categorised
    data (with 'category' column). Writes report_path as a JSON list. Each
    entry has 'category', 'skipped', 'market_count', and 'reason' (when skipped).
    """
    raw_path = Path(raw_path)
    report_path = Path(report_path)
    assembler = _ensure_assembler()

    df = pd.read_parquet(raw_path)
    rows = []
    for _, row in df.iterrows():
        try:
            out_row = _build_feature_row(row, assembler)
            if "result" in row.index:
                result_val = str(row.get("result", "no") or "no").strip().lower()
                out_row["resolved_yes"] = 1 if result_val == "yes" else 0
            elif "resolved_yes" in row.index and row["resolved_yes"] is not None:
                raw_yes = row["resolved_yes"]
                out_row["resolved_yes"] = int(bool(raw_yes))
            else:
                out_row["resolved_yes"] = 0
            out_row["source"] = "kalshi"
            rows.append(out_row)
        except Exception as exc:
            logger.warning("process_and_report: skipping row — %s", exc)

    report: list[dict] = []
    if rows:
        result_df = pd.DataFrame(rows)
        for category, cat_df in result_df.groupby("category"):
            count = len(cat_df)
            if count < MIN_CATEGORY_MARKETS:
                report.append({
                    "category": str(category),
                    "skipped": True,
                    "reason": "insufficient_data",
                    "market_count": count,
                })
            else:
                report.append({
                    "category": str(category),
                    "skipped": False,
                    "market_count": count,
                })

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    logger.info("process_and_report: wrote report to %s", report_path)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Process raw PM parquets into per-category feature DataFrames."""
    parser = argparse.ArgumentParser(
        description="Process raw Kalshi + Polymarket parquets for PM model training."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw/prediction_markets"),
        help="Directory containing kalshi_resolved.parquet and polymarket_resolved.parquet",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/processed/prediction_markets"),
        help="Directory for per-category output parquets",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Run in offline mode (no API calls; add-on features default to 0.0)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    assembler = _ensure_assembler()

    kalshi_path = args.raw_dir / "kalshi_resolved.parquet"
    polymarket_path = args.raw_dir / "polymarket_resolved.parquet"

    if kalshi_path.exists():
        kalshi_df = process_kalshi(kalshi_path, args.out_dir, assembler)
        logger.info("Processed Kalshi: %d rows", len(kalshi_df))
    else:
        logger.warning("kalshi_resolved.parquet not found at %s", kalshi_path)

    if polymarket_path.exists():
        poly_df = process_polymarket(polymarket_path, args.out_dir, assembler)
        logger.info("Processed Polymarket: %d rows", len(poly_df))
    else:
        logger.warning("polymarket_resolved.parquet not found at %s", polymarket_path)


if __name__ == "__main__":
    main()
