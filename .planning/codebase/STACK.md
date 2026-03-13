# Technology Stack

**Analysis Date:** 2026-03-13

## Languages

**Primary:**
- Python 3.12 - All backend services, Discord bot, webhook server, data processing

**Secondary:**
- YAML - Configuration files for Claude agents and claude-flow
- TOML - Project configuration (pyproject.toml, ruff.toml)

## Runtime

**Environment:**
- Python 3.12 (configured in `.python-version`)

**Package Manager:**
- UV (modern Python package manager)
- Lockfile: Managed by UV workspace at root level

## Frameworks

**Core:**
- FastAPI 0.115+ - HTTP framework for webhook server (`/apps/webhook_server`)
- discord.py 2.0+ - Discord bot framework (`/apps/bot`)
- APScheduler 3.10+ - Background job scheduling for odds monitoring and alerts

**API Client:**
- httpx 0.27+ - Async HTTP client for external API calls (odds, Discord, Whop)
- openai-agents 0.0.7+ - OpenAI agent framework for research agent integration

**Database:**
- Supabase 2.0+ - PostgreSQL database client and abstraction layer (`packages/database`)

**Data/Analytics:**
- NumPy 1.26+/2.0+ - Numerical computing (`packages/analytics`, `packages/models`)
- SciPy 1.14+ - Scientific computing and statistical functions (`packages/analytics`)
- scikit-learn 1.5+ - Machine learning models (`packages/models`)
- Matplotlib 3.8+ - Data visualization (`packages/analytics`)

**Configuration:**
- pydantic 2.0+ - Data validation and settings management (across all packages)
- pydantic-settings 2.0+ - Environment-based configuration loader

**Payment Processing:**
- stripe 11.0+ - Legacy Stripe payment integration (deprecated, kept for migration)
- Whop (via webhook handling) - Primary payment provider, integrated via webhook server

**Caching:**
- redis 5.0+ - In-memory cache and session store (`packages/odds_client`)

## Key Dependencies

**Critical:**
- discord.py - Core bot functionality; enables Discord integration
- supabase - Primary database interface; used across all data operations
- httpx - All external API communication (async-first)
- FastAPI + uvicorn - Webhook server for payment events

**Infrastructure:**
- APScheduler - Background job orchestration for monitoring jobs
- redis - Odds caching (see `packages/odds_client/cache.py`)
- pydantic - Input validation at system boundaries

**Analytics & Modeling:**
- NumPy/SciPy - Statistical calculations for line movement analysis, value detection
- scikit-learn - Predictive models for EV calculation and betting recommendations
- Matplotlib - Visualization for analysis reports

## Configuration

**Environment:**
- `.env` file (not committed; `.env.example` provides template)
- Configuration classes use Pydantic BaseSettings:
  - `BotConfig` in `apps/bot/src/sharpedge_bot/config.py` - Bot settings
  - `WebhookConfig` in `apps/webhook_server/src/sharpedge_webhooks/config.py` - Webhook settings
- Environment variables are the primary configuration mechanism (see **Key Env Vars** in INTEGRATIONS.md)

**Build:**
- `ruff.toml` - Code linting and formatting configuration
  - Target version: Python 3.12
  - Line length: 100 characters
  - Rules: pycodestyle, pyflakes, isort, flake8 variants, ruff-specific checks
  - Quote style: double quotes
  - Indent: 4 spaces

**Development:**
- `pyproject.toml` (root) - UV workspace configuration with members pointing to `apps/*` and `packages/*`
- Individual `pyproject.toml` files in each package declare dependencies and build metadata

## Testing Framework

**Runner:**
- pytest 8.0+ - Test framework
- pytest-asyncio 0.24+ - Async test support
- pytest-mock 3.14+ - Mocking utilities

**Command:**
- `npm test` - Runs test suite (defined in package scripts)
- Note: Project uses Python with npm convention for consistency

## Platform Requirements

**Development:**
- Python 3.12
- Redis instance (for caching odds data)
- Supabase project (database)
- Discord Bot application token
- OpenAI API key (optional, for agent features)

**Production:**
- Python 3.12 runtime
- Redis (persistent storage recommended)
- Supabase (managed PostgreSQL)
- Docker support (docker-compose.yml present for Redis)

## Code Quality Tools

**Linting & Formatting:**
- Ruff (unified linter/formatter)
  - Selected rules: E, W, F, I, N, UP, B, SIM, T20, TCH, RUF
  - Ignores: E501 (line length handled by formatter)
  - First-party packages configured for import grouping: sharpedge_bot, sharpedge_webhooks, sharpedge_db, sharpedge_models, sharpedge_odds, sharpedge_shared

**Type Checking:**
- mypy 1.14+ - Static type analysis

---

*Stack analysis: 2026-03-13*
