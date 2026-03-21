#!/usr/bin/env python3
"""Ablation backtest: model vs fee-adjusted fallback on historical resolved PM data.

Reads resolved markets from Supabase `resolved_pm_markets` table, loads
trained .joblib models, computes per-category and overall edge delta.
Writes data/ablation_report.json (machine-readable) and prints console table.

Usage:
    python scripts/run_ablation.py
    ABLATION_FEE_RATE=0.07 python scripts/run_ablation.py  # custom fee rate
    ABLATION_THRESHOLD_PCT=2.0 python scripts/run_ablation.py  # stricter threshold
"""
import json
import os
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sharpedge_venue_adapters.ablation import compute_ablation_report
from sharpedge_venue_adapters.capital_gate import CATEGORIES


def _fetch_resolved_markets() -> list[dict]:
    """Fetch resolved PM markets from Supabase."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY required.")
        sys.exit(1)
    from supabase import create_client
    client = create_client(url, key)
    result = client.table("resolved_pm_markets").select("*").execute()
    return result.data or []


def _print_table(report: dict) -> None:
    """Print human-readable console table (D-08, D-10)."""
    print("\n=== Ablation Report ===\n")
    print(f"  {'Category':<16} {'Model Edge':>12} {'Fallback Edge':>14} {'Delta':>10} {'N':>6} {'Result':>8}")
    print(f"  {'-'*16} {'-'*12} {'-'*14} {'-'*10} {'-'*6} {'-'*8}")
    for cat in CATEGORIES:
        c = report["categories"].get(cat, {})
        mark = "PASS" if c.get("passed", False) else "FAIL"
        print(
            f"  {cat:<16} {c.get('model_edge', 0):>11.4%} {c.get('fallback_edge', 0):>13.4%} "
            f"{c.get('delta', 0):>9.4%} {c.get('n_markets', 0):>6} {mark:>8}"
        )
    print(f"  {'-'*16} {'-'*12} {'-'*14} {'-'*10} {'-'*6} {'-'*8}")
    o = report["overall"]
    overall_mark = "PASS" if o.get("passed", False) else "FAIL"
    print(
        f"  {'OVERALL':<16} {o.get('model_edge', 0):>11.4%} {o.get('fallback_edge', 0):>13.4%} "
        f"{o.get('delta', 0):>9.4%} {'':>6} {overall_mark:>8}"
    )
    print(f"\n  Threshold: overall delta >= {report.get('threshold_pct', 1.5):.1f}%")
    final = "PASS" if report.get("passed", False) else "FAIL"
    print(f"  Final result: {final}\n")


def main() -> None:
    fee_rate = float(os.environ.get("ABLATION_FEE_RATE", "0.05"))
    threshold_pct = float(os.environ.get("ABLATION_THRESHOLD_PCT", "1.5"))
    models_dir = Path(os.environ.get("CAPITAL_GATE_MODELS_DIR", "data/models/pm"))

    print("Fetching resolved markets from Supabase...")
    markets = _fetch_resolved_markets()
    if not markets:
        print("ERROR: No resolved markets found in Supabase.")
        sys.exit(1)
    print(f"Found {len(markets)} resolved markets.")

    report = compute_ablation_report(
        resolved_markets=markets,
        models_dir=models_dir,
        fee_rate=fee_rate,
        threshold_pct=threshold_pct,
    )

    _print_table(report)

    # Write JSON report (D-08)
    output_path = Path("data/ablation_report.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Report written to {output_path}")


if __name__ == "__main__":
    main()
