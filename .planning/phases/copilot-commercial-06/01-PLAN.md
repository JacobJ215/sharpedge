---
phase: copilot-commercial-06
plan: 01
type: execute
wave: 1
depends_on:
  - copilot-commercial-05
files_modified:
  - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py
  - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/router.py
  - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/prompts.py
  - packages/agent_pipeline/tests/test_copilot_router.py
autonomous: true
requirements:
  - .planning/phases/copilot-commercial-06/06-CONTEXT.md
must_haves:
  truths:
    - "Copilot can restrict or bias tool visibility by session intent without breaking existing default behavior when env is unset."
    - "Default graph behavior matches today when router is disabled."
---

<objective>
**Commercial Phase 6 — Wave 1 soft router:** configurable intent → tool subset + system addendum; no subgraph split yet.
</objective>

## Task 1 — Router helper

<action>
Add `copilot/router.py` with e.g. `resolve_tool_subset(env_focus: str | None) -> tuple[list, str]` returning `(tools, system_addendum)` where `env_focus` reads `COPILOT_ROUTER_FOCUS` values like `sports`, `pm`, `portfolio`, `all` (default `all` = full `COPILOT_TOOLS`, empty addendum). Subsets are explicit allowlists of tool **names** (strings), not heuristics.

`build_copilot_graph(tools=..., checkpointer=...)` must accept the filtered list (already supported).
</action>

<read_first>
- packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py
- packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py (`COPILOT_TOOLS`, `_copilot_tool_list`)
</read_first>

<acceptance_criteria>
- `router.py` exists; `grep -n COPILOT_ROUTER_FOCUS packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/router.py` matches.
- Unit test: `packages/agent_pipeline/tests/test_copilot_router.py` asserts `all` returns full count and `pm` returns strict subset of names.
</acceptance_criteria>

## Task 2 — Wire into graph build path used by webhook

<action>
Webhook uses `build_copilot_graph` from agent — ensure **lifespan** and **fallback** both call the same factory. Option A: `build_copilot_graph()` reads env inside factory. Option B: pass tools from router in `copilot_lifespan` only — then document that ephemeral graph path must also use router. Prefer **single factory** inside `build_copilot_graph` so bot + webhook stay aligned.

Prepend optional `system_addendum` to `COPILOT_SYSTEM_PROMPT` in `agent_node` via `_with_system_prompt` or equivalent (concatenate below main prompt).
</action>

<read_first>
- apps/webhook_server/src/sharpedge_webhooks/copilot_lifespan.py
</read_first>

<acceptance_criteria>
- `grep -n router\\|COPILOT_ROUTER_FOCUS packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py` matches.
- `uv run pytest packages/agent_pipeline/tests/test_copilot_router.py packages/agent_pipeline/tests/test_copilot.py -q` exits 0 (adjust `test_copilot.py` if prompt length assertion brittle).
</acceptance_criteria>

## Task 3 — Document Wave 2 (no code)

<action>
Maintain **`06-WAVE2-SUBGRAPHS.md`** (criteria to promote to LangGraph subgraphs). Update only if product SLOs change. No subgraph implementation in Wave 1.
</action>

<read_first>
- .planning/phases/copilot-commercial-06/06-WAVE2-SUBGRAPHS.md
</read_first>

<acceptance_criteria>
- `grep -n Wave 2 .planning/phases/copilot-commercial-06/06-WAVE2-SUBGRAPHS.md` matches.
- `grep -n subgraph .planning/phases/copilot-commercial-06/06-WAVE2-SUBGRAPHS.md` matches.
</acceptance_criteria>
