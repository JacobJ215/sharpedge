# Phase 7: Model Pipeline Completion — Research

**Researched:** 2026-03-14
**Domain:** ML model training pipeline, walk-forward backtesting, Platt calibration, promotion gates
**Confidence:** HIGH (all findings verified by direct codebase inspection)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Data Pipeline:** Run `scripts/download_historical_data.py` for NBA, NFL, NCAAB, MLB, NHL. Run `scripts/process_historical_data.py`. Verify `FeatureAssembler` produces correct `GameFeatures`. Confirm time-correct splits — no lookahead bias.
- **Model Training:** Train all 5 ensemble models via `EnsembleManager`. Train stacking layer on OOF predictions. OOF indices must be stored alongside OOF predictions. Persist artifacts to `data/models/`. Scripts must handle missing model files gracefully.
- **Walk-Forward Backtesting:** Run `WalkForwardBacktester`. Non-overlapping windows, no lookahead. Per-window: win rate, ROI, edge after fees. Quality badge `high` or `excellent` before promotion.
- **Platt Calibration:** Run `CalibrationStore` on lagged OOS data only. Fit per model, per sport, per market family. Update `confidence_mult` in composite alpha. Plots inspected before sign-off.
- **Venue-Specific Calibration:** Kalshi by category/time-to-close; Polymarket reports; sportsbooks no-vig by sport/bet type; cross-venue dislocation baseline.
- **Integration Tests:** `packages/models/tests/` full pipeline test. Verify `compose_alpha()` uses calibrated `confidence_mult`. Verify `run_models()`. Verify weekly retrain scheduler.
- **Promotion Gate (all must pass):** Calibration error < threshold (Brier or ECE). Post-cost edge > 2% on test set. Max drawdown within limit on walk-forward windows. 30-day paper stability tracked (not code-enforced). Walk-forward quality badge `high` or `excellent`.

### Claude's Discretion
- Exact threshold values for calibration error (derive from dataset characteristics)
- Whether to create `scripts/train_models.py` or extend existing scripts
- How to structure calibration report output (JSON, text, or both)
- Whether venue-specific calibration runs as separate script or extension of existing calibration
- Internal structure of promotion gate report artifact

### Deferred Ideas (OUT OF SCOPE)
- Frontend wiring (Phase 8)
- Live execution on any venue
- New model architectures beyond the 5 specified
- Paper trading / shadow mode
- 30-day paper stability period enforcement in code
</user_constraints>

---

## Summary

Phase 7 completes the model pipeline by running all training, calibration, and validation scripts against real data, then verifying the integrated pipeline end-to-end. Critically, the key infrastructure from Phases 5 and 6 already exists in the codebase — `EnsembleManager`, `WalkForwardBacktester`, `CalibrationStore`, `FeatureAssembler`, `run_models()`, `compose_alpha()` (node), and `start_retrain_scheduler()` are all implemented and tested. Phase 7's work is almost entirely **pipeline execution + gap closure**, not greenfield development.

The most significant gaps uncovered by codebase inspection are: (1) `scripts/download_historical_data.py` covers only NFL and NBA from Kaggle (NCAAB, MLB, NHL sources are absent); (2) `scripts/process_historical_data.py` produces only NFL and NBA processed datasets; (3) `scripts/train_models.py` exists and calls `train_ensemble()` but only trains NFL and NBA; (4) there is no `packages/models/tests/` directory — tests for models live in `tests/unit/models/`; (5) `CalibrationStore` stores per-sport state but has no per-venue-family segmentation yet; (6) no promotion gate report artifact exists; (7) the weekly retrain scheduler imports from `sharpedge_feeds.supabase_client` (non-existent) instead of `sharpedge_db.client`.

**Primary recommendation:** Extend the three scripts to cover NCAAB, MLB, NHL (ESPN API data is already fetched for all four scoreboard sports); add `scripts/run_walk_forward.py` and `scripts/run_calibration.py` as new pipeline steps; add a `scripts/generate_promotion_gate.py` that writes a JSON report; fix the `retrain_scheduler.py` import bug; add the missing integration test file.

---

## Standard Stack

### Core (all already installed in the workspace)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scikit-learn | latest (workspace) | GradientBoostingClassifier, CalibratedClassifierCV, TimeSeriesSplit, brier_score_loss | Industry standard; all model training code already uses it |
| numpy | latest (workspace) | Array manipulation for OOF predictions | Required by ensemble_trainer.py |
| pandas | latest (workspace) | DataFrame-based feature processing in process_historical_data.py | Data pipeline already uses it |
| joblib | latest (workspace) | Model persistence (.joblib files) | Used by train_models.py, CalibrationStore, EnsembleManager |
| scipy | latest (workspace) | brentq solver in no_vig.py (Shin devigging for venue calibration) | Already used by no_vig.py (Phase 6 devig_shin_n_outcome) |
| apscheduler | latest (webhook_server) | AsyncIOScheduler for weekly retrain cron | Already wired in retrain_scheduler.py |
| kaggle | CLI tool (external) | Historical data download | Configured in download_historical_data.py |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| matplotlib / seaborn | for calibration plots | Calibration curve visualization | `CalibrationStore.update()` does not produce plots — new script must |
| pytest | latest | Integration tests in `tests/unit/models/` | Already configured (conftest.py at root) |

**Installation:** No new packages required. All dependencies already present in workspace.

---

## Architecture Patterns

### Existing Script Pipeline (confirmed by codebase)

```
scripts/
├── download_historical_data.py   # Kaggle (NFL+NBA only) + ESPN scoreboard data
├── process_historical_data.py    # Feature engineering (NFL+NBA only) → data/processed/
├── train_models.py               # Train spread/totals GBMs + ensemble (NFL+NBA only)
├── run_walk_forward.py           # MISSING — needs to be created
├── run_calibration.py            # MISSING — needs to be created
└── generate_promotion_gate.py    # MISSING — needs to be created
```

### Existing Model Artifacts Location

```
data/
├── models/                       # gitignored — all .joblib files here
│   ├── {sport}_spread_model.joblib
│   ├── {sport}_totals_model.joblib
│   ├── {sport}_spread_metrics.json
│   ├── {sport}_totals_metrics.json
│   ├── ensemble_model.joblib     # saved by EnsembleManager.train()
│   ├── ensemble_model_prev.joblib
│   └── all_model_metrics.json
├── processed/                    # gitignored
│   ├── nfl_training.parquet
│   ├── nba_training.parquet
│   └── feature_metadata.json
├── raw/                          # gitignored
│   ├── nfl_betting/
│   ├── nba_betting/
│   └── espn/                     # nfl_scoreboard.json, nba_scoreboard.json, mlb_scoreboard.json, nhl_scoreboard.json
└── calibration_store.joblib      # gitignored — CalibrationStore persistence
```

### Pattern 1: Extending Scripts for NCAAB, MLB, NHL

**What:** The three existing scripts (download, process, train) are sport-specific. Each requires parallel additions for NCAAB, MLB, NHL.

**When to use:** Any time a new sport needs end-to-end pipeline coverage.

**Key facts from codebase:**
- `download_historical_data.py`: Kaggle datasets defined in `KAGGLE_DATASETS` list (currently NFL + NBA only). ESPN endpoints defined in `ESPN_ENDPOINTS` dict — already includes `mlb_scoreboard` and `nhl_scoreboard`. NCAAB requires a separate Kaggle dataset or ESPN college basketball endpoint.
- `process_historical_data.py`: `load_nfl_data()` / `load_nba_data()` are separate functions. Pattern is: `load_{sport}_data() -> pd.DataFrame | None`. Same feature engineering applies across sports.
- `train_models.py`: `train_sport_models(sport: str)` is already parameterized. Calling it with `"ncaab"`, `"mlb"`, `"nhl"` will work if processed parquet files exist.

**Integration point:** `_train_ensemble_for_sport()` in train_models.py validates that all `DOMAIN_FEATURES` columns exist in the DataFrame before calling `train_ensemble()`. If NCAAB/MLB/NHL processed data lacks the ensemble feature columns (e.g. `home_injury_impact`, `line_movement_velocity`), training will raise `ValueError`. The fix is to add zero-fill or median-fill for missing domain columns during processing.

### Pattern 2: Walk-Forward Backtesting Script

**What:** `WalkForwardBacktester` exists in `walk_forward.py` with two entry points:
- `run(results: list[BacktestResult], n_windows=4)` — reads stored `BacktestResult` objects from `BacktestEngine`
- `run_with_model_inference(feature_df, model_fn, y, n_windows=4)` — drives full train+predict loop per window (preferred for Phase 7 as it produces honest OOS metrics without needing a populated `backtest_results` DB table)

**Key output:** `BacktestReport.quality_badge` is `Literal["low", "medium", "high", "excellent"]`. Thresholds: excellent = 4+ windows, 3+ positive ROI; high = 3+ windows, 2+ positive ROI.

**ROI formula confirmed (from walk_forward.py line 207-213):** Win returns `odds/100` (positive American) or `100/abs(odds)` (negative American). Loss returns -1.0. ROI = total_return / n_resolved.

### Pattern 3: CalibrationStore Integration Flow

```
result_watcher.py
    └── trigger_calibration_update(sport, resolved_game)
            └── CalibrationStore(DEFAULT_CALIBRATION_PATH).update(sport, probs, outcomes)
                    └── joblib.dump → data/calibration_store.joblib

compose_alpha.py (node)
    └── _get_cal_store(DEFAULT_CALIBRATION_PATH)  [singleton]
            └── CalibrationStore.get_confidence_mult(sport) → float
                    └── compose_alpha(edge_score, regime_scale, survival_prob, confidence_mult)
```

**Calibration path constant:**
- `DEFAULT_CALIBRATION_PATH` in `calibration_store.py` resolves to `{repo_root}/data/calibration_store.joblib`
- `compose_alpha.py` node imports `DEFAULT_CALIBRATION_PATH` directly from `calibration_store`
- The singleton `_CAL_STORE` is process-level — tests that mock `CalibrationStore` must patch at `sharpedge_agent_pipeline.nodes.compose_alpha.CalibrationStore`

**Calibration thresholds (from calibration_store.py):**
- `BRIER_BASELINE = 0.25` (coin-flip benchmark)
- `BRIER_GOOD = 0.22` (above-average threshold)
- `MIN_GAMES = 50` (minimum samples before calibration activates; below this, `confidence_mult` stays 1.0)
- `confidence_mult` clamped to `[0.5, 1.2]`

### Pattern 4: Venue-Specific Calibration

**What:** Phase 6 added `devig_shin_n_outcome` in `packages/models/src/sharpedge_models/no_vig.py`. This is the devigging function for N-outcome sportsbook markets. The `CalibrationStore` currently segments only by sport. Phase 7 extends calibration to sport × venue family.

**Key constraint:** `CalibrationStore.update(sport, probs, outcomes)` writes to `self._calibrations[sport.lower()]`. For venue-specific calibration, the key needs to be `f"{sport}_{venue_family}"` (e.g. `"nba_kalshi"`, `"nfl_sportsbook_moneyline"`). This requires either (a) extending CalibrationStore with a `key` parameter, or (b) a separate calibration report script that does not use CalibrationStore persistence (writes JSON directly).

**Recommendation (Claude's discretion):** Separate script `scripts/run_calibration.py` that writes JSON calibration reports. Do not extend CalibrationStore's internal storage — the existing per-sport key is used by compose_alpha() and must not be broken. Venue calibration is reporting/analysis output, not real-time alpha input.

### Pattern 5: Promotion Gate Report

**What:** A structured artifact that records pass/fail for each gate criterion. The artifact must be human-readable and machine-checkable.

**Recommendation (Claude's discretion):** Write `data/promotion_gate_{sport}_{timestamp}.json` with fields:
```json
{
  "generated_at": "ISO-8601",
  "sport": "nba",
  "model_version": "...",
  "gates": {
    "calibration_brier_score": {"value": 0.21, "threshold": 0.25, "passed": true},
    "min_post_cost_edge": {"value": 0.031, "threshold": 0.02, "passed": true},
    "max_drawdown": {"value": 0.14, "threshold": 0.20, "passed": true},
    "walk_forward_badge": {"value": "high", "required": ["high", "excellent"], "passed": true},
    "paper_stability_days": {"value": null, "threshold": 30, "passed": null, "note": "Tracked manually"}
  },
  "overall_passed": true
}
```

### Anti-Patterns to Avoid

- **Training ensemble on full dataset without OOF split:** EnsembleManager already prevents this — meta-learner is fit only on OOF predictions. Do not bypass by calling `fit()` directly on the meta-learner.
- **Calibrating on training data:** CalibrationStore.update() must receive lagged OOS data only. `trigger_calibration_update` fetches from `backtest_results` table (post-resolution data).
- **Using `run()` (stored BacktestResult) instead of `run_with_model_inference()`:** If `backtest_results` DB table is empty, `run()` returns a low-quality badge by default. Use `run_with_model_inference()` for scripts that operate on static training data.
- **Calling `train_models.py` with sports that lack ensemble feature columns:** `_train_ensemble_for_sport()` raises `ValueError` if `DOMAIN_FEATURES` columns are missing. Must zero-fill or skip ensemble step for sports with incomplete features.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Time-series CV splits | Custom fold generator | `sklearn.model_selection.TimeSeriesSplit` | Already used in train_models.py; prevents lookahead in a single call |
| Probability calibration | Manual Platt implementation | `sklearn.calibration.CalibratedClassifierCV` or `CalibrationStore` using `LogisticRegression` | Existing CalibrationStore fits LogisticRegression (Platt scaling) correctly |
| Walk-forward window creation | Custom chunking logic | `WalkForwardBacktester.run_with_model_inference()` | Existing implementation with CRITICAL INVARIANT assertion on zero overlap |
| Model persistence with versioning | Custom save/load | `joblib.dump` + `save_model_versioned()` pattern from ensemble_trainer.py | Active/previous rotation already implemented |
| Brier score computation | Manual squared error loop | `sklearn.metrics.brier_score_loss` | Already used in CalibrationStore; handles edge cases |
| N-outcome devigging | Custom Shin calculation | `devig_shin_n_outcome` in no_vig.py | Implemented in Phase 6 with brentq fallback to multiplicative |

**Key insight:** The model pipeline infrastructure is complete. Phase 7's primary work is data coverage extension (NCAAB/MLB/NHL), pipeline script creation for the three missing steps, and integration test coverage.

---

## Common Pitfalls

### Pitfall 1: NCAAB/MLB/NHL Missing DOMAIN_FEATURES Columns

**What goes wrong:** `_train_ensemble_for_sport()` raises `ValueError: train_models: DataFrame missing DOMAIN_FEATURES columns` when processing NCAAB/MLB/NHL data because `engineer_rolling_features()` and `engineer_ats_features()` do not produce the ensemble columns (`home_injury_impact`, `line_movement_velocity`, `public_pct_home`, `weather_impact_score`, `travel_penalty`, `h2h_home_cover_rate`, `h2h_total_games`, `home_away_split_delta`, `opponent_strength_home`, `opponent_strength_away`).

**Why it happens:** These columns come from FeatureAssembler (live inference) and are not in historical CSV/parquet data. The ensemble training path in train_models.py checks for them before training.

**How to avoid:** In `_train_ensemble_for_sport()`, wrap the `missing_cols` check — if columns are missing, add zero-filled columns rather than raising. Or, for Phase 7's scripts, produce synthetic zero-fill versions of the missing ensemble columns in the processing step for sports that lack that data.

**Warning signs:** `ValueError: train_models: DataFrame missing DOMAIN_FEATURES columns` in script output.

### Pitfall 2: retrain_scheduler.py Has a Bad Import

**What goes wrong:** `from sharpedge_feeds.supabase_client import get_supabase_client` fails at runtime — the correct module is `sharpedge_db.client` (per STATE.md decision: "Module-level lazy-import wrappers" and "sharpedge_db.client.get_supabase_client"). The package `sharpedge_feeds` does not export `supabase_client`.

**Why it happens:** The scheduler was written with an incorrect import path. The actual Supabase client is in `packages/database/src/sharpedge_db/client.py`.

**How to avoid:** In the integration test for `start_retrain_scheduler()`, mock `sharpedge_db.client.get_supabase_client` and verify `_sync_retrain()` succeeds. Also fix the import in retrain_scheduler.py.

**Warning signs:** `ModuleNotFoundError: No module named 'sharpedge_feeds.supabase_client'` when scheduler triggers.

### Pitfall 3: _CAL_STORE Singleton Breaks Tests

**What goes wrong:** `_CAL_STORE` is a module-level singleton in `compose_alpha.py`. Tests that modify CalibrationStore state can pollute subsequent tests if they don't reset the singleton.

**Why it happens:** The singleton is set on first call to `_get_cal_store()` and never cleared.

**How to avoid:** In test setup, patch `sharpedge_agent_pipeline.nodes.compose_alpha._CAL_STORE = None` in a fixture teardown, or mock `CalibrationStore` at import time. The STATE.md confirms the correct patch target: `sharpedge_agent_pipeline.nodes.compose_alpha.CalibrationStore`.

### Pitfall 4: WalkForwardBacktester.run() Needs Populated BacktestResults

**What goes wrong:** `WalkForwardBacktester.run(results)` takes a list of `BacktestResult` objects. If the Supabase `backtest_results` table is empty or unavailable in scripts, the result list is empty and the report returns `quality_badge="low"`.

**Why it happens:** `run()` is designed for production use with a populated DB. Scripts running against local parquet data should use `run_with_model_inference()` instead.

**How to avoid:** Use `run_with_model_inference(feature_df, model_fn, y)` in all training scripts. Reserve `run()` for the production scheduler path.

### Pitfall 5: download_historical_data.py Has No NCAAB Source

**What goes wrong:** NCAAB (college basketball) has no Kaggle dataset configured and no ESPN endpoint. `ESPN_ENDPOINTS` has `mlb_scoreboard` and `nhl_scoreboard` but only current scoreboard data, not historical game results.

**Why it happens:** NCAAB data is more fragmented than professional leagues. The ESPN college basketball endpoint is `https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard` but provides only current-week data.

**How to avoid:** For Phase 7, use the ESPN endpoint for NCAAB current data and document that historical NCAAB training data requires manual download or a separate data source. The processing script can handle missing sports gracefully (load function returns None).

### Pitfall 6: CalibrationStore MIN_GAMES Guard

**What goes wrong:** With fewer than 50 resolved games, `CalibrationStore.get_confidence_mult()` returns 1.0 even after update() is called. If scripts run calibration on small datasets, the confidence_mult in alpha scores will appear unchanged.

**Why it happens:** `MIN_GAMES = 50` is a deliberate guard in calibration_store.py (line 112: `if len(probs) >= MIN_GAMES`). Below threshold, `mult` is forced to 1.0.

**How to avoid:** Document this in the promotion gate report. For sports with fewer than 50 resolved games in the test period, calibration error metrics can be computed but `confidence_mult` remains at default. This is correct behavior.

---

## Code Examples

### EnsembleManager.train() — DataFrame path (production)

```python
# Source: packages/models/src/sharpedge_models/ensemble_trainer.py
from sharpedge_models.ensemble_trainer import train_ensemble, DOMAIN_FEATURES
from pathlib import Path

# df must have all DOMAIN_FEATURES columns + "home_covered" target
# DOMAIN_FEATURES keys: form, matchup, injury, sentiment, weather
all_domain_cols = [col for cols in DOMAIN_FEATURES.values() for col in cols]
# Required columns per domain:
# form: home_ppg_10g, home_papg_10g, away_ppg_10g, away_papg_10g, home_ats_10g, away_ats_10g
# matchup: h2h_home_cover_rate, h2h_total_games, home_away_split_delta, opponent_strength_home, opponent_strength_away
# injury: home_injury_impact, away_injury_impact
# sentiment: line_movement_velocity, public_pct_home
# weather: weather_impact_score, travel_penalty

y = df["home_covered"].astype(int).values
manager = train_ensemble(df, y, models_dir=Path("data/models"), model_version="2026-03-14")
# Persists ensemble_model.joblib with active/prev rotation
```

### WalkForwardBacktester.run_with_model_inference() — script usage

```python
# Source: packages/models/src/sharpedge_models/walk_forward.py
from sharpedge_models.walk_forward import WalkForwardBacktester
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

backtester = WalkForwardBacktester()

def model_fn(X_train, X_test, y_train):
    pipe = Pipeline([("scaler", StandardScaler()), ("clf", GradientBoostingClassifier())])
    pipe.fit(X_train, y_train)
    return pipe

report = backtester.run_with_model_inference(
    feature_df=df[feature_cols],
    model_fn=model_fn,
    y=y,
    n_windows=4,
)
print(report.quality_badge)         # "low" | "medium" | "high" | "excellent"
print(report.overall_roi)           # weighted average ROI across windows
print(report.overall_win_rate)
for w in report.windows:
    print(f"Window {w.window_id}: ROI={w.out_of_sample_roi:.3f} WR={w.out_of_sample_win_rate:.3f} n={w.n_bets}")
```

### CalibrationStore.update() + compose_alpha integration

```python
# Source: packages/models/src/sharpedge_models/calibration_store.py
from sharpedge_models.calibration_store import CalibrationStore, DEFAULT_CALIBRATION_PATH

store = CalibrationStore(DEFAULT_CALIBRATION_PATH)
store.update(
    sport="nba",
    probs=[0.62, 0.58, 0.71, ...],    # model predicted probabilities (OOS only)
    outcomes=[True, False, True, ...],  # actual outcomes (resolved games)
)
# Persists to data/calibration_store.joblib
mult = store.get_confidence_mult("nba")  # 1.0 if n < 50, else clamped [0.5, 1.2]

# compose_alpha node reads this automatically via _CAL_STORE singleton:
# packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/compose_alpha.py
# confidence_mult = _get_cal_store(DEFAULT_CALIBRATION_PATH).get_confidence_mult(sport)
```

### retrain_scheduler fix (confirmed bug)

```python
# BUG in retrain_scheduler.py line 36:
from sharpedge_feeds.supabase_client import get_supabase_client  # WRONG

# CORRECT import (per packages/database/src/sharpedge_db/client.py):
from sharpedge_db.client import get_supabase_client
```

### Venue-specific calibration using devig_shin_n_outcome

```python
# Source: packages/models/src/sharpedge_models/no_vig.py (Phase 6)
from sharpedge_models.no_vig import devig_shin_n_outcome
# Returns list[float] of fair probabilities for N-outcome markets
# Used for sportsbook calibration by sport and bet type
fair_probs = devig_shin_n_outcome([home_odds, away_odds])  # 2-way
fair_probs = devig_shin_n_outcome([home_odds, draw_odds, away_odds])  # 3-way
```

---

## Gap Analysis: What Phase 7 Must Create vs. Extend

### Scripts (extend existing)

| File | Status | Required Change |
|------|--------|-----------------|
| `scripts/download_historical_data.py` | EXISTS | Add NCAAB ESPN endpoint; add MLB/NHL Kaggle or ESPN historical fallback |
| `scripts/process_historical_data.py` | EXISTS | Add `load_ncaab_data()`, `load_mlb_data()`, `load_nhl_data()`; zero-fill missing ensemble columns |
| `scripts/train_models.py` | EXISTS | Call `train_sport_models()` for ncaab, mlb, nhl; handle missing ensemble columns gracefully |

### Scripts (create new)

| File | Status | Purpose |
|------|--------|---------|
| `scripts/run_walk_forward.py` | MISSING | Load processed parquet; call `WalkForwardBacktester.run_with_model_inference()`; print/save BacktestReport |
| `scripts/run_calibration.py` | MISSING | Load processed OOS data; call `CalibrationStore.update()` per sport; generate calibration plots; run venue-specific calibration reports |
| `scripts/generate_promotion_gate.py` | MISSING | Aggregate metrics from model metrics JSON + backtest report + calibration store; write promotion gate JSON per sport |

### Integration Tests (create new)

| File | Status | Purpose |
|------|--------|---------|
| `tests/unit/models/test_pipeline_integration.py` | MISSING | Full pipeline: DataFrame → train_ensemble → run_with_model_inference → CalibrationStore.update → compose_alpha with calibrated mult |
| `tests/unit/jobs/test_retrain_scheduler.py` | EXISTS | Already tests scheduler; extend to verify `get_supabase_client` mock path |

### Bug Fixes (must land in Phase 7)

| File | Bug | Fix |
|------|-----|-----|
| `apps/webhook_server/src/sharpedge_webhooks/jobs/retrain_scheduler.py` | `from sharpedge_feeds.supabase_client import get_supabase_client` — wrong module | Change to `from sharpedge_db.client import get_supabase_client` |

### Code Extensions (extend existing)

| File | Required Extension |
|------|-------------------|
| `packages/models/src/sharpedge_models/calibration_store.py` | None needed for per-sport alpha; venue calibration is a separate reporting script |
| `packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/compose_alpha.py` | None needed — already reads `confidence_mult` from CalibrationStore singleton |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (confirmed: conftest.py at repo root, tests/ directory exists) |
| Config file | `pyproject.toml` root-level or `pytest.ini` (verify in workspace root) |
| Quick run command | `pytest tests/unit/models/ -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PIPE-01 | EnsembleManager trains on all 5 domain arrays without leakage | unit | `pytest tests/unit/models/test_ensemble_trainer.py -x` | YES |
| PIPE-02 | WalkForwardBacktester produces quality badge from feature_df | unit | `pytest tests/unit/models/test_walk_forward.py -x` | YES |
| PIPE-03 | CalibrationStore.update() persists and get_confidence_mult() reads back | unit | `pytest tests/unit/models/test_calibration_store.py -x` | YES |
| PIPE-04 | compose_alpha node reads calibrated confidence_mult (not 1.0 default) | unit | `pytest tests/unit/agent_pipeline/test_compose_alpha.py -x` | YES |
| PIPE-05 | trigger_calibration_update wires resolved game → CalibrationStore | unit | `pytest tests/unit/jobs/test_result_watcher_calibration.py -x` | YES |
| PIPE-06 | retrain_scheduler triggers weekly job with correct import path | unit | `pytest tests/unit/jobs/test_retrain_scheduler.py -x` | YES |
| PIPE-07 | Full pipeline integration: data → ensemble → backtest → calibration → alpha | integration | `pytest tests/unit/models/test_pipeline_integration.py -x` | NO — Wave 0 |
| PIPE-08 | Promotion gate report JSON contains all 5 required gate fields | unit | `pytest tests/unit/models/test_promotion_gate.py -x` | NO — Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/unit/models/ tests/unit/jobs/ -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/models/test_pipeline_integration.py` — covers PIPE-07 (full pipeline integration)
- [ ] `tests/unit/models/test_promotion_gate.py` — covers PIPE-08 (gate report structure)
- [ ] Verify `pytest.ini` or root `pyproject.toml` has pytest configuration (check `testpaths`, `asyncio_mode`)

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-sport models (NFL, NBA only) | All 5 sports planned | Phase 7 deliverable | NCAAB/MLB/NHL require data extension |
| `confidence_mult = 1.0` hardcoded | Read from CalibrationStore per sport | Phase 5 | compose_alpha now reflects real OOS quality |
| Manual Platt calibration | CalibrationStore.update() with LogisticRegression fit | Phase 5 | Automated per-sport calibration on game resolution |
| `BacktestEngine` with in-memory dict stubs | `WalkForwardBacktester.run_with_model_inference()` | Phase 5 | Honest OOS badge without DB dependency |
| `from sharpedge_feeds.supabase_client` | `from sharpedge_db.client` | Phase 7 bug fix | Scheduler actually triggers retrain |

**Deprecated/outdated:**
- `retrain_scheduler.py` import `sharpedge_feeds.supabase_client`: wrong path, must be fixed
- Training only NFL/NBA: scripts must be extended for all 5 sports before promotion gate can be evaluated

---

## Open Questions

1. **NCAAB historical data source**
   - What we know: ESPN endpoint provides current-week scoreboard only, not multi-season history
   - What's unclear: Is there a Kaggle NCAAB dataset suitable for betting model training?
   - Recommendation: For Phase 7, use ESPN NCAAB scoreboard for current data; document that full multi-season NCAAB history requires separate sourcing. Do not block phase on this — skip ensemble training for NCAAB if insufficient data.

2. **Exact Brier score threshold for promotion gate**
   - What we know: `BRIER_BASELINE = 0.25`, `BRIER_GOOD = 0.22` in CalibrationStore
   - What's unclear: The CONTEXT.md says "derive from dataset characteristics" — this requires running calibration first
   - Recommendation: Use `BRIER_GOOD = 0.22` as the promotion threshold; sport-specific tuning after initial run.

3. **Maximum drawdown calculation for promotion gate**
   - What we know: `WalkForwardBacktester.run_with_model_inference()` computes per-window ROI but not cumulative drawdown
   - What's unclear: Is max drawdown computed over the walk-forward period or the full backtest horizon?
   - Recommendation: In `scripts/run_walk_forward.py`, compute max drawdown from the per-window ROI sequence (treat each window as a "bet period"). If all windows are positive, drawdown is 0.

---

## Sources

### Primary (HIGH confidence — direct codebase inspection)

- `scripts/download_historical_data.py` — confirmed sports coverage: NFL + NBA only; ESPN endpoints include MLB + NHL
- `scripts/process_historical_data.py` — confirmed: NFL + NBA processing only; `engineer_rolling_features()` and `engineer_ats_features()` are generic (reusable for other sports)
- `scripts/train_models.py` — confirmed: `train_sport_models(sport)` is parameterized; `_train_ensemble_for_sport()` validates `DOMAIN_FEATURES` columns
- `packages/models/src/sharpedge_models/ensemble_trainer.py` — confirmed: `EnsembleManager.train()` dual-path (dict or DataFrame); `oof_indices` stored; `save_model_versioned()` active/prev rotation
- `packages/models/src/sharpedge_models/walk_forward.py` — confirmed: `WalkForwardBacktester.run()` and `run_with_model_inference()`; quality badge thresholds
- `packages/models/src/sharpedge_models/calibration_store.py` — confirmed: `MIN_GAMES=50`, `BRIER_GOOD=0.22`, `confidence_mult` clamped `[0.5, 1.2]`
- `packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/compose_alpha.py` — confirmed: `_CAL_STORE` singleton; correct patch target
- `packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/run_models.py` — confirmed: `run_models()` calls `predict_ensemble()` via `MLModelManager`
- `apps/webhook_server/src/sharpedge_webhooks/jobs/retrain_scheduler.py` — confirmed bug: wrong import `sharpedge_feeds.supabase_client`
- `apps/webhook_server/src/sharpedge_webhooks/jobs/result_watcher.py` — confirmed: `trigger_calibration_update()` wiring
- `tests/` directory scan — confirmed: no `packages/models/tests/` directory; tests live in `tests/unit/models/`; 31 test files exist; `test_pipeline_integration.py` is missing

---

## Metadata

**Confidence breakdown:**
- Script gap analysis: HIGH — confirmed by direct file inspection and function tracing
- EnsembleManager interface: HIGH — full source read
- CalibrationStore thresholds: HIGH — constants confirmed from source
- compose_alpha integration: HIGH — both node and model source confirmed
- NCAAB data sourcing: LOW — ESPN endpoint available but historical coverage unverified
- Promotion gate thresholds: MEDIUM — Brier threshold derived from existing constants; drawdown limit undefined

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable codebase; fast-moving only if new packages added to workspace)
