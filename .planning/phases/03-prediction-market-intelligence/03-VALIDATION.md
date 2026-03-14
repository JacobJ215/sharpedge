---
phase: 3
slug: prediction-market-intelligence
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0 + pytest-asyncio 0.24 + pytest-mock 3.14 |
| **Config file** | pyproject.toml (no separate pytest.ini) |
| **Quick run command** | `python -m pytest tests/unit/analytics/ -x -q` |
| **Full suite command** | `python -m pytest tests/unit/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/unit/analytics/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/unit/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 0 | PM-01, PM-02 | unit | `python -m pytest tests/unit/analytics/test_pm_edge_scanner.py -x -q` | ❌ W0 | ⬜ pending |
| 3-01-02 | 01 | 0 | PM-03 | unit | `python -m pytest tests/unit/analytics/test_pm_regime.py -x -q` | ❌ W0 | ⬜ pending |
| 3-01-03 | 01 | 0 | PM-04 | unit | `python -m pytest tests/unit/analytics/test_pm_correlation.py -x -q` | ❌ W0 | ⬜ pending |
| 3-02-01 | 02 | 1 | PM-01, PM-02 | unit | `python -m pytest tests/unit/analytics/test_pm_edge_scanner.py -x -q` | ✅ W0 | ⬜ pending |
| 3-02-02 | 02 | 1 | PM-03 | unit | `python -m pytest tests/unit/analytics/test_pm_regime.py -x -q` | ✅ W0 | ⬜ pending |
| 3-03-01 | 03 | 2 | PM-04 | unit | `python -m pytest tests/unit/analytics/test_pm_correlation.py -x -q` | ✅ W0 | ⬜ pending |
| 3-03-02 | 03 | 2 | PM-04 | integration | `python -m pytest tests/unit/analytics/test_pm_edge_scanner.py::test_correlation_warning_order -x` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/analytics/test_pm_edge_scanner.py` — RED stubs for PM-01, PM-02, correlation warning order
- [ ] `tests/unit/analytics/test_pm_regime.py` — RED stubs for PM-03 (all 5 regime states, threshold adjustment)
- [ ] `tests/unit/analytics/test_pm_correlation.py` — RED stubs for PM-04 (token overlap detection, >0.6 threshold)
- [ ] `tests/unit/analytics/__init__.py` — already exists (no gap)

*No new framework install required — pytest already configured.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PM edge appears in Discord with `[PM]` label prefix | PM-01, PM-02 | Requires live Discord bot + API credentials | Trigger scanner job manually; verify embed has PM prefix and alpha badge |
| Correlation warning embed appears BEFORE the correlated alert | PM-04 | Message ordering in Discord requires visual inspection | Log multiple correlated positions, trigger scan, verify warning precedes alert |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
