---
phase: copilot-commercial-05
plan: 01
type: execute
wave: 1
depends_on:
  - copilot-commercial-04
files_modified:
  - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py
  - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/pm_tools_logic.py
  - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/prompts.py
  - packages/agent_pipeline/tests/test_copilot_tools_count.py
  - tests/unit/agent_pipeline/test_copilot_tools.py
autonomous: true
requirements:
  - .planning/phases/copilot-commercial-05/05-CONTEXT.md
must_haves:
  truths:
    - "At least one new copilot tool returns a capped list of PM edges without requiring user-supplied market_id."
    - "At least one tool surfaces regime and/or correlation insight using sharpedge_analytics."
    - "Tool outputs remain JSON dicts with error keys; no order placement."
---

<objective>
**Commercial Phase 5 — PM depth:** add capped **`sharpedge_analytics`**-backed copilot tools so common PM questions work without pasting tickers; align prompts; extend tests.
</objective>

## Task 1 — `pm_tools_logic` module

<action>
Add `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/pm_tools_logic.py` with:

1. `scan_top_pm_edges_impl(*, max_markets: int = 40, max_edges: int = 10) -> dict` — fetch a bounded set of open markets from Kalshi and/or Polymarket (reuse async patterns from `get_prediction_market_edge`), run `scan_pm_edges(kalshi, poly, model_probs={})`, return `{"edges": [...], "count": N}` with each edge dict capped to fields: `platform`, `market_id`, `market_title`, `edge_pct`, `alpha_badge`, `regime` (and `market_prob`/`model_prob` if small).

2. `check_pm_correlation_impl(pm_market_title: str, user_id: str) -> dict` — load pending bets via `get_pending_bets`, call `detect_correlated_positions` or `compute_entity_correlation` as appropriate; return `{"correlation": float|None, "warnings": [...]}` capped at 5 items.

Handle missing API keys with `{"error": "...", "edges":[]}` / similar. Use `asyncio.run` or thread pool like existing PM tool if needed; `close()` clients.
</action>

<read_first>
- packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py (get_prediction_market_edge)
- packages/analytics/src/sharpedge_analytics/pm_edge_scanner.py
- packages/analytics/src/sharpedge_analytics/pm_correlation.py
</read_first>

<acceptance_criteria>
- `pm_tools_logic.py` exists and defines `scan_top_pm_edges_impl` and `check_pm_correlation_impl`.
- `grep -n scan_pm_edges packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/pm_tools_logic.py` matches.
</acceptance_criteria>

## Task 2 — Register `@tool` wrappers

<action>
In `tools.py`, add `scan_top_pm_edges` and `check_pm_correlation` (names adjustable) with docstrings; wire `RunnableConfig` for `user_id` on correlation tool. Append to `COPILOT_TOOLS`. Update `test_copilot_tools_count.py` `_EXPECTED_ALWAYS` and `test_copilot_tools.py` matrix + patches (mock impls to avoid network).
</action>

<read_first>
- packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py
- packages/agent_pipeline/tests/test_copilot_tools_count.py
</read_first>

<acceptance_criteria>
- `uv run pytest packages/agent_pipeline/tests/test_copilot_tools_count.py tests/unit/agent_pipeline/test_copilot_tools.py -q` exits 0.
</acceptance_criteria>

## Task 3 — Prompt

<action>
Extend `COPILOT_SYSTEM_PROMPT`: when user asks for PM edges / “what’s mispriced”, prefer `scan_top_pm_edges`; for overlap with sportsbook bets, `check_pm_correlation` + `pm_market_title`.
</action>

<read_first>
- packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/prompts.py
</read_first>

<acceptance_criteria>
- `grep -n scan_top_pm_edges\\|check_pm_correlation packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/prompts.py` matches at least one line.
</acceptance_criteria>
