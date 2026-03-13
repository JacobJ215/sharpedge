# SharpEdge — Next Steps to Get Running

## 1. Set Up External Accounts

You need credentials for the following services. Create accounts if you haven't already:

### Core Services

| Service | URL | What You Need | Priority |
|---------|-----|---------------|----------|
| **Discord** | https://discord.com/developers/applications | Bot token, Client ID, Guild ID | Required |
| **Supabase** | https://supabase.com/dashboard | Project URL, Service Key | Required |
| **The Odds API** | https://the-odds-api.com | API Key | Required |
| **OpenAI** | https://platform.openai.com/api-keys | API Key (GPT-4o access) | Required |
| **Upstash Redis** | https://upstash.com | Redis URL (or use local Docker) | Required |

### Payment & Monetization

| Service | URL | What You Need | Priority |
|---------|-----|---------------|----------|
| **Whop** | https://whop.com/sell | API Key, Webhook Secret, Product IDs | Required |

### Prediction Markets (Optional - for PM features)

| Service | URL | What You Need | Priority |
|---------|-----|---------------|----------|
| **Kalshi** | https://kalshi.com/sign-up | API Key, RSA Private Key | Optional |
| **Polymarket** | https://polymarket.com | API Key, API Secret | Optional |

### Data Enrichment (Optional - enhances analysis)

| Service | URL | What You Need | Priority |
|---------|-----|---------------|----------|
| **WeatherAPI** | https://weatherapi.com | API Key (free tier) | Recommended |
| **ESPN** | Public API | No key needed | Recommended |
| **SportsData.io** | https://sportsdata.io | API Key ($50+/mo) | Future |
| **Action Network** | Enterprise only | API Key | Future |

---

## 2. Discord Bot Setup

1. Go to Discord Developer Portal → New Application → "SharpEdge"
2. Go to Bot tab → Reset Token → copy `DISCORD_BOT_TOKEN`
3. Copy Application ID as `DISCORD_CLIENT_ID`
4. Enable Privileged Intents: Server Members Intent, Message Content Intent
5. Generate invite URL: OAuth2 → URL Generator → Select `bot` + `applications.commands` → Select permissions (Send Messages, Manage Roles, Use Slash Commands, Embed Links, Attach Files)
6. Invite bot to your test server
7. Copy your server's ID as `DISCORD_GUILD_ID` (right-click server → Copy Server ID, developer mode must be on)

---

## 3. Whop Setup (Payments)

Whop is the recommended platform for selling Discord-based products. It handles payments, access control, and integrates natively with Discord.

### Create Your Whop Store

1. Go to https://whop.com/sell and create a seller account
2. Create a new product: "SharpEdge Pro" or "SharpEdge"
3. Set up pricing tiers:
   - **Free Tier**: $0 (optional, for lead gen)
   - **Pro Tier**: $49/month
   - **Sharp Tier**: $99/month

### Configure Products

For each tier, set up:
- Name and description
- Price and billing cycle (monthly)
- Discord integration (connects to your server automatically)
- Role assignment (Whop manages Discord roles for you)

### Get API Credentials

1. Go to Whop Dashboard → Settings → Developer
2. Create API Key → copy as `WHOP_API_KEY`
3. Set up webhook endpoint: `https://your-domain.com/webhooks/whop`
4. Copy webhook secret as `WHOP_WEBHOOK_SECRET`
5. Copy Product IDs:
   - Pro product → `WHOP_PRO_PRODUCT_ID`
   - Sharp product → `WHOP_SHARP_PRODUCT_ID`

### Webhook Events to Handle

Configure webhooks for:
- `membership.went_valid` - Grant access
- `membership.went_invalid` - Revoke access
- `payment.succeeded` - Log payment
- `payment.failed` - Handle failed payment

---

## 4. Prediction Market Setup (Optional)

### Kalshi API Setup

1. Sign up at https://kalshi.com
2. Go to Account → API → Generate API Key
3. Generate RSA keypair for request signing:
   ```bash
   openssl genrsa -out kalshi_private.pem 2048
   openssl rsa -in kalshi_private.pem -pubout -out kalshi_public.pem
   ```
4. Upload public key to Kalshi dashboard
5. Store private key content in `KALSHI_PRIVATE_KEY` (or as file path)
6. Copy API Key as `KALSHI_API_KEY`

### Polymarket API Setup

1. Sign up at https://polymarket.com
2. API access may require application for full CLOB access
3. Once approved, copy credentials:
   - `POLYMARKET_API_KEY`
   - `POLYMARKET_API_SECRET`
   - `POLYMARKET_PASSPHRASE` (if required)

---

## 5. Configure Environment

```bash
cp .env.example .env
```

Fill in all values:

```bash
# ===========================================
# CORE SERVICES
# ===========================================
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_CLIENT_ID=your_client_id
DISCORD_GUILD_ID=your_guild_id

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key

ODDS_API_KEY=your_odds_api_key
OPENAI_API_KEY=sk-your-openai-key

REDIS_URL=redis://default:password@your-redis.upstash.io:6379

# ===========================================
# WHOP (PAYMENTS)
# ===========================================
WHOP_API_KEY=your_whop_api_key
WHOP_WEBHOOK_SECRET=your_webhook_secret
WHOP_PRO_PRODUCT_ID=prod_xxxxx
WHOP_SHARP_PRODUCT_ID=prod_xxxxx

# ===========================================
# DISCORD ROLES & CHANNELS
# ===========================================
FREE_ROLE_ID=123456789
PRO_ROLE_ID=123456789
SHARP_ROLE_ID=123456789

VALUE_ALERTS_CHANNEL_ID=123456789
LINE_MOVEMENT_CHANNEL_ID=123456789
ARB_ALERTS_CHANNEL_ID=123456789
PM_ALERTS_CHANNEL_ID=123456789

# ===========================================
# PREDICTION MARKETS (Optional)
# ===========================================
KALSHI_API_KEY=your_kalshi_key
KALSHI_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----

POLYMARKET_API_KEY=your_polymarket_key
POLYMARKET_API_SECRET=your_polymarket_secret

# ===========================================
# DATA ENRICHMENT (Optional)
# ===========================================
WEATHER_API_KEY=your_weatherapi_key
```

---

## 6. Deploy Database Schema

### Option A — Supabase SQL Editor (Recommended)

```bash
python scripts/deploy_schema.py
```

Copy/paste output into Supabase SQL Editor:
`https://supabase.com/dashboard/project/YOUR_PROJECT/sql/new`

Run migrations in order:
1. `001_initial_schema.sql` - Core tables
2. `002_analytics_tables.sql` - Analytics & alerts
3. `003_prediction_markets.sql` - PM tables

### Option B — Direct execution

```bash
psql YOUR_SUPABASE_CONNECTION_STRING < packages/database/src/sharpedge_db/migrations/001_initial_schema.sql
```

---

## 7. Install Dependencies

```bash
uv sync
```

This installs all workspace packages and their dependencies.

---

## 8. Start Local Redis (Development)

```bash
docker compose up -d
```

Or skip this if using Upstash Redis (cloud).

---

## 9. Set Up Discord Server Structure

Create these channels and categories:

```
📢 INFORMATION
├── #welcome
├── #announcements
└── #faq

🆓 FREE
├── #general
├── #game-day
└── #free-analysis

💎 PRO ONLY (locked to @Pro Member role)
├── #value-alerts
├── #line-movement
├── #model-analysis
├── #sharp-action
└── #bet-reviews

🔥 SHARP ONLY (locked to @Sharp Member role)
├── #arbitrage-alerts
├── #pm-arb-alerts
├── #advanced-analytics
└── #1on1-support

🤖 BOT
├── #bot-commands
├── #bet-log
└── #my-stats

👥 COMMUNITY
├── #wins-losses
├── #bad-beats
└── #strategy-discussion
```

Create roles:
- `@Admin`
- `@Sharp Member` → copy Role ID as `SHARP_ROLE_ID`
- `@Pro Member` → copy Role ID as `PRO_ROLE_ID`
- `@Free Member` → copy Role ID as `FREE_ROLE_ID`

**Note:** If using Whop, roles can be managed automatically through Whop's Discord integration.

---

## 10. Run the Bot

```bash
uv run sharpedge-bot
```

Or from the bot directory:
```bash
cd apps/bot
uv run python -m sharpedge_bot.main
```

Expected output:
```
SharpEdge bot is online as SharpEdge#XXXX
Slash commands synced to guild XXXXX
Background scheduler started with 7 jobs: opening_lines, odds_monitor, consensus_calc, value_scanner, arb_scanner, alert_dispatcher, pm_arb_scanner
```

---

## 11. Run the Webhook Server (Separate Process)

```bash
uv run sharpedge-webhooks
```

Starts FastAPI server on port 8000 for Whop webhooks.

For local development with Whop:
- Use ngrok or similar: `ngrok http 8000`
- Set webhook URL in Whop dashboard to: `https://your-ngrok-url.ngrok.io/webhooks/whop`

---

## 12. Test Commands

### Free Tier Commands
- `/bankroll set 5000` — Set your bankroll
- `/kelly -110 55` — Calculate Kelly sizing
- `/lines Chiefs Raiders` — Compare odds
- `/subscribe` — See subscription options
- `/tier` — Check your current tier

### Pro Tier Commands
- `/bet NFL "Chiefs -3" -110 2` — Log a bet
- `/pending` — View pending bets
- `/stats` — View performance
- `/analyze Chiefs Raiders` — AI game analysis
- `/value` — Find +EV plays
- `/sharp` — Sharp money indicators
- `/research "What's the sharp action on tonight's game?"` — AI research
- `/chart-movement Chiefs Raiders` — Visual line movement
- `/chart-bankroll` — Your bankroll performance chart

### Sharp Tier Commands
- `/arb` — Current arbitrage opportunities
- `/pm-arb` — Cross-platform PM arbitrage
- `/pm-markets` — Prediction market browser
- `/review-week` — Weekly betting review
- `/chart-clv` — Your CLV tracking chart

---

## 13. Deploy to Production

### Railway (Recommended)

1. Push to GitHub
2. Create Railway project with two services:
   - **Bot**: Start command `uv run sharpedge-bot`
   - **Webhooks**: Start command `uv run sharpedge-webhooks`
3. Set all environment variables
4. Update Whop webhook URL to Railway's webhook server URL

### Alternative: Render, Fly.io, or VPS

Similar process — just ensure both bot and webhook processes run continuously.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Bot not coming online | Check `DISCORD_BOT_TOKEN`, verify intents enabled |
| Commands not showing | Wait 1-2 min for sync, verify `DISCORD_GUILD_ID` |
| Database errors | Verify Supabase URL/key, check schema deployed |
| Odds not loading | Verify `ODDS_API_KEY`, check quota at the-odds-api.com |
| AI analysis failing | Verify `OPENAI_API_KEY` has credits, GPT-4o access |
| Whop webhooks failing | Check webhook secret, verify endpoint URL |
| PM features not working | Verify Kalshi/Polymarket API keys configured |
| Charts not generating | Verify matplotlib installed (included in analytics package) |

---

## Feature Activation Checklist

| Feature | Required Keys | Status |
|---------|---------------|--------|
| Core Bot | Discord, Supabase, Redis | Required |
| Live Odds | The Odds API | Required |
| AI Analysis | OpenAI (GPT-4o) | Required |
| Payments | Whop | Required for monetization |
| Weather Impact | WeatherAPI | Recommended |
| PM Arbitrage | Kalshi + Polymarket | Optional |
| Advanced Stats | SportsData.io | Future |
| Public Betting | Action Network | Future |

---

## API Cost Estimates (Monthly)

| Service | Free Tier | Typical Usage | Notes |
|---------|-----------|---------------|-------|
| The Odds API | 500 requests | $20-100 | Based on request volume |
| OpenAI GPT-4o | None | $50-200 | Based on usage |
| Supabase | 500MB, 2GB transfer | $25+ | Scales with users |
| Upstash Redis | 10K commands/day | $0-10 | Usually free tier sufficient |
| WeatherAPI | 1M calls/month | $0 | Free tier sufficient |
| Kalshi | Free | $0 | No API costs |
| Polymarket | Free | $0 | No API costs |

**Estimated total**: $75-335/month depending on usage

---

## Whop Integration Notes

### Why Whop over Stripe?

1. **Native Discord Integration**: Whop automatically manages Discord roles based on subscription status
2. **Built for Discord Products**: Purpose-built for selling access to Discord servers
3. **Simplified Checkout**: Users familiar with Whop for Discord purchases
4. **Affiliate System**: Built-in affiliate marketing if desired
5. **Analytics**: Dashboard shows subscriber metrics, churn, etc.

### Migration from Stripe (if applicable)

If you previously set up Stripe:
1. Update `apps/webhook_server/` to handle Whop webhooks instead of Stripe
2. Update `subscription_service.py` to use Whop API
3. Update `/subscribe` command to generate Whop checkout links
4. Remove Stripe-related env vars

### Whop Webhook Handler

The webhook server needs to handle:
```python
@app.post("/webhooks/whop")
async def whop_webhook(request: Request):
    # Verify signature
    # Handle membership.went_valid → assign role
    # Handle membership.went_invalid → remove role
    # Handle payment events → log
```
