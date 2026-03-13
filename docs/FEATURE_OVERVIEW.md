# SharpEdge Feature Overview

## What is SharpEdge?

SharpEdge is a Discord-based sports betting intelligence platform that combines real-time odds analysis, AI-powered research, and professional-grade analytics to help bettors find value and make informed decisions.

---

## Core Feature Categories

### 1. Real-Time Odds Intelligence

| Feature | Description | Tier |
|---------|-------------|------|
| **Live Odds Comparison** | Compare odds across 14+ sportsbooks in real-time | Free |
| **Best Line Finder** | Instantly identify which book has the best odds | Free |
| **No-Vig Fair Odds** | See true probabilities with bookmaker margin removed | Pro |
| **Consensus Line** | Market consensus weighted by book sharpness | Pro |
| **Opening Line Tracking** | Track movement from open to current | Pro |

**Sportsbooks Integrated:**
DraftKings, FanDuel, BetMGM, Caesars, PointsBet, BetRivers, Barstool, WynnBET, Unibet, FOX Bet, BetUS, Bovada, Pinnacle, Betfair

---

### 2. Value Detection

| Feature | Description | Tier |
|---------|-------------|------|
| **+EV Scanner** | Automated scanning for positive expected value bets | Pro |
| **Value Alerts** | Real-time notifications when value appears | Pro |
| **Edge Calculator** | Calculate your edge vs market odds | Pro |
| **Kelly Criterion** | Optimal bet sizing based on edge and bankroll | Free |
| **CLV Tracking** | Track your closing line value over time | Sharp |

**How Value Detection Works:**
1. Background job scans odds every 5 minutes
2. Compares market odds to model projections
3. Calculates expected value for each opportunity
4. Filters for EV > threshold (configurable)
5. Ranks by confidence and alerts subscribers

---

### 3. Sharp Money Indicators

| Feature | Description | Tier |
|---------|-------------|------|
| **Line Movement Analysis** | Classify movements as steam, RLM, buyback | Pro |
| **Steam Move Detection** | Identify sharp, sudden moves across books | Pro |
| **Reverse Line Movement** | Line moves opposite to public betting | Pro |
| **Public vs Sharp** | Ticket % vs money % divergence | Pro |
| **Sharp Play Finder** | Identify where professional money is going | Sharp |

**Movement Types Detected:**
- **Steam Move**: Sharp action causing 1+ point move in <30 minutes
- **RLM (Reverse Line Movement)**: Line moves against public consensus
- **Buyback**: Line correction after initial sharp move
- **Gradual**: Normal market adjustment

---

### 4. Arbitrage & Middles

| Feature | Description | Tier |
|---------|-------------|------|
| **Arbitrage Scanner** | Find guaranteed profit across books | Sharp |
| **Fee-Adjusted Arb** | Net profit after considering book fees | Sharp |
| **Middle Finder** | Find opportunities to win both sides | Sharp |
| **Cross-Platform Arb** | Sportsbook vs prediction market arbs | Sharp |

**Arbitrage Example:**
```
FanDuel: Chiefs +150
DraftKings: Raiders -140
Combined Implied: 98.2%
Guaranteed Profit: 1.8%
```

---

### 5. AI Research Assistant

| Feature | Description | Tier |
|---------|-------------|------|
| **Natural Language Research** | Ask any betting question in plain English | Pro |
| **Game Breakdown** | Comprehensive matchup analysis | Pro |
| **Historical Trends** | Query historical betting trends | Pro |
| **Player Projections** | AI-generated player stat projections | Sharp |
| **Personalized Insights** | Analysis based on your betting history | Sharp |

**Example Queries:**
- "What's the sharp action on the Chiefs game?"
- "How do road underdogs perform in primetime?"
- "What's the weather impact on tonight's Bears game?"
- "Show me contrarian opportunities this weekend"

**AI Agent Tools:**
The research agent has access to 8 specialized tools:
1. `get_matchup_breakdown` - Team stats, injuries, trends
2. `get_player_projections` - Stat projections by player
3. `get_historical_trends` - Historical situation analysis
4. `scan_current_value` - Find current +EV plays
5. `get_sharp_action_summary` - Sharp money overview
6. `analyze_line_value` - Evaluate specific line value
7. `get_key_numbers_analysis` - Key number crossing impact
8. `calculate_clv_projection` - Project closing line value

---

### 6. Visual Analytics

| Feature | Description | Tier |
|---------|-------------|------|
| **Line Movement Charts** | Visual spread/total movement over time | Pro |
| **Value Distribution** | Chart of current value plays by EV | Pro |
| **Bankroll Performance** | Your profit/loss over time | Pro |
| **CLV Chart** | Track your CLV performance | Sharp |
| **Odds Comparison** | Side-by-side book comparison | Pro |
| **Public Betting Chart** | Ticket vs money visualization | Pro |

**Chart Commands:**
- `/chart-movement` - Line movement for any game
- `/chart-value` - Current value plays visualization
- `/chart-bankroll` - Your bankroll over time
- `/chart-clv` - Your closing line value history
- `/chart-public` - Public betting breakdown

---

### 7. Bet Tracking & Performance

| Feature | Description | Tier |
|---------|-------------|------|
| **Bet Logger** | Log bets with full details | Pro |
| **Result Tracking** | Record wins, losses, pushes | Pro |
| **Performance Stats** | Win rate, ROI, units won/lost | Pro |
| **Sport Breakdown** | Performance by sport | Pro |
| **Bet Type Breakdown** | Performance by spread/total/ML | Pro |
| **CLV Analysis** | Track your edge vs closing line | Sharp |
| **Weekly Review** | AI-powered betting review | Sharp |

**Stats Tracked:**
- Total bets, wins, losses, pushes
- Win rate and ROI percentage
- Units won/lost
- Average odds
- CLV (positive = long-term edge)
- Sport-by-sport performance
- Bet type performance

---

### 8. Prediction Market Integration

| Feature | Description | Tier |
|---------|-------------|------|
| **PM Market Browser** | Browse Kalshi/Polymarket markets | Sharp |
| **Cross-Platform Arb** | Find arbs between PM platforms | Sharp |
| **PM Probability Gaps** | Detect pricing inefficiencies | Sharp |
| **Unified Scanner** | Scan sportsbooks + PMs together | Sharp |
| **Sizing Instructions** | Precise position sizing for PM arbs | Sharp |

**Platforms Integrated:**
- **Kalshi**: CFTC-regulated, US-legal prediction market
- **Polymarket**: Crypto-based prediction market

**How PM Arbitrage Works:**
```
Kalshi: "Chiefs win" at $0.55 (55% implied)
Polymarket: "Chiefs lose" at $0.43 (43% implied)
Total implied: 98% → 2% arbitrage opportunity
```

---

### 9. Situational Analysis

| Feature | Description | Tier |
|---------|-------------|------|
| **Key Number Analysis** | NFL/NBA key number crossing | Pro |
| **Weather Impact** | Game weather and scoring impact | Pro |
| **Rest/Travel Edge** | Schedule advantage calculations | Pro |
| **Trap Game Detection** | Identify trap situations | Pro |
| **Revenge Spot Detection** | Teams seeking revenge | Pro |

**Key Numbers (NFL):**
- 3: ~15% of games decided by exactly 3
- 7: ~10% of games decided by exactly 7
- 6, 4, 10: Secondary key numbers

**Weather Factors:**
- Wind speed (impacts passing/kicking)
- Temperature (cold = lower scoring)
- Precipitation (rain/snow = lower totals)
- Dome detection for irrelevant weather

---

### 10. Alerts & Notifications

| Feature | Description | Tier |
|---------|-------------|------|
| **Value Alerts** | Notified when +EV plays appear | Pro |
| **Line Movement Alerts** | Steam moves and significant changes | Pro |
| **Arbitrage Alerts** | Arb opportunities detected | Sharp |
| **PM Arb Alerts** | Cross-platform PM arbs | Sharp |

**Alert Frequency:**
- Value/Movement: Checked every 5 minutes
- Sportsbook Arbs: Checked every 5 minutes
- PM Arbs: Checked every 2 minutes (short-lived)

---

## Feature Matrix by Tier

| Feature | Free | Pro ($49/mo) | Sharp ($99/mo) |
|---------|:----:|:------------:|:--------------:|
| Live odds comparison | Yes | Yes | Yes |
| Best line finder | Yes | Yes | Yes |
| Kelly calculator | Yes | Yes | Yes |
| Bankroll tracking | Yes | Yes | Yes |
| **Bet logging** | - | Yes | Yes |
| **Performance stats** | - | Yes | Yes |
| **No-vig odds** | - | Yes | Yes |
| **Value scanner** | - | Yes | Yes |
| **Line movement** | - | Yes | Yes |
| **AI research** | - | Yes | Yes |
| **Visual charts** | - | Yes | Yes |
| **Weather/situational** | - | Yes | Yes |
| **Arbitrage scanner** | - | - | Yes |
| **PM integration** | - | - | Yes |
| **CLV analysis** | - | - | Yes |
| **Weekly AI review** | - | - | Yes |

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
├─────────────────────────────────────────────────────────────────┤
│  The Odds API    ESPN API    WeatherAPI    Kalshi    Polymarket │
└──────────┬─────────────────────────────────────────────────┬────┘
           │                                                 │
           ▼                                                 ▼
┌──────────────────────┐                    ┌──────────────────────┐
│   BACKGROUND JOBS    │                    │   PREDICTION MARKETS │
├──────────────────────┤                    ├──────────────────────┤
│ • Opening lines (30m)│                    │ • PM scanner (2m)    │
│ • Odds monitor (5m)  │                    │ • Cross-platform arb │
│ • Consensus calc (5m)│                    │ • Probability gaps   │
│ • Value scanner (5m) │                    └──────────┬───────────┘
│ • Arb scanner (5m)   │                               │
│ • Alerts (5m)        │                               │
└──────────┬───────────┘                               │
           │                                           │
           ▼                                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SUPABASE DATABASE                           │
├─────────────────────────────────────────────────────────────────┤
│  users, bets, odds_history, opening_lines, consensus_lines      │
│  value_plays, line_movements, arbitrage_opportunities           │
│  public_betting, pm_canonical_events, pm_arbitrage_opportunities│
└──────────┬──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ANALYTICS ENGINE                             │
├─────────────────────────────────────────────────────────────────┤
│  no_vig, consensus, arbitrage, middles, key_numbers, movement   │
│  value_scanner, weather, rest_travel, public_betting            │
│  prediction_markets, visualizations, unified_markets            │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DISCORD BOT                                 │
├─────────────────────────────────────────────────────────────────┤
│  Slash Commands → Embeds → Charts → Alerts                      │
│  AI Research Agent (GPT-4o) ← 8 specialized tools               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Command Reference

### Free Tier
| Command | Description |
|---------|-------------|
| `/lines <team1> <team2>` | Compare odds across all books |
| `/bankroll set <amount>` | Set your bankroll |
| `/kelly <odds> <win_pct>` | Calculate Kelly bet size |
| `/subscribe` | View subscription options |
| `/tier` | Check your current tier |

### Pro Tier
| Command | Description |
|---------|-------------|
| `/bet <sport> <pick> <odds> <units>` | Log a bet |
| `/result <bet_id> <win\|loss\|push>` | Record bet result |
| `/pending` | View pending bets |
| `/history` | View bet history |
| `/stats` | View performance stats |
| `/analyze <team1> <team2>` | AI game analysis |
| `/value [sport]` | Find +EV plays |
| `/sharp [sport]` | Sharp money indicators |
| `/consensus <team1> <team2>` | Market consensus line |
| `/steam` | Recent steam moves |
| `/fade` | Contrarian opportunities |
| `/research <query>` | AI research assistant |
| `/breakdown <game> <sport>` | Comprehensive breakdown |
| `/trends <type> <sport>` | Historical trends |
| `/chart-movement <game>` | Line movement chart |
| `/chart-value [sport]` | Value plays chart |
| `/chart-bankroll` | Bankroll performance chart |
| `/chart-public <game>` | Public betting chart |

### Sharp Tier
| Command | Description |
|---------|-------------|
| `/arb [sport]` | Current arbitrage opportunities |
| `/review [period]` | AI betting review |
| `/review-week` | Weekly performance review |
| `/pm-arb` | Cross-platform PM arbitrage |
| `/pm-markets <query>` | Search prediction markets |
| `/pm-compare <market>` | Compare PM prices |
| `/chart-clv` | CLV tracking chart |
