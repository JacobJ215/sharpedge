# Phase 2: Agent Architecture - Research

**Researched:** 2026-03-14
**Domain:** LangGraph StateGraph orchestration, BettingCopilot, LLM setup evaluator, alpha-ranked alert dispatch
**Confidence:** HIGH (LangGraph API confirmed from PyPI + GitHub source; existing codebase read directly)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AGENT-01 | 9-node LangGraph StateGraph: route_intent → fetch_context → detect_regime → run_models → calculate_ev → validate_setup → compose_alpha → size_position → generate_report | LangGraph 1.1.2 StateGraph with TypedDict state + Annotated reducers; detect_regime/run_models/calculate_ev fan-out in parallel; Phase 1 outputs (AlphaComposer, RegimeDetector, MonteCarloSimulator, EVCalculator) are the computation back-ends |
| AGENT-02 | LLM setup evaluator returns PASS/WARN/REJECT with reasoning before alert dispatch | ChatOpenAI.with_structured_output(SetupEvalResult) using Pydantic model; GPT-4o-mini for cost; validate_setup node in the StateGraph; retry_count in state prevents infinite re-route |
| AGENT-03 | BettingCopilot answers NL questions with full portfolio context (active bets, bankroll exposure, regime state) | Separate ReAct-style agent node within or adjacent to the graph; reads from Supabase via existing sharpedge_db query modules (get_pending_bets, get_performance_summary); regime state passed from main graph state |
| AGENT-04 | BettingCopilot supports 10 tools: get_active_bets, get_portfolio_stats, analyze_game, search_value_plays, check_line_movement, get_sharp_indicators, estimate_bankroll_risk, get_prediction_market_edge, compare_books, get_model_predictions | @tool decorated functions wrapping existing service layer (bet_service, bankroll_service, odds_service, sharpedge_analytics); tiktoken 0.12.0 for token counting; trim_messages sliding window prevents context overflow |
| AGENT-05 | Value play alerts ranked by alpha score before dispatching (highest alpha posts first) | Intercept _pending_value_alerts in value_scanner_job.py; replace rank_value_plays() (sorts by ev_percentage) with sort by BettingAlpha.alpha_score before appending to _pending_value_alerts; alpha scores computed by AlphaComposer from Phase 1 |
</phase_requirements>

---

## Summary

Phase 2 replaces the existing flat 3-agent OpenAI Agents SDK setup in `apps/bot/src/sharpedge_bot/agents/` with a 9-node LangGraph 1.1.x StateGraph. The graph routes every betting analysis request through a sequential pipeline with one parallel fan-out: `detect_regime`, `run_models`, and `calculate_ev` can run simultaneously because they each write to distinct state keys. All Phase 1 quant modules (AlphaComposer, MonteCarloSimulator, RegimeDetector, EVCalculator, KeyNumberZoneDetector) become computation nodes called from within graph nodes — the nodes own I/O, the quant modules own computation.

The BettingCopilot is a ReAct agent embedded as a node in the same StateGraph or invoked as a sub-graph. It uses the 10 `@tool`-decorated functions that wrap existing service modules, never making direct DB calls itself. Context window overflow is mitigated via `trim_messages` from `langchain_core.messages` with a `max_tokens=80000` sliding window, plus `tiktoken` for token counting. The LLM setup evaluator uses `ChatOpenAI.with_structured_output()` with a Pydantic model to return a typed `SetupEvalResult` (verdict: PASS/WARN/REJECT, reasoning: str) — this is more reliable than prompt-parsing.

The alert dispatch intercept for AGENT-05 is minimal: replace the `rank_value_plays()` sort key in `value_scanner_job.py` with a sort on `alpha_score` (populated by AlphaComposer) before plays are appended to `_pending_value_alerts`.

**Primary recommendation:** Place the LangGraph pipeline in a new package `packages/agent_pipeline/` to avoid bloating `apps/bot/` further. The bot commands call into `agent_pipeline` as a black-box async function. This keeps the 500-line file limit achievable and makes the pipeline independently testable.

---

## Standard Stack

### Core (new additions for Phase 2)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| langgraph | 1.1.2 | StateGraph 9-node orchestration, parallel fan-out, loop guards | Latest stable (confirmed PyPI 2026-03-13); replaces OpenAI Agents SDK flat setup; native parallel execution, recursion_limit, checkpointing |
| langchain-openai | 0.3.14 | ChatOpenAI wrapper with structured output, bind_tools | Required for with_structured_output() (AGENT-02) and tool-calling in BettingCopilot (AGENT-04) |
| langchain-core | (pulled by langgraph) | BaseMessage, trim_messages, @tool decorator | trim_messages is the correct mitigation for Pitfall 6; @tool replaces @function_tool from OpenAI Agents SDK |
| tiktoken | 0.12.0 | Token counting for context window management | Count tokens before LLM calls; alert at 80k; GPT-4o context is 128k |
| langgraph-checkpoint-postgres | 3.0.4 | PostgreSQL checkpointing for BettingCopilot session memory | Persists conversation state across Discord sessions; uses existing Supabase connection |

### Existing (extend, do not replace)

| Library | Version | Purpose | Why Keep |
|---------|---------|---------|----------|
| sharpedge-models | workspace | AlphaComposer, MonteCarloSimulator, EVCalculator, WalkForwardBacktester | Phase 1 outputs; graph nodes call these as pure functions |
| sharpedge-analytics | workspace | RegimeDetector, KeyNumberZoneDetector, ValueScanner | Phase 1 outputs; detect_regime node wraps RegimeDetector |
| sharpedge-db | workspace | Supabase query modules (get_pending_bets, get_performance_summary, etc.) | BettingCopilot tools read portfolio data from here |
| sharpedge-odds | workspace | OddsClient with Redis caching | fetch_context node calls OddsClient once; all downstream nodes read from state |
| redis-py | 5.0+ | BettingCopilot session state TTL storage (30-min sessions) | Already present; store conversation snapshots by Discord user ID |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| langgraph 1.1.x | langgraph 0.2.x (pinned in STACK.md) | STACK.md listed 0.2.x as [VERIFY]; PyPI confirms latest is 1.1.2 — use 1.1.x; API is largely compatible but recursion_limit moved from compile() to invoke config dict |
| with_structured_output() | Prompt parsing PASS/WARN/REJECT | Prompt parsing is fragile; structured output returns a Pydantic model directly — type-safe, testable without LLM |
| langchain-openai | openai SDK directly | openai SDK has no with_structured_output() or bind_tools() integration with LangGraph state; langchain-openai provides the bridge |
| tiktoken | Manual token estimation | tiktoken is the official tokenizer for GPT-4o; manual estimation (char/4) is ±30% off for JSON payloads |

**Installation:**
```bash
uv add langgraph langchain-openai tiktoken langgraph-checkpoint-postgres \
  --package sharpedge-agent-pipeline
```

---

## Architecture Patterns

### Recommended Module Layout

```
packages/agent_pipeline/
├── pyproject.toml                  # sharpedge-agent-pipeline package
└── src/sharpedge_agent_pipeline/
    ├── __init__.py
    ├── state.py                    # BettingAnalysisState TypedDict (< 100 lines)
    ├── graph.py                    # build_analysis_graph() factory (< 200 lines)
    ├── nodes/
    │   ├── __init__.py
    │   ├── route_intent.py         # classify intent (analyze/copilot/scan)
    │   ├── fetch_context.py        # single Odds API call, all data into state
    │   ├── detect_regime.py        # wraps RegimeDetector from Phase 1
    │   ├── run_models.py           # wraps EVCalculator + KeyNumberZoneDetector
    │   ├── calculate_ev.py         # calls simulate_bankroll() from Phase 1
    │   ├── validate_setup.py       # LLM evaluator: PASS/WARN/REJECT
    │   ├── compose_alpha.py        # calls AlphaComposer from Phase 1
    │   ├── size_position.py        # Kelly sizing node
    │   └── generate_report.py      # formats Discord embed output
    ├── copilot/
    │   ├── __init__.py
    │   ├── agent.py                # BettingCopilot ReAct agent (< 150 lines)
    │   ├── tools.py                # 10 @tool functions (< 400 lines — split if needed)
    │   └── session.py              # Redis session management + trim_messages
    └── alerts/
        ├── __init__.py
        └── alpha_ranker.py         # sort _pending_value_alerts by alpha_score

apps/bot/src/sharpedge_bot/
├── commands/analysis.py            # MODIFY: call agent_pipeline instead of old agents
├── jobs/value_scanner_job.py       # MODIFY: use alpha_ranker before alert dispatch
└── agents/                         # RETIRE: game_analyst.py, research_agent.py, review_agent.py
                                    # Keep tools.py for backward compat during transition
```

### Pattern 1: BettingAnalysisState with Safe Parallel Keys

Nodes that run in parallel (detect_regime, run_models, calculate_ev) each write to distinct keys — no Annotated reducer needed for those. Only `quality_warnings` (accumulate from multiple nodes) uses `operator.add`.

```python
# packages/agent_pipeline/src/sharpedge_agent_pipeline/state.py
# Source: LangGraph docs + GitHub test_pregel.py (confirmed pattern)

from typing import Annotated
import operator
from typing_extensions import TypedDict
from sharpedge_analytics.regime import RegimeClassification
from sharpedge_models.alpha import BettingAlpha
from sharpedge_models.monte_carlo import MonteCarloResult


class BettingAnalysisState(TypedDict):
    # Input
    game_query: str
    sport: str
    user_id: str

    # Set by fetch_context (one node only — no reducer needed)
    game_context: dict          # raw odds + line movement snapshot
    regime_inputs: dict         # extracted ticket_pct, handle_pct, move_velocity etc.

    # Set by parallel nodes (distinct keys — no collision)
    regime_result: RegimeClassification     # detect_regime writes this
    ev_result: dict                         # run_models writes this
    mc_result: MonteCarloResult | None      # calculate_ev writes this

    # Set by validate_setup
    eval_verdict: str           # "PASS" | "WARN" | "REJECT"
    eval_reasoning: str
    retry_count: int            # loop guard: max 2 retries

    # Set by compose_alpha + size_position
    alpha: BettingAlpha | None
    kelly_fraction: float | None

    # Accumulated by multiple nodes (Annotated reducer required)
    quality_warnings: Annotated[list[str], operator.add]

    # Set by generate_report
    report: str
    error: str | None
```

### Pattern 2: 9-Node Graph Wiring with Parallel Fan-Out

```python
# packages/agent_pipeline/src/sharpedge_agent_pipeline/graph.py
# Source: LangGraph docs confirmed — multiple outgoing edges = parallel execution

from langgraph.graph import StateGraph, START, END
from .state import BettingAnalysisState
from .nodes import (
    route_intent, fetch_context, detect_regime, run_models,
    calculate_ev, validate_setup, compose_alpha, size_position,
    generate_report, error_handler,
)


def build_analysis_graph() -> ...:
    g = StateGraph(BettingAnalysisState)

    # Add all nodes
    g.add_node("route_intent", route_intent)
    g.add_node("fetch_context", fetch_context)
    g.add_node("detect_regime", detect_regime)   # parallel
    g.add_node("run_models", run_models)          # parallel
    g.add_node("calculate_ev", calculate_ev)      # parallel
    g.add_node("validate_setup", validate_setup)
    g.add_node("compose_alpha", compose_alpha)
    g.add_node("size_position", size_position)
    g.add_node("generate_report", generate_report)
    g.add_node("error_handler", error_handler)

    # Sequential edges
    g.add_edge(START, "route_intent")
    g.add_edge("route_intent", "fetch_context")

    # Parallel fan-out: fetch_context → 3 nodes simultaneously
    g.add_edge("fetch_context", "detect_regime")
    g.add_edge("fetch_context", "run_models")
    g.add_edge("fetch_context", "calculate_ev")

    # Fan-in: all 3 parallel nodes → validate_setup
    g.add_edge("detect_regime", "validate_setup")
    g.add_edge("run_models", "validate_setup")
    g.add_edge("calculate_ev", "validate_setup")

    # Conditional routing after validation
    g.add_conditional_edges("validate_setup", _route_after_validation)
    g.add_edge("compose_alpha", "size_position")
    g.add_edge("size_position", "generate_report")
    g.add_edge("generate_report", END)
    g.add_edge("error_handler", END)

    return g.compile()


def _route_after_validation(state: BettingAnalysisState) -> str:
    if state["eval_verdict"] == "REJECT":
        return "generate_report"   # emit REJECT report, no alpha
    if state["eval_verdict"] == "PASS":
        return "compose_alpha"
    # WARN: retry once, then force through
    if state.get("retry_count", 0) >= 2:
        return "compose_alpha"     # proceed with WARN badge
    return "fetch_context"         # re-enrich once
```

### Pattern 3: recursion_limit via Config Dict (NOT compile())

LangGraph 1.x moved recursion_limit out of `compile()`. It is now passed per-invocation via the config dict. Default is 1000 (as of 1.0.6+).

```python
# In the Discord command handler or job:
result = await graph.ainvoke(
    initial_state,
    config={"recursion_limit": 25},   # 9 nodes + 1 retry = 18 max; 25 gives buffer
)
```

This is critical: the STACK.md/PITFALLS.md note about `graph.compile(recursion_limit=10)` is outdated for LangGraph 1.x. The API changed. Passing it at invoke time is correct.

### Pattern 4: LLM Setup Evaluator with Structured Output (AGENT-02)

```python
# packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/validate_setup.py
# Source: langchain-openai with_structured_output — confirmed pattern

from pydantic import BaseModel
from typing import Literal
from langchain_openai import ChatOpenAI


class SetupEvalResult(BaseModel):
    verdict: Literal["PASS", "WARN", "REJECT"]
    reasoning: str
    confidence: float  # 0-1


def validate_setup(state: BettingAnalysisState) -> dict:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    evaluator = llm.with_structured_output(SetupEvalResult)

    prompt = _build_eval_prompt(state)
    result: SetupEvalResult = evaluator.invoke(prompt)

    retry_count = state.get("retry_count", 0)
    return {
        "eval_verdict": result.verdict,
        "eval_reasoning": result.reasoning,
        "retry_count": retry_count + 1 if result.verdict == "WARN" else retry_count,
    }
```

Use GPT-4o-mini for this node (per PROJECT.md constraint: GPT-4o-mini for routing/eval nodes).

### Pattern 5: BettingCopilot Context Window Management (AGENT-03 / AGENT-04)

The official mitigation for PITFALLS.md Pitfall 6 is `trim_messages` from `langchain_core.messages`, combined with tiktoken token counting.

```python
# packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/session.py
# Source: langchain_core.messages.trim_messages (confirmed API)

from langchain_core.messages import trim_messages, BaseMessage
import tiktoken

MAX_TOKENS = 80_000   # GPT-4o limit is 128k; leave buffer for tool calls


def trim_conversation(messages: list[BaseMessage], model: str = "gpt-4o") -> list[BaseMessage]:
    """Trim conversation to stay under context limit. Keeps most-recent messages."""
    enc = tiktoken.encoding_for_model(model)
    return trim_messages(
        messages,
        strategy="last",           # keep the most recent messages
        token_counter=lambda msgs: sum(len(enc.encode(m.content)) for m in msgs),
        max_tokens=MAX_TOKENS,
        start_on="human",          # never start trimmed context mid-assistant turn
        include_system=True,       # preserve system prompt
        allow_partial=False,       # never cut a message in half
    )
```

Store the full conversation in Redis (keyed by `{user_id}:{session_id}`), trim before each LLM call. This prevents context window overflow without losing full history.

### Pattern 6: AGENT-05 Alpha Ranking Intercept

The existing `value_scanner_job.py` appends to `_pending_value_alerts` ordered by `rank_value_plays()` which sorts by `ev_percentage`. Replace the sort key with `alpha_score`.

```python
# apps/bot/src/sharpedge_bot/alerts/alpha_ranker.py
# New thin module; value_scanner_job.py imports this instead of rank_value_plays

from sharpedge_agent_pipeline.alerts.alpha_ranker import rank_by_alpha


def rank_by_alpha(plays: list[ValuePlay]) -> list[ValuePlay]:
    """Sort value plays by BettingAlpha.alpha descending.

    Falls back to ev_percentage for plays where alpha_score is not yet populated.
    """
    return sorted(
        plays,
        key=lambda p: (p.alpha_score if p.alpha_score is not None else 0.0),
        reverse=True,
    )
```

The `ValuePlay` model needs an `alpha_score: float | None = None` field added. AlphaComposer is called during the value scanner loop (or in a dedicated enrichment step) before plays are queued for dispatch.

### Pattern 7: New Package Registration

```toml
# packages/agent_pipeline/pyproject.toml
[project]
name = "sharpedge-agent-pipeline"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "langgraph>=1.1.0,<2",
    "langchain-openai>=0.3.0,<0.4",
    "langgraph-checkpoint-postgres>=3.0.0,<4",
    "tiktoken>=0.12.0,<1",
    "sharpedge-models",
    "sharpedge-analytics",
    "sharpedge-db",
    "sharpedge-odds",
    "sharpedge-shared",
]
```

Add to root `pyproject.toml` workspace members:
```toml
[tool.uv.workspace]
members = ["apps/bot", "apps/webhook_server", "packages/*"]
# packages/* already covers packages/agent_pipeline/ — no change needed
```

Add to `apps/bot/pyproject.toml` dependencies: `"sharpedge-agent-pipeline"`.

### Anti-Patterns to Avoid

- **LLM calls inside parallel nodes:** `detect_regime`, `run_models`, `calculate_ev` must not call LLMs — they call Phase 1 pure functions only. LLM calls in parallel nodes multiply cost and latency.
- **Multiple Odds API calls per graph run:** All external data is fetched once in `fetch_context`. Downstream nodes read from state. One API call per graph execution.
- **compile(recursion_limit=...):** This parameter was removed from `compile()` in LangGraph 1.x. Pass `config={"recursion_limit": N}` to `ainvoke()` instead.
- **Global module-level graph instance:** Build the graph at startup (call `build_analysis_graph()` once), not per-request. The compiled graph is reusable.
- **Swallowed async exceptions:** Wrap every `graph.ainvoke()` in try/except; route to `error_handler` node for graceful Discord response (Pitfall 11 in PITFALLS.md).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parallel node state merging | Custom locking/mutex in state | `Annotated[list[str], operator.add]` reducer | LangGraph handles parallel write merging natively with reducers |
| Context window trimming | Manual message truncation | `langchain_core.messages.trim_messages` | Handles system message preservation, partial-turn avoidance, strategy selection |
| Token counting | `len(text) / 4` estimate | `tiktoken.encoding_for_model()` | ±30% error on JSON payloads from DB queries; tiktoken is exact for GPT-4o |
| Structured LLM output parsing | Regex on verdict string | `ChatOpenAI.with_structured_output(Pydantic model)` | Type-safe; validation built-in; no hallucination of non-PASS/WARN/REJECT values |
| Graph loop prevention | Custom retry counter in application code | `retry_count` in state + `config={"recursion_limit": N}` at ainvoke | Two-layer guard: application logic (retry_count) + LangGraph engine (recursion_limit) |
| Conversation persistence | Redis pickle of messages list | `langgraph-checkpoint-postgres` | Thread-safe, supports resume across Discord bot restarts, uses existing Supabase |

**Key insight:** LangGraph 1.x handles the hard parts (parallel state merging, checkpoint persistence, loop detection) natively. The Phase 2 task is wiring domain logic into nodes, not building framework features.

---

## Common Pitfalls

### Pitfall 1: recursion_limit in compile() — WRONG in LangGraph 1.x
**What goes wrong:** STACK.md and PITFALLS.md reference `graph.compile(recursion_limit=10)`. This API no longer exists in LangGraph 1.x. Passing it to `compile()` silently does nothing.
**Why it happens:** STACK.md was written against 0.2.x; PyPI confirms current is 1.1.2.
**How to avoid:** Pass `config={"recursion_limit": 25}` to every `graph.ainvoke()` call. Add an integration test that verifies `GraphRecursionError` is raised when limit is exceeded.
**Warning signs:** Infinite loop is not stopped despite "setting" recursion_limit in compile.

### Pitfall 2: Parallel State Collision (from PITFALLS.md Pitfall 1)
**What goes wrong:** detect_regime, run_models, calculate_ev run in the same superstep. If any two write to the same state key, LangGraph's default last-write-wins drops one result silently.
**How to avoid:** Each parallel node writes to its own distinct key (regime_result, ev_result, mc_result). Only `quality_warnings` (append-only) uses `Annotated[list[str], operator.add]`. Audit state schema before adding any key.
**Warning signs:** Unit test that runs two parallel nodes and asserts both values survive — if assertion passes, state is safe.

### Pitfall 3: Infinite Loop on WARN Re-route (from PITFALLS.md Pitfall 5)
**What goes wrong:** WARN re-routes to fetch_context. Without a retry counter, this loops indefinitely.
**How to avoid:** `retry_count: int` in state; `_route_after_validation` returns "compose_alpha" when `retry_count >= 2`. Two guards: application-level counter + `config={"recursion_limit": 25}` catches anything that slips through.

### Pitfall 4: BettingCopilot Context Overflow After 10 Turns (from PITFALLS.md Pitfall 6)
**What goes wrong:** JSON tool call results (portfolio stats, Monte Carlo result, 30-book odds comparison) accumulate quickly. After 5-10 turns, total context > 128k tokens → API error.
**How to avoid:** `trim_messages(strategy="last", max_tokens=80_000)` before every LLM call in BettingCopilot. Store full history in Redis. Track tokens per call with tiktoken; log warning when > 80k.

### Pitfall 5: Tools Make Direct DB Calls Instead of Using Service Layer
**What goes wrong:** BettingCopilot `@tool` functions bypass the service layer and call Supabase directly. This duplicates query logic already in `sharpedge_db.queries.*` and `sharpedge_bot.services.*`.
**How to avoid:** Every tool wraps an existing service function. `get_active_bets` calls `bet_service.get_pending_bets()`. `get_portfolio_stats` calls `stats_service.get_performance_summary()`. No raw Supabase client calls inside tool functions.

### Pitfall 6: AGENT-05 Alpha Score Not Populated Before Sort
**What goes wrong:** `ValuePlay.alpha_score` is `None` for plays discovered before AlphaComposer is called. Sorting on `None` raises TypeError; sorting with fallback `0.0` puts unenriched plays last (which is actually correct behavior, but looks like a bug).
**How to avoid:** Enrichment step (call AlphaComposer) must run before `rank_by_alpha()`. Add an assertion in the alert dispatch: `assert all(p.alpha_score is not None for p in top_plays_to_alert)`.

### Pitfall 7: Odds API Called in Multiple Parallel Nodes
**What goes wrong:** If `detect_regime` and `run_models` both call OddsClient independently, monthly quota is consumed 2-3× per graph run (Pitfall 7 in PITFALLS.md).
**How to avoid:** Snapshot-at-entry: `fetch_context` node fetches everything from OddsClient once and stores in `state["game_context"]`. All downstream nodes read from state only.

---

## Code Examples

Verified from codebase reads and LangGraph GitHub source:

### Full State Key Audit (which keys need reducers)

```python
# Keys written by ONLY ONE node → no reducer needed (last-write-wins is fine)
# - game_context: fetch_context
# - regime_result: detect_regime
# - ev_result: run_models
# - mc_result: calculate_ev
# - eval_verdict, eval_reasoning, retry_count: validate_setup
# - alpha: compose_alpha
# - kelly_fraction: size_position
# - report, error: generate_report / error_handler

# Keys written by MULTIPLE nodes → Annotated reducer required
# - quality_warnings: validate_setup + compose_alpha can both append warnings
quality_warnings: Annotated[list[str], operator.add]
```

### recursion_limit (confirmed from LangGraph test suite)

```python
# WRONG (LangGraph 0.2.x, no longer works in 1.x)
# app = graph.compile(recursion_limit=10)

# CORRECT (LangGraph 1.x, confirmed from test_pregel.py)
result = await graph.ainvoke(state, config={"recursion_limit": 25})

# Catching the error
from langgraph.errors import GraphRecursionError
try:
    result = await graph.ainvoke(state, config={"recursion_limit": 25})
except GraphRecursionError:
    return {"error": "Analysis loop exceeded limit", "eval_verdict": "REJECT"}
```

### BettingCopilot Tool (wrapping existing service layer)

```python
# packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py
from langchain_core.tools import tool
from sharpedge_db.queries.bets import get_pending_bets
from sharpedge_db.queries.users import get_user_by_discord_id


@tool
def get_active_bets(user_id: str) -> str:
    """Get the user's currently active (pending) bets.

    Args:
        user_id: Discord user ID
    """
    import json
    user = get_user_by_discord_id(user_id)
    if not user:
        return json.dumps({"error": "User not found"})
    bets = get_pending_bets(user.id)
    # Return only top 10 to limit token usage
    return json.dumps([{
        "game": b.game,
        "bet_type": b.bet_type,
        "selection": b.selection,
        "odds": b.odds,
        "units": float(b.units),
        "stake": float(b.stake),
        "sport": b.sport,
    } for b in bets[:10]])
```

### Value Scanner Alpha Enrichment (AGENT-05)

```python
# In apps/bot/src/sharpedge_bot/jobs/value_scanner_job.py
# BEFORE (existing): sorted by ev_percentage via rank_value_plays()
# AFTER: enrich with alpha then sort by alpha_score

from sharpedge_analytics import enrich_with_alpha  # added in Phase 1 Plan 3
from sharpedge_agent_pipeline.alerts.alpha_ranker import rank_by_alpha

# Replace the existing rank_value_plays call:
enriched_plays = enrich_with_alpha(all_value_plays)   # adds alpha_score to each
ranked_plays = rank_by_alpha(enriched_plays)           # sort by alpha_score desc
```

### Graph Unit Test Without LLM (confirmed from LangGraph test suite)

```python
# tests/unit/agent_pipeline/test_graph_nodes.py

from unittest.mock import patch, MagicMock
from sharpedge_agent_pipeline.nodes.detect_regime import detect_regime
from sharpedge_agent_pipeline.state import BettingAnalysisState


def test_detect_regime_steam_move():
    """detect_regime node sets regime_result in state — no LLM call."""
    state: BettingAnalysisState = {
        "game_context": {},
        "regime_inputs": {
            "ticket_pct": 0.50,
            "handle_pct": 0.55,
            "line_move_pts": 1.5,
            "move_velocity": 0.8,   # fast
            "book_alignment": 0.85, # high alignment → STEAM_MOVE
        },
        # ... other required keys with defaults
    }
    result = detect_regime(state)
    assert result["regime_result"].regime.value == "STEAM_MOVE"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `openai-agents` flat 3-agent setup | LangGraph 1.1.x StateGraph | Phase 2 | Graph routing, parallel fan-out, persistent checkpoints |
| `graph.compile(recursion_limit=N)` | `graph.ainvoke(state, config={"recursion_limit": N})` | LangGraph ~0.2 → 1.0 | Config moved to invocation time; compile() parameter silently ignored in 1.x |
| Manual prompt parsing for PASS/WARN/REJECT | `ChatOpenAI.with_structured_output(Pydantic)` | langchain-openai 0.1+ | Type-safe; no regex; model validates against schema |
| `@function_tool` (OpenAI Agents SDK) | `@tool` (langchain-core) | Phase 2 migration | Same callable pattern; integrates with LangGraph's ToolNode |
| aioredis | `redis.asyncio` (redis-py 5.0+) | redis-py 4.2 merge | aioredis is deprecated; `redis.asyncio` is the async interface |

**Deprecated/outdated in current codebase:**
- `openai-agents` (`openai-agents>=0.0.7` in apps/bot/pyproject.toml): replace with LangGraph; keep during transition, remove after all commands migrated
- `@function_tool` decorator in `agents/tools.py`: replace with `@tool` from langchain-core

---

## Open Questions

1. **LangGraph 1.x MessagesState vs custom TypedDict**
   - What we know: LangGraph provides `MessagesState` as a built-in TypedDict with a `messages: Annotated[list[BaseMessage], add_messages]` key
   - What's unclear: BettingCopilot likely wants MessagesState for its conversation loop; the analysis graph wants a custom domain TypedDict. Can they coexist in the same compile()?
   - Recommendation: Use MessagesState for the BettingCopilot sub-graph; use custom BettingAnalysisState for the analysis graph. Two separate compiled graphs invoked from different bot commands.

2. **langgraph-checkpoint-postgres connection to Supabase**
   - What we know: Package is 3.0.4 (Jan 2026); uses asyncpg connection string
   - What's unclear: Whether the Supabase connection string format (postgresql+asyncpg://...) is compatible with the 3.0.x checkpoint saver initialization API
   - Recommendation: Test checkpoint connection in Wave 0 with a smoke test before building the full BettingCopilot. Add `tests/integration/test_checkpoint_connection.py` with a `@pytest.mark.skipif(no_db_env)` guard.

3. **Where does BettingCopilot live in the graph?**
   - What we know: AGENT-03/04 describe a conversational agent; AGENT-01 describes an analysis pipeline
   - What's unclear: Is the copilot a separate graph invoked from a different Discord command (`/copilot`), or a node within the 9-node analysis graph?
   - Recommendation: Separate graph. The 9-node graph is the analysis pipeline for `/analyze`. BettingCopilot is its own StateGraph (using MessagesState + ToolNode pattern) invoked from `/copilot`. This avoids mixing conversational and batch analysis logic.

4. **Alpha score field on ValuePlay**
   - What we know: `ValuePlay` is defined in `sharpedge_analytics`; `enrich_with_alpha()` was added in Phase 1 Plan 3
   - What's unclear: Whether `ValuePlay` already has `alpha_score: float | None` added (Phase 1 may not be fully complete)
   - Recommendation: Verify in Phase 1 completion check. If missing, add to `ValuePlay` as first task of Phase 2 Wave 1.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-asyncio 0.24+ and pytest-mock 3.14+ |
| Config file | `pyproject.toml` (root workspace) — existing config |
| Quick run command | `uv run pytest tests/unit/agent_pipeline/ -x -q` |
| Full suite command | `uv run pytest tests/ -x -q --ignore=tests/integration` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AGENT-01 | Graph executes all 9 nodes in order with mock node functions (no LLM) | unit | `uv run pytest tests/unit/agent_pipeline/test_graph.py -x` | Wave 0 |
| AGENT-01 | Parallel nodes write to distinct state keys — no collision | unit | `uv run pytest tests/unit/agent_pipeline/test_state.py::test_parallel_writes_no_collision -x` | Wave 0 |
| AGENT-01 | quality_warnings accumulate from multiple nodes via operator.add reducer | unit | `uv run pytest tests/unit/agent_pipeline/test_state.py::test_warnings_accumulate -x` | Wave 0 |
| AGENT-02 | validate_setup node returns SetupEvalResult with PASS/WARN/REJECT (mock LLM) | unit | `uv run pytest tests/unit/agent_pipeline/test_validate_setup.py -x` | Wave 0 |
| AGENT-02 | WARN verdict with retry_count >= 2 routes to compose_alpha, not back to fetch_context | unit | `uv run pytest tests/unit/agent_pipeline/test_graph.py::test_warn_retry_cap -x` | Wave 0 |
| AGENT-03 | BettingCopilot returns response referencing active bets when asked (mock tools) | unit | `uv run pytest tests/unit/agent_pipeline/test_copilot.py::test_active_bets_awareness -x` | Wave 0 |
| AGENT-04 | All 10 tool functions return valid JSON without errors (no live DB) | unit | `uv run pytest tests/unit/agent_pipeline/test_copilot_tools.py -x` | Wave 0 |
| AGENT-04 | trim_conversation reduces message list when total tokens > MAX_TOKENS | unit | `uv run pytest tests/unit/agent_pipeline/test_session.py::test_trim_conversation -x` | Wave 0 |
| AGENT-05 | rank_by_alpha sorts ValuePlay list by alpha_score descending | unit | `uv run pytest tests/unit/agent_pipeline/test_alpha_ranker.py -x` | Wave 0 |
| AGENT-05 | Plays with alpha_score=None sort after plays with alpha_score > 0 | unit | `uv run pytest tests/unit/agent_pipeline/test_alpha_ranker.py::test_none_alpha_last -x` | Wave 0 |

### Unit vs Integration Split

**Unit testable (no LLM, no DB, no network):**
- All node logic with Phase 1 pure functions (detect_regime, run_models, calculate_ev, compose_alpha, size_position)
- Graph routing / conditional edge logic (mock node return values)
- State reducer behavior (Annotated fields)
- trim_conversation token counting and message trimming
- rank_by_alpha sorting
- SetupEvalResult validation (mock ChatOpenAI response)

**Integration only (requires live services — mark @pytest.mark.integration):**
- langgraph-checkpoint-postgres connection to Supabase
- BettingCopilot end-to-end with real LLM (GPT-4o-mini)
- Full graph ainvoke with real Odds API data
- value_scanner_job.py with real Supabase alpha enrichment

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/agent_pipeline/ -x -q` (target: < 15 seconds)
- **Per wave merge:** `uv run pytest tests/ -x -q --ignore=tests/integration`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps (must be created before implementation starts)

- [ ] `packages/agent_pipeline/` — new package directory + `pyproject.toml`
- [ ] `packages/agent_pipeline/src/sharpedge_agent_pipeline/__init__.py`
- [ ] `tests/unit/agent_pipeline/__init__.py`
- [ ] `tests/unit/agent_pipeline/test_graph.py` — covers AGENT-01 routing
- [ ] `tests/unit/agent_pipeline/test_state.py` — covers AGENT-01 parallel state safety
- [ ] `tests/unit/agent_pipeline/test_validate_setup.py` — covers AGENT-02 (mocked LLM)
- [ ] `tests/unit/agent_pipeline/test_copilot.py` — covers AGENT-03 (mocked tools)
- [ ] `tests/unit/agent_pipeline/test_copilot_tools.py` — covers AGENT-04 (mocked DB)
- [ ] `tests/unit/agent_pipeline/test_session.py` — covers AGENT-04 trim_messages
- [ ] `tests/unit/agent_pipeline/test_alpha_ranker.py` — covers AGENT-05

---

## Sources

### Primary (HIGH confidence)

- PyPI `langgraph` JSON API — confirmed version 1.1.2 as latest stable (fetched 2026-03-14)
- PyPI `langchain-openai` JSON API — confirmed version 0.3.14 (fetched 2026-03-14)
- PyPI `langgraph-checkpoint-postgres` JSON API — confirmed version 3.0.4, released Jan 2026 (fetched 2026-03-14)
- PyPI `tiktoken` JSON API — confirmed version 0.12.0 (fetched 2026-03-14)
- GitHub `langchain-ai/langgraph` `libs/langgraph/langgraph/graph/state.py` — confirmed compile() parameters (no recursion_limit); checkpointer, cache, store, interrupt_before/after, debug, name
- GitHub `langchain-ai/langgraph` `libs/langgraph/tests/test_pregel.py` — confirmed recursion_limit passed as `config={"recursion_limit": N}` to invoke(); confirmed `Annotated[list[str], operator.add]` reducer pattern
- LangGraph docs (docs.langchain.com) — confirmed parallel fan-out via multiple add_edge, Send API pattern, `Annotated` state reducers
- `/Users/revph/sharpedge/packages/models/src/sharpedge_models/alpha.py` — AlphaComposer API: `compose_alpha(edge_score, regime_scale, survival_prob, confidence_mult) -> BettingAlpha`
- `/Users/revph/sharpedge/packages/analytics/src/sharpedge_analytics/regime.py` — RegimeDetector API: `classify_regime(...) -> RegimeClassification`
- `/Users/revph/sharpedge/apps/bot/src/sharpedge_bot/agents/game_analyst.py` — existing agent to replace: `Agent` + `Runner.run()` from openai-agents
- `/Users/revph/sharpedge/apps/bot/src/sharpedge_bot/jobs/value_scanner_job.py` — confirmed alert dispatch uses `_pending_value_alerts` global; sorts by `rank_value_plays()` (ev_percentage)
- `/Users/revph/sharpedge/apps/bot/src/sharpedge_bot/services/` — confirmed service layer (bankroll_service, bet_service, odds_service, stats_service) available for tool wrapping
- `/Users/revph/sharpedge/.planning/research/PITFALLS.md` — Pitfalls 1, 5, 6, 7, 11 all Phase 2-specific; mitigations verified against LangGraph source
- `/Users/revph/sharpedge/.planning/STATE.md` — locked decision: LangGraph replaces OpenAI Agents SDK
- `/Users/revph/sharpedge/.planning/PROJECT.md` — locked constraints: GPT-4o for analysis nodes, GPT-4o-mini for routing/eval nodes

### Secondary (MEDIUM confidence)

- `with_structured_output()` pattern: confirmed via LangGraph docs example code; specific langchain-openai 0.3.x API surface not directly read from source but consistent with known behavior since 0.1.x
- `trim_messages(strategy="last", ...)` parameter names: consistent with langchain-core API known through training; exact parameter names not confirmed against 0.3.x source — verify before implementing

### Tertiary (LOW confidence)

- BettingCopilot as separate graph vs node in analysis graph: architectural recommendation; no official LangGraph guidance on this pattern
- Redis conversation snapshot TTL (30 minutes): heuristic from PITFALLS.md; actual appropriate TTL depends on user session patterns

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — LangGraph version confirmed from PyPI; langchain-openai, tiktoken, checkpoint-postgres all confirmed
- Architecture (graph wiring, state keys): HIGH — Annotated reducer pattern confirmed from LangGraph test suite; compile() vs ainvoke() recursion_limit confirmed from source
- LLM evaluator pattern: HIGH — with_structured_output is stable API; MEDIUM for exact parameter names in langchain-openai 0.3.x
- BettingCopilot trim_messages: MEDIUM — trim_messages API is known but not verified against langchain-core current source
- Alert dispatch intercept (AGENT-05): HIGH — value_scanner_job.py read directly; pattern is simple sort replacement

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (30 days — LangGraph is actively developed; re-verify version before pinning)
