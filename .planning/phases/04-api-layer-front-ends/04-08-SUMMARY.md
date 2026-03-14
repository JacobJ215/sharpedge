---
phase: 04-api-layer-front-ends
plan: "08"
subsystem: database, ui
tags: [supabase, rls, row-level-security, recharts, portfolio, auth-token, next.js]

requires:
  - phase: 04-00
    provides: Supabase schema + RLS migration baseline for bets/value_plays/user_device_tokens
  - phase: 04-03
    provides: Portfolio page and web app scaffold with RoiCurve pattern

provides:
  - user_bankroll RLS policy (user_own_bankroll + service_role_all_bankroll)
  - BankrollCurve Recharts AreaChart component (blue, accepts { date, bankroll }[] data)
  - Portfolio page sourcing auth token from supabase.auth.getSession() with onAuthStateChange listener

affects:
  - phase-05-model-pipeline
  - 04-VERIFICATION

tech-stack:
  added: []
  patterns:
    - "supabase.auth.getSession() + onAuthStateChange in useEffect for live token state"
    - "SWR key set to null when token empty to suppress pre-auth fetch"
    - "Recharts AreaChart with linearGradient fill in JSX (not named exports)"

key-files:
  created:
    - apps/web/src/components/portfolio/bankroll-curve.tsx
  modified:
    - scripts/schema_rls.sql
    - apps/web/src/app/(dashboard)/page.tsx

key-decisions:
  - "SWR key includes token and is null when empty — prevents 401 fetch before session resolves"
  - "onAuthStateChange listener added alongside getSession — handles token refresh and sign-out events"
  - "Pre-existing TS errors in roi-curve.tsx (defs/linearGradient/stop named exports) are out of scope — not introduced by this plan"

patterns-established:
  - "BankrollCurve follows RoiCurve pattern with blue (#3b82f6) color to visually distinguish curves"
  - "user_bankroll RLS mirrors bets pattern: user_own policy (auth.uid() = user_id) + service_role bypass"

requirements-completed: [API-06, WEB-01]

duration: 2min
completed: 2026-03-14
---

# Phase 4 Plan 08: Gap Closure — user_bankroll RLS + Portfolio Auth Token + BankrollCurve Summary

**user_bankroll RLS policies added to schema_rls.sql, portfolio page auth token sourced from supabase.auth.getSession(), and BankrollCurve Recharts AreaChart component created — closing API-06 and WEB-01 blockers from Phase 4 verification**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-14T14:04:18Z
- **Completed:** 2026-03-14T14:06:08Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- Added `ALTER TABLE user_bankroll ENABLE ROW LEVEL SECURITY` plus user_own_bankroll and service_role_all_bankroll policies to schema_rls.sql
- Updated schema_rls.sql verification query to include user_bankroll in the four-table IN clause
- Created bankroll-curve.tsx as a blue AreaChart component accepting `{ date: string; bankroll: number }[]` data
- Removed hardcoded `const token = ''` from portfolio page; token now populated by `supabase.auth.getSession()` in useEffect with onAuthStateChange listener for live updates
- SWR key changed to `null` when token is empty to prevent pre-auth 401 requests

## Task Commits

1. **Task 1: Add user_bankroll RLS to schema_rls.sql** - `91bf6ff` (feat)
2. **Task 2: Fix portfolio page auth token + add BankrollCurve** - `605f0fa` (feat)

## Files Created/Modified

- `scripts/schema_rls.sql` - Added section 5b: user_bankroll RLS enablement + two policies; updated verification query to 4-table IN clause
- `apps/web/src/components/portfolio/bankroll-curve.tsx` - New BankrollCurve Recharts AreaChart component (blue, exported, typed interface)
- `apps/web/src/app/(dashboard)/page.tsx` - Removed hardcoded empty token; added getSession/onAuthStateChange useEffect; added BankrollCurve below RoiCurve; updated SWR key to include token

## Decisions Made

- SWR key set to `null` when token empty — suppresses fetch until session resolves, preventing the 401 loop
- `onAuthStateChange` added alongside `getSession` call — ensures token state updates on sign-in, sign-out, and token refresh without requiring page reload
- Pre-existing TypeScript errors in roi-curve.tsx (invalid named exports `defs`, `linearGradient`, `stop` from recharts) confirmed pre-existing and left out of scope per deviation rule scope boundary

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing TypeScript errors in `apps/web/src/components/portfolio/roi-curve.tsx` (attempting to import `defs`, `linearGradient`, `stop` as named exports from recharts — these are SVG JSX elements, not exports). Confirmed pre-existing via `git stash` check. Out of scope for this plan; bankroll-curve.tsx was written correctly without those invalid imports.

## User Setup Required

None - no external service configuration required. The schema_rls.sql changes require running the migration against Supabase (as documented in the file header: `psql $DATABASE_URL < scripts/schema_rls.sql`).

## Next Phase Readiness

- API-06 blocker closed: user_bankroll now has RLS parity with bets/value_plays/user_device_tokens
- WEB-01 blocker closed: portfolio page sends real Bearer token; BankrollCurve renders below ROI curve
- Phase 4 VERIFICATION.md should now pass for both API-06 and WEB-01 criteria

---
*Phase: 04-api-layer-front-ends*
*Completed: 2026-03-14*
