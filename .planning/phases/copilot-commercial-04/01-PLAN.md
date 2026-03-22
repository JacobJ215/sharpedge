---
phase: copilot-commercial-04
plan: 01
type: execute
wave: 1
depends_on:
  - copilot-commercial-03
files_modified:
  - apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py
  - apps/webhook_server/tests/unit/api/test_copilot_sse.py
  - apps/web/src/components/copilot/chat-stream.tsx
  - apps/mobile/lib/screens/copilot_screen.dart
autonomous: true
requirements:
  - .planning/COPILOT-COMMERCIAL-ROADMAP.md (Phase 4)
  - .planning/phases/copilot-commercial-04/04-CONTEXT.md
  - .planning/phases/copilot-commercial-04/04-RESEARCH.md
must_haves:
  truths:
    - "SSE stream distinguishes assistant token chunks from tool-trace frames so clients do not append tool JSON into markdown."
    - "At minimum one tool start and one tool end (or combined) frame is emitted per tool invocation with tool name and human-readable summary."
    - "Web copilot UI shows tool activity (chips and/or collapsible Steps) for the latest assistant turn."
    - "Mobile copilot parses the same SSE contract and shows an equivalent compact tool list."
  artifacts:
    - path: apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py
      provides: SSE framing + event normalization from LangGraph astream_events
    - path: apps/web/src/components/copilot/chat-stream.tsx
      provides: client parser + Steps UI
---

<objective>
Implement **Copilot Commercial Phase 4 — transparency**: extend copilot SSE with **tool lifecycle frames** (name + short summary, no full raw payloads) and update **web + mobile** clients to render **Steps / sources** without corrupting assistant markdown.
</objective>

<execution_context>
@.planning/phases/copilot-commercial-04/04-CONTEXT.md
@.planning/phases/copilot-commercial-04/04-RESEARCH.md
@.planning/phases/copilot-commercial-04/04-VALIDATION.md
@apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py
@apps/web/src/components/copilot/chat-stream.tsx
@apps/mobile/lib/screens/copilot_screen.dart
</execution_context>

## Wave 1 — SSE contract + server + web + mobile + tests

### Task 0 — Event name spike (read-only)

<action>
Confirm tool event names against **`04-RESEARCH.md` §1** (verified: **`on_tool_start`**, **`on_tool_end`** on `astream_events(..., version="v1")`). Copy the exact strings into a module-level comment in `copilot.py` above `_stream_copilot` (no need to re-run spike unless LangGraph is upgraded).
</action>

<read_first>
- .planning/phases/copilot-commercial-04/04-RESEARCH.md
- apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py
- packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py
</read_first>

<acceptance_criteria>
- `copilot.py` contains a comment block listing the **exact** `event` keys used for tool start/end (verbatim strings).
- `grep -n "on_tool" apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py` returns at least one line (or the documented alternative keys if vendor uses different names).
</acceptance_criteria>

---

### Task 1 — SSE framing for tokens vs tool frames

<action>
Refactor `_stream_copilot` so assistant text uses **explicit SSE event type** `message` and tool trace uses **`event: copilot_tool`** with **JSON `data`** payload:

```json
{"phase":"start","name":"<tool_name>","summary":"<short string>"}
{"phase":"end","name":"<tool_name>","summary":"<short string>"}
```

**LangGraph mapping (from `04-RESEARCH.md` §1):**

- On **`on_tool_start`**: read `event["name"]` and `event.get("data", {}).get("input")` → build summary → yield `event: copilot_tool` + `phase: start`.
- On **`on_tool_end`**: read `event["name"]`; **do not** forward `data.output` raw → yield `phase: end` with summary `"done"` or a **safe** one-liner (e.g. parsed `count` from small JSON dict only if trivial).

**Summary helper:** Add a pure function in `copilot.py` or `copilot_sse_utils.py` next to the route, e.g. `_summarize_tool_input(name: str, inp: object) -> str`, implementing **`04-RESEARCH.md` §3 allowlist** (`sport`, `game_id`, `game_query`, `market_id`, numeric limits) — max **120** chars, single line, **omit** `user_id` / unknown keys. Unit-test the helper in `apps/webhook_server/tests/...` (new small test module is OK).

Rules:
- **Do not** stream full tool `input`/`output` dicts to the client.
- Preserve existing terminal `data: [DONE]\n\n` on default event (or document new terminator); clients must still detect end of stream.
- Error path: unchanged JSON error in `data:` acceptable if still clearly not assistant prose (e.g. prefix or separate `event: error`).

Concrete wire format example (must match implementation):

```
event: message
data: Hello

event: copilot_tool
data: {"phase":"start","name":"search_games","summary":"search_games sport=NBA"}

event: message
data: world

event: copilot_tool
data: {"phase":"end","name":"search_games","summary":"done"}

data: [DONE]

```

Use `\n\n` record separators per SSE spec.
</action>

<read_first>
- apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py (full file)
</read_first>

<acceptance_criteria>
- `grep -n "event: message\\|event: copilot_tool" apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py` matches yielded SSE lines (choose one consistent pair; adjust grep if names differ but document in comment).
- `grep -n "on_tool_start\\|on_tool_end" apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py` matches branches handling LangGraph tool events.
- `grep -n "on_chat_model_stream" apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py` still exists for token path.
- `grep -n "_summarize_tool_input\\|summarize_tool_input" apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py apps/webhook_server/src/sharpedge_webhooks/` matches the summary helper (path adjusted if extracted to a sibling module).
- Fallback when graph is None: still returns stream ending with `data: [DONE]`.
</acceptance_criteria>

---

### Task 2 — API tests for SSE tool frames

<action>
Extend `apps/webhook_server/tests/unit/api/test_copilot_sse.py`:

1. Patch `_stream_copilot` with an async generator that yields at least one `event: copilot_tool` record and one `event: message` record, then `[DONE]`.
2. Assert client response text **contains** substring `event: copilot_tool` (or chosen event name) and valid JSON with `"phase":"start"` and `"name"`.

Add a second test: **legacy** token-only mock still parses (if any test relied on raw `data: text` without `event:` — update expectations so all tests align with new contract).
</action>

<read_first>
- apps/webhook_server/tests/unit/api/test_copilot_sse.py
</read_first>

<acceptance_criteria>
- `uv run pytest apps/webhook_server/tests/unit/api/test_copilot_sse.py -q` exits 0 from repo root (matches **`04-VALIDATION.md`** quick command).
- New test function name includes `tool` or `copilot_tool` (grep-verifiable).
- Any new test module for `_summarize_tool_input` is included in the same `uv run pytest apps/webhook_server/tests/unit/api/ ...` invocation the executor runs (single command must exit 0).
</acceptance_criteria>

---

### Task 3 — Web client parser + Steps UI

<action>
Update `chat-stream.tsx` fetch reader loop:

1. Buffer SSE **records** (split on `\n\n`); within each record parse optional `event:` line and `data:` line(s).
2. If `event: message` (or default) and data is not `[DONE]` and not a JSON object with `"phase"`, append to assistant text (preserve existing `\\n` unescape behavior for prose).
3. If `event: copilot_tool` (or chosen name), parse JSON and append to a `steps` array on the **current assistant message** (last assistant bubble).
4. UI: below assistant markdown for that turn, render a collapsible **“Steps”** (closed by default on mobile-width; open optional on desktop) listing `name` — `summary` for start/end (dedupe or show “Running…” then “Done” per tool as appropriate).

Do not append tool JSON strings into `assistantMsg` content.
</action>

<read_first>
- apps/web/src/components/copilot/chat-stream.tsx (full file)
</read_first>

<acceptance_criteria>
- `grep -n "copilot_tool\\|Steps" apps/web/src/components/copilot/chat-stream.tsx` has matches.
- `grep -n "event: message" apps/web/src/components/copilot/chat-stream.tsx` OR parser comment documents handling of SSE `event:` lines (grep for `event:`).
</acceptance_criteria>

---

### Task 4 — Mobile client parser + compact tool list

<action>
Update `copilot_screen.dart` streaming loop to:

1. Split on blank-line SSE record boundaries OR parse lines to detect `event:` prefix (match web contract).
2. On tool frames, append to a per-assistant-turn list of strings (e.g. `"{name}: {summary}"`).
3. Show under the assistant bubble a small collapsible or always-visible muted list (max ~5 lines, scroll if more) for the **current** streaming assistant message; clear when starting a new assistant message.

Ensure existing token accumulation for normal `message` events remains correct.
</action>

<read_first>
- apps/mobile/lib/screens/copilot_screen.dart (streaming section)
</read_first>

<acceptance_criteria>
- `grep -n "copilot_tool\\|event:" apps/mobile/lib/screens/copilot_screen.dart` has matches.
- `dart analyze apps/mobile/lib/screens/copilot_screen.dart` exits 0 (no issues).
</acceptance_criteria>

---

## Verification (phase goal)

- Manual: with real backend, ask a question that triggers `search_games` or `get_active_bets`; web UI shows Steps; assistant text contains no raw JSON tool payloads.

---

## Plan metadata

- **2026-03-22:** Plan created via `/gsd-plan-phase` Copilot Commercial Phase 4 (`copilot-commercial-04`; not in main `.planning/ROADMAP.md` numeric phases — directory is canonical).
- **2026-03-22:** Replanned with **`/gsd-plan-phase copilot-commercial-04 --skip-research`** — merged **`04-RESEARCH.md`** (verified `on_tool_start` / `on_tool_end`, payload shapes, PII allowlist) into Task 1; linked **`04-VALIDATION.md`**; added summary-helper + grep criteria for LangGraph branches.
