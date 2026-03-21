# Technology Stack

**Analysis Date:** 2026-03-21

## Languages

**Primary:**
- **Python 3.12+** — Backend services, packages, bots, webhooks, ML/analytics (`requires-python = ">=3.12"` in `/Users/revph/sharpedge/pyproject.toml` and workspace members).
- **TypeScript** — Next.js web app in `apps/web` (`typescript` in `apps/web/package.json`).
- **Dart / Flutter** — Mobile client (`apps/mobile/pubspec.yaml`, SDK `>=3.0.0 <4.0.0`, Flutter `>=3.10.0`).

**Secondary:**
- **SQL** — Supabase/Postgres migrations in `packages/database/src/sharpedge_db/migrations/*.sql`.
- **CSS** — Tailwind via PostCSS for `apps/web`.

## Runtime

**Environment:**
- **CPython 3.12** — Declared across the uv workspace; Docker images use `python:3.12-slim` in `packages/trading_swarm/Dockerfile`, `packages/value_scanner/Dockerfile`, `packages/arb_stream/Dockerfile`.
- **Node.js** — Implied by Next.js 14 in `apps/web` (no root `package.json`; version pinned via `@types/node` ^20).

**Package Manager:**
- **uv** — Python workspace and dependency resolution (`[tool.uv.workspace]` in `/Users/revph/sharpedge/pyproject.toml`, `members = ["apps/bot", "apps/webhook_server", "packages/*"]`).
- **npm** — Used for `apps/web` only (`apps/web/package.json`); **no** monorepo-level `pnpm-workspace.yaml` or `turbo.json` detected at repository root.

**Lockfiles:**
- Python: uv lock behavior per project (check for `uv.lock` locally when installing).
- Web: `package-lock.json` may exist under `apps/web` if generated (not assumed committed).

## Frameworks

**Core (Python):**
- **discord.py** (`>=2.0`) — Discord bot (`apps/bot/pyproject.toml`).
- **FastAPI** + **Uvicorn** — HTTP API and webhook server (`apps/webhook_server/pyproject.toml`).
- **openai-agents** (`>=0.0.7,<0.1.0`) — Bot agent orchestration (`apps/bot`); **LangGraph / LangChain** stack in `packages/agent_pipeline/pyproject.toml` (`langgraph`, `langchain-openai`, `langgraph-checkpoint-postgres`, `tiktoken`).
- **APScheduler** — Scheduled jobs in bot (`apps/bot`).
- **Pydantic** / **pydantic-settings** — Settings and models across packages.

**Core (Web):**
- **Next.js 14.2.5** (App Router) — `apps/web/package.json` (`next`, `react` ^18.3).
- **Tailwind CSS 3.4** + **PostCSS** + **Autoprefixer** — `apps/web` styling (`tailwind.config.ts`, `postcss` dev deps).

**Core (Mobile):**
- **Flutter** — UI and platform integration (`apps/mobile/pubspec.yaml`).
- **provider** — State management.
- **supabase_flutter** — Backend/auth client.

**Data / ML:**
- **NumPy**, **SciPy**, **scikit-learn**, **joblib** — Models and trading stack (`packages/models`, `packages/trading_swarm`, `packages/analytics`, `packages/venue_adapters`).
- **pandas**, **pyarrow** — Declared as root dev dependencies in `/Users/revph/sharpedge/pyproject.toml` (data tooling).
- **matplotlib** — Analytics visualization (`packages/analytics`).

**Testing:**
- **pytest**, **pytest-asyncio**, **pytest-mock** — Python (root `pyproject.toml` dev-dependencies; some packages define `tool.pytest.ini_options`).
- **Vitest 2.x** + **Testing Library** + **jsdom** — `apps/web` (`apps/web/vitest.config.ts`, `apps/web/package.json` scripts `test` / `test:watch`).

**Build / packaging:**
- **hatchling** — Wheel build backend for several packages (e.g. `apps/bot/pyproject.toml`, `apps/webhook_server/pyproject.toml`).

## Key Dependencies

**Critical:**
- **supabase** (Python `>=2.0`) — Server-side DB/auth client (`packages/database/pyproject.toml`); **@supabase/supabase-js** + **@supabase/ssr** — Web (`apps/web/package.json`); **supabase_flutter** — Mobile.
- **httpx** — Async/sync HTTP across bot, webhooks, odds, feeds, venue adapters.
- **redis** — Caching and session-related usage (`apps/bot`, `packages/odds_client`).
- **stripe** — Legacy payments still in bot and webhook server dependencies; Whop is primary for new flows (see `INTEGRATIONS.md`).
- **firebase-admin** — Push notifications (`apps/bot`, `apps/webhook_server`).
- **websockets** + **cryptography** — Streaming and signed APIs (`packages/data_feeds`).

**Infrastructure / CLI:**
- **python-dotenv** — Root and webhook server env loading.
- **ruff** — Lint/format (`/Users/revph/sharpedge/ruff.toml`, target Py312, isort first-party packages).
- **mypy** — Type checking (declared root dev dependency).

## Configuration

**Environment:**
- Shared template: `.env.example` at repo root documents Discord, Supabase, OpenAI, Odds API, Redis, Whop, prediction markets, enrichment keys, and legacy Stripe placeholders.
- **Pydantic Settings** loads `.env` for bot (`apps/bot/src/sharpedge_bot/config.py`) and webhook server (`apps/bot` uses single `.env`; `WebhookConfig` checks `../../.env` then `.env` in `apps/webhook_server/src/sharpedge_webhooks/config.py`).
- **Next.js public env** — `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` consumed in `apps/web/src/lib/supabase.ts`.

**Build:**
- **Next:** `apps/web/next.config.mjs`.
- **TypeScript:** `apps/web/tsconfig.json`.
- **Vitest:** `apps/web/vitest.config.ts` (path alias `@` → `./src`).
- **Python:** Per-package `pyproject.toml`; workspace orchestration via root `pyproject.toml` `[tool.uv.workspace]`.

## Platform Requirements

**Development:**
- Python 3.12+, **uv** for installs and `uv run` in workspace members.
- Node/npm for `apps/web` (`npm run dev|build|test` per `apps/web/package.json`).
- Flutter SDK >=3.10 for `apps/mobile`.

**Production:**
- **Docker** — Optional containerized workers: trading swarm daemon (`packages/trading_swarm/Dockerfile` → `python -m sharpedge_trading.daemon`), value scanner (`packages/value_scanner/Dockerfile` → `scripts/run_scanners.py`), arb stream (`packages/arb_stream/Dockerfile` → `scripts/run_arb_stream.py`).
- Web: standard Next.js deployment target (Vercel or Node host); no `vercel.json` present in repo snapshot.
- External managed services: Supabase (Postgres/Auth/Storage), Redis (e.g. Upstash noted in `.env.example`), cloud push via Firebase.

---

*Stack analysis: 2026-03-21*
