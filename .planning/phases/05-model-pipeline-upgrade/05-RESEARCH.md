# Phase 5: Model Pipeline Upgrade - Research

**Researched:** 2026-03-14
**Domain:** ML ensemble stacking, Platt calibration, feature engineering, walk-forward backtesting, job scheduling
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Meta-learner (stacking):** 5 base models produce probabilities; logistic regression (6th model) combines them into final probability
- **Calibration trigger:** After each individual resolved game via `result_watcher.py` hook point
- **Calibration scope:** Per-sport (NFL/NBA tracked separately); fallback to `confidence_mult = 1.0` if sport has fewer than 50 resolved games
- **Calibration penalty:** `confidence_mult < 1.0` when Brier score is high — miscalibrated model actively reduces alpha scores
- **Ensemble models:** (1) team form — last 10 game rolling stats; (2) matchup history — H2H results/cover rates; (3) injury impact — ESPN injury reports; (4) market sentiment — line movement velocity + public betting %; (5) weather/travel — weather client + timezone crossings
- **Live features:** OddsAPI / public betting clients pulled on-demand at inference time
- **Rolling team stats:** Query from Supabase historical game table (last 10 results, home/away splits, opponent strength)
- **Missing features:** Sport-specific median imputation; model still runs
- **Rest days:** Compute from game schedule in Supabase (date diff between games)
- **Full retrain:** Weekly cron job — all 5 base models + meta-learner
- **Platt recalibration:** After every resolved game (separate lighter-weight job)
- **Version policy:** Replace active model in place; keep `{model_name}_prev.joblib` for rollback; store `model_version` with every BacktestResult

### Claude's Discretion
- Exact `confidence_mult` formula (clamping range, Brier score baseline per sport)
- Meta-learner variant (logistic regression preferred, logistic is standard for stacking)
- Training data partitioning for meta-learner (must use out-of-fold predictions to avoid leakage)
- Specific ESPN injury API endpoints and field mapping
- Cron scheduling mechanism (apscheduler, cron tab, or webhook_server background task)
- DB schema additions for `model_version` field in BacktestResult

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| QUANT-07 | System continuously recalibrates ML model confidence using Platt scaling after each game resolves | Platt sigmoid fit + Brier-score-based confidence_mult formula; result_watcher.py hook; per-sport storage in joblib |
| MODEL-01 | Prediction ensemble uses 5 models with calibrated weights (meta-learner stacking) | StackingClassifier data-leakage mechanics; out-of-fold prediction pattern; LogisticRegression meta-learner |
| MODEL-02 | Feature builder assembles game feature vector from last 10 results, opponent strength, rest days, injury report, home/away splits, line movement velocity, public betting %, key number proximity | Feature source mapping to existing clients; GameFeatures dataclass extension; ESPN injury endpoint mapping; sport-specific imputation strategy |
</phase_requirements>

---

## Summary

Phase 5 replaces two placeholder values with real ML outputs: `confidence_mult = 1.0` in `compose_alpha.py:49` and `model_prob = 0.52` in `run_models.py:32`. Every downstream surface (API, web, mobile, Discord) already consumes these values — Phase 5 makes them accurate.

The three-part upgrade follows a clear dependency order: (1) **feature assembly** (MODEL-02) must exist before any model can be trained, (2) **5-model ensemble with meta-learner** (MODEL-01) replaces the single GBM in `ml_inference.py`, and (3) **rolling Platt calibration** (QUANT-07) wires into `result_watcher.py` to update `confidence_mult` after each game resolves. The walk-forward backtester (`walk_forward.py`) already runs on prediction IDs — Phase 5 needs it to run actual inference per window to produce honest quality badges.

The codebase is well-positioned: `train_models.py` has a working `CalibratedClassifierCV + TimeSeriesSplit` pipeline; all five data feed clients exist in `packages/data_feeds/`; `BacktestEngine` stores predictions; and `GameFeatures` has a `to_array()` method that just needs more fields. The primary engineering work is (a) extending `GameFeatures` with MODEL-02 fields, (b) building `FeatureAssembler` that pulls live data at inference time, (c) restructuring `train_models.py` to train 5 separate base models then a meta-learner, and (d) adding a `CalibrationStore` that persists per-sport sigmoid parameters.

**Primary recommendation:** Build in three waves — Wave 0 (RED test stubs + schema additions), Wave 1 (feature assembler + extended GameFeatures), Wave 2 (5-model training + meta-learner + MLModelManager upgrade), Wave 3 (Platt calibration store + result_watcher hook + walk-forward inference integration).

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scikit-learn | >=1.3 (already in workspace) | StackingClassifier, LogisticRegression, CalibratedClassifierCV, TimeSeriesSplit | Already used in train_models.py; StackingClassifier handles OOF meta-features cleanly |
| joblib | already installed | Model serialization, `_prev` versioning pattern | Established pattern in project; joblib.dump already used |
| numpy | already installed | Feature arrays, imputation | GameFeatures.to_array() already uses numpy |
| pandas | already installed | Training data, rolling window calculations | process_historical_data.py already uses pandas |
| scipy.special | already installed | `expit()` for Platt sigmoid application at inference | Used in backtesting.py; expit IS the sigmoid |
| apscheduler | >=3.10 | Weekly retrain cron inside webhook_server async context | AsyncIOScheduler integrates with asyncio event loop; no separate process needed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sklearn.calibration.calibration_curve | part of sklearn | Validate Platt fit quality (plot predicted vs actual) | During training metrics reporting only |
| sklearn.metrics.brier_score_loss | part of sklearn | Compute Brier score for confidence_mult formula | After every Platt recalibration cycle |
| sklearn.linear_model.LogisticRegression | part of sklearn | Meta-learner for ensemble stacking | Fits on OOF base model probabilities |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sklearn.StackingClassifier | Manual OOF loop | StackingClassifier's `passthrough=False` is cleaner but less transparent; manual OOF loop is more explicit about leakage prevention and easier to unit test |
| apscheduler | system cron + subprocess | apscheduler runs inside the existing async event loop; system cron requires separate process management and env var propagation |
| LogisticRegression meta-learner | Ridge or GBM | Logistic regression is the canonical stacking meta-learner — interpretable, low variance, avoids overfitting on 5 features |

**Installation:**
```bash
uv add apscheduler --package apps/webhook_server
```
(scikit-learn, joblib, numpy, pandas, scipy already installed)

---

## Architecture Patterns

### Recommended Project Structure

New modules to create:

```
packages/models/src/sharpedge_models/
├── ml_inference.py          # EXTEND: add predict_ensemble(), load 5 base + meta-learner
├── feature_assembler.py     # NEW: FeatureAssembler class, async, pulls live + DB data
├── calibration_store.py     # NEW: CalibrationStore, per-sport sigmoid params, joblib persistence
└── ensemble_trainer.py      # NEW: train_ensemble() orchestrates 5-model + meta-learner

apps/webhook_server/src/sharpedge_webhooks/jobs/
├── result_watcher.py        # EXTEND: call trigger_calibration_update() after WIN stored
└── retrain_scheduler.py     # NEW: apscheduler weekly retrain job

packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/
├── compose_alpha.py         # EXTEND: replace confidence_mult=1.0 with CalibrationStore lookup
└── run_models.py            # EXTEND: replace model_prob=0.52 with predict_ensemble() call
```

### Pattern 1: Out-of-Fold Meta-Learning (No Leakage)

**What:** Train each base model on K-1 folds, predict on fold K. Collect OOF predictions for all training rows. Then train meta-learner on these OOF predictions.

**When to use:** Any time you stack classifiers — OOF is the only correct way to prevent data leakage from base models to meta-learner.

**Why sklearn.StackingClassifier is preferred:**

```python
# Source: sklearn docs https://scikit-learn.org/stable/modules/ensemble.html#stacked-generalization
from sklearn.ensemble import StackingClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit

# Each estimator produces P(class=1) as a feature for the meta-learner.
# StackingClassifier uses cross_val_predict internally to generate OOF predictions
# — base models never see their own test fold during meta-feature generation.
base_estimators = [
    ("form", GradientBoostingClassifier()),       # Model 1: team form
    ("matchup", GradientBoostingClassifier()),    # Model 2: matchup history
    ("injury", GradientBoostingClassifier()),     # Model 3: injury impact
    ("sentiment", GradientBoostingClassifier()),  # Model 4: market sentiment
    ("weather", GradientBoostingClassifier()),    # Model 5: weather/travel
]

stack = StackingClassifier(
    estimators=base_estimators,
    final_estimator=LogisticRegression(C=1.0, max_iter=500),
    cv=TimeSeriesSplit(n_splits=5),   # CRITICAL: time-series CV, not random
    stack_method="predict_proba",
    passthrough=False,                 # meta-learner sees only base model probs
)
```

**CRITICAL CONSTRAINT:** Each base model must be trained on a feature subset corresponding to its factor domain. They do NOT share the same feature matrix X. The `StackingClassifier` approach with a single X matrix would merge all features — for domain-specific base models, manual OOF training per model is more appropriate.

**Manual OOF approach (preferred for domain-separated base models):**

```python
# Pseudocode — actual implementation in ensemble_trainer.py
from sklearn.model_selection import TimeSeriesSplit
import numpy as np

tscv = TimeSeriesSplit(n_splits=5)
oof_preds = np.zeros((len(X_all_games), 5))  # 5 base models

for model_idx, (feature_cols, base_model) in enumerate(base_models):
    X = X_all_games[feature_cols].values
    y = y_all_games.values
    for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(X)):
        clone = clone_estimator(base_model)
        clone.fit(X[train_idx], y[train_idx])
        oof_preds[val_idx, model_idx] = clone.predict_proba(X[val_idx])[:, 1]

# Train meta-learner on OOF predictions only
meta_learner = LogisticRegression(C=1.0)
# Use only rows where all 5 models have OOF predictions (first n_splits folds may be partial)
meta_learner.fit(oof_preds[valid_rows], y[valid_rows])
```

### Pattern 2: Platt Calibration Store

**What:** After each resolved game, fit a per-sport sigmoid (Platt scaling) on the last N resolved predictions. Persist the sigmoid's `(a, b)` parameters. At inference, `confidence_mult = sigmoid(raw_prob)` adjustment; for `confidence_mult` specifically, use the Brier score of recent predictions.

**The distinction:** Phase 5 uses Platt scaling in TWO ways:
1. **Training-time calibration** (existing): `CalibratedClassifierCV(method="isotonic")` wraps each base model so `predict_proba()` outputs calibrated probabilities.
2. **Runtime confidence_mult** (new): A lightweight per-sport post-hoc calibrator that converts the ensemble's rolling Brier score into a multiplicative penalty.

**Confidence mult formula (Claude's discretion, recommended):**

```python
# Brier score baseline for a coin-flip model = 0.25 (worst useful model)
# A perfect model has Brier score = 0.0
# A well-calibrated ~55% model has Brier score ~ 0.22-0.24
BRIER_BASELINE = 0.25  # sport-agnostic baseline
BRIER_GOOD = 0.22      # threshold below which model earns full credit

def compute_confidence_mult(brier_score: float) -> float:
    """Convert Brier score to confidence multiplier clamped to [0.5, 1.2]."""
    if brier_score <= BRIER_GOOD:
        # Model is performing well — reward with up to 1.2x
        mult = 1.0 + (BRIER_GOOD - brier_score) / BRIER_GOOD * 0.2
    else:
        # Model is underperforming baseline — penalize
        mult = 1.0 - (brier_score - BRIER_GOOD) / (BRIER_BASELINE - BRIER_GOOD) * 0.5
    return max(0.5, min(1.2, mult))
```

### Pattern 3: Feature Assembler (Inference-Time)

**What:** At inference time, assemble all MODEL-02 features from multiple async sources.

**Data sources per feature:**

| Feature | Source | Client/Method |
|---------|--------|---------------|
| Last 10 results, ATS trend | Supabase historical_games table | Supabase query, `ORDER BY game_date DESC LIMIT 10` |
| Opponent strength (SOS) | Supabase historical_games | Aggregate opponent win rates |
| Home/away splits | Supabase historical_games | Filter by home_team / away_team |
| Rest days | Supabase schedule | `game_date - prev_game_date` |
| Injury report | ESPN API | `espn_client.get_scoreboard()` + competition.injuries field |
| Line movement velocity | Supabase line_movements table | `movement.py` records exist in DB; query last 3 movements, compute delta/time |
| Public betting % | `public_betting_client.get_public_betting()` | Live pull at inference |
| Key number proximity | `analyze_zone(spread_line, sport)` | Already in run_models.py, reuse |
| Weather/travel penalty | `weather_client.get_game_weather()` | Existing client |
| Timezone crossings | Compute from team city timezones | Static lookup dict (team → timezone) |

### Pattern 4: Versioned Model Persistence

```python
# Versioning pattern for joblib models
from pathlib import Path
import joblib

def save_model_versioned(model_bundle: tuple, name: str, models_dir: Path) -> None:
    """Save model with _prev rollback copy."""
    active_path = models_dir / f"{name}_model.joblib"
    prev_path = models_dir / f"{name}_model_prev.joblib"

    # Rotate: active -> prev
    if active_path.exists():
        if prev_path.exists():
            prev_path.unlink()  # discard version N-2
        active_path.rename(prev_path)

    joblib.dump(model_bundle, active_path)
```

### Pattern 5: APScheduler Weekly Retrain (async)

```python
# Source: apscheduler docs https://apscheduler.readthedocs.io/en/3.x/userguide.html
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job("cron", day_of_week="sun", hour=2)
async def weekly_retrain_job():
    """Retrain all 5 base models + meta-learner every Sunday at 2am UTC."""
    await run_ensemble_training()

# Start scheduler inside the FastAPI lifespan or main() startup
scheduler.start()
```

### Anti-Patterns to Avoid

- **Using StackingClassifier with a single feature matrix for domain-specific models:** Each base model should only see its own factor domain's features. Merging all features into one X destroys the interpretability benefit of factor decomposition.
- **Fitting Platt sigmoid on the full training set:** Platt parameters must be fit on a held-out validation set (or via cross-validation). Fitting on training data produces overconfident probabilities.
- **Re-using train data for meta-learner:** Meta-learner must be fit only on OOF predictions. This is the single most common stacking mistake.
- **Global model manager without sport-specific routing:** `MLModelManager` currently has one model per `{sport}_{market_type}`. Phase 5 needs `predict_ensemble(sport, features)` — a new method, not replacement.
- **Blocking the async event loop during retraining:** `train_ensemble()` is CPU-bound. Use `asyncio.get_event_loop().run_in_executor(None, train_fn)` or a background thread via APScheduler's `ThreadPoolExecutor`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Out-of-fold meta-feature generation | Manual nested loop with index tracking | `cross_val_predict(base_model, X, y, cv=tscv, method="predict_proba")` | Handles edge cases (partial folds, stratification) correctly |
| Brier score computation | `np.mean((y_pred - y_true)**2)` loop | `sklearn.metrics.brier_score_loss(y_true, y_pred)` | Correct sign convention; already used in train_models.py |
| Sigmoid application | Manual logistic function | `scipy.special.expit(a * score + b)` | Numerically stable; already available in scipy |
| AUC-ROC for calibration validation | Concordant pair counting | `sklearn.metrics.roc_auc_score` | Already established pattern in backtesting.py (line 329) |
| Time-zone offset computation | String parsing + UTC arithmetic | `zoneinfo.ZoneInfo` (stdlib 3.9+) | Available in Python 3.12; no extra dep needed |

**Key insight:** The sklearn calibration and metrics ecosystem handles all edge cases for small samples, monotone failures, and numerical stability. Custom implementations of probability calibration have historically introduced subtle sign errors and overflow issues in this codebase (see resolved issues in STATE.md).

---

## Common Pitfalls

### Pitfall 1: Data Leakage in Meta-Learner Training

**What goes wrong:** If base models are fit on all training data then their `predict_proba()` is used to generate meta-features for the same training set, the meta-learner sees "cheated" predictions. This inflates in-sample performance by 3–8 percentage points with no out-of-sample benefit.

**Why it happens:** It feels natural to train base models, then pass the training set through them again to get "features" for the meta-learner.

**How to avoid:** Always generate meta-features using cross-validated predictions (`cross_val_predict`). Only train base models on the full training set AFTER the meta-learner has been trained on OOF predictions.

**Warning signs:** In-sample stacking accuracy much higher than any individual base model; out-of-sample accuracy no better than best single model.

### Pitfall 2: Wrong CV Type for Time-Series Data

**What goes wrong:** Using `KFold` or `StratifiedKFold` for sports betting data allows future games to appear in the training fold, creating lookahead bias. A model trained this way can appear 60%+ accurate in CV but perform at ~50% in production.

**Why it happens:** sklearn defaults to `KFold`. Developers familiar with ML but not time-series data use the default.

**How to avoid:** Always use `TimeSeriesSplit` for any sports data. Already established in `train_models.py` — apply the same pattern to all new base model training.

**Warning signs:** CV accuracy significantly higher than walk-forward out-of-sample accuracy.

### Pitfall 3: Platt Calibration on Live Data

**What goes wrong:** Triggering Platt recalibration using predictions made on data the model was trained on produces circular calibration — the sigmoid learns to correct the model's training errors, not its generalization errors.

**Why it happens:** `result_watcher.py` has access to all resolved predictions; it's tempting to calibrate on all of them.

**How to avoid:** Calibrate only on predictions made AFTER the model's training cutoff date. Store `trained_at` timestamp (already in metrics JSON) and filter calibration data to `resolved_at > trained_at`. The 50-game threshold guards against this partially but doesn't fully solve it.

**Warning signs:** `confidence_mult` starts very high then crashes after enough data accumulates.

### Pitfall 4: ESPN Injury Field Mapping

**What goes wrong:** ESPN's public API returns injury data inconsistently — some endpoints nest it under `competitions[].competitors[].injuries[]`, others under `athletes[]`. The field name for status changes between endpoints.

**Why it happens:** ESPN's public API (site.api.espn.com) is undocumented; field structure is inferred by inspection.

**How to avoid:** Use the scoreboard endpoint (`/scoreboard`) which includes game-specific injury context. Key fields: `athletes[].injuries[].status` values are: `"Questionable"`, `"Doubtful"`, `"Out"`, `"IR"`, `"Day-To-Day"`. Map to a numeric impact: `{"Out": -1.0, "Doubtful": -0.6, "Questionable": -0.3, "Day-To-Day": -0.2}`.

**Warning signs:** 95% of injury_impact features are 0.0 (neutral) suggesting the field path is wrong.

### Pitfall 5: WalkForwardBacktester on Prediction IDs vs Model Inference

**What goes wrong:** The existing `WalkForwardBacktester.run()` computes win rates and ROI from stored `BacktestResult` objects. It does NOT re-run model inference per window. For Phase 5's quality badge to be honest, the backtester must actually call the ensemble model on each test window's feature vectors.

**Why it happens:** Phase 1 implemented the backtester to work with whatever predictions are in the DB, which was correct for Phase 1. Phase 5 needs the backtester to drive model training + inference.

**How to avoid:** Add a `run_with_model_inference(feature_data, model_fn, n_windows)` method to `WalkForwardBacktester` that (1) splits feature data into windows, (2) trains the model on the train split, (3) runs inference on the test split, (4) computes metrics. This is the honest out-of-sample validation the ROADMAP requires.

### Pitfall 6: Blocking the Webhook Server Event Loop

**What goes wrong:** `train_ensemble()` involves GBM training with `n_estimators=100` per model × 5 models × 5 CV folds = 2500 model fits. This is CPU-bound and will block the asyncio event loop for 30–120 seconds, preventing FastAPI from serving requests.

**How to avoid:** Use `asyncio.get_event_loop().run_in_executor(None, sync_train_fn)` for the blocking training call. APScheduler's `AsyncIOScheduler` with `executor='threadpool'` handles this transparently.

### Pitfall 7: Timezone Crossing Feature for NBA

**What goes wrong:** NBA teams cross multiple time zones regularly (e.g., Golden State to Boston = 3 zones). The weather_client.py has an `NFL_STADIUMS` dict but no NBA arena dict. If the feature assembler tries to look up an NBA team in `NFL_STADIUMS`, it returns `None` and the feature silently becomes 0.

**How to avoid:** Add `NBA_ARENAS` dict with `team_name → (city, timezone_str)` similar to `NFL_STADIUMS`. Use `zoneinfo` to compute timezone offset difference. Falls back to 0 (no penalty) if lookup fails — consistent with missing feature imputation strategy.

---

## Code Examples

### ESPN Injury Field Access (Verified by inspection of ESPN public API)

```python
# Source: site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard response shape
# Accessing injury data from scoreboard response
async def get_injury_impact(home_team: str, away_team: str, sport: str) -> tuple[float, float]:
    """Return (home_injury_score, away_injury_score) where -1.0 = all starters out."""
    client = ESPNClient()
    scoreboard = await client.get_scoreboard(sport)
    if not scoreboard:
        return 0.0, 0.0

    STATUS_IMPACT = {"Out": -1.0, "Doubtful": -0.6, "Questionable": -0.3, "Day-To-Day": -0.2}

    for event in scoreboard.get("events", []):
        for competition in event.get("competitions", []):
            for competitor in competition.get("competitors", []):
                team_name = competitor.get("team", {}).get("displayName", "")
                injuries = competitor.get("injuries", [])  # May be absent
                total_impact = sum(
                    STATUS_IMPACT.get(inj.get("status", ""), 0.0)
                    for inj in injuries
                    # Filter to probable starters only if "starter" field exists
                )
                # Map to home/away
    return home_impact, away_impact
```

### Platt CalibrationStore (Persistence)

```python
# calibration_store.py — new module
import joblib
from pathlib import Path
from dataclasses import dataclass
from sklearn.linear_model import LogisticRegression

@dataclass
class SportCalibration:
    """Per-sport Platt calibration parameters."""
    sport: str
    n_samples: int           # resolved games used for calibration
    brier_score: float       # current Brier score
    confidence_mult: float   # computed multiplier [0.5, 1.2]
    trained_at: str          # ISO timestamp
    # sigmoid stored as LogisticRegression fitted on shape (N, 1)
    sigmoid: LogisticRegression | None = None

class CalibrationStore:
    def __init__(self, store_path: Path):
        self._path = store_path
        self._calibrations: dict[str, SportCalibration] = {}

    def get_confidence_mult(self, sport: str) -> float:
        """Return confidence_mult for sport, default 1.0 if not enough data."""
        cal = self._calibrations.get(sport.lower())
        if cal is None or cal.n_samples < 50:
            return 1.0
        return cal.confidence_mult

    def update(self, sport: str, probs: list[float], outcomes: list[bool]) -> None:
        """Refit calibration from resolved game predictions."""
        # ... fit LogisticRegression on (probs, outcomes), compute Brier score
        # ... compute confidence_mult via formula
        # ... persist via joblib.dump
```

### Timezone Crossing Computation

```python
# Source: Python stdlib zoneinfo (Python 3.9+, available in Python 3.12 workspace)
from zoneinfo import ZoneInfo
from datetime import datetime, timezone

TEAM_TIMEZONES: dict[str, str] = {
    # NFL
    "Green Bay Packers": "America/Chicago",
    "New England Patriots": "America/New_York",
    "Los Angeles Rams": "America/Los_Angeles",
    "Denver Broncos": "America/Denver",
    # NBA
    "Golden State Warriors": "America/Los_Angeles",
    "Boston Celtics": "America/New_York",
    # ... etc
}

def compute_timezone_crossings(away_team: str, home_team: str) -> int:
    """Return number of timezone hours crossed by away team traveling to home venue."""
    away_tz = TEAM_TIMEZONES.get(away_team)
    home_tz = TEAM_TIMEZONES.get(home_team)
    if not away_tz or not home_tz:
        return 0  # Unknown teams — no penalty, consistent with imputation strategy
    now = datetime.now(timezone.utc)
    away_offset = now.astimezone(ZoneInfo(away_tz)).utcoffset().seconds // 3600
    home_offset = now.astimezone(ZoneInfo(home_tz)).utcoffset().seconds // 3600
    return abs(home_offset - away_offset)

def travel_penalty(away_team: str, home_team: str) -> float:
    """Return penalty factor: 0.0 (no travel) to -0.3 (cross-country)."""
    crossings = compute_timezone_crossings(away_team, home_team)
    if crossings >= 3:
        return -0.3
    elif crossings == 2:
        return -0.15
    return 0.0
```

### Supabase Query for Last 10 Results

```python
# Supabase query pattern — consistent with existing DB query patterns
def fetch_team_last_10(client, team_name: str, sport: str, before_date: str) -> list[dict]:
    """Fetch last 10 completed games for a team before a given date."""
    resp = (
        client.table("historical_games")
        .select("*")
        .eq("sport", sport)
        .or_(f"home_team.eq.{team_name},away_team.eq.{team_name}")
        .lt("game_date", before_date)
        .eq("is_complete", True)
        .order("game_date", desc=True)
        .limit(10)
        .execute()
    )
    return resp.data or []
```

### GameFeatures Extension (MODEL-02 Fields)

```python
# Extend existing GameFeatures dataclass in ml_inference.py
# New fields to add for MODEL-02 compliance:
@dataclass
class GameFeatures:
    # ... existing fields ...

    # Model 1: Team form (rolling 10-game)
    home_ppg_10g: float | None = None       # points per game, last 10
    home_papg_10g: float | None = None      # points allowed per game
    away_ppg_10g: float | None = None
    away_papg_10g: float | None = None
    home_ats_10g: float | None = None       # ATS cover rate, last 10
    away_ats_10g: float | None = None

    # Model 2: Matchup history (H2H)
    h2h_home_cover_rate: float | None = None   # home team ATS rate in H2H games
    h2h_total_games: int | None = None

    # Model 3: Injury impact
    home_injury_impact: float | None = None    # sum of STATUS_IMPACT for home
    away_injury_impact: float | None = None

    # Model 4: Market sentiment
    line_movement_velocity: float | None = None  # points moved / hours since open
    public_pct_home: float | None = None         # % tickets on home spread

    # Model 5: Weather/travel
    weather_impact_score: float | None = None    # from WeatherImpact.total_impact
    travel_penalty: float | None = None          # timezone crossings penalty

    # Additional MODEL-02 fields
    home_rest_days: int | None = None       # already exists
    away_rest_days: int | None = None       # already exists
    home_away_split_delta: float | None = None  # home win% - away win%
    opponent_strength_home: float | None = None  # avg opponent win rate
    opponent_strength_away: float | None = None
    key_number_proximity: float | None = None  # zone_strength from analyze_zone
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single GBM for spread/totals | 5-model domain-specific ensemble + logistic meta-learner | Phase 5 | model_prob goes from 0.52 default to actual ML output |
| confidence_mult = 1.0 (placeholder) | Brier-score-based confidence_mult per sport | Phase 5 | Alpha scores now penalize miscalibrated predictions |
| WalkForwardBacktester on stored IDs | WalkForwardBacktester with actual inference per window | Phase 5 | Quality badges become honest out-of-sample metrics |
| Isotonic calibration only at train time | Train-time isotonic + rolling Platt per-sport at runtime | Phase 5 | Model improves continuously without weekly full retrains |

**Deprecated/outdated patterns to replace:**
- `compose_alpha.py:49` — `confidence_mult = 1.0` placeholder (replace with `CalibrationStore.get_confidence_mult(sport)`)
- `run_models.py:32` — `model_prob = game_context.get("model_prob", 0.52)` (replace with `MLModelManager.predict_ensemble(sport, features)`)
- `BacktestResult` dataclass — needs `model_version: str` field added

---

## Open Questions

1. **ESPN Injury Endpoint Availability**
   - What we know: ESPNClient.get_scoreboard() returns competition data; injuries may be nested under competitors
   - What's unclear: Whether the public ESPN API consistently includes injury data vs only during game days; field name may differ between NFL and NBA
   - Recommendation: In Wave 1, add a `get_injuries(sport, team)` method to ESPNClient that falls back to empty list gracefully; log the full response shape for the first call to verify field path

2. **Supabase historical_games Table Schema**
   - What we know: `scripts/schema.sql` and `scripts/process_historical_data.py` exist; the training data pipeline writes to Supabase in Phase 4
   - What's unclear: Whether `historical_games` table has the exact columns needed for MODEL-02 feature queries (specifically: `home_team`, `away_team`, `home_covered`, `spread_line`, `game_date` as individual columns vs embedded JSON)
   - Recommendation: Read `scripts/schema.sql` before Wave 1 planning; if table doesn't exist with right columns, add a Wave 0 migration task

3. **OddsAPI Line Movement History**
   - What we know: `line_movements` table exists in DB (confirmed by `packages/database/src/sharpedge_db/queries/line_movements.py`); `movement.py` classifies movement types
   - What's unclear: Whether there is enough line movement history stored to compute `line_movement_velocity` (needs at least 2 timestamps per game)
   - Recommendation: Compute velocity from `line_movements` DB table (already populated by the OddsAPI scanner in Phase 3). If fewer than 2 records per game, fall back to 0.0 (median imputation).

4. **Action Network API for Public Betting %**
   - What we know: `public_betting_client.py` has an Action Network stub that returns `None`; falls back to estimated 55/45 home/away split with 0.3 confidence
   - What's unclear: Whether the estimated fallback (55/45) is good enough for the sentiment model to train meaningfully vs introducing noise
   - Recommendation: Model 4 (market sentiment) should be trained with the Action Network data as a feature only when `confidence >= 0.7`; otherwise use `line_movement_velocity` alone and impute the betting % with sport-specific median

5. **Weekly Retrain CPU Budget**
   - What we know: GBM with 100 estimators × 5 CV folds takes ~10-60 seconds per model on moderate hardware; 5 models = 5-10 minutes total
   - What's unclear: What hardware the webhook_server runs on and whether a 5-10 minute background task is acceptable
   - Recommendation: Cap base model `n_estimators=50` for weekly retrain job (lower quality but faster); run full `n_estimators=200` training manually via `scripts/train_models.py`

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0 + pytest-asyncio 0.24 |
| Config file | pyproject.toml (root) |
| Quick run command | `pytest tests/unit/models/ -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUANT-07 | CalibrationStore.get_confidence_mult returns 1.0 below 50 games | unit | `pytest tests/unit/models/test_calibration_store.py -x` | Wave 0 |
| QUANT-07 | CalibrationStore.update computes correct Brier score and confidence_mult | unit | `pytest tests/unit/models/test_calibration_store.py -x` | Wave 0 |
| QUANT-07 | result_watcher calls trigger_calibration_update after WIN bet stored | unit | `pytest tests/unit/jobs/test_result_watcher_calibration.py -x` | Wave 0 |
| QUANT-07 | confidence_mult propagates from CalibrationStore into compose_alpha output | unit | `pytest tests/unit/agent_pipeline/test_compose_alpha.py -x` | Wave 0 |
| MODEL-01 | Stacking ensemble produces probability in [0, 1] for known game input | unit | `pytest tests/unit/models/test_ensemble_trainer.py::test_predict_ensemble -x` | Wave 0 |
| MODEL-01 | OOF meta-features have zero overlap with training predictions (leakage check) | unit | `pytest tests/unit/models/test_ensemble_trainer.py::test_no_leakage -x` | Wave 0 |
| MODEL-01 | predict_ensemble returns 5 base model probs + meta-learner prob | unit | `pytest tests/unit/models/test_ml_inference.py::test_predict_ensemble -x` | Wave 0 |
| MODEL-02 | FeatureAssembler.assemble returns GameFeatures with all MODEL-02 fields | unit | `pytest tests/unit/models/test_feature_assembler.py -x` | Wave 0 |
| MODEL-02 | Missing features are imputed with sport-specific median, not 0.0 | unit | `pytest tests/unit/models/test_feature_assembler.py::test_imputation -x` | Wave 0 |
| MODEL-02 | timezone_crossings >= 2 produces travel_penalty < 0 | unit | `pytest tests/unit/models/test_feature_assembler.py::test_travel_penalty -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/unit/models/ -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/models/test_calibration_store.py` — covers QUANT-07 CalibrationStore unit tests
- [ ] `tests/unit/models/test_feature_assembler.py` — covers MODEL-02 FeatureAssembler unit tests
- [ ] `tests/unit/models/test_ensemble_trainer.py` — covers MODEL-01 stacking + leakage tests
- [ ] `tests/unit/jobs/test_result_watcher_calibration.py` — covers QUANT-07 hook integration
- [ ] `tests/unit/jobs/__init__.py` — new test subdirectory

---

## Sources

### Primary (HIGH confidence)

- Codebase direct read — `packages/models/src/sharpedge_models/ml_inference.py` — existing MLModelManager, GameFeatures, model loading patterns
- Codebase direct read — `scripts/train_models.py` — `CalibratedClassifierCV(method="isotonic", cv=tscv)`, `TimeSeriesSplit`, `Pipeline` patterns established and working
- Codebase direct read — `packages/models/src/sharpedge_models/walk_forward.py` — `WalkForwardBacktester`, `create_windows()`, `quality_badge_from_windows()` — full implementation confirmed
- Codebase direct read — `packages/models/src/sharpedge_models/backtesting.py` — `BacktestResult` dataclass, `BacktestEngine`, Brier score calculation at line 300
- Codebase direct read — `packages/models/src/sharpedge_models/alpha.py` — `compose_alpha()` formula, `BettingAlpha` dataclass
- Codebase direct read — `packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/compose_alpha.py:49` — `confidence_mult = 1.0` placeholder confirmed
- Codebase direct read — `packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/run_models.py:32` — `model_prob = game_context.get("model_prob", 0.52)` placeholder confirmed
- Codebase direct read — `packages/data_feeds/src/sharpedge_feeds/espn_client.py` — ESPNClient structure, available methods, injury field path gap identified
- Codebase direct read — `packages/data_feeds/src/sharpedge_feeds/weather_client.py` — WeatherClient, NFL_STADIUMS, `get_game_weather()` confirmed working
- Codebase direct read — `packages/data_feeds/src/sharpedge_feeds/public_betting_client.py` — PublicBettingClient, Action Network stub (returns None), 55/45 fallback

### Secondary (MEDIUM confidence)

- sklearn ensemble documentation (training knowledge, August 2025 cutoff) — `StackingClassifier` API, `cross_val_predict` for OOF generation, `TimeSeriesSplit` behavior
- apscheduler 3.x documentation (training knowledge) — `AsyncIOScheduler`, `scheduled_job("cron", ...)` pattern
- Python 3.12 stdlib (training knowledge) — `zoneinfo.ZoneInfo` availability confirmed for Python 3.12 workspace

### Tertiary (LOW confidence)

- ESPN public API field structure — injury data path inferred from known response shapes; ESPN's undocumented public API can change without notice; must verify at implementation time

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in workspace; no new uncertain dependencies
- Architecture: HIGH — patterns derived from existing codebase conventions; stacking pattern well-established in sklearn
- Feature engineering: MEDIUM — ESPN injury field path is LOW confidence; line movement velocity source is MEDIUM (DB table exists, query pattern not yet proven); all other features have confirmed data sources
- Pitfalls: HIGH — leakage and time-series CV pitfalls are deterministic sklearn behavior; ESPN API pitfall inferred from known API inconsistencies

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable sklearn APIs; ESPN API field structure LOW-confidence note valid ~7 days)
