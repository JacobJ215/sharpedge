# Phase 5: Model Pipeline Upgrade - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Upgrade the prediction system with: (1) rolling Platt calibration that updates `confidence_mult` after each resolved game, (2) a 5-model ensemble with a meta-learner combining probabilities from team form, matchup history, injury impact, market sentiment, and weather/travel models, and (3) a full feature vector (MODEL-02) assembled at inference time. No new UI surfaces — Phase 4 displays already consume `confidence_mult` and ensemble `model_prob`. This phase makes those values real.

</domain>

<decisions>
## Implementation Decisions

### Calibration behavior
- Trigger: After each individual resolved game — `result_watcher.py` is the hook point
- Scope: Per-sport (NFL and NBA tracked separately); falls back to `confidence_mult = 1.0` if sport has fewer than 50 resolved games
- Minimum threshold: 50 resolved games per sport before Platt scaling produces a stable sigmoid
- Poor calibration penalty: `confidence_mult < 1.0` when Brier score is high — a miscalibrated model actively reduces alpha scores rather than staying neutral
- Formula: `confidence_mult = 1.0 - (brier_score - brier_baseline)` clamped to [0.5, 1.2] range (Claude's discretion on exact formula)

### Ensemble composition
- Architecture: **Meta-learner (stacking)** — 5 base models each produce a probability, a 6th model (logistic regression) takes those 5 probabilities as inputs and produces the final probability
- Model 1 — Team form: rolling stats from last 10 games (offense/defense avg, ATS trend)
- Model 2 — Matchup history: head-to-head historical results and cover rates
- Model 3 — Injury impact: ESPN injury reports via existing ESPN client in `packages/data_feeds`
- Model 4 — Market sentiment: line movement velocity + public betting % from OddsAPI
- Model 5 — Weather/travel: weather client (existing) + timezone crossing count (2+ zones = penalty factor)
- Travel definition: timezone crossings only — away team traveling 2+ time zones gets a penalty factor; distance/back-to-back approach is Claude's discretion for implementation

### Feature freshness at inference
- Live features (line movement velocity, public betting %): pull from existing OddsAPI / public betting clients **on demand** at inference time — always fresh, latency is acceptable since analysis is not real-time
- Rolling team stats (last 10 results, opponent strength, home/away splits): query from Supabase historical game table
- Injury status: pull from ESPN client at inference time
- Missing feature handling: impute with **sport-specific median** for that feature — model still runs, reduced calibration handles uncertainty
- Rest days: compute from game schedule in Supabase (date diff between games)

### Training cadence & versioning
- Full retrain: **weekly cron job** — all 5 base models + meta-learner retrain from latest Supabase data
- Platt recalibration: after every resolved game (separate from full retrain — lighter-weight, updates only `confidence_mult`)
- Version policy: replace active model in place, keep previous version as `{model_name}_prev.joblib` for rollback (last 2 versions on disk)
- Attribution: store `model_version` (trained_at timestamp string) alongside every prediction in BacktestResult in Supabase — enables tracing win rate changes to specific retraining events

### Claude's Discretion
- Exact `confidence_mult` formula (clamping range, Brier score baseline per sport)
- Whether meta-learner uses logistic regression, ridge, or gradient boosting (logistic is standard for stacking)
- Training data partitioning for the meta-learner (must use out-of-fold predictions from base models to avoid leakage)
- Specific ESPN injury API endpoints and field mapping
- Cron scheduling mechanism (apscheduler, cron tab, or webhook_server background task)
- DB schema additions for model_version field in BacktestResult

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `compose_alpha.py:49` — `confidence_mult = 1.0` is the confirmed placeholder; Phase 5 replaces this with per-sport calibrated value
- `run_models.py:32` — `model_prob = game_context.get("model_prob", 0.52)` is the ensemble injection point; Phase 5 populates this from the meta-learner output
- `ml_inference.py` — `MLModelManager` already loads `.joblib` models and calls `predict_proba`; Phase 5 extends this to load all 5 base models + meta-learner
- `train_models.py` — working GBM + Platt calibration pipeline; Phase 5 extends to 5 separate feature groups + meta-learner training
- `apps/webhook_server/jobs/result_watcher.py` — existing game resolution hook; Phase 5 adds calibration trigger here
- `packages/data_feeds/` — ESPN, weather, OddsAPI clients already exist; Phase 5 uses them for inference-time feature assembly

### Established Patterns
- Platt calibration pattern: `CalibratedClassifierCV(pipeline, method="isotonic", cv=tscv)` — already in `train_models.py`, replicate for each base model
- Model persistence: `joblib.dump(model_bundle, path)` — established pattern, extend with `_prev` versioning
- Walk-forward windows: `create_windows()` in `walk_forward.py` — use for train/test splits when evaluating base model quality
- Feature arrays: `GameFeatures.to_array(feature_names)` — extend `GameFeatures` dataclass with MODEL-02 fields

### Integration Points
- `compose_alpha.py` — replace `confidence_mult = 1.0` with per-sport lookup from calibration store
- `run_models.py` — replace `model_prob` default with `MLModelManager.predict_ensemble(sport, features)` call
- `result_watcher.py` — add `trigger_calibration_update(sport, resolved_game)` call after result is stored
- `BacktestResult` in `backtesting.py` — add `model_version: str` field

</code_context>

<specifics>
## Specific Ideas

- "Institutional-grade" framing means the meta-learner should be explainable — logistic regression stacking is preferred over black-box approaches, so confidence intervals on the ensemble are interpretable
- The 5 model structure maps directly to quant factor decomposition: momentum (form), value (matchup edge), quality (injury-adjusted), sentiment (market), macro (weather/travel)
- Calibration penalty actively reduces alpha — this is intentional and directly tied to the core value prop: only surface edges the model has earned the right to surface

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-model-pipeline-upgrade*
*Context gathered: 2026-03-14*
