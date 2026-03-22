# Copilot Commercial Phase 4 — Context

**Gathered:** 2026-03-22  
**Status:** Ready for planning  
**Source:** `.planning/COPILOT-COMMERCIAL-ROADMAP.md` Phase 4

---

## Phase boundary

Make **which tools ran** visible to users and support: **SSE metadata** (tool start/end with short labels) plus **web + mobile UI** to show steps/sources without dumping full tool I/O.

---

## Implementation decisions

### Locked

- **Transport:** Extend the existing **`POST /api/v1/copilot/chat`** SSE stream (same URL, auth, `thread_id`). No second HTTP round-trip required for MVP.
- **Payload shape:** Use standard SSE **`event:`** names (or an unambiguous `data:` JSON discriminator) so **token text is never mixed** with control frames — today’s clients append every `data:` line to assistant markdown; that must change.
- **Content policy:** Emit **tool name + one-line summary** (optional short input hint, e.g. sport or game_id). **No** full raw tool args/response JSON by default (PII + token noise).
- **Touchpoints:** `apps/webhook_server/.../routes/v1/copilot.py` (`_stream_copilot`), `apps/web/.../chat-stream.tsx`, `apps/mobile/.../copilot_screen.dart`, tests under `apps/webhook_server/tests/unit/api/test_copilot_sse.py`.

### Claude's discretion

- Exact LangGraph `astream_events` event names (`on_tool_start` / `on_tool_end` vs vendor-specific) — confirm against installed `langchain_core` / `langgraph` in a spike; normalize in one helper.
- UI pattern: collapsible **“Steps”** below the assistant bubble vs inline chips — match existing dashboard dark/zinc + teal accent.
- Whether to log the same tool events server-side (structured logging) as a stretch task.

### UI design contract

No standalone `UI-SPEC.md` for this phase; visuals should follow existing copilot screen patterns in `chat-stream.tsx` / `copilot_screen.dart`.

---

## Canonical references

- `.planning/COPILOT-COMMERCIAL-ROADMAP.md` — Phase 4 goals and exit criteria
- `apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py`
- `apps/web/src/components/copilot/chat-stream.tsx`
- `apps/mobile/lib/screens/copilot_screen.dart`
- `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py` — graph + `astream_events` consumer

---

*Phase: copilot-commercial-04*
