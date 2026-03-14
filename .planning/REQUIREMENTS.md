# Requirements: SharpEdge v2

**Defined:** 2026-03-13
**Core Value:** Surface high-alpha betting edges — ranked by composite probability score — before anyone else sees them, with bankroll risk quantified so users bet the right size every time.

---

## v1 Requirements

Requirements for the v2 upgrade milestone. Each maps to a roadmap phase.

### Quant Engine

- [ ] **QUANT-01**: System calculates composite alpha score (EV × regime_scale × survival_prob × confidence_mult) for every betting opportunity
- [ ] **QUANT-02**: System simulates 2000 bankroll paths and returns ruin probability, P5/P50/P95 outcomes, and max drawdown distribution for a given bet
- [ ] **QUANT-03**: System classifies current betting market into one of 7 regime states (SHARP_VS_PUBLIC, STEAM_MOVE, PUBLIC_HEAVY, SHARP_CONSENSUS, THIN_MARKET, POST_NEWS, SETTLED) with confidence score
- [ ] **QUANT-04**: System detects when a spread/total is at or near a key number and returns historical cover rate, half-point value, and zone strength
- [ ] **QUANT-05**: System produces walk-forward backtest report with out-of-sample win rate, out-of-sample ROI, per-window results, and quality badge (low/medium/high/excellent)
- [ ] **QUANT-06**: System tracks CLV (closing line value) for each bet and updates user's CLV stats after game closes
- [x] **QUANT-07**: System continuously recalibrates ML model confidence using Platt scaling after each game resolves

### Agent Orchestration

- [x] **AGENT-01**: System routes all betting analysis requests through a 9-node LangGraph StateGraph (route_intent → fetch_context → detect_regime → run_models → calculate_ev → validate_setup → compose_alpha → size_position → generate_report)
- [x] **AGENT-02**: LLM setup evaluator returns PASS/WARN/REJECT decision with reasoning before any alert is dispatched
- [x] **AGENT-03**: BettingCopilot answers natural language questions about any game or market with full portfolio context (active bets, bankroll exposure, regime state)
- [x] **AGENT-04**: BettingCopilot supports at least 10 tools: get_active_bets, get_portfolio_stats, analyze_game, search_value_plays, check_line_movement, get_sharp_indicators, estimate_bankroll_risk, get_prediction_market_edge, compare_books, get_model_predictions
- [x] **AGENT-05**: All value play alerts are ranked by alpha score before dispatching (highest alpha posts first)

### Prediction Market Intelligence

- [x] **PM-01**: System scans all active Kalshi markets, computes model probability vs market probability, and surfaces edges >3% with alpha score
- [x] **PM-02**: System scans Polymarket markets with same edge detection as Kalshi
- [x] **PM-03**: System classifies prediction market regime (Discovery, Consensus, News Catalyst, Pre-Resolution, Sharp Disagreement) and adjusts edge threshold accordingly
- [x] **PM-04**: System detects correlated positions across sportsbook bets and prediction markets and warns user when portfolio correlation coefficient exceeds 0.6

### API Layer

- [x] **API-01**: FastAPI exposes GET /api/v1/value-plays with min_alpha filter returning alpha-ranked opportunities
- [x] **API-02**: FastAPI exposes GET /api/v1/games/:id/analysis returning full analysis state for a game
- [x] **API-03**: FastAPI exposes POST /api/v1/copilot/chat with SSE streaming for BettingCopilot responses
- [x] **API-04**: FastAPI exposes GET /api/v1/users/:id/portfolio returning ROI, win rate, CLV, drawdown, active bets
- [x] **API-05**: FastAPI exposes POST /api/v1/bankroll/simulate returning Monte Carlo result for given parameters
- [x] **API-06**: Supabase RLS is enabled for all user-scoped tables before any API route is wired to user data

### Web Dashboard

- [x] **WEB-01**: Dashboard page shows portfolio overview: ROI curve, win rate, CLV trend, bankroll curve, active bets
- [x] **WEB-02**: Value plays page shows live alpha-ranked betting opportunities with regime indicator and alpha badge (PREMIUM/HIGH/MEDIUM/SPECULATIVE)
- [x] **WEB-03**: Game detail page shows full analysis: model prediction, EV breakdown, regime state, key number proximity, sharp vs public percentages
- [x] **WEB-04**: Bankroll page shows Monte Carlo fan chart (P5/P50/P95 paths), Kelly calculator, and exposure limits
- [x] **WEB-05**: Copilot page provides streaming chat interface with BettingCopilot
- [x] **WEB-06**: Prediction markets page shows Kalshi/Polymarket edge dashboard with regime classification

### Mobile App

- [x] **MOB-01**: Feed screen shows live alpha-ranked value plays with swipe-right to log bet
- [x] **MOB-02**: Copilot screen provides BettingCopilot chat interface
- [x] **MOB-03**: Portfolio screen shows bet tracker and performance stats
- [x] **MOB-04**: Push notifications deliver high-alpha alerts (PREMIUM/HIGH badge) before Discord alert fires
- [x] **MOB-05**: App uses biometric auth (Face ID / fingerprint) for account access

### Model Pipeline

- [x] **MODEL-01**: Prediction ensemble uses 5 models (team form, matchup history, injury impact, market sentiment, weather/travel) with calibrated weights
- [x] **MODEL-02**: Feature builder assembles game feature vector from last 10 results, opponent strength, rest days, injury report, home/away splits, line movement velocity, public betting %, key number proximity

---

## v2 Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### Advanced Analytics

- **ADV-01**: Model disagreement alerts (when 2+ ensemble models strongly disagree)
- **ADV-02**: Performance attribution (which model/feature drives wins per sport/market)
- **ADV-03**: A/B test alpha thresholds (separate alert groups by alpha band)
- **ADV-04**: Walk-forward validation dashboard (web page showing historical model performance windows)

### Platform

- **PLAT-01**: Line movement chart (FinnAI-style time-series line history chart per game)
- **PLAT-02**: iOS home screen widget (bankroll + pending bets)
- **PLAT-03**: Multi-sport portfolio correlation matrix

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Automated bet placement | Regulatory risk; platform provides intelligence, user places bets |
| Social / community features | Wrong user profile; serious bettors don't want feeds |
| AI-generated narrative content | Commoditized; adds no edge |
| Direct sportsbook account linking | API access restrictions; regulatory complexity |
| Real-time chat between users | Not core to value proposition |
| OAuth login (Google/GitHub) | Email/password + Whop sufficient for v2 |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| QUANT-01 | Phase 1 | Pending |
| QUANT-02 | Phase 1 | Pending |
| QUANT-03 | Phase 1 | Pending |
| QUANT-04 | Phase 1 | Pending |
| QUANT-05 | Phase 1 | Pending |
| QUANT-06 | Phase 1 | Pending |
| QUANT-07 | Phase 5 | Complete |
| AGENT-01 | Phase 2 | Complete |
| AGENT-02 | Phase 2 | Complete |
| AGENT-03 | Phase 2 | Complete |
| AGENT-04 | Phase 2 | Complete |
| AGENT-05 | Phase 2 | Complete |
| PM-01 | Phase 3 | Complete |
| PM-02 | Phase 3 | Complete |
| PM-03 | Phase 3 | Complete |
| PM-04 | Phase 3 | Complete |
| API-01 | Phase 4 | Complete |
| API-02 | Phase 4 | Complete |
| API-03 | Phase 4 | Complete |
| API-04 | Phase 4 | Complete |
| API-05 | Phase 4 | Complete |
| API-06 | Phase 4 | Complete |
| WEB-01 | Phase 4 | Complete |
| WEB-02 | Phase 4 | Complete |
| WEB-03 | Phase 4 | Complete |
| WEB-04 | Phase 4 | Complete |
| WEB-05 | Phase 4 | Complete |
| WEB-06 | Phase 4 | Complete |
| MOB-01 | Phase 4 | Complete |
| MOB-02 | Phase 4 | Complete |
| MOB-03 | Phase 4 | Complete |
| MOB-04 | Phase 4 | Complete |
| MOB-05 | Phase 4 | Complete |
| MODEL-01 | Phase 5 | Complete |
| MODEL-02 | Phase 5 | Complete |

**Coverage:**
- v1 requirements: 35 total
- Mapped to phases: 35
- Unmapped: 0

---
*Requirements defined: 2026-03-13*
*Last updated: 2026-03-13 after roadmap confirmation — all 35 requirements mapped to ROADMAP.md phases*
