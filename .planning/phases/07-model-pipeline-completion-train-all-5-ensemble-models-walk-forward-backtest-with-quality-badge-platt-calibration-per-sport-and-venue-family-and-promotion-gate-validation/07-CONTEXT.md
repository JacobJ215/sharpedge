# Phase 7: Model Pipeline Completion — Context

**Gathered:** 2026-03-14
**Status:** Ready for planning
**Source:** PRD Express Path (docs/NEXT_PHASES_BRIEF.md — Item 1)

<domain>
## Phase Boundary

Phase 7 completes the model pipeline so that all 5 ensemble models are trained, calibrated, walk-forward validated, and gated through honest promotion criteria. At the end of this phase:
- Historical data is downloaded and processed for all supported sports
- All 5 models trained with the EnsembleManager stacking layer (no leakage)
- Walk-forward backtest produces a quality badge of `high` or `excellent`
- Platt calibration runs per model, per sport, and per venue family
- The `confidence_mult` in composite alpha scores reflects real out-of-sample quality
- Venue-specific calibration baselines established for Kalshi, Polymarket, and sportsbooks (Phase 6 extension)
- Full pipeline integration tested: raw data → alpha score → Discord alert

**NOT in Phase 7 scope:**
- Frontend wiring (Phase 8)
- Phase 6 venue adapter live production connections (read-only calibration data is fine)
- New model architectures beyond the 5 already specified in Phase 5

**Depends on:** Phase 5 (EnsembleManager, CalibrationStore, WalkForwardBacktester exist), Phase 6 (venue adapters for venue-specific calibration)

</domain>

<decisions>
## Implementation Decisions

### Data Pipeline (LOCKED)
- Run `scripts/download_historical_data.py` for NBA, NFL, NCAAB, MLB, NHL
- Run `scripts/process_historical_data.py` to produce feature-complete datasets
- Verify `FeatureAssembler` produces correct `GameFeatures` for all sports
- Confirm time-correct train/validation/test splits — no lookahead bias whatsoever

### Model Training (LOCKED)
- Train all 5 ensemble models via `EnsembleManager`:
  1. Team form model (last 10 results, opponent strength, rest days)
  2. Matchup history model (head-to-head splits)
  3. Injury impact model (injury report integration)
  4. Market sentiment model (line movement velocity, public betting %)
  5. Weather/travel model (home/away splits, travel penalty)
- Train EnsembleManager stacking layer on out-of-fold predictions
- OOF indices must be stored alongside OOF predictions (leakage prevention — established in STATE.md)
- Persist trained model artifacts to `data/models/` (excluded from git via .gitignore)
- Note: `data/models/` is gitignored — scripts must handle missing model files gracefully

### Walk-Forward Backtesting (LOCKED)
- Run `WalkForwardBacktester` (Phase 1/5)
- Non-overlapping windows, no lookahead
- Per-window breakdown: win rate, ROI, edge after fees
- Generate quality badge: `low / medium / high / excellent`
- Quality badge must be `high` or `excellent` before promotion

### Platt Calibration (LOCKED)
- Run `CalibrationStore` on lagged (not live) out-of-sample data only
- Fit Platt scaling per model, per sport, per market family
- Update `confidence_mult` used in composite alpha score
- Calibration plots must be inspected for overfit before signing off

### Venue-Specific Calibration (LOCKED — Phase 6 extension)
- Kalshi: calibration by category and time-to-close
- Polymarket: calibration reports
- Sportsbooks: no-vig calibration by sport and bet type (moneyline, spread, total)
- Cross-venue dislocation baseline: consensus price benchmark established

### Integration Tests (LOCKED)
- `packages/models/tests/` — full model pipeline integration test
- Verify `compose_alpha()` incorporates calibrated `confidence_mult` correctly
- Verify `run_models()` wiring in webhook_server/jobs
- Verify weekly retrain scheduler triggers correctly

### Promotion Gate Checklist (LOCKED — all must pass before any model goes live)
- Calibration error < threshold (Brier score or ECE)
- Minimum post-cost edge > 2% on test set
- Maximum drawdown within limit on walk-forward windows
- Minimum 30-day paper stability period (tracked, not enforced in code for this phase)
- Walk-forward quality badge: `high` or `excellent`

### Claude's Discretion
- Exact threshold values for calibration error (derive from dataset characteristics)
- Whether to create a `scripts/train_models.py` or extend existing scripts
- How to structure calibration report output (JSON, text, or both)
- Whether venue-specific calibration runs as a separate script or extension of existing calibration
- Internal structure of promotion gate report artifact

</decisions>

<specifics>
## Specific Ideas from Brief

- The `_CAL_STORE singleton` in compose_alpha ensures single joblib read per process (from STATE.md — important for integration)
- `EnsembleManager.train()` accepts `dict[str, np.ndarray]` OR `pd.DataFrame` (dual-path established in Phase 5)
- `AsyncIOScheduler._eventloop` must be set explicitly before start() for weekly retrain scheduler
- `trigger_calibration_update` falls back to resolved_game data point when Supabase unavailable
- OOF indices stored alongside `oof_preds_` in EnsembleManager (leakage verification)
- Lazy EnsembleManager import inside MLModelManager to avoid circular import
- `devig_shin_n_outcome` now available in no_vig.py (Phase 6) — use for sportsbook venue calibration

</specifics>

<deferred>
## Deferred (Explicitly Out of Scope for Phase 7)

- Frontend wiring — Phase 8
- Live execution on any venue — later phase
- New model architectures beyond the 5 specified
- Paper trading / shadow mode — later phase
- 30-day paper stability period enforcement in code (tracked manually in this phase)

</deferred>

---

*Phase: 07-model-pipeline-completion*
*Context gathered: 2026-03-14 via PRD Express Path (docs/NEXT_PHASES_BRIEF.md)*
