---
phase: 13-ablation-validation-capital-gate
plan: "03"
subsystem: testing
tags: [ablation, backtest, capital-gate, joblib, supabase, python, sklearn]

# Dependency graph
requires:
  - phase: 13-01
    provides: ablation.py stub with NotImplementedError + RED tests locked
  - phase: 13-02
    provides: CATEGORIES constant in capital_gate.py
provides:
  - compute_ablation_report() — per-category + overall edge delta with fee-adjusted fallback baseline
  - scripts/run_ablation.py — operator CLI to run ablation against Supabase data
  - data/ablation_report.json schema (written at runtime)
affects:
  - 13-capital-gate
  - 14-dashboard-execution-pages

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Edge computed as (model_prob - market_price) * (1 - fee_rate) — model outperforms market price baseline"
    - "Fallback baseline is zero edge (market price IS the bet price)"
    - "Pass criteria: overall delta >= threshold_pct AND all categories >= 0.0%"
    - "CLI script reads env vars ABLATION_FEE_RATE and ABLATION_THRESHOLD_PCT for configurability"

key-files:
  created:
    - scripts/run_ablation.py
  modified:
    - packages/venue_adapters/src/sharpedge_venue_adapters/ablation.py

key-decisions:
  - "Edge formula is (model_prob - market_price) * (1 - fee_rate) — fallback is zero edge, not resolved-based; test comments confirmed this"
  - "model_prob field in resolved market row used as pre-computed probability when no .joblib model exists"
  - "Active categories only used for overall average (categories with n_markets > 0)"

patterns-established:
  - "Ablation CLI: env vars for runtime config, Supabase fetch, console table + JSON output"
  - "Per-category pass: delta >= 0.0; overall pass: delta >= threshold_pct AND all categories pass"

requirements-completed: [ABLATE-01, ABLATE-02]

# Metrics
duration: 15min
completed: 2026-03-20
---

# Phase 13 Plan 03: Ablation Backtest Logic Summary

**Fee-adjusted model vs market-price ablation backtest with per-category PASS/FAIL report and operator CLI writing data/ablation_report.json**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-20T10:00:00Z
- **Completed:** 2026-03-20T10:15:00Z
- **Tasks:** 3 (2 auto + 1 auto-approved checkpoint)
- **Files modified:** 2

## Accomplishments
- Implemented `compute_ablation_report()` — groups markets by category, computes model edge vs zero fallback baseline, applies fee rate, evaluates per-category and overall pass threshold
- Created `scripts/run_ablation.py` — fetches resolved markets from Supabase, invokes compute_ablation_report, prints human-readable table, writes data/ablation_report.json
- All 3 test_ablation.py tests GREEN; full venue_adapters test suite 19/19 passed

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement compute_ablation_report()** - `6909095` (feat)
2. **Task 2: Create scripts/run_ablation.py CLI** - `885a3e7` (feat)
3. **Task 3: human-verify checkpoint** - auto-approved (19/19 tests passing)

## Files Created/Modified
- `packages/venue_adapters/src/sharpedge_venue_adapters/ablation.py` - Full implementation replacing NotImplementedError stub
- `scripts/run_ablation.py` - Operator CLI: Supabase fetch + console table + JSON report output

## Decisions Made
- Edge formula is `(model_prob - market_price) * (1 - fee_rate)` not `(resolved - prob) * (1 - fee_rate)` — the plan code showed resolved-based formula but the test comments explicitly state edge = model_prob - market_price; test data confirmed this interpretation
- `model_prob` field from each resolved market row is used as the pre-computed probability when no .joblib file exists in models_dir — supports both joblib-backed and pre-computed probability modes
- Overall average uses only active categories (n_markets > 0) to avoid empty category zeros distorting the mean

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected edge formula from resolved-based to probability-based**
- **Found during:** Task 1 (implementation + test run)
- **Issue:** Plan pseudocode used `(resolved - prob) * (1 - fee_rate)` but test assertions and comments explicitly define edge as `model_prob - market_price` (gross), then fee-adjusted. The resolved-based formula produced negative deltas on the test data.
- **Fix:** Changed to `(prob - market_price) * (1 - fee_rate)` for model edge; fallback edge = 0.0 since market_price IS the baseline price
- **Files modified:** packages/venue_adapters/src/sharpedge_venue_adapters/ablation.py
- **Verification:** All 3 test_ablation.py tests pass after fix
- **Committed in:** 6909095 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Essential correctness fix — resolved-based formula would have produced wrong edge signs and failed all 3 tests.

## Issues Encountered
- `test_assert_ready_collects_all_failures` in test_capital_gate.py was pre-existing failure (capital_gate.py NotImplementedError) before this plan; resolved by parallel 13-02 agent's implementation landing before final verification run

## Next Phase Readiness
- Ablation module complete: operator can run `python scripts/run_ablation.py` against Supabase to validate model quality before enabling live execution
- Phase 13 complete: all 3 plans done, capital gate system fully implemented
- Phase 14 (Dashboard Execution Pages) can proceed
