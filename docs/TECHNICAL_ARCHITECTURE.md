# SharpEdge Technical Architecture

## Overview

SharpEdge is a Python monorepo built with `uv` workspaces. The architecture follows a modular design with clear separation between the Discord interface, business logic, data layer, and external integrations.

---

## Repository Structure

```
sharpedge/
├── pyproject.toml              # Root workspace configuration
├── .python-version             # Python 3.12+
├── .env.example                # Environment variable template
├── ruff.toml                   # Linting configuration
├── docker-compose.yml          # Local Redis for development
│
├── apps/
│   ├── bot/                    # Discord bot application
│   │   ├── pyproject.toml
│   │   └── src/sharpedge_bot/
│   │       ├── main.py         # Entry point
│   │       ├── config.py       # Environment configuration
│   │       ├── bot.py          # Bot class, cog loading
│   │       ├── commands/       # Slash command cogs
│   │       ├── events/         # Discord event handlers
│   │       ├── agents/         # AI agents (OpenAI Agents SDK)
│   │       ├── services/       # Business logic layer
│   │       ├── middleware/     # Rate limiting, tier checks
│   │       ├── jobs/           # Background schedulers
│   │       ├── embeds/         # Discord embed builders
│   │       └── utils/          # Helpers, formatters
│   │
│   └── webhook_server/         # Payment webhook handler
│       ├── pyproject.toml
│       └── src/sharpedge_webhooks/
│           ├── main.py         # FastAPI entry point
│           └── handlers/       # Whop webhook handlers
│
├── packages/
│   ├── analytics/              # Pure analytics calculations
│   │   ├── pyproject.toml
│   │   └── src/sharpedge_analytics/
│   │       ├── no_vig.py       # Fair odds calculation
│   │       ├── consensus.py    # Market consensus
│   │       ├── arbitrage.py    # Arb detection
│   │       ├── middles.py      # Middle finder
│   │       ├── key_numbers.py  # NFL/NBA key numbers
│   │       ├── movement.py     # Line movement classification
│   │       ├── value_scanner.py# +EV detection
│   │       ├── weather.py      # Weather impact
│   │       ├── rest_travel.py  # Schedule advantages
│   │       ├── public_betting.py# Sharp money analysis
│   │       ├── prediction_markets.py # PM arbitrage
│   │       ├── unified_markets.py   # Cross-platform analytics
│   │       └── visualizations.py    # Chart generation
│   │
│   ├── database/               # Data access layer
│   │   ├── pyproject.toml
│   │   └── src/sharpedge_db/
│   │       ├── client.py       # Supabase client singleton
│   │       ├── models.py       # Pydantic data models
│   │       ├── queries/        # Database query modules
│   │       └── migrations/     # SQL schema files
│   │
│   ├── odds_client/            # The Odds API client
│   │   ├── pyproject.toml
│   │   └── src/sharpedge_odds/
│   │       ├── client.py       # API client
│   │       ├── models.py       # Response models
│   │       ├── cache.py        # Redis caching
│   │       └── constants.py    # Sport keys, markets
│   │
│   ├── data_feeds/             # External data clients
│   │   ├── pyproject.toml
│   │   └── src/sharpedge_feeds/
│   │       ├── weather_client.py    # WeatherAPI
│   │       ├── espn_client.py       # ESPN API
│   │       ├── public_betting_client.py
│   │       ├── kalshi_client.py     # Kalshi API
│   │       └── polymarket_client.py # Polymarket API
│   │
│   └── shared/                 # Shared types and utilities
│       ├── pyproject.toml
│       └── src/sharpedge_shared/
│           ├── types.py        # Enums, type definitions
│           ├── constants.py    # Rate limits, thresholds
│           └── errors.py       # Custom exceptions
│
├── scripts/
│   ├── deploy_schema.py        # Print SQL for deployment
│   ├── register_commands.py    # Force command sync
│   └── seed_data.py            # Test data seeding
│
├── tests/                      # Test suite
│
└── docs/                       # Documentation
    ├── FEATURE_OVERVIEW.md
    ├── PITCH_DECK.md
    ├── TECHNICAL_ARCHITECTURE.md
    └── USER_GUIDE.md
```

---

## Package Dependencies

```
sharpedge (root workspace)
├── sharpedge-bot (apps/bot)
│   ├── sharpedge-analytics
│   ├── sharpedge-db
│   ├── sharpedge-odds
│   ├── sharpedge-feeds
│   ├── sharpedge-shared
│   ├── discord.py
│   ├── openai-agents
│   ├── apscheduler
│   └── redis
│
├── sharpedge-webhooks (apps/webhook_server)
│   ├── sharpedge-db
│   ├── sharpedge-shared
│   ├── fastapi
│   └── uvicorn
│
├── sharpedge-analytics (packages/analytics)
│   ├── sharpedge-shared
│   ├── numpy
│   ├── scipy
│   └── matplotlib
│
├── sharpedge-db (packages/database)
│   ├── sharpedge-shared
│   ├── supabase
│   └── pydantic
│
├── sharpedge-odds (packages/odds_client)
│   ├── sharpedge-shared
│   ├── httpx
│   └── redis
│
├── sharpedge-feeds (packages/data_feeds)
│   ├── sharpedge-shared
│   └── httpx
│
└── sharpedge-shared (packages/shared)
    └── pydantic
```

---

## Core Components

### 1. Discord Bot (`apps/bot`)

The main user interface, built with discord.py 2.x.

#### Entry Point (`main.py`)
```python
async def main():
    config = BotConfig()
    bot = SharpEdgeBot(config)
    await bot.start(config.discord_bot_token)
```

#### Bot Class (`bot.py`)
- Initializes intents and activity
- Loads all command cogs in `setup_hook()`
- Syncs slash commands to guild
- Starts background scheduler

#### Command Cogs (`commands/`)
Each file is a discord.py Cog with related commands:

| Cog | Commands |
|-----|----------|
| `betting.py` | `/bet`, `/result`, `/pending`, `/history` |
| `stats.py` | `/stats` |
| `bankroll.py` | `/bankroll`, `/kelly` |
| `lines.py` | `/lines` |
| `subscription.py` | `/subscribe`, `/tier`, `/manage` |
| `analysis.py` | `/analyze`, `/movement` |
| `review.py` | `/review`, `/review-week` |
| `value.py` | `/value`, `/arb`, `/sharp` |
| `market.py` | `/consensus`, `/steam`, `/fade` |
| `prediction_markets.py` | `/pm-arb`, `/pm-markets`, `/pm-compare` |
| `research.py` | `/research`, `/breakdown`, `/trends`, `/chart-*` |

#### Middleware (`middleware/`)

**Rate Limiter** (`rate_limiter.py`):
```python
@rate_limited(requests=10, window=60)
async def some_command(interaction):
    ...
```

**Tier Check** (`tier_check.py`):
```python
@require_tier(Tier.PRO)
async def pro_only_command(interaction):
    ...
```

#### Background Jobs (`jobs/`)

Scheduled with APScheduler:

| Job | Frequency | Purpose |
|-----|-----------|---------|
| `opening_lines.py` | 30 min | Capture first odds |
| `odds_monitor.py` | 5 min | Track movements |
| `consensus_calc.py` | 5 min | Aggregate consensus |
| `value_scanner_job.py` | 5 min | Find +EV plays |
| `arbitrage_scanner.py` | 5 min | Detect arbs |
| `alert_dispatcher.py` | 5 min | Send notifications |
| `prediction_market_scanner.py` | 2 min | PM arb detection |

#### AI Agents (`agents/`)

Built with OpenAI Agents SDK:

**Game Analyst** (`game_analyst.py`):
- Analyzes matchups and provides comprehensive breakdowns
- Uses 5 tools for real-time data retrieval
- Model: gpt-5-mini (cost-efficient, accurate)

**Review Agent** (`review_agent.py`):
- Analyzes user betting history with CLV tracking
- Provides personalized, actionable feedback
- Model: gpt-5-mini (balanced reasoning)

**Research Agent** (`research_agent.py`):
- Deep research queries with multi-source analysis
- 8 specialized tools for comprehensive research
- Model: gpt-5-mini (advanced reasoning)

---

### 2. Analytics Engine (`packages/analytics`)

Pure Python calculations with no side effects. Stateless and testable.

#### Key Modules

**no_vig.py** - Fair odds calculation:
```python
def calculate_no_vig_odds(odds_a: int, odds_b: int) -> NoVigResult:
    """Remove vig to get true probabilities."""
    # Convert to implied probabilities
    # Normalize to remove margin
    # Return fair odds for both sides
```

**arbitrage.py** - Arbitrage detection:
```python
def find_arbitrage(odds_a: int, odds_b: int) -> ArbitrageResult:
    """Check if arbitrage exists between two odds."""
    # If combined implied < 100%, arb exists
    # Calculate optimal stake allocation
    # Return profit percentage
```

**value_scanner.py** - Value detection:
```python
def scan_for_value(
    games: list[Game],
    projections: dict[str, float],
    min_ev: float = 2.0,
) -> list[ValuePlay]:
    """Find bets with positive expected value."""
```

**visualizations.py** - Chart generation:
```python
def create_line_movement_chart(
    timestamps: list[datetime],
    lines: list[float],
    team_name: str,
    opening_line: float,
    consensus_line: float,
    key_numbers: list[float],
) -> bytes:
    """Generate PNG chart bytes for Discord."""
```

**prediction_markets.py** - PM analytics:
```python
def find_cross_platform_arbitrage(
    kalshi_markets: list[dict],
    polymarket_markets: list[dict],
) -> list[PredictionMarketArbitrage]:
    """Find arb between Kalshi and Polymarket."""
```

---

### 3. Database Layer (`packages/database`)

Supabase (PostgreSQL) with Pydantic models.

#### Client (`client.py`)
```python
_client: Client | None = None

def get_supabase_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(url, key)
    return _client
```

#### Models (`models.py`)
```python
class Bet(BaseModel):
    id: UUID
    user_id: str
    sport: str
    game: str
    bet_type: str
    selection: str
    odds: int
    units: Decimal
    stake: Decimal
    potential_win: Decimal
    result: BetResult
    profit: Decimal | None
    clv_points: Decimal | None
    created_at: datetime
```

#### Query Modules (`queries/`)

Organized by entity:
- `users.py` - User CRUD
- `bets.py` - Bet tracking, performance
- `value_plays.py` - Value play storage
- `line_movements.py` - Movement history
- `arbitrage.py` - Arb opportunities
- etc.

#### Migrations (`migrations/`)

Three migration files:
1. `001_initial_schema.sql` - Core tables (users, bets, usage, alerts)
2. `002_analytics_tables.sql` - Analytics tables
3. `003_prediction_markets.sql` - PM tables

---

### 4. External Clients

#### Odds Client (`packages/odds_client`)

```python
class OddsClient:
    async def get_odds(
        self,
        sport: str,
        markets: list[str] = ["spreads", "totals", "h2h"],
    ) -> list[Game]:
        """Fetch odds from The Odds API with caching."""
```

Features:
- Redis caching (5 min TTL)
- Automatic rate limiting
- Response parsing to models

#### Data Feeds (`packages/data_feeds`)

**Kalshi Client**:
```python
class KalshiClient:
    async def get_markets(self, event_ticker: str) -> list[KalshiMarket]:
        """Fetch markets with RSA-signed requests."""
```

**Polymarket Client**:
```python
class PolymarketClient:
    async def get_markets(self, query: str) -> list[PolymarketMarket]:
        """Search Polymarket via Gamma API."""
```

---

## Data Flow

### Command Flow

```
User types /lines Chiefs Raiders
         │
         ▼
┌─────────────────────────────┐
│    Discord Gateway          │
│    (discord.py receives)    │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│    Tier Check Middleware    │
│    (verify user tier)       │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│    Rate Limit Middleware    │
│    (check Redis counter)    │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│    LinesCog.lines_command   │
│    (business logic)         │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│    OddsService.get_lines    │
│    (orchestration)          │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│    OddsClient.get_odds      │
│    (API call + cache)       │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│    Analytics Engine         │
│    (no_vig, consensus, etc.)│
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│    EmbedBuilder             │
│    (format response)        │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│    interaction.response     │
│    (send to Discord)        │
└─────────────────────────────┘
```

### Background Job Flow

```
APScheduler triggers value_scanner (every 5 min)
         │
         ▼
┌─────────────────────────────┐
│    Fetch current odds       │
│    (OddsClient)             │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│    Load model projections   │
│    (Supabase)               │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│    Scan for value           │
│    (Analytics: scan_for_value)│
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│    Store value plays        │
│    (Supabase)               │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│    Queue alerts             │
│    (Supabase alerts table)  │
└─────────────────────────────┘
         │
         ▼
alert_dispatcher runs (every 5 min)
         │
         ▼
┌─────────────────────────────┐
│    Fetch pending alerts     │
│    Filter by user tier      │
│    Send to Discord channels │
└─────────────────────────────┘
```

---

## Configuration

### Environment Variables

```python
class BotConfig(BaseSettings):
    # Discord
    discord_bot_token: str
    discord_client_id: str
    discord_guild_id: str

    # Database
    supabase_url: str
    supabase_key: str

    # Redis
    redis_url: str

    # APIs
    odds_api_key: str
    openai_api_key: str

    # Payments
    whop_api_key: str
    whop_webhook_secret: str
    whop_pro_product_id: str
    whop_sharp_product_id: str

    # Roles
    free_role_id: str
    pro_role_id: str
    sharp_role_id: str

    # Channels
    value_alerts_channel_id: str
    line_movement_channel_id: str

    # Optional
    kalshi_api_key: str | None = None
    kalshi_private_key: str | None = None
    polymarket_api_key: str | None = None
    weather_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env")
```

---

## Error Handling

### Custom Exceptions (`sharpedge_shared/errors.py`)

```python
class SharpEdgeError(Exception):
    """Base exception for all SharpEdge errors."""

class RateLimitExceeded(SharpEdgeError):
    """User exceeded rate limit."""

class TierRestricted(SharpEdgeError):
    """Feature requires higher tier."""

class ExternalAPIError(SharpEdgeError):
    """External API call failed."""

class DatabaseError(SharpEdgeError):
    """Database operation failed."""
```

### Error Handling Pattern

```python
@app_commands.command(name="value")
@require_tier(Tier.PRO)
async def value_command(self, interaction: discord.Interaction):
    try:
        plays = get_active_value_plays()
        embed = build_value_embed(plays)
        await interaction.response.send_message(embed=embed)
    except RateLimitExceeded:
        await interaction.response.send_message(
            "Rate limit exceeded. Please wait.",
            ephemeral=True
        )
    except ExternalAPIError as e:
        logger.exception("API error in value command")
        await interaction.response.send_message(
            f"External service error: {e}",
            ephemeral=True
        )
    except Exception as e:
        logger.exception("Unexpected error in value command")
        await interaction.response.send_message(
            "An unexpected error occurred.",
            ephemeral=True
        )
```

---

## Testing Strategy

### Unit Tests

Test analytics functions in isolation:
```python
def test_calculate_no_vig_odds():
    result = calculate_no_vig_odds(-110, -110)
    assert result.fair_prob_a == 0.5
    assert result.fair_prob_b == 0.5
    assert result.vig_percentage == pytest.approx(4.76, 0.01)
```

### Integration Tests

Test with mocked external services:
```python
async def test_get_odds_with_cache(mock_redis, mock_odds_api):
    client = OddsClient(mock_redis, mock_odds_api)

    # First call hits API
    games = await client.get_odds("americanfootball_nfl")
    assert mock_odds_api.called

    # Second call hits cache
    mock_odds_api.reset_mock()
    games = await client.get_odds("americanfootball_nfl")
    assert not mock_odds_api.called
```

### End-to-End Tests

Test full command flow:
```python
async def test_lines_command(bot, test_guild):
    # Simulate user interaction
    interaction = MockInteraction(user=test_user, guild=test_guild)

    await bot.cogs["LinesCog"].lines_command(
        interaction, "Chiefs", "Raiders"
    )

    # Verify response
    assert interaction.response.sent
    assert "Chiefs" in interaction.response.embed.title
```

---

## Deployment

### Development

```bash
# Install dependencies
uv sync

# Start Redis
docker compose up -d

# Run bot
uv run sharpedge-bot

# Run webhook server (separate terminal)
uv run sharpedge-webhooks
```

### Production (Railway)

Two services:
1. **Bot**: `uv run sharpedge-bot`
2. **Webhooks**: `uv run sharpedge-webhooks`

Environment variables set in Railway dashboard.

### Monitoring

- **Logs**: Railway provides log streaming
- **Errors**: Sentry integration (optional)
- **Metrics**: Custom Discord status showing uptime

---

## Security Considerations

### Secrets Management

- All secrets in environment variables
- Never commit `.env` files
- Use Supabase service role key (server-side only)

### Discord Security

- Verify webhook signatures
- Rate limit all commands
- Tier checks on sensitive commands
- No direct user input in SQL

### API Security

- RSA signing for Kalshi requests
- API keys never exposed to clients
- Redis authentication enabled

---

## Performance Optimization

### Caching Strategy

| Data | Cache Location | TTL |
|------|---------------|-----|
| Odds | Redis | 5 minutes |
| User tier | Redis | 10 minutes |
| Rate limits | Redis | Per window |
| Consensus | Redis | 5 minutes |

### Database Optimization

- Indexes on frequently queried columns
- Pagination for large result sets
- Background jobs batch operations

### API Efficiency

- Batch odds requests where possible
- Parallel requests for independent data
- Exponential backoff on failures
