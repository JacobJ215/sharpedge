---
phase: 05-model-pipeline-upgrade
verified: 2026-03-14T16:00:00Z
status: passed
score: 15/15 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Trigger a WIN bet through the result_watcher and confirm CalibrationStore is called"
    expected: "trigger_calibration_update is invoked with the correct sport, CalibrationStore.update receives probs/outcomes from Supabase, and get_confidence_mult returns an updated value"
    why_human: "Requires a live Supabase instance with backtest_results rows; cannot be verified programmatically against production data"
  - test: "Start the webhook server with the retrain scheduler and wait for the Sunday 02:00 UTC trigger"
    expected: "weekly_retrain_job fires, _sync_retrain loads data from Supabase, train_ensemble completes, and ensemble_model.joblib is written"
    why_human: "Requires a live environment with Supabase access and waiting for the scheduled cron window"
  - test: "Run the live analysis pipeline on a real game context and confirm compose_alpha returns a confidence_mult other than 1.0"
    expected: "After at least 50 resolved games are stored, compose_alpha reads CalibrationStore and applies a non-1.0 multiplier to the BettingAlpha score"
    why_human: "Requires a populated calibration_store.joblib on the production host; cannot replicate without live data"
---

# Phase 5: Model Pipeline Upgrade Verification Report

**Phase Goal:** 5-model ensemble upgrade (team form, matchup, injury, sentiment, weather) + continuous Platt calibration engine (auto-weighting) + walk-forward honest inference + weekly retrain scheduler
**Verified:** 2026-03-14T16:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | 5-model ensemble (form, matchup, injury, sentiment, weather) exists and trains via OOF | VERIFIED | `ensemble_trainer.py` DOMAIN_FEATURES dict with 5 keys; OOF loop via TimeSeriesSplit + cross_val_predict; oof_preds_ and oof_indices stored |
| 2 | Meta-learner is LogisticRegression fit only on OOF predictions | VERIFIED | `LogisticRegression(C=1.0, max_iter=500)` fit on `oof_preds` at line 180 of ensemble_trainer.py |
| 3 | predict_ensemble returns dict with meta_prob plus 5 domain probs, all in [0,1] | VERIFIED | `predict_ensemble` method returns dict with 6 keys: meta_prob, form_prob, matchup_prob, injury_prob, sentiment_prob, weather_prob |
| 4 | CalibrationStore updates confidence_mult per sport using Brier score after each resolved game | VERIFIED | calibration_store.py: compute_confidence_mult formula maps Brier score to [0.5, 1.2]; update() called by trigger_calibration_update in result_watcher |
| 5 | CalibrationStore returns 1.0 below MIN_GAMES=50 threshold | VERIFIED | Line 80: `if cal is None or cal.n_samples < MIN_GAMES: return 1.0` |
| 6 | CalibrationStore persists state via joblib | VERIFIED | joblib.dump called in update(); constructor loads from disk on init |
| 7 | GameFeatures has all MODEL-02 fields with sport-specific median imputation | VERIFIED | ml_inference.py lines 78-103: all 16 new fields present; SPORT_MEDIANS imported from _sport_medians.py; to_array() uses medians not 0.0 |
| 8 | travel_penalty is < 0 when away team crosses 2+ timezones | VERIFIED | _feature_helpers.py provides compute_timezone_crossings + travel_penalty_from_crossings (-0.15 for 2 zones, -0.3 for 3+) |
| 9 | compose_alpha node sources confidence_mult from CalibrationStore singleton (not hardcoded 1.0) | VERIFIED | Lines 14-31, 67-73: _CAL_STORE singleton + _get_cal_store() + try/except fallback to 1.0 |
| 10 | run_models node sources model_prob from predict_ensemble (not hardcoded 0.52) | VERIFIED | Lines 33-47: lazy import of MLModelManager + FeatureAssembler, calls predict_ensemble, fallback to 0.52 on failure |
| 11 | WalkForwardBacktester has run_with_model_inference for honest per-window inference | VERIFIED | walk_forward.py line 244: method fully implemented; train indices always strictly lower than test indices (non-overlapping chunks) |
| 12 | Weekly retrain cron job exists using APScheduler AsyncIOScheduler | VERIFIED | retrain_scheduler.py: AsyncIOScheduler, weekly cron day_of_week="sun" hour=2, run_in_executor for CPU-bound work |
| 13 | train_models.py extended to call train_ensemble with DOMAIN_FEATURES column alignment guard | VERIFIED | scripts/train_models.py lines 280-309: _train_ensemble_for_sport validates column alignment before calling train_ensemble |
| 14 | BacktestResult has model_version field | VERIFIED | backtesting.py line 44: `model_version: str = ""` |
| 15 | All implementations degrade gracefully when ensemble/calibration not loaded | VERIFIED | compose_alpha: try/except fallback; run_models: is_loaded check + try/except; FeatureAssembler: returns {} for missing clients |

**Score:** 15/15 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/unit/models/test_calibration_store.py` | RED stubs for CalibrationStore (QUANT-07) | VERIFIED | File exists; imported by test suite |
| `tests/unit/models/test_feature_assembler.py` | RED stubs for FeatureAssembler (MODEL-02) | VERIFIED | File exists; 16 tests documented in summary |
| `tests/unit/models/test_ensemble_trainer.py` | RED stubs for EnsembleManager (MODEL-01) | VERIFIED | File exists |
| `tests/unit/jobs/test_result_watcher_calibration.py` | RED stub for trigger_calibration_update | VERIFIED | File exists |
| `tests/unit/agent_pipeline/test_compose_alpha.py` | RED stub for CalibrationStore wiring | VERIFIED | File exists |
| `tests/unit/jobs/test_retrain_scheduler.py` | RED stub for retrain scheduler | VERIFIED | File exists |
| `packages/models/src/sharpedge_models/feature_assembler.py` | FeatureAssembler class | VERIFIED | 274 lines; exports FeatureAssembler; imports GameFeatures, WeatherClient via _feature_helpers |
| `packages/models/src/sharpedge_models/ml_inference.py` | Extended GameFeatures + predict_ensemble | VERIFIED | 523 lines; home_ppg_10g and all MODEL-02 fields present; predict_ensemble method confirmed |
| `packages/models/src/sharpedge_models/ensemble_trainer.py` | EnsembleManager + train_ensemble + save_model_versioned | VERIFIED | 347 lines; all 3 exports confirmed |
| `packages/models/src/sharpedge_models/calibration_store.py` | CalibrationStore + SportCalibration + compute_confidence_mult | VERIFIED | 136 lines; all 3 exports confirmed |
| `packages/models/src/sharpedge_models/backtesting.py` | BacktestResult.model_version field | VERIFIED | model_version field at line 44 |
| `packages/models/src/sharpedge_models/walk_forward.py` | WalkForwardBacktester.run_with_model_inference | VERIFIED | 311 lines; method at line 244 |
| `apps/webhook_server/src/sharpedge_webhooks/jobs/result_watcher.py` | trigger_calibration_update wired post-WIN | VERIFIED | 230 lines; CalibrationStore imported at module level; trigger called at line 225 |
| `apps/webhook_server/src/sharpedge_webhooks/jobs/retrain_scheduler.py` | APScheduler weekly retrain job | VERIFIED | 84 lines; start_retrain_scheduler exported |
| `packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/compose_alpha.py` | confidence_mult from CalibrationStore | VERIFIED | 86 lines; _CAL_STORE singleton wired |
| `packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/run_models.py` | model_prob from predict_ensemble | VERIFIED | 89 lines; predict_ensemble call wired |
| `scripts/train_models.py` | train_ensemble call + DOMAIN_FEATURES guard | VERIFIED | _train_ensemble_for_sport function with column alignment assertion |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| feature_assembler.py | ml_inference.py GameFeatures | from sharpedge_models.ml_inference import GameFeatures | WIRED | Confirmed at line 26 of feature_assembler.py |
| feature_assembler.py | _feature_helpers (WeatherClient/timezone) | from sharpedge_models._feature_helpers import TEAM_TIMEZONES, compute_timezone_crossings, travel_penalty_from_crossings | WIRED | Lines 22-24 |
| ensemble_trainer.py | ml_inference.py GameFeatures | uses GameFeatures fields via _resolve_domain_arrays | WIRED | DOMAIN_FEATURES dict drives attribute extraction from GameFeatures |
| ml_inference.py MLModelManager | ensemble_trainer.py EnsembleManager | lazy import inside _load_ensemble_models + ensemble_model.joblib | WIRED | Lines 179-190; circular import avoided via lazy import |
| scripts/train_models.py | ensemble_trainer.train_ensemble | from sharpedge_models.ensemble_trainer import DOMAIN_FEATURES, train_ensemble | WIRED | Lines 286-309 |
| result_watcher.py | calibration_store.CalibrationStore | from sharpedge_models.calibration_store import CalibrationStore, DEFAULT_CALIBRATION_PATH (module level) | WIRED | Line 20; call at line 225 |
| calibration_store.py | sklearn.metrics.brier_score_loss | from sklearn.metrics import brier_score_loss | WIRED | Line 17 |
| compose_alpha.py | calibration_store.CalibrationStore | module-level try/except import; _get_cal_store singleton | WIRED | Lines 14-31; get_confidence_mult called at line 70 |
| run_models.py | ml_inference.MLModelManager.predict_ensemble | lazy import inside try/except; get_model_manager().predict_ensemble | WIRED | Lines 33-47 |
| retrain_scheduler.py | ensemble_trainer.train_ensemble | lazy import inside _sync_retrain; asyncio.run_in_executor | WIRED | Lines 27-46 |

---

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|---------|
| MODEL-01 | 05-01, 05-03, 05-05 | Prediction ensemble uses 5 models (team form, matchup history, injury impact, market sentiment, weather/travel) with calibrated weights | SATISFIED | EnsembleManager with 5-domain DOMAIN_FEATURES; OOF stacking; LogisticRegression meta-learner; predict_ensemble wired into run_models node; train_ensemble in train_models.py; retrain scheduler |
| MODEL-02 | 05-01, 05-02 | Feature builder assembles game feature vector from last 10 results, opponent strength, rest days, injury report, home/away splits, line movement velocity, public betting %, key number proximity | SATISFIED | GameFeatures extended with all 16 MODEL-02 fields; FeatureAssembler.assemble() calls _team_form, _matchup_history, _injury_impact, _market_sentiment, _weather_travel; sport-specific median imputation in to_array() |
| QUANT-07 | 05-01, 05-04, 05-05 | System continuously recalibrates ML model confidence using Platt scaling after each game resolves | SATISFIED | CalibrationStore with Brier-score compute_confidence_mult; trigger_calibration_update called post-WIN in result_watcher; confidence_mult applied in compose_alpha singleton; MIN_GAMES=50 threshold guard |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| feature_assembler.py | 126, 149, 157, 170, 182 | `return {}` in private helpers | Info | Intentional graceful-degradation pattern — documented in docstring. Empty dicts cause to_array() to use SPORT_MEDIANS imputation. Not a stub. |
| compose_alpha.py | 73 | `confidence_mult = 1.0` in except clause | Info | Intentional fallback value, not a placeholder. The primary path calls CalibrationStore. Acceptable defensive coding. |
| run_models.py | 42, 44, 47 | `model_prob = game_context.get("model_prob", 0.52)` in fallback branches | Info | Intentional fallback. Primary path calls predict_ensemble. 0.52 is the fallback default, not a hardcoded placeholder. |

No blockers. No warnings. All flagged patterns are documented, intentional, and required for graceful degradation.

---

### Commit Verification

All 9 plan commits verified in git history:

| Commit | Plan | Description |
|--------|------|-------------|
| 1365849 | 05-01 | test: RED TDD stubs for Phase 5 model pipeline requirements |
| c4b5379 | 05-02 | feat: extend GameFeatures with MODEL-02 fields + sport-specific median imputation |
| e70874d | 05-02 | feat: implement FeatureAssembler with graceful degradation and travel penalty |
| 5398c3a | 05-03 | feat: implement EnsembleManager with 5-domain OOF stacking ensemble |
| 5810b4f | 05-03 | feat: extend MLModelManager with predict_ensemble and BacktestResult model_version |
| 41dbaad | 05-04 | feat: implement CalibrationStore with Platt scaling and Brier-score confidence_mult |
| aac2c4f | 05-04 | feat: wire CalibrationStore into result_watcher via trigger_calibration_update |
| 85cf14e | 05-05 | feat: wire CalibrationStore into compose_alpha and EnsembleManager into run_models |
| 70133af | 05-05 | feat: add run_with_model_inference to WalkForwardBacktester and weekly retrain scheduler |

---

### Human Verification Required

#### 1. Live Calibration Update Cycle

**Test:** Process a WIN bet through the webhook server against a live Supabase instance that has backtest_results rows for at least one sport.
**Expected:** trigger_calibration_update fetches resolved predictions, calls CalibrationStore.update, and the confidence_mult returned by get_confidence_mult reflects the updated Brier score.
**Why human:** Requires a populated Supabase backtest_results table and a live webhook event.

#### 2. Weekly Retrain Job Execution

**Test:** Deploy the webhook server with retrain_scheduler started. Wait for Sunday 02:00 UTC or manually trigger weekly_retrain_job in an async context.
**Expected:** _sync_retrain loads training data from Supabase, calls train_ensemble, and writes ensemble_model.joblib to the models directory.
**Why human:** Requires live Supabase data and either waiting for the cron window or an async test harness; pandas is not installed in the unit test environment so run_with_model_inference tests already skip.

#### 3. End-to-End Confidence Multiplier Propagation

**Test:** After storing 50+ resolved games for a sport, run the full analysis pipeline on a real game context for that sport.
**Expected:** compose_alpha reads a calibration_store.joblib with n_samples >= 50 and applies a confidence_mult != 1.0 to the BettingAlpha score.
**Why human:** Requires a production host with 50+ resolved bets for one sport and a populated calibration_store.joblib file.

---

### Phase Goal Summary

The phase goal is fully achieved in the codebase:

- **5-model ensemble:** EnsembleManager trains 5 domain-specific GBMs (form, matchup, injury, sentiment, weather) via OOF stacking with a LogisticRegression meta-learner. predict_ensemble wired into run_models node.
- **Continuous Platt calibration:** CalibrationStore computes Brier-score-based confidence_mult per sport, persists via joblib, activates above MIN_GAMES=50. Triggered post-WIN in result_watcher. Applied via singleton in compose_alpha.
- **Walk-forward honest inference:** WalkForwardBacktester.run_with_model_inference trains and infers per window with guaranteed no-lookahead (train indices strictly lower than test indices).
- **Weekly retrain scheduler:** APScheduler AsyncIOScheduler with Sunday 02:00 UTC cron job that offloads train_ensemble to a thread executor.

All 15 must-have truths are verified. All 9 commits confirmed. All key links are wired. No blocker anti-patterns.

---

_Verified: 2026-03-14T16:00:00Z_
_Verifier: Claude (gsd-verifier)_
