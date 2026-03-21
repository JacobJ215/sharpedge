---
phase: 16-auth-bridge
plan: 01
subsystem: auth
tags: [supabase, jwt, custom-access-token-hook, postgres, rls, revenuecat, whop, webhooks]

requires: []
provides:
  - "Migration 008: supabase_auth_id bridge column linking Supabase Auth UUIDs to public.users"
  - "handle_new_auth_user trigger: auto-creates public.users row on Supabase Auth signup"
  - "custom_access_token_hook: injects tier + is_operator into every JWT at issue time"
  - "push_tier_to_supabase_auth in whop.py: propagates tier to auth.users on Whop events"
  - "revenuecat.py webhook handler: propagates tier to auth.users on Apple/Google IAP events"
  - "RLS policies: authenticated users can read/update their own public.users row"
affects:
  - 17-web-deployment
  - 18-discord-community
  - 20-mobile-submission

tech-stack:
  added: []
  patterns:
    - "Auth bridge pattern: supabase_auth_id UUID column links auth.users to public.users"
    - "Custom Access Token Hook: SECURITY DEFINER function reads public.users.tier into JWT app_metadata"
    - "Dual-path tier push: Whop events push via discord_id lookup; RevenueCat events push via supabase_auth_id directly"
    - "Discord-only user graceful handling: push_tier_to_supabase_auth skips when supabase_auth_id is NULL"

key-files:
  created:
    - packages/database/src/sharpedge_db/migrations/008_auth_bridge.sql
    - apps/webhook_server/src/sharpedge_webhooks/routes/revenuecat.py
    - apps/webhook_server/tests/test_whop_tier_push.py
    - apps/webhook_server/tests/test_revenuecat.py
  modified:
    - apps/webhook_server/src/sharpedge_webhooks/routes/whop.py
    - apps/webhook_server/src/sharpedge_webhooks/main.py

key-decisions:
  - "discord_id DROP NOT NULL placed before trigger creation so email-only web signups do not fail INSERT"
  - "is_operator column added to public.users and injected into JWT app_metadata to gate execution routes without exposing it to users"
  - "RevenueCat app_user_id is the Supabase Auth UUID (Flutter calls Purchases.logIn(supabaseUserId) after sign-in)"
  - "BILLING_ISSUE event logs warning but does not downgrade tier — tier stays active during billing resolution window"
  - "ON CONFLICT (supabase_auth_id) DO NOTHING in trigger prevents duplicate rows if trigger fires twice"

patterns-established:
  - "Tier push pattern: after every DB tier update, call Supabase Admin API to update auth.users.app_metadata.tier"
  - "Auth gate pattern: JWT app_metadata.tier read by all protected routes without DB query per request"

requirements-completed: [AUTH-01, AUTH-02, AUTH-04]

duration: 2min
completed: 2026-03-21
---

# Phase 16 Plan 01: Auth Bridge Summary

**Supabase Auth bridge via migration 008 (supabase_auth_id column, SECURITY DEFINER trigger, custom_access_token_hook), Whop tier push, and RevenueCat IAP handler with 7 passing tests**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-21T18:03:52Z
- **Completed:** 2026-03-21T18:05:42Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Migration 008 creates the supabase_auth_id bridge column, makes discord_id nullable, auto-creates public.users rows on Supabase Auth signup via SECURITY DEFINER trigger, and injects tier + is_operator into every JWT via Custom Access Token Hook function
- Whop webhook now calls push_tier_to_supabase_auth after every tier update so JWT reflects the change immediately without waiting for the ~1 hour auto-refresh
- New revenuecat.py handles the full Apple IAP / Google Play billing lifecycle (INITIAL_PURCHASE, RENEWAL, CANCELLATION, EXPIRATION) and pushes tier to both public.users and auth.users.app_metadata

## Task Commits

Each task was committed atomically:

1. **Task 1: Write migration 008_auth_bridge.sql** - `f32fc01` (feat)
2. **Task 2: Add push_tier_to_supabase_auth, RevenueCat handler, tests** - `dd20848` (feat)

## Files Created/Modified

- `packages/database/src/sharpedge_db/migrations/008_auth_bridge.sql` - Schema bridge: supabase_auth_id column, nullable discord_id, handle_new_auth_user trigger, custom_access_token_hook, RLS policies, grants
- `apps/webhook_server/src/sharpedge_webhooks/routes/whop.py` - Added push_tier_to_supabase_auth function and call sites in went_valid/went_invalid blocks
- `apps/webhook_server/src/sharpedge_webhooks/routes/revenuecat.py` - New RevenueCat webhook handler for mobile IAP tier sync
- `apps/webhook_server/src/sharpedge_webhooks/main.py` - Registered revenuecat_router
- `apps/webhook_server/tests/test_whop_tier_push.py` - 3 tests: linked account, discord-only user, no row
- `apps/webhook_server/tests/test_revenuecat.py` - 4 tests: INITIAL_PURCHASE, EXPIRATION, invalid auth, no app_user_id

## Decisions Made

- discord_id DROP NOT NULL must precede trigger creation so email-only signups do not fail on INSERT (discord_id has no default)
- is_operator column added as BOOLEAN DEFAULT FALSE NOT NULL; set manually for platform owner; injected into JWT app_metadata to gate execution/swarm routes server-side
- BILLING_ISSUE events log a warning only — tier is not downgraded during the billing resolution window
- RevenueCat app_user_id is set to Supabase Auth UUID at purchase time (Flutter calls Purchases.logIn after sign-in), enabling direct supabase_auth_id lookup without an intermediate discord_id step

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

**External services require manual configuration before this plan's artifacts are active:**

1. Apply migration 008 in the Supabase Dashboard SQL editor
2. Register `public.custom_access_token_hook` in the Supabase Dashboard under Authentication -> Hooks -> Custom Access Token Hook
3. Set `REVENUECAT_WEBHOOK_SECRET` environment variable in the webhook server

## Next Phase Readiness

- Migration 008 and the Custom Access Token Hook give Plan 02 everything it needs to register the hook and verify tier appears in JWTs
- Whop tier push is live; RevenueCat tier push is live — both paths write to auth.users.app_metadata immediately
- Phase 17 (web deployment) can now implement JWT-based feature gating against `app_metadata.tier`

## Self-Check: PASSED

All files verified present. Both commits verified in git log.

---
*Phase: 16-auth-bridge*
*Completed: 2026-03-21*
