---
phase: 08-frontend-polish-and-full-backend-wiring
plan: "06"
subsystem: copilot-auth-wiring
tags: [wire-06, copilot, auth, fastapi, langchain, flutter, next-js]
dependency_graph:
  requires: [08-02, 08-03]
  provides: [copilot-auth-aware-endpoint, web-chat-auth-header, flutter-chat-auth-header]
  affects: [apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py, apps/web/src/components/copilot/chat-stream.tsx, apps/mobile/lib/screens/copilot_screen.dart]
tech_stack:
  added: []
  patterns: [optional-auth-header, langchain-runnable-config, supabase-getSession, provider-pattern]
key_files:
  created: []
  modified:
    - apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py
    - apps/web/src/components/copilot/chat-stream.tsx
    - apps/mobile/lib/screens/copilot_screen.dart
decisions:
  - "Auth header extracted inline in the endpoint (not via Depends) so that absent/invalid tokens degrade to user_id=None rather than returning 401"
  - "user_id threaded via graph config['configurable']['user_id'] rather than tool input schema — keeps tool signatures clean and follows LangChain RunnableConfig pattern"
  - "chat-stream.tsx modified (not copilot/page.tsx) because page.tsx delegates entirely to the ChatStream component which owns the fetch call"
  - "Flutter uses Provider.of<AppState>(context, listen: false).authToken — consistent with how other screens (line_movement, value_plays, bankroll) access the token"
  - "Pre-existing roi-curve.tsx build failure (recharts defs export) not fixed — documented as pre-existing in 08-03-SUMMARY, out of scope"
metrics:
  duration: "~8 minutes"
  completed_date: "2026-03-15"
  tasks_completed: 2
  files_created: 0
  files_modified: 4
---

# Phase 08 Plan 06: Copilot Auth Token Wiring Summary

**One-liner:** Optional Authorization header added to the copilot SSE endpoint — user_id threaded via LangChain RunnableConfig into get_active_bets and get_portfolio_stats; web ChatStream and Flutter CopilotScreen both forward the session token.

---

## What Was Built

### Task 1: Auth-aware copilot endpoint + web client token forwarding

**`apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py`:**
- Added `Optional[str] = Header(None, alias="Authorization")` parameter to `copilot_chat`
- Added `_resolve_user_id(token)` helper — calls Supabase `get_user()` inline; returns `None` on any error or missing env vars (no 401 raised)
- Token extracted via `authorization.removeprefix("Bearer ").strip()`
- `user_id` passed into graph via `config={"configurable": {"user_id": user_id}}`
- Unauthenticated calls continue to work — `user_id=None` → tools return placeholder/demo data

**`packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py`:**
- Added `from langchain_core.runnables import RunnableConfig` import
- `get_active_bets` and `get_portfolio_stats` each accept `config: RunnableConfig = None`
- Both read `config["configurable"].get("user_id")` and prefer it over the `user_id` tool input arg
- COPILOT_TOOLS list unchanged — still 12 entries (10 base + 2 VENUE_TOOLS)

**`apps/web/src/components/copilot/chat-stream.tsx`:**
- Added `import { supabase } from '@/lib/supabase'`
- `sendMessage` now calls `supabase.auth.getSession()` before the fetch
- If `session.access_token` present: adds `Authorization: Bearer {token}` header
- If no session: sends request without auth header (public copilot still works)

### Task 2: Flutter CopilotScreen auth token forwarding

**`apps/mobile/lib/screens/copilot_screen.dart`:**
- Added `import 'package:provider/provider.dart'` and `import '../providers/app_state.dart'`
- In `_send()`, reads `Provider.of<AppState>(context, listen: false).authToken`
- Adds `request.headers['Authorization'] = 'Bearer $token'` before `.send()` when token non-null
- All SSE parsing, message list, input field, and loading dot logic unchanged
- File stays at 500 lines (498 after changes)

---

## Test Results

| Test | Result |
|------|--------|
| test_copilot_tools_count.py::test_copilot_tools_has_12_entries | PASSED |
| test_copilot_tools_count.py::test_copilot_tools_includes_venue_tools | PASSED |
| test_copilot_tools_count.py::test_copilot_tools_includes_base_tools | PASSED |
| flutter analyze lib/screens/copilot_screen.dart | No issues |

**Note:** `npm run build` fails due to pre-existing `roi-curve.tsx` recharts type error (documented in 08-03-SUMMARY as deferred, unrelated to this plan). Our TypeScript changes in chat-stream.tsx compile cleanly (`tsc --noEmit` reports no errors for our files).

---

## Checkpoint Pending

**Task 3 (checkpoint:human-verify) is pending user approval.** The automated changes are complete and committed. The human-verify gate requires:

- Web: full 10+ turn conversation with all 12 tools verified via /copilot UI
- Flutter: 3+ turn conversation with SSE streaming verified on device
- Specific prompt: "What are my active bets?" should return real user data (not demo) when authenticated

---

## Deviations from Plan

### Route of web auth token injection

**Found during:** Task 1 code reading
**Issue:** `copilot/page.tsx` is a thin wrapper that renders `<ChatStream />`. The SSE fetch call lives in `apps/web/src/components/copilot/chat-stream.tsx`, not in page.tsx. Plan specified modifying page.tsx.
**Fix:** Modified `chat-stream.tsx` instead — this is the correct integration point since it owns the fetch call. page.tsx has no fetch logic.
**Rule:** Rule 1 (Auto-fix) — modifying the wrong file would not achieve the auth header injection.

---

## Commits

| Hash | Message |
|------|---------|
| 7c820da | feat(08-06): copilot endpoint accepts optional auth — user_id threaded to tools |
| 3b6fff4 | feat(08-06): web + Flutter CopilotScreen forward auth token in SSE POST |

---

## Self-Check

Files modified:
- apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py: FOUND
- packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py: FOUND
- apps/web/src/components/copilot/chat-stream.tsx: FOUND
- apps/mobile/lib/screens/copilot_screen.dart: FOUND

## Self-Check: PASSED
