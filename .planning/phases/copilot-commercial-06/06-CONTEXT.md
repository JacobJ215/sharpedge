# Copilot Commercial Phase 6 — Context

**Phase:** copilot-commercial-06  
**Source:** `.planning/COPILOT-COMMERCIAL-ROADMAP.md` Phase 6

## Boundary

Reduce **flat tool sprawl** and mis-routing: introduce a **routing layer** (supervisor or lightweight intent router) so Sports vs PM vs Portfolio intents prefer the right tool family. **AppGuide** (product help + deep links, no fabricated stats) is optional stretch.

## Staged approach

1. **Wave 1 (MVP):** **Soft router** — no new LangGraph subgraph yet: e.g. `COPILOT_FOCUS` env or first-turn classifier that **injects a short system addendum** listing allowed tool names for this session, or filters `bind_tools` subset. Lowest risk.
2. **Wave 2:** **LangGraph subgraphs** per domain sharing `MessagesState` checkpoint — larger refactor; only after Wave 1 proves routing value.

## Canonical refs

- `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py`
- `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py`
