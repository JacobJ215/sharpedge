# SharpEdge Upgrade Roadmap
## FinnAI → SharpEdge: Institutional-Grade Prediction Markets & Sports Betting

> **Goal**: Transform SharpEdge from a Discord bot with basic AI agents into an institutional-grade probabilistic intelligence platform — applying the full quantitative rigor of FinnAI to sports betting and prediction markets.

---

## Current State Assessment

### What SharpEdge Already Has (Good Foundation)
- Discord.py bot with 9 slash commands
- Basic OpenAI agent system (Game Analyst, Research Agent, Review Agent)
- EV calculator with Bayesian confidence (P(edge > 0) via Beta distribution)
- No-vig fair odds calculation
- Arbitrage detection (cross-book + Kalshi × sportsbooks)
- Line movement classification (steam, RLM, buyback)
- Kelly Criterion sizing
- Gradient boosting ML models (spread, totals)
- Historical odds + outcomes pipeline
- Kalshi + Polymarket API clients
- Supabase DB with solid schema
- Whop monetization

### What's Missing (The Gap vs FinnAI)
1. **Shallow agent orchestration** — 3 standalone agents, no graph-based workflow, no specialist routing, no copilot pattern
2. **No Monte Carlo bankroll simulation** — no ruin probability, no path distribution, no tail risk quantification
3. **No regime detection** — no classification of betting market conditions (sharp-dominated, public-heavy, thin, consensus)
4. **Weak backtesting pipeline** — no walk-forward validation, no out-of-sample testing, no ablation studies
5. **No alpha scoring** — predictions not composed into a single edge-weighted score
6. **No prediction market mispricings** — PM clients exist but only used for arbitrage, not probabilistic edge detection
7. **Discord-only UI** — no web dashboard, no mobile app
8. **No copilot** — no conversational analysis tool with full context awareness

---

## Upgrade Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     SharpEdge v2                                │
├─────────────────────────────────────────────────────────────────┤
│  FRONT-ENDS                                                     │
│  ├── Discord Bot (keep, enhance alerts)                         │
│  ├── Web Dashboard (Next.js — new)                              │
│  └── Mobile App (React Native / Expo — new)                     │
├─────────────────────────────────────────────────────────────────┤
│  AGENT LAYER (LangChain + OpenAI Agents SDK)                    │
│  ├── BettingCopilot (conversational analysis tool)              │
│  ├── Specialist Agents (graph-routed, parallel)                 │
│  │   ├── Line Analyst (odds movement, sharp vs public)          │
│  │   ├── Game Researcher (stats, injuries, weather, travel)     │
│  │   ├── PM Analyst (Kalshi/Polymarket edge detection)          │
│  │   ├── Quant Strategist (model selection, EV composition)     │
│  │   ├── Risk Manager (Kelly, bankroll, exposure limits)        │
│  │   └── Reporter (alert generation, explanation)              │
│  └── Evaluator (LLM validates setups before alerting)          │
├─────────────────────────────────────────────────────────────────┤
│  QUANTITATIVE ENGINE                                            │
│  ├── Alpha Composer (edge × survival × regime × confidence)     │
│  ├── Monte Carlo Bankroll Simulator                             │
│  ├── Walk-Forward Backtester                                    │
│  ├── Regime Detector (betting market state HMM)                 │
│  ├── Calibration Engine (model accuracy tracking)              │
│  └── Key Number Zones (FinnAI-style support/resistance)        │
├─────────────────────────────────────────────────────────────────┤
│  DATA LAYER (existing + enhanced)                               │
│  ├── The Odds API (30+ sportsbooks)                             │
│  ├── Kalshi + Polymarket                                        │
│  ├── ESPN + Weather                                             │
│  ├── Public betting data                                        │
│  └── Historical odds archive (Supabase)                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Quantitative Engine Upgrade
*Priority: Highest — this is the core value*

### 1.1 Alpha Scoring System

Port FinnAI's `AnchorFlowTypes.ts` alpha composition to Python. Replace raw EV% with a composite score:

```python
@dataclass
class BettingAlpha:
    ev_score: float          # EV% from current ev_calculator.py
    edge_prob: float         # P(edge > 0) — already built
    regime_scale: float      # 0.5-1.5 based on market regime
    survival_prob: float     # P(line holds to game time)
    confidence_mult: float   # Calibration quality multiplier

    @property
    def alpha(self) -> float:
        """
        Composite edge score. Port of FinnAI's:
        alpha = edgeScore × survivalProb × regimeScale × calibrationBoost

        For betting:
        alpha = edge_prob × ev_score × regime_scale × survival_prob × confidence_mult
        """
        edge_score = self.edge_prob * (1 + self.ev_score) - (1 - self.edge_prob)
        return edge_score * self.survival_prob * self.regime_scale * self.confidence_mult
```

This becomes the single ranking metric for all alerts. Higher alpha = post first.

### 1.2 Monte Carlo Bankroll Simulator

Port FinnAI's `monteCarloSimulator.ts` to Python. This is critical for communicating risk to users:

```python
class MonteCarloSimulator:
    def simulate_bankroll(
        self,
        win_prob: float,
        odds_decimal: float,
        unit_size_pct: float,  # % of bankroll per bet
        num_bets: int = 500,
        num_paths: int = 2000,
        seed: int = 42,
    ) -> MonteCarloResult:
        """
        Simulate 2000 betting sequences to produce:
        - P(ruin): Probability bankroll → 0
        - P95 outcome: 95th percentile bankroll after N bets
        - P05 outcome: 5th percentile (drawdown risk)
        - Median outcome: Expected path
        - Max drawdown distribution

        Uses seeded Box-Muller transform (same approach as FinnAI).
        """
```

**Output usage**:
- Show users "with 1.5 unit Kelly sizing: 3.2% ruin probability over 500 bets"
- Alert when user's bet history puts them in high-ruin regime
- Size recommendations based on ruin tolerance (aggressive/moderate/conservative)

### 1.3 Walk-Forward Backtester

Replace current `backtesting.py` (calibration only) with a full walk-forward engine:

```python
class WalkForwardBacktester:
    """
    Port of FinnAI's quantFactory backtest + walk-forward validation.

    For each betting strategy:
    1. Split historical bets into rolling windows (e.g., 2 seasons train, 1 season test)
    2. Train on train window, evaluate on test window
    3. Aggregate across all windows: win rate stability, ROI consistency
    4. Flag strategies where out-of-sample degrades significantly (overfitting)
    5. Run Monte Carlo on aggregated trade set for ruin/profit distribution
    """

    def validate(self, strategy_name: str, historical_bets: list[BetRecord]) -> BacktestReport:
        ...

@dataclass
class BacktestReport:
    summary: BacktestSummary
    walk_forward_windows: list[WindowResult]  # Per-window performance
    out_of_sample_win_rate: float             # Key metric
    out_of_sample_roi: float
    monte_carlo: MonteCarloResult             # Ruin/profit distribution
    quality_badge: Literal['low', 'medium', 'high', 'excellent']
    quality_warnings: list[str]               # e.g., "Win rate drops 12% out-of-sample"
```

### 1.4 Betting Market Regime Detector

Port FinnAI's HMM market state engine (`deterministic/`, `anchorflow/`) to classify betting market conditions:

```python
class BettingRegimeDetector:
    """
    Classifies current market conditions for a given game/market.
    Analogous to FinnAI's 7-state HMM for equity markets.
    """

    REGIMES = [
        'SHARP_CONSENSUS',      # Sharp books all aligned, public following
        'SHARP_VS_PUBLIC',      # Sharp money opposite public — RLM present  ← highest alpha
        'PUBLIC_HEAVY',         # >70% public tickets, books haven't moved  ← fade signal
        'STEAM_MOVE',           # Rapid coordinated sharp move in progress
        'THIN_MARKET',          # Low handle, unreliable signals
        'POST_NEWS',            # Injury/lineup news causing adjustment
        'SETTLED',              # Stable, market consensus reached
    ]

    def classify(self, game_id: str) -> RegimeState:
        """
        Uses: line movement history, ticket%, handle%, book alignment, velocity
        Returns: regime + confidence + recommended_action
        """
```

**Regime → Alpha mapping** (direct port from FinnAI regime scaling):
- `SHARP_VS_PUBLIC`: regime_scale = 1.4 (RLM is the strongest edge)
- `STEAM_MOVE` (first 30 min): regime_scale = 1.2
- `PUBLIC_HEAVY`: regime_scale = 1.1 (fade public)
- `SHARP_CONSENSUS`: regime_scale = 1.0
- `THIN_MARKET`: regime_scale = 0.5 (reduce confidence)
- `POST_NEWS`: regime_scale = 0.7 (wait for market to settle)

### 1.5 Key Number Zones (FinnAI-Inspired)

FinnAI detects supply/demand zones where institutional orders cluster. In sports betting, **key numbers** serve the same role — spreads cluster at -3, -7, -10 in NFL; totals cluster at 43, 44, 47:

```python
class KeyNumberZoneDetector:
    """
    Inspired by FinnAI's zone detection (AnchorFlow zonePrimitives).

    Finds spreads/totals at or near key numbers and assesses:
    - Historical cover rate when line is AT key number (e.g., -3 in NFL)
    - Value of buying half-point through key number vs current odds
    - Whether current line offers edge at this number vs historical base rate
    """

    NFL_KEY_NUMBERS = {
        'spread': [3, 7, 10, 14, 6, 4],    # Margin of victory clusters
        'total': [43, 44, 45, 47, 51, 37],  # Common scoring totals
    }

    def analyze(self, line: float, sport: str, market_type: str) -> ZoneAnalysis:
        """
        Returns: at_key_number, half_point_value, historical_cover_rate, zone_strength
        """
```

---

## Phase 2: Agent Architecture Upgrade
*Replaces 3 standalone agents with graph-routed specialist system*

### 2.1 LangChain StateGraph Orchestration

Port FinnAI's `quantFactory/workflow.ts` (LangChain StateGraph with 15+ nodes) to Python. This is the core orchestration upgrade:

```python
# packages/agents/src/sharpedge_agents/workflow.py

from langgraph.graph import StateGraph, END

class BettingAnalysisState(TypedDict):
    request: str                    # User's natural language request
    intent: BettingIntent           # Normalized intent (sport, market_type, game)
    game_context: GameContext       # Odds, injuries, weather, stats
    regime_state: RegimeState       # Current betting market regime
    model_predictions: ModelPreds   # Ensemble model output
    ev_analysis: EVAnalysis         # Expected value with confidence
    monte_carlo: MonteCarloResult   # Bankroll risk simulation
    recommendation: Recommendation  # Final bet/pass/watch decision
    explanation: str                # Natural language explanation
    quality_badge: str              # 'PREMIUM' | 'HIGH' | 'MEDIUM' | 'SPECULATIVE'

# Graph nodes (specialist agents):
graph = StateGraph(BettingAnalysisState)
graph.add_node("route_intent", route_intent)        # Normalize & classify request
graph.add_node("fetch_context", fetch_game_context) # Odds + injuries + weather
graph.add_node("detect_regime", detect_regime)      # Market condition classification
graph.add_node("run_models", run_model_ensemble)    # ML predictions
graph.add_node("calculate_ev", calculate_ev)        # EV + confidence
graph.add_node("validate_setup", validate_setup)    # LLM evaluator gate
graph.add_node("compose_alpha", compose_alpha)      # Alpha = EV × regime × survival
graph.add_node("size_position", size_position)      # Kelly + Monte Carlo
graph.add_node("generate_report", generate_report)  # Format for Discord/web/mobile
```

**Routing**:
- Sports moneyline → `run_models → calculate_ev → validate → report`
- Prediction market → `fetch_pm_context → detect_mispricing → validate → report`
- Arbitrage → `scan_books → verify_arb → size_arb → report`
- Copilot question → `route_to_copilot`

### 2.2 Betting Copilot

Direct port of FinnAI's `liquidityDislocation/copilot.ts` + `copilotTools.ts`:

```python
class BettingCopilot:
    """
    Conversational analysis tool with full portfolio awareness.

    User can ask: "Should I bet Lakers -3.5 tonight?"
    Copilot: fetches odds, runs model, checks bankroll exposure,
             detects regime, computes alpha, gives recommendation with reasoning.

    Maintains snapshot state — follow-up questions have full context.
    """

    snapshot: CopilotSnapshot   # Current portfolio + active games + alerts

    # Tools (analogous to FinnAI copilotTools.ts):
    tools = [
        get_active_bets,            # Current open bets with exposure
        get_portfolio_stats,         # ROI, win rate, CLV, drawdown
        analyze_game,                # Full analysis pipeline for a game
        search_value_plays,          # Filter by min_alpha
        check_line_movement,         # Movement history + regime
        get_sharp_indicators,        # Sharp vs public data
        estimate_bankroll_risk,      # Monte Carlo for current portfolio
        get_prediction_market_edge,  # Kalshi/Polymarket mispricing
        compare_books,               # Best available odds + no-vig
        get_model_predictions,       # ML model output for game
    ]
```

### 2.3 LLM Setup Evaluator

Port FinnAI's `anchorflowSwingEvaluator.ts` — an LLM that validates setups before alerting:

```python
class BettingSetupEvaluator:
    """
    Final LLM gate before an alert is sent.

    In FinnAI: vision model checks chart + zone to catch traps.
    Here: LLM checks betting setup for red flags.

    Checks:
    - Is the model prediction consistent with line movement direction?
    - Are there any contradictory signals (sharp fading our bet side)?
    - Is this a "trap" public line or genuine edge?
    - Does injury news materially affect the prediction?
    - Is the bet within recommended bankroll exposure limits?

    Returns: PASS / WARN / REJECT + reasoning
    """

    async def evaluate(self, setup: BettingSetup, context: GameContext) -> EvalResult:
        prompt = self._build_eval_prompt(setup, context)
        response = await openai_client.chat(prompt)
        return self._parse_eval_response(response)
```

---

## Phase 3: Prediction Market Intelligence
*Apply quant rigor to Kalshi/Polymarket — beyond arbitrage*

### 3.1 Probabilistic Mispricing Detection

Currently: Kalshi/Polymarket are only used for cross-platform arbitrage detection.
**Upgrade**: Detect when market probability materially differs from model probability:

```python
class PredictionMarketEdgeScanner:
    """
    For each active PM market:
    1. Fetch current market probability (from CLOB mid price)
    2. Run our own model to estimate true probability
    3. Compute edge = model_prob - market_prob
    4. If |edge| > threshold AND P(edge > 0) > 70%:
       → Generate alpha-scored alert

    Analogous to FinnAI's strategy detection but for binary prediction markets.
    """

    async def scan_kalshi(self) -> list[PMEdge]:
        markets = await kalshi_client.get_active_markets()
        edges = []
        for market in markets:
            model_prob = await self._estimate_probability(market)
            market_prob = market.yes_price  # CLOB mid
            edge = model_prob - market_prob
            if abs(edge) > 0.03:  # >3% edge minimum
                alpha = await self._compute_alpha(market, edge, model_prob)
                if alpha > ALPHA_THRESHOLD:
                    edges.append(PMEdge(market=market, edge=edge, alpha=alpha))
        return sorted(edges, key=lambda x: x.alpha, reverse=True)
```

### 3.2 Cross-Market Correlation Engine

```python
class CrossMarketCorrelationEngine:
    """
    Finds correlated positions across sports and prediction markets.

    Example: NBA team wins tonight correlates with their star player
    scoring 25+ on Kalshi. If we have edge on team win, we may have
    correlated edge on player props.

    Also: Sports result correlates with Kalshi election/economics markets
    (e.g., "Super Bowl winner predicts stock market direction").

    Prevents over-exposure to correlated bets (critical for Kelly sizing).
    """

    def check_portfolio_correlation(self, proposed_bet: Bet, current_bets: list[Bet]) -> float:
        """Returns correlation coefficient. >0.6 triggers exposure warning."""
```

### 3.3 PM Regime Classification

Apply the regime detector to prediction markets too:

- **Discovery Phase**: New market, low liquidity, price discovery ongoing → thin, avoid
- **Consensus Phase**: Market has converged, price stable → only enter with strong model edge
- **News Catalyst**: Breaking news causing repricing → assess direction before entry
- **Pre-Resolution**: Hours before resolution, price approaching 0/100 → avoid
- **Sharp Disagreement**: Market price far from model + sharp money present → investigate

---

## Phase 4: Front-End Upgrade
*From Discord-only to multi-platform*

### 4.1 Web Dashboard (Next.js)

**Stack**: Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui

**Reference**: FinnAI's `apps/web/` — same structure, adapt for betting context.

**Pages**:
```
/dashboard          — Portfolio overview: ROI, win rate, CLV, bankroll curve
/value-plays        — Live alpha-ranked betting opportunities
/game/:id           — Full game analysis (copilot embedded)
/prediction-markets — Kalshi/Polymarket edge dashboard
/arbitrage          — Live arbitrage opportunities with sizing
/bankroll           — Monte Carlo simulator, Kelly calculator, exposure limits
/performance        — Walk-forward backtest results, model calibration
/copilot            — Chat interface for BettingCopilot
```

**Key components** (reuse FinnAI patterns where possible):
- `AlphaScoreCard` — Displays alpha badge (PREMIUM/HIGH/MEDIUM/SPECULATIVE) with breakdown
- `MonteCarloChart` — Fan chart showing bankroll paths (P5/P50/P95)
- `RegimeIndicator` — Current market regime with explanation
- `OddsComparisonTable` — Multi-book odds with no-vig highlighted
- `LineMovementChart` — FinnAI-style time-series chart for line history
- `CopilotPanel` — Embedded chat with BettingCopilot

### 4.2 Mobile App (React Native / Expo)

**Stack**: Expo (React Native), TypeScript, NativeWind (Tailwind for RN)

**Why Expo**: Fastest path to iOS + Android from shared codebase. Can share types/API client with web.

**Architecture**:
```
apps/mobile/
├── app/                    # Expo Router (file-based routing)
│   ├── (tabs)/
│   │   ├── index.tsx       # Feed — live value plays
│   │   ├── copilot.tsx     # BettingCopilot chat
│   │   ├── portfolio.tsx   # Bet tracker + stats
│   │   └── markets.tsx     # Prediction markets
│   └── game/[id].tsx       # Game detail
├── components/
│   ├── AlphaBadge.tsx
│   ├── BetCard.tsx
│   ├── OddsDisplay.tsx
│   └── RegimeChip.tsx
└── lib/
    └── api/                # Shared API client (reuse web types)
```

**Mobile-specific features**:
- Push notifications for high-alpha alerts (before Discord)
- Swipe-to-track: swipe right on a value play to log it
- Live widgets (iOS — bankroll + pending bets)
- Biometric auth for account access

### 4.3 Shared API Layer

Add a REST/GraphQL API layer so both web and mobile consume the same data:

```
apps/api/                   # FastAPI (extend existing webhook_server)
├── routes/
│   ├── value_plays.py      # GET /api/v1/value-plays?min_alpha=0.1
│   ├── game_analysis.py    # GET /api/v1/games/:id/analysis
│   ├── copilot.py          # POST /api/v1/copilot/chat (streaming)
│   ├── portfolio.py        # GET /api/v1/users/:id/portfolio
│   ├── bankroll.py         # POST /api/v1/bankroll/simulate
│   └── prediction_markets.py
```

---

## Phase 5: Enhanced Data & Model Pipeline

### 5.1 Ensemble Model Upgrade

Currently: 2 sklearn gradient boosting models (spread, totals).
**Upgrade**: 5-model ensemble inspired by FinnAI's multi-factor approach:

```python
BettingEnsemble:
  models:
    - team_form_model        # Recent performance (last 10 games)
    - matchup_history_model  # Head-to-head historical rates
    - injury_impact_model    # Player availability → projected output delta
    - market_sentiment_model # Sharp money signal classifier
    - weather_travel_model   # Rest days, travel distance, weather

  aggregation: weighted_average
  weights: calibrated per sport per season (recalibrated monthly)
  output: ensemble_prob + confidence_interval + disagreement_score
```

### 5.2 Real-Time Feature Pipeline

```python
class GameFeatureBuilder:
    """
    Port of FinnAI's alpacaTool multi-timeframe data builder.

    For each game, builds feature vector from:
    - Last 10 game results + margins
    - Opponent strength (recent record, scoring avg)
    - Rest days for each team
    - Injury report (weighted by player importance)
    - Home/away performance split
    - Weather (for outdoor sports)
    - Line movement velocity (opens vs current)
    - Public betting % (ticket + handle)
    - Historical performance at this spread (key number proximity)
    """

    def build(self, game_id: str, sport: Sport) -> FeatureVector:
        ...
```

### 5.3 Continuous Calibration

Port FinnAI's `backtesting.py` calibration engine + `anchorflowIntradayEvaluator` self-evaluation:

```python
class ContinuousCalibrationEngine:
    """
    After each game resolves:
    1. Record predicted probability vs actual outcome
    2. Update Platt scaling parameters for each model
    3. Update confidence multiplier for alpha composer
    4. Flag models that drift (accuracy drops vs baseline)
    5. Auto-weight ensemble based on rolling accuracy

    Reports calibration quality badge (same as FinnAI):
    UNCALIBRATED → PRELIMINARY → CALIBRATED → WELL_CALIBRATED
    """
```

---

## Technology Decisions

| Component | Current | Recommended Upgrade | Why |
|-----------|---------|--------------------|----|
| Agent framework | OpenAI Agents SDK (basic) | LangChain + OpenAI Agents SDK | Graph-based routing, specialist agents, state management |
| LLM | GPT-5-mini | GPT-4o (analysis) + GPT-4o-mini (routing/eval) | Balance cost vs quality for different nodes |
| Backtesting | Basic calibration only | Walk-forward + Monte Carlo | Prevent overfitting, quantify uncertainty |
| Database | Supabase (PostgreSQL) | Keep + add Redis for real-time | Good foundation, add caching layer |
| Front-end | Discord only | Next.js + Expo (React Native) | Web + mobile from shared TypeScript |
| API | FastAPI webhook only | FastAPI with full REST + streaming | Support web/mobile clients |
| ML | Sklearn gradient boosting | Keep + add ensemble + calibration | Good base, needs ensemble + recalibration |

---

## Implementation Order

### Week 1-2: Quant Engine (Highest Value)
1. `MonteCarloSimulator` — Python port, ruin probability, bankroll distribution
2. `BettingRegimeDetector` — 7 regimes, HMM-inspired classification
3. `AlphaComposer` — Combine EV × regime × survival × confidence
4. `KeyNumberZoneDetector` — NFL/NBA/MLB/NHL key numbers
5. Replace raw EV% ranking with alpha ranking across all alerts

### Week 3-4: Agent Upgrade
1. LangChain StateGraph skeleton + intent routing
2. Specialist nodes: context fetcher, regime detector, EV calculator, alpha composer
3. `BettingSetupEvaluator` — LLM gate before alerting
4. Walk-forward backtester
5. `BettingCopilot` with full tool set

### Week 5-6: Prediction Market Intelligence
1. `PredictionMarketEdgeScanner` — model probability vs market probability
2. `CrossMarketCorrelationEngine` — prevent correlated overexposure
3. PM regime classification
4. Kalshi + Polymarket copilot tools (add to copilot)
5. PM alerts via Discord + new API

### Week 7-8: API + Web Dashboard
1. FastAPI expansion — all routes for web/mobile
2. Next.js project setup + auth (Supabase auth)
3. Core pages: dashboard, value plays, game detail, bankroll simulator
4. BettingCopilot chat UI (streaming)
5. Monte Carlo bankroll chart

### Week 9-10: Mobile App
1. Expo project setup + shared types
2. Core screens: feed, copilot, portfolio, markets
3. Push notifications (Expo + Firebase)
4. Swipe-to-track gesture
5. Biometric auth

### Week 11-12: Polish + Calibration
1. Ensemble model upgrade + recalibration pipeline
2. Walk-forward validation dashboard
3. Model disagreement alerts
4. Performance attribution (which model/feature drives wins)
5. A/B test alpha thresholds

---

## Key Files to Port from FinnAI

| FinnAI File | Port To SharpEdge | Notes |
|-------------|-------------------|-------|
| `quantIntraday/sim/monteCarloSimulator.ts` | `packages/models/src/sharpedge_models/monte_carlo.py` | Core simulation logic, Python rewrite |
| `quantIntraday/ev/evEvaluator.ts` | Extend existing `ev_calculator.py` | Add composite alpha output |
| `quantFactory/workflow.ts` | `packages/agents/src/sharpedge_agents/workflow.py` | LangChain StateGraph |
| `strategies/liquidityDislocation/copilot.ts` | `apps/bot/src/sharpedge_bot/agents/copilot.py` | BettingCopilot |
| `strategies/liquidityDislocation/copilotTools.ts` | `apps/bot/src/sharpedge_bot/agents/copilot_tools.py` | Tool set |
| `anchorflowSwingEvaluator.ts` | `apps/bot/src/sharpedge_bot/agents/setup_evaluator.py` | LLM gate |
| `deterministic/marketStateBuilder.ts` | `packages/analytics/src/sharpedge_analytics/regime.py` | Regime classifier |
| `discord-server/src/bot/discordBot.ts` (alert patterns) | Enhance existing bot | Alert formatting patterns |
| `AnchorFlowTypes.ts` alpha formula | `packages/models/src/sharpedge_models/alpha.py` | Composite scoring |
| `quantFactory/backtest.ts` | `packages/models/src/sharpedge_models/walk_forward.py` | Walk-forward engine |

---

## Success Metrics

| Metric | Current | Target (Post-Upgrade) |
|--------|---------|-----------------------|
| Alert quality (alpha-ranked) | None | Top 20% of alerts → PREMIUM/HIGH badge |
| Monte Carlo ruin probability | Not tracked | <5% ruin over 500 bets at recommended sizing |
| Walk-forward out-of-sample ROI | Not validated | Positive ROI in all walk-forward windows |
| Model calibration | Basic Brier score | CALIBRATED badge within 3 months |
| PM edge detection | Arbitrage only | 5+ genuine probability edges/week |
| Front-end | Discord only | Web + mobile (iOS + Android) |
| Copilot sessions | None | Users ask 10+ copilot questions/day |

---

## Notes on Separation from FinnAI

- SharpEdge uses **Python** (uv workspace), FinnAI uses **TypeScript** — ports require full rewrites, not copy-paste
- SharpEdge uses **LangChain** for agents; FinnAI uses OpenAI Agents SDK + LangChain (quantFactory). Use LangGraph (Python) for the StateGraph
- SharpEdge's existing `ev_calculator.py` is already excellent — extend it, don't replace it
- FinnAI's quant math (Monte Carlo, EV formulas, Kelly) is language-agnostic — port the formulas, not the code
- SharpEdge should remain an independent repository after this planning phase

---

*Document created: 2026-03-13*
*Based on analysis of FinnAI codebase (.planning/codebase/) and SharpEdge current implementation*
