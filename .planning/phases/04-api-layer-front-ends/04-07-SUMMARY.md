---
phase: 04-api-layer-front-ends
plan: "07"
subsystem: mobile-push-notifications
tags: [fcm, push-notifications, flutter, fastapi, firebase-admin, mob-04]
dependency_graph:
  requires: [04-02, 04-05, 04-06]
  provides: [fcm-push-before-discord, device-token-registration, flutter-notification-service]
  affects: [apps/bot, apps/mobile, apps/webhook_server]
tech_stack:
  added: [firebase-admin>=6.5, firebase_messaging (Flutter), flutter_local_notifications (Flutter)]
  patterns: [FCM v1 HTTP API via firebase-admin SDK, upsert on conflict for idempotent token registration, fail-silent FCM dispatch]
key_files:
  created:
    - apps/webhook_server/src/sharpedge_webhooks/routes/v1/notifications.py
    - apps/mobile/lib/services/notification_service.dart
  modified:
    - apps/bot/src/sharpedge_bot/jobs/value_scanner_job.py
    - apps/bot/pyproject.toml
    - apps/webhook_server/src/sharpedge_webhooks/main.py
    - apps/webhook_server/tests/unit/api/test_device_token.py
    - apps/mobile/lib/main.dart
decisions:
  - monkeypatch env vars in test_device_token rather than os.environ.get fallback — keeps production code strict and test setup explicit
  - module-level create_client import in notifications.py enables clean unittest.mock.patch target
  - _fcm_logger separate from existing logger in value_scanner_job — avoids confusion between job logger and FCM subsystem logger
  - registerToken called via addPostFrameCallback in _ShellState.initState — avoids context access before widget tree is built
metrics:
  duration_seconds: 281
  completed_date: "2026-03-14"
  tasks_completed: 2
  files_created: 2
  files_modified: 5
---

# Phase 4 Plan 07: FCM Push Notifications Summary

**One-liner:** FCM push via firebase-admin fires before Discord dispatch for PREMIUM/HIGH alpha plays; Flutter app registers device token on startup via POST /api/v1/users/{id}/device-token.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | FCM dispatch before Discord + device-token endpoint | 761747f | value_scanner_job.py, notifications.py, main.py, test_device_token.py, pyproject.toml |
| 2 | Flutter NotificationService + token registration on startup | 93bddf3 | notification_service.dart, main.dart |

## What Was Built

### Task 1: Backend FCM + Device Token Endpoint

**value_scanner_job.py** — Added `send_fcm_notifications_for_play()` helper (lines 31–138) and inserted it at the alert queue point (line 336) before `_pending_value_alerts.append(play)`. FCM fires for PREMIUM (alpha >= 0.85) and HIGH (alpha >= 0.70) plays only. Fails silently to never block Discord dispatch. Uses firebase-admin SDK with `FIREBASE_SERVICE_ACCOUNT_PATH` env var. Fetches tokens from `user_device_tokens` table via Supabase service_role key. File stays at 491 lines (under 500 limit).

**routes/v1/notifications.py** — New file with `POST /api/v1/users/{user_id}/device-token` endpoint. Requires auth, validates user owns their own token (403 on mismatch), validates platform is 'ios' or 'android' (422 otherwise), upserts to `user_device_tokens` with `on_conflict="user_id,fcm_token"`.

**main.py** — `v1_notifications_router` imported and registered with `/api/v1` prefix.

**test_device_token.py** — Replaced RED stubs with 2 real TestClient tests: 201 on success (patched supabase client), 401 without auth (dependency override removed). `monkeypatch.setenv` provides required env vars without production code changes.

### Task 2: Flutter NotificationService

**notification_service.dart** — Static `initialize()` sets up background handler (`@pragma('vm:entry-point')`), creates Android channel `sharp_alerts` (Importance.max), requests iOS APNs permissions (alert/badge/sound), listens for foreground messages and shows them via `flutter_local_notifications`. Static `registerToken()` gets FCM token, detects platform via `dart:io Platform.isIOS`, POSTs to `/api/v1/users/{id}/device-token` with auth header. Fails silently on any error.

**main.dart** — `NotificationService.initialize()` called in `main()` after `Supabase.initialize()`. `_ShellState.initState()` added to call `registerToken()` via `addPostFrameCallback` (ensures context and auth state are available).

## Verification Results

- `uv run pytest tests/unit/api/test_device_token.py -x -q`: 2 passed
- `uv run pytest tests/unit/api/ -q`: 18 passed (all passing, no regressions)
- `flutter analyze --no-fatal-infos`: 5 warnings (all pre-existing, none in new files)
- FCM fires at line 336 before Discord queue at line 337 in value_scanner_job.py

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_device_token.py needed monkeypatch for SUPABASE_URL**
- **Found during:** Task 1 test verification
- **Issue:** `os.environ["SUPABASE_URL"]` raised `KeyError` in test environment even with patched `create_client`; env var access happens before the mock intercepts
- **Fix:** Added `monkeypatch.setenv("SUPABASE_URL", ...)` and `monkeypatch.setenv("SUPABASE_SERVICE_KEY", ...)` to `test_device_token_register_success` parameter list
- **Files modified:** `apps/webhook_server/tests/unit/api/test_device_token.py`
- **Commit:** 761747f (part of Task 1 commit)

**2. [Rule 1 - Bug] notifications.py needed module-level create_client import for mockability**
- **Found during:** Task 1 test verification
- **Issue:** `from supabase import create_client` inside the function body made `patch("sharpedge_webhooks.routes.v1.notifications.create_client")` fail with AttributeError since the name wasn't in the module namespace
- **Fix:** Moved `from supabase import create_client` to module-level import in `notifications.py`
- **Files modified:** `apps/webhook_server/src/sharpedge_webhooks/routes/v1/notifications.py`
- **Commit:** 761747f (part of Task 1 commit)

## Self-Check: PASSED
