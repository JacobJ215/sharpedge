---
status: testing
phase: 07-model-pipeline-completion
source: [07-01-SUMMARY.md, 07-02-SUMMARY.md, 07-03-SUMMARY.md, 07-04-SUMMARY.md, 07-05-SUMMARY.md, 07-06-SUMMARY.md]
started: 2026-03-14T00:00:00Z
updated: 2026-03-14T00:00:00Z
---

## Current Test

number: 1
name: Full Test Suite is Green
expected: |
  Running `uv run pytest tests/unit/models/ tests/integration/ -q` completes
  with 0 failures. All 66 tests pass. No ERRORs.
awaiting: user response

## Tests

### 1. Full Test Suite is Green
expected: Running `uv run pytest tests/unit/models/ tests/integration/ -q` completes with 0 failures. All 66 tests pass.
result: [pending]

### 2. Walk-Forward Script Dry-Run
expected: Running `uv run python scripts/run_walk_forward.py --sport nba --dry-run` prints a row/feature count message and exits 0 (no crash). The script accepts --sport and --dry-run flags.
result: [pending]

### 3. Calibration Script Parses Correctly
expected: Running `python -c "import ast; ast.parse(open('scripts/run_calibration.py').read()); print('OK')"` prints "OK" without error. The script contains CalibrationStore, devig_shin_n_outcome, and compute_ece symbols.
result: [pending]

### 4. Promotion Gate Constants
expected: Running `python -c "import ast, re; src=open('scripts/generate_promotion_gate.py').read(); ast.parse(src); assert 'MAX_DRAWDOWN_THRESHOLD = 0.20' in src; assert 'BRIER_THRESHOLD = 0.22' in src; print('constants OK')"` prints "constants OK".
result: [pending]

### 5. Promotion Gate Evaluates 5 Gates
expected: When `evaluate_gates()` is called with a passing walk-forward report (badge="high", roi=0.03, max_drawdown=0.14) and calibration report (brier=0.21), it returns `overall_passed=True` with all 5 gate keys: calibration_brier_score, min_post_cost_edge, max_drawdown, walk_forward_badge, paper_stability_days.
result: [pending]

### 6. Train Models Supports 5 Sports
expected: `scripts/train_models.py` has a `SUPPORTED_SPORTS` constant containing all 5 sports: nfl, nba, ncaab, mlb, nhl. Running `grep "SUPPORTED_SPORTS" scripts/train_models.py` shows this constant exists.
result: [pending]

### 7. Download Script Has NCAAB Endpoint
expected: `scripts/download_historical_data.py` includes ncaab in its ESPN_ENDPOINTS. Running `grep -i ncaab scripts/download_historical_data.py` shows at least one match.
result: [pending]

### 8. Retrain Scheduler Import Fixed
expected: Running `grep "sharpedge_db.client" apps/webhook_server/src/sharpedge_webhooks/jobs/retrain_scheduler.py` finds the corrected import. Running `grep "sharpedge_feeds" apps/webhook_server/src/sharpedge_webhooks/jobs/retrain_scheduler.py` finds nothing.
result: [pending]

## Summary

total: 8
passed: 0
issues: 0
pending: 8
skipped: 0

## Gaps

[none yet]
