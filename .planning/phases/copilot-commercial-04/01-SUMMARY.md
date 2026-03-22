---
phase: copilot-commercial-04
plan: "01"
subsystem: api
tags: [sse, copilot, langgraph, nextjs, flutter]

requires:
  - phase: copilot-commercial-03
    provides: prior copilot SSE baseline
provides:
  - SSE contract with event:message vs event:copilot_tool
  - Server-side tool start/end frames from on_tool_start / on_tool_end
  - Web Steps panel + mobile tool trace list
affects: [web-copilot, mobile-copilot, webhook_server]

tech-stack:
  added: []
  patterns:
    - "Blank-line SSE record parsing shared conceptually across web and Flutter"

key-files:
  created:
    - apps/webhook_server/tests/unit/api/test_copilot_tool_summary.py
  modified:
    - apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py
    - apps/webhook_server/tests/unit/api/test_copilot_sse.py
    - apps/web/src/components/copilot/chat-stream.tsx
    - apps/mobile/lib/screens/copilot_screen.dart
    - apps/mobile/lib/widgets/copilot_widgets.dart

key-decisions:
  - "Assistant tokens only via event:message; tool trace only via event:copilot_tool JSON"
  - "Tool input summaries use allowlisted keys + 120-char cap; end phase defaults to done or count=N from small JSON"

patterns-established:
  - "LangGraph v1 stream events on_tool_start / on_tool_end documented in copilot.py header"

requirements-completed: []

duration: —
completed: 2026-03-22
---

# Copilot Commercial Phase 4 — Plan 01 Summary

**Delivered a typed SSE contract so tool lifecycle frames never corrupt assistant markdown, with matching web Steps UI and mobile tool traces.**

## Accomplishments

- Server emits `event: message` for `on_chat_model_stream` and `event: copilot_tool` for `on_tool_start` / `on_tool_end`, plus `_summarize_tool_input` with PII-aware allowlist.
- API tests cover tool summary helper and mocked `copilot_tool` frames; persistence mock uses `event: message`.
- Web client buffers `\n\n`-delimited SSE records; collapsible Steps panel (desktop starts expanded ≥768px).
- Mobile client accumulates tool lines on the streaming assistant bubble with a scroll-capped muted list.

## Verification

- `uv run pytest apps/webhook_server/tests/unit/api/test_copilot_sse.py apps/webhook_server/tests/unit/api/test_copilot_tool_summary.py -q` — pass
- `dart analyze` on modified Dart files — no issues
- `npm run build` (apps/web) — run in CI/local before merge

## Self-Check: PASSED
