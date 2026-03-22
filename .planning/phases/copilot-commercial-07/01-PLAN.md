---
phase: copilot-commercial-07
plan: 01
type: execute
wave: 1
depends_on:
  - copilot-commercial-05
files_modified:
  - apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py
  - apps/webhook_server/src/sharpedge_webhooks/copilot_rate_limit.py
  - apps/webhook_server/pyproject.toml
  - apps/webhook_server/tests/unit/api/test_copilot_sse.py
  - .planning/COPILOT-CHECKPOINT-RETENTION.md
autonomous: true
requirements:
  - .planning/phases/copilot-commercial-07/07-CONTEXT.md
must_haves:
  truths:
    - "Copilot chat endpoint returns 429 when rate limit exceeded (tested)."
    - "Repo documents checkpoint retention / cleanup options for LangGraph Postgres tables."
    - "Request logging does not include raw user message content by default."
---

<objective>
**Commercial Phase 7 — hardening:** rate limit `/api/v1/copilot/chat`, add safe structured logging, document checkpoint retention; optional graph recursion/env caps.
</objective>

## Task 1 — Rate limiter

<action>
Add `copilot_rate_limit.py` with in-memory sliding window or token bucket (per-process; document that multi-instance deploys need Redis later). Read limits from env: `COPILOT_RATE_LIMIT_PER_MINUTE` (default e.g. 20), `COPILOT_RATE_BURST` optional.

Apply in `copilot_chat` via `Depends()` or inline check: key = `user_id` or `client.host` / forwarded-for first hop. On exceed: `HTTPException(429, detail="Rate limit exceeded")`.

Add dependency only to `copilot` router or single route to avoid affecting other v1 routes.
</action>

<read_first>
- apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py
</read_first>

<acceptance_criteria>
- `grep -n COPILOT_RATE_LIMIT apps/webhook_server/src/sharpedge_webhooks/copilot_rate_limit.py` matches default constant or env read.
- New test in `test_copilot_sse.py` or `test_copilot_rate_limit.py`: two rapid posts exceed limit → second returns 429 (mock time or tiny limit via `monkeypatch.setenv`).
</acceptance_criteria>

## Task 2 — Structured logging

<action>
In `copilot_chat` or `_stream_copilot` entry: `logging.info` one JSON line or key=value string: `copilot_request thread_prefix=... duration_ms=... user_authenticated=bool` — **never** log `body.message`. Use SHA256 prefix of `thread_id` if present.
</action>

<read_first>
- apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py
</read_first>

<acceptance_criteria>
- `grep -n "copilot_request\\|sharpedge.copilot" apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py` matches logger call.
</acceptance_criteria>

## Task 3 — Recursion / cost cap (minimal)

<action>
Pass `config` to `graph.astream_events` including `recursion_limit` if LangGraph supports it on compiled graph (verify in installed version). If unsupported, set env `COPILOT_RECURSION_LIMIT` and document; implement only if one-line config merge works.

Alternatively: document-only in `07-CONTEXT.md` if API not available without library upgrade.
</action>

<read_first>
- packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py (compile options)
</read_first>

<acceptance_criteria>
- Either `grep -n recursion_limit apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py` matches **or** `07-CONTEXT.md` states “recursion_limit deferred” with reason.
</acceptance_criteria>

## Task 4 — Checkpoint retention doc

<action>
Create **`.planning/COPILOT-CHECKPOINT-RETENTION.md`** (short): LangGraph Postgres table names from `langgraph-checkpoint-postgres`, example **optional** `DELETE`/`VACUUM` schedule by age, note **RLS** is operator’s choice in Supabase UI, link to commercial roadmap Phase 2 exit criteria. **Do not** commit secrets.
</action>

<acceptance_criteria>
- File `.planning/COPILOT-CHECKPOINT-RETENTION.md` exists.
- Contains substring `checkpoint` and `retention` or `TTL`.
</acceptance_criteria>
