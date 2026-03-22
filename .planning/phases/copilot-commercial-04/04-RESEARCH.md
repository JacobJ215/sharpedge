# Copilot Commercial Phase 4 — Technical research

**Phase:** copilot-commercial-04  
**Date:** 2026-03-22  
**Question:** What do we need to know to implement **SSE tool transparency** (server + web + mobile) safely and compatibly with the current copilot stack?

---

## RESEARCH COMPLETE

---

## 1. LangGraph `astream_events` (verified on repo stack)

**Setup:** `build_copilot_graph()` from `sharpedge_agent_pipeline.copilot.agent`, `astream_events(..., version="v1")`, LangChain `HumanMessage` + mocked `ChatOpenAI` that returns `AIMessage` with `tool_calls`, patched DB-backed tool.

### Tool boundary event names (exact strings)

| Event | Count (sample run) | Use |
|--------|-------------------|-----|
| **`on_tool_start`** | 1 per tool invocation | Emit SSE “start” frame with tool name + safe input summary |
| **`on_tool_end`** | 1 per tool invocation | Emit SSE “end” frame; optional status summary |

Other events observed on the same run: `on_chain_start`, `on_chain_end`, `on_chain_stream` (multiple). **Do not** treat `on_chain_stream` as user-visible tokens — assistant **tokens** for copilot today come from **`on_chat_model_stream`** (existing `copilot.py` path).

### Sample payloads (structure)

**`on_tool_start`**

```json
{
  "event": "on_tool_start",
  "name": "get_active_bets",
  "data": { "input": {} }
}
```

Top-level **`name`** is the tool name. **`data.input`** is the tool argument dict (LangChain normalized).

**`on_tool_end`**

```json
{
  "event": "on_tool_end",
  "name": "get_active_bets",
  "data": {
    "input": {},
    "output": "<ToolMessage repr or structured — do not forward raw to clients>"
  }
}
```

**`data.output`** may be a `ToolMessage` string representation or large JSON — **not suitable** for direct SSE to UI. Phase 4 should use **`name` + truncated `input` only** for summaries; optionally parse output for a one-line count (e.g. `"count": 3`) if cheap and non-sensitive.

### Implementation note for `_stream_copilot`

Keep handling **`on_chat_model_stream`** unchanged for assistant prose. Add branches:

```python
if event.get("event") == "on_tool_start":
    ...
elif event.get("event") == "on_tool_end":
    ...
```

---

## 2. SSE framing: separate `event:` from assistant text

**Problem:** Current web/mobile clients treat every `data:` line as assistant markdown. Any JSON tool payload would corrupt the message.

**Recommendation (matches `01-PLAN.md`):**

- **`event: message`** + `data: <token or chunk>` for LLM text (escape newlines in `data` as today).
- **`event: copilot_tool`** + `data: {"phase":"start"|"end","name":"...","summary":"..."}` for tool trace.
- Terminator: keep **`data: [DONE]\n\n`** on default event (or also after last `message` — document one canonical form in code comment).

**Parsing:** Clients must buffer by **blank-line-separated SSE records** (`\n\n`), not line-by-line only, because `data` may be multi-line in theory (keep single-line JSON for tool frames to simplify).

**References:** HTML SSE spec — multiple `event:` types per connection is standard; `fetch()` + `ReadableStream` requires manual record parsing (no browser `EventSource` if custom headers for auth).

---

## 3. Safe “summary” construction

| Risk | Mitigation |
|------|------------|
| PII in tool `input` (e.g. free text) | Allowlist keys to show: `sport`, `game_id`, `game_query`, `market_id`, numeric limits. Strip `user_id` if ever passed explicitly. |
| Huge structures | `str()` then **slice to ~120 chars**, single line. |
| Output leakage | Default **end** summary = `"done"` or `"ok"`; optional derived hint only from known-safe keys (e.g. `count` from dict if output is JSON-parsable small dict). |

---

## 4. Web (Next.js) client

- **File:** `apps/web/src/components/copilot/chat-stream.tsx`
- **Change class:** Replace naive `chunk.split('\n')` + `line.startsWith('data: ')` with **record parser** (split `\n\n`, then parse `event:` + `data:`).
- **State:** Per assistant message: `content: string` + `steps: Array<{phase, name, summary}>` (or merge start/end into one row per tool).
- **A11y:** Collapsible “Steps” with `aria-expanded` / button label “Show tool steps”.

---

## 5. Mobile (Flutter) client

- **File:** `apps/mobile/lib/screens/copilot_screen.dart`
- **Change class:** Same SSE record contract; accumulate tool lines on the **last** assistant `CopilotMessage` during stream.
- **UI:** Muted `ListTile` / `Text` stack under bubble; cap visible rows with “+N more” if needed.

---

## 6. Tests

- **Extend** `apps/webhook_server/tests/unit/api/test_copilot_sse.py` with mocked `_stream_copilot` yielding multi-event records.
- Optional **unit** test in `packages/agent_pipeline` if extracting “summary from tool input” into a pure function (recommended for grep-stable acceptance).

---

## 7. Optional later (out of Phase 4 scope)

- Server structured logs mirroring `copilot_tool` frames (correlation id = `thread_id`).
- `EventSource` API route without auth for debugging only (not recommended for prod).

---

## Validation Architecture

Phase 4 validation is **automated-first** with one **manual** smoke:

| Dimension | Approach |
|-----------|----------|
| Contract | Pytest: response body contains `event: copilot_tool` and JSON with `phase` + `name`. |
| Regression | Pytest: assistant path still ends with `[DONE]`. |
| Web | No jest requirement in plan; optional Playwright later. |
| Mobile | `dart analyze` on edited screen. |
| Manual | One real request triggering a tool; Steps visible, no JSON in markdown. |

See **`04-VALIDATION.md`** for Nyquist-style sampling commands.

---

*End of research — executor should read this file before implementing `01-PLAN.md`.*
