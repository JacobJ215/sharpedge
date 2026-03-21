# SharpEdge Enhancement Plan

## Overview

This document outlines enhancements to transform SharpEdge from an MVP into a premium-worthy sports betting intelligence platform (list pricing is **$19.99 / $49.99** Pro/Sharp — see `docs/PLATFORM_FEATURES.md`).

---

## Phase 1: Core Value Enhancements

### 1.1 No-Vig (Fair) Line Calculation

**What it does:** Removes the bookmaker's margin to show the "true" market line.

**Why it matters:**
- The vig inflates both sides, hiding the true probability
- No-vig lines are the benchmark for identifying value
- Pinnacle's no-vig lines are considered the sharpest market

**Implementation:**
```python
# For a -110/-110 spread, true probability is 50/50
# But implied prob of -110 is 52.38%, totaling 104.76% (4.76% vig)
# Remove vig by normalizing: 52.38 / 104.76 = 50%

def calculate_no_vig_odds(odds_a: int, odds_b: int) -> tuple[float, float]:
    """Return true probabilities for both sides."""
    prob_a = american_to_implied_prob(odds_a)
    prob_b = american_to_implied_prob(odds_b)
    total = prob_a + prob_b  # This is > 100% due to vig

    fair_prob_a = prob_a / total
    fair_prob_b = prob_b / total
    return fair_prob_a, fair_prob_b
```

**User Value:**
- See the "true" line across the market
- Instantly identify which side has value
- Compare your model's projection to fair market odds

---

### 1.2 Opening Line Tracking

**What it does:** Stores the first odds snapshot when a game appears, tracks movement over time.

**Why it matters:**
- Opening lines reflect initial sharp money
- Closing Line Value (CLV) is the #1 predictor of long-term profit
- "Beat the close" = you have edge

**Implementation:**
- Background job captures opening lines when games first appear
- Store in `odds_history` with `is_opening = true` flag
- Calculate movement: `current_line - opening_line`
- Display in embeds: "Opened: -3, Now: -4.5 (1.5 pts toward favorite)"

**User Value:**
- See how lines have moved since open
- Identify steam moves (sharp money)
- Track personal CLV more accurately

---

### 1.3 Real-Time +EV Scanner

**What it does:** Continuously scans all games for positive expected value bets based on model projections.

**Why it matters:**
- Automated edge detection across all markets
- Users don't have to manually check every game
- Alerts when value appears (time-sensitive)

**Implementation:**
```python
# Background job every 5 minutes:
1. Get model projections for all active games
2. Fetch current odds from all sportsbooks
3. Calculate EV for each side at each book
4. Filter for EV > threshold (configurable, default 2%)
5. Rank by EV and confidence
6. Queue alerts for Pro/Sharp users
```

**User Value:**
- Never miss a value bet
- Prioritized by expected edge
- Actionable alerts with specific book recommendations

---

### 1.4 Public Betting Data Integration

**What it does:** Shows where the public is betting (ticket %) vs where the money is going (handle %).

**Why it matters:**
- Public bettors lose long-term
- Sharp money often opposes public sentiment
- Ticket/money divergence = sharp action indicator

**Data Sources:**
- Action Network API (paid)
- Covers.com (scraping)
- Manual data entry fallback
- Aggregated consensus

**Implementation:**
```python
class PublicBettingData:
    game_id: str
    spread_ticket_home: float   # % of bets on home
    spread_money_home: float    # % of money on home
    total_ticket_over: float    # % of bets on over
    total_money_over: float     # % of money on over
    ml_ticket_home: float
    ml_money_home: float

    @property
    def sharp_side_spread(self) -> str:
        """Divergence indicates sharp money."""
        if self.spread_money_home > self.spread_ticket_home + 10:
            return "home"  # Money > tickets = sharps on home
        elif self.spread_money_away > self.spread_ticket_away + 10:
            return "away"
        return "neutral"
```

**User Value:**
- Fade the public with confidence
- Identify sharp vs square games
- Contrarian betting opportunities

---

## Phase 2: Advanced Analytics

### 2.1 Consensus Line Calculation

**What it does:** Aggregates lines across all books to find the market consensus.

**Implementation:**
- Median line across all sportsbooks
- Weighted by book sharpness (Pinnacle > recreational books)
- Show deviation from consensus: "FanDuel -3.5 (0.5 off market)"

**Metrics:**
```python
class ConsensusData:
    spread_consensus: float          # Median spread
    spread_range: tuple[float, float]  # Min/max across books
    total_consensus: float
    total_range: tuple[float, float]
    books_count: int
    sharpest_book: str              # Usually Pinnacle if available
```

---

### 2.2 Line Movement Analysis

**What it does:** Tracks and interprets line movements with context.

**Movement Types:**
- **Steam Move:** Sharp, sudden move across multiple books (1+ points in <30 min)
- **Reverse Line Movement (RLM):** Line moves opposite to public betting
- **Buyback:** Line moves back after initial sharp action
- **Dead Number:** Line sitting on key number (3, 7 in NFL)

**Implementation:**
```python
class LineMovement:
    game_id: str
    timestamp: datetime
    old_line: float
    new_line: float
    direction: str  # "toward_favorite" | "toward_underdog"
    magnitude: float
    movement_type: str  # "steam" | "rlm" | "buyback" | "gradual"
    interpretation: str
```

---

### 2.3 Key Number Analysis (NFL/NCAAF)

**What it does:** Identifies when lines cross key numbers and probability impact.

**Key Numbers:**
- **3:** ~15% of NFL games decided by exactly 3
- **7:** ~10% of NFL games decided by exactly 7
- **6, 4, 10:** Secondary key numbers

**User Value:**
- Know when -2.5 to -3 is a huge difference
- Teaser optimization through key numbers
- Alternate spread value identification

---

### 2.4 Weather Impact Scoring

**What it does:** Quantifies weather impact on totals and spreads.

**Factors:**
```python
class WeatherImpact:
    wind_speed: float      # mph
    temperature: float     # fahrenheit
    precipitation: float   # probability %

    @property
    def total_adjustment(self) -> float:
        adj = 0
        if self.wind_speed > 15:
            adj -= (self.wind_speed - 15) * 0.15  # -0.15 pts per mph over 15
        if self.temperature < 32:
            adj -= 1.5
        if self.precipitation > 50:
            adj -= 1.0
        return adj
```

**Integration:** WeatherAPI.com or OpenWeatherMap

---

### 2.5 Rest & Travel Analysis

**What it does:** Quantifies schedule-based advantages.

**Factors:**
```python
class ScheduleEdge:
    home_rest_days: int
    away_rest_days: int
    rest_advantage: int  # positive = home advantage

    away_travel_miles: int
    away_timezone_change: int

    home_games_last_7: int
    away_games_last_7: int

    is_back_to_back: bool
    is_3_in_4: bool
    is_4_in_5: bool

    @property
    def spread_adjustment(self) -> float:
        """Estimated point adjustment based on schedule."""
        adj = 0
        adj += self.rest_advantage * 0.5  # 0.5 pts per rest day advantage
        if self.away_timezone_change >= 2:
            adj += 1.0  # West to East travel penalty
        if self.is_back_to_back:
            adj += 1.5 if self.away_is_b2b else -1.5
        return adj
```

---

### 2.6 Historical Matchup Data

**What it does:** Provides H2H history and trends.

**Data Points:**
- Last 5 matchups: scores, spreads, ATS results
- Home/away splits in matchup
- Total trends in matchup
- Division/rivalry context

---

### 2.7 Situational Spot Analysis

**What it does:** Identifies historical profitable situations.

**Spots to Track:**
- Revenge games (lost to opponent last meeting)
- Letdown spots (after big win vs rival)
- Lookahead spots (before marquee matchup)
- Trap games (heavy favorite vs bad team before tough game)
- Divisional unders (familiarity breeds low-scoring games)
- Prime time adjustments
- Week 1 / early season uncertainty

---

### 2.8 Bankroll Simulation

**What it does:** Monte Carlo simulation of betting strategies.

**Simulations:**
- Kelly vs Half Kelly vs Flat betting
- Projected bankroll growth over N bets
- Risk of ruin calculations
- Optimal bet sizing for user's risk tolerance

```python
def simulate_bankroll(
    edge: float,           # Expected edge per bet (e.g., 0.02 = 2%)
    odds: int,             # Average odds
    bankroll: float,
    num_bets: int,
    strategy: str,         # "kelly" | "half_kelly" | "flat"
    simulations: int = 10000
) -> SimulationResult:
    """Monte Carlo bankroll simulation."""
```

---

### 2.9 Arbitrage Detection

**What it does:** Finds guaranteed profit opportunities across sportsbooks.

**How it works:**
```python
# If FanDuel has Team A +150 and DraftKings has Team B -140
# Check if you can bet both sides for guaranteed profit

def find_arbitrage(odds_a: int, odds_b: int) -> ArbitrageResult:
    implied_a = american_to_implied_prob(odds_a)
    implied_b = american_to_implied_prob(odds_b)

    if implied_a + implied_b < 1.0:  # Arb exists!
        # Calculate optimal stakes
        total_implied = implied_a + implied_b
        stake_a_pct = implied_a / total_implied
        stake_b_pct = implied_b / total_implied
        profit_pct = (1 / total_implied - 1) * 100
        return ArbitrageResult(exists=True, profit_pct=profit_pct, ...)
```

**User Value:**
- Risk-free profit opportunities
- Rare but valuable when found
- Requires accounts at multiple books

---

### 2.10 Middle Opportunity Detection

**What it does:** Finds chances to win both sides of a bet.

**Example:**
- Book A: Team -2.5
- Book B: Team +3.5
- Bet both → Win both if team wins by exactly 3

**Implementation:**
```python
def find_middles(spreads: list[BookmakerOdds]) -> list[MiddleOpportunity]:
    """Find spread middles across books."""
    opportunities = []
    for book_a, book_b in combinations(spreads, 2):
        if book_a.home_spread < book_b.away_spread:
            # Middle exists
            middle_range = (book_a.home_spread, book_b.away_spread)
            # Calculate probability of hitting middle
```

---

## Phase 3: Enhanced Agent Capabilities

### 3.1 New Agent Tools

```python
# Data retrieval tools
get_injury_report(team: str) -> InjuryReport
get_weather_forecast(game_id: str) -> WeatherForecast
get_public_betting(game_id: str) -> PublicBettingData
get_line_history(game_id: str) -> list[LineSnapshot]
get_opening_line(game_id: str) -> LineSnapshot
get_consensus_line(game_id: str) -> ConsensusData
get_historical_matchup(team_a: str, team_b: str) -> MatchupHistory
get_schedule_edge(game_id: str) -> ScheduleEdge

# Analysis tools
calculate_arbitrage(game_id: str) -> ArbitrageResult
find_value_plays(sport: str, min_ev: float) -> list[ValuePlay]
analyze_line_movement(game_id: str) -> LineMovementAnalysis
get_sharp_indicators(game_id: str) -> SharpIndicators

# User-specific tools
get_profitable_spots(user_id: str) -> list[ProfitableSpot]
simulate_bankroll(user_id: str, strategy: str) -> SimulationResult
```

### 3.2 Specialist Agents

**Research Agent:**
- Gathers all relevant data for a game
- Compiles injury reports, weather, public betting
- Prepares context for analysis

**Sharp Money Agent:**
- Specializes in line movement interpretation
- Identifies steam moves, RLM, sharp action
- Tracks where professional money is going

**Value Scanner Agent:**
- Continuously scans for +EV opportunities
- Ranks by confidence and expected edge
- Generates actionable recommendations

**Personal Coach Agent:**
- Analyzes user's betting history
- Identifies strengths and leaks
- Provides personalized improvement plans

---

## Phase 4: Data Sources to Integrate

### 4.1 Required APIs

| API | Purpose | Cost | Priority |
|-----|---------|------|----------|
| **The Odds API** | Live odds (have) | $20-200/mo | Have |
| **WeatherAPI.com** | Game weather | Free tier | P1 |
| **ESPN API** | Team stats, schedules | Free | P1 |
| **Sportsdata.io** | Injuries, advanced stats | $50+/mo | P2 |
| **Action Network** | Public betting % | Enterprise | P2 |

### 4.2 Data Collection Jobs

| Job | Frequency | Purpose |
|-----|-----------|---------|
| `capture_opening_lines` | Every 30 min | Store first line for new games |
| `monitor_odds` | Every 5 min | Track movements (have) |
| `fetch_weather` | Every hour | Update weather forecasts |
| `fetch_injuries` | Every 6 hours | Update injury reports |
| `calculate_consensus` | Every 5 min | Aggregate market consensus |
| `scan_value_plays` | Every 5 min | Find +EV opportunities |
| `detect_arbitrage` | Every 5 min | Find arb opportunities |
| `generate_alerts` | Every 5 min | Queue user notifications |

---

## Phase 5: New Database Tables

### 5.1 Schema Additions

```sql
-- Opening lines tracking
CREATE TABLE opening_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    sport TEXT NOT NULL,
    sportsbook TEXT NOT NULL,
    bet_type TEXT NOT NULL,  -- spread, total, moneyline
    line DECIMAL,
    odds_home INTEGER,
    odds_away INTEGER,
    captured_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(game_id, sportsbook, bet_type)
);

-- Public betting percentages
CREATE TABLE public_betting (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    sport TEXT NOT NULL,
    spread_ticket_home DECIMAL,
    spread_money_home DECIMAL,
    total_ticket_over DECIMAL,
    total_money_over DECIMAL,
    ml_ticket_home DECIMAL,
    ml_money_home DECIMAL,
    source TEXT NOT NULL,
    captured_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_public_betting_game ON public_betting(game_id);

-- Weather data cache
CREATE TABLE game_weather (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL UNIQUE,
    venue TEXT,
    is_dome BOOLEAN DEFAULT FALSE,
    temperature DECIMAL,
    wind_speed DECIMAL,
    wind_direction TEXT,
    precipitation_chance DECIMAL,
    conditions TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Injury reports
CREATE TABLE injuries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team TEXT NOT NULL,
    sport TEXT NOT NULL,
    player_name TEXT NOT NULL,
    position TEXT,
    status TEXT NOT NULL,  -- Out, Doubtful, Questionable, Probable
    injury_type TEXT,
    impact_rating DECIMAL,  -- 0-10 scale of impact
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_injuries_team ON injuries(team, sport);

-- Value plays detected
CREATE TABLE value_plays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    sport TEXT NOT NULL,
    bet_type TEXT NOT NULL,
    side TEXT NOT NULL,
    sportsbook TEXT NOT NULL,
    model_prob DECIMAL NOT NULL,
    market_odds INTEGER NOT NULL,
    ev_percentage DECIMAL NOT NULL,
    edge_percentage DECIMAL NOT NULL,
    confidence TEXT NOT NULL,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_value_plays_active ON value_plays(created_at)
    WHERE expires_at IS NULL OR expires_at > NOW();

-- Arbitrage opportunities
CREATE TABLE arbitrage_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    sport TEXT NOT NULL,
    bet_type TEXT NOT NULL,
    book_a TEXT NOT NULL,
    odds_a INTEGER NOT NULL,
    book_b TEXT NOT NULL,
    odds_b INTEGER NOT NULL,
    profit_percentage DECIMAL NOT NULL,
    stake_a_percentage DECIMAL NOT NULL,
    stake_b_percentage DECIMAL NOT NULL,
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    expired_at TIMESTAMPTZ
);

-- Consensus lines
CREATE TABLE consensus_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    sport TEXT NOT NULL,
    spread_consensus DECIMAL,
    spread_min DECIMAL,
    spread_max DECIMAL,
    total_consensus DECIMAL,
    total_min DECIMAL,
    total_max DECIMAL,
    books_count INTEGER,
    calculated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_consensus_game ON consensus_lines(game_id);

-- Line movements log
CREATE TABLE line_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    sport TEXT NOT NULL,
    bet_type TEXT NOT NULL,
    sportsbook TEXT,
    old_line DECIMAL,
    new_line DECIMAL,
    old_odds INTEGER,
    new_odds INTEGER,
    direction TEXT,
    magnitude DECIMAL,
    movement_type TEXT,  -- steam, rlm, gradual, buyback
    detected_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_movements_game ON line_movements(game_id, detected_at);
```

---

## Implementation Order

### Batch 1: Foundation (This Session)
1. No-vig line calculation utilities
2. Opening line capture job
3. Consensus line calculation
4. Line movement detection enhancement
5. New database migrations

### Batch 2: Value Detection
6. Enhanced +EV scanner with alerts
7. Arbitrage detection
8. Middle finder
9. Key number analysis

### Batch 3: Data Integration
10. Weather API integration
11. Public betting data (manual entry first, API later)
12. Schedule/rest analysis

### Batch 4: Agent Enhancement
13. New agent tools
14. Enhanced prompts with new data
15. Multi-agent workflows

### Batch 5: Analytics Dashboard
16. Stats embeds with new metrics
17. Leaderboard system
18. Personalized edge analysis

---

## Success Metrics

**At $19.99/mo (Pro), users should:**
- Find 2-3 +EV plays daily
- See where sharp money is going
- Track CLV accurately
- Get value alerts before lines move

**At $49.99/mo (Sharp), users should:**
- Never miss a value opportunity
- Identify arbitrage when available
- Understand every line movement
- Have personalized edge analysis
- Access to all agent capabilities

---

## File Structure for New Code

```
packages/
├── analytics/                    # NEW PACKAGE
│   └── src/sharpedge_analytics/
│       ├── __init__.py
│       ├── no_vig.py            # Fair odds calculation
│       ├── consensus.py         # Market consensus
│       ├── arbitrage.py         # Arb detection
│       ├── middles.py           # Middle finder
│       ├── key_numbers.py       # NFL/NCAAB key numbers
│       ├── movement.py          # Line movement analysis
│       ├── weather.py           # Weather impact
│       ├── rest_travel.py       # Schedule advantages
│       └── value_scanner.py     # +EV scanning
├── data_feeds/                   # NEW PACKAGE
│   └── src/sharpedge_feeds/
│       ├── __init__.py
│       ├── weather_client.py    # Weather API
│       ├── espn_client.py       # ESPN stats
│       └── public_betting.py    # Public % data

apps/bot/src/sharpedge_bot/
├── jobs/
│   ├── opening_lines.py         # NEW
│   ├── consensus_calc.py        # NEW
│   ├── value_scanner.py         # NEW
│   ├── arbitrage_scanner.py     # NEW
│   └── weather_fetcher.py       # NEW
├── agents/
│   └── tools.py                 # ENHANCE with new tools
├── embeds/
│   ├── value_embeds.py          # NEW
│   ├── arbitrage_embeds.py      # NEW
│   └── analytics_embeds.py      # NEW
└── commands/
    ├── value.py                 # NEW - /value, /ev commands
    └── market.py                # NEW - /consensus, /sharp commands
```

---

## Implementation Status

### Batch 1: Foundation - COMPLETED

1. **Analytics Package** (`packages/analytics/`) - DONE
   - `no_vig.py` - Fair odds calculations
   - `consensus.py` - Market consensus
   - `arbitrage.py` - Arb detection (including fee-adjusted)
   - `middles.py` - Middle finder
   - `key_numbers.py` - NFL/NBA key numbers
   - `movement.py` - Line movement classification
   - `value_scanner.py` - +EV scanning
   - `weather.py` - Weather impact
   - `rest_travel.py` - Schedule advantages
   - `public_betting.py` - Sharp money analysis

2. **Database Migrations** - DONE
   - `002_analytics_tables.sql` with 12 new tables

3. **Data Feeds Package** (`packages/data_feeds/`) - DONE
   - `weather_client.py` - WeatherAPI.com
   - `espn_client.py` - ESPN API
   - `public_betting_client.py` - Public betting

4. **Background Jobs** - DONE
   - `opening_lines.py` - Capture opening lines
   - `consensus_calc.py` - Calculate consensus
   - `value_scanner_job.py` - Scan for +EV
   - `arbitrage_scanner.py` - Detect arbs

5. **Database Queries** - DONE
   - opening_lines, consensus, value_plays
   - public_betting, line_movements, arbitrage

6. **Agent Tools** - DONE
   - 15+ new tools for analytics access

7. **Discord Commands** - DONE
   - `/value`, `/arb`, `/sharp` (value.py)
   - `/consensus`, `/steam`, `/fade` (market.py)
   - Enhanced `/lines` with analytics for Pro/Sharp

### Batch 2: Prediction Markets - COMPLETED

1. **Prediction Market Analytics** (`packages/analytics/`) - DONE
   - `prediction_markets.py` - PM arbitrage detection
   - `unified_markets.py` - Cross-platform analytics (sportsbook + PM)
   - Fee-adjusted arbitrage calculations
   - Cross-platform probability gap detection

2. **PM Data Feeds** (`packages/data_feeds/`) - DONE
   - `kalshi_client.py` - Kalshi API with RSA signing
   - `polymarket_client.py` - Polymarket Gamma/CLOB API

3. **PM Database** - DONE
   - `003_prediction_markets.sql` - PM tables

4. **PM Background Jobs** - DONE
   - `prediction_market_scanner.py` - Scans every 2 minutes

5. **PM Discord Commands** - DONE
   - `/pm-arb` - Cross-platform PM arbitrage
   - `/pm-markets` - Browse prediction markets
   - `/pm-compare` - Compare prices across platforms

### Batch 3: AI Research & Visualizations - COMPLETED

1. **Advanced Research Agent** (`apps/bot/agents/`) - DONE
   - `research_agent.py` - GPT-5-mini powered (upgraded from GPT-4o)
   - 8 specialized research tools:
     - Matchup breakdown
     - Player projections
     - Historical trends
     - Value scanning
     - Sharp action summary
     - Line value analysis
     - Key numbers analysis
     - CLV projection

2. **Visual Analytics** (`packages/analytics/`) - DONE
   - `visualizations.py` - Discord-optimized charts
   - 7 chart types:
     - Line movement chart
     - EV distribution chart
     - Bankroll performance chart
     - CLV tracking chart
     - Odds comparison chart
     - Arbitrage visualization
     - Public betting chart

3. **Research Discord Commands** - DONE
   - `/research` - Natural language research queries
   - `/breakdown` - Comprehensive game breakdown
   - `/trends` - Historical betting trends
   - `/chart-movement` - Line movement visualization
   - `/chart-value` - Value play distribution
   - `/chart-bankroll` - Personal bankroll chart
   - `/chart-clv` - CLV tracking chart
   - `/chart-public` - Public betting breakdown

4. **Supporting Infrastructure** - DONE
   - `chart_sender.py` - Discord chart utilities
   - Additional database queries for charts

### Batch 4: Payment Integration - COMPLETED

1. **Whop Integration** (replacing Stripe) - DONE
   - Updated `config.py` with Whop settings
   - New `routes/whop.py` webhook handler
   - Updated `subscription_service.py` for Whop
   - Updated `/subscribe` command with Whop checkout
   - Updated `/manage` command for Whop portal
   - Auto role management via webhooks

2. **Documentation Suite** - DONE
   - `docs/FEATURE_OVERVIEW.md` - Complete feature breakdown
   - `docs/PITCH_DECK.md` - Value proposition & market positioning
   - `docs/TECHNICAL_ARCHITECTURE.md` - Developer reference
   - `docs/USER_GUIDE.md` - End user documentation
   - Updated `NEXT_STEPS.md` with all new API keys

### Batch 5: Statistical Foundation & GPT-5 Migration - COMPLETED

1. **GPT-5 Model Migration** - DONE
   - Updated `research_agent.py` → GPT-5-mini
   - Updated `game_analyst.py` → GPT-5-mini
   - Updated `review_agent.py` → GPT-5-mini
   - Added configurable model settings in config.py
   - Cost-optimized while maintaining quality

2. **Backtesting Engine** - DONE (NEW)
   - `backtesting.py` - Infrastructure for statistical calibration:
     - Record predictions and outcomes
     - Calculate calibration curves (predicted vs actual)
     - Wilson score confidence intervals
     - Brier score and calibration error metrics
     - CalibrationStatus: UNCALIBRATED → PRELIMINARY → CALIBRATED → WELL_CALIBRATED
     - Historical backtest runner for model validation

3. **Statistically-Grounded EV Calculator** - DONE
   - `ev_calculator.py` - Proper uncertainty quantification:
     - Beta distribution for probability uncertainty
     - P(edge > 0) - Bayesian probability of positive edge
     - 95% credible intervals on model estimates
     - Integration with calibration data (when available)
     - Honest about uncalibrated state ("Theoretical - no backtest data yet")
     - Kelly criterion with uncertainty adjustment

4. **Statistical Confidence Levels** - DONE
   - Based on P(edge > 0), not arbitrary thresholds:
     - PREMIUM: P(edge > 0) >= 95% (2σ equivalent)
     - HIGH: P(edge > 0) >= 84% (1σ equivalent)
     - MEDIUM: P(edge > 0) >= 70%
     - LOW: P(edge > 0) >= 55%
     - SPECULATIVE: P(edge > 0) < 55%

5. **Spread Model with Proper Uncertainty** - DONE
   - `spreads.py` - Statistical prediction intervals:
     - 95% confidence intervals on spread predictions
     - Standard error calculation
     - Probability of crossing key numbers
     - Removed arbitrary confidence ratings
     - Calibration status tracking

6. **Stats Embeds with Statistical Context** - DONE
   - Win rate with Wilson score confidence intervals
   - ROI with bootstrap-approximated CI
   - Sample size indicators and warnings
   - Small sample warnings (n < 100)
   - Clear statistical notes for users

7. **Analysis Embeds with Calibration Status** - DONE
   - Shows P(edge > 0) probability
   - Displays 95% CI on model probability
   - Calibration indicator (✓ Backtested vs ⚠ Theoretical)
   - Explanation of confidence meaning

8. **Professional Visualizations** - DONE
   - Enhanced charts with gradient fills
   - Velocity subplots for line movement
   - Drawdown tracking for bankroll
   - 200 DPI output for clarity

### Remaining Work (Future Sessions)

1. **Data Enrichment**
   - SportsData.io integration (injuries, advanced stats)
   - Action Network integration (public betting %)
   - Historical matchup database

2. **Advanced Features**
   - Bankroll simulation (Monte Carlo)
   - Personal coach agent
   - Multi-agent workflows
   - Leaderboard system

3. **Platform Expansion**
   - Additional sports (Soccer, Golf, Tennis)
   - Mobile companion app
   - Web dashboard
