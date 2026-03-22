---
phase: copilot-commercial-04
slug: copilot-commercial-04
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-03-22
---

# Phase copilot-commercial-04 — Validation Strategy

> Validation contract for SSE tool transparency (webhook + web + mobile).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (Python), Dart analyzer (Flutter) |
| **Config file** | `apps/webhook_server` pytest via monorepo root `uv run pytest` |
| **Quick run command** | `uv run pytest apps/webhook_server/tests/unit/api/test_copilot_sse.py -q` |
| **Full suite command** | `uv run pytest apps/webhook_server/tests/unit/api/test_copilot_sse.py packages/agent_pipeline/tests/ -q` (adjust if new unit tests added) |
| **Estimated runtime** | ~60s (includes slow tool-json tests if run together) |

---

## Sampling Rate

- **After server SSE changes:** Run quick copilot SSE command.
- **After web/mobile changes:** `dart analyze` on touched Dart files; no full Flutter test gate required unless widgets tested.
- **Before merge:** Quick pytest target + manual one-turn copilot smoke (optional but recommended in UAT).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 04-01-0 | 01 | 1 | Event names documented | manual grep | `grep -n on_tool apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py` | ⬜ pending |
| 04-01-1 | 01 | 1 | SSE contract | unit | `uv run pytest apps/webhook_server/tests/unit/api/test_copilot_sse.py -q` | ⬜ pending |
| 04-01-3 | 01 | 1 | Web parser | lint/build | `npm run lint` in `apps/web` if configured | ⬜ pending |
| 04-01-4 | 01 | 1 | Mobile | analyzer | `dart analyze apps/mobile/lib/screens/copilot_screen.dart` | ⬜ pending |

---

## Wave 0 Requirements

- [x] Existing `test_copilot_sse.py` — extend for new SSE event types
- [x] No new global test framework required

---

## Manual-Only Verifications

| Behavior | Why manual | Test instructions |
|----------|------------|---------------------|
| Steps UI matches real tool run | Requires OpenAI + Odds/DB env | Sign in, ask a question that triggers `search_games` or `get_active_bets`; confirm Steps list and clean markdown. |

---

## Validation Sign-Off

- [ ] `test_copilot_sse.py` green after SSE refactor
- [ ] `dart analyze` clean for `copilot_screen.dart`
- [ ] `nyquist_compliant: true` after execution wave complete

**Approval:** pending
