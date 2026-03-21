# Codebase Structure

**Analysis Date:** 2026-03-21

## Directory Layout

```
sharpedge/
├── pyproject.toml              # uv workspace root; members: apps/bot, apps/webhook_server, packages/*
├── uv.lock                     # Locked Python dependencies for the workspace
├── docker-compose.yml          # trading-swarm, arb-stream, value-scanner services
├── apps/
│   ├── bot/                    # Discord application (Python package sharpedge_bot)
│   ├── webhook_server/         # FastAPI HTTP + webhooks + v1 API (sharpedge_webhooks)
│   ├── web/                    # Next.js 14 dashboard (standalone Node app)
│   └── mobile/                 # Flutter app (not a uv member)
├── packages/
│   ├── agent_pipeline/         # LangGraph betting analysis + copilot tools
│   ├── analytics/              # Sports / PM analytics domain code
│   ├── arb_stream/             # Arbitrage streaming worker (Docker)
│   ├── data_feeds/             # External API clients (Kalshi, Polymarket, odds, …)
│   ├── database/               # Supabase client + SQL migrations + query modules
│   ├── models/                 # Model / calibration / EV utilities
│   ├── odds_client/            # Odds API client package (sharpedge-odds)
│   ├── shared/                 # Cross-cutting Python types/helpers
│   ├── trading_swarm/          # Event-bus trading daemon + agents + execution
│   ├── value_scanner/          # Value scanner worker (Docker)
│   └── venue_adapters/         # Venue normalization, ledger, execution engine
├── data/                       # Training / processed datasets (large artifacts; see .gitignore policy locally)
├── docs/                       # Design notes and specs
├── scripts/                    # Operational and dev scripts
└── tests/                      # Top-level Python tests (workspace-level)
```

## Directory Purposes

**`apps/bot`:**

- Purpose: Discord bot runtime, commands, background jobs, integration with agent pipeline and DB.
- Contains: `src/sharpedge_bot/` (`commands/`, `jobs/`, `services/`, `agents/`, `middleware/`, `embeds/`, `utils/`), `tests/`.
- Key files: `apps/bot/src/sharpedge_bot/main.py`, `apps/bot/src/sharpedge_bot/bot.py`, `apps/bot/pyproject.toml` (entry `sharpedge-bot`).

**`apps/webhook_server`:**

- Purpose: Primary **backend HTTP** process: webhooks (Stripe, Whop, RevenueCat), `routes/v1/*` REST, background tasks.
- Contains: `src/sharpedge_webhooks/routes/`, `src/sharpedge_webhooks/routes/v1/`, `src/sharpedge_webhooks/jobs/`, `src/sharpedge_webhooks/services/`, `tests/unit/api/`.
- Key files: `apps/webhook_server/src/sharpedge_webhooks/main.py`, `apps/webhook_server/pyproject.toml` (entry `sharpedge-webhooks`).

**`apps/web`:**

- Purpose: Subscriber-facing Next.js UI (App Router, Tailwind).
- Contains: `src/app/` (routes), `src/components/`, `src/lib/` (API + Supabase), `src/middleware.ts`, root configs `next.config.mjs`, `tailwind.config.ts`, `vitest.config.ts`.
- Note: Duplicate legacy paths `apps/web/components/` exist alongside `src/components/` — prefer `src/` for new work.

**`apps/mobile`:**

- Purpose: Flutter client; Supabase + optional Firebase push.
- Contains: `lib/screens/`, `lib/widgets/`, `lib/services/`, `lib/models/`, `lib/providers/`, platform folders `ios/`, `android/`, `macos/`, etc.

**`packages/database`:**

- Purpose: Data access + schema evolution.
- Contains: `src/sharpedge_db/client.py`, `src/sharpedge_db/queries/*.py`, `src/sharpedge_db/migrations/*.sql`.

**`packages/trading_swarm`:**

- Purpose: Long-running trading coordination; Dockerized via `packages/trading_swarm/Dockerfile` from repo root context.

**`packages/agent_pipeline`:**

- Purpose: LangGraph pipeline and copilot-oriented agent code under `src/sharpedge_agent_pipeline/`.

**`packages/venue_adapters` & `packages/data_feeds`:**

- Purpose: External venue and market data; execution and polling live next to feed clients.

## Key File Locations

**Entry Points:**

- `apps/bot/src/sharpedge_bot/main.py`: Discord bot `main()`.
- `apps/webhook_server/src/sharpedge_webhooks/main.py`: FastAPI app + uvicorn `run()`.
- `packages/trading_swarm/src/sharpedge_trading/daemon.py`: `run_daemon()` trading process.
- `apps/web/src/app/page.tsx`: Web landing; `apps/web/src/app/(dashboard)/page.tsx`: dashboard home.
- `apps/mobile/lib/main.dart`: Flutter `main()`.

**Configuration:**

- Root Python workspace: `pyproject.toml` (uv `tool.uv.workspace.members`).
- Per-package: `apps/*/pyproject.toml`, `packages/*/pyproject.toml`.
- Web: `apps/web/package.json`, `apps/web/tsconfig.json`, Tailwind/PostCSS next to web app root.
- Mobile: `apps/mobile/pubspec.yaml`.
- Local orchestration: `docker-compose.yml` (bind-mounts `.env` — do not commit secrets).

**Core Logic:**

- Analysis graph: `packages/agent_pipeline/src/sharpedge_agent_pipeline/graph.py`.
- Trading events: `packages/trading_swarm/src/sharpedge_trading/events/`.
- Execution: `packages/venue_adapters/src/sharpedge_venue_adapters/execution_engine.py`, `packages/trading_swarm/src/sharpedge_trading/execution/`.
- HTTP v1 API: `apps/webhook_server/src/sharpedge_webhooks/routes/v1/*.py`.

**Testing:**

- Web: `apps/web/src/test/*.tsx`, `apps/web/vitest.config.ts`.
- Webhook server: `apps/webhook_server/tests/`.
- Bot: `apps/bot/tests/`.
- Trading swarm: `packages/trading_swarm/tests/`.
- Repo-level: `tests/` at repository root.

## Naming Conventions

**Files:**

- **Python:** `snake_case.py` modules; package dirs match import root (`sharpedge_bot`, `sharpedge_db`, `sharpedge_trading`).
- **TypeScript/React:** `kebab-case.tsx` or descriptive names (e.g. `stats-cards.tsx`, `monte-carlo-chart.tsx`); some `PascalCase.tsx` for components (e.g. `VenueDislocWidget.tsx`).
- **Dart:** `snake_case.dart` for screens/widgets/services (`value_plays_screen.dart`, `api_service.dart`).

**Directories:**

- Next.js App Router: route segments in parentheses for groups, e.g. `apps/web/src/app/(dashboard)/`.
- Python: plural folders for domain areas (`commands/`, `jobs/`, `routes/`, `queries/`).

**Packages vs import names:**

- PyPI-style distribution names use hyphens (`sharpedge-db`, `sharpedge-trading` in `pyproject.toml`); Python import paths use underscores (`sharpedge_db`, `sharpedge_trading`).

## Where to Add New Code

**New REST endpoint (v1):**

- Add router module under `apps/webhook_server/src/sharpedge_webhooks/routes/v1/`, register in `apps/webhook_server/src/sharpedge_webhooks/main.py`.
- Tests: `apps/webhook_server/tests/unit/api/`.

**New Supabase query or schema change:**

- Queries: new module or functions in `packages/database/src/sharpedge_db/queries/`, export via `packages/database/src/sharpedge_db/queries/__init__.py` if applicable.
- Schema: new numbered migration in `packages/database/src/sharpedge_db/migrations/` (follow existing sequence after `008_auth_bridge.sql`).

**New Discord command or job:**

- Commands: `apps/bot/src/sharpedge_bot/commands/`.
- Scheduled/async jobs: `apps/bot/src/sharpedge_bot/jobs/`, wire in `apps/bot/src/sharpedge_bot/jobs/scheduler.py` when appropriate.

**New LangGraph node or copilot tool:**

- Nodes: `packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/`, update `packages/agent_pipeline/src/sharpedge_agent_pipeline/graph.py` edges.
- Copilot: `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/`.

**New trading agent or signal:**

- Agents: `packages/trading_swarm/src/sharpedge_trading/agents/`.
- Signal / external clients: `packages/trading_swarm/src/sharpedge_trading/signals/`.
- Daemon wiring: `packages/trading_swarm/src/sharpedge_trading/daemon.py`.

**New venue or feed client:**

- Feeds: `packages/data_feeds/src/sharpedge_feeds/`.
- Adapters / execution: `packages/venue_adapters/src/sharpedge_venue_adapters/adapters/` or sibling modules.

**New dashboard page or component:**

- Pages: `apps/web/src/app/(dashboard)/<route>/page.tsx`.
- Shared UI: `apps/web/src/components/` (mirror existing Tailwind patterns).

**New mobile screen:**

- `apps/mobile/lib/screens/<name>_screen.dart`, register navigation in `apps/mobile/lib/main.dart` or home shell as done for existing screens.

## Special Directories

**`data/`:**

- Purpose: Processed training data, parquet/csv artifacts referenced by ML workflows; may be large.
- Generated: Mix of generated and curated; follow repo policy for committing binaries.

**`.planning/`:**

- Purpose: GSD / planning artifacts (this folder).
- Committed: Typically yes for plans; exclude secrets.

**`FinnAI/`, `docs/superpowers/`:**

- Purpose: Adjacent specs and planning docs; not runtime code paths for SharpEdge services.

---

*Structure analysis: 2026-03-21*
