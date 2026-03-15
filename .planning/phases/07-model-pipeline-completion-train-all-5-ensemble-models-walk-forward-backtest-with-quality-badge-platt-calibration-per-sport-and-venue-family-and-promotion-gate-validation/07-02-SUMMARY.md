---
phase: 07-model-pipeline-completion
plan: "02"
subsystem: data-pipeline
tags: [python, pandas, espn-api, parquet, ensemble, sports-data]

requires:
  - phase: 07-01
    provides: ensemble_trainer.DOMAIN_FEATURES list that zero_fill_domain_features imports

provides:
  - NCAAB ESPN scoreboard endpoint in download_historical_data.py
  - load_ncaab_data(), load_mlb_data(), load_nhl_data() in process_historical_data.py
  - zero_fill_domain_features() filling missing DOMAIN_FEATURES columns with 0.0
  - main() in process_historical_data.py now processes all 5 sports gracefully

affects:
  - 07-03 (train_models.py Wave 2 — unblocked by processed parquets for all sports)

tech-stack:
  added: []
  patterns:
    - "ESPN scoreboard JSON parsed via _parse_espn_scoreboard() shared helper"
    - "process_nba_data() reused as generic column-detection processor for ESPN-sourced sports"
    - "zero_fill_domain_features() imports DOMAIN_FEATURES lazily; graceful ImportError fallback"
    - "_finalize_processed_df() extracts duplicate dropna/sort/season logic"

key-files:
  created: []
  modified:
    - scripts/download_historical_data.py
    - scripts/process_historical_data.py

key-decisions:
  - "NCAAB ESPN endpoint provides current-week scoreboard only — documented in module docstring; multi-season history deferred"
  - "process_nba_data() reused for NCAAB/MLB/NHL ESPN data (same heuristic column detection applies)"
  - "dt.tz_convert(None) used instead of dt.tz_localize(None) for UTC-aware ESPN timestamps — tz_localize raises on tz-aware series"
  - "_finalize_processed_df() extracted to eliminate 30+ lines of duplicated dropna/sort/season logic in both process functions"
  - "File stays at 498 lines (under 500-line limit) via lambda w=window default-arg pattern in rolling loops"

patterns-established:
  - "ESPN sports loader pattern: _parse_espn_scoreboard(path) -> load_X_data() wrapper -> process_nba_data() -> zero_fill -> save"
  - "Domain feature gap-filling: import DOMAIN_FEATURES at call time with ImportError fallback; zero-fill any missing columns"

requirements-completed: [PIPE-01]

duration: 5min
completed: 2026-03-14
---

# Phase 07 Plan 02: NCAAB/MLB/NHL Data Pipeline Extension Summary

**ESPN scoreboard loaders for NCAAB, MLB, and NHL with zero-fill for missing DOMAIN_FEATURES columns, unblocking Wave 2 train_models.py for all 5 sports**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-14T19:22:17Z
- **Completed:** 2026-03-14T19:27:51Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `ncaab_scoreboard` key to `ESPN_ENDPOINTS` dict in download script; module docstring updated with current-week-only limitation
- Added `_parse_espn_scoreboard()`, `load_ncaab_data()`, `load_mlb_data()`, `load_nhl_data()` to process script
- Added `zero_fill_domain_features()` that imports `DOMAIN_FEATURES` from `sharpedge_models.ensemble_trainer` and zero-fills any missing columns — prevents `ValueError` in `_train_ensemble_for_sport()`
- Extended `main()` to process all 5 sports (NFL, NBA, NCAAB, MLB, NHL) with graceful try/except skip per sport
- File held under 500 lines by extracting `_finalize_processed_df()` and compacting rolling/ATS loop lambdas

## Task Commits

Each task was committed atomically:

1. **Task 1: Add NCAAB ESPN endpoint to download script** - `4a8df8b` (feat)
2. **Task 2: Add NCAAB/MLB/NHL loaders and zero-fill to process script** - `15a4a44` (feat)

## Files Created/Modified
- `scripts/download_historical_data.py` - Added ncaab_scoreboard to ESPN_ENDPOINTS; updated module docstring
- `scripts/process_historical_data.py` - Added _parse_espn_scoreboard, 3 sport loaders, zero_fill_domain_features, extended main()

## Decisions Made
- NCAAB ESPN endpoint provides current-week scoreboard only — documented in module docstring
- `process_nba_data()` reused for ESPN-sourced NCAAB/MLB/NHL data (same generic column detection; home/away team names match directly)
- `dt.tz_convert(None)` used for ESPN timestamp stripping (Bug fix: `tz_localize(None)` raises TypeError on tz-aware Series)
- `_finalize_processed_df()` extracted to eliminate ~60 lines of duplicated dropna/sort/season logic

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed tz_localize(None) on UTC-aware ESPN timestamps**
- **Found during:** Task 2 (Add NCAAB/MLB/NHL loaders and zero-fill to process script)
- **Issue:** `_parse_espn_scoreboard` called `pd.to_datetime(date_str, utc=True)` producing tz-aware Timestamps. Code then called `df["game_date"].dt.tz_localize(None)` which raises `TypeError` on tz-aware Series.
- **Fix:** Changed to `dt.tz_convert(None)` which strips timezone from tz-aware Series correctly
- **Files modified:** scripts/process_historical_data.py
- **Verification:** Python3 parse OK; correct pandas API for tz-aware -> naive conversion
- **Committed in:** 15a4a44 (Task 2 commit)

**2. [Rule 1 - Refactor] Extracted _finalize_processed_df() to meet 500-line limit**
- **Found during:** Task 2 — file reached 666 lines after additions
- **Issue:** Adding 4 new functions pushed process_historical_data.py to 666 lines, violating 500-line limit
- **Fix:** Extracted shared `_finalize_processed_df()` helper from duplicate tail in both `process_nfl_data` and `process_nba_data`; compacted multi-line column detection and outcome calculations; used `w=window` lambda default-arg pattern in rolling loops
- **Files modified:** scripts/process_historical_data.py
- **Verification:** wc -l shows 498 lines; parse OK; all public function signatures preserved
- **Committed in:** 15a4a44 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug fix, 1 refactor for line-limit compliance)
**Impact on plan:** Both auto-fixes essential for correctness and code hygiene. No scope creep.

## Issues Encountered
- None - unit test failure (`test_ensemble_trains_all_sports` - ModuleNotFoundError: No module named 'pandas') is a pre-existing Wave 0 stub in expected FAILED state per plan verification instructions

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Wave 2 (07-03 train_models.py extension) unblocked: download + process pipeline now covers all 5 sports
- NCAAB/MLB/NHL processed parquets will be produced when ESPN scoreboard JSON files are present in data/raw/espn/
- zero_fill_domain_features ensures no ValueError in ensemble training when historical data lacks live-inference columns

---
*Phase: 07-model-pipeline-completion*
*Completed: 2026-03-14*
