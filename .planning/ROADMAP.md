# Roadmap: SharpEdge v2

**Project:** SharpEdge v2 — Institutional-Grade Sports Betting Intelligence Platform
**Milestone:** v2 upgrade
**Created:** 2026-03-13
**Granularity:** Coarse (5 phases)
**Coverage:** 35/35 v1 requirements mapped

---

## Phases

- [ ] **Phase 1: Quant Engine** - Pure-Python quantitative primitives with no framework dependency
- [ ] **Phase 2: Agent Architecture** - LangGraph StateGraph + BettingCopilot wired onto Phase 1 modules
- [ ] **Phase 3: Prediction Market Intelligence** - PM edge scanning and cross-market correlation on stable Phase 2 graph
- [ ] **Phase 4: API Layer + Front-Ends** - FastAPI REST/SSE + Next.js web dashboard + Expo mobile app
- [ ] **Phase 5: Model Pipeline Upgrade** - 5-model ensemble, continuous Platt calibration, walk-forward validation

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Quant Engine | 1/3 | In progress | - |
| 2. Agent Architecture | 1/4 | In Progress|  |
| 3. Prediction Market Intelligence | 0/? | Not started | - |
| 4. API Layer + Front-Ends | 0/? | Not started | - |
| 5. Model Pipeline Upgrade | 0/? | Not started | - |

---

## Phase Details

### Phase 1: Quant Engine
**Goal**: The computational primitives that all downstream work depends on are correct, thread-safe, and unit-tested in isolation — with no LangGraph or I/O dependency
**Depends on**: Nothing (first phase)
**Requirements**: QUANT-01, QUANT-02, QUANT-03, QUANT-04, QUANT-05, QUANT-06
**Success Criteria** (what must be TRUE):
  1. User sees a composite alpha score (EV × regime_scale × survival_prob × confidence_mult) attached to every value play alert
  2. User can run a Monte Carlo bankroll simulation and receive ruin probability, P5/P50/P95 path outcomes, and max drawdown — with no shared RNG state between concurrent requests
  3. User sees the current betting market classified into a regime (minimum 3 states, e.g. SHARP_CONSENSUS / PUBLIC_HEAVY / STEAM_MOVE) with a confidence score displayed alongside each alert
  4. User sees key number proximity flagged for any spread or total at or near a historical cluster, with historical cover rate shown
  5. User sees a CLV figure on each closed bet that updates after the closing line is recorded, with a running CLV average in their portfolio stats
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Debt fix + test infrastructure (datetime, visualizations split, backtesting stubs, test stubs)
- [ ] 01-02-PLAN.md — Core quant modules (monte_carlo, alpha, regime, key_numbers extension)
- [ ] 01-03-PLAN.md — Persistence + integration (walk_forward, clv, alpha wired into value_scanner)

### Phase 2: Agent Architecture
**Goal**: All betting analysis requests flow through a 9-node LangGraph StateGraph with safe parallel state, loop guards, and a conversational BettingCopilot that answers questions with full portfolio awareness
**Depends on**: Phase 1
**Requirements**: AGENT-01, AGENT-02, AGENT-03, AGENT-04, AGENT-05
**Success Criteria** (what must be TRUE):
  1. A bet analysis request enters at route_intent and exits at generate_report having passed through all 9 nodes — with no silent state overwrite when parallel nodes write the same key
  2. Every candidate alert passes through the LLM setup evaluator and receives a PASS, WARN, or REJECT decision with reasoning before any Discord alert is dispatched
  3. User can ask BettingCopilot "what's my riskiest active bet?" and receive a response that references their actual active bets, current bankroll exposure, and regime state
  4. BettingCopilot supports all 10 required tools without hitting context window limits in sessions of 10+ turns
  5. Value play alerts arrive in Discord ranked by alpha score (highest alpha posts first), not by discovery order
**Plans**: 4 plans

Plans:
- [ ] 02-01-PLAN.md — Package scaffold + RED test stubs + dependency registration (Wave 0)
- [ ] 02-02-PLAN.md — BettingAnalysisState + 9-node graph wiring + all node implementations (Wave 1, AGENT-01/02)
- [ ] 02-03-PLAN.md — BettingCopilot ReAct graph + 10 tools + trim_conversation session (Wave 2, AGENT-03/04)
- [ ] 02-04-PLAN.md — Alpha ranking intercept in value_scanner_job + full suite regression (Wave 3, AGENT-05)

### Phase 3: Prediction Market Intelligence
**Goal**: The platform surfaces edges in Kalshi and Polymarket markets, classifies PM regime, and prevents double-exposure across correlated positions — all sitting on top of the stable Phase 2 graph
**Depends on**: Phase 2
**Requirements**: PM-01, PM-02, PM-03, PM-04
**Success Criteria** (what must be TRUE):
  1. User sees Kalshi markets where model probability exceeds market probability by more than 3%, each with an alpha score, and only for markets with sufficient liquidity (bid-ask spread within threshold)
  2. User sees equivalent Polymarket edge opportunities surfaced with the same scoring and liquidity filter
  3. User sees the current prediction market regime (e.g. Discovery, Consensus, News Catalyst) alongside each PM edge, with the edge threshold adjusted based on that regime classification
  4. User receives a portfolio correlation warning when any combination of active sportsbook bets and prediction market positions has a correlation coefficient above 0.6
**Plans**: TBD

### Phase 4: API Layer + Front-Ends
**Goal**: Users can access all Phase 1–3 intelligence through a web dashboard, a mobile app, and a REST/SSE API — with Supabase RLS protecting all user-scoped data before any route goes live
**Depends on**: Phase 1, Phase 2, Phase 3
**Requirements**: API-01, API-02, API-03, API-04, API-05, API-06, WEB-01, WEB-02, WEB-03, WEB-04, WEB-05, WEB-06, MOB-01, MOB-02, MOB-03, MOB-04, MOB-05
**Success Criteria** (what must be TRUE):
  1. Supabase RLS is enabled on all user-scoped tables and a user accessing the API can only retrieve their own portfolio data — verified before any user-scoped endpoint is deployed
  2. Web dashboard loads a portfolio overview page with ROI curve, win rate, CLV trend, bankroll curve, and active bets; a value plays page showing live alpha-ranked opportunities with regime indicator and alpha badges; a game detail page with full analysis; a bankroll page with Monte Carlo fan chart; a BettingCopilot streaming chat page; and a prediction markets page
  3. Mobile app shows a live alpha-ranked feed where the user can swipe right to log a bet, a BettingCopilot chat screen, a portfolio performance screen, and delivers push notifications for PREMIUM/HIGH alpha alerts before the Discord alert fires
  4. Mobile app requires Face ID or fingerprint authentication before granting account access
  5. FastAPI exposes all six required endpoints (value-plays, game analysis, copilot SSE chat, portfolio, bankroll simulate, with RLS-gated user data) and handles concurrent BettingCopilot SSE streams without blocking other routes
**Plans**: TBD

### Phase 5: Model Pipeline Upgrade
**Goal**: The prediction system continuously improves through rolling Platt scaling calibration, a 5-model ensemble, and a fully implemented walk-forward backtester that produces honest out-of-sample quality badges
**Depends on**: Phase 1 (Quant Engine), Phase 4 (deployed baseline for calibration feedback loop)
**Requirements**: QUANT-07, MODEL-01, MODEL-02
**Success Criteria** (what must be TRUE):
  1. After each game resolves, the system recalibrates ML model confidence using Platt scaling fit on lagged (not live) data only — and the updated confidence multiplier is reflected in alpha scores within the next analysis cycle
  2. The prediction ensemble draws on all 5 model inputs (team form, matchup history, injury impact, market sentiment, weather/travel) with calibrated weights, and the feature vector includes all specified inputs (last 10 results, opponent strength, rest days, injury report, home/away splits, line movement velocity, public betting %, key number proximity)
  3. Walk-forward backtester produces a report with out-of-sample win rate, out-of-sample ROI, per-window breakdown, and a quality badge (low / medium / high / excellent) — using non-overlapping windows with no lookahead bias
**Plans**: TBD

---

## Coverage

| Requirement | Phase |
|-------------|-------|
| QUANT-01 | Phase 1 |
| QUANT-02 | Phase 1 |
| QUANT-03 | Phase 1 |
| QUANT-04 | Phase 1 |
| QUANT-05 | Phase 1 |
| QUANT-06 | Phase 1 |
| AGENT-01 | Phase 2 |
| AGENT-02 | Phase 2 |
| AGENT-03 | Phase 2 |
| AGENT-04 | Phase 2 |
| AGENT-05 | Phase 2 |
| PM-01 | Phase 3 |
| PM-02 | Phase 3 |
| PM-03 | Phase 3 |
| PM-04 | Phase 3 |
| API-01 | Phase 4 |
| API-02 | Phase 4 |
| API-03 | Phase 4 |
| API-04 | Phase 4 |
| API-05 | Phase 4 |
| API-06 | Phase 4 |
| WEB-01 | Phase 4 |
| WEB-02 | Phase 4 |
| WEB-03 | Phase 4 |
| WEB-04 | Phase 4 |
| WEB-05 | Phase 4 |
| WEB-06 | Phase 4 |
| MOB-01 | Phase 4 |
| MOB-02 | Phase 4 |
| MOB-03 | Phase 4 |
| MOB-04 | Phase 4 |
| MOB-05 | Phase 4 |
| QUANT-07 | Phase 5 |
| MODEL-01 | Phase 5 |
| MODEL-02 | Phase 5 |

**Total v1:** 35 | **Mapped:** 35 | **Unmapped:** 0

---
*Roadmap created: 2026-03-13*
*Updated: 2026-03-14 — Plan 01-01 complete (debt clearance + test stubs)*
*Updated: 2026-03-13 — Phase 2 plans created (02-01 through 02-04, 4 waves)*
