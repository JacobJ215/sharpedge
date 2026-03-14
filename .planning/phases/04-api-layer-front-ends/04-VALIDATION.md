---
phase: 4
slug: api-layer-front-ends
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (Python)** | pytest 7.x (existing) |
| **Framework (Next.js)** | vitest + @testing-library/react (Wave 0 installs) |
| **Config file** | `pyproject.toml` (Python), `apps/web/vitest.config.ts` (Wave 0) |
| **Quick run command (API)** | `cd apps/webhook_server && uv run pytest tests/unit/ -x -q` |
| **Full suite command (API)** | `uv run pytest tests/ -q` |
| **Quick run command (Web)** | `cd apps/web && npm test -- --run` |
| **Estimated runtime** | ~15 seconds (Python), ~10 seconds (Next.js) |

---

## Sampling Rate

- **After every task commit:** Run quick command for the affected layer (Python or Next.js)
- **After every plan wave:** Run full suites for all layers touched in that wave
- **Before `/gsd:verify-work`:** Full suite must be green across all layers
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | API-06 | integration | `uv run pytest tests/unit/api/test_rls.py -x -q` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | API-01 | unit | `uv run pytest tests/unit/api/test_value_plays_v1.py -x -q` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | API-02 | unit | `uv run pytest tests/unit/api/test_game_analysis.py -x -q` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | API-03 | unit | `uv run pytest tests/unit/api/test_copilot_sse.py -x -q` | ❌ W0 | ⬜ pending |
| 04-01-05 | 01 | 1 | API-04 | unit | `uv run pytest tests/unit/api/test_portfolio.py -x -q` | ❌ W0 | ⬜ pending |
| 04-01-06 | 01 | 1 | API-05 | unit | `uv run pytest tests/unit/api/test_bankroll_simulate.py -x -q` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | WEB-01 | unit | `cd apps/web && npm test -- --run src/components/dashboard` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | WEB-02 | unit | `cd apps/web && npm test -- --run src/components/value-plays` | ❌ W0 | ⬜ pending |
| 04-02-03 | 02 | 2 | WEB-03 | unit | `cd apps/web && npm test -- --run src/components/game-detail` | ❌ W0 | ⬜ pending |
| 04-02-04 | 02 | 2 | WEB-04 | unit | `cd apps/web && npm test -- --run src/components/bankroll` | ❌ W0 | ⬜ pending |
| 04-02-05 | 02 | 2 | WEB-05 | unit | `cd apps/web && npm test -- --run src/components/copilot` | ❌ W0 | ⬜ pending |
| 04-02-06 | 02 | 2 | WEB-06 | unit | `cd apps/web && npm test -- --run src/components/prediction-markets` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 3 | MOB-05 | manual | See manual verification table | N/A | ⬜ pending |
| 04-03-02 | 03 | 3 | MOB-01 | manual | See manual verification table | N/A | ⬜ pending |
| 04-03-03 | 03 | 3 | MOB-02 | manual | See manual verification table | N/A | ⬜ pending |
| 04-03-04 | 03 | 3 | MOB-03 | manual | See manual verification table | N/A | ⬜ pending |
| 04-03-05 | 03 | 3 | MOB-04 | manual | See manual verification table | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/api/__init__.py` — API test package init
- [ ] `tests/unit/api/test_rls.py` — RED stubs for API-06 RLS enforcement (user_id isolation)
- [ ] `tests/unit/api/test_value_plays_v1.py` — RED stubs for API-01 (min_alpha filter, alpha_badge in response)
- [ ] `tests/unit/api/test_game_analysis.py` — RED stubs for API-02 (game analysis route)
- [ ] `tests/unit/api/test_copilot_sse.py` — RED stubs for API-03 (SSE response headers, streaming)
- [ ] `tests/unit/api/test_portfolio.py` — RED stubs for API-04 (portfolio response shape)
- [ ] `tests/unit/api/test_bankroll_simulate.py` — RED stubs for API-05 (Monte Carlo response)
- [ ] `apps/web/` — Next.js 14 project scaffold (`npx create-next-app@14 --typescript --tailwind --app`)
- [ ] `apps/web/vitest.config.ts` — vitest config for React component testing
- [ ] `apps/web/src/components/` — component stub files for each WEB-* requirement
- [ ] Supabase migration: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` for all tables + policies
- [ ] Supabase migration: `CREATE TABLE user_device_tokens (...)` for MOB-04 FCM tokens

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Swipe-right bottom sheet pre-fills Kelly stake | MOB-01 | Flutter UI interaction | Run app on simulator, swipe right on value play, verify bottom sheet appears with stake pre-filled |
| BettingCopilot SSE streams tokens in real-time | MOB-02, WEB-05 | Live SSE streaming | Open copilot, send query, verify tokens appear progressively (not all at once) |
| Face ID / fingerprint blocks app entry | MOB-05 | Device biometric auth | Launch app on device, verify biometric prompt appears before any screen loads |
| FCM push fires before Discord alert | MOB-04 | Cross-system timing | Trigger value scan with PREMIUM play, verify phone notification arrives before Discord message |
| RLS blocks cross-user data access | API-06 | Live Supabase instance | Authenticate as User A, attempt to fetch User B's portfolio by ID, verify 403/empty |
| BettingCopilot streams concurrent requests | API-03 | Concurrent load | Open 2 browser tabs on copilot, submit queries simultaneously, verify both stream independently |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
