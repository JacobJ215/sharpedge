---
phase: 04-api-layer-front-ends
plan: "05"
subsystem: auth
tags: [flutter, dart, local_auth, supabase, firebase_messaging, biometrics, mobile]

# Dependency graph
requires:
  - phase: 04-api-layer-front-ends/04-00
    provides: FastAPI v1 routes including /api/v1/value-plays, /api/v1/users/{id}/portfolio, /api/v1/bankroll/simulate
provides:
  - Flutter biometric auth gate (Face ID / fingerprint via local_auth)
  - AuthService with Supabase sign-in + biometric challenge
  - LoginScreen with email/password form + biometric prompt post sign-in
  - ApiService v1 methods: getValuePlaysV1(), getPortfolio(), simulateBankroll()
  - AppState auth state: isAuthenticated, userId, authToken, setAuthenticated(), clearAuth()
  - ValuePlayV1 model with alphaScore, alphaBadge, regimeState fields
affects:
  - 04-06 (value plays screen uses getValuePlaysV1 + AppState.authToken)
  - 04-07 (copilot screen needs auth state)
  - 04-08 (portfolio screen uses getPortfolio + AppState.userId)

# Tech tracking
tech-stack:
  added:
    - local_auth ^2.3.0 (Face ID / fingerprint biometrics)
    - firebase_messaging ^15.1.0 (FCM push notifications)
    - flutter_local_notifications ^17.2.4 (local notification display)
    - supabase_flutter ^2.6.0 (Supabase auth client)
  patterns:
    - Supabase sign-in then biometric challenge before setting AppState.isAuthenticated
    - AuthService wraps local_auth and supabase_flutter behind clean interface
    - ApiService v1 methods use _baseUrlV1 = baseUrl + /api/v1 static getter
    - Bearer token passed as named param to v1 API methods

key-files:
  created:
    - apps/mobile/lib/services/auth_service.dart
    - apps/mobile/lib/screens/login_screen.dart
  modified:
    - apps/mobile/pubspec.yaml
    - apps/mobile/lib/services/api_service.dart
    - apps/mobile/lib/providers/app_state.dart
    - apps/mobile/lib/models/value_play.dart

key-decisions:
  - "ValuePlayV1 added to value_play.dart alongside ValuePlay to avoid new model file"
  - "biometricOnly: false allows PIN fallback so users without enrolled biometrics can proceed"
  - "isBiometricAvailable() check gates biometric prompt — devices without hardware bypass it"

patterns-established:
  - "AuthService pattern: supabase sign-in then local_auth challenge, PlatformException caught silently"
  - "ApiService v1 pattern: static _baseUrlV1 getter, token passed as optional named param"
  - "AppState auth pattern: setAuthenticated() / clearAuth() with notifyListeners()"

requirements-completed: [MOB-05]

# Metrics
duration: 2min
completed: 2026-03-14
---

# Phase 4 Plan 05: Flutter Biometric Auth + ApiService v1 Methods Summary

**Supabase sign-in with local_auth biometric gate (Face ID / fingerprint), v1 API client methods for alpha-enriched value plays, portfolio, and bankroll simulation.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-14T06:28:20Z
- **Completed:** 2026-03-14T06:30:22Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Added local_auth, firebase_messaging, flutter_local_notifications, supabase_flutter to pubspec.yaml
- Built AuthService with Supabase email/password sign-in and biometric challenge (Face ID / fingerprint / PIN fallback)
- Built LoginScreen that enforces biometric gate after Supabase auth, signs out + shows error on failure
- Extended ApiService with v1 methods: getValuePlaysV1(), getPortfolio(), simulateBankroll() all using /api/v1 base
- Added auth state to AppState: isAuthenticated, userId, authToken, setAuthenticated(), clearAuth()
- Added ValuePlayV1 model with alphaScore, alphaBadge, regimeState to value_play.dart

## Task Commits

Each task was committed atomically:

1. **Task 1: pubspec.yaml + AuthService with Supabase + local_auth biometrics** - `4b161cb` (feat)
2. **Task 2: LoginScreen + ApiService v1 methods + app_state auth integration** - `c6c5d6c` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `apps/mobile/pubspec.yaml` - Added local_auth, firebase_messaging, flutter_local_notifications, supabase_flutter
- `apps/mobile/lib/services/auth_service.dart` - New: Supabase sign-in, biometric auth, isSignedIn, currentToken
- `apps/mobile/lib/screens/login_screen.dart` - New: email/password form, biometric gate, AppState.setAuthenticated on success
- `apps/mobile/lib/services/api_service.dart` - Added _baseUrlV1 getter + getValuePlaysV1(), getPortfolio(), simulateBankroll()
- `apps/mobile/lib/providers/app_state.dart` - Added _isAuthenticated, _userId, _authToken fields + setAuthenticated(), clearAuth()
- `apps/mobile/lib/models/value_play.dart` - Added ValuePlayV1 class with alphaScore, alphaBadge, regimeState

## Decisions Made
- ValuePlayV1 appended to value_play.dart alongside existing ValuePlay (avoids new file, keeps model co-located)
- `biometricOnly: false` allows PIN fallback so users without enrolled biometrics can still authenticate
- `isBiometricAvailable()` bypasses biometric prompt entirely on devices with no biometric hardware

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required in this plan. Supabase and Firebase credentials are environment-configured at app build time.

## Next Phase Readiness
- Auth gate and v1 API layer ready for Wave 3 screens (value plays feed, copilot, portfolio)
- Wave 3 plans (04-06, 04-07, 04-08) can now consume AppState.authToken and getValuePlaysV1()
- No blockers

---
*Phase: 04-api-layer-front-ends*
*Completed: 2026-03-14*
