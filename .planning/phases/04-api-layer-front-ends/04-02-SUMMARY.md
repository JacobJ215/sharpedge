---
phase: 04-api-layer-front-ends
plan: "02"
subsystem: api
tags: [fastapi, sse, streaming, monte-carlo, supabase-rls, jwt, portfolio, bankroll]

requires:
  - phase: 04-api-layer-front-ends/04-01
    provides: deps.py with get_current_user and CurrentUser for auth-gated routes
  - phase: 01-quant-engine
    provides: simulate_bankroll() module-level function from monte_carlo.py
  - phase: 02-agent-architecture
    provides: build_copilot_graph() returning CompiledStateGraph or None

provides:
  - POST /api/v1/copilot/chat — SSE streaming via StreamingResponse text/event-stream
  - GET /api/v1/users/{id}/portfolio — auth-gated portfolio stats (RLS-enforced)
  - POST /api/v1/bankroll/simulate — public Monte Carlo bankroll simulation
  - All 5 v1 routes wired into main.py under /api/v1 prefix

affects:
  - 04-api-layer-front-ends/04-03 and beyond (full v1 surface complete)
  - Mobile app (Expo) consuming these endpoints
  - Next.js web app consuming portfolio and bankroll endpoints

tech-stack:
  added: []
  patterns:
    - "SSE streaming: async generator + StreamingResponse(media_type='text/event-stream')"
    - "Lazy graph import with None fallback for missing OPENAI_API_KEY"
    - "Module-level wrapper functions for patchability in tests (bankroll.simulate_bankroll, portfolio.get_performance_summary)"
    - "Thin lazy import shims for DB query functions enable test-time patching without real DB"

key-files:
  created:
    - apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py
    - apps/webhook_server/src/sharpedge_webhooks/routes/v1/portfolio.py
    - apps/webhook_server/src/sharpedge_webhooks/routes/v1/bankroll.py
  modified:
    - apps/webhook_server/src/sharpedge_webhooks/main.py
    - apps/webhook_server/tests/unit/api/test_copilot_sse.py
    - apps/webhook_server/tests/unit/api/test_portfolio.py
    - apps/webhook_server/tests/unit/api/test_bankroll_simulate.py

key-decisions:
  - "Module-level lazy-import wrapper functions (not inline lazy imports) allow unittest.mock.patch to target the correct namespace"
  - "Copilot route gracefully degrades to fallback SSE message when graph is None (no OPENAI_API_KEY) rather than raising 500"
  - "Portfolio route enforces user_id == current_user['id'] check as secondary authorization guard (RLS is primary)"

patterns-established:
  - "SSE pattern: async def _stream_*() AsyncGenerator + StreamingResponse with Cache-Control/Connection/X-Accel-Buffering headers"
  - "Public endpoint pattern: no Depends() on auth, just lazy-import Phase 1 function and return normalized dict"
  - "Auth-gated pattern: CurrentUser annotation injects Depends(get_current_user) transparently; route raises 403 for cross-user access"

requirements-completed: [API-03, API-04, API-05]

duration: 2min
completed: 2026-03-14
---

# Phase 4 Plan 02: Remaining v1 Routes (Copilot SSE + Portfolio + Bankroll) Summary

**Three FastAPI v1 routes added: SSE-streaming BettingCopilot chat, RLS-gated portfolio analytics, and public Monte Carlo bankroll simulation — completing the full v1 API surface**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-14T06:28:16Z
- **Completed:** 2026-03-14T06:30:29Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 7

## Accomplishments

- Implemented `copilot.py` with SSE streaming that gracefully falls back when OPENAI_API_KEY is absent
- Implemented `portfolio.py` with auth-gated portfolio analytics (ROI, win rate, CLV average, drawdown, active bets)
- Implemented `bankroll.py` with public Monte Carlo simulation delegating to Phase 1 `simulate_bankroll()`
- Registered all 5 v1 routers in `main.py` — value-plays, game-analysis, copilot, portfolio, bankroll/simulate
- 16 API tests pass (2 skipped for unrelated stubs), 0 failures

## Task Commits

Each task was committed atomically:

1. **Task 1: POST /api/v1/copilot/chat SSE streaming** - `c85fc71` (feat)
2. **Task 2: Portfolio + Bankroll routes + main.py wiring** - `9adf58f` (feat)

## Files Created/Modified

- `apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py` - SSE streaming endpoint with LangGraph astream_events and [DONE] terminator
- `apps/webhook_server/src/sharpedge_webhooks/routes/v1/portfolio.py` - Auth-gated portfolio stats with CLV average and max drawdown calculation
- `apps/webhook_server/src/sharpedge_webhooks/routes/v1/bankroll.py` - Public Monte Carlo simulation with Pydantic validation
- `apps/webhook_server/src/sharpedge_webhooks/main.py` - Added 3 new router registrations under /api/v1
- `apps/webhook_server/tests/unit/api/test_copilot_sse.py` - 3 tests: content-type, data: lines, [DONE] terminator
- `apps/webhook_server/tests/unit/api/test_portfolio.py` - 2 tests: 401 no-auth, shape with mocked auth
- `apps/webhook_server/tests/unit/api/test_bankroll_simulate.py` - 2 tests: public access (200), response shape

## Decisions Made

- **Module-level lazy-import wrappers for test patchability:** Used `def simulate_bankroll(...)` and `def get_performance_summary(...)` as module-level wrappers (rather than inline lazy imports inside route functions). This exposes the correct patch target as `sharpedge_webhooks.routes.v1.bankroll.simulate_bankroll` so `unittest.mock.patch` can intercept them during tests.
- **Copilot graceful degradation:** When `build_copilot_graph()` returns None (no OPENAI_API_KEY), the endpoint emits a descriptive fallback SSE message rather than raising a 500 error. This allows the mobile/web UI to display something useful in offline/unconfigured environments.
- **Portfolio secondary authorization check:** Even though Supabase RLS is the primary guard, the route explicitly checks `current_user["id"] != user_id` and raises 403. Defense in depth.

## Deviations from Plan

None — plan executed exactly as written. The only structural adaptation was using module-level wrapper functions instead of inline lazy imports to ensure correct mock patch targets, which is consistent with the plan's test mocking guidance.

## Issues Encountered

None.

## Next Phase Readiness

- Full v1 API surface complete: 5 routes under /api/v1
- Ready for Phase 4 Plan 03 (Next.js web front-end consuming these endpoints)
- Bankroll simulator endpoint is immediately usable from mobile app
- Portfolio endpoint ready for Expo mobile integration once auth flow is complete

---
*Phase: 04-api-layer-front-ends*
*Completed: 2026-03-14*
