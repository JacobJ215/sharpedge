"""Nightly retrain check: append new resolved markets, retrain any newly-ready categories.

Run via cron (e.g. nightly at 2am):
    0 2 * * * cd /path/to/sharpedge && python scripts/retrain_if_ready.py >> logs/retrain.log 2>&1

What it does:
1. Runs export_kalshi_training in append mode (adds rows since last export)
2. Checks if any previously-skipped category now has >= MIN_MARKETS rows
3. If so, retrains all categories and promotes new models
"""
import logging
import subprocess
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path("data/processed/prediction_markets")
MIN_MARKETS = 200


def _category_counts() -> dict[str, int]:
    counts = {}
    for f in DATA_DIR.glob("*.parquet"):
        try:
            counts[f.stem] = len(pd.read_parquet(f))
        except Exception:
            pass
    return counts


def main() -> None:
    before = _category_counts()
    skipped_before = {cat for cat, n in before.items() if n < MIN_MARKETS}

    logger.info("Running export (append mode)...")
    result = subprocess.run(
        [sys.executable, "scripts/export_kalshi_training.py"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        logger.error("Export failed: %s", result.stderr)
        sys.exit(1)
    logger.info("Export complete.")

    after = _category_counts()
    newly_ready = {cat for cat in skipped_before if after.get(cat, 0) >= MIN_MARKETS}

    if not newly_ready:
        logger.info("No new categories ready for training. Done.")
        return

    logger.info("New categories crossed %d rows: %s — retraining...", MIN_MARKETS, newly_ready)
    result = subprocess.run(
        [sys.executable, "-m", "scripts.train_pm_models"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        logger.error("Training failed: %s", result.stderr)
        sys.exit(1)
    logger.info("Retrain complete.\n%s", result.stdout)


if __name__ == "__main__":
    main()
