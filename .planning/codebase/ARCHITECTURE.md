# Architecture

**Analysis Date:** 2026-03-13

## Pattern Overview

**Overall:** Event-driven, layered monorepo with a Discord bot as the primary interface and background job processors handling asynchronous analytics and monitoring.

**Key Characteristics:**
- Modular monorepo using `uv` workspace with strict package boundaries
- Async-first design with APScheduler for background jobs
- Separation of concerns: bot UI, webhook handlers, analytics engines, data feeds, database abstraction
- Hierarchical tier-based access control (FREE → PRO → SHARP)
- Real-time event processing with message queue for alerts

## Layers

**Presentation Layer:**
- Purpose: Discord slash commands and interactive embeds for user interactions
- Location: `apps/bot/src/sharpedge_bot/commands/` and `apps/bot/src/sharpedge_bot/embeds/`
- Contains: Discord command handlers (betting, stats, analysis, lines, market research)
- Depends on: Business logic layer, middleware for auth/tier checks
- Used by: Discord users via slash commands

**Webhook/Events Layer:**
- Purpose: Handle external events (Whop payments, Stripe webhooks, Discord member joins)
- Location: `apps/webhook_server/` and `apps/bot/src/sharpedge_bot/events/`
- Contains: FastAPI routes for payment processors, Discord event handlers
- Depends on: Database layer, shared types
- Used by: External payment processors, Discord gateway

**Business Logic Layer:**
- Purpose: Core service implementations for betting, odds, analysis workflows
- Location: `apps/bot/src/sharpedge_bot/services/` (e.g., `bet_service.py`)
- Contains: User operations, bet tracking, odds caching, subscription management
- Depends on: Data access layer, analytics packages
- Used by: Command handlers, background jobs

**Job Processing/Analytics Layer:**
- Purpose: Background jobs that run on schedules to scan odds, detect value, calculate consensus
- Location: `apps/bot/src/sharpedge_bot/jobs/`
- Contains: Scheduled tasks (value scanner, arbitrage scanner, odds monitor, alert dispatcher)
- Depends on: Data feeds, analytics engines, database
- Used by: APScheduler running every 2-5 minutes

**Analytics/Models Layer:**
- Purpose: Pure computational engines for betting analysis, fair odds, arbitrage detection
- Location: `packages/analytics/` and `packages/models/`
- Contains: Value play detection, no-vig consensus calculation, arbitrage detection, ML inference
- Depends on: Shared types
- Used by: Jobs and services

**Data Feeds Layer:**
- Purpose: Client abstractions for external data sources (ESPN, Odds API, Kalshi, Polymarket, weather)
- Location: `packages/data_feeds/` and `packages/odds_client/`
- Contains: HTTP clients for each feed, caching logic
- Depends on: Shared types and configuration
- Used by: Jobs, analytics, and services

**Database Access Layer:**
- Purpose: Supabase abstraction with query modules organized by domain
- Location: `packages/database/src/sharpedge_db/`
- Contains: Client singleton, models (SQLAlchemy/Pydantic), query modules for bets/users/alerts
- Depends on: Shared types
- Used by: All layers that need persistence

**Shared Layer:**
- Purpose: Constants, enums, and types used across all packages
- Location: `packages/shared/src/sharpedge_shared/`
- Contains: Sport/BetType/Tier enums, error classes, common constants
- Depends on: Nothing
- Used by: All packages

## Data Flow

**User Command Flow:**
1. User executes `/bet` command in Discord
2. `require_tier` middleware decorator intercepts, looks up user tier from database
3. Command handler in `commands/betting.py` receives interaction with user attached
4. Handler calls `bet_service.log_bet()` to record bet
5. Service persists to Supabase via `sharpedge_db.queries.bets`
6. Response embed generated and sent to Discord

**Background Job Flow (Value Scanning):**
1. APScheduler triggers `scan_for_value_plays()` every 5 minutes at :02, :07, :12...
2. Job fetches current odds from Odds API via `odds_client.get_odds(sport)`
3. Data is passed to `scan_for_value_no_vig()` analytics engine
4. Analytics calculates fair probability using no-vig consensus from all books
5. Identifies +EV opportunities by comparing each book to consensus
6. Top plays stored in database table `value_plays`
7. Value alerts queued to `_pending_value_alerts` list
8. Alert dispatcher job (runs at :04, :09, :14...) sends to Discord channels

**Webhook/Payment Flow:**
1. Whop sends POST to `/webhooks/whop` with signature verification
2. FastAPI handler in `routes/whop.py` validates signature
3. Updates user tier in Supabase database
4. Triggers Discord role assignment via bot API
5. Returns 200 OK to Whop

**State Management:**
- Persistent state: Supabase PostgreSQL for users, bets, alerts, odds history
- Cache state: Redis for odds and odds history (via `odds_client.cache`)
- In-memory state: APScheduler job queue, pending alerts list in `value_scanner_job`
- No local state files; all ephemeral data in memory during job runs

## Key Abstractions

**Services (Business Logic):**
- Purpose: Encapsulate domain workflows and delegate to lower layers
- Examples: `bet_service.py` (log/track bets), `alert_service.py` (manage alerts)
- Pattern: Synchronous functions that compose database queries and analytics

**Clients (External Integration):**
- Purpose: Abstract external APIs with consistent async interfaces
- Examples: `OddsClient` (fetch lines), `ESPNClient` (team data), `KalshiClient` (prediction markets)
- Pattern: Async context managers with httpx, implement caching and retry logic

**Cogs (Discord Command Modules):**
- Purpose: Group related Discord commands with shared dependencies
- Examples: `BettingCog`, `AnalysisCog`, `MarketCog`
- Pattern: Inherit from `discord.ext.commands.Cog`, use decorators for slash commands and options

**Jobs (Background Tasks):**
- Purpose: Scheduled analytics workloads that run periodically
- Examples: `odds_monitor`, `value_scanner_job`, `arbitrage_scanner`
- Pattern: Async functions with retry logic, store results in database or in-memory queues

**Query Modules (Database Access):**
- Purpose: Domain-specific database operations organized by entity
- Examples: `sharpedge_db.queries.bets`, `sharpedge_db.queries.users`, `sharpedge_db.queries.alerts`
- Pattern: Functions that return typed Pydantic models or raw rows from Supabase

## Entry Points

**Discord Bot:**
- Location: `apps/bot/src/sharpedge_bot/bot.py`
- Triggers: `uv run sharpedge-bot` (entry point defined in app's pyproject.toml)
- Responsibilities: Initialize Discord intents, load all command cogs, sync slash commands to guild, start APScheduler with all background jobs

**Webhook Server:**
- Location: `apps/webhook_server/src/sharpedge_webhooks/main.py`
- Triggers: `uv run sharpedge-webhooks`
- Responsibilities: Initialize FastAPI app, configure Whop and optional Stripe routers, start uvicorn server on configured port

**Background Jobs:**
- Location: `apps/bot/src/sharpedge_bot/jobs/scheduler.py`
- Triggers: Invoked by bot's `setup_hook()` which calls `start_scheduler(bot)`
- Responsibilities: Register all scheduled jobs with APScheduler, set staggered execution times to avoid thundering herd

## Error Handling

**Strategy:** Try-catch at job and command boundaries; log and continue rather than cascade failures.

**Patterns:**
- Commands: Wrap in try-catch, send error embed to user, log with logger.exception()
- Jobs: Wrap individual sport iterations in try-catch (outer loop continues if one sport fails)
- Database: Return None or empty list on query failure; handle missing data gracefully
- External APIs: Use httpx timeouts (10 seconds default), catch connection errors

**Examples:**
- `scan_for_value_plays()` catches exceptions per sport and logs; if odds_data is None, skips that sport
- Command handlers use `@app_commands.error()` decorator for global error handling
- Middleware decorator catches tier lookup failures and sends user-facing error embed

## Cross-Cutting Concerns

**Logging:**
- Framework: Python's `logging` module with per-module loggers (e.g., `logging.getLogger("sharpedge.jobs.value_scanner")`)
- Format: `[%(levelname)s] %(name)s: %(message)s` with ISO timestamp
- Levels: DEBUG for data flow, INFO for job starts/stops, ERROR for failures

**Validation:**
- Discord command parameters validated via `@app_commands.describe()` and type hints
- Enums (Sport, BetType, Tier) used for closed-set validation
- User input (odds, units) converted to Decimal/float at command boundary
- Database queries assume Supabase enforces schema constraints

**Authentication:**
- Discord OAuth: Implicit via `discord.Interaction.user` for commands
- Tier-based: `require_tier()` decorator checks user.tier hierarchy (FREE < PRO < SHARP)
- Whop webhook: Signature verification in `routes/whop.py` before processing
- Database: Supabase API key in service layer; row-level security not currently used

**Scheduling:**
- Framework: APScheduler AsyncIOScheduler with cron and interval triggers
- Staggered execution: Each job type runs at offset minutes to spread load (e.g., odds :00, consensus :01, value :02)
- Job IDs: Used to replace existing jobs on bot restart

---

*Architecture analysis: 2026-03-13*
