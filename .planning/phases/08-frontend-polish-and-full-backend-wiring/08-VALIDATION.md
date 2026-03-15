---
phase: 8
slug: frontend-polish-and-full-backend-wiring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend), vitest (Next.js), flutter test (mobile) |
| **Config file** | `pyproject.toml` (pytest), `apps/web/vitest.config.ts`, `apps/mobile/pubspec.yaml` |
| **Quick run command** | `uv run pytest tests/integration/ -q` |
| **Full suite command** | `uv run pytest tests/ -q && cd apps/web && npm test -- --run && cd ../mobile && flutter test` |
| **Estimated runtime** | ~90 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/integration/ -q`
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 08-01-01 | 01 | 0 | WIRE-01 | unit/integration stub | `uv run pytest tests/integration/test_auth_wiring.py -q` | ⬜ pending |
| 08-02-01 | 02 | 1 | WIRE-01 | integration | `uv run pytest tests/integration/test_auth_wiring.py -q` | ⬜ pending |
| 08-02-02 | 02 | 1 | WIRE-03 | integration | `uv run pytest tests/integration/test_rls_endpoints.py -q` | ⬜ pending |
| 08-03-01 | 03 | 2 | WIRE-02 | component test | `cd apps/web && npm test -- --run src/components/venue` | ⬜ pending |
| 08-04-01 | 04 | 2 | WIRE-04 | flutter test | `cd apps/mobile && flutter test test/api_service_test.dart` | ⬜ pending |
| 08-05-01 | 05 | 3 | WIRE-05 | integration | `uv run pytest tests/integration/test_fcm_dispatch.py -q` | ⬜ pending |
| 08-06-01 | 06 | 3 | WIRE-06 | integration | `uv run pytest tests/integration/test_copilot_tools_e2e.py -q` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/integration/test_auth_wiring.py` — stubs for WIRE-01 (web auth, JWT in all calls)
- [ ] `tests/integration/test_rls_endpoints.py` — stubs for WIRE-03 (RLS with real JWT, not service_role)
- [ ] `tests/integration/test_fcm_dispatch.py` — stubs for WIRE-05 (FCM fires before Discord)
- [ ] `tests/integration/test_copilot_tools_e2e.py` — stubs for WIRE-06 (all 12 tools reachable)
- [ ] `apps/web/src/components/venue/__tests__/VenueDislocWidget.test.tsx` — stub for WIRE-02

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Biometric auth (Face ID / fingerprint) on Flutter | WIRE-04 | Requires physical device, can't run in emulator | 1. Build release APK/IPA 2. Install on real device 3. Login → verify biometric prompt appears |
| FCM push received before Discord message | WIRE-05 | Push delivery timing requires real FCM token on device | 1. Login on device to register FCM token 2. Trigger a PREMIUM alpha play 3. Confirm push notification arrives before Discord message in channel |
| SSE streaming from Flutter mobile | WIRE-06 | Flutter SSE client requires real HTTP connection | 1. Open BettingCopilot chat in mobile app 2. Send query 3. Verify tokens stream in real time |
| Offline feed caching in Flutter | WIRE-04 | Requires disabling network mid-session | 1. Load app and let feed populate 2. Disable airplane mode 3. Verify last feed is visible without error |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
