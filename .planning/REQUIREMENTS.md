# Requirements: SharpEdge v2.0

**Defined:** 2026-03-15
**Core Value:** Surface high-alpha betting edges — ranked by composite probability score — before anyone else sees them, with bankroll risk quantified so users bet the right size every time.

## v2.0 Requirements

### Execution Pipeline (EXEC)

- [ ] **EXEC-01**: Operator can run shadow-mode execution that logs order intents without submitting to Kalshi
- [ ] **EXEC-02**: Shadow mode records market_id, predicted edge, Kelly-sized amount, and timestamp per signal to a ledger
- [ ] **EXEC-03**: Operator can enable live Kalshi CLOB order submission via `ENABLE_KALSHI_EXECUTION` env flag
- [ ] **EXEC-04**: System enforces per-market and per-day max-exposure limits before any order intent is created
- [ ] **EXEC-05**: System polls Kalshi order status after submission and records fills and cancellations in SettlementLedger

### Model Training (TRAIN)

- [x] **TRAIN-01**: Operator can run `download_pm_historical.py` against live Kalshi + Polymarket APIs to backfill resolved markets
- [x] **TRAIN-02**: Operator can run `process_pm_historical.py` to produce per-category feature DataFrames from the backfill
- [x] **TRAIN-03**: Operator can run `train_pm_models.py` to produce per-category `.joblib` RandomForest artifacts
- [x] **TRAIN-04**: Training pipeline emits a JSON report with quality badge, calibration score, and category market counts

### Ablation & Validation (ABLATE)

- [ ] **ABLATE-01**: Operator can run an ablation backtest comparing fee-adjusted fallback vs trained-model edge on historical paper data
- [ ] **ABLATE-02**: Ablation report shows edge delta (model vs fallback) per category and overall, with configurable pass/fail threshold

### Live Capital Gate (GATE)

- [ ] **GATE-01**: System rejects `ENABLE_KALSHI_EXECUTION=true` unless trained `.joblib` artifacts exist for all 5 categories
- [ ] **GATE-02**: System requires a configurable N-day paper-trading period with acceptable edge-to-fill ratio before live flag is honoured
- [ ] **GATE-03**: Operator completes a manual review step (CLI confirmation + timestamped log entry) before enabling live execution
- [ ] **GATE-04**: System auto-disables live execution if daily realized loss exceeds a configurable drawdown threshold

### Dashboard (DASH)

- [ ] **DASH-01**: Web dashboard shows execution status (paper vs live, flag state, last signal timestamp)
- [ ] **DASH-02**: Web dashboard shows paper-trading summary (signal count, would-have-been trade log, edge distribution chart)

## v3 Requirements

Deferred to future milestone.

### Polymarket Live Execution

- **POLY-EXEC-01**: Operator can enable live Polymarket CLOB order submission via flag
- **POLY-EXEC-02**: Polymarket wallet/CLOB auth abstraction handles key management
- **POLY-EXEC-03**: Fill tracking and reward attribution for Polymarket maker positions

### Advanced Execution

- **EXEC-ADV-01**: Passive quoting strategy (make not take) for Kalshi CLOB
- **EXEC-ADV-02**: Multi-leg correlated position netting across Kalshi + Polymarket
- **EXEC-ADV-03**: Slippage and queue-position estimation before order submission

### Previously Deferred (from v1.0)

- **ADV-01**: Model disagreement alerts (when 2+ ensemble models strongly disagree)
- **ADV-02**: Performance attribution (which model/feature drives wins per sport/market)
- **ADV-03**: A/B test alpha thresholds (separate alert groups by alpha band)
- **ADV-04**: Walk-forward validation dashboard (web page showing historical model performance windows)
- **PLAT-01**: Line movement chart (FinnAI-style time-series line history chart per game)
- **PLAT-02**: iOS home screen widget (bankroll + pending bets)
- **PLAT-03**: Multi-sport portfolio correlation matrix

## Out of Scope

| Feature | Reason |
|---------|--------|
| Automated bet placement for sportsbooks | Regulatory risk; user places sportsbook bets manually |
| Polymarket live execution | Wallet/CLOB auth complexity; defer to v2.1 after paper validation |
| Social / community features | Wrong user profile; serious bettors don't want feeds |
| AI-generated narrative content | Commoditized; adds no edge |
| Direct sportsbook account linking | API access restrictions; regulatory complexity |
| Real-time chat between users | Not core to value proposition |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| EXEC-01 | Phase 11 | Pending |
| EXEC-02 | Phase 11 | Pending |
| EXEC-03 | Phase 12 | Pending |
| EXEC-04 | Phase 11 | Pending |
| EXEC-05 | Phase 12 | Pending |
| TRAIN-01 | Phase 10 | Complete |
| TRAIN-02 | Phase 10 | Complete |
| TRAIN-03 | Phase 10 | Complete |
| TRAIN-04 | Phase 10 | Complete |
| ABLATE-01 | Phase 13 | Pending |
| ABLATE-02 | Phase 13 | Pending |
| GATE-01 | Phase 13 | Pending |
| GATE-02 | Phase 13 | Pending |
| GATE-03 | Phase 13 | Pending |
| GATE-04 | Phase 13 | Pending |
| DASH-01 | Phase 14 | Pending |
| DASH-02 | Phase 14 | Pending |

**Coverage:**
- v2.0 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0

---
*Requirements defined: 2026-03-15*
*Last updated: 2026-03-15 — traceability table updated after roadmap creation*
