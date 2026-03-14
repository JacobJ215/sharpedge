# Next Phases Brief — SharpEdge v2

**Created:** 2026-03-14
**Purpose:** Reference document for the two upcoming work items before the next milestone.

---

## Item 1: Model Pipeline Completion

**Goal:** All models are trained, calibrated, backtested, and walk-forward validated with honest out-of-sample quality scores. The system continuously improves through rolling calibration.

### What Needs to Be Done

#### Data Pipeline
- Run `scripts/download_historical_data.py` for all supported sports (NBA, NFL, NCAAB, MLB, NHL)
- Run `scripts/process_historical_data.py` to produce feature-complete datasets
- Verify `FeatureAssembler` (Phase 5) produces correct `GameFeatures` for all sports
- Confirm time-correct train/validation/test splits (no lookahead bias)

#### Model Training
- Run `scripts/train_models.py` to train all 5 ensemble models:
  - Team form model (last 10 results, opponent strength, rest days)
  - Matchup history model (head-to-head splits)
  - Injury impact model (injury report integration)
  - Market sentiment model (line movement velocity, public betting %)
  - Weather/travel model (home/away splits, travel penalty)
- Train `EnsembleManager` stacking layer on out-of-fold predictions
- Verify OOF indices stored alongside OOF predictions (no leakage)
- Persist trained models to `data/models/`

#### Walk-Forward Backtesting
- Run walk-forward backtest via `WalkForwardBacktester` (Phase 1/5)
- Non-overlapping windows, no lookahead
- Produce per-window breakdown: win rate, ROI, edge after fees
- Generate quality badge: `low / medium / high / excellent`
- Calibration error must be below threshold before promotion

#### Platt Calibration
- Run `CalibrationStore` on lagged (not live) out-of-sample data
- Fit Platt scaling per model, per sport, per market family
- Update `confidence_mult` used in composite alpha score
- Verify calibration plots are reasonable (no overfit)

#### Venue-Specific Calibration (Phase 6 extension)
- Run calibration reports for Kalshi binary markets by category and time-to-close
- Run calibration reports for Polymarket markets
- Run no-vig sportsbook calibration by sport and bet type (moneyline, spread, total)
- Cross-venue dislocation baseline: establish consensus price benchmark

#### Integration Tests
- `packages/models/tests/` — full model pipeline integration test
- Verify `compose_alpha()` incorporates calibrated confidence_mult correctly
- Verify `run_models()` wiring in webhook_server/jobs
- Verify weekly retrain scheduler triggers correctly

#### Promotion Gate Checklist
Before any model goes live in production scoring:
- [ ] Calibration error < threshold (Brier score or ECE)
- [ ] Minimum post-cost edge > 2% on test set
- [ ] Maximum drawdown within limit on walk-forward windows
- [ ] Minimum 30-day paper stability period
- [ ] Walk-forward quality badge: `high` or `excellent`

---

## Item 2: Frontend Completion

**Goal:** The web dashboard (Next.js) and mobile app (Flutter) are fully wired to all backend capabilities — real data, real auth, real APIs — with no mock stubs or placeholder endpoints remaining.

### Web Dashboard (Next.js)

#### Pages to Complete / Verify
| Page | Route | Backend Endpoint | Status |
|------|-------|-----------------|--------|
| Portfolio Overview | `/` | `GET /api/v1/users/{id}/portfolio` | Verify real auth token |
| Value Plays | `/plays` | `GET /api/v1/value-plays` | Verify alpha ranking + regime badge |
| Game Detail | `/games/{id}` | `GET /api/v1/games/{id}/analysis` | Verify full analysis object |
| Bankroll | `/bankroll` | `POST /api/v1/bankroll/simulate` | Verify Monte Carlo fan chart |
| BettingCopilot | `/copilot` | `POST /api/v1/copilot/chat` (SSE) | Verify streaming + all 12 tools |
| Prediction Markets | `/markets` | Phase 3 PM edge scanner | Verify PM edges + regime |
| Venue Dislocation | Add to `/markets` | `get_venue_dislocation` copilot tool | New — Phase 6 |
| Exposure Status | Add to `/bankroll` | `get_exposure_status` copilot tool | New — Phase 6 |

#### Remaining Web Tasks
- Wire real Supabase JWT from auth session into all API calls (remove placeholder `""` token)
- Complete `apps/web/src/app/auth/` — login, callback, session handling
- Verify RLS enforced on all user-scoped routes (portfolio, bets)
- Add venue dislocation widget to prediction markets page
- Add exposure/Kelly utilization widget to bankroll page
- End-to-end test: login → view plays → log bet → see portfolio update

### Flutter Mobile App

#### Screens to Complete / Verify
| Screen | API Integration | Status |
|--------|----------------|--------|
| Login | Supabase auth (biometric) | Verify Face ID / fingerprint flow |
| Home feed | `GET /api/v1/value-plays` | Verify alpha-ranked, swipe-to-log |
| BettingCopilot chat | `POST /api/v1/copilot/chat` (SSE) | Verify streaming SSE in Flutter |
| Portfolio | `GET /api/v1/users/{id}/portfolio` | Verify ROI, win rate, CLV |
| Bankroll | `POST /api/v1/bankroll/simulate` | Verify fan chart |
| Prediction Markets | PM edge scanner | Verify PM edges + regime |
| Arbitrage | Phase 3 correlation warnings | Verify correlation alerts |
| Line Movement | Phase 3 scanner | Verify line movement feed |

#### Remaining Flutter Tasks
- Verify `ApiService` base URL points to deployed webhook_server (not localhost)
- Complete FCM push notification registration flow (token registration on login)
- Verify push notification fires before Discord alert for PREMIUM/HIGH alpha
- Wire `apps/mobile/lib/screens/arbitrage_screen.dart` to real PM correlation endpoint
- Wire `apps/mobile/lib/screens/line_movement_screen.dart` to real scanner
- Test on physical device (iOS + Android) — biometric auth requires real device
- Verify offline degradation — app usable without network (cached last feed)

### Shared Backend Verification
- All Phase 4 FastAPI endpoints tested with real Supabase RLS (not test bypass)
- `apps/webhook_server/src/sharpedge_webhooks/jobs/` scanners running in production mode
- Phase 6 `packages/venue_adapters/` wired into webhook_server for live Kalshi/Polymarket data
- `SnapshotStore` persistence verified with real Supabase connection
- `LedgerEntry` writing to real `ledger_entries` table

---

## Suggested Phase Structure

### Phase 7: Model Pipeline Completion
**Goal:** All 5 models trained, walk-forward validated, Platt-calibrated, and gated through promotion criteria. Composite alpha scores reflect honest out-of-sample quality badges.

**Key deliverables:**
- Trained model artifacts in `data/models/`
- Walk-forward report with quality badge ≥ `high`
- Calibration reports per sport and venue family
- Integration tests: full pipeline from raw data → alpha score → Discord alert

### Phase 8: Frontend Polish & Full Backend Wiring
**Goal:** Zero placeholder endpoints, zero mock data — every screen in web and mobile reads from real production APIs with real auth.

**Key deliverables:**
- Web auth flow complete (Supabase JWT in all calls)
- Phase 6 venue dislocation + exposure widgets live in UI
- Flutter app end-to-end tested on physical device
- FCM push notifications verified
- All 12 BettingCopilot tools exercised from both web and mobile chat

---

*Document created: 2026-03-14*
*Use this as context when running `/gsd:add-phase` for Phase 7 and Phase 8.*
