---
phase: 12
slug: live-kalshi-execution
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.24 (asyncio_mode = "auto") |
| **Config file** | `packages/venue_adapters/pyproject.toml` — `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_live_execution_engine.py -x -q` |
| **Full suite command** | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_live_execution_engine.py -x -q`
- **After every plan wave:** Run `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 0 | EXEC-03, EXEC-05 | unit stub | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_live_execution_engine.py -x -q` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 1 | EXEC-03 | unit | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_live_execution_engine.py::test_live_mode_calls_create_order -x -q` | ❌ W0 | ⬜ pending |
| 12-01-03 | 01 | 1 | EXEC-03 | unit | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_live_execution_engine.py::test_shadow_mode_unchanged -x -q` | ❌ W0 | ⬜ pending |
| 12-01-04 | 01 | 1 | EXEC-03 | unit | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_live_execution_engine.py::test_live_mode_exposure_guard_still_applied -x -q` | ❌ W0 | ⬜ pending |
| 12-02-01 | 02 | 1 | EXEC-05 | unit | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_live_execution_engine.py::test_fill_event_recorded -x -q` | ❌ W0 | ⬜ pending |
| 12-02-02 | 02 | 1 | EXEC-05 | unit | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_live_execution_engine.py::test_cancel_event_recorded -x -q` | ❌ W0 | ⬜ pending |
| 12-02-03 | 02 | 1 | EXEC-05 | unit | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_live_execution_engine.py::test_fill_on_first_poll -x -q` | ❌ W0 | ⬜ pending |
| 12-02-04 | 02 | 2 | EXEC-03, EXEC-05 | integration | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_live_execution_engine.py::test_full_live_flow -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/venue_adapters/tests/test_live_execution_engine.py` — all RED stubs for EXEC-03, EXEC-05 (new file)
- [ ] `packages/data_feeds/src/sharpedge_feeds/kalshi_client.py` — add `get_order(order_id)` method (required for poll loop)
- [ ] `packages/venue_adapters/tests/conftest.py` — extend with mock KalshiClient fixture if needed

*Existing pytest + pytest-asyncio infrastructure in venue_adapters covers all phase requirements — no new install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real Kalshi order submission | EXEC-03 | Requires live KALSHI_API_KEY + KALSHI_PRIVATE_KEY_PATH and real capital | Set `ENABLE_KALSHI_EXECUTION=true`, `KALSHI_API_KEY`, `KALSHI_PRIVATE_KEY_PATH`; run engine with a low-value OrderIntent; verify order appears in Kalshi portfolio |
| Real fill detection via polling | EXEC-05 | Requires a live order to be matched on Kalshi CLOB | Follow EXEC-03 manual test; wait for fill; verify FILL entry in SettlementLedger |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
