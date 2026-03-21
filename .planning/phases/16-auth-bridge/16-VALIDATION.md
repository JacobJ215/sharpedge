---
phase: 16
slug: auth-bridge
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (Python webhook), vitest (Next.js), Flutter test |
| **Config file** | `apps/webhook_server/pyproject.toml`, `apps/web/vitest.config.ts` |
| **Quick run command** | `cd apps/webhook_server && uv run pytest tests/test_revenuecat.py tests/test_whop_tier_push.py -x -q` |
| **Full suite command** | `cd apps/webhook_server && uv run pytest -x -q && cd ../../apps/web && npm test -- --run` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 16-01-01 | 01 | 1 | AUTH-01 | migration | `psql $DATABASE_URL -c "\\d public.users"` | ⬜ pending |
| 16-01-02 | 01 | 1 | AUTH-01 | unit | `uv run pytest tests/test_auth_trigger.py -x -q` | ⬜ pending |
| 16-01-03 | 01 | 1 | AUTH-02 | unit | `uv run pytest tests/test_auth_trigger.py::test_rls -x -q` | ⬜ pending |
| 16-02-01 | 02 | 2 | AUTH-04 | unit | `uv run pytest tests/test_whop_tier_push.py -x -q` | ⬜ pending |
| 16-02-02 | 02 | 2 | AUTH-04 | unit | `uv run pytest tests/test_revenuecat.py -x -q` | ⬜ pending |
| 16-02-03 | 02 | 2 | AUTH-04 | manual | Dashboard hook registration | ⬜ pending |
| 16-03-01 | 03 | 3 | AUTH-03 | unit | `npm test -- --run middleware` | ⬜ pending |
| 16-03-02 | 03 | 3 | AUTH-05 | manual | In-app tier display smoke test | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/webhook_server/tests/test_whop_tier_push.py` — stubs for AUTH-04 (Whop → Supabase tier push)
- [ ] `apps/webhook_server/tests/test_revenuecat.py` — stubs for AUTH-04 (RevenueCat → Supabase tier push)
- [ ] `apps/web/src/__tests__/middleware.test.ts` — stubs for AUTH-03 (tier-gated route middleware)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Custom Access Token Hook injects `tier` into JWT | AUTH-04 | Requires Supabase Dashboard UI click to register | 1. Deploy function via migration, 2. Register in Dashboard → Auth → Hooks → Custom Access Token Hook, 3. Sign in as test user, 4. `console.log(session.user.app_metadata.tier)` in browser |
| Whop subscription triggers role upgrade within 30s | AUTH-04 | Requires live Whop test checkout | Use Whop sandbox mode; complete test purchase; verify tier updates in Supabase within 30s |
| Upgrade prompt shown to free user | AUTH-03 | UI behavior requires visual verification | Log in as free user; navigate to a paid feature; confirm upgrade prompt appears (not blank/error) |
| Tier link visible in account page | AUTH-05 | UI component requires visual check | Log in as paid user; navigate to account/settings; confirm tier badge and Whop manage-subscription link are visible |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
