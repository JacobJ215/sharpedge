# Architecture

**Analysis Date:** 2026-03-21

## Pattern Overview

**Overall:** Polyglot monorepo with a **Python-first backend workspace** (uv) and **separate client applications** (Next.js web, Flutter mobile). Domain logic is split into installable Python packages under `packages/`; long-running processes are **apps** (`apps/bot`, `apps/webhook_server`) or **containerized workers** (`docker-compose.yml` → trading swarm, arb stream, value scanner).

**Key Characteristics:**

- **Bounded contexts** map to Python package names (`sharpedge_db`, `sharpedge_analytics`, `sharpedge_trading`, …) rather than a single `src/` tree.
- **Supabase (Postgres)** is the system of record; server code uses the Supabase Python client via `packages/database` (`get_supabase_client()` in `packages/database/src/sharpedge_db/client.py`).
- **Agentic analysis** for betting workflows uses **LangGraph** (`StateGraph`, compiled singleton `ANALYSIS_GRAPH`) in `packages/agent_pipeline/src/sharpedge_agent_pipeline/graph.py`.
- **Trading / execution** uses an **event-driven asyncio pipeline** (`EventBus` in `packages/trading_swarm/src/sharpedge_trading/events/bus.py`) plus **shadow / optional live execution** in `packages/venue_adapters/src/sharpedge_venue_adapters/execution_engine.py` (Kalshi integration when enabled).

## Layers

**Presentation — Web (Next.js App Router):**

- Purpose: Subscriber dashboard, auth flows, tier-gated routes, UI over REST + Supabase session.
- Location: `apps/web/src/app/`, `apps/web/src/components/`
- Contains: Route groups `(dashboard)`, auth pages, React components, `middleware.ts` for Supabase SSR and tier checks.
- Depends on: `@supabase/ssr`, `@supabase/supabase-js`, backend HTTP API (`NEXT_PUBLIC_API_URL` defaulting in `apps/web/src/lib/api.ts`).
- Used by: End users in the browser.

**Presentation — Mobile (Flutter):**

- Purpose: Native app shell, screens for plays, bankroll, copilot, notifications.
- Location: `apps/mobile/lib/`
- Contains: `screens/`, `widgets/`, `services/api_service.dart`, `services/auth_service.dart`, `providers/app_state.dart`.
- Depends on: `supabase_flutter`, Firebase (push), HTTP to backend as implemented in services.
- Used by: Mobile end users.

**API & integrations — FastAPI “webhook” service:**

- Purpose: HTTP surface for **Stripe (legacy)**, **Whop**, **RevenueCat**, **mobile** hooks, and versioned REST **`/api/v1/*`** (portfolio, value plays, bankroll, copilot SSE, swarm, game analysis, notifications, markets). Background jobs start in app lifespan.
- Location: `apps/webhook_server/src/sharpedge_webhooks/` (`main.py`, `routes/`, `routes/v1/`, `jobs/`, `services/`)
- Contains: FastAPI routers, dependency modules, scheduled/async jobs (e.g. `jobs/result_watcher.py`, `jobs/alert_poster.py`, `jobs/retrain_scheduler.py`).
- Depends on: `sharpedge-db`, `sharpedge-shared`, Stripe/Firebase/etc. per route (see `apps/webhook_server/pyproject.toml`).
- Used by: `apps/web` (`apps/web/src/lib/api.ts`), mobile clients, payment webhooks, internal jobs.

**Discord application — Bot:**

- Purpose: Discord-first product surface: commands, embeds, scheduled jobs, subscription/tier middleware.
- Location: `apps/bot/src/sharpedge_bot/`
- Contains: `commands/`, `jobs/`, `services/`, `agents/`, `middleware/`, `embeds/`, entry `main.py` → `SharpEdgeBot` in `bot.py`.
- Depends on: `sharpedge-shared`, `sharpedge-db`, `sharpedge-odds`, `sharpedge-models`, `sharpedge-agent-pipeline`, Redis, Stripe, OpenAI Agents SDK, APScheduler, Firebase Admin.
- Used by: Discord guilds / operators.

**Domain — Analytics & models:**

- Purpose: Sports and prediction-market analytics, scanners, calibration, EV and regime logic.
- Location: `packages/analytics/src/sharpedge_analytics/`, `packages/models/src/sharpedge_models/`
- Contains: Domain modules (e.g. arbitrage, consensus, regime, prediction market helpers) and model artifacts / training-adjacent code.
- Depends on: Numerical stack (numpy, sklearn where applicable), other internal packages as wired by consumers.
- Used by: Bot jobs, webhook routes, trading swarm agents.

**Domain — Data ingestion:**

- Purpose: External API clients (odds, Kalshi, Polymarket, weather, public betting, etc.).
- Location: `packages/data_feeds/src/sharpedge_feeds/`
- Contains: Client modules per data source; imported by bot, swarm, or adapters as needed.
- Depends on: `httpx` / venue-specific auth (env-driven).
- Used by: Scanning, execution, and analysis paths.

**Domain — Venue adapters & execution:**

- Purpose: Normalize venue data, **ledger / shadow ledger**, dislocation and microstructure helpers, **execution engine** (exposure limits, optional live Kalshi CLOB).
- Location: `packages/venue_adapters/src/sharpedge_venue_adapters/`
- Contains: `execution_engine.py`, `ledger.py`, `adapters/` (e.g. `kalshi.py`, `polymarket.py`), `execution_engine.py` coordinating with `sharpedge_feeds.kalshi_client` when available.
- Depends on: `sharpedge_feeds` (Kalshi client), environment flags (e.g. `ENABLE_KALSHI_EXECUTION` referenced in `execution_engine.py` docstring).
- Used by: Trading swarm execution path, bot executor services.

**Infrastructure — Database access:**

- Purpose: Supabase client singleton and **SQL migrations**; query modules per aggregate.
- Location: `packages/database/src/sharpedge_db/`
- Contains: `client.py`, `models.py`, `queries/*.py`, `migrations/*.sql` (`001_initial_schema.sql` … `008_auth_bridge.sql`, including `007_trading_swarm.sql`).
- Depends on: `supabase` Python SDK, env `SUPABASE_URL` / `SUPABASE_SERVICE_KEY`.
- Used by: Bot, webhook server, any package calling `get_supabase_client()`.

**Orchestration — Agent pipeline (LangGraph):**

- Purpose: Multi-node betting analysis graph with parallel fan-out and conditional routing after validation.
- Location: `packages/agent_pipeline/src/sharpedge_agent_pipeline/`
- Contains: `graph.py` (`build_analysis_graph`, `ANALYSIS_GRAPH`), `nodes/` (`route_intent`, `fetch_context`, `detect_regime`, `run_models`, `calculate_ev`, `validate_setup`, `compose_alpha`, `size_position`, `generate_report`, `error_handler`), `state.py`, `copilot/` tools and session.
- Depends on: `langgraph`, OpenAI stack as configured by callers.
- Used by: Discord bot analysis flows and related commands.

**Orchestration — Trading swarm:**

- Purpose: Long-running **asyncio** coordination of specialized agents (scan, research, prediction, risk, portfolio, monitor, post-mortem) over typed events; startup validation and promotion gate logic.
- Location: `packages/trading_swarm/src/sharpedge_trading/`
- Contains: `daemon.py` (`run_daemon`), `events/`, `agents/`, `signals/`, `execution/` (`executor_factory.py`, `paper_executor.py`, `base_executor.py`), `config.py`.
- Depends on: `supabase`, `httpx`, `numpy`, `sklearn`, optional social/API clients in `signals/`.
- Used by: `docker-compose.yml` service `trading-swarm` (image built from `packages/trading_swarm/Dockerfile`).

**Workers (containers):**

- Purpose: Dedicated processes for **arb streaming** and **value scanning** with their own Dockerfiles and env contracts.
- Location: `packages/arb_stream/`, `packages/value_scanner/` (plus root `docker-compose.yml` services `arb-stream`, `value-scanner`).
- Contains: Minimal or service-specific code per package `pyproject.toml`.
- Depends on: Env vars declared in `docker-compose.yml` (e.g. `ODDS_API_KEY`, Kalshi paths, execution toggles).

## Data Flow

**Dashboard data (web):**

1. User authenticates via Supabase (SSR cookies); `apps/web/src/middleware.ts` enforces **tier** (`free` / `pro` / `sharp`) and **operator-only** route prefixes.
2. Client components call `fetch` helpers in `apps/web/src/lib/api.ts` against `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).
3. FastAPI handlers under `apps/webhook_server/src/sharpedge_webhooks/routes/v1/` read/write Supabase via `sharpedge_db` queries or inline client usage.

**Discord analysis command:**

1. User invokes a command; `apps/bot/src/sharpedge_bot/commands/` dispatches to services or agents.
2. Deep analysis path may invoke `ANALYSIS_GRAPH` from `packages/agent_pipeline/src/sharpedge_agent_pipeline/graph.py` (nodes fetch context, run models in parallel, validate, then compose / size / report).
3. Results may be persisted or formatted via `apps/bot/src/sharpedge_bot/embeds/`.

**Trading swarm pipeline:**

1. `run_daemon()` in `packages/trading_swarm/src/sharpedge_trading/daemon.py` loads config, validates models/gates in live mode, builds `EventBus`.
2. Agents consume/produce typed events on channels defined in `packages/trading_swarm/src/sharpedge_trading/events/bus.py`.
3. Execution stage uses `get_executor()` from `packages/trading_swarm/src/sharpedge_trading/execution/executor_factory.py`; shadow/live behavior ties into `packages/venue_adapters/src/sharpedge_venue_adapters/execution_engine.py` and Kalshi client from `sharpedge_feeds` when configured.

**State Management:**

- **Web:** React server/client components; SWR listed in `apps/web/package.json` for client caching where used.
- **Mobile:** `ChangeNotifier` / `AppState` in `apps/mobile/lib/providers/app_state.dart`.
- **Backend:** Postgres via Supabase; Redis used by bot (`apps/bot/pyproject.toml`) for rate limiting / caching patterns as implemented in `apps/bot/src/sharpedge_bot/middleware/`.

## Key Abstractions

**BettingAnalysisState / LangGraph graph:**

- Purpose: Typed state flowing through the 9-node analysis pipeline.
- Examples: `packages/agent_pipeline/src/sharpedge_agent_pipeline/state.py`, `packages/agent_pipeline/src/sharpedge_agent_pipeline/graph.py`
- Pattern: Compiled `StateGraph` singleton; callers must pass `config={'recursion_limit': 25}` at `ainvoke` time (documented in `graph.py`).

**EventBus (trading):**

- Purpose: Decouple producers/consumers across scan → research → prediction → risk → execution → resolution.
- Examples: `packages/trading_swarm/src/sharpedge_trading/events/bus.py`, `packages/trading_swarm/src/sharpedge_trading/events/types.py`
- Pattern: One reader per channel per process; asyncio queues.

**ShadowExecutionEngine / ledger:**

- Purpose: Enforce exposure and record shadow (and optional live) fills.
- Examples: `packages/venue_adapters/src/sharpedge_venue_adapters/execution_engine.py`, `packages/venue_adapters/src/sharpedge_venue_adapters/ledger.py`
- Pattern: Engine coordinates polling and ledger writes; feature-flagged live submission.

**Supabase client wrapper:**

- Purpose: Single service-role client for backend processes.
- Examples: `packages/database/src/sharpedge_db/client.py`
- Pattern: Module-level singleton `get_supabase_client()`.

## Entry Points

**Python apps (uv workspace members — see root `pyproject.toml`):**

- Discord bot CLI: `sharpedge-bot` → `apps/bot/src/sharpedge_bot/main.py` (`main()`).
- FastAPI server: `sharpedge-webhooks` → `apps/webhook_server/src/sharpedge_webhooks/main.py` (`run()` / uvicorn app).

**Trading swarm:**

- Async entry: `asyncio.run(run_daemon())` at bottom of `packages/trading_swarm/src/sharpedge_trading/daemon.py` when executed as script; container image wired in root `docker-compose.yml` service `trading-swarm`.

**Next.js web:**

- Dev/prod: `apps/web/package.json` scripts `next dev`, `next build`, `next start`; App Router root layout `apps/web/src/app/layout.tsx`, home `apps/web/src/app/page.tsx`, dashboard group `apps/web/src/app/(dashboard)/`.

**Flutter mobile:**

- `apps/mobile/lib/main.dart` — initializes Firebase (optional), Supabase, `NotificationService`, `Provider` + `AppState`.

## Error Handling

**Strategy:** Layer-specific — FastAPI HTTP errors on the API surface; graph-level `error_handler` node in LangGraph; logging + `StartupError` in trading daemon for fatal misconfiguration; defensive fallbacks (e.g. Kalshi stub in `daemon.py` when client build fails).

**Patterns:**

- Trading: `StartupError` raised from `run_daemon()` when validation fails (see tests in `packages/trading_swarm/tests/smoke/test_daemon_smoke.py`).
- Agent pipeline: Dedicated `error_handler` node and conditional routing after `validate_setup` in `graph.py`.

## Cross-Cutting Concerns

**Logging:** Standard library `logging` in Python services (`apps/bot/src/sharpedge_bot/main.py`, `apps/webhook_server/src/sharpedge_webhooks/main.py`, `packages/trading_swarm/src/sharpedge_trading/daemon.py`).

**Validation:** Pydantic settings in webhook and bot configs (`apps/webhook_server/src/sharpedge_webhooks/config.py`, `apps/bot/src/sharpedge_bot/config.py`); Pydantic elsewhere per package.

**Authentication:** Supabase JWT/session for web (middleware + `apps/web/src/lib/supabase-server.ts` / `apps/web/src/lib/supabase.ts`); bearer tokens on selected API routes (e.g. `getPortfolio` in `apps/web/src/lib/api.ts`); Discord bot token for gateway; mobile Supabase anon + `String.fromEnvironment` fallbacks in `apps/mobile/lib/main.dart`.

---

*Architecture analysis: 2026-03-21*
