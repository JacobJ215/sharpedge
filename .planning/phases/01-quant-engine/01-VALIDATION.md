---
phase: 1
slug: quant-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.24 + pytest-mock 3.14 |
| **Config file** | `pyproject.toml` (root — already configured) |
| **Quick run command** | `uv run pytest tests/unit/models/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~10 seconds (unit only, no I/O) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/models/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| debt-fix | 01 | 0 | QUANT-02,05 | unit | `uv run pytest tests/unit/models/test_backtesting.py -x -q` | ❌ W0 | ⬜ pending |
| alpha-composer | 01 | 1 | QUANT-01 | unit | `uv run pytest tests/unit/models/test_alpha.py -x -q` | ❌ W0 | ⬜ pending |
| monte-carlo | 01 | 1 | QUANT-02 | unit | `uv run pytest tests/unit/models/test_monte_carlo.py -x -q` | ❌ W0 | ⬜ pending |
| regime-detector | 01 | 1 | QUANT-03 | unit | `uv run pytest tests/unit/models/test_regime.py -x -q` | ❌ W0 | ⬜ pending |
| key-numbers | 01 | 1 | QUANT-04 | unit | `uv run pytest tests/unit/analytics/test_key_numbers.py -x -q` | ❌ W0 | ⬜ pending |
| walk-forward | 01 | 2 | QUANT-05 | unit | `uv run pytest tests/unit/models/test_walk_forward.py -x -q` | ❌ W0 | ⬜ pending |
| clv-tracking | 01 | 2 | QUANT-06 | unit | `uv run pytest tests/unit/models/test_clv.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — package init
- [ ] `tests/unit/__init__.py` — unit package
- [ ] `tests/unit/models/__init__.py` — models package
- [ ] `tests/unit/analytics/__init__.py` — analytics package
- [ ] `tests/conftest.py` — shared fixtures (sample game data, mock odds)
- [ ] `tests/unit/models/test_alpha.py` — stubs for QUANT-01
- [ ] `tests/unit/models/test_monte_carlo.py` — stubs for QUANT-02
- [ ] `tests/unit/models/test_regime.py` — stubs for QUANT-03
- [ ] `tests/unit/analytics/test_key_numbers.py` — stubs for QUANT-04
- [ ] `tests/unit/models/test_walk_forward.py` — stubs for QUANT-05
- [ ] `tests/unit/models/test_clv.py` — stubs for QUANT-06
- [ ] `tests/unit/models/test_backtesting.py` — stubs for debt-fix coverage

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Discord alert shows alpha badge (PREMIUM/HIGH/MEDIUM/SPECULATIVE) | QUANT-01 | Requires Discord bot running + live odds | Run bot locally, trigger `/value` command, verify badge appears on alert |
| Monte Carlo fan chart renders in expected format | QUANT-02 | Chart output is visual | Call `MonteCarloSimulator.simulate_bankroll()`, inspect returned paths structure |
| CLV updates after game closes | QUANT-06 | Requires Supabase write + game resolution event | Manually trigger `update_clv_after_close()` with test bet, verify `closing_line_value` column updated |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
