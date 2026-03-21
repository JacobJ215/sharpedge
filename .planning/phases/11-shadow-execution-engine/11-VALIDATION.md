---
phase: 11
slug: shadow-execution-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.24 |
| **Config file** | `packages/venue_adapters/pyproject.toml` (asyncio_mode=auto confirmed) |
| **Quick run command** | `pytest packages/venue_adapters/tests/test_execution_engine.py -x -q` |
| **Full suite command** | `pytest packages/venue_adapters/tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest packages/venue_adapters/tests/test_execution_engine.py -x -q`
- **After every plan wave:** Run `pytest packages/venue_adapters/tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 0 | EXEC-01, EXEC-02 | unit stub | `pytest packages/venue_adapters/tests/test_execution_engine.py -x -q` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | EXEC-02 | unit | `pytest packages/venue_adapters/tests/test_execution_engine.py::test_shadow_ledger_entry -x -q` | ❌ W0 | ⬜ pending |
| 11-01-03 | 01 | 1 | EXEC-02 | unit | `pytest packages/venue_adapters/tests/test_execution_engine.py::test_shadow_ledger_append -x -q` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 0 | EXEC-04 | unit stub | `pytest packages/venue_adapters/tests/test_exposure_guards.py -x -q` | ❌ W0 | ⬜ pending |
| 11-02-02 | 02 | 1 | EXEC-04 | unit | `pytest packages/venue_adapters/tests/test_exposure_guards.py::test_market_guard_reject -x -q` | ❌ W0 | ⬜ pending |
| 11-02-03 | 02 | 1 | EXEC-04 | unit | `pytest packages/venue_adapters/tests/test_exposure_guards.py::test_day_guard_reject -x -q` | ❌ W0 | ⬜ pending |
| 11-02-04 | 02 | 1 | EXEC-04 | unit | `pytest packages/venue_adapters/tests/test_exposure_guards.py::test_reject_before_ledger_write -x -q` | ❌ W0 | ⬜ pending |
| 11-03-01 | 03 | 1 | EXEC-01 | unit | `pytest packages/venue_adapters/tests/test_execution_engine.py::test_shadow_mode_no_kalshi_calls -x -q` | ❌ W0 | ⬜ pending |
| 11-03-02 | 03 | 2 | EXEC-01, EXEC-02, EXEC-04 | integration | `pytest packages/venue_adapters/tests/test_execution_engine.py::test_full_signal_flow -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/venue_adapters/tests/test_execution_engine.py` — stubs for EXEC-01, EXEC-02 (ShadowLedger, ShadowExecutionEngine)
- [ ] `packages/venue_adapters/tests/test_exposure_guards.py` — stubs for EXEC-04 (MarketExposureGuard, DayExposureGuard, reject-before-write)
- [ ] `packages/venue_adapters/tests/conftest.py` — shared fixtures (mock ExposureBook, sample OrderIntent)

*Existing pytest + pytest-asyncio infrastructure in venue_adapters covers all phase requirements — no new install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Supabase optional persistence for ShadowLedger | EXEC-02 | Requires live Supabase credentials | Set SUPABASE_URL + SUPABASE_SERVICE_KEY, run `python -c "from sharpedge_venue_adapters.execution_engine import ShadowLedger; ..."`, verify row in shadow_ledger table |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
