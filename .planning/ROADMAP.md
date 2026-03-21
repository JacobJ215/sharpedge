# Roadmap: SharpEdge v3.0

**Project:** SharpEdge v3.0 — Launch & Distribution
**Milestone:** v3.0 — Launch & Distribution
**Created:** 2026-03-13
**Updated:** 2026-03-21 — v3.0 milestone added (Phases 16–21, 26 requirements mapped)
**Granularity:** Coarse (5 phases)
**Coverage:** 35/35 v1 requirements mapped + 10 Phase 6 requirements + v3.0 26 requirements

---

## Phases

- [x] **Phase 1: Quant Engine** - Pure-Python quantitative primitives with no framework dependency (completed 2026-03-16)
- [x] **Phase 2: Agent Architecture** - LangGraph StateGraph + BettingCopilot wired onto Phase 1 modules
- [x] **Phase 3: Prediction Market Intelligence** - PM edge scanning and cross-market correlation on stable Phase 2 graph (completed 2026-03-14)
- [x] **Phase 4: API Layer + Front-Ends** - FastAPI REST/SSE + Next.js web dashboard + Flutter mobile app (completed 2026-03-14)
- [x] **Phase 5: Model Pipeline Upgrade** - 5-model ensemble, continuous Platt calibration, walk-forward validation (completed 2026-03-14)

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Quant Engine | 3/3 | Complete    | 2026-03-16 |
| 2. Agent Architecture | 4/4 | Complete | 2026-03-13 |
| 3. Prediction Market Intelligence | 3/3 | Complete   | 2026-03-14 |
| 4. API Layer + Front-Ends | 10/10 | Complete   | 2026-03-14 |
| 5. Model Pipeline Upgrade | 5/5 | Complete   | 2026-03-14 |
| 6. Multi-Venue Quant Infrastructure | 8/8 | Complete   | 2026-03-14 |
| 7. Model Pipeline Completion | 6/6 | Complete | 2026-03-15 |
| 8. Frontend Polish & Full Backend Wiring | 7/7 | Complete | 2026-03-15 |
| 9. Prediction Market Resolution Models | 5/5 | Complete | 2026-03-15 |
| 10. Training Pipeline Validation | 3/3 | Complete   | 2026-03-16 |
| 11. Shadow Execution Engine | 2/2 | Complete   | 2026-03-18 |
| 12. Live Kalshi Execution | 2/2 | Complete    | 2026-03-20 |
| 13. Ablation Validation & Capital Gate | 3/3 | Complete    | 2026-03-21 |
| 14. Dashboard Execution Pages | 0/3 | Not started | - |
| 15. Arb Scanner Hardening | 3/3 | Complete    | 2026-03-18 |
| 16. Auth Bridge | 1/3 | In Progress|  |
| 17. Web Deployment | 0/3 | Not started | - |
| 18. Discord Community | 0/3 | Not started | - |
| 19. Marketing & Onboarding | 0/2 | Not started | - |
| 20. Mobile Submission | 0/3 | Not started | - |
| 21. Monitoring | 0/2 | Not started | - |

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
- [x] 01-02-PLAN.md — Core quant modules (monte_carlo, alpha, regime, key_numbers extension)
- [x] 01-03-PLAN.md — Persistence + integration (walk_forward, clv, alpha wired into value_scanner)

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
- [x] 02-02-PLAN.md — BettingAnalysisState + 9-node graph wiring + all node implementations (Wave 1, AGENT-01/02)
- [x] 02-03-PLAN.md — BettingCopilot ReAct graph + 10 tools + trim_conversation session (Wave 2, AGENT-03/04)
- [x] 02-04-PLAN.md — Alpha ranking intercept in value_scanner_job + full suite regression (Wave 3, AGENT-05)

### Phase 3: Prediction Market Intelligence
**Goal**: The platform surfaces edges in Kalshi and Polymarket markets, classifies PM regime, and prevents double-exposure across correlated positions — all sitting on top of the stable Phase 2 graph
**Depends on**: Phase 2
**Requirements**: PM-01, PM-02, PM-03, PM-04
**Success Criteria** (what must be TRUE):
  1. User sees Kalshi markets where model probability exceeds market probability by more than 3%, each with an alpha score, and only for markets with sufficient liquidity (bid-ask spread within threshold)
  2. User sees equivalent Polymarket edge opportunities surfaced with the same scoring and liquidity filter
  3. User sees the current prediction market regime (e.g. Discovery, Consensus, News Catalyst) alongside each PM edge, with the edge threshold adjusted based on that regime classification
  4. User receives a portfolio correlation warning when any combination of active sportsbook bets and prediction market positions has a correlation coefficient above 0.6
**Plans**: 3 plans

Plans:
- [ ] 03-01-PLAN.md — prediction_markets.py split + RED test stubs for PM-01/02/03/04 (Wave 1)
- [ ] 03-02-PLAN.md — pm_regime.py + pm_edge_scanner.py core implementations (Wave 2)
- [ ] 03-03-PLAN.md — pm_correlation.py + value_scanner_job wiring + copilot tool (Wave 3)

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
**Plans**: 8 plans

Plans:
- [ ] 04-00-PLAN.md — RED test stubs (API-01–06) + Next.js 14 scaffold + RLS SQL migration (Wave 0)
- [x] 04-01-PLAN.md — FastAPI v1 auth dependency + GET /api/v1/value-plays + GET /api/v1/games/{id}/analysis (Wave 1, API-01/02/06)
- [ ] 04-02-PLAN.md — POST /api/v1/copilot/chat SSE + GET /api/v1/users/{id}/portfolio + POST /api/v1/bankroll/simulate (Wave 1, API-03/04/05)
- [ ] 04-03-PLAN.md — Next.js portfolio overview page + value plays page (Wave 2, WEB-01/02)
- [ ] 04-04-PLAN.md — Next.js game detail + bankroll + copilot + prediction markets pages (Wave 2, WEB-03/04/05/06)
- [ ] 04-05-PLAN.md — Flutter auth/biometrics + pubspec deps + ApiService v1 layer (Wave 2, MOB-05)
- [ ] 04-06-PLAN.md — Flutter feed screen (swipe-to-log) + copilot chat + portfolio screen (Wave 3, MOB-01/02/03)
- [ ] 04-07-PLAN.md — FCM push notifications + value_scanner_job FCM-before-Discord wiring (Wave 3, MOB-04)

### Phase 5: Model Pipeline Upgrade
**Goal**: The prediction system continuously improves through rolling Platt scaling calibration, a 5-model ensemble, and a fully implemented walk-forward backtester that produces honest out-of-sample quality badges
**Depends on**: Phase 1 (Quant Engine), Phase 4 (deployed baseline for calibration feedback loop)
**Requirements**: QUANT-07, MODEL-01, MODEL-02
**Success Criteria** (what must be TRUE):
  1. After each game resolves, the system recalibrates ML model confidence using Platt scaling fit on lagged (not live) data only — and the updated confidence multiplier is reflected in alpha scores within the next analysis cycle
  2. The prediction ensemble draws on all 5 model inputs (team form, matchup history, injury impact, market sentiment, weather/travel) with calibrated weights, and the feature vector includes all specified inputs (last 10 results, opponent strength, rest days, injury report, home/away splits, line movement velocity, public betting %, key number proximity)
  3. Walk-forward backtester produces a report with out-of-sample win rate, out-of-sample ROI, per-window breakdown, and a quality badge (low / medium / high / excellent) — using non-overlapping windows with no lookahead bias
**Plans**: 5 plans

Plans:
- [ ] 05-01-PLAN.md — RED test stubs for QUANT-07, MODEL-01, MODEL-02 (Wave 0, TDD)
- [ ] 05-02-PLAN.md — FeatureAssembler + GameFeatures MODEL-02 extension (Wave 1, MODEL-02)
- [ ] 05-03-PLAN.md — EnsembleManager 5-model stacking + MLModelManager.predict_ensemble (Wave 2, MODEL-01)
- [ ] 05-04-PLAN.md — CalibrationStore + result_watcher trigger (Wave 3, QUANT-07)
- [ ] 05-05-PLAN.md — Integration wiring: compose_alpha + run_models + walk-forward inference + weekly retrain scheduler (Wave 4, QUANT-07 + MODEL-01)

### Phase 6: Multi-Venue Quant Infrastructure

**Goal:** The platform has a canonical multi-venue adapter layer (Kalshi CLOB, Polymarket CLOB, multi-book sportsbook via The Odds API), a market catalog with lifecycle state tracking, cross-venue quote normalization with historical replay, a microstructure fill-hazard model, cross-venue dislocation detection, a risk/exposure framework with fractional Kelly, and a settlement ledger with deterministic replay — all as a new `packages/venue_adapters/` package in the existing Python uv workspace.
**Requirements**: VENUE-01, VENUE-02, VENUE-03, VENUE-04, VENUE-05, PRICE-01, MICRO-01, DISLO-01, RISK-01, SETTLE-01
**Depends on:** Phase 5
**Plans:** 3/3 plans complete

Plans:
- [ ] 06-01-PLAN.md — Package scaffold + RED TDD stubs for all 10 requirements (Wave 0)
- [ ] 06-02-PLAN.md — VenueAdapter Protocol + MarketCatalog state machine + canonical typed contracts (Wave 1, VENUE-01/02)
- [ ] 06-03-PLAN.md — KalshiAdapter + PolymarketAdapter wrapping existing transport clients (Wave 2, VENUE-03/04)
- [ ] 06-04-PLAN.md — OddsApiAdapter multi-book line shopping + devig_shin_n_outcome N-outcome extension (Wave 3, VENUE-05/PRICE-01)
- [ ] 06-05-PLAN.md — FillHazardModel microstructure + cross-venue dislocation scoring (Wave 4, MICRO-01/DISLO-01)
- [ ] 06-06-PLAN.md — ExposureBook fractional Kelly + settlement ledger + Supabase migration (Wave 5, RISK-01/SETTLE-01)
- [ ] 06-07-PLAN.md — BettingCopilot venue tools (get_venue_dislocation + get_exposure_status) (Wave 6, DISLO-01/RISK-01)
- [ ] 06-08-PLAN.md — SnapshotStore market state persistence + market_snapshots DDL (Wave 6, VENUE-01/02)

### Phase 7: Model Pipeline Completion

**Goal:** All 5 ensemble models trained, walk-forward validated (quality badge `high`/`excellent`), Platt-calibrated per sport and venue family, and gated through promotion criteria. `confidence_mult` in composite alpha scores reflects real out-of-sample quality. Pipeline integration verified end-to-end.
**Requirements**: PIPE-01, WALK-01, CAL-01, GATE-01, INT-01
**Depends on:** Phase 6
**Plans:** 4/6 plans executed

Plans:
- [x] 07-01-PLAN.md — RED TDD stubs (test_pipeline_integration, test_promotion_gate, test_alpha_pipeline) + retrain_scheduler import fix (Wave 0, PIPE-01/GATE-01/INT-01)
- [x] 07-02-PLAN.md — Extend download + process scripts for NCAAB, MLB, NHL with graceful skip + zero-fill (Wave 1, PIPE-01)
- [ ] 07-03-PLAN.md — Extend train_models.py for all 5 sports + zero-fill in _train_ensemble_for_sport (Wave 2, PIPE-01)
- [ ] 07-04-PLAN.md — Create scripts/run_walk_forward.py — WalkForwardBacktester orchestrator + max_drawdown + JSON report (Wave 3, WALK-01)
- [ ] 07-05-PLAN.md — Create scripts/run_calibration.py — CalibrationStore.update on OOS data + venue calibration stubs + JSON report (Wave 4, CAL-01)
- [ ] 07-06-PLAN.md — Create scripts/generate_promotion_gate.py + turn all RED stubs GREEN (Wave 5, GATE-01/INT-01/PIPE-01)

### Phase 8: Frontend Polish & Full Backend Wiring

**Goal:** Zero placeholder endpoints, zero mock data — every screen in web and mobile reads from real production APIs with real auth. All Phase 6 venue dislocation and exposure widgets are live in the UI. BettingCopilot is fully exercised from both surfaces.
**Requirements**: WIRE-01, WIRE-02, WIRE-03, WIRE-04, WIRE-05, WIRE-06
**Depends on:** Phase 7
**Plans:** 7/7 plans complete

Plans:
- [x] 08-01-PLAN.md — Phase 8 setup (completed 2026-03-15)
- [x] 08-02-PLAN.md — WIRE-01 web auth + WIRE-02 FastAPI endpoint scaffolding (completed 2026-03-15)

### Phase 9: Prediction Market Resolution Models & Expansion Beyond Sports

**Goal:** Kalshi and Polymarket binary resolution models trained on historical resolved-market data, replacing the fee-adjusted probability fallback in the PM edge scanner with ML-predicted resolution probabilities. Five expansion categories (political, economic, entertainment, crypto, weather) each have their own feature set and calibration. All gated behind ENABLE_PM_RESOLUTION_MODEL env var.
**Requirements**: PM-DATA-01, PM-DATA-02, PM-RES-01, PM-RES-02, PM-INT-01
**Depends on:** Phase 8
**Plans:** 5/5 plans complete

Plans:
- [x] 09-01-PLAN.md — RED TDD stubs: PMFeatureAssembler, PMResolutionPredictor, 3 API clients (CoinGecko/FEC/BLS), download/process/train scripts (Wave 1)
- [ ] 09-02-PLAN.md — download_pm_historical.py + CoinGeckoClient + FECClient + BLSClient implementations (Wave 2, PM-DATA-01)
- [ ] 09-03-PLAN.md — PMFeatureAssembler: 6-universal + category add-on feature vector + category detection (Wave 2, PM-RES-01)
- [ ] 09-04-PLAN.md — process_pm_historical.py + train_pm_models.py: per-category RF + walk-forward + low-data skip + JSON report (Wave 3, PM-DATA-02/PM-RES-01)
- [ ] 09-05-PLAN.md — PMResolutionPredictor: ENABLE_PM_RESOLUTION_MODEL flag + build_model_probs() integration with scan_pm_edges (Wave 4, PM-RES-02/PM-INT-01)

---

## v2.0 — Live Execution (Phases 10–14)

**Milestone Goal:** Promote SharpEdge from intelligence platform to active trading system — shadow-mode execution pipeline, live Kalshi CLOB order submission, trained PM resolution models, ablation validation, and a live-capital gate requiring all four checks to pass before real orders flow.

### Phase 10: Training Pipeline Validation
**Goal**: Per-category `.joblib` RandomForest artifacts exist, are calibrated, and the training report confirms quality — so Phase 11 has real models to gate against.
**Depends on**: Phase 9
**Requirements**: TRAIN-01, TRAIN-02, TRAIN-03, TRAIN-04
**Success Criteria** (what must be TRUE):
  1. Operator can run `download_pm_historical.py` against live Kalshi and Polymarket APIs and the resolved-market backfill completes without error
  2. Operator can run `process_pm_historical.py` and receive one feature DataFrame per category with expected column schema
  3. Operator can run `train_pm_models.py` and receive one `.joblib` file per category in the configured artifacts directory
  4. Training report JSON exists and contains a quality badge, calibration score, and market count per category
**Plans**: 3 plans

Plans:
- [x] 10-01-PLAN.md — Supabase migration DDL + Wave 0 test scaffold (Wave 1, TRAIN-01/02/03/04)
- [x] 10-02-PLAN.md — download + process scripts migrated to Supabase (Wave 2, TRAIN-01/02)
- [x] 10-03-PLAN.md — calibration_score in training report + human verify checkpoint (Wave 2, TRAIN-03/04)

### Phase 11: Shadow Execution Engine
**Goal**: Order intents flow through an execution engine that enforces position limits and writes every signal to a ShadowLedger — with no capital at risk.
**Depends on**: Phase 10
**Requirements**: EXEC-01, EXEC-02, EXEC-04
**Success Criteria** (what must be TRUE):
  1. Operator can start shadow mode and verify that signals produce ledger entries (market_id, predicted edge, Kelly-sized amount, timestamp) with no Kalshi API calls made
  2. An order intent for a market that would breach the per-market max-exposure limit is rejected before the ledger entry is written
  3. An order intent that would push cumulative day exposure past the per-day limit is rejected before the ledger entry is written
**Plans**: 2 plans

Plans:
- [ ] 11-01-PLAN.md — Wave 0 test stubs + execution_engine.py stub module (RED tests, EXEC-01/02/04)
- [ ] 11-02-PLAN.md — Full implementation: ShadowLedger + exposure guards + ShadowExecutionEngine (EXEC-01/02/04)

### Phase 12: Live Kalshi Execution
**Goal**: The same execution engine submits real CLOB orders when `ENABLE_KALSHI_EXECUTION=true`, and all fills and cancellations are recorded in SettlementLedger.
**Depends on**: Phase 11
**Requirements**: EXEC-03, EXEC-05
**Success Criteria** (what must be TRUE):
  1. With `ENABLE_KALSHI_EXECUTION=true`, the engine submits a limit order to Kalshi CLOB and the order ID is written to SettlementLedger
  2. After submission, the engine polls Kalshi order status and records fill quantity, fill price, and timestamp on a fill event
  3. A cancelled order is detected during polling and the cancellation is recorded in SettlementLedger with a reason field
**Plans**: 2 plans

Plans:
- [ ] 12-01-PLAN.md — RED test stubs (test_live_execution_engine.py) + get_order() on KalshiClient (Wave 1, EXEC-03/EXEC-05)
- [ ] 12-02-PLAN.md — LiveOrderPoller + live branch in ShadowExecutionEngine until all tests GREEN (Wave 2, EXEC-03/EXEC-05)

### Phase 13: Ablation Validation & Capital Gate
**Goal**: An ablation script confirms model edge over fallback, and the capital gate enforces all four conditions before live execution is honoured.
**Depends on**: Phase 12
**Requirements**: ABLATE-01, ABLATE-02, GATE-01, GATE-02, GATE-03, GATE-04
**Success Criteria** (what must be TRUE):
  1. Operator can run the ablation backtest and receive an edge-delta report (model vs fee-adjusted fallback) per category and overall, with a configurable pass/fail threshold applied
  2. Setting `ENABLE_KALSHI_EXECUTION=true` is rejected at startup with a clear error message if `.joblib` artifacts are missing for any of the 5 categories
  3. Setting `ENABLE_KALSHI_EXECUTION=true` is rejected if the paper-trading period has not reached the configured minimum days with an acceptable edge-to-fill ratio
  4. Operator can complete manual review via CLI confirmation prompt and the timestamped approval is written to a log entry before live mode activates
  5. Live execution auto-disables and writes a circuit-breaker log entry when daily realized loss exceeds the configured drawdown threshold
**Plans**: 3 plans

Plans:
- [x] 13-01-PLAN.md — RED test stubs + capital_gate.py and ablation.py stub modules (Wave 1)
- [x] 13-02-PLAN.md — CapitalGate implementation + from_env() wiring + approve_live.py (Wave 2, GATE-01..04)
- [x] 13-03-PLAN.md — Ablation backtest implementation + run_ablation.py CLI script (Wave 2, ABLATE-01/02)

### Phase 14: Dashboard Execution Pages
**Goal**: The web dashboard surfaces execution status and paper-trading history so the operator can monitor the system without inspecting logs.
**Depends on**: Phase 13
**Requirements**: DASH-01, DASH-02
**Success Criteria** (what must be TRUE):
  1. Web dashboard execution status page shows current mode (paper vs live), ENABLE_KALSHI_EXECUTION flag state, and timestamp of last signal processed
  2. Web dashboard paper-trading summary page shows total signal count, a scrollable would-have-been trade log, and an edge distribution chart across all shadow signals
**Plans**: 3 plans

Plans:
- [x] 13-01-PLAN.md — RED test stubs + capital_gate.py and ablation.py stub modules (Wave 1)
- [ ] 13-02-PLAN.md — CapitalGate implementation + from_env() wiring + approve_live.py (Wave 2, GATE-01..04)
- [x] 13-03-PLAN.md — Ablation backtest implementation + run_ablation.py CLI script (Wave 2, ABLATE-01/02)

### Phase 15: Arb Scanner Hardening
**Goal**: The real-time arb scanner operates without manual pair registration, rejects stale price data, places orders on both Kalshi and Polymarket, and correctly prices NO-side legs for markets where the NO token trades independently.
**Depends on**: Phase 10 (streaming infra from arb scanner work)
**Requirements**: ARB-01, ARB-02, ARB-03, ARB-04
**Success Criteria** (what must be TRUE):
  1. Operator can start the arb scanner without pre-registering any pairs — it discovers and matches Kalshi/Polymarket markets automatically using the existing MarketCorrelationNetwork, subscribing streams for all matched pairs
  2. When a YES or NO price tick arrives and the other side's last update is older than a configurable staleness threshold (default 5s), the pair is skipped and a staleness warning is logged — no false arb fires on stale data
  3. When an arb opportunity exceeds the execution threshold, the scanner places limit orders on both Kalshi (via `KalshiClient.create_order()`) and Polymarket (via CLOB API) simultaneously, and records both order IDs
  4. When `polymarket_no_token` is not provided, the scanner fetches the independent NO token's actual order book rather than deriving price as `1 − yes_ask`, and uses the real best ask for fee-adjusted arb calculation
**Plans**: 3 plans

Plans:
- [ ] 15-01-PLAN.md — RED test suite: 8 failing stubs for ARB-01 through ARB-04 (Wave 1, all ARB reqs)
- [ ] 15-02-PLAN.md — ARB-03 staleness guard + ARB-04 real NO token orderbook (Wave 2, ARB-03/ARB-04)
- [ ] 15-03-PLAN.md — ARB-01 discover_and_wire() + ARB-02 shadow dual-platform execution (Wave 3, ARB-01/ARB-02)

---

## v3.0 — Launch & Distribution (Phases 16–21)

**Milestone Goal:** Deploy SharpEdge to production — web app live on Vercel Pro, backend services on Railway, Discord community with 3-tier channel structure and monetized role gating, iOS + Android apps approved on App Store and Play Store, marketing landing page converting visitors to signups, and full error tracking and monitoring active across all platforms.

### Phase 16: Auth Bridge
**Goal**: Users on web and mobile share a single unified account where Whop subscription tier propagates into every JWT within seconds — eliminating the two-identity gap between `discord_id` and `supabase_auth_id`.
**Depends on**: Phase 15
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05
**Success Criteria** (what must be TRUE):
  1. A new user can sign up on the web app with an email address and a `public.users` row is created automatically, linked to their Supabase Auth UUID
  2. A user who subscribes via Whop sees their tier reflected in the web app and mobile app within 30 seconds — without logging out and back in
  3. A free-tier user attempting to access a paid feature sees a clear upgrade prompt — not a blank page or an error
  4. A paid-tier user who logs in on mobile sees the same feature access as on web, derived from the same JWT tier claim
  5. A user can view their current tier (Free / Mid / Premium) and a link to their Whop subscription management page from within the app
**Plans**: 3 plans

Plans:
- [x] 16-01-PLAN.md — Migration 008 + push_tier_to_supabase_auth in whop.py + RevenueCat webhook handler (Wave 1, AUTH-01/02/04)
- [ ] 16-02-PLAN.md — Custom Access Token Hook dashboard registration + @supabase/ssr + middleware.ts + signup + upgrade pages (Wave 2, AUTH-01/02/03/04)
- [ ] 16-03-PLAN.md — Flutter currentTier getter + hasProAccess gates + UpgradePromptWidget + web /account page (Wave 2, AUTH-03/05)

### Phase 17: Web Deployment
**Goal**: The SharpEdge web app and all backend services are running in production — accessible at a live domain, protected by JWT-based feature gating, deploying automatically on every merge to main.
**Depends on**: Phase 16
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04
**Success Criteria** (what must be TRUE):
  1. A visitor can reach the SharpEdge web app at a live production domain over HTTPS
  2. A Whop subscription event or Stripe payment triggers the webhook server and the user's tier is updated in Supabase — confirmed by inspecting the Supabase `public.users` row
  3. The Discord bot responds to slash commands in the production server — it is not running on a developer's laptop
  4. A merge to the `main` branch on GitHub triggers an automatic deploy of the web app to Vercel — the change is live within 5 minutes without any manual action
**Plans**: TBD

Plans:
- [ ] 17-01-PLAN.md — Vercel Pro project setup + environment variables + production domain + Next.js deployment verification (Wave 1, DEPLOY-01/04)
- [ ] 17-02-PLAN.md — Railway service setup: FastAPI webhook server + Discord bot as two separate always-on services + Railway auto-deploy from GitHub (Wave 2, DEPLOY-02/03)
- [ ] 17-03-PLAN.md — GitHub Actions CI gates: test jobs for web (TypeScript) and Python services blocking merge to main (Wave 3, DEPLOY-04)

### Phase 18: Discord Community
**Goal**: The SharpEdge Discord server is a credible, active community before the first outsider joins — with tier-gated channels, automated daily content, a tested Whop→role sync, and a 7-day content seed that makes the server look alive.
**Depends on**: Phase 16
**Requirements**: DISCORD-01, DISCORD-02, DISCORD-03, DISCORD-04, DISCORD-05
**Success Criteria** (what must be TRUE):
  1. A free user joining the server sees only the free-tier channels — they cannot read or post in Mid or Premium channels
  2. A user who subscribes via Whop is assigned the correct Discord role automatically — confirmed by testing with a real $1 test subscription before any public users exist
  3. A free-tier user running a premium bot command sees a restricted-access response with an upgrade prompt — not an error or silent failure
  4. A new member who joins the server is guided through an onboarding flow that shows rules, FAQ, and a clear path to subscribe
  5. The `#free-picks` channel has at least 7 days of bot-generated edge posts visible when the server opens to the public — the server does not look empty on day one
**Plans**: TBD

Plans:
- [ ] 18-01-PLAN.md — Server channel structure (3-tier: free/mid/premium), role hierarchy, Whop Bot placement at top of role list, rules + FAQ + getting-started resources (Wave 1, DISCORD-01/05)
- [ ] 18-02-PLAN.md — Whop→Discord role sync: end-to-end test with real test subscription, idempotency key in webhook handler, Sentry alerts on role assignment failures, event log channel (Wave 2, DISCORD-02)
- [ ] 18-03-PLAN.md — Bot role-gated commands + `/upgrade` command + Discord Community Onboarding flow + 7-day content pre-seed in free channels (Wave 3, DISCORD-03/04)

### Phase 19: Marketing & Onboarding
**Goal**: Any visitor to the SharpEdge landing page understands the value, sees the pricing, and has a single clear action to take — and any new user who signs up is guided to their first meaningful experience within the same session.
**Depends on**: Phase 17 (live production domain required for landing page and privacy policy URL)
**Requirements**: GROWTH-01, GROWTH-02, GROWTH-03, GROWTH-04
**Success Criteria** (what must be TRUE):
  1. A visitor to the landing page sees a benefit-driven headline, three pricing tiers with Mid and Premium prices shown, and at least three real model performance data points — all above the fold on desktop and mobile
  2. A visitor can take exactly one primary action from the landing page hero: join Discord free or start a free trial — not multiple competing CTAs
  3. A new user who signs up on web sees a tour of the key features (top edge of the day, Kelly sizing, regime indicator) within their first session — without needing to read documentation
  4. A social media profile (X/Twitter minimum) exists with a pinned post linking to the Discord server and at least 5 posts of real SharpEdge output published before public launch
**Plans**: TBD

Plans:
- [ ] 19-01-PLAN.md — Landing page: benefit headline, pricing tiers, performance data points, single CTA, live privacy policy URL, mobile-responsive, <3s load (Wave 1, GROWTH-01/02)
- [ ] 19-02-PLAN.md — New user onboarding flow (in-app tour of top edge, Kelly sizing, regime indicator) + X/Twitter profile setup + pre-launch content posts (Wave 2, GROWTH-03/04)

### Phase 20: Mobile Submission
**Goal**: Both the iOS and Android apps are approved and publicly available on their respective app stores — with the iOS app passing Apple review under the read-only companion pattern (no payment UI) and the Android app promoted from internal track to production.
**Depends on**: Phase 17 (production backend required for store submission), Phase 19 (privacy policy URL required for App Store Connect)
**Requirements**: MOBILE-01, MOBILE-02, MOBILE-03, MOBILE-04, MOBILE-05
**Success Criteria** (what must be TRUE):
  1. A user can download the iOS app from the App Store, log in with their existing account, and see tier-gated features — with no pricing, upgrade buttons, or Whop links visible anywhere in the app
  2. A user can download the Android app from Google Play and access the same core features as the iOS app
  3. The App Store listing shows at minimum 6 captioned screenshots, a keyword-optimized title and subtitle, a description using the approved analytics-not-betting formula, a 17+ age rating, and a live privacy policy URL
  4. The iOS app has completed a TestFlight beta period and passed at least one full Apple App Review cycle before the public release date
  5. A merge to `main` that passes CI triggers automatic iOS and Android build jobs in parallel — a developer does not need to build locally to release a new version
**Plans**: TBD

Plans:
- [ ] 20-01-PLAN.md — Fastlane + GitHub Actions CI/CD: parallel iOS (macOS runner) + Android (ubuntu runner) build jobs, Fastlane match for iOS cert management, App Store Connect API Key + Google Play Service Account (Wave 1, MOBILE-01/02)
- [ ] 20-02-PLAN.md — iOS App Store Connect: `PrivacyInfo.xcprivacy` manifest, read-only companion pattern audit (zero payment UI), 17+ age rating, keyword-optimized metadata, 6 captioned screenshots, privacy policy URL, TestFlight beta (Wave 2, MOBILE-03/04)
- [ ] 20-03-PLAN.md — Android Play Store: internal track upload via Play Console web UI (first upload), promote to production after review, Play Store listing with screenshots and description (Wave 3, MOBILE-05)

### Phase 21: Monitoring
**Goal**: Errors and downtime are visible to the operator before users notice them — Sentry captures every unhandled exception across web, mobile, and Python services, and UptimeRobot alerts the operator the moment any service goes dark.
**Depends on**: Phase 17 (production services must exist before they can be monitored)
**Requirements**: MONITOR-01, MONITOR-02, MONITOR-03
**Success Criteria** (what must be TRUE):
  1. An unhandled exception in the Next.js web app, the Flutter mobile app, or the FastAPI webhook server appears as a Sentry issue within 60 seconds — tagged with `production` environment and the correct platform
  2. The Discord bot going offline (Railway service restart, crash, or deployment) triggers a Discord webhook alert to a private `#ops` channel within 5 minutes
  3. A user signing up, upgrading their tier, or using a core feature (running a bot command, loading the value plays page) emits a tracked event visible in the analytics dashboard
**Plans**: TBD

Plans:
- [ ] 21-01-PLAN.md — Sentry setup: 3 projects (Next.js `@sentry/nextjs ^8.x`, Flutter `sentry_flutter ^8.x`, Python `sentry-sdk ^2.x`) + production/staging environment tags + Sentry alert on webhook role-assignment handler exceptions (Wave 1, MONITOR-01)
- [ ] 21-02-PLAN.md — UptimeRobot: monitor FastAPI `/health` endpoint + web domain + Discord bot health check via Redis key ping; Discord webhook alerts to private `#ops` channel + key user event tracking (signup, upgrade, feature usage) (Wave 2, MONITOR-02/03)

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
| VENUE-01 | Phase 6 |
| VENUE-02 | Phase 6 |
| VENUE-03 | Phase 6 |
| VENUE-04 | Phase 6 |
| VENUE-05 | Phase 6 |
| PRICE-01 | Phase 6 |
| MICRO-01 | Phase 6 |
| DISLO-01 | Phase 6 |
| RISK-01 | Phase 6 |
| SETTLE-01 | Phase 6 |
| PIPE-01 | Phase 7 |
| WALK-01 | Phase 7 |
| CAL-01 | Phase 7 |
| GATE-01 | Phase 7 |
| INT-01 | Phase 7 |
| WIRE-01 | Phase 8 |
| WIRE-02 | Phase 8 |
| WIRE-03 | Phase 8 |
| WIRE-04 | Phase 8 |
| WIRE-05 | Phase 8 |
| WIRE-06 | Phase 8 |
| PM-DATA-01 | Phase 9 |
| PM-DATA-02 | Phase 9 |
| PM-RES-01  | Phase 9 |
| PM-RES-02  | Phase 9 |
| PM-INT-01  | Phase 9 |
| TRAIN-01 | Phase 10 |
| TRAIN-02 | Phase 10 |
| TRAIN-03 | Phase 10 |
| TRAIN-04 | Phase 10 |
| EXEC-01 | Phase 11 |
| EXEC-02 | Phase 11 |
| EXEC-04 | Phase 11 |
| EXEC-03 | Phase 12 |
| EXEC-05 | Phase 12 |
| ABLATE-01 | Phase 13 |
| ABLATE-02 | Phase 13 |
| GATE-01 (v2) | Phase 13 |
| GATE-02 | Phase 13 |
| GATE-03 | Phase 13 |
| GATE-04 | Phase 13 |
| DASH-01 | Phase 14 |
| DASH-02 | Phase 14 |
| ARB-01 | Phase 15 |
| ARB-02 | Phase 15 |
| ARB-03 | Phase 15 |
| ARB-04 | Phase 15 |
| AUTH-01 | Phase 16 |
| AUTH-02 | Phase 16 |
| AUTH-03 | Phase 16 |
| AUTH-04 | Phase 16 |
| AUTH-05 | Phase 16 |
| DEPLOY-01 | Phase 17 |
| DEPLOY-02 | Phase 17 |
| DEPLOY-03 | Phase 17 |
| DEPLOY-04 | Phase 17 |
| DISCORD-01 | Phase 18 |
| DISCORD-02 | Phase 18 |
| DISCORD-03 | Phase 18 |
| DISCORD-04 | Phase 18 |
| DISCORD-05 | Phase 18 |
| GROWTH-01 | Phase 19 |
| GROWTH-02 | Phase 19 |
| GROWTH-03 | Phase 19 |
| GROWTH-04 | Phase 19 |
| MOBILE-01 | Phase 20 |
| MOBILE-02 | Phase 20 |
| MOBILE-03 | Phase 20 |
| MOBILE-04 | Phase 20 |
| MOBILE-05 | Phase 20 |
| MONITOR-01 | Phase 21 |
| MONITOR-02 | Phase 21 |
| MONITOR-03 | Phase 21 |

**Total v1:** 35 | **Mapped:** 35 | **Unmapped:** 0
**Phase 6:** 10 new requirements
**Phase 7:** 5 new requirements
**Phase 8:** 6 new requirements
**Phase 9:** 5 new requirements
**v2.0 (Phases 10–14):** 17 new requirements | **Mapped:** 17 | **Unmapped:** 0
**Phase 15:** 4 new requirements | **Mapped:** 4 | **Unmapped:** 0
**v3.0 (Phases 16–21):** 26 new requirements | **Mapped:** 26 | **Unmapped:** 0

---
*Roadmap created: 2026-03-13*
*Updated: 2026-03-14 — Plan 01-01 complete (debt clearance + test stubs)*
*Updated: 2026-03-13 — Phase 2 plans created (02-01 through 02-04, 4 waves)*
*Updated: 2026-03-14 — Plan 02-02 complete (BettingAnalysisState + 9-node graph + all node implementations, 16 tests green)*
*Updated: 2026-03-13 — Plan 02-03 complete (BettingCopilot ReAct graph + 10 tools + trim_conversation, 13 tests green)*
*Updated: 2026-03-13 — Plan 02-04 complete (rank_by_alpha + alpha-ranked alert dispatch, 57 tests green) — Phase 2 COMPLETE*
*Updated: 2026-03-14 — Phase 3 plans created (03-01 through 03-03, 3 waves)*
*Updated: 2026-03-14 — Phase 4 plans created (04-00 through 04-07, 4 waves, 17 requirements covered)*
*Updated: 2026-03-14 — Phase 5 plans created (05-01 through 05-05, 5 waves)*
*Updated: 2026-03-14 — Phase 6 plans created (06-01 through 06-06, 6 waves, 10 requirements covered)*
*Updated: 2026-03-14 — Phase 6 extended (06-07 through 06-08 added: copilot venue tools + snapshot persistence)*
*Updated: 2026-03-14 — Phase 7 plans created (07-01 through 07-06, 6 waves, 5 requirements covered)*
*Updated: 2026-03-14 — Plan 07-02 complete (NCAAB/MLB/NHL data pipeline extension, zero-fill domain features)*
*Updated: 2026-03-15 — Phase 9 plans created (09-01 through 09-05, 4 waves, 5 requirements covered)*
*Updated: 2026-03-15 — Plan 09-01 complete (RED TDD stubs: 5 stub modules, 8 test files, all interface contracts locked)*
*Updated: 2026-03-15 — v2.0 milestone roadmap added (Phases 10–14, 17 requirements mapped, 100% coverage)*
*Updated: 2026-03-21 — v3.0 milestone roadmap added (Phases 16–21, 26 requirements mapped, 100% coverage)*
*Updated: 2026-03-21 — Phase 16 plans created (16-01 through 16-03, 2 waves, 5 requirements covered)*
