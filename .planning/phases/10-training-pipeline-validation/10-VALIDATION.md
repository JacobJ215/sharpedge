---
phase: 10
slug: training-pipeline-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.24 + pytest-mock 3.14 |
| **Config file** | `pyproject.toml` (pytest section) |
| **Quick run command** | `python -m pytest tests/unit/scripts/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/unit/scripts/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 0 | TRAIN-01 | unit | `pytest tests/unit/scripts/test_download_pm_historical.py -x -q` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 0 | TRAIN-01 | unit | `pytest tests/unit/scripts/test_download_pm_historical.py -x -q` | ❌ W0 | ⬜ pending |
| 10-01-03 | 01 | 0 | TRAIN-01 | unit | `pytest tests/unit/scripts/test_download_pm_historical.py -x -q` | ❌ W0 | ⬜ pending |
| 10-01-04 | 01 | 0 | TRAIN-02 | unit | `pytest tests/unit/scripts/test_process_pm_historical.py -x -q` | ❌ W0 | ⬜ pending |
| 10-01-05 | 01 | 0 | TRAIN-03 | unit | `pytest tests/unit/scripts/test_train_pm_models.py -x -q` | ✅ (xfail) | ⬜ pending |
| 10-01-06 | 01 | 0 | TRAIN-04 | unit | `pytest tests/unit/scripts/test_train_pm_models.py -x -q` | ❌ W0 | ⬜ pending |
| 10-02-01 | 02 | 1 | TRAIN-01 | unit | `pytest tests/unit/scripts/test_download_pm_historical.py -x -q` | ✅ W0 | ⬜ pending |
| 10-02-02 | 02 | 1 | TRAIN-02 | unit | `pytest tests/unit/scripts/test_process_pm_historical.py -x -q` | ✅ W0 | ⬜ pending |
| 10-03-01 | 03 | 1 | TRAIN-03 | unit | `pytest tests/unit/scripts/test_train_pm_models.py -x -q` | ✅ W0 | ⬜ pending |
| 10-03-02 | 03 | 1 | TRAIN-04 | unit | `pytest tests/unit/scripts/test_train_pm_models.py -x -q` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/scripts/test_download_pm_historical.py` — add test: Supabase upsert called when `SUPABASE_URL` is set (mock `supabase.create_client`); covers TRAIN-01 storage migration
- [ ] `tests/unit/scripts/test_download_pm_historical.py` — add test: preflight exits with `SystemExit` when `KALSHI_API_KEY` present but `get_markets` raises; covers TRAIN-01 credential check
- [ ] `tests/unit/scripts/test_download_pm_historical.py` — add test: Polymarket markets with `volume <= 100` are excluded from upsert; covers TRAIN-01 volume filter
- [ ] `tests/unit/scripts/test_process_pm_historical.py` — add test: main() queries Supabase when `SUPABASE_URL` set (mock client); covers TRAIN-02 storage migration
- [ ] `tests/unit/scripts/test_train_pm_models.py` — add test: report entry contains `calibration_score` key when OOF data available; covers TRAIN-04
- [ ] `packages/database/src/sharpedge_db/migrations/006_resolved_pm_markets.sql` — create DDL; required before any Supabase upsert can work

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `download_pm_historical.py` completes full all-time backfill against live Kalshi + Polymarket APIs without error | TRAIN-01 | Requires live API credentials; cursor exhaustion takes minutes | Run `python scripts/download_pm_historical.py`; confirm exit code 0 and record count in log |
| `data/models/pm/` contains `.joblib` files for all categories with >= 200 resolved markets | TRAIN-03 | Requires real data after live backfill | Run `python scripts/train_pm_models.py`; inspect `data/models/pm/` directory |
| Training report JSON contains quality badge, calibration_score, and market_count per trained category | TRAIN-04 | Report content depends on real training data | Open `data/models/pm/training_report.json`; verify all three fields present per category |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
