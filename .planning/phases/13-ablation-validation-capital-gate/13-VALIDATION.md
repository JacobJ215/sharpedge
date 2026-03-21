---
phase: 13
slug: ablation-validation-capital-gate
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.24 (asyncio_mode = "auto") |
| **Config file** | `packages/venue_adapters/pyproject.toml` |
| **Quick run command** | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_capital_gate.py -x -q` |
| **Full suite command** | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_capital_gate.py -x -q`
- **After every plan wave:** Run `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 0 | GATE-01..04 | unit stub | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_capital_gate.py -x -q` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 0 | ABLATE-01/02 | unit stub | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_ablation.py -x -q` | ❌ W0 | ⬜ pending |
| 13-02-01 | 02 | 1 | GATE-01 | unit | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_capital_gate.py::test_gate01_fails_missing_artifact packages/venue_adapters/tests/test_capital_gate.py::test_gate01_passes_all_artifacts -x -q` | ❌ W0 | ⬜ pending |
| 13-02-02 | 02 | 1 | GATE-02 | unit | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_capital_gate.py::test_gate02_fails_insufficient_days packages/venue_adapters/tests/test_capital_gate.py::test_gate02_passes_valid_period -x -q` | ❌ W0 | ⬜ pending |
| 13-02-03 | 02 | 1 | GATE-03 | unit | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_capital_gate.py::test_gate03_fails_no_approval_file packages/venue_adapters/tests/test_capital_gate.py::test_gate03_passes_valid_approval -x -q` | ❌ W0 | ⬜ pending |
| 13-02-04 | 02 | 1 | GATE-04 | unit | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_capital_gate.py::test_gate04_breach_invalidates_approval packages/venue_adapters/tests/test_capital_gate.py::test_gate04_daily_reset -x -q` | ❌ W0 | ⬜ pending |
| 13-02-05 | 02 | 1 | D-01/D-02 | unit | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_capital_gate.py::test_assert_ready_collects_all_failures packages/venue_adapters/tests/test_capital_gate.py::test_assert_ready_raises_capital_gate_error -x -q` | ❌ W0 | ⬜ pending |
| 13-03-01 | 03 | 2 | ABLATE-01/02 | unit | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_ablation.py -x -q` | ❌ W0 | ⬜ pending |
| 13-03-02 | 03 | 2 | GATE-01..04 | integration | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/ -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/venue_adapters/tests/test_capital_gate.py` — RED stubs for GATE-01 through GATE-04 + assert_ready() behavior
- [ ] `packages/venue_adapters/tests/test_ablation.py` — RED stubs for ABLATE-01 and ABLATE-02

*Existing pytest + pytest-asyncio infrastructure in venue_adapters covers all phase requirements — no new install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `approve_live.py` shows full gate table and writes approval token | GATE-03 | Requires interactive terminal prompt | Run `python scripts/approve_live.py`, verify table displays, type operator name, confirm `data/live_approval.json` exists with correct fields |
| Ablation console table renders correctly | ABLATE-01 | Console output verification | Run `python scripts/run_ablation.py`, verify per-category table with PASS/FAIL column and overall result |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
