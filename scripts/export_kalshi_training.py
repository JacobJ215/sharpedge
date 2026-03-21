"""One-shot export: stream Kalshi training rows from Postgres directly to parquet.

Uses a server-side cursor (no REST API, no timeout) to stream rows in batches.

Usage:
    DATABASE_URL=postgresql://... python scripts/export_kalshi_training.py

DATABASE_URL: Supabase → Settings → Database → Connection string → Direct connection
"""
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("DATABASE_URL not set. Get it from Supabase → Settings → Database → Connection string.")

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    sys.exit("Run: pip install psycopg2-binary")

OUT_DIR = Path("data/processed/prediction_markets")
BATCH_SIZE = 5_000
MAX_PER_CATEGORY = 10_000
YEARS_BACK = 2

QUERY = f"""
    SELECT source, category, market_prob, bid_ask_spread, last_price,
           volume, open_interest, days_to_close, resolved_yes
    FROM resolved_pm_markets
    WHERE source = 'kalshi'
      AND category IS NOT NULL
      AND category != 'general'
      AND resolved_at > NOW() - INTERVAL '{YEARS_BACK} years'
    ORDER BY resolved_at DESC
"""

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    category_counts: dict[str, int] = {}

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False  # required for server-side cursor

    with conn.cursor(name="kalshi_stream", cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.itersize = BATCH_SIZE
        cur.execute(QUERY)

        total = 0
        while True:
            rows = cur.fetchmany(BATCH_SIZE)
            if not rows:
                break

            df = pd.DataFrame(rows)

            for category, cat_df in df.groupby("category"):
                already = category_counts.get(category, 0)
                if already >= MAX_PER_CATEGORY:
                    continue
                need = MAX_PER_CATEGORY - already
                cat_df = cat_df.head(need)

                out_path = OUT_DIR / f"{category}.parquet"
                if out_path.exists():
                    cat_df = pd.concat([pd.read_parquet(out_path), cat_df], ignore_index=True)
                cat_df.to_parquet(out_path, index=False)
                category_counts[category] = len(cat_df)

            total += len(rows)
            print(f"Streamed {total} rows | categories: {dict(category_counts)}", flush=True)

            if all(v >= MAX_PER_CATEGORY for v in category_counts.values()) and len(category_counts) > 3:
                print("All categories capped. Done early.")
                break

    conn.close()
    print(f"\nDone. {len(category_counts)} category parquets written to {OUT_DIR}/")
    for cat, count in sorted(category_counts.items()):
        print(f"  {cat}: {count} rows")

if __name__ == "__main__":
    main()
