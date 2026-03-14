---
phase: 04-api-layer-front-ends
plan: "01"
subsystem: api
tags: [fastapi, supabase, jwt, alpha-scoring, value-plays, game-analysis]

# Dependency graph
requires:
  - phase: 03-prediction-market-intelligence
    provides: alpha scoring patterns (alpha_score, regime_state, badges)
  - phase: 02-agent-architecture
    provides: compose_alpha, rank_by_alpha module functions
provides:
  - GET /api/v1/value-plays with alpha enrichment (alpha_score, alpha_badge, regime_state)
  - GET /api/v1/games/{game_id}/analysis with model_prediction, ev_breakdown, regime_state
  - get_current_user FastAPI dependency (Supabase JWT verification)
  - CurrentUser Annotated type alias for downstream routes
  - routes/v1/ package structure for Phase 4 API plans
affects: [04-02-portfolio-bankroll, 04-03-web-frontend, 04-04-mobile-frontend]

# Tech tracking
tech-stack:
  added: [fastapi HTTPBearer, supabase.create_client (lazy import in auth path)]
  patterns: [TDD London School with unittest.mock.patch for DB/Supabase calls, Annotated dependency injection, alpha badge threshold table, lazy supabase import in auth dependency]

key-files:
  created:
    - apps/webhook_server/src/sharpedge_webhooks/routes/v1/__init__.py
    - apps/webhook_server/src/sharpedge_webhooks/routes/v1/deps.py
    - apps/webhook_server/src/sharpedge_webhooks/routes/v1/value_plays.py
    - apps/webhook_server/src/sharpedge_webhooks/routes/v1/game_analysis.py
    - apps/webhook_server/tests/__init__.py
    - apps/webhook_server/tests/unit/__init__.py
    - apps/webhook_server/tests/unit/api/__init__.py
  modified:
    - apps/webhook_server/src/sharpedge_webhooks/main.py
    - apps/webhook_server/tests/unit/api/test_rls.py
    - apps/webhook_server/tests/unit/api/test_value_plays_v1.py
    - apps/webhook_server/tests/unit/api/test_game_analysis.py

key-decisions:
  - "Lazy supabase import inside get_current_user avoids import-time Supabase client creation — safe for test environments without env vars"
  - "Patch target for Supabase mock is supabase.create_client not the local import path (lazy import pattern)"
  - "Alpha badge thresholds: PREMIUM>=0.85, HIGH>=0.70, MEDIUM>=0.50, SPECULATIVE<0.50 — matches existing alpha.py badges from Phase 1/2"
  - "game_analysis reuses get_active_value_plays by game ID match — avoids new DB query for now; Phase 5 will add dedicated game table query"
  - "Both v1 routers registered separately in main.py (not combined v1 APIRouter) to keep files small and independent"

patterns-established:
  - "v1 route pattern: module-level router with APIRouter(tags=['v1']), registered in main.py with prefix='/api/v1'"
  - "Auth dependency: get_current_user in deps.py with CurrentUser = Annotated[dict, Depends(get_current_user)] for downstream routes"
  - "Alpha enrichment: float(r.get('alpha_score') or 0.0) pattern for safe None/missing DB field handling"
  - "Test mocking: patch sharpedge_webhooks.routes.v1.{module}.get_active_value_plays for DB isolation"

requirements-completed: [API-06, API-01, API-02]

# Metrics
duration: 18min
completed: 2026-03-14
---

# Phase 4 Plan 01: v1 Auth Dependency + Value-Plays + Game-Analysis Summary

**FastAPI v1 routes with Supabase JWT auth dependency, alpha-ranked value-plays endpoint (PREMIUM/HIGH/MEDIUM/SPECULATIVE badges), and game analysis endpoint returning model_prediction, ev_breakdown, and regime_state**

## Performance

- **Duration:** 18 min
- **Started:** 2026-03-14T05:42:05Z
- **Completed:** 2026-03-14T06:00:00Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments

- Established the routes/v1/ package and get_current_user auth dependency with Supabase JWT verification (raises 401 for invalid tokens, 503 if Supabase unconfigured)
- GET /api/v1/value-plays returns alpha-enriched plays with alpha_score, alpha_badge (PREMIUM/HIGH/MEDIUM/SPECULATIVE), regime_state, and min_alpha filtering
- GET /api/v1/games/{game_id}/analysis returns model_prediction, ev_breakdown, regime_state, key_number_proximity with 404 for unknown game IDs
- 9 unit tests passing (4 auth, 3 value-plays, 2 game-analysis); old /api/value-plays unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1: v1 auth dependency (deps.py) + package init** - `d56f440` (feat)
2. **Task 2: GET /api/v1/value-plays + game-analysis + wire into main.py** - `25d8fdd` (feat)

## Files Created/Modified

- `apps/webhook_server/src/sharpedge_webhooks/routes/v1/__init__.py` - Package init
- `apps/webhook_server/src/sharpedge_webhooks/routes/v1/deps.py` - get_current_user + CurrentUser type alias
- `apps/webhook_server/src/sharpedge_webhooks/routes/v1/value_plays.py` - GET /api/v1/value-plays with alpha enrichment
- `apps/webhook_server/src/sharpedge_webhooks/routes/v1/game_analysis.py` - GET /api/v1/games/{game_id}/analysis
- `apps/webhook_server/src/sharpedge_webhooks/main.py` - v1 router registration added
- `apps/webhook_server/tests/unit/api/test_rls.py` - Replaced skip stubs with 4 real auth tests
- `apps/webhook_server/tests/unit/api/test_value_plays_v1.py` - Replaced skip stubs with 3 real tests
- `apps/webhook_server/tests/unit/api/test_game_analysis.py` - Replaced skip stubs with 2 real tests

## Decisions Made

- Used lazy `from supabase import create_client` inside `get_current_user` to avoid import-time Supabase initialization; this means tests must patch `supabase.create_client`, not the local module path
- Both v1 routers registered separately in main.py (`v1_value_plays_router` and `v1_game_analysis_router`) rather than combining into a single APIRouter — keeps each file under 60 lines and independently testable
- `game_analysis` reuses `get_active_value_plays(limit=200)` and finds by ID — avoids a new dedicated query; this will be replaced in Phase 5 when a proper game-level table query exists

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected mock patch target for lazy supabase import**
- **Found during:** Task 1 (test_rls.py execution)
- **Issue:** Plan specified patching `sharpedge_webhooks.routes.v1.deps.create_client` but since create_client is imported lazily inside the function body, the module attribute doesn't exist at patch time
- **Fix:** Changed patch target to `supabase.create_client` which patches the source module
- **Files modified:** apps/webhook_server/tests/unit/api/test_rls.py
- **Verification:** All 4 test_rls.py tests pass
- **Committed in:** d56f440 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in test patch target)
**Impact on plan:** Essential for test correctness. Lazy import is the right pattern; tests simply needed the correct patch target.

## Issues Encountered

None beyond the patch target deviation documented above.

## User Setup Required

None - no external service configuration required for this plan. Supabase credentials are read from environment variables at runtime (SUPABASE_URL, SUPABASE_KEY).

## Next Phase Readiness

- `get_current_user` and `CurrentUser` are ready for Plan 02 (portfolio/bankroll routes) to import from `sharpedge_webhooks.routes.v1.deps`
- v1 router pattern established — Plan 02 follows same `APIRouter(tags=["v1"])` + `include_router(router, prefix="/api/v1")` pattern
- Old `/api/value-plays` mobile route unchanged (backward-compatible for Flutter app)

---
*Phase: 04-api-layer-front-ends*
*Completed: 2026-03-14*
