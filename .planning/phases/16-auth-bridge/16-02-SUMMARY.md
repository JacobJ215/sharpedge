---
phase: 16-auth-bridge
plan: 02
subsystem: auth
tags: [supabase, ssr, middleware, next-js, tier-gating, signup, upgrade, jwt]

requires:
  - "16-01: Migration 008 and custom_access_token_hook deployed"
provides:
  - "@supabase/ssr installed with server-side session reading capability"
  - "middleware.ts: tier-based route protection at Edge layer with TIER_ORDER"
  - "supabase-server.ts: server-side Supabase client factory (createServerSupabaseClient)"
  - "supabase.ts: refactored to createBrowserClient with backward-compat legacy export"
  - "/auth/callback: server client with correct cookie writing via exchangeCodeForSession"
  - "/auth/signup: email/password registration page with confirmation flow"
  - "/upgrade: upgrade prompt page with Whop link for free-tier users"
affects:
  - 17-web-deployment

tech-stack:
  added:
    - "@supabase/ssr@0.9.0 — server-side Supabase client with getAll/setAll cookie API"
  patterns:
    - "Middleware tier gate: createServerClient in middleware reads session, checks app_metadata.tier against TIER_ORDER"
    - "Operator route gate: app_metadata.is_operator === true required for /execution, /swarm, etc."
    - "Server client pattern: getAll/setAll cookie API (not get/set/remove) required by @supabase/ssr v0.9.0+"

key-files:
  created:
    - apps/web/src/lib/supabase-server.ts
    - apps/web/src/middleware.ts
    - apps/web/src/app/auth/signup/page.tsx
    - apps/web/src/app/upgrade/page.tsx
  modified:
    - apps/web/src/lib/supabase.ts
    - apps/web/src/app/auth/callback/route.ts
    - apps/web/package.json

key-decisions:
  - "@supabase/ssr v0.9.0 uses getAll/setAll cookie API (not get/set/remove) — plan code updated accordingly"
  - "Legacy supabase export kept in supabase.ts so login page and dashboard layout require no changes in this plan"
  - "Operator routes redirect to / silently (no upgrade prompt) to avoid leaking route existence to subscribers"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03, AUTH-04]

duration: 2min
completed: 2026-03-21
---

# Phase 16 Plan 02: Auth Bridge Web Infrastructure Summary

**@supabase/ssr with tier-based middleware route protection, server-side callback handler, email signup page, and Whop upgrade prompt**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-21T18:08:19Z
- **Completed:** 2026-03-21T18:11:04Z
- **Tasks:** 2 (1 checkpoint auto-approved, 1 auto)
- **Files modified:** 7

## Accomplishments

- Task 1 (checkpoint:human-verify) was auto-approved in auto mode — Custom Access Token Hook registration in Supabase Dashboard is a manual step the user must complete; documented in User Setup section
- Installed @supabase/ssr@0.9.0 and refactored supabase.ts to use createBrowserClient; legacy `supabase` named export retained so existing consumers (login page, dashboard layout) continue to work unchanged
- Created middleware.ts with TIER_ORDER = { free: 0, pro: 1, sharp: 2 }, protecting 6 subscriber routes at Edge and 6 operator-only routes; reads app_metadata.tier from JWT via getSession()
- Created supabase-server.ts with createServerSupabaseClient factory for use in Route Handlers and Server Components
- Rewrote auth/callback/route.ts to use server client with proper cookie writing via exchangeCodeForSession (was using browser client which cannot write cookies server-side)
- Added /auth/signup page with email/password form, emailRedirectTo pointing to /auth/callback, and "check your email" confirmation state
- Added /upgrade page with Whop link (https://whop.com/sharpedge/) for free-tier users redirected from gated routes
- Build passes with 18 static/dynamic routes and 75.5 kB middleware bundle

## Task Commits

Each task was committed atomically:

1. **Task 1: Register Custom Access Token Hook** — checkpoint:human-verify, auto-approved (no commit — no code changes)
2. **Task 2: Install @supabase/ssr + all web auth files** — `7c69776` (feat)

## Files Created/Modified

- `apps/web/package.json` — Added @supabase/ssr@^0.9.0 dependency
- `apps/web/src/lib/supabase.ts` — Refactored to createBrowserClient from @supabase/ssr; legacy export preserved
- `apps/web/src/lib/supabase-server.ts` — New: createServerSupabaseClient factory with getAll/setAll cookie API
- `apps/web/src/middleware.ts` — New: TIER_ORDER, ROUTE_MIN_TIER, OPERATOR_ROUTES; Edge session check via createServerClient
- `apps/web/src/app/auth/callback/route.ts` — Rewritten: now uses createServerClient with getAll/setAll for correct session cookie writing
- `apps/web/src/app/auth/signup/page.tsx` — New: email/password signup with emailRedirectTo callback and confirmation state
- `apps/web/src/app/upgrade/page.tsx` — New: upgrade prompt with Whop link for free-tier users

## Decisions Made

- @supabase/ssr v0.9.0 requires getAll/setAll cookie API — the plan's code used the deprecated get/set/remove API; auto-fixed inline before build
- Legacy `supabase` named export retained in supabase.ts to avoid breaking login page and dashboard layout in this plan scope
- Operator route redirects to `/` (not `/upgrade`) — silently excludes non-operators without leaking that restricted routes exist

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated cookie API from get/set/remove to getAll/setAll**
- **Found during:** Task 2 — first build attempt
- **Issue:** @supabase/ssr v0.9.0 `CookieMethodsServer` type requires `getAll`/`setAll` — the plan's code examples used the deprecated `get`/`set`/`remove` interface, causing TypeScript errors in middleware.ts, supabase-server.ts, and callback/route.ts
- **Fix:** Updated all three files to use `getAll: () => cookieStore.getAll()` and `setAll: (cookiesToSet) => cookiesToSet.forEach(...)` pattern
- **Files modified:** middleware.ts, supabase-server.ts, app/auth/callback/route.ts
- **Commit:** 7c69776

## User Setup Required

**Task 1 checkpoint — human action still required:**

The Custom Access Token Hook must be registered in the Supabase Dashboard before JWTs will contain `app_metadata.tier`:

1. Open Supabase Dashboard for this project
2. Navigate to Authentication -> Hooks
3. Find "Custom Access Token Hook" section
4. Set Schema = "public", Function = "custom_access_token_hook"
5. Click Save
6. Verify: sign in as a test user and run `(await supabase.auth.getSession()).data.session.user.app_metadata` in browser console — should contain `{ tier: 'free' }`

**Without this step:** The middleware will see `app_metadata.tier = undefined` and default to `'free'`, redirecting all users to /upgrade for pro routes.

## Next Phase Readiness

- Phase 17 (Web Deployment) can now configure Vercel env vars and deploy — the auth infrastructure is complete
- middleware.ts is ready for any additional routes added in Phase 17
- The /upgrade page Whop URL (`https://whop.com/sharpedge/`) should be updated with the actual Whop product URL once finalized

## Self-Check: PASSED

All files verified present. Commit 7c69776 verified in git log.

---
*Phase: 16-auth-bridge*
*Completed: 2026-03-21*
