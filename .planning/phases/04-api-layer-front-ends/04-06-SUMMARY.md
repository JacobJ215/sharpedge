---
phase: 04-api-layer-front-ends
plan: "06"
subsystem: ui
tags: [flutter, dart, mobile, sse, streaming, value-plays, portfolio]

# Dependency graph
requires:
  - phase: 04-05
    provides: "ApiService with getValuePlaysV1/getPortfolio, AppState with auth fields, ValuePlayV1 model"
provides:
  - "value_plays_screen.dart: alpha-ranked feed with swipe-right Dismissible cards opening LogBetSheet"
  - "log_bet_sheet.dart: bottom sheet pre-filled with Kelly stake (alphaScore*20) and book name"
  - "alpha_badge_widget.dart: PREMIUM=emerald, HIGH=blue, MEDIUM=amber, SPECULATIVE=zinc pill badges"
  - "copilot_screen.dart: BettingCopilot SSE chat via http.Client.send() + LineSplitter token streaming"
  - "bankroll_screen.dart: portfolio screen calling getPortfolio() showing roi/win_rate/clv_average/drawdown/active_bets"
  - "ApiService.baseUrl static getter for CopilotScreen SSE URI"
affects:
  - phase 04-07 (authentication integration, biometric)
  - phase 05 (model pipeline provides richer alpha_score values)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Screen-local ApiService instance pattern (avoids Provider registration for API calls)"
    - "Dismissible with confirmDismiss=false to show modal without removing card"
    - "SSE streaming via http.Client.send() + utf8.decoder + LineSplitter, appending tokens to last message"

key-files:
  created:
    - apps/mobile/lib/screens/value_plays_screen.dart
    - apps/mobile/lib/screens/copilot_screen.dart
    - apps/mobile/lib/widgets/alpha_badge_widget.dart
    - apps/mobile/lib/widgets/log_bet_sheet.dart
  modified:
    - apps/mobile/lib/screens/bankroll_screen.dart
    - apps/mobile/lib/services/api_service.dart

key-decisions:
  - "Screen-local ApiService instance instead of Provider.of<ApiService> — avoids Provider registration while keeping API calls clean"
  - "Dismissible confirmDismiss returns false to show LogBetSheet without removing card — preserves feed state"
  - "Kelly suggestion = alphaScore * 20 as simplified proxy (actual bankroll from portfolio deferred)"
  - "bankroll_screen renamed conceptually to Portfolio screen — displays portfolio metrics from /api/v1/users/{id}/portfolio"

patterns-established:
  - "SSE: http.Request + http.Client().send() + StreamedResponse.stream.transform(utf8.decoder).transform(LineSplitter)"
  - "Swipe-to-log: Dismissible(direction: startToEnd) + showModalBottomSheet(isScrollControlled: true)"

requirements-completed: [MOB-01, MOB-02, MOB-03]

# Metrics
duration: 4min
completed: 2026-03-14
---

# Phase 4 Plan 06: Flutter Core Screens Summary

**Alpha-ranked feed with swipe-to-log (MOB-01), BettingCopilot SSE streaming chat (MOB-02), and portfolio performance screen with ROI/CLV/drawdown/active-bets (MOB-03)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-14T06:34:14Z
- **Completed:** 2026-03-14T06:37:44Z
- **Tasks:** 2 (+ 1 checkpoint)
- **Files modified:** 6

## Accomplishments
- Feed screen uses getValuePlaysV1() with auth token; each card wrapped in Dismissible (swipe-right) that opens LogBetSheet pre-filled with Kelly stake and book
- AlphaBadgeWidget renders PREMIUM/HIGH/MEDIUM/SPECULATIVE with correct brand colors
- CopilotScreen streams SSE tokens progressively via http.Client.send() + LineSplitter, appending to last assistant message
- BankrollScreen replaced with portfolio-first layout: calls getPortfolio(userId, token), displays roi/win_rate/clv_average/drawdown/active_bets in a stat grid + active bets list
- Added ApiService.baseUrl static getter needed by CopilotScreen for SSE URI construction

## Task Commits

Each task was committed atomically:

1. **Task 1: Feed screen with swipe-to-log + alpha badge widget** - `120116c` (feat)
2. **Task 2: Copilot SSE chat screen + portfolio screen** - `c316bd7` (feat)

**Plan metadata:** (docs commit pending checkpoint resolution)

## Files Created/Modified
- `apps/mobile/lib/screens/value_plays_screen.dart` - Rebuilt to use ValuePlayV1 + getValuePlaysV1(), Dismissible swipe-to-log, AlphaBadgeWidget per card
- `apps/mobile/lib/widgets/alpha_badge_widget.dart` - Created: pill badge with 4 badge levels and brand colors
- `apps/mobile/lib/widgets/log_bet_sheet.dart` - Created: modal bottom sheet pre-filled with Kelly stake (alphaScore*20) and book; Confirm button returns stake/book map
- `apps/mobile/lib/screens/copilot_screen.dart` - Created: BettingCopilot with SSE streaming, token-by-token progressive rendering
- `apps/mobile/lib/screens/bankroll_screen.dart` - Updated: now calls getPortfolio() with userId+token; shows ROI, Win Rate, CLV Average, Max Drawdown, Active Bets
- `apps/mobile/lib/services/api_service.dart` - Added `static String get baseUrl` getter

## Decisions Made
- Screen-local `final _apiService = ApiService()` pattern chosen over `context.read<ApiService>()` because ApiService is not registered as a Provider — avoids adding unnecessary Provider registration
- `confirmDismiss` returns `false` so swiping opens the LogBetSheet without permanently removing the card from the feed
- Kelly stake pre-fill uses `alphaScore * 20` as a simplified proxy until actual bankroll from portfolio is wired in a future plan

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed withOpacity deprecation warnings in new files**
- **Found during:** Task 2 (flutter analyze verification)
- **Issue:** `withOpacity()` deprecated in favor of `withValues(alpha:)` in Flutter 3.x
- **Fix:** Replaced all `withOpacity()` calls in alpha_badge_widget.dart and value_plays_screen.dart
- **Files modified:** apps/mobile/lib/widgets/alpha_badge_widget.dart, apps/mobile/lib/screens/value_plays_screen.dart
- **Verification:** flutter analyze: 0 errors after fix
- **Committed in:** c316bd7 (Task 2 commit)

**2. [Rule 2 - Missing Critical] Added null-guard on _scrollCtrl.hasClients before jumpTo**
- **Found during:** Task 2 (copilot_screen.dart implementation)
- **Issue:** Plan code called `_scrollCtrl.jumpTo(...)` without checking hasClients — would throw if called before ListView renders
- **Fix:** Added `if (_scrollCtrl.hasClients)` guard before scroll jump
- **Files modified:** apps/mobile/lib/screens/copilot_screen.dart
- **Verification:** No runtime crash path exists for early scroll
- **Committed in:** c316bd7 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug fix, 1 missing critical guard)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
None significant. `_kCard` unused constant removed from copilot_screen.dart (lint cleanup). Pre-existing `use_build_context_synchronously` in login_screen.dart is out of scope.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- MOB-01/MOB-02/MOB-03 screens built and ready for human verification via flutter run
- Awaiting checkpoint verification before proceeding to plan 04-07 (auth/biometric integration)
- Note: copilot_screen.dart does not yet attach auth token to SSE request — will be added in auth integration plan

---
*Phase: 04-api-layer-front-ends*
*Completed: 2026-03-14*
