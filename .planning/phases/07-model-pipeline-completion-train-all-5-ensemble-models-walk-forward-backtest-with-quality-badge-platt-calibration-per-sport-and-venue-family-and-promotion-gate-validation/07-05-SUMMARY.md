---
plan: 05
phase: 07-model-pipeline-completion
status: complete
wave: 4
completed: 2026-03-14
requirements_satisfied: [CAL-01]
---

# Plan 07-05 Summary: Calibration Script

## What Was Built

- `scripts/run_calibration.py` (~250 lines) — Platt calibration orchestrator
  - `compute_ece(probs, outcomes, n_bins=10)` — Expected Calibration Error
  - Uses `TimeSeriesSplit(n_splits=5)` last fold as OOS proxy (no leakage)
  - Loads trained model or falls back to 0.5 baseline
  - Calls `CalibrationStore.update(sport, probs, outcomes)` with OOS data only
  - Calls `devig_shin_n_outcome` for sportsbook venue calibration stubs
  - Saves JSON report to `data/calibration_reports/{sport}_calibration.json`
  - `--plot` flag generates reliability diagram PNG

## Tests GREEN

- `test_calibration_store_updates_confidence_mult` — confidence_mult != 1.0 after >=50 games
- `test_compute_ece` — low ECE for well-calibrated predictions
- `test_oos_only_update` — mock verifies OOS subset passed, not full dataset

## Key Decisions

- OOS split: `TimeSeriesSplit(n_splits=5)` last fold (preserves temporal order)
- Venue calibration stubs: Kalshi/Polymarket note "no data available for this sport"
- Sportsbook uses `devig_shin_n_outcome([-110.0, -110.0])` as demonstration
- JSON report fields: brier_score, ece, confidence_mult, min_games_met, venue_calibration

## Artifacts

| File | Lines | Status |
|------|-------|--------|
| `scripts/run_calibration.py` | ~250 | ✅ Created |
