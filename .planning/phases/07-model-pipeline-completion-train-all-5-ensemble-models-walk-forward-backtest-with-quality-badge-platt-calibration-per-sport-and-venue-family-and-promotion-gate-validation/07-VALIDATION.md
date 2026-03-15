---
phase: 7
slug: model-pipeline-completion
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-14
completed: 2026-03-14
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | pyproject.toml (root workspace) |
| **Quick run command** | `uv run pytest tests/unit/models/ -x -q` |
| **Full suite command** | `uv run pytest tests/unit/models/ tests/integration/ -q` |
| **Actual runtime** | ~10 seconds (unit only), ~45 seconds (with integration) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/models/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/unit/models/ tests/integration/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 7-01-01 | 01 | 0 | PIPE-01 | unit | `uv run pytest tests/unit/models/test_pipeline_integration.py -x -q` | ✅ | ✅ green |
| 7-01-02 | 01 | 0 | GATE-01 | unit | `uv run pytest tests/unit/models/test_promotion_gate.py -x -q` | ✅ | ✅ green |
| 7-02-01 | 02 | 1 | PIPE-01 | unit | `uv run pytest tests/unit/models/test_pipeline_integration.py -x` | ✅ | ✅ green |
| 7-02-02 | 02 | 1 | PIPE-01 | script | `uv run python scripts/download_historical_data.py --sport ncaab --dry-run` | ✅ | ✅ green |
| 7-03-01 | 03 | 2 | PIPE-01 | unit | `uv run pytest tests/unit/models/test_pipeline_integration.py::test_ensemble_trains_all_sports -x` | ✅ | ✅ green |
| 7-03-02 | 03 | 2 | PIPE-01 | script | `uv run python scripts/train_models.py --dry-run --sports nba nfl` | ✅ | ✅ green |
| 7-04-01 | 04 | 3 | WALK-01 | unit | `uv run pytest tests/unit/models/ -k walk_forward -x` | ✅ | ✅ green |
| 7-04-02 | 04 | 3 | WALK-01 | script | `uv run python scripts/run_walk_forward.py --sport nba --dry-run` | ✅ | ✅ green |
| 7-05-01 | 05 | 4 | CAL-01 | unit | `uv run pytest tests/unit/models/ -k calibration -x` | ✅ | ✅ green |
| 7-05-02 | 05 | 4 | CAL-01 | script | `uv run python scripts/run_calibration.py --sport nba --dry-run` | ✅ | ✅ green |
| 7-06-01 | 06 | 5 | GATE-01 | unit | `uv run pytest tests/unit/models/test_promotion_gate.py -x` | ✅ | ✅ green |
| 7-06-02 | 06 | 5 | INT-01 | integration | `uv run pytest tests/integration/test_alpha_pipeline.py -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/unit/models/test_pipeline_integration.py` — 8 tests GREEN
- [x] `tests/unit/models/test_promotion_gate.py` — 3 tests GREEN
- [x] `tests/integration/test_alpha_pipeline.py` — 2 tests GREEN
- [x] Fix import bug in `scripts/retrain_scheduler.py` line 36 (`sharpedge_feeds.supabase_client` → `sharpedge_db.client`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Walk-forward quality badge is `high` or `excellent` | WALK-01 | Requires real trained models + full dataset | Run `uv run python scripts/run_walk_forward.py --sport nba` and inspect badge in output JSON |
| Calibration plots show no overfit | CAL-01 | Visual inspection required | Run `uv run python scripts/run_calibration.py --sport nba --plot` and inspect reliability diagram |
| NCAAB historical data multi-season coverage | PIPE-01 | ESPN endpoint coverage unverified | Run `uv run python scripts/download_historical_data.py --sport ncaab` and verify season count |
| 30-day paper stability period | GATE-01 | Time-based, cannot be automated | Manually track paper mode start date; mark in promotion gate report |

---

## Final Suite Result

```
uv run pytest tests/unit/models/ tests/unit/jobs/ tests/integration/ -q
66 passed, 1 warning in 8.98s
```

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete — 2026-03-14
