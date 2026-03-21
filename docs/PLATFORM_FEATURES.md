# Platform features & pricing (current)

Single reference for **list prices**, **tier rules**, and **recent product additions**. Whop product prices must be updated manually in the Whop dashboard to match.

## Subscription tiers

| Tier | Price (list) | Notes |
|------|----------------|-------|
| **Free** | $0 | Discord basics; web/mobile limited tabs |
| **Pro** | **$19.99/mo** | Main paid tier: analytics, PM, portfolio, line shop, props |
| **Sharp** | **$49.99/mo** | Pro + sportsbook arb (Discord), CLV depth, weekly AI review |

**Order:** `free` < `pro` < `sharp`. Sharp satisfies any gate that requires Pro.

**Operator** (`is_operator` in JWT) is not a subscription tier; it gates internal execution/swarm routes only.

**Code references:** `Tier` enum in `packages/shared/src/sharpedge_shared/types.py`; display cents in `packages/shared/src/sharpedge_shared/constants.py` (`TIER_PRICES`); web gates in `apps/web/src/middleware.ts`; mobile tab gates in `apps/mobile/lib/main.dart`.

---

## Recent platform additions (high level)

### Multi-book odds API (webhook server)

Public JSON endpoints (server needs `ODDS_API_KEY` / config `odds_api_key`):

- `GET /api/v1/odds/games?sport=NFL` — game picker data  
- `GET /api/v1/odds/line-comparison?sport=&game_id=` — spreads, totals, ML across books with best-line flags  
- `GET /api/v1/odds/props?sport=&game_id=&market_key=` — alternate/prop market rows from The Odds API  

**Implementation:** `apps/webhook_server/src/sharpedge_webhooks/routes/v1/odds_lines.py`

### Web dashboard (Pro-gated)

- **`/lines`** — Line shop UI (sport, game, comparison tables)  
- **`/props`** — Props explorer (market key + game; Odds API alternate markets)  
- Nav links in `apps/web/src/app/(dashboard)/layout.tsx`; middleware in `apps/web/src/middleware.ts`

### Mobile app (Flutter)

- **Portfolio performance** — Stats (ROI, win rate, CLV, max drawdown), ROI / P/L charts, active bets; extends `PortfolioSnapshot` from `GET /api/v1/users/{id}/portfolio`  
- **Game analysis** — Tap a value play → `GET /api/v1/games/{id}/analysis` (model summary + injuries)  
- **Markets → ⋮** — **Line shop** and **Props explorer** screens calling the odds v1 API  
- **Tier parity** — Pro tabs aligned with web middleware (Feed remains more open)

### Prediction markets tier alignment

**Pro** is the minimum tier for prediction-market surfaces everywhere: Discord `/pm-markets`, `/pm-compare`, `/pm-arb`; web `/prediction-markets`; mobile **Markets**. **Sharp** adds sportsbook **`/arb`**, CLV tooling, and weekly reviews—not PM exclusivity.

### Microcopy

Shared upgrade tone and Whop URL:

- Web: `apps/web/src/lib/microcopy.ts`  
- Mobile: `apps/mobile/lib/copy/microcopy.dart`  
- Discord tier embeds: `apps/bot/src/sharpedge_bot/microcopy.py` (used by `tier_check.py`)

---

## User-facing docs

- **Day-to-day guide:** `docs/USER_GUIDE.md`  
- **Feature catalog & matrix:** `docs/FEATURE_OVERVIEW.md`  
- **This file:** pricing snapshot + what shipped recently  

---

## Whop checklist

After changing list prices:

1. Update **Pro** and **Sharp** product prices in [Whop](https://whop.com).  
2. Confirm Discord role / entitlement mapping still matches `WHOP_PRO_PRODUCT_ID` / `WHOP_SHARP_PRODUCT_ID`.  
3. Spot-check `/subscribe` in Discord and the web landing page copy.
