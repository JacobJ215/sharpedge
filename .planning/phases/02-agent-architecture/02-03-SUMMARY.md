---
phase: 02-agent-architecture
plan: 03
subsystem: agent-pipeline
tags: [langgraph, react-agent, copilot, tool-calling, session-management, tiktoken, tdd, wave-2]
dependency_graph:
  requires: [02-02 (ANALYSIS_GRAPH singleton, 9-node graph)]
  provides:
    - copilot/session.py: trim_conversation() + MAX_TOKENS=80000
    - copilot/tools.py: 10 @tool-decorated functions wrapping service layer
    - copilot/agent.py: build_copilot_graph() ReAct StateGraph + COPILOT_GRAPH singleton
  affects: [02-04 (Discord /copilot command wires to COPILOT_GRAPH)]
tech_stack:
  added:
    - langgraph MessagesState + ToolNode ReAct pattern (separate from 9-node analysis graph)
    - langchain_core.tools @tool decorator (StructuredTool)
    - tiktoken.encoding_for_model() for accurate GPT-4o token counting
    - lazy COPILOT_GRAPH singleton (None when OPENAI_API_KEY absent)
  patterns:
    - ReAct: agent_node trims before every llm.invoke(); should_continue routes to tools or END
    - Tool separation: service layer (packages/*) called from tools; tools never call Supabase directly
    - Offline-safe singleton: _try_build_graph() returns None if no API key (test/CI environments)
    - StructuredTool.invoke(dict) is the correct call pattern (not tool_fn(**kwargs))
key_files:
  created:
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/__init__.py
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/session.py
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py
  modified:
    - packages/database/src/sharpedge_db/models.py (BankrollInfo.sizing_table type fix)
    - tests/unit/agent_pipeline/test_session.py (remove xfail, fix token assertion)
    - tests/unit/agent_pipeline/test_copilot.py (remove xfail, mock LLM)
    - tests/unit/agent_pipeline/test_copilot_tools.py (remove xfail, mock service, use .invoke())
decisions:
  - StructuredTool from @tool is not directly callable via (**kwargs) — tests updated to use .invoke(dict)
  - COPILOT_GRAPH singleton is None when OPENAI_API_KEY absent to support offline/test environments
  - trim_conversation accepts plain dicts (not BaseMessage) for compatibility with LangGraph MessagesState dicts and tests
  - test_session.py over-limit test uses tiktoken for assertion (chars/4 heuristic incompatible with word-based content at 80k token limit)
  - compare_books tool returns offline note when ODDS_API_KEY is absent (no crash)
  - get_prediction_market_edge returns Phase 3 stub message (PM scanner deferred)
metrics:
  duration: ~35 minutes
  completed: "2026-03-13"
  tasks_completed: 2
  files_created: 4
  files_modified: 4
---

# Phase 2 Plan 03: BettingCopilot ReAct Graph + 10 Tools + Session Management Summary

**One-liner:** ReAct MessagesState copilot graph with 10 service-layer tool wrappers and tiktoken-based conversation trimming — all 13 unit tests GREEN with fully mocked service/LLM calls.

## What Was Built

Wave 2 of Phase 2 implements the BettingCopilot as a separate LangGraph StateGraph from the 9-node analysis graph. Users can ask natural language questions; the copilot calls relevant tools and responds with portfolio context.

### Task 1: trim_conversation Session Management (TDD)

**session.py** (`packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/session.py`):
- `MAX_TOKENS = 80_000` — leaves 48k buffer below GPT-4o's 128k limit for tool call responses
- `trim_conversation(messages, model="gpt-4o")` accepts plain dicts with `role`/`content` keys
- Separates system messages (always preserved) from conversation messages
- Uses `tiktoken.encoding_for_model(model)` for accurate token counting with 4-token per-message overhead
- Walks conversation from newest to oldest, keeps as many messages as fit within budget
- Logs WARNING when trimming occurs: `"Trimming conversation: N -> M messages"`
- Falls back to `cl100k_base` encoding for unknown model names

**test_session.py updates:**
- Removed `xfail(strict=True)` markers
- Fixed over-limit test to use `tiktoken` for token assertion (chars/4 heuristic overcounts word-based content by ~5x)
- Both tests GREEN

### Task 2: 10 Copilot Tools + BettingCopilot ReAct Graph (TDD)

**tools.py** (`packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py`, 382 lines):

All 10 tools use `@tool` from `langchain_core.tools`. Each returns a `dict` (JSON-serializable), handles exceptions by returning `{"error": str(e)}`, and limits results to 10 records.

| # | Tool | Service Layer | Returns |
|---|------|--------------|---------|
| 1 | `get_active_bets` | `sharpedge_db.queries.bets.get_pending_bets` | Top 10 pending bets dict |
| 2 | `get_portfolio_stats` | `sharpedge_db.queries.bets.get_performance_summary` | Win rate, ROI, units_won |
| 3 | `analyze_game` | `ANALYSIS_GRAPH.ainvoke` (lazy import) | Analysis report str (≤2000 chars) |
| 4 | `search_value_plays` | `sharpedge_db.queries.value_plays.get_active_value_plays` | Top 5 value plays |
| 5 | `check_line_movement` | `sharpedge_db.queries.line_movements.get_line_movements` | Last 10 movements |
| 6 | `get_sharp_indicators` | `get_line_movements` + `get_movement_summary` | Steam/RLM counts + signals |
| 7 | `estimate_bankroll_risk` | `sharpedge_models.monte_carlo.simulate_bankroll` | Ruin prob, p50/p05/p95 |
| 8 | `get_prediction_market_edge` | Phase 3 stub | `{"note": "PM scanner available in Phase 3."}` |
| 9 | `compare_books` | `sharpedge_odds.client.OddsClient` | Offline note or book list |
| 10 | `get_model_predictions` | `sharpedge_db.queries.projections.get_projection` | Projected spread/total/confidence |

**agent.py** (`packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py`, 115 lines):
- `build_copilot_graph(tools=None)` builds ReAct StateGraph: agent_node → should_continue → tools or END
- `agent_node` converts MessagesState messages to plain dicts, calls `trim_conversation()`, then passes original BaseMessage objects to LLM
- `should_continue` checks `last.tool_calls` — empty list → END
- `COPILOT_GRAPH = _try_build_graph()` — returns None if OPENAI_API_KEY absent (offline/test safe)
- All 10 tool names imported into agent.py namespace for monkeypatch compatibility in tests

**test_copilot.py updates:**
- Removed `xfail(strict=True)` marker
- Mocks `ChatOpenAI` with a pre-canned AIMessage response containing game names
- Mocks `get_active_bets` at `sharpedge_agent_pipeline.copilot.agent.get_active_bets`
- No real API calls — test passes in offline/CI environments

**test_copilot_tools.py updates:**
- Removed `xfail(strict=True)` marker
- All 6 service layer functions mocked via `unittest.mock.patch`
- Calls `tool_fn.invoke(kwargs)` (correct StructuredTool invocation pattern)
- All 10 parametrized tool tests GREEN

## Verification Results

1. `uv run pytest tests/unit/agent_pipeline/test_copilot.py tests/unit/agent_pipeline/test_copilot_tools.py tests/unit/agent_pipeline/test_session.py -x -q` — **13 passed** ✓
2. `from sharpedge_agent_pipeline.copilot.tools import get_active_bets, ...; print('10 tools loaded')` — **10 tools loaded** ✓
3. `from sharpedge_agent_pipeline.copilot.session import trim_conversation, MAX_TOKENS; print(MAX_TOKENS)` — **80000** ✓
4. `wc -l tools.py` — **382 lines** (under 400 limit) ✓; `agent.py` — **115 lines** (under 150) ✓

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] BankrollInfo.sizing_table used Field as type annotation**
- **Found during:** Task 2 — importing sharpedge_db caused pydantic schema generation error
- **Issue:** `sizing_table: dict[str, Field] = {}` in `sharpedge_db/models.py` caused `NameError: name 'Any' is not defined` in pydantic's schema evaluator; `Field` is not a valid type annotation
- **Fix:** Added `from typing import Any` and changed `dict[str, Field]` to `dict[str, Any]`
- **Files modified:** `packages/database/src/sharpedge_db/models.py`

**2. [Rule 1 - Bug] Test content insufficient to exceed 80k token budget**
- **Found during:** Task 1 — test_session.py over-limit test used "X " * 200 per message (≈200 tiktoken tokens/message × 200 messages ≈ 40k tokens < 80k)
- **Issue:** `len(result) < len(messages)` assertion could never pass — trimming would not occur
- **Fix:** Changed test content to `f"tok{i}"` words repeated 1000× (~4000 tokens/message × 200 messages ≈ 800k tokens >> 80k) and assertion to use actual tiktoken counting instead of chars/4 heuristic
- **Files modified:** `tests/unit/agent_pipeline/test_session.py`

**3. [Rule 1 - Bug] StructuredTool not callable via (**kwargs)**
- **Found during:** Task 2 — test_copilot_tools.py called `tool_fn(**kwargs)` but LangChain StructuredTool removed `__call__` — `TypeError: 'StructuredTool' object is not callable`
- **Fix:** Updated test to use `tool_fn.invoke(kwargs)` which is the documented StructuredTool invocation API
- **Files modified:** `tests/unit/agent_pipeline/test_copilot_tools.py`

**4. [Rule 1 - Bug] Module-level COPILOT_GRAPH crashed without OPENAI_API_KEY**
- **Found during:** Task 2 — importing agent.py raised `openai.OpenAIError` in test environments
- **Fix:** Wrapped singleton build in `_try_build_graph()` that returns None when API key absent; callers use `build_copilot_graph()` directly in production
- **Files modified:** `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py`

## Self-Check

Files created:
- [x] packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/__init__.py
- [x] packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/session.py
- [x] packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py
- [x] packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py
- [x] .planning/phases/02-agent-architecture/02-03-SUMMARY.md

Note: git commit was blocked by sandbox restrictions during this execution session.
All implementation files and test updates are staged in git index (git add completed).
Commits pending user authorization.

## Self-Check: PASSED
