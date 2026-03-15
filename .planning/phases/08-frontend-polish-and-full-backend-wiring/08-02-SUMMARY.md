---
phase: 08-frontend-polish-and-full-backend-wiring
plan: 02
subsystem: auth-and-api-endpoints
tags: [auth, supabase, fastapi, web, next-js, endpoints]
dependency_graph:
  requires: [08-01]
  provides: [web-auth-flow, markets-dislocation-endpoint, bankroll-exposure-endpoint]
  affects: [08-03, 08-04, 08-05]
tech_stack:
  added: []
  patterns: [supabase-browser-auth, use-client-auth-guard, fastapi-lazy-import, graceful-degradation]
key_files:
  created:
    - apps/web/src/app/auth/login/page.tsx
    - apps/web/src/app/auth/callback/route.ts
    - apps/webhook_server/src/sharpedge_webhooks/routes/v1/markets.py
    - packages/venue_adapters/tests/test_snapshot_store_supabase.py
    - apps/web/src/test/auth.test.tsx
    - apps/web/src/test/auth-guard.test.tsx
  modified:
    - apps/web/src/app/(dashboard)/layout.tsx
    - apps/webhook_server/src/sharpedge_webhooks/routes/v1/bankroll.py
    - apps/webhook_server/src/sharpedge_webhooks/main.py
decisions:
  - "Dashboard layout uses useEffect + getSession() to check auth and router.replace() to redirect — avoids SSR complications with supabase-js browser client"
  - "markets.py returns scores as dict keyed by venue_id to match pre-existing RED stub test expectations (test expected dict not list)"
  - "Exposure endpoint reshapes venue_tools get_exposure_status output (venue_id -> venue, utilization_pct -> pct) to match pre-written test schema"
  - "SnapshotStore Supabase test updated from @pytest.mark.skip to @pytest.mark.skipif(SUPABASE_URL not in os.environ) — runs only in integration environments"
metrics:
  duration: 236s
  completed_date: "2026-03-15"
  tasks_completed: 2
  files_created: 6
  files_modified: 3
---

# Phase 8 Plan 02: Web Auth + FastAPI Endpoint Scaffolding Summary

**One-liner:** Supabase browser-client login page with dashboard auth guard, plus GET /markets/dislocation and GET /bankroll/exposure FastAPI endpoints wired to Phase 6 venue_tools.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Web auth pages — login, callback, dashboard auth guard | 924af3d | login/page.tsx, callback/route.ts, layout.tsx (modified), auth.test.tsx, auth-guard.test.tsx |
| 2 | FastAPI dislocation + exposure endpoints + RLS integration test update | 59ca4c6 | markets.py, bankroll.py (modified), main.py (modified), test_snapshot_store_supabase.py |

---

## What Was Built

**Task 1 — Web auth flow (WIRE-01):**
- `/auth/login/page.tsx`: `'use client'` component with email/password form, loading state on submit button, error display below form, `supabase.auth.signInWithPassword()` on submit, `router.push('/')` on success
- `/auth/callback/route.ts`: GET route handler that calls `supabase.auth.exchangeCodeForSession(code)` and redirects to `/`
- `(dashboard)/layout.tsx`: Modified to add `'use client'`, `useEffect` auth guard via `supabase.auth.getSession()`, skeleton `<div>` while checking, `router.replace('/auth/login')` when session is null

**Task 2 — FastAPI endpoints (WIRE-02):**
- `routes/v1/markets.py`: GET `/api/v1/markets/dislocation` — lazy-imports `get_venue_dislocation` from `sharpedge_agent_pipeline.copilot.venue_tools`, returns `{market_id, consensus_prob, scores: dict, dislocation_bps}`; graceful empty-scores degradation on tool errors
- `routes/v1/bankroll.py`: Extended with GET `/api/v1/bankroll/exposure` — lazy-imports `get_exposure_status`, reshapes venue entries to `{venue, exposure, pct}` schema
- `main.py`: `markets_v1.router` registered with `app.include_router(..., prefix="/api/v1")`
- `test_snapshot_store_supabase.py`: Updated `@pytest.mark.skip` to `@pytest.mark.skipif("SUPABASE_URL" not in os.environ, reason="integration test...")`

---

## Test Results

| Suite | Tests | Result |
|-------|-------|--------|
| auth.test.tsx | 5 | PASSED |
| auth-guard.test.tsx | 3 | PASSED |
| test_dislocation_endpoint.py | 3 | PASSED |
| test_exposure_endpoint.py | 2 | PASSED |
| **Total** | **13** | **ALL GREEN** |

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Adaptation] scores returned as dict not list**
- **Found during:** Task 2 — examining pre-written RED stub test
- **Issue:** `test_dislocation_endpoint.py` asserts `isinstance(data["scores"], dict)` but plan spec says `scores` should be a `list`. The existing tests are the authoritative contract in TDD.
- **Fix:** Implemented `scores` as `dict[venue_id, score_entry]` in markets.py endpoint; added `dislocation_bps` as top-level field to satisfy the third test
- **Files modified:** `markets.py`

**2. [Rule 1 - Adaptation] Exposure venue field names differ from plan spec**
- **Found during:** Task 2 — examining pre-written RED stub test
- **Issue:** `test_exposure_endpoint.py` asserts `venue`, `exposure`, `pct` fields but plan spec says `venue_id`, `exposure`, `utilization_pct` and venue_tools returns `venue_id`, `utilization_pct`
- **Fix:** Reshape in the endpoint handler — `venue_id -> venue`, `utilization_pct -> pct`
- **Files modified:** `bankroll.py`

---

## Self-Check: PASSED

| Item | Status |
|------|--------|
| apps/web/src/app/auth/login/page.tsx | FOUND |
| apps/web/src/app/auth/callback/route.ts | FOUND |
| apps/webhook_server/src/sharpedge_webhooks/routes/v1/markets.py | FOUND |
| .planning/phases/08-frontend-polish-and-full-backend-wiring/08-02-SUMMARY.md | FOUND |
| Commit 924af3d | FOUND |
| Commit 59ca4c6 | FOUND |
