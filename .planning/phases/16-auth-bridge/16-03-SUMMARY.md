---
phase: 16-auth-bridge
plan: 03
subsystem: auth
tags: [flutter, dart, supabase, jwt, tier-gating, whop, next-js, account-page]

requires:
  - "16-01: custom_access_token_hook injecting app_metadata.tier into JWT"
provides:
  - "AuthService.currentTier: reads JWT app_metadata['tier'], defaults 'free'"
  - "AuthService.isOperator: reads JWT app_metadata['is_operator']"
  - "AppState.hasProAccess: true for pro/sharp tiers"
  - "AppState.hasSharpAccess: true for sharp tier only"
  - "AppState.isOperator: operator gate getter"
  - "UpgradePromptWidget: reusable free-tier gate UI with Whop CTA"
  - "Web /account page: tier display + Whop subscription management links"
  - "Dashboard sidebar Account nav item"
affects:
  - 17-web-deployment
  - 20-mobile-submission

tech-stack:
  added:
    - "url_launcher ^6.2.0 (Flutter — required for UpgradePromptWidget Whop link)"
  patterns:
    - "Tier gate pattern: AppState.hasProAccess / hasSharpAccess guards gated screens; UpgradePromptWidget shown to free users"
    - "JWT read pattern: app_metadata read directly from Supabase.instance.client.auth.currentUser?.appMetadata without DB query"
    - "Account page pattern: client-side getSession() reads tier from session.user.app_metadata for display"

key-files:
  created:
    - apps/mobile/lib/widgets/upgrade_prompt.dart
    - apps/web/src/app/account/page.tsx
  modified:
    - apps/mobile/lib/services/auth_service.dart
    - apps/mobile/lib/providers/app_state.dart
    - apps/mobile/pubspec.yaml
    - apps/web/src/app/(dashboard)/layout.tsx

key-decisions:
  - "UpgradePromptWidget reads tier as 'pro' default requiredTier param — callers override for sharp-only gates"
  - "Web account page uses client-side supabase.auth.getSession() — no server component needed since tier is non-sensitive display data"
  - "iOS upgrade button links to whop.com/sharpedge/ external browser only — no in-app purchase flow, Apple Guideline 3.1.1 compliant"
  - "url_launcher added to pubspec.yaml — was not previously a dependency"

duration: 4min
completed: 2026-03-21
---

# Phase 16 Plan 03: Tier UI — Flutter Getters + Web Account Page Summary

**Flutter tier getters (currentTier, hasProAccess, hasSharpAccess, isOperator) + UpgradePromptWidget, web /account page with JWT tier display and Whop subscription management link, dashboard Account nav item**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-21T18:07:00Z
- **Completed:** 2026-03-21T18:10:01Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- AuthService gains `currentTier` and `isOperator` getters reading directly from Supabase JWT app_metadata — no DB query needed per the custom_access_token_hook established in Plan 01
- AppState gains `currentTier`, `hasProAccess`, `hasSharpAccess`, and `isOperator` computed getters; imports supabase_flutter for appMetadata access
- New `UpgradePromptWidget` provides a reusable lock screen with lock icon, upgrade message, and "Upgrade on Whop" button that opens whop.com/sharpedge/ in external browser
- Web /account page displays current tier with color-coded badge (zinc=free, emerald=pro, amber=sharp), "Manage subscription on Whop" link for paid users, "Subscribe on Whop" for free users
- Dashboard sidebar updated with Account nav item (user icon) linking to /account

## Task Commits

Each task was committed atomically:

1. **Task 1: Flutter tier getters + UpgradePromptWidget** - `bb3473c` (feat)
2. **Task 2: Web /account page + Account nav item** - `5786e61` (feat)

## Files Created/Modified

- `apps/mobile/lib/services/auth_service.dart` - Added currentTier + isOperator getters after isSignedIn
- `apps/mobile/lib/providers/app_state.dart` - Added supabase_flutter import + currentTier, hasProAccess, hasSharpAccess, isOperator computed getters
- `apps/mobile/lib/widgets/upgrade_prompt.dart` - New UpgradePromptWidget with configurable requiredTier param and Whop external link
- `apps/mobile/pubspec.yaml` - Added url_launcher ^6.2.0
- `apps/web/src/app/account/page.tsx` - New client-side account page with tier badge + Whop links
- `apps/web/src/app/(dashboard)/layout.tsx` - Added Account nav item after Feed

## Decisions Made

- UpgradePromptWidget defaults requiredTier to 'pro'; callers pass 'sharp' for sharp-only gated screens
- Web account page uses client-side getSession() rather than a server component — tier is display data, not a security gate, so SSR is unnecessary overhead here
- iOS upgrade path links to external browser only (no in-app payment UI) to comply with Apple Guideline 3.1.1
- url_launcher was not previously in pubspec.yaml and was added as part of this task (deviation Rule 3 — missing dependency)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Missing Dependency] Added url_launcher to pubspec.yaml**
- **Found during:** Task 1 — UpgradePromptWidget uses url_launcher but it was absent from pubspec.yaml
- **Fix:** Added `url_launcher: ^6.2.0` to dependencies section
- **Files modified:** apps/mobile/pubspec.yaml
- **Commit:** bb3473c

## Issues Encountered

None beyond the url_launcher dependency gap handled above.

## Self-Check: PASSED

All files verified present and commits verified in git log.

---
*Phase: 16-auth-bridge*
*Completed: 2026-03-21*
