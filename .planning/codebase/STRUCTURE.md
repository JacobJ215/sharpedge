# Structure

> Directory layout, key file locations, package boundaries, and naming conventions.

---

## Monorepo Layout

```
sharpedge/
├── apps/
│   ├── bot/                        # Discord bot (entry point: main.py)
│   │   └── src/sharpedge_bot/
│   │       ├── agents/             # OpenAI agent wrappers
│   │       ├── commands/           # Discord slash commands (cogs)
│   │       ├── embeds/             # Discord embed builders
│   │       ├── events/             # Discord event handlers
│   │       ├── jobs/               # Background scheduled tasks
│   │       ├── middleware/         # Rate limiting, tier checks
│   │       ├── services/           # Business logic layer
│   │       ├── utils/              # Formatting, math helpers
│   │       ├── bot.py              # Bot setup + cog loading
│   │       ├── config.py           # Env var validation
│   │       └── main.py             # Entry point
│   └── webhook_server/             # FastAPI webhook handler
│       └── src/sharpedge_webhooks/
│           ├── routes/             # Stripe, Whop webhook endpoints
│           ├── config.py
│           └── main.py             # FastAPI app entry point
├── packages/
│   ├── analytics/                  # Pure calculation modules (no I/O)
│   │   └── src/sharpedge_analytics/
│   │       ├── arbitrage.py        # Arbitrage detection
│   │       ├── consensus.py        # Sharp consensus analysis
│   │       ├── key_numbers.py      # NFL/NBA key number zones
│   │       ├── middles.py          # Middle opportunity detection
│   │       ├── movement.py         # Line movement classification
│   │       ├── no_vig.py           # No-vig fair odds
│   │       ├── prediction_markets.py # Kalshi/Polymarket analysis
│   │       ├── public_betting.py   # Public betting % analysis
│   │       ├── rest_travel.py      # Rest days, travel distance
│   │       ├── unified_markets.py  # Cross-market unification
│   │       ├── value_scanner.py    # Value play detection pipeline
│   │       ├── visualizations.py   # Chart generation (896 lines — needs split)
│   │       └── weather.py          # Weather impact
│   ├── data_feeds/                 # External data source clients
│   │   └── src/sharpedge_feeds/
│   │       ├── espn_client.py
│   │       ├── kalshi_client.py
│   │       ├── polymarket_client.py
│   │       ├── public_betting_client.py
│   │       └── weather_client.py
│   ├── database/                   # Supabase client + queries + schema
│   │   └── src/sharpedge_db/
│   │       ├── client.py           # Supabase connection
│   │       ├── models.py           # Pydantic DB models
│   │       ├── migrations/         # Raw SQL migration files (001–005)
│   │       └── queries/            # Domain-scoped query modules
│   │           ├── bets.py
│   │           ├── alerts.py
│   │           ├── arbitrage.py
│   │           ├── consensus.py
│   │           ├── line_movements.py
│   │           ├── odds_history.py
│   │           ├── opening_lines.py
│   │           ├── projections.py
│   │           ├── public_betting.py
│   │           ├── usage.py
│   │           ├── users.py
│   │           └── value_plays.py
│   ├── models/                     # ML models + quant calculators
│   │   └── src/sharpedge_models/
│   │       ├── arbitrage.py        # Arbitrage sizing model
│   │       ├── backtesting.py      # Calibration + walk-forward (stubs present)
│   │       ├── ev_calculator.py    # EV + Bayesian confidence
│   │       ├── ml_inference.py     # Gradient boosting inference
│   │       ├── no_vig.py           # No-vig math
│   │       ├── spreads.py          # Spread prediction model
│   │       └── totals.py           # Totals prediction model
│   ├── odds_client/                # The Odds API wrapper
│   │   └── src/sharpedge_odds/
│   │       ├── cache.py
│   │       ├── client.py
│   │       ├── constants.py        # Sport keys, market types
│   │       └── models.py           # Pydantic response models
│   └── shared/                     # Cross-package types + constants
│       └── src/sharpedge_shared/
│           ├── constants.py
│           ├── errors.py           # Custom exception hierarchy
│           └── types.py            # Shared TypedDicts / dataclasses
├── data/
│   └── raw/
│       ├── nba_betting/            # nba_2008-2025.csv
│       └── nfl_betting/            # spreadspoke_scores.csv, nfl_teams.csv
├── docs/                           # Static documentation
├── scripts/                        # One-off CLI scripts (training, seeding, deploy)
├── pyproject.toml                  # uv workspace root
├── ruff.toml                       # Linter/formatter config
└── docker-compose.yml
```

---

## Package Boundaries

| Package | Imports from | Does NOT import from |
|---------|-------------|---------------------|
| `sharpedge_shared` | nothing | everything |
| `sharpedge_odds` | `sharpedge_shared` | bot, db, analytics |
| `sharpedge_db` | `sharpedge_shared` | bot, analytics, models |
| `sharpedge_feeds` | `sharpedge_shared` | bot, db, analytics |
| `sharpedge_models` | `sharpedge_shared` | bot, db, feeds |
| `sharpedge_analytics` | `sharpedge_shared`, `sharpedge_models` | bot, db |
| `sharpedge_bot` | all packages | webhook_server |
| `sharpedge_webhooks` | `sharpedge_db`, `sharpedge_shared` | bot, analytics |

---

## Naming Conventions

- **Packages**: `sharpedge_<domain>` (snake_case)
- **Modules**: `<noun>.py` (e.g., `ev_calculator.py`, `movement.py`)
- **Classes**: PascalCase (e.g., `EVCalculator`, `ArbitrageDetector`)
- **Functions**: snake_case (e.g., `calculate_ev`, `detect_steam_move`)
- **Constants**: SCREAMING_SNAKE_CASE (e.g., `NFL_KEY_NUMBERS`)
- **DB query files**: domain-scoped noun (e.g., `bets.py`, `users.py`)
- **Commands**: verb/noun Discord cogs (e.g., `analysis.py`, `bankroll.py`)
- **Jobs**: `<noun>_job.py` or `<verb>_<noun>.py` (e.g., `value_scanner_job.py`, `arbitrage_scanner.py`)

---

## Key Entry Points

| Entry Point | Path |
|-------------|------|
| Discord bot | `apps/bot/src/sharpedge_bot/main.py` |
| Webhook server | `apps/webhook_server/src/sharpedge_webhooks/main.py` |
| Model training | `scripts/train_models.py` |
| Schema deploy | `scripts/deploy_schema.py` |
| Data ingestion | `scripts/download_historical_data.py` |
