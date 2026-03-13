# SharpEdge v2

## What This Is

SharpEdge is an institutional-grade probabilistic intelligence platform for sports betting and prediction markets. It combines a Discord bot with a full quantitative engine, multi-specialist agent orchestration, and multi-platform front-ends (web + mobile) to give bettors the same analytical rigor that quant trading firms apply to financial markets.

## Core Value

Surface high-alpha betting edges — ranked by composite probability score (EV × regime × survival × confidence) — before anyone else sees them, with bankroll risk quantified so users bet the right size every time.

## Requirements

### Validated

- ✓ Discord bot with 9 slash commands — existing
- ✓ EV calculator with Bayesian confidence (P(edge > 0) via Beta distribution) — existing
- ✓ No-vig fair odds calculation — existing
- ✓ Arbitrage detection (cross-book + Kalshi × sportsbooks) — existing
- ✓ Line movement classification (steam, RLM, buyback) — existing
- ✓ Kelly Criterion sizing — existing
- ✓ Gradient boosting ML models (spread, totals) — existing
- ✓ Historical odds + outcomes pipeline — existing
- ✓ Kalshi + Polymarket API clients — existing
- ✓ Supabase DB with solid schema — existing
- ✓ Whop monetization — existing

### Active

- [ ] Alpha scoring system (composite EV × regime × survival × confidence)
- [ ] Monte Carlo bankroll simulator (ruin probability, path distribution)
- [ ] Walk-forward backtester (out-of-sample validation, quality badges)
- [ ] Betting market regime detector (7-state HMM classifier)
- [ ] Key number zone detector (NFL/NBA/MLB/NHL spread + total clusters)
- [ ] LangGraph StateGraph agent orchestration (9-node workflow)
- [ ] BettingCopilot (conversational analysis with full portfolio awareness)
- [ ] LLM setup evaluator (PASS/WARN/REJECT gate before alerting)
- [ ] Prediction market edge scanner (model prob vs market prob)
- [ ] Cross-market correlation engine (prevent correlated overexposure)
- [ ] PM regime classification
- [ ] FastAPI REST layer (web + mobile clients)
- [ ] Next.js 14 web dashboard (8 pages)
- [ ] Expo/React Native mobile app (push notifications, swipe-to-track)
- [ ] 5-model ensemble upgrade (team form, matchup, injury, sentiment, weather)
- [ ] Continuous calibration engine (Platt scaling, auto-weighting)

### Out of Scope

- Real-time chat between users — not core to platform value
- Social/community features — defer to v3+
- Direct sportsbook account integration — regulatory complexity, out of scope
- Automated bet placement — user places bets manually, platform provides intelligence only

## Context

This is a brownfield upgrade. The existing codebase is a uv Python monorepo with:
- `apps/bot/` — Discord bot (discord.py, OpenAI Agents SDK)
- `apps/webhook_server/` — FastAPI Whop/Stripe webhook handler
- `packages/models/` — EV calculator, Kelly, gradient boosting ML, backtesting stubs
- `packages/analytics/` — arbitrage, line movement, value scanner, visualizations
- `packages/data_feeds/` — ESPN, Kalshi, Polymarket, weather, public betting clients
- `packages/database/` — Supabase client, 5 migrations, domain-scoped query modules
- `packages/odds_client/` — The Odds API wrapper (30+ books)
- `packages/shared/` — cross-package types, errors, constants

The upgrade is a Python port of quantitative patterns from FinnAI (TypeScript) — formulas and logic, not code copy-paste. LangGraph (Python) replaces the current flat 3-agent OpenAI SDK setup.

Zero test coverage currently. Backtesting persistence layer has 4 unimplemented stubs. `visualizations.py` (896 lines) and `tools.py` (576 lines) exceed the 500-line limit and need splitting.

## Constraints

- **Language**: Python only (uv workspace) — no TypeScript in backend
- **Agent framework**: LangGraph (Python) for StateGraph orchestration
- **LLM routing**: GPT-4o for analysis nodes, GPT-4o-mini for routing/eval nodes
- **Database**: Supabase stays; add Redis for real-time caching layer
- **Front-end**: Next.js 14 (web) + Expo (mobile) — shared TypeScript API client
- **File size**: Keep all modules under 500 lines
- **Math ports**: Port FinnAI quant formulas (Monte Carlo, EV, Kelly) — don't copy TS code

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LangGraph over OpenAI Agents SDK for orchestration | Graph-based routing, parallel specialist nodes, state management — matches FinnAI's quantFactory pattern | — Pending |
| Composite alpha score as single ranking metric | Prevents optimizing EV alone without accounting for regime/survival/calibration quality | — Pending |
| Monte Carlo as primary risk communication tool | Users understand "3.2% ruin over 500 bets" better than abstract Kelly fractions | — Pending |
| 7-regime HMM for betting market state | Directly maps sharp/public/steam/thin signals to alpha multipliers | — Pending |
| Keep existing ev_calculator.py — extend, don't replace | Already excellent Bayesian EV implementation | — Pending |

---
*Last updated: 2026-03-13 after initialization*
