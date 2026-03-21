# Feature Research

**Domain:** Institutional-grade sports betting + prediction market intelligence platform — freemium launch with Discord community and mobile apps
**Researched:** 2026-03-21
**Confidence:** MEDIUM-HIGH (quant features HIGH from prior research; launch/distribution features MEDIUM from verified web research 2026-03-21)

---

## Part 1: Quant Engine Feature Landscape (retained from prior research)

> Confidence: HIGH. Based on deep reading of PROJECT.md and competitive analysis of OddsJam, Pikkit, Betburger, Action Network, Betstamp, Sportsline Pro.

### Table Stakes — Quant/Analytics

Features that serious/professional bettors expect. Missing = platform feels amateur, users leave for OddsJam or Action Network.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Expected Value (EV) calculator | Every pro tool has this. Without it, platform is a tip service, not analytics. | LOW | Already built. Bayesian confidence (P(edge > 0)) is above average for this category. |
| No-vig fair odds / true probability | Devig is step 0 before any edge calculation. | LOW | Already built. |
| Multi-book odds comparison | Pros shop lines. Single-book users are not the target. | LOW-MED | The Odds API (30+ books) is connected. Display layer needed. |
| Line movement history + classification | Sharp vs public movement is the most widely used qualitative signal. | MED | Already built (steam, RLM, buyback). Display needed. |
| Arbitrage detection | Cross-book arb is table stakes for any "edge detection" pitch. | MED | Already built (cross-book + Kalshi x sportsbooks). |
| Kelly Criterion sizing | Bankroll management is non-negotiable for pros. Flat betting is a dealbreaker signal. | LOW | Already built. |
| Bet tracking / portfolio logging | ROI, win rate, CLV tracking — pros won't use a tool that doesn't track their history. | MED | Schema exists. Portfolio API route needed. |
| Closing Line Value (CLV) tracking | CLV is the gold standard metric for serious bettors. Beating the close = long-run positive EV. | MED | Not yet built. High priority for credibility with pros. |
| Historical odds archive | Needed for backtesting, CLV, and any model validation claim. | MED | Already built (Supabase). |
| Subscription / access control | Monetization must exist or platform is a hobby. | LOW | Already built (Whop). |
| Odds alert / notification system | Pros need to be notified of edges, not polling a dashboard. | MED | Discord alerts exist. Push notifications needed for mobile. |
| Injury / news integration | Pros account for injuries manually if the tool doesn't. | MED | ESPN feed exists. Injury impact scoring not yet built. |

### Differentiators — Quant/Analytics

Features that separate SharpEdge from every OddsJam/Action Network tier tool.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Composite Alpha Score (EV x regime x survival x confidence) | Single ranking number integrating multiple signals. No other retail tool does multi-factor alpha composition. | HIGH | Core differentiator. Prevents gaming a single metric. |
| Monte Carlo bankroll ruin simulation | "3.2% ruin over 500 bets at this sizing" is intuitively powerful. No retail betting tool provides this. | HIGH | Transforms abstract Kelly fractions into survival probability. |
| Betting market regime detection (7-state HMM) | Classifying sharp/public/steam/thin/post-news states and weighting edges accordingly. | HIGH | Requires public % + handle + line velocity data to function. |
| Walk-forward backtesting with quality badges | Out-of-sample validation. "EXCELLENT" quality badge signals reliability. No retail tool does honest walk-forward. | HIGH | Requires historical data pipeline already in place. |
| LLM setup evaluator (PASS/WARN/REJECT gate) | LLM checks for contradictory signals, trap lines, injury conflicts before alerting. Reduces false-positive alerts. | MED-HIGH | Direct differentiator vs purely mechanical alert systems like OddsJam. |
| BettingCopilot (conversational analysis with portfolio awareness) | "Should I bet Lakers -3.5?" with full context: current exposure, bankroll, regime, model output. | HIGH | Highest stickiness feature. Makes the platform feel like a quant analyst in your pocket. |
| Prediction market probabilistic edge detection (Kalshi/Polymarket) | Model probability vs market probability — beyond arbitrage. Retail tools only do PM arb, not edge scoring. | HIGH | Novel in retail. |
| Cross-market correlation engine | Prevents double-exposure to correlated bets. Retail tools don't track portfolio correlation. | MED-HIGH | Critical for Kelly sizing to be correct across a portfolio. |
| Model calibration quality badges | Transparent confidence about model reliability. No retail tool exposes calibration quality. | MED | Builds trust with sophisticated users. Distinguishes from black-box tip services. |

---

## Part 2: Launch & Distribution Feature Landscape (new for v3.0)

> Confidence: MEDIUM. Based on web research conducted 2026-03-21. Sources cited inline.

This section answers the v3.0 question: what features, structure, and conversion patterns are table stakes vs differentiators for the launch milestone specifically.

---

## Table Stakes — Discord Community Monetization

Features a credible paid Discord signals/analytics community must have at launch. Missing any of these = server feels unfinished, members don't trust it, conversion stalls.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Clear channel structure separating free vs paid | Members expect to see what they're missing. Visible gated channels are the primary upsell surface. | LOW | Create #free-picks, #public-edges, #getting-started as visible-to-all; #pro-alerts, #model-edges, #kalshi-signals as role-gated. |
| Automated role assignment on payment | Members expect instant access when they pay. Manual role grants cause churn. | LOW | Whop bot handles this automatically on subscription. Zero custom code needed. |
| Welcome / onboarding flow (Discord Community Onboarding feature) | New members who can't find value in 15 minutes leave forever. Discord's built-in onboarding reduces friction. | LOW | Use Discord's native Community Onboarding — assign roles by bettor type (casual/sharp/PM trader). Avoid bot-gate mazes. |
| Rules, FAQ, and getting-started resources | Trust signal. No rules channel = unmoderated-feeling server. | LOW | One rules channel, one FAQ, one #start-here pinned message is sufficient. Do not over-architect. |
| Regular signal posts (bot-automated) | Dead servers die. Members expect activity. Sporadic manual posts kill retention. | MED | Bot must post to free tier channels on schedule; absence of activity is the #1 Discord community killer. |
| Pinned win/track-record evidence | Sports bettors are scam-wary. Track record transparency is a trust prerequisite. | LOW | Post model performance weekly in a #track-record channel visible to free tier. |
| Upgrade prompt at natural friction points | Conversion requires friction + escape. Members need to know exactly how to upgrade when they hit a gated channel. | LOW | Whop link pinned in every locked channel's description. Bot responds to free-tier slash commands with upgrade prompt. |

### Pricing for Discord Tier (MEDIUM confidence — benchmarks from market research)

Sports betting Discord servers cluster into two working models:

- **$15-30/month Mid tier** (Discord + more alerts): Best fit for casual bettors. GoldBoys Silver at $50/month is the high end; PromoGuy Plus at $19/month is the floor. SharpEdge Mid at **$19-29/month** is defensible given quant credentials.
- **$50-150/month Premium tier** (web + mobile + full suite): Comparable to OddsJam Gold ($199/month) but SharpEdge is solo-founder pre-reputation. Start at **$49-79/month** for early adopters.

The 2-5% Discord member → paid conversion rate is the industry floor. Target 5-10% via tight free/paid channel separation and immediate value demonstration in free channels.

---

## Table Stakes — App Store Listing

Features and metadata elements required for App Store approval and organic discovery. Missing = app rejected or invisible.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Privacy policy URL | Apple mandates for apps that collect user data. Absence = rejection. | LOW | One-page hosted policy is sufficient. Termly or Iubenda generate compliant ones cheaply. |
| Age verification / 17+ rating | Apple Guideline 5.3: apps that display gambling content (even analytics) must be rated 17+. | LOW | Set age rating in App Store Connect to 17+. No additional UX needed. |
| Geo-restriction language in description | Apple scrutinizes gambling-adjacent apps for jurisdiction compliance. Clear "not available for real-money wagering" language avoids rejection. | LOW | Add disclaimer: "SharpEdge provides analytics only. No real-money wagering facilitated through this app." |
| Keyword-optimized title + subtitle | 70% of app installs start from search. Title and subtitle are the highest-weight keyword fields. | LOW | Target: "sports betting analytics", "EV calculator", "odds comparison", "bet tracker". Max 30 chars in subtitle. |
| Screenshots with active feature captions | Apple's algorithm reads text in screenshots for keyword ranking. Screenshots without captions lose ranking signals. | LOW-MED | 6 screenshots minimum. Each screenshot shows a key screen with overlay text. Use captions like "Find +EV edges instantly" not just a raw screen. |
| Preview video (optional but high-ROI) | Adding a preview video lifts conversion rate by 10-30% (verified by ASO research). | MED | 15-30 second demo showing: alert arrives → edge details → tap to see Kelly sizing. |
| App category selection | Sports (primary) + Finance (secondary) maximizes keyword surface area for a betting analytics app. | LOW | Sports is correct primary; Finance secondary captures the quant/EV calculator searchers. |

### App Store Risk: Guideline 5.3

SharpEdge is an analytics app, not a gambling app, but Apple applies 5.3 scrutiny to anything gambling-adjacent. The safe positioning is: "sports analytics and odds tracking." The dangerous positioning is: "find profitable bets." Use "find +EV opportunities" not "find profitable bets" in all copy. Geo-restriction and age-gating (17+) are non-negotiable for approval. Expect 1-2 review cycles on first submission — build 2 weeks into the timeline.

---

## Table Stakes — Landing Page Conversion (Cold Launch, No Audience)

A cold-launch landing page has one job: convert a skeptical stranger into a free signup or Discord join within 90 seconds. These features are table stakes — missing them kills conversion.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Single above-the-fold CTA | Pages with one CTA outperform multiple-CTA pages. "Start Free" or "Join Discord Free" — pick one. | LOW | Do not offer "Start Free" AND "See Pricing" AND "Learn More" in the hero. One button. |
| Benefit-driven headline (not feature-driven) | "Surface high-alpha edges before the market moves" converts better than "Bayesian EV calculator with regime detection." Visitors buy outcomes, not features. | LOW | Lead with outcome: "Bet with an edge, not a guess." Feature language goes below the fold. |
| Social proof before the fold | Testimonials increase conversion by 34% (Unbounce research). No audience = no testimonials yet. Use model performance data instead: "12% average CLV on NFL spreads, 847 bets tracked." Data is social proof when people aren't. | LOW-MED | Screenshot of track record dashboard. Real numbers. No fake testimonials. |
| Pricing tiers visible without scrolling | Freemium products with hidden pricing lose comparison shoppers. Show Free / Mid / Premium clearly. | LOW | Three-column pricing card below hero. Free tier must be clearly labeled — it drives top-of-funnel. |
| Free tier value is obvious | Visitors won't sign up for Free if they can't tell what they get. Free must feel useful, not crippled. | LOW | List 3-4 specific free features in the pricing tier card: "Daily +EV alerts via Discord", "EV calculator", "Line movement feed." |
| Mobile-responsive design | 60%+ of cold traffic arrives on mobile. | LOW | Not optional. |
| Fast page load (<3 seconds) | Every second of load delay reduces conversion ~7%. | LOW | Static or SSG page. No server-side rendering needed for a landing page. |

### What NOT to do on the landing page

- Do not gate the pricing page behind email signup. Conversion drops dramatically when pricing is hidden.
- Do not use vague sports analytics copy ("institutional-grade probabilistic intelligence platform"). Too abstract. Say: "Find +EV bets before the line moves. Track every edge. Build a bankroll."
- Do not list every feature. Pick the 3 most differentiating and explain each in one sentence.
- Do not A/B test at launch. Not enough traffic. Ship a single strong version.

---

## Differentiators — Discord Community

Features that separate a credible paid signals server from the hundreds of scam-adjacent tip servers.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Weekly model performance transparency (#track-record channel) | Bettors have been burned by tip services. Public, bot-generated track record (auto-posted from actual model outputs) is extremely rare and extremely credible. | MED | Requires model results to flow into a public Discord post automatically. Not a manual screenshot — auto-generated from settled bets. |
| Free tier shows real edge detection output (not "teaser" picks) | Most tip servers post vague free picks with no methodology. Posting actual EV% + model confidence in free tier lets the math speak. | LOW | Post one free edge/day with EV%, no-vig probability, and line source. Members who understand EV are the buyers. |
| Bot commands as product demo | Free-tier slash commands that work (even with limited data) demonstrate product quality before payment. | MED | /ev, /arb, /lines available to free users with rate limiting. Premium unlocks full depth. |
| Response to questions from the founder | Solo founder, early community: answering DMs and server questions is the highest-ROI activity for early retention and conversion. Scales poorly, but critical for first 100 users. | LOW | Not a feature to build — a behavior to commit to. |
| Office hours / AMA sessions (async) | Rithmm uses this. Monthly text-channel Q&A with the analyst is a differentiator vs fully automated servers. | LOW | One dedicated async thread per month. Low overhead, high perceived value. |

---

## Differentiators — App Store Listing

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Custom Product Pages (Apple) | Up to 35 variant App Store pages — one targeting "bet tracker" searchers, one for "EV calculator" searchers, one for "arbitrage" searchers. Each variant ranks independently. | MED | Available in App Store Connect. Each page has its own screenshots and keyword emphasis. High ROI for an app that serves multiple use cases. |
| Screenshot sequence that tells a story | Most sports apps show raw screens. A screenshot sequence that walks through a workflow ("Edge found → sizing → bet tracked → CLV confirmed") converts better than disconnected feature screenshots. | LOW-MED | 6 screenshots: Alert fires → Edge detail screen → Kelly sizing → Bet logged → CLV result → Premium upgrade prompt. |
| Seasonal keyword updates | Sports analytics has seasonal search spikes (NFL season, March Madness, NBA playoffs). Updating the keyword field before each season captures high-intent searchers. | LOW | Calendar task, not a feature build. |

---

## Differentiators — Landing Page

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Live model output embedded in landing page | A live odds scanner or EV feed on the landing page (anonymized) proves the product works before signup. Extremely rare on sports analytics landing pages. | MED | Requires API endpoint returning sanitized edge data. Shows the engine is real, not mockups. |
| "How the model works" explainer section | Serious bettors (the buyers) are skeptical of black boxes. A brief, honest technical explainer ("gradient boosting on 4 years of spread data, Bayesian confidence intervals") increases conversion for the target segment. | LOW | Text section, no build cost. Counter-intuitive: less technical copy hurts with quant-curious bettors. |
| Specific, non-hedged performance claims | "Our model hit 54.3% on NFL spreads ATS last season across 312 plays (ROI: +4.8%)" converts better than "better than average." Show the actual data. | LOW | Requires honest track record to exist. Do not fabricate. |

---

## Differentiators — Onboarding Sequence (Free to Paid)

The sequence that converts a new free signup into a paying subscriber. Industry average: 2-5% free→paid. Top SaaS: 15%+. This sequence is the primary lever.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Immediate value delivery (Day 0) | Nearly 60% of free users drop off before Day 3. The fastest path to retained users is showing a real edge within the first session. | MED | First Discord message to new member is a bot-generated edge post for that day's games, not a "welcome to the community" message. Immediate utility > welcome ceremony. |
| Behavior-triggered upgrade prompt (not time-triggered) | Trigger-based emails convert significantly higher than time-based drips. Trigger: user runs /ev command (shows engagement) → upgrade prompt fires within minutes. | MED | Requires event tracking (Sentry or Posthog). User runs bot command → webhook fires → Whop checkout link sent via DM. |
| 3-email onboarding sequence (Day 0, Day 3, Day 7) | High-performing SaaS onboarding uses 4-6 emails. Sports analytics users need: (1) what you can do now, (2) what you're missing, (3) time-limited offer. | LOW | Day 0: Welcome + today's free edge. Day 3: "Here's what Pro members saw this week" (model output sample). Day 7: Upgrade CTA with early-adopter price if launching in first 30 days. |
| "Aha moment" as design target, not feature | The aha moment for this product is seeing a line that moves in your predicted direction after your edge was flagged. Design the free tier to show this happening. | MED | Show a recent edge where the line moved sharply after alert. In a #proof channel or bot post. |
| Upgrade in-app (not redirect to Whop) | Friction kills conversion. If upgrading requires leaving the Discord to visit Whop, drop-off increases. | LOW | Whop's Linktree-style shop page is the minimum. A /upgrade bot command that posts the Whop link inline is better. |

---

## Anti-Features — Launch Phase

Features that seem essential but add cost without improving the v3.0 conversion funnel.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Referral / affiliate program at launch | Requires baseline conversion data to calibrate. Building before you know your baseline conversion rate wastes engineering time on wrong incentive amounts. | Launch first, add referral after 60 days of conversion data. Already deferred in REQUIREMENTS.md. |
| In-app community / social features | Real-time user chat, picks sharing, leaderboards attract tip-followers and increase moderation burden. Not the target user. | Keep community in Discord where it belongs. |
| Admin dashboard for user management | Can manage via Supabase + Whop dashboards during launch phase. Custom admin adds 2-4 weeks of build time. | Build after first 200 users when manual management becomes painful. |
| Multiple landing page variants at launch | Not enough traffic to A/B test meaningfully. Building 3 variants before launch wastes time. | Ship one strong landing page. Test after you have 500+ weekly visitors. |
| Email newsletter / content marketing | Requires consistent content production. Dilutes focus from product. SEO takes 6+ months to compound. | Build in public on X/Twitter instead. Lower overhead, faster distribution. |
| Paywalled free trial (credit card required) | "Free" with a credit card gate is not free. Drops top-of-funnel signups significantly. Discord join as the free entry point avoids this entirely. | Discord join = true freemium entry. No friction, no card. |
| Complex Discord bot permission system at launch | Over-engineering role hierarchies and channel permissions creates a confusing server for new joiners. Discord's own research shows bot-gate mazes hurt retention. | Three tiers max: @everyone (can see free channels), @Mid (mid tier), @Premium. Whop assigns roles. Done. |

---

## Feature Dependencies — Launch Layer

```
Whop Account
    └──required for──> Discord Role Assignment
    └──required for──> Web App Auth (paid unlock)
    └──required for──> Mobile App Auth (paid unlock)

Discord Bot (already built)
    └──required for──> Discord Tier Gating
    └──required for──> Onboarding Sequence (bot sends Day 0 DM)
    └──required for──> Behavior Trigger (bot command → upgrade prompt)

Event Tracking (Posthog or Sentry)
    └──required for──> Behavior-Triggered Upgrade Prompt
    └──required for──> Onboarding Email Sequence Trigger

Landing Page
    └──feeds──> Discord Join (free CTA)
    └──feeds──> Whop Checkout (paid CTA)
    └──optional enhancement: Live Model Output Embed

App Store Listing
    └──requires──> Privacy Policy URL
    └──requires──> 17+ Age Rating
    └──requires──> Geo-restriction disclaimer
    └──benefits from──> Preview Video (10-30% lift in conversion)
    └──benefits from──> Custom Product Pages (multiple keyword targets)

Free Tier Value
    └──required for──> Discord Retention (members see daily edge posts)
    └──required for──> Onboarding Aha Moment (user sees a live edge)
    └──drives──> Upgrade Conversion (members who see value convert)
```

---

## MVP Definition — v3.0 Launch

### Launch With

- [ ] Discord server with 3-tier channel structure (free visible, Mid + Premium gated) — table stakes, zero revenue without this
- [ ] Whop → Discord role assignment working end-to-end — without this, payments don't unlock access
- [ ] Bot posting to free channels on schedule (1 edge/day minimum) — dead server = no conversion
- [ ] #track-record channel with automated weekly model performance post — trust signal, required for sports betting niche
- [ ] Landing page with single CTA, benefit headline, pricing tiers, and 3 performance data points — minimum credible web presence
- [ ] App Store listing with 17+ rating, privacy policy, keyword-optimized title + subtitle, and 6 captioned screenshots — minimum for approval
- [ ] 3-email onboarding sequence (Day 0, Day 3, Day 7) — highest ROI conversion activity, low build cost
- [ ] /upgrade bot command that posts Whop checkout link inline — removes upgrade friction

### Add After First 30 Days

- [ ] Behavior-triggered upgrade prompt (bot command → DM with Whop link) — needs event tracking to be in place first
- [ ] Custom Product Pages for App Store (target 2-3 keyword variants) — needs baseline install data first
- [ ] Preview video for App Store listing — can A/B test after baseline established
- [ ] "Office hours" async AMA thread in Discord — low overhead, add when server has >50 members

### Defer to v3.1+

- [ ] Referral / affiliate program — needs baseline conversion data
- [ ] Admin dashboard — Supabase + Whop is sufficient until ~200 users
- [ ] Content marketing / blog — high time cost, slow ROI; build-in-public on X is faster
- [ ] Email newsletter — not core to conversion funnel at this scale

---

## Feature Prioritization Matrix — v3.0

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Discord tier structure + Whop role assignment | HIGH | LOW | P1 |
| Bot posting free edges daily | HIGH | LOW | P1 |
| Landing page (single CTA, pricing, data) | HIGH | LOW | P1 |
| App Store listing (compliant, keyword-optimized) | HIGH | LOW | P1 |
| 3-email onboarding sequence | HIGH | LOW | P1 |
| #track-record channel (bot-automated) | HIGH | LOW | P1 |
| /upgrade bot command | MED | LOW | P1 |
| Behavior-triggered upgrade prompt | HIGH | MED | P2 |
| App Store preview video | MED | MED | P2 |
| Custom App Store Product Pages | MED | MED | P2 |
| Discord office hours AMA | MED | LOW | P2 |
| Live model output embed on landing page | HIGH | MED | P2 |
| Referral program | MED | HIGH | P3 |
| Content marketing / SEO blog | MED | HIGH | P3 |
| Admin dashboard | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch — revenue is blocked without this
- P2: Add within 30 days of launch — significant conversion impact
- P3: Post-validation — defer until baseline data exists

---

## Competitor Feature Analysis — Launch & Distribution

| Feature | OddsJam | BettingPros | Action Network | SharpEdge Approach |
|---------|---------|-------------|----------------|---------------------|
| Free tier | 7-day trial only (card required) | Free daily picks + limited analytics | Fully free core app | Discord join with daily free edge — true freemium, no card |
| Pricing | $19.99–$399.99/month | Undisclosed | Free + Pro tier | Mid $19-29, Premium $49-79 — competitive vs segment |
| App Store presence | Yes, full iOS/Android | Yes, full iOS/Android | Yes, dominant | Must launch with iOS + Android simultaneously |
| Discord community | None | None | None | Unique distribution channel for this segment |
| Onboarding | Email trial sequence | In-app | In-app | Discord DM + email sequence hybrid |
| Social proof | Reviews on site | App store reviews | App store reviews + media coverage | Model track record + App Store reviews |
| Landing page CTA | "Start Free Trial" | App Store link | App download | "Join Discord Free" (lower friction than app download or card) |

Key insight: OddsJam, BettingPros, and Action Network have no Discord community strategy. A credible paid Discord server with real model outputs fills a gap that the incumbents are not serving.

---

## Sources

**Quant Engine Research:**
- PROJECT.md — Existing feature inventory and constraints
- Training knowledge (MEDIUM confidence): OddsJam, Pikkit, Betburger, Action Network, Betstamp feature sets as of August 2025

**Launch & Distribution Research (conducted 2026-03-21):**
- [How to Monetize a Discord Server in 2026](https://www.discortize.com/blogs/how-to-monetize-discord-server)
- [Discord Monetization — Paid Roles, Tiers, Perks](https://postiz.com/blog/discord-monetization-paid-roles-tiers-and-perks)
- [Monetization for Discord Communities](https://www.meegle.com/en_us/topics/monetization-models/monetization-for-discord-communities)
- [How to Set Up Membership Tiers on Discord — Whop](https://whop.com/blog/membership-tiers-discord/)
- [Top Sports Betting Discord Servers 2026 — Whop](https://whop.com/blog/sports-betting-discord-servers/)
- [Sports Betting Discords 2026 — BVCompany](https://bvcompany.org/best-sports-betting-discords/)
- [Discord Community Onboarding — Official Docs](https://discord.com/community/community-onboarding)
- [Fix Apple Gambling App Rejection (Guideline 5.3)](https://shopapper.com/fix-apple-gambling-app-rejection-guideline-5-3/)
- [iOS App Store Review Guidelines 2026](https://theapplaunchpad.com/blog/app-store-review-guidelines)
- [ASO Guide for Sports Apps — Togwe](https://www.togwe.com/blog/aso-app-store-optimization/)
- [ASO 2025 Complete Guide — Udonis](https://www.blog.udonis.co/mobile-marketing/mobile-apps/complete-guide-to-app-store-optimization)
- [SaaS Landing Page Best Practices 2025 — Grafit Agency](https://www.grafit.agency/blog/saas-landing-page-best-practices)
- [Landing Page Conversion Stats 2026 — Genesys Growth](https://genesysgrowth.com/blog/landing-page-conversion-stats-for-marketing-leaders)
- [Free Trial to Paid — 7 Proven Tactics 2025](https://beyondlabs.io/blogs/how-to-turn-free-trial-users-into-paying-saas-customers)
- [How to Improve Free-to-Paid SaaS Conversion Rates — MADX](https://www.madx.digital/learn/how-to-improve-free-to-paid-saas-conversion-rates)
- [SaaS Onboarding Email Sequences Examples — Sequenzy](https://www.sequenzy.com/blog/onboarding-email-sequence-examples)
- [OddsJam Subscription Packages](https://oddsjam.com/subscribe)
- [Best Sports Betting Analytics Tools 2026 — HeatCheck HQ](https://heatcheckhq.io/blog/best-sports-betting-analytics-tools-2026)
- [Product Hunt Alternatives 2026 — LaunchDirectories](https://launchdirectories.com/blog/product-hunt-alternatives-18-places-to-launch-in-2026)

---
*Feature research for: SharpEdge v3.0 Launch & Distribution*
*Researched: 2026-03-21*
