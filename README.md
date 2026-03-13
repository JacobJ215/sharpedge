# SharpEdge

SharpEdge is a Python monorepo for a Discord-first sports betting intelligence platform. It combines a Discord bot, a webhook server, analytics packages, database access, and external data-feed clients in a single `uv` workspace.

## What It Includes

- Discord bot for betting workflows, stats, bankroll tools, line movement, value plays, arbitrage, and research commands
- Webhook server for subscription and payment-related events
- Analytics packages for fair odds, consensus, arbitrage, prediction markets, weather, and market movement
- Database package with migrations and query modules
- Data feed clients for odds, ESPN, weather, Kalshi, Polymarket, and public betting sources

## Repository Layout

```text
sharpedge/
├── apps/
│   ├── bot/               # Discord bot application
│   └── webhook_server/    # FastAPI webhook service
├── packages/
│   ├── analytics/         # Pure analytics calculations
│   ├── data_feeds/        # External data clients
│   ├── database/          # DB client, models, queries, migrations
│   ├── models/            # Betting and ML-related models
│   ├── odds_client/       # Odds API client and caching
│   └── shared/            # Shared types, constants, errors
├── data/                  # Local source data
├── docs/                  # Product and architecture docs
└── scripts/               # Utility scripts for schema, training, seeding
```

## Requirements

- Python 3.12+
- `uv`
- Docker Desktop or a local Redis instance for development
- Accounts or API keys for the services you plan to use

## Quick Start

1. Install `uv` if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Create your environment file:

```bash
cp .env.example .env
```

3. Install the workspace dependencies:

```bash
uv sync
```

4. Start Redis locally:

```bash
docker compose up -d
```

5. Fill in the required values in `.env`.

At minimum, local development typically needs:

- `DISCORD_BOT_TOKEN`
- `DISCORD_CLIENT_ID`
- `DISCORD_GUILD_ID`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `OPENAI_API_KEY`
- `ODDS_API_KEY`
- `REDIS_URL`

## Running The Services

Run the Discord bot:

```bash
uv run sharpedge-bot
```

Run the webhook server:

```bash
uv run sharpedge-webhooks
```

The webhook server uses `WEBHOOK_PORT`, which defaults to `8000` in `.env.example`.

## Useful Development Commands

Lint the repo:

```bash
uv run ruff check .
```

Run tests:

```bash
uv run pytest
```

Print schema deployment SQL:

```bash
uv run python scripts/deploy_schema.py
```

Seed local or test data:

```bash
uv run python scripts/seed_data.py
```

## Environment Notes

`.env.example` includes configuration for:

- Discord bot and guild setup
- Supabase
- OpenAI models
- The Odds API
- Redis
- Whop product and webhook settings
- Optional prediction market integrations
- Optional weather and sports data providers

Do not commit a populated `.env`.

## Documentation

- `docs/FEATURE_OVERVIEW.md`
- `docs/TECHNICAL_ARCHITECTURE.md`
- `docs/USER_GUIDE.md`
- `docs/PITCH_DECK.md`

## Status

This repository is now initialized on GitHub with `main` tracking `origin/main`.
