---
phase: copilot-commercial-02
plan: 01
type: execute
wave: 1
depends_on:
  - copilot-commercial-01
files_modified:
  - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py
  - apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py
  - apps/webhook_server/src/sharpedge_webhooks/main.py
  - apps/web/src/components/copilot/chat-stream.tsx
  - apps/mobile/lib/screens/copilot_screen.dart
  - apps/webhook_server/tests/unit/api/test_copilot_sse.py
  - packages/database/src/sharpedge_db/migrations/ (optional — if not using saver.setup() only)
autonomous: true
requirements:
  - .planning/COPILOT-COMMERCIAL-ROADMAP.md (Phase 2)
  - .planning/COPILOT-COMMERCIAL-ROADMAP.md architecture decision (Postgres on webhook server)
must_haves:
  truths:
    - "POST /api/v1/copilot/chat accepts a stable thread id from the client and loads prior MessagesState from Postgres when present."
    - "Checkpoint thread identity is scoped to the authenticated user (no cross-user thread reuse)."
    - "Web and mobile persist the same thread UUID locally and send it on every copilot request."
    - "When DATABASE_URL / checkpoint DSN is unset, copilot degrades to current single-turn behavior or explicit 503 with clear message (product choice documented in CONTEXT)."
  artifacts:
    - path: apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py
      provides: thread_id in body + LangGraph run config + optional new-thread response contract
    - path: packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py
      provides: compile(..., checkpointer=...) factory accepting injected checkpointer
---

<objective>
Implement **Copilot Commercial Phase 2 — server-side memory**: Postgres-backed LangGraph checkpoints on the **webhook server**, `thread_id` wired from web + mobile, and **auth-scoped** checkpoint keys so one user cannot continue another’s thread.

**Prerequisite:** Phase 1 (trust + tools) complete.

**Optional before coding:** `/gsd-discuss-phase` for **Phase 2** to lock anonymous-user policy, retention TTL, and exact env var names (`DATABASE_URL` vs pooled Supabase string) → `COPILOT-COMMERCIAL-02-CONTEXT.md`.
</objective>

<execution_context>
@.planning/COPILOT-COMMERCIAL-ROADMAP.md
@packages/agent_pipeline/pyproject.toml
@apps/webhook_server/pyproject.toml
@apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py
@packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py
</execution_context>

## Context summary

| Source | Decision (locked) |
|--------|-------------------|
| Commercial roadmap | Persistence = **LangGraph + Postgres** colocated with **FastAPI copilot** route |
| Dependency | `langgraph-checkpoint-postgres` already in **agent_pipeline** `pyproject.toml` — webhook must resolve **runtime** import + DB driver (see Task 0) |

---

## Task 0 — Dependency and DSN wiring

- Confirm **webhook_server** installs **sharpedge-agent-pipeline** (workspace dep) if not already in `apps/webhook_server/pyproject.toml` — copilot already lazy-imports it at runtime; production must match.
- Add any **extra** deps required by `langgraph-checkpoint-postgres` (e.g. async Postgres driver) to the package that **owns the lifespan** that creates the saver (likely **webhook_server** or root install).
- Standardize env: **`COPILOT_DATABASE_URL`** or reuse **`DATABASE_URL`** / Supabase **pooler** URL — document in `config` or `.env.example` (no secrets in repo).

---

## Task 1 — Checkpointer lifecycle (FastAPI)

- Use **`AsyncPostgresSaver`** (or current **langgraph-checkpoint-postgres** API) per package docs: call **`setup()`** once at startup to create tables if missing (or ship SQL migration if org forbids runtime DDL).
- **Lifespan** (`main.py`): open connection pool / saver, attach to **`app.state.copilot_checkpointer`** (or factory that returns compiled graph).
- **Shutdown**: close pool cleanly.
- **Tests / dev**: when DSN missing, **`build_copilot_graph(checkpointer=None)`** preserves today’s behavior.

---

## Task 2 — `build_copilot_graph` accepts checkpointer

**Edit** `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py`:

- Signature: **`build_copilot_graph(tools=None, checkpointer=None)`**.
- **`g.compile(checkpointer=checkpointer)`** when non-None; else **`g.compile()`** (current).
- **`COPILOT_GRAPH` / `_try_build_graph`**: keep **no checkpointer** at import time (avoid DB at module load); production graph built in webhook lifespan with saver.

---

## Task 3 — Thread id + authZ in API

**Edit** `apps/webhook_server/.../copilot.py`:

- Request body: require or strongly recommend **`thread_id`** (reuse existing **`session_id`** field by **alias** `thread_id` in Pydantic, or rename with backward compatibility).
- **Authenticated:** `checkpoint_thread_id = f"{user_id}:{thread_id}"` (or HMAC / hash if length limits — document).
- **Anonymous:** choose one: (a) no persistence (ephemeral thread id ignored), (b) `anon:{thread_id}` with rate limits, or (c) reject missing JWT when `COPILOT_REQUIRE_AUTH_FOR_THREADS=1` — **lock in CONTEXT**.
- Pass to LangGraph:

  ```text
  config = {
    "configurable": {
      "thread_id": checkpoint_thread_id,
      "user_id": user_id,
    }
  }
  ```

- **Input state:** append **only the new user message** to state; LangGraph + checkpointer merges with history (verify **`messages` reducer** for `MessagesState` — default append).
- **`astream_events`:** use same `config` as `invoke`/`ainvoke` would.

---

## Task 4 — Web client

**Edit** `apps/web/src/components/copilot/chat-stream.tsx`:

- On mount: `localStorage.getItem('sharpedge_copilot_thread_id')` or **`crypto.randomUUID()`**, then persist.
- Include **`thread_id`** (or agreed field name) in JSON body with **`message`**.
- **New chat:** generate new UUID, update storage, clear UI messages.

---

## Task 5 — Mobile client

**Edit** `apps/mobile/lib/screens/copilot_screen.dart` (or small helper):

- Persist thread id with **`shared_preferences`** (or existing app storage pattern).
- Send same field in POST body as web.
- **New chat:** new UUID + clear messages.

---

## Task 6 — Tests

- **Unit:** mock checkpointer / `MemorySaver` in agent_pipeline tests to assert **`configurable.thread_id`** is honored across two synthetic turns.
- **API:** extend **`test_copilot_sse.py`** — with graph mocked, assert request body includes **`thread_id`** forwarded (or contract test on pydantic model).
- **Optional integration:** skip in CI without DSN; document `pytest -m copilot_db`.

---

## Task 7 — Retention and compliance (minimal v1)

- Document in README or internal runbook: checkpoint tables grow unbounded — **Phase 7** or ops cron: delete rows older than **N** days / per-user cap.
- If product needs **export/delete** for GDPR: note follow-up phase (not blocking Phase 2 merge).

---

## Verification checklist

- [ ] Logged-in user: send message A, then B in same thread → model sees context from A.
- [ ] Same `thread_id` under **different** `user_id` → must **not** see prior user’s messages.
- [ ] New chat on web + mobile → new UUID, empty context.
- [ ] DSN unset locally → copilot still responds (single-turn or clear error per policy).
- [ ] `uv run pytest` for touched packages green.

---

## Risks / notes

- **SSE + long runs:** checkpoint writes per step; watch DB connection count under load (pool size).
- **Trimming:** `trim_conversation` still runs in `agent_node`; checkpoint may store full history while LLM sees trimmed — acceptable if documented; alternatively trim before persist (harder).
- **Supabase:** use **transaction** pooler for serverless-friendly Postgres if applicable.

---

## Document history

- **2026-03-21:** Plan created via `/gsd-plan-phase` (auto: Copilot Commercial Phase 2).
