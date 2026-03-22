# Copilot Commercial Phase 7 — Context

**Phase:** copilot-commercial-07  
**Source:** `.planning/COPILOT-COMMERCIAL-ROADMAP.md` Phase 7 + **Phase 2 gaps** (retention / compliance).

## Boundary

**Production operations:** abuse resistance, cost control, observability without leaking PII. **Checkpoint retention** is policy + optional SQL/cron — document in-repo; RLS on LangGraph tables is **Supabase UI** per project rules (provide SQL snippets only).

## Decisions

- Rate limit **`POST /api/v1/copilot/chat`** by **`user_id` if authenticated else client IP** (header `X-Forwarded-For` aware behind proxy).
- **Recursion / tool rounds:** `recursion_limit` is passed on copilot `astream_events` config from env **`COPILOT_RECURSION_LIMIT`** (default 25), aligned with the analysis graph pattern in `packages/agent_pipeline`.
- **Logging:** structured log line per request: `thread_id` prefix hash, tier if available, duration — **no** message body in logs by default.
- **Feature flags:** extend existing env patterns (`COPILOT_*`) for experimental tools.

## Canonical refs

- `apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py`
- `apps/webhook_server/src/sharpedge_webhooks/main.py`
- `apps/bot/src/sharpedge_bot/middleware/rate_limiter.py` (pattern reference if applicable)
