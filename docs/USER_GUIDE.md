# SharpEdge User Guide

Welcome to SharpEdge! This guide will help you get the most out of your subscription.

---

## Getting Started

### Joining the Server

1. Purchase a subscription through Whop
2. You'll automatically receive the appropriate Discord role
3. Access unlocked channels based on your tier

### Your First Commands

Try these commands to get started:

```
/bankroll set 5000    → Set your bankroll to $5,000
/tier                 → Check your subscription tier
/lines Chiefs Raiders → Compare odds across all sportsbooks
```

---

## Understanding Your Tier

### Free Tier

Access to basic tools:
- `/lines` - Compare odds across books
- `/bankroll` - Set your bankroll
- `/kelly` - Calculate optimal bet sizes
- `/subscribe` - Upgrade your tier

### Pro Tier ($19.99/month)

Everything in Free, plus:
- Bet tracking and performance stats
- +EV value scanner
- Sharp money indicators
- AI research assistant
- Line movement analysis
- Visual charts
- Real-time alerts
- **Prediction markets** (Kalshi / Polymarket): browse, compare, and PM arbitrage (`/pm-markets`, `/pm-compare`, `/pm-arb`)
- **Web / mobile:** portfolio with performance splits, ROI / P/L curves, active bets; value plays; **line shop** and **props explorer** (Odds API); game analysis with injuries

### Sharp Tier ($49.99/month)

Everything in Pro, plus:
- **Sportsbook** arbitrage scanner (guaranteed profit across books)
- Closing Line Value (CLV) tracking
- Weekly AI betting review
- Priority support

---

## Core Features

### Comparing Odds

The `/lines` command shows odds across all sportsbooks:

```
/lines Chiefs Raiders
```

**Output includes:**
- Spread from each book
- Total (over/under) from each book
- Moneyline from each book
- Best line highlighted
- (Pro) No-vig fair odds
- (Pro) Consensus line

**Pro tip:** Always bet at the book with the best odds. Over time, small differences compound significantly.

---

### Bankroll Management

#### Setting Your Bankroll

```
/bankroll set 5000
```

This establishes your starting bankroll for unit calculations.

#### Kelly Criterion Calculator

The Kelly formula tells you how much to bet based on your edge:

```
/kelly -110 55
```

Parameters:
- `-110` = The odds you're betting
- `55` = Your estimated win probability (%)

**Output:**
- Full Kelly percentage
- Half Kelly (recommended for most bettors)
- Quarter Kelly (conservative)
- Suggested stake based on your bankroll

**Important:** Most professionals bet Half Kelly or less. Full Kelly is mathematically optimal but volatile.

---

### Logging Bets (Pro+)

Track your bets to understand your performance:

```
/bet NFL "Chiefs -3" -110 2
```

Parameters:
- `NFL` = Sport
- `"Chiefs -3"` = Your pick (use quotes for multi-word)
- `-110` = Odds
- `2` = Units

Optional parameters:
- `sportsbook:` Which book you used
- `notes:` Any notes about the bet

#### Recording Results

When your bet settles:

```
/result abc123 win
```

Parameters:
- `abc123` = Bet ID (shown when you logged it)
- `win` / `loss` / `push` = Result

**Pro tip:** Log bets immediately when you place them. This captures the odds you actually got.

---

### Viewing Your Stats (Pro+)

```
/stats
```

Shows your:
- Win/loss record
- Win rate percentage
- ROI (return on investment)
- Units won/lost
- Average odds
- (Sharp) CLV analysis

#### Filtering Stats

```
/stats period:month sport:NFL
```

Filter by:
- `period`: today, week, month, season, all
- `sport`: NFL, NBA, MLB, NHL

---

### Finding Value (Pro+)

The value scanner finds bets where you have an edge:

```
/value
```

Shows:
- Game and pick
- Current odds and book
- Expected Value (EV%)
- Edge over fair odds
- Confidence level (HIGH/MEDIUM/LOW)

**How to interpret:**
- **EV%** = Your expected profit per dollar bet
- **Edge** = How much better than fair odds
- **Confidence** = Based on model certainty and line stability

**Example:**
```
Chiefs -3 @ DraftKings (-105)
EV: +3.2%  |  Edge: 2.8%  |  Confidence: HIGH
→ Kelly: 2.1 units
```

This means betting $100 on this line should return $3.20 on average.

---

### Sharp Money Indicators (Pro+)

See where professional bettors are putting their money:

```
/sharp
```

Shows:
- Public ticket percentage
- Money percentage
- Sharp side (when there's divergence)
- Recent steam moves
- Reverse line movement

**Key concept:** When 70% of tickets are on Team A but only 50% of money, sharps are on Team B.

```
/steam
```

Shows recent sharp, sudden line movements across multiple books.

```
/fade
```

Shows contrarian opportunities where public is heavily one-sided (potential fade candidates).

---

### AI Research Assistant (Pro+)

Ask any betting question in plain English:

```
/research What's the sharp action on the Chiefs game tonight?
```

The AI will:
1. Gather relevant data
2. Analyze line movements
3. Check public betting percentages
4. Provide a comprehensive answer

**Example queries:**
- "How do road underdogs perform in primetime?"
- "What's the weather impact on the Bears game?"
- "Should I take the over in this Cowboys game?"
- "What's my best bet tonight based on current value?"

#### Game Breakdown

Get comprehensive analysis for any matchup:

```
/breakdown "Chiefs Raiders" NFL
```

Includes:
- Team stats and trends
- Injury report
- Weather (if outdoor)
- Rest/travel analysis
- Sharp money indicators
- Historical matchup data
- AI recommendation

---

### Visual Charts (Pro+)

#### Line Movement Chart

```
/chart-movement "Chiefs Raiders"
```

Visual graph showing:
- Spread movement over last 24-48 hours
- Opening line marker
- Consensus line marker
- Key numbers highlighted (3, 7 for NFL)

#### Value Play Distribution

```
/chart-value
```

Bar chart of current value plays by EV percentage, color-coded by confidence.

#### Your Bankroll Performance

```
/chart-bankroll
```

Line graph showing:
- Your bankroll over time
- Win/loss markers
- Trend line

#### CLV Tracking (Sharp)

```
/chart-clv
```

Shows your closing line value over time:
- Individual bet CLV
- Rolling average
- Cumulative CLV

**Why CLV matters:** Positive CLV = you're consistently beating the closing line = long-term profitability.

---

### Arbitrage Scanner (Sharp)

Find guaranteed profit opportunities:

```
/arb
```

Shows:
- The opportunity (e.g., "Chiefs vs Raiders")
- Book A odds and stake percentage
- Book B odds and stake percentage
- Guaranteed profit percentage

**Example:**
```
FanDuel: Chiefs +155 (stake 41.2%)
DraftKings: Raiders -145 (stake 58.8%)
Guaranteed Profit: 1.8%
```

With $1,000 total:
- Bet $412 on Chiefs at FanDuel
- Bet $588 on Raiders at DraftKings
- Profit $18 guaranteed regardless of outcome

**Important notes:**
- Arbs are time-sensitive and may disappear quickly
- Some books limit or ban arb bettors
- Factor in withdrawal fees and limits

---

### Prediction Markets (Pro)

Browse and analyze prediction markets (same tier as web **Markets** and mobile **Markets**):

```
/pm-markets "Super Bowl"
```

Shows Kalshi and Polymarket markets for your search.

#### Cross-Platform Arbitrage

```
/pm-arb
```

Finds arbitrage between Kalshi and Polymarket when the same event is priced differently.

**Example:**
```
Event: "Chiefs win Super Bowl"
Kalshi: Yes @ $0.42 (42%)
Polymarket: No @ $0.55 (55%)
Combined: 97% → 3% arbitrage
```

---

## Best Practices

### 1. Always Take the Best Line

Even a 5-10 cent difference matters over time:
- -105 vs -110 on a $100 bet = $4.50 more profit
- Over 500 bets/year = $2,250 extra

Use `/lines` before every bet.

### 2. Track Everything

Log every bet with `/bet`. This enables:
- Accurate performance analysis
- CLV tracking
- AI-powered reviews
- Identifying your strengths/weaknesses

### 3. Focus on CLV, Not Results

Short-term results are noisy. CLV is the true measure of skill:
- Positive CLV = you're finding value
- Negative CLV = you're getting bad numbers

Even with positive CLV, you can have losing weeks. Trust the process.

### 4. Size Bets Appropriately

Use `/kelly` but bet Half Kelly or less:
- Full Kelly is mathematically optimal but very volatile
- Half Kelly reduces variance by 50%
- Quarter Kelly for conservative approach

Never bet more than 5% of bankroll on a single bet.

### 5. Follow Sharp Money

When public and money diverge, follow the money:
- 70% public tickets on Team A
- 55% money on Team A
- Sharp money is on Team B

Use `/sharp` to identify these opportunities.

### 6. Act on Alerts Quickly

Value and arbitrage opportunities are time-sensitive:
- Steam moves can close in minutes
- Arb windows are often seconds to minutes
- Set up notifications in Discord

### 7. Review Weekly

Use `/review-week` (Sharp tier) to:
- See what worked and didn't
- Identify patterns in your betting
- Get AI recommendations for improvement

---

## Common Questions

### What sports are supported?

Currently: NFL, NBA, MLB, NHL

Coming soon: NCAA Football, NCAA Basketball, Soccer

### How accurate is the AI analysis?

The AI uses real data from our analytics engine, not opinions. However:
- Past performance doesn't guarantee future results
- Weather and injury data can change
- Always use as one input, not the only input

### Why don't I see any arbitrage opportunities?

True arbitrage is rare and short-lived:
- Most arb windows last seconds to minutes
- We scan every 5 minutes for sportsbooks
- We scan every 2 minutes for prediction markets

When arbs appear, act fast.

### Can I get banned for arbitrage betting?

Some sportsbooks limit or ban profitable bettors:
- Spread arb bets across books
- Mix in recreational bets
- Don't always max bet
- Some books are more tolerant than others

### What's the difference between EV and Edge?

- **Edge** = How much better than fair odds (probability difference)
- **EV** = Expected profit per dollar (accounts for odds)

Both are important. High edge at bad odds can have lower EV than moderate edge at good odds.

### How is CLV calculated?

CLV (Closing Line Value) compares:
- The odds you bet at
- The odds at game start (closing line)

If you bet Chiefs -3 at -105, and they closed at -3.5 at -110, you had positive CLV.

---

## Command Reference

### Free Tier
| Command | Description |
|---------|-------------|
| `/lines <team1> <team2>` | Compare odds |
| `/bankroll set <amount>` | Set bankroll |
| `/kelly <odds> <win_pct>` | Kelly calculator |
| `/subscribe` | View plans |
| `/tier` | Check your tier |

### Pro Tier
| Command | Description |
|---------|-------------|
| `/bet <sport> <pick> <odds> <units>` | Log bet |
| `/result <id> <win\|loss\|push>` | Record result |
| `/pending` | View pending bets |
| `/history` | Bet history |
| `/stats` | Performance stats |
| `/analyze <team1> <team2>` | AI analysis |
| `/value` | Find +EV plays |
| `/sharp` | Sharp indicators |
| `/consensus <team1> <team2>` | Market consensus |
| `/steam` | Steam moves |
| `/fade` | Contrarian plays |
| `/research <query>` | AI research |
| `/breakdown <game> <sport>` | Full breakdown |
| `/trends <type> <sport>` | Historical trends |
| `/chart-movement <game>` | Movement chart |
| `/chart-value` | Value chart |
| `/chart-bankroll` | Bankroll chart |
| `/chart-public <game>` | Public betting |
| `/pm-arb` | PM cross-platform arbitrage |
| `/pm-markets <query>` | Browse PMs (Kalshi / Polymarket) |
| `/pm-compare <market>` | Compare PM prices |

### Sharp Tier
| Command | Description |
|---------|-------------|
| `/arb` | Arbitrage scanner |
| `/review` | AI bet review |
| `/review-week` | Weekly review |
| `/chart-clv` | CLV chart |

---

## Support

### Getting Help

- Type `/help` for command list
- Ask in #general for community help
- Sharp tier: Use #1on1-support channel

### Reporting Issues

If something isn't working:
1. Check your tier has access to the command
2. Try the command again (occasional API hiccups)
3. Report in #support with:
   - Command you tried
   - Error message (if any)
   - Screenshot (helpful)

---

*Good luck, and bet sharp!*
