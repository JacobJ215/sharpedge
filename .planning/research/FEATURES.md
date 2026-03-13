# Feature Landscape

**Domain:** Institutional-grade sports betting + prediction market intelligence platform
**Researched:** 2026-03-13
**Confidence note:** WebSearch unavailable. Findings based on training knowledge (cutoff Aug 2025) of
the competitive landscape (OddsJam, Pikkit, Betburger, Action Network, Betstamp, PropSwap,
Sportsline Pro, Pinnacle data tools) plus deep reading of PROJECT.md and UPGRADE_ROADMAP.md.
Confidence on competitive positioning is MEDIUM. Confidence on feature categorization given the
explicit project context is HIGH.

---

## Table Stakes

Features that serious/professional bettors expect. Missing = platform feels amateur, users leave for
OddsJam or Action Network.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Expected Value (EV) calculator | Every pro tool has this. Without it, platform is a tip service, not analytics. | Low | Already built. Bayesian confidence (P(edge > 0)) is above average for this category. |
| No-vig fair odds / true probability | Devig is step 0 before any edge calculation. Bettors do this manually if tools don't. | Low | Already built. |
| Multi-book odds comparison | Pros shop lines. Single-book users are not the target. | Low-Med | Covered via The Odds API (30+ books). Display layer needed. |
| Line movement history + classification | Sharp vs public movement is the most widely used qualitative signal. | Med | Already built (steam, RLM, buyback). Display needed. |
| Arbitrage detection | Cross-book arb is table stakes for any "edge detection" pitch. | Med | Already built (cross-book + Kalshi x sportsbooks). |
| Kelly Criterion sizing | Bankroll management is non-negotiable for pros. Flat betting is a dealbreaker signal. | Low | Already built. |
| Bet tracking / portfolio logging | ROI, win rate, CLV tracking — pros won't use a tool that doesn't track their history. | Med | Schema exists. Portfolio API route needed. |
| Closing Line Value (CLV) tracking | CLV is the gold standard metric for serious bettors. Beating the close = long-run positive EV. | Med | Not yet built. High priority for credibility with pros. |
| Historical odds archive | Needed for backtesting, CLV, and any model validation claim. | Med | Already built (Supabase). |
| Subscription / access control | Monetization must exist or platform is a hobby. | Low | Already built (Whop). |
| Odds alert / notification system | Pros need to be notified of edges, not polling a dashboard. | Med | Discord alerts exist. Push notifications needed for mobile. |
| Injury / news integration | Pros account for injuries manually if the tool doesn't. Makes tool feel incomplete. | Med | ESPN feed exists. Injury impact scoring (not yet built). |

---

## Differentiators

Features that separate SharpEdge from every OddsJam/Action Network tier tool. These are the
competitive moat. The target user is a professional or semi-pro bettor willing to pay $50-200/month
for a genuine edge over the market.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Composite Alpha Score (EV x regime x survival x confidence) | Single ranking number that integrates multiple signals. No other retail tool does multi-factor alpha composition. | High | Core differentiator. Prevents gaming a single metric. UPGRADE_ROADMAP §1.1. |
| Monte Carlo bankroll ruin simulation | "3.2% ruin over 500 bets at this sizing" is intuitively powerful. No retail betting tool provides this. | High | Huge communication advantage. Transforms abstract Kelly fractions into survival probability. UPGRADE_ROADMAP §1.2. |
| Betting market regime detection (7-state HMM) | Classifying sharp/public/steam/thin/post-news states and weighting edges accordingly. No retail tool does market regime-aware sizing. | High | Requires public % + handle + line velocity data to function. UPGRADE_ROADMAP §1.4. |
| Walk-forward backtesting with quality badges | Out-of-sample validation prevents overfitting. "EXCELLENT" quality badge signals reliability. No retail tool does honest walk-forward. | High | Requires historical data pipeline already in place. UPGRADE_ROADMAP §1.3. |
| LLM setup evaluator (PASS/WARN/REJECT gate) | LLM checks for contradictory signals, trap lines, injury conflicts before alerting. Reduces false-positive alerts. | Med-High | Direct differentiator vs purely mechanical alert systems like OddsJam. UPGRADE_ROADMAP §2.3. |
| BettingCopilot (conversational analysis with portfolio awareness) | "Should I bet Lakers -3.5?" with full context: current exposure, bankroll, regime, model output. No retail tool has this. | High | Highest stickiness feature. Makes the platform feel like a quant analyst in your pocket. UPGRADE_ROADMAP §2.2. |
| Prediction market probabilistic edge detection (Kalshi/Polymarket) | Model probability vs market probability — beyond arbitrage. Retail tools only do PM arb, not edge scoring. | High | Novel in retail. PMs have genuine mispricings pros miss because they lack models. UPGRADE_ROADMAP §3.1. |
| Cross-market correlation engine | Prevents double-exposure to correlated bets (e.g., team win + player prop). Retail tools don't track portfolio correlation. | Med-High | Critical for Kelly sizing to be correct across a portfolio. UPGRADE_ROADMAP §3.2. |
| Key number zone detection with historical cover rates | NFL -3, -7, -10 with historical cover rates and half-point values. Better implementations than basic "near key number" flags on Action Network. | Med | Adds depth to line analysis. Requires historical spread outcome data. UPGRADE_ROADMAP §1.5. |
| Model calibration quality badges (CALIBRATED → WELL_CALIBRATED) | Transparent confidence about model reliability. No retail tool exposes calibration quality. | Med | Builds trust with sophisticated users. Distinguishes from black-box tip services. |
| Continuous model auto-weighting (Platt scaling) | Ensemble weights recalibrated monthly. Self-improving accuracy. | High | Prevents model decay. No retail tool does this transparently. UPGRADE_ROADMAP §5.3. |
| 5-model ensemble with team form / matchup / injury / sentiment / weather | Multi-factor model vs single-factor. Each specialist model focuses on one signal type. | High | Requires feature engineering for all 5. Injury impact model is hardest. UPGRADE_ROADMAP §5.1. |
| PM regime classification for prediction markets | Discovery/Consensus/News Catalyst/Pre-Resolution phases — sized differently. | Med | Novel. Applies betting market intuition to PM structure. UPGRADE_ROADMAP §3.3. |
| Mobile push notifications with alpha threshold filtering | Only notify at PREMIUM/HIGH alpha. No noise. Before Discord. | Med | Differentiated delivery. Discord bots are noisy; mobile alerts with threshold filtering are not. UPGRADE_ROADMAP §4.2. |
| CLV tracking (Closing Line Value) | Measures whether users are consistently beating the close. Strongest long-run profitability signal. | Med | Required for credibility with sharp bettors. Needs historical close integration. |

---

## Anti-Features

Things to deliberately NOT build. Either because they dilute focus, add regulatory risk, or attract
the wrong user.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Automated bet placement / direct sportsbook integration | Regulatory complexity (varies by state/country). Violates most sportsbook ToS. Attracts account-limited users who will churn when accounts get restricted. | Provide sizing recommendations. Let users place manually. Keep platform in intelligence layer only. |
| Social / community features (picks sharing, leaderboards, chat) | Attracts tip-followers, not analytics users. Leaderboard dynamics create false confidence. Dilutes positioning as institutional tool. Community moderation overhead. | Focus on individual portfolio analysis. V3+ if users demonstrate demand. |
| Real-time chat between users | Same as above. Platform value is analytical, not social. | Copilot satisfies the "conversational" need without community overhead. |
| "Picks" or "experts" marketplace | Pure tip service positioning. Opposite of quant credibility. No data validation of expert track records possible at launch. | Let the model outputs speak. Alpha score is the expert. |
| Browser extension for live odds | Chrome extension is a different distribution channel with different maintenance burden. | API + mobile push covers real-time delivery needs. |
| Sportsbook account health scoring / risk of limitation | Technically interesting but attracts users in a losing battle with books. Not aligned with analytical value. | Keep focus on finding edges, not evading detection. |
| General sports news / injury reports feed | Commoditized. ESPN, RotoBaller, etc. do this better. | Consume injury data as a signal input, don't surface raw news. |
| Public consensus / public picks aggregation | Also commoditized (Action Network does this). Low differentiation. | Use public % as a regime signal internally, don't surface as a standalone feature. |
| Paper trading / simulated bets without real data | Attracts non-serious users. Gamification of the platform dilutes positioning. | Walk-forward backtesting serves the validation need for serious users. |
| AI-generated game narratives / write-ups | LLMs writing "here's why the Chiefs cover tonight" is commoditized. | Copilot serves analysis needs. Avoid editorial content. |

---

## Feature Dependencies

Understanding what must be built before what, given the existing foundation.

```
# Foundation (already built)
EV Calculator → Alpha Score (extends EV, adds multipliers)
Historical Odds Archive → Walk-Forward Backtester
Historical Odds Archive → Key Number Zone Detector
Kelly Calculator → Monte Carlo Simulator (Monte Carlo validates Kelly fractions)
Line Movement Classifier → Regime Detector (regime uses movement as input signal)
Kalshi/Polymarket API clients → PM Edge Scanner
PM Edge Scanner → PM Regime Classification

# New dependencies
Regime Detector → Alpha Score (regime_scale is a required input)
Monte Carlo Simulator → Alpha Score display (ruin probability shown alongside alpha)
Walk-Forward Backtester → Quality Badges (badges are walk-forward output)
Alpha Score → LLM Setup Evaluator (evaluator validates alpha before alerting)
Alpha Score → BettingCopilot (copilot uses alpha ranking for recommendations)
LLM Setup Evaluator → Alert System (evaluator gates all Discord/push alerts)
LangGraph StateGraph → BettingCopilot (copilot is a graph node)
LangGraph StateGraph → Specialist Agents (workflow routes to specialists)

# Front-end dependencies
FastAPI REST Layer → Web Dashboard
FastAPI REST Layer → Mobile App
Alpha Score + Monte Carlo + Regime Detector → Web Dashboard (all three needed for dashboard to be useful)
Push Notification System → Mobile App value plays feed
Cross-Market Correlation Engine → Portfolio page (needed for exposure visualization)
CLV Tracking → Portfolio performance page (CLV is the headline portfolio metric)

# Data dependencies
Public Betting % + Handle % → Regime Detector (required inputs)
Injury Report API → LLM Setup Evaluator (evaluator checks injury conflicts)
Historical Spread Outcomes → Key Number Zone Detector
Model Predictions → PM Edge Scanner (model_prob needed to compare vs market_prob)
Platt Scaling Calibration → Confidence Multiplier in Alpha Score
```

---

## MVP Recommendation for the Upgrade Milestone

The upgrade adds to an existing, functional platform. "MVP" here means the minimum viable upgrade
that delivers on the institutional-grade promise.

**Prioritize:**
1. Alpha Score — replaces raw EV% ranking everywhere. Immediate quality improvement to existing alerts.
2. Regime Detector — provides the regime_scale input that makes Alpha Score meaningful.
3. Monte Carlo Simulator — provides ruin probability. Immediately communicable risk metric.
4. LLM Setup Evaluator — reduces false positives. Quality gate before any alert ships.
5. LangGraph StateGraph skeleton — enables specialist routing (required for Copilot).
6. BettingCopilot — highest stickiness. Makes platform feel genuinely different.

**Defer until after Copilot is working:**
- Walk-forward backtester (valuable but not blocking any UX flow)
- 5-model ensemble upgrade (current 2-model base is functional)
- PM regime classification (PM edge scanner is the value; regime adds refinement)
- Mobile app (web dashboard first; mobile needs web API to be stable)
- Cross-market correlation engine (valuable but complex; MVP portfolio view works without it)

**Never defer:**
- CLV tracking — add early. Serious bettors ask for it immediately. Simple to compute
  once you have closing lines in the historical archive.
- LLM Setup Evaluator — must ship before BettingCopilot to ensure recommendation quality.

---

## Competitive Positioning Reference

Competitors and where SharpEdge differentiates (MEDIUM confidence — training data, not verified):

| Tool | Primary Strength | SharpEdge Advantage |
|------|-----------------|---------------------|
| OddsJam | Positive EV finder, odds comparison, CLV | Alpha Score > raw EV. Regime-aware sizing. Copilot. Monte Carlo. |
| Pikkit | Bet tracking, CLV, bankroll management | Model-driven recommendations. PM edge. Regime detection. |
| Betburger | Arb + surebets across global books | Already matched on arb. SharpEdge wins on model predictions + PM edge. |
| Action Network | Line movement, public %, sharp vs public | SharpEdge formalizes sharp vs public as regime classifier with alpha multipliers. |
| Betstamp | CLV tracking, bet logging | SharpEdge adds model predictions + copilot to the tracking layer. |
| Sportsline Pro | Model-based predictions | SharpEdge adds transparency (calibration badges), bankroll simulation, copilot. |

None of these tools combine: composite alpha scoring + Monte Carlo risk + regime detection +
conversational copilot + prediction market edge detection in one platform. That combination is
the institutional-grade pitch.

---

## Sources

- PROJECT.md — Existing feature inventory and constraints
- UPGRADE_ROADMAP.md — Detailed feature specifications and phase plan
- Training knowledge (MEDIUM confidence): OddsJam, Pikkit, Betburger, Action Network, Betstamp
  feature sets as of August 2025. Competitive landscape may have shifted.
- Note: WebSearch was unavailable. Competitive analysis should be re-verified against current
  product pages before roadmap is finalized.
