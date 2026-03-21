# External Integrations

**Analysis Date:** 2026-03-21

## APIs & External Services

**Discord:**
- **discord.py** bot — Commands, roles, channels; config in `apps/bot/src/sharpedge_bot/config.py` (`discord_bot_token`, `discord_client_id`, `discord_guild_id`, role/channel IDs).
- **Discord REST** — Webhook server uses bot token + guild for social/alert flows (`apps/webhook_server/src/sharpedge_webhooks/config.py`, `discord_bot_token`, `discord_guild_id`).

**LLM / agents:**
- **OpenAI** — API key and model names in bot config (`openai_api_key`, `openai_default_model`, `openai_research_model` in `apps/bot/src/sharpedge_bot/config.py`); webhook server exposes copilot-related routes with optional `openai_api_key` in `WebhookConfig`.
- **LangChain OpenAI + LangGraph** — Agent pipeline package (`packages/agent_pipeline/pyproject.toml`) for graph orchestration and structured outputs; checkpointing via **langgraph-checkpoint-postgres** (Supabase-compatible Postgres).

**Sports odds:**
- **The Odds API** — HTTP client in `packages/odds_client/src/sharpedge_odds/client.py`; API key `odds_api_key` / `ODDS_API_KEY` (`.env.example`, bot config). Optional Redis-backed cache in `OddsClient`.

**Prediction markets:**
- **Kalshi** — REST + WebSocket clients (`packages/data_feeds/src/sharpedge_feeds/kalshi_client.py`, `kalshi_stream.py`); RSA-PSS signing; env: `KALSHI_API_KEY`, `KALSHI_PRIVATE_KEY`, trading flags in bot config (`kalshi_live_trading`, bankroll limits).
- **Polymarket** — REST + WebSocket (`packages/data_feeds/src/sharpedge_feeds/polymarket_client.py`, `polymarket_stream.py`); env: `POLYMARKET_API_KEY`, `POLYMARKET_API_SECRET`, `POLYMARKET_PASSPHRASE`.

**Data enrichment & public data:**
- **WeatherAPI** — `WEATHER_API_KEY` (`.env.example`); weather client in `packages/data_feeds` (see `sharpedge_feeds.weather_client`).
- **SportsData.io** — `SPORTSDATA_API_KEY` in `.env.example` / bot config.
- **ESPN** (unofficial HTTP usage) — `packages/data_feeds/src/sharpedge_feeds/espn_client.py`.
- **Action Network** — Optional `ACTION_NETWORK_API_KEY` in `packages/data_feeds/src/sharpedge_feeds/public_betting_client.py`.
- **CoinGecko** — `packages/data_feeds/src/sharpedge_feeds/coingecko_client.py`.
- **FEC** / **BLS** — `fec_client.py`, `bls_client.py` under `packages/data_feeds/src/sharpedge_feeds/`.

**Social / marketing:**
- **Twitter API** (legacy-style keys) — `WebhookConfig`: `twitter_api_key`, `twitter_api_secret`, `twitter_access_token`, `twitter_access_token_secret`.
- **Instagram Graph API** — `instagram_access_token`, `instagram_account_id`, `instagram_account_handle` in `apps/webhook_server/src/sharpedge_webhooks/config.py`.

**Community / research:**
- **Reddit (PRAW)** — `praw` dependency in `packages/trading_swarm/pyproject.toml` for swarm-related ingestion.

**Payments & monetization:**
- **Whop** — Primary checkout and membership validation; HTTP to `api.whop.com` in `apps/bot/src/sharpedge_bot/services/subscription_service.py`; Discord `/subscribe` flow in `apps/bot/src/sharpedge_bot/commands/subscription.py`. Webhook routes under `apps/webhook_server/src/sharpedge_webhooks/routes/whop.py` (registered in `main.py`). Env: `WHOP_API_KEY`, `WHOP_WEBHOOK_SECRET`, product IDs, `WHOP_COMPANY_SLUG` (see `.env.example` and `WebhookConfig`).
- **RevenueCat** — Mobile IAP webhooks: `POST /webhooks/revenuecat` in `apps/webhook_server/src/sharpedge_webhooks/routes/revenuecat.py`; verification via `REVENUECAT_WEBHOOK_SECRET` (Authorization header). Tests in `apps/webhook_server/tests/test_revenuecat.py`.
- **Stripe** — Legacy: optional router `apps/webhook_server/src/sharpedge_webhooks/routes/stripe.py` (import guarded in `main.py`); dependencies remain in `apps/webhook_server` and `apps/bot` for migration. Env placeholders commented in `.env.example`.

## Data Storage

**Databases:**
- **Supabase (Postgres)** — Primary datastore and auth. Python client usage via `sharpedge-db` (`packages/database/pyproject.toml`, `supabase>=2.0`). SQL migrations versioned in `packages/database/src/sharpedge_db/migrations/` (e.g. `001_initial_schema.sql` through `008_auth_bridge.sql`, `007_trading_swarm.sql`).
- **Connection config** — `SUPABASE_URL`, `SUPABASE_KEY` / service role variants (bot: `apps/bot/src/sharpedge_bot/config.py`; webhooks: `WebhookConfig`; web: `NEXT_PUBLIC_*` in `apps/web/src/lib/supabase.ts`).

**File / object storage:**
- **Supabase Storage** — Bucket name default `social-cards` (`supabase_storage_bucket` in `WebhookConfig`) for generated social images.

**Caching:**
- **Redis** — `REDIS_URL` (`.env.example` suggests Upstash); used by bot config and odds caching (`packages/odds_client`).

## Authentication & Identity

**Auth provider:**
- **Supabase Auth** — Web uses SSR/browser clients (`apps/web/src/lib/supabase.ts`, `apps/web/src/lib/supabase-server.ts`, middleware in `apps/web/src/middleware.ts`, routes under `apps/web/src/app/auth/`).
- **Mobile** — `supabase_flutter` in `apps/mobile/pubspec.yaml`; ties to same Supabase project as web/backend.
- **Tier / JWT claims** — Database migrations and webhook handlers (Whop + RevenueCat) sync subscription tier into `public.users` and Supabase Auth metadata (see `008_auth_bridge.sql` and webhook route modules).

**Discord identity:**
- Bot resolves users by Discord ID for Whop checkout links and role management (`subscription_service`, user queries in `sharpedge_db`).

## Monitoring & Observability

**Error tracking:**
- Not a dedicated third-party error SaaS in code scan; logging via standard library `logging` modules (e.g. `sharpedge.webhooks`, `sharpedge.services.subscription`).

**Logs:**
- Python services rely on structured loggers; Docker images set `PYTHONUNBUFFERED=1` for immediate stdout.

## CI/CD & Deployment

**Hosting:**
- Not specified in-repo; Next.js app is deployable to any Node host. No `vercel.json` found in snapshot.

**CI pipeline:**
- **No `.github/workflows`** detected under `/Users/revph/sharpedge` at analysis time — CI may live outside this tree or be added later.

**Containers:**
- Three Dockerfiles for long-running Python workers (`packages/trading_swarm/Dockerfile`, `packages/value_scanner/Dockerfile`, `packages/arb_stream/Dockerfile`) copying selective `packages/*/src` and scripts from `scripts/`.

## Environment Configuration

**Required env vars (typical production):**
- Discord: `DISCORD_BOT_TOKEN`, `DISCORD_CLIENT_ID`, `DISCORD_GUILD_ID` (and role/channel IDs as used).
- Supabase: `SUPABASE_URL`, service-capable key for server (`SUPABASE_KEY` / `SUPABASE_SERVICE_KEY` pattern in webhook config).
- OpenAI: `OPENAI_API_KEY` where agents/copilot enabled.
- Odds: `ODDS_API_KEY` for line data.
- Redis: `REDIS_URL`.
- Whop: `WHOP_API_KEY`, `WHOP_WEBHOOK_SECRET`, product IDs, `WHOP_COMPANY_SLUG`.
- RevenueCat: `REVENUECAT_WEBHOOK_SECRET` for webhook verification.
- Optional: Kalshi/Polymarket, weather/sportsdata keys, Firebase JSON string `firebase_service_account_json`, Twitter/Instagram keys for social automation.

**Secrets location:**
- Local: `.env` at repo root (never commit). Template without secrets: `.env.example`.
- Production: host/platform secret stores (not defined in repository).

## Webhooks & Callbacks

**Incoming (FastAPI app in `apps/webhook_server`):**
- **Whop** — Subscription lifecycle → tier sync (`routes/whop.py`).
- **RevenueCat** — IAP events → tier sync (`routes/revenuecat.py`, prefix `/webhooks/revenuecat`).
- **Stripe** (optional/legacy) — `routes/stripe.py` if installed.
- **Mobile-specific** and **v1 API** routers registered in `apps/webhook_server/src/sharpedge_webhooks/main.py` (e.g. `routes/mobile.py`, `routes/v1/*` for bankroll, copilot, markets, portfolio, swarm, value plays, notifications).

**Outgoing:**
- Bot and jobs post to Discord channels (alert channel IDs in config).
- Whop checkout URLs are user-facing redirects (`https://whop.com/...` built in `subscription_service.py`).
- HTTP clients (`httpx`) call external APIs listed above from bot, webhooks, feeds, and trading packages.

---

*Integration audit: 2026-03-21*
