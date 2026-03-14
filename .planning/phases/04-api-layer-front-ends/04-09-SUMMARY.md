---
phase: 04-api-layer-front-ends
plan: "09"
subsystem: mobile

tags: [flutter, dart, http, provider, api, bets]

# Dependency graph
requires:
  - phase: 04-api-layer-front-ends/04-05
    provides: ApiService class with simulateBankroll() pattern and AppState provider
  - phase: 04-api-layer-front-ends/04-06
    provides: LogBetSheet widget and value_plays_screen swipe-to-log flow

provides:
  - ApiService.logBet() method that POSTs bets to /api/v1/bets with Bearer auth
  - LogBetSheet with real async API call on Confirm (loading indicator + error snackbar)

affects:
  - phase-05-model-pipeline
  - any backend plan implementing the POST /api/v1/bets endpoint

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Async Flutter state management: _isLoading bool disables button during in-flight POST"
    - "AppState token read via context.read<AppState>() in modal sheet"
    - "mounted guard after async gap before setState/Navigator calls"
    - "ApiException catch + generic catch for comprehensive error Snackbar display"

key-files:
  created: []
  modified:
    - apps/mobile/lib/services/api_service.dart
    - apps/mobile/lib/widgets/log_bet_sheet.dart

key-decisions:
  - "LogBetSheet reads auth token from AppState via Provider rather than constructor parameter — consistent with how value_plays_screen.dart uses AppState"
  - "Module-level _apiService instance in log_bet_sheet.dart for simplicity — matches existing pattern in the codebase"
  - "logBet() accepts both 200 and 201 response codes — backend endpoint spec says 201 but defensive coding allows either"

patterns-established:
  - "Bet persistence pattern: ApiService.logBet() called from sheet _confirmBet() with full play metadata + user stake"

requirements-completed:
  - MOB-01

# Metrics
duration: 1min
completed: 2026-03-14
---

# Phase 4 Plan 09: Log Bet API Wiring Summary

**MOB-01 gap-closure: swipe-to-log now persists bets via ApiService.logBet() POST to /api/v1/bets with Bearer auth, loading indicator, and error snackbar retry flow**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-14T16:04:25Z
- **Completed:** 2026-03-14T16:05:18Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `logBet()` method to ApiService that POSTs play_id, event, market, team, book, stake as JSON with Authorization: Bearer token header; throws ApiException on non-200/201
- Replaced the TODO stub Confirm button in LogBetSheet with a real async `_confirmBet()` method that shows CircularProgressIndicator while loading, shows error Snackbar on failure (sheet stays open for retry), and pops with result on success
- Removed the `// TODO: POST bet to API in full implementation` comment — MOB-01 is now fully closed

## Task Commits

Each task was committed atomically:

1. **Task 1: Add logBet() to ApiService** - `c4f8ae1` (feat)
2. **Task 2: Wire LogBetSheet Confirm to ApiService.logBet() with async lifecycle** - `83d761f` (feat)

## Files Created/Modified

- `apps/mobile/lib/services/api_service.dart` - Added `logBet()` method (POST /api/v1/bets, Bearer auth, JSON body)
- `apps/mobile/lib/widgets/log_bet_sheet.dart` - Replaced TODO stub with async `_confirmBet()`, added `_isLoading` state, provider import, api_service import

## Decisions Made

- LogBetSheet reads auth token from `AppState` via `context.read<AppState>()` rather than constructor parameter — this is consistent with how `value_plays_screen.dart` already uses AppState and avoids threading token through call sites
- Module-level `_apiService` instance in log_bet_sheet.dart for simplicity, matching the codebase's existing pattern
- `logBet()` accepts both HTTP 200 and 201 — the backend spec says 201 but defensive coding avoids fragility if the endpoint returns 200

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required. The POST /api/v1/bets backend endpoint is a Phase 5 concern; the mobile client will POST to it correctly once it exists.

## Next Phase Readiness

- MOB-01 fully closed: swipe-to-log is now a complete persistence flow
- Backend team needs to implement POST /api/v1/bets (bets table + RLS is already in schema_rls.sql)
- All mobile screens and flows are complete for Phase 4

## Self-Check: PASSED

- `apps/mobile/lib/services/api_service.dart` — FOUND, contains logBet()
- `apps/mobile/lib/widgets/log_bet_sheet.dart` — FOUND, contains _confirmBet() + _isLoading
- Commit c4f8ae1 — FOUND (Task 1)
- Commit 83d761f — FOUND (Task 2)

---
*Phase: 04-api-layer-front-ends*
*Completed: 2026-03-14*
