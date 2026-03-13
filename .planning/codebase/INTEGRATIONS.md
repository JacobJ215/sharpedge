# External Integrations

**Analysis Date:** 2026-03-13

## APIs & External Services

**Discord:**
- Service: Discord bot platform + REST API for role management
  - SDK/Client: discord.py 2.0+
  - Auth: `DISCORD_BOT_TOKEN` environment variable
  - Endpoints used:
    - Slash commands (primary command interface)
    - Role management API: `POST /guilds/{guild_id}/members/{user_id}/roles/{role_id}`
    - Member join/leave events
  - Key config: `DISCORD_GUILD_ID`, `DISCORD_CLIENT_ID` (see `apps/bot/src/sharpedge_bot/config.py`)

**Whop (Payment Provider):**
- Service: Subscription and payment management platform (primary payment provider)
  - SDK/Client: HTTP webhooks (via `apps/webhook_server/src/sharpedge_webhooks/routes/whop.py`)
  - Auth: `WHOP_API_KEY`, `WHOP_WEBHOOK_SECRET`
  - Webhook endpoint: `POST /webhooks/whop`
  - Events handled:
    - `membership.went_valid`, `membership.created`, `membership.renewed` - Add Discord role
    - `membership.went_invalid`, `membership.cancelled`, `membership.expired` - Remove Discord role
    - `payment.succeeded` - Log payment to database
    - `payment.failed` - Log failed payment
  - Products:
    - `WHOP_PRO_PRODUCT_ID` - maps to "pro" tier and `PRO_ROLE_ID`
    - `WHOP_SHARP_PRODUCT_ID` - maps to "sharp" tier (includes pro) and `SHARP_ROLE_ID`
  - Implementation: `apps/webhook_server/src/sharpedge_webhooks/routes/whop.py`

**The Odds API:**
- Service: Sports betting odds and market data aggregation
  - SDK/Client: httpx (custom client in `packages/odds_client`)
  - Auth: `ODDS_API_KEY`
  - Caching: Redis (TTL-based, see `packages/odds_client/src/sharpedge_odds/cache.py`)
  - Usage: Fetch current odds, track line movements, detect arbitrage opportunities
  - Supported sports: NFL, NBA, MLB, NHL (configured via constants in `packages/odds_client`)
  - Implementation: `packages/odds_client/src/sharpedge_odds/client.py`

**OpenAI:**
- Service: AI-powered agent framework for research and analysis
  - SDK/Client: openai-agents 0.0.7+
  - Auth: `OPENAI_API_KEY`
  - Models:
    - `OPENAI_DEFAULT_MODEL` (default: gpt-5-mini) - General agent operations
    - `OPENAI_RESEARCH_MODEL` (default: gpt-5-mini) - Research agent tasks
    - Can override to gpt-5 for complex reasoning tasks
  - Usage: Research agent (`apps/bot/src/sharpedge_bot/agents/research_agent.py`), game analysis
  - Implementation: Via `openai-agents` framework with custom tools

**Stripe (Legacy - Deprecated):**
- Service: Payment processing (being phased out in favor of Whop)
  - SDK/Client: stripe 11.0+ (optional)
  - Auth: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
  - Config: `STRIPE_PRO_PRICE_ID`, `STRIPE_SHARP_PRICE_ID`
  - Status: Kept for migration purposes; new subscriptions use Whop
  - Implementation: `apps/webhook_server/src/sharpedge_webhooks/routes/stripe.py` (imported conditionally)

**Prediction Market APIs (Optional):**
- Kalshi
  - Auth: `KALSHI_API_KEY`, `KALSHI_PRIVATE_KEY`
  - Usage: Prediction market data for research
- Polymarket
  - Auth: `POLYMARKET_API_KEY`, `POLYMARKET_API_SECRET`, `POLYMARKET_PASSPHRASE`
  - Usage: Prediction market odds and analysis
- Status: Configured but integration status varies (see config in `apps/bot/src/sharpedge_bot/config.py`)

**Data Enrichment APIs (Optional):**
- Weather API
  - Auth: `WEATHER_API_KEY`
  - Usage: Weather conditions for game analysis
- SportsData API
  - Auth: `SPORTSDATA_API_KEY`
  - Usage: Detailed sports statistics and player data

## Data Storage

**Databases:**
- Supabase (PostgreSQL)
  - Connection: `SUPABASE_URL`, `SUPABASE_KEY` (or `SUPABASE_SERVICE_KEY`)
  - Client: `supabase>=2.0`
  - Tables used:
    - `users` - User profiles, tier information, Discord ID mapping
    - `bets` - Logged user bets with outcomes
    - `payments` - Payment transaction history
    - `alerts` - Line movement and value alerts
    - `odds_history` - Historical odds snapshots
    - `arbitrage` - Detected arbitrage opportunities
    - `line_movements` - Line movement tracking
    - `opening_lines` - Opening line data for analysis
  - ORM/Client: Direct Supabase client (custom queries in `packages/database/src/sharpedge_db/queries/`)
  - Singleton pattern: `get_supabase_client()` in `packages/database/src/sharpedge_db/client.py`

**Caching:**
- Redis 5.0+
  - Connection: `REDIS_URL` (default: `redis://localhost:6379`)
  - Docker compose: Redis 7-alpine service with volume for persistence
  - Usage:
    - Odds data caching with TTL (`packages/odds_client/src/sharpedge_odds/cache.py`)
    - Session management (via discord.py extensions)
  - Enabled in docker-compose.yml with AOF persistence

**File Storage:**
- Local filesystem only (no cloud storage configured)

## Authentication & Identity

**Auth Provider:**
- Discord OAuth (implicit via discord.py bot token)
  - Users authenticate through Discord guild membership
  - Bot manages roles based on Whop subscription status
  - No separate auth system; Discord ID is primary user identifier
  - Implementation: Role-based access control via Discord roles (`PRO_ROLE_ID`, `SHARP_ROLE_ID`, `FREE_ROLE_ID`)

**Token Management:**
- Bot Token: Long-lived Discord bot token
- Webhook Secrets: HMAC-SHA256 signatures for Whop webhooks (verification in `apps/webhook_server/src/sharpedge_webhooks/routes/whop.py`)

## Monitoring & Observability

**Error Tracking:**
- Standard Python logging (no external service configured)
  - Logging configuration: `apps/bot/src/sharpedge_bot/main.py`
  - Log level: DEBUG in development, INFO in production
  - Output: stdout (suitable for container logging)

**Logs:**
- Approach: Python stdlib logging with structured format
  - Format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
  - Handlers: StreamHandler to stdout
  - Suppressed noisy loggers: `discord`, `discord.http`

**Metrics:**
- None configured; API usage tracked from response headers (The Odds API)

## CI/CD & Deployment

**Hosting:**
- Not yet deployed; infrastructure TBD
- Local development and testing

**CI Pipeline:**
- None configured (no GitHub Actions or similar)
- Build tools: Ruff for linting, pytest for testing
- Can be run locally: `npm run build`, `npm test`, `npm run lint`

**Containerization:**
- Docker support present (docker-compose.yml for Redis)
- No application Docker image defined yet

## Environment Configuration

**Required env vars:**

**Critical (must be set):**
- `DISCORD_BOT_TOKEN` - Discord bot authentication
- `DISCORD_GUILD_ID` - Target Discord server
- `DISCORD_CLIENT_ID` - Discord application ID
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` / `SUPABASE_SERVICE_KEY` - Database authentication

**Payment & Subscription:**
- `WHOP_API_KEY` - Whop API access
- `WHOP_WEBHOOK_SECRET` - Webhook signature verification
- `WHOP_PRO_PRODUCT_ID` - Pro tier product ID
- `WHOP_SHARP_PRODUCT_ID` - Sharp tier product ID
- `PRO_ROLE_ID` - Discord role for pro subscribers
- `SHARP_ROLE_ID` - Discord role for sharp subscribers
- `FREE_ROLE_ID` - Discord role for free users (optional)

**Odds & Data:**
- `ODDS_API_KEY` - The Odds API authentication

**AI & Analysis:**
- `OPENAI_API_KEY` - OpenAI API key (optional but required for agent features)
- `OPENAI_DEFAULT_MODEL` - Default model (default: gpt-5-mini)
- `OPENAI_RESEARCH_MODEL` - Research agent model (default: gpt-5-mini)

**Optional (enhancement features):**
- `KALSHI_API_KEY`, `KALSHI_PRIVATE_KEY` - Kalshi prediction markets
- `POLYMARKET_API_KEY`, `POLYMARKET_API_SECRET`, `POLYMARKET_PASSPHRASE` - Polymarket
- `WEATHER_API_KEY` - Weather data enrichment
- `SPORTSDATA_API_KEY` - Sports statistics enrichment

**Redis:**
- `REDIS_URL` - Redis connection (default: `redis://localhost:6379`)

**Channels (Discord):**
- `VALUE_ALERTS_CHANNEL_ID` - Value opportunity alerts
- `LINE_MOVEMENT_CHANNEL_ID` - Line movement notifications
- `ARB_ALERTS_CHANNEL_ID` - Arbitrage opportunity alerts
- `PM_ALERTS_CHANNEL_ID` - Prediction market alerts

**Environment:**
- `ENVIRONMENT` - "development" or "production" (affects log level)
- `NODE_ENV` - Checked for development mode (alternative to ENVIRONMENT)

**Secrets location:**
- `.env` file in project root (not committed)
- `.env.example` provides template
- All secrets must be set before starting bot or webhook server

## Webhooks & Callbacks

**Incoming:**
- Whop Payment Webhooks
  - Endpoint: `POST /webhooks/whop` (webhook server at port configured in `WebhookConfig`)
  - Signature verification: HMAC-SHA256 via `X-Whop-Signature` header
  - Events: membership status changes, payment success/failure
  - Triggers: Discord role updates, user tier updates in database

- Stripe Webhooks (Legacy)
  - Endpoint: `POST /webhooks/stripe` (if Stripe router is loaded)
  - Status: Optional, kept for migration

**Outgoing:**
- Discord REST API calls (role management)
  - Endpoints: Add/remove roles via Discord API
  - Called from Whop webhook handler
  - Authentication: Bot token in Authorization header

- Database writes via Supabase
  - User tier updates on subscription changes
  - Payment logging
  - Bet tracking from Discord commands

- The Odds API calls
  - Regular fetches for current odds (background jobs)
  - Triggered by scheduler jobs in `apps/bot/src/sharpedge_bot/jobs/`

---

*Integration audit: 2026-03-13*
