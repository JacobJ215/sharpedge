---
phase: 5
slug: model-pipeline-upgrade
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (uv workspace) |
| **Config file** | `pyproject.toml` (root) |
| **Quick run command** | `uv run pytest tests/unit/models/ tests/unit/analytics/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~25 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/models/ tests/unit/analytics/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 0 | QUANT-07, MODEL-01, MODEL-02 | unit stub | `uv run pytest tests/unit/models/test_ensemble_trainer.py tests/unit/models/test_calibration_store.py tests/unit/models/test_feature_assembler.py tests/unit/agent_pipeline/test_compose_alpha.py tests/unit/jobs/test_retrain_scheduler.py -x` | ❌ W0 | ⬜ pending |
| 5-01-02 | 01 | 1 | MODEL-02 | unit | `uv run pytest tests/unit/models/test_feature_assembler.py -x` | ❌ W0 | ⬜ pending |
| 5-02-01 | 02 | 2 | MODEL-01 | unit | `uv run pytest tests/unit/models/test_ensemble_trainer.py -x` | ❌ W0 | ⬜ pending |
| 5-02-02 | 02 | 2 | MODEL-01 | unit | `uv run pytest tests/unit/models/test_ensemble_trainer.py -x` | ❌ W0 | ⬜ pending |
| 5-03-01 | 03 | 3 | QUANT-07 | unit | `uv run pytest tests/unit/models/test_calibration_store.py -x` | ❌ W0 | ⬜ pending |
| 5-03-02 | 03 | 3 | QUANT-07 | unit | `uv run pytest tests/unit/models/test_calibration_store.py -x` | ❌ W0 | ⬜ pending |
| 5-04-01 | 04 | 4 | QUANT-07, MODEL-01 | integration | `uv run pytest tests/unit/models/ -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/models/test_ensemble_trainer.py` — stubs for MODEL-01 (5 base models, meta-learner, OOF training, predict_ensemble)
- [ ] `tests/unit/models/test_calibration_store.py` — stubs for QUANT-07 (CalibrationStore, per-sport Brier score, confidence_mult derivation)
- [ ] `tests/unit/models/test_feature_assembler.py` — stubs for MODEL-02 (FeatureAssembler, all 10 feature fields, imputation)
- [ ] `tests/unit/agent_pipeline/test_compose_alpha.py` — RED stub for compose_alpha CalibrationStore wiring (QUANT-07)
- [ ] `tests/unit/jobs/test_retrain_scheduler.py` — RED stub for start_retrain_scheduler (MODEL-01)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Weekly retrain cron fires correctly | MODEL-01 | Scheduler timing requires live process | Start webhook_server, wait for scheduled trigger or trigger manually, verify new `.joblib` files written |
| ESPN injury client returns usable field | MODEL-02 | External API — undocumented field path | Call ESPN client for an NFL game with known injured player, verify injury flag populated |
| model_version stored in BacktestResult DB row | QUANT-07 | Requires live Supabase connection | Run calibration update, check `model_version` column in `backtest_results` table |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
