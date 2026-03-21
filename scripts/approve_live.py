#!/usr/bin/env python3
"""Manual review gate for live Kalshi execution (GATE-03).

Shows full capital gate status, blocks if GATE-01 or GATE-02 not met,
prompts operator for approval, writes data/live_approval.json.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sharpedge_venue_adapters.capital_gate import CapitalGate


def main() -> None:
    gate = CapitalGate.from_env()
    status = gate.check()

    # Print status table
    print("\n=== Capital Gate Status ===\n")
    for c in status.conditions:
        mark = "PASS" if c.passed else "FAIL"
        print(f"  [{mark}] {c.name}: {c.reason}")
    print()

    # Block if GATE-01 or GATE-02 not met
    gate01 = next((c for c in status.conditions if c.name == "GATE-01"), None)
    gate02 = next((c for c in status.conditions if c.name == "GATE-02"), None)
    if gate01 and not gate01.passed:
        print("ERROR: GATE-01 (model artifacts) must pass before approval.")
        sys.exit(1)
    if gate02 and not gate02.passed:
        print("ERROR: GATE-02 (paper-trading period) must pass before approval.")
        sys.exit(1)

    # Prompt operator
    name = input("Enter your name to approve live execution: ").strip()
    if not name:
        print("Aborted — no name provided.")
        sys.exit(1)

    # Build gate snapshot at approval time
    snapshot = {}
    for c in status.conditions:
        key = c.name.lower().replace("-", "_")
        snapshot[key] = c.passed

    approval = {
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "approved_by": name,
        "gate_snapshot": snapshot,
    }

    approval_path = Path(
        os.environ.get("CAPITAL_GATE_APPROVAL_PATH", "data/live_approval.json")
    )
    approval_path.parent.mkdir(parents=True, exist_ok=True)
    approval_path.write_text(json.dumps(approval, indent=2) + "\n")
    print(f"\nApproval written to {approval_path}")


if __name__ == "__main__":
    main()
