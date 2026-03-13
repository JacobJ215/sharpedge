# Architecture Patterns

**Domain:** Institutional-grade sports betting intelligence platform — LangGraph orchestration layer
**Researched:** 2026-03-13
**Confidence:** MEDIUM (LangGraph patterns from training data through Aug 2025; no live doc verification due to tool constraints)

---

## Recommended Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  FRONT-ENDS                                                         │
│  Discord Bot  │  Next.js Web (SSE streaming)  │  Expo Mobile        │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ HTTP / SSE
┌──────────────────────────▼──────────────────────────────────────────┐
│  FastAPI REST Layer  (apps/api/)                                     │
│  /api/v1/copilot/chat  [SSE stream]                                  │
│  /api/v1/value-plays   /api/v1/games/:id/analysis                   │
│  /api/v1/bankroll/simulate  /api/v1/users/:id/portfolio             │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ Python calls
┌──────────────────────────▼──────────────────────────────────────────┐
│  AGENT LAYER  (packages/agents/)                                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  LangGraph StateGraph  (BettingAnalysisWorkflow)             │   │
│  │                                                              │   │
│  │  [route_intent] → [fetch_context] → [detect_regime]         │   │
│  │       ↓                                                      │   │
│  │  [run_models] → [calculate_ev] → [validate_setup]           │   │
│  │       ↓                  ↓             ↓ REJECT→END         │   │
│  │  [compose_alpha] → [size_position] → [generate_report]→END  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  BettingCopilot  (conversational — tool-calling loop)        │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ function calls
┌──────────────────────────▼──────────────────────────────────────────┐
│  QUANTITATIVE ENGINE  (packages/models/, packages/analytics/)       │
│  MonteCarloSimulator │ BettingRegimeDetector │ AlphaComposer        │
│  WalkForwardBacktester │ KeyNumberZoneDetector │ ev_calculator.py   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────────┐
│  DATA LAYER                                                         │
│  Odds API (30+ books) │ Kalshi │ Polymarket │ ESPN │ Weather        │
│  Redis (hot cache)    │ Supabase (persistent store)                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

| Component | Package / Module | Responsibility | Communicates With |
|-----------|-----------------|----------------|-------------------|
| `BettingAnalysisWorkflow` | `packages/agents/src/sharpedge_agents/workflow.py` | LangGraph StateGraph — routes incoming bet analysis requests through 9 specialist nodes | Quant engine modules, data feed clients |
| `BettingCopilot` | `packages/agents/src/sharpedge_agents/copilot.py` | Stateful conversational agent using tool-call loop against CopilotSnapshot | All quant engine modules via tool wrappers |
| `BettingSetupEvaluator` | `packages/agents/src/sharpedge_agents/evaluator.py` | LLM gate (GPT-4o-mini) that validates each candidate alert before it reaches the report node | Called from `validate_setup` graph node only |
| `MonteCarloSimulator` | `packages/models/src/sharpedge_models/monte_carlo.py` | Simulate 2000 bankroll paths; return ruin probability, percentile outcomes, max drawdown | Called by `size_position` node; exposed as copilot tool and `/bankroll/simulate` endpoint |
| `BettingRegimeDetector` | `packages/analytics/src/sharpedge_analytics/regime.py` | Classify betting market state into one of 7 regimes using line movement, ticket/handle, book alignment | Called by `detect_regime` node; output stored in `BettingAnalysisState.regime_state` |
| `AlphaComposer` | `packages/models/src/sharpedge_models/alpha.py` | Compute composite alpha = edge_prob × ev_score × regime_scale × survival_prob × confidence_mult | Called by `compose_alpha` node; produces the single ranking metric |
| `WalkForwardBacktester` | `packages/models/src/sharpedge_models/walk_forward.py` | Sliding-window out-of-sample validation; produces quality badge | Called by background job, not in hot path; exposed via `/performance` endpoint |
| `KeyNumberZoneDetector` | `packages/analytics/src/sharpedge_analytics/key_numbers.py` | Detects proximity to NFL/NBA/MLB/NHL clustering numbers; adjusts alpha | Called within `calculate_ev` node |
| FastAPI layer | `apps/api/` | REST + SSE endpoints consumed by web and mobile | Agent layer, quant engine, Supabase, Redis |
| Discord Bot | `apps/bot/` | Existing slash commands + enhanced alert dispatch | FastAPI layer or direct agent layer calls |

---

## LangGraph StateGraph Node Design

### Shared State Schema

All nodes read from and write to a single `TypedDict`. No node has side effects outside of writing to state — external I/O (DB, APIs) happens inside nodes but results are stored in state fields.

```python
# packages/agents/src/sharpedge_agents/state.py

from typing import TypedDict, Literal, Optional
from sharpedge_models.alpha import BettingAlpha
from sharpedge_models.monte_carlo import MonteCarloResult
from sharpedge_analytics.regime import RegimeState

class BettingAnalysisState(TypedDict):
    # Input
    request: str                             # Raw user request text
    user_id: str                             # For bankroll context

    # Routing
    intent: Optional[BettingIntent]          # Normalized intent after route_intent
    routing_path: Optional[str]             # 'sports' | 'prediction_market' | 'arbitrage' | 'copilot'

    # Context (populated by fetch_context)
    game_context: Optional[GameContext]      # Odds, injuries, weather, stats
    sport: Optional[str]
    game_id: Optional[str]

    # Regime (populated by detect_regime)
    regime_state: Optional[RegimeState]      # 7-state classification + confidence

    # Model layer (populated by run_models)
    model_predictions: Optional[ModelPreds] # Ensemble output + disagreement score

    # EV layer (populated by calculate_ev)
    ev_analysis: Optional[EVAnalysis]        # EV%, P(edge>0), no-vig, key number proximity

    # Evaluation gate (populated by validate_setup)
    eval_result: Optional[EvalResult]        # PASS | WARN | REJECT + reasoning
    eval_gate_passed: bool                   # Controls conditional edge to compose_alpha

    # Alpha composition (populated by compose_alpha)
    alpha: Optional[BettingAlpha]            # Composite score + breakdown

    # Risk/sizing (populated by size_position)
    kelly_fraction: Optional[float]
    monte_carlo: Optional[MonteCarloResult]
    recommended_units: Optional[float]

    # Output (populated by generate_report)
    recommendation: Optional[Recommendation] # BET | PASS | WATCH + reasoning
    report_text: str                          # Formatted explanation
    quality_badge: Literal['PREMIUM', 'HIGH', 'MEDIUM', 'SPECULATIVE', '']
    alert_ready: bool                         # Whether to dispatch to Discord/push
```

### Node Definitions

Each node is a pure async function with signature `async def node_name(state: BettingAnalysisState) -> dict`.  The return dict is a partial state update — LangGraph merges it with existing state.

**Node 1: `route_intent`** (GPT-4o-mini)
- Input: `state["request"]`
- Work: Parse user request into structured `BettingIntent` — sport, market type, game identifiers, explicit vs exploratory
- Output: `{"intent": BettingIntent, "routing_path": str, "sport": str, "game_id": str}`
- Cost tier: GPT-4o-mini (routing only, cheap)

**Node 2: `fetch_context`** (pure I/O, no LLM)
- Input: `state["intent"]`, `state["game_id"]`
- Work: Concurrently fetch odds (OddsClient), injuries (ESPNClient), weather, historical lines from Redis/Supabase
- Output: `{"game_context": GameContext}`
- Pattern: `asyncio.gather()` across all data sources; populate missing fields with None, not errors

**Node 3: `detect_regime`** (pure math, no LLM)
- Input: `state["game_context"]` (line movement history, ticket%, handle%, book alignment)
- Work: Call `BettingRegimeDetector.classify(game_id)` — deterministic rule-based classifier, HMM-inspired
- Output: `{"regime_state": RegimeState}` — includes regime enum + confidence + regime_scale float
- Note: This is NOT an LLM call. It is deterministic analytics.

**Node 4: `run_models`** (pure math, no LLM)
- Input: `state["game_context"]`, `state["sport"]`
- Work: Build feature vector via `GameFeatureBuilder`; run ensemble models; return predictions + disagreement score
- Output: `{"model_predictions": ModelPreds}`
- Note: If model confidence below threshold, set `disagreement_score` high — downstream nodes use this

**Node 5: `calculate_ev`** (pure math, no LLM)
- Input: `state["model_predictions"]`, `state["game_context"]`
- Work: Call existing `ev_calculator.py`; run `KeyNumberZoneDetector`; compute P(edge > 0) via Beta distribution
- Output: `{"ev_analysis": EVAnalysis}` — includes ev_pct, edge_prob, no_vig_prob, at_key_number, key_number_adjustment

**Node 6: `validate_setup`** (GPT-4o-mini LLM gate)
- Input: full state (ev_analysis, regime_state, model_predictions, game_context)
- Work: Call `BettingSetupEvaluator.evaluate()` — checks for contradictory signals, trap lines, injury impact
- Output: `{"eval_result": EvalResult, "eval_gate_passed": bool}`
- Conditional edge: if `eval_gate_passed == False` → route to `generate_report` with REJECT report; skip compose_alpha and size_position

**Node 7: `compose_alpha`** (pure math, no LLM)
- Input: `state["ev_analysis"]`, `state["regime_state"]`, `state["model_predictions"]`
- Work: Call `AlphaComposer` — multiply ev_score × regime_scale × survival_prob × confidence_mult
- Output: `{"alpha": BettingAlpha}` — full breakdown stored in state

**Node 8: `size_position`** (pure math, no LLM)
- Input: `state["alpha"]`, `state["ev_analysis"]`, user bankroll from DB
- Work: Compute Kelly fraction (fractional Kelly at 0.25×); run `MonteCarloSimulator`; map to unit recommendation
- Output: `{"kelly_fraction": float, "monte_carlo": MonteCarloResult, "recommended_units": float}`

**Node 9: `generate_report`** (GPT-4o)
- Input: full state
- Work: Format recommendation with reasoning; assign quality badge (alpha thresholds: PREMIUM >0.15, HIGH >0.08, MEDIUM >0.03, SPECULATIVE otherwise); build `report_text` for Discord/web/mobile
- Output: `{"recommendation": Recommendation, "report_text": str, "quality_badge": str, "alert_ready": bool}`

### Graph Wiring

```python
# packages/agents/src/sharpedge_agents/workflow.py

from langgraph.graph import StateGraph, END
from .state import BettingAnalysisState
from .nodes import (
    route_intent, fetch_context, detect_regime,
    run_models, calculate_ev, validate_setup,
    compose_alpha, size_position, generate_report
)

def build_workflow() -> StateGraph:
    graph = StateGraph(BettingAnalysisState)

    graph.add_node("route_intent", route_intent)
    graph.add_node("fetch_context", fetch_context)
    graph.add_node("detect_regime", detect_regime)
    graph.add_node("run_models", run_models)
    graph.add_node("calculate_ev", calculate_ev)
    graph.add_node("validate_setup", validate_setup)
    graph.add_node("compose_alpha", compose_alpha)
    graph.add_node("size_position", size_position)
    graph.add_node("generate_report", generate_report)

    graph.set_entry_point("route_intent")
    graph.add_edge("route_intent", "fetch_context")
    graph.add_edge("fetch_context", "detect_regime")
    graph.add_edge("detect_regime", "run_models")
    graph.add_edge("run_models", "calculate_ev")
    graph.add_edge("calculate_ev", "validate_setup")

    # Conditional: REJECT skips alpha composition and sizing
    graph.add_conditional_edges(
        "validate_setup",
        lambda s: "compose_alpha" if s["eval_gate_passed"] else "generate_report",
        {"compose_alpha": "compose_alpha", "generate_report": "generate_report"},
    )

    graph.add_edge("compose_alpha", "size_position")
    graph.add_edge("size_position", "generate_report")
    graph.add_edge("generate_report", END)

    return graph.compile()
```

### Node Groupings by LLM Cost

| Tier | Nodes | LLM | Rationale |
|------|-------|-----|-----------|
| No LLM | `fetch_context`, `detect_regime`, `run_models`, `calculate_ev`, `compose_alpha`, `size_position` | None | Pure I/O or math — LLM adds no value |
| GPT-4o-mini | `route_intent`, `validate_setup` | GPT-4o-mini | Routing + gate — low-stakes classification |
| GPT-4o | `generate_report` | GPT-4o | Explanation quality matters here |

---

## How Quant Engine Modules Plug Into the Graph

### Module → Node Mapping

```
BettingRegimeDetector.classify()     →  detect_regime node
                                          ↓ regime_state.regime_scale
                                          ↓ used by AlphaComposer

ev_calculator.calculate_ev()         →  calculate_ev node
KeyNumberZoneDetector.analyze()      →  calculate_ev node (adjusts ev output)
                                          ↓ ev_analysis.edge_prob + ev_pct
                                          ↓ used by AlphaComposer

AlphaComposer.compose()              →  compose_alpha node
                                          ↓ alpha.alpha (float)
                                          ↓ used by size_position, generate_report

MonteCarloSimulator.simulate()       →  size_position node
                                          ↓ monte_carlo.ruin_prob
                                          ↓ monte_carlo.p95_bankroll
                                          ↓ surfaces to user via report

WalkForwardBacktester.validate()     →  NOT in hot path
                                          → background job (APScheduler)
                                          → results stored in Supabase
                                          → confidence_mult used by AlphaComposer via DB lookup
```

### Quant Module Independence

Each quant module must be importable standalone (no LangGraph dependency). The graph nodes are thin wrappers that:
1. Extract the relevant slice of state as plain Python data
2. Call the quant module function
3. Wrap the result back into a state update dict

This keeps quant modules testable in isolation and reusable from the FastAPI layer directly.

---

## BettingCopilot Tool Pattern

### Architecture: Snapshot State + Tool-Call Loop

The copilot uses LangGraph's `ToolNode` pattern (or equivalent manual loop) rather than a linear pipeline. It holds a `CopilotSnapshot` representing the current session context.

```python
# packages/agents/src/sharpedge_agents/copilot.py

class CopilotSnapshot(TypedDict):
    user_id: str
    active_bets: list[BetRecord]          # Open positions
    portfolio_stats: PortfolioStats       # ROI, win rate, CLV, drawdown
    active_alerts: list[Alert]            # Live high-alpha plays
    bankroll: float                       # Current bankroll
    session_history: list[Message]        # Conversation turns

class BettingCopilot:
    """
    Stateful conversational agent. On each user message:
    1. Append message to session_history
    2. Refresh CopilotSnapshot from DB/Redis (lazy, on first call)
    3. Run LLM with tools bound — LLM decides which tools to call
    4. Execute tool calls, append results
    5. LLM generates final response with full tool outputs in context
    6. Stream response tokens via FastAPI SSE
    """
```

### Tool List

Each tool is a Python callable with a LangChain `@tool` decorator. Tools read from live data; they do NOT write.

| Tool | Purpose | Hot Path |
|------|---------|----------|
| `get_active_bets` | Fetch user's open bets + exposure | Supabase |
| `get_portfolio_stats` | ROI, win rate, CLV, drawdown, calibration | Supabase aggregate |
| `analyze_game` | Run full `BettingAnalysisWorkflow` for a game | Invokes StateGraph |
| `search_value_plays` | Filter current alerts by min_alpha, sport, market_type | Redis + Supabase |
| `check_line_movement` | Movement history + current regime for a game | OddsClient + RegimeDetector |
| `get_sharp_indicators` | Sharp vs public ticket%, handle%, steam flags | OddsClient |
| `estimate_bankroll_risk` | Run MonteCarloSimulator against current portfolio | MonteCarloSimulator |
| `get_prediction_market_edge` | Kalshi/Polymarket model prob vs market prob | KalshiClient + model |
| `compare_books` | Best available odds + no-vig across all books | OddsClient |
| `get_model_predictions` | Raw ensemble model output for a game | Models package |

### Tool Call Loop Termination

The LLM loop terminates when:
- The LLM generates a response with no tool calls (final answer ready)
- A maximum turn limit is hit (default: 5 tool call rounds per user message)
- A tool returns an error — copilot explains what it couldn't fetch

### Snapshot Refresh Strategy

Snapshot is hydrated once per conversation session on first user message. Subsequent messages reuse the in-memory snapshot unless a write-through tool (e.g., `analyze_game`) signals stale data. This prevents redundant Supabase calls on follow-up questions.

---

## FastAPI Streaming for Copilot Chat

### SSE Endpoint Pattern

```python
# apps/api/routes/copilot.py

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from sharpedge_agents.copilot import BettingCopilot

@router.post("/api/v1/copilot/chat")
async def copilot_chat(request: CopilotChatRequest) -> StreamingResponse:
    """
    Streams copilot response tokens as Server-Sent Events.
    Client receives: data: {"token": "...", "done": false}
    Final event:     data: {"token": "", "done": true, "tool_calls": [...]}
    """
    async def event_generator():
        copilot = BettingCopilot(user_id=request.user_id)
        async for chunk in copilot.stream(request.message, request.session_id):
            yield f"data: {chunk.model_dump_json()}\n\n"
        yield "data: {\"done\": true}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

### Streaming Implementation Inside Copilot

LangGraph supports `.astream_events()` which emits granular events (node starts, LLM tokens, tool calls). The copilot layer filters this stream to:
- Forward LLM output tokens immediately (low latency)
- Emit a structured `tool_call_started` event when a tool begins (client can show loading indicator)
- Emit `tool_call_result` when tool returns (client can show data before final prose)
- Suppress internal graph routing events

Confidence note on `.astream_events()`: HIGH — this API existed in LangGraph 0.1.x and was stable by 0.2.x. Verify exact event type names against current docs before implementing.

---

## Data Flow: Odds API → Regime → Alpha → Alert

```
1. INGESTION (APScheduler, every 5 min)
   OddsClient.get_odds(sport)
        │
        ▼
   Redis cache (odds TTL: 90s)
   Supabase odds_history (for regime lookups)

2. REGIME DETECTION (synchronous within graph node)
   BettingRegimeDetector.classify(game_id)
        reads: Redis cached odds + line movement history from Supabase
        computes: ticket_pct, handle_pct, book alignment, movement velocity
        returns: RegimeState(regime=SHARP_VS_PUBLIC, confidence=0.82, scale=1.4)

3. EV + MODEL (synchronous within graph nodes)
   ev_calculator.calculate_ev(market_odds, ensemble_prob)
        reads: model prediction from GameFeatureBuilder (ESPN + weather + injury data)
        returns: EVAnalysis(ev_pct=0.064, edge_prob=0.81, at_key_number=True)

4. ALPHA COMPOSITION (synchronous)
   AlphaComposer.compose(ev_analysis, regime_state, model_preds, calibration_mult)
        returns: BettingAlpha(alpha=0.142, quality_badge='HIGH')

5. VALIDATE (LLM gate)
   BettingSetupEvaluator.evaluate(setup, game_context)
        if REJECT: pipeline terminates, no alert
        if PASS/WARN: continue

6. MONTE CARLO SIZING
   MonteCarloSimulator.simulate(win_prob, odds, unit_size)
        returns: ruin_prob=0.031, p50=1.23x, p95=2.1x, p05=0.61x

7. ALERT DISPATCH
   generate_report node: formats Discord embed + web/mobile push payload
   alert_ready=True → Discord alert dispatcher job picks up
                     → FastAPI /alerts endpoint returns to web/mobile
                     → Push notification via Expo (mobile)

8. PERSISTENCE
   alpha-ranked alert stored in Supabase value_plays table
   monte_carlo result stored with alert for display in bankroll UI
```

---

## Package Structure (New Additions)

```
packages/
└── agents/                              ← NEW package
    └── src/sharpedge_agents/
        ├── __init__.py
        ├── state.py                     ← BettingAnalysisState TypedDict
        ├── workflow.py                  ← StateGraph definition + compile()
        ├── nodes/
        │   ├── __init__.py
        │   ├── route_intent.py          ← GPT-4o-mini routing node
        │   ├── fetch_context.py         ← async gather across data feeds
        │   ├── detect_regime.py         ← calls regime.py
        │   ├── run_models.py            ← calls model ensemble
        │   ├── calculate_ev.py          ← calls ev_calculator + key_numbers
        │   ├── validate_setup.py        ← GPT-4o-mini evaluator gate
        │   ├── compose_alpha.py         ← calls alpha.py
        │   ├── size_position.py         ← calls monte_carlo.py + Kelly
        │   └── generate_report.py      ← GPT-4o report formatter
        ├── copilot.py                   ← BettingCopilot class
        ├── copilot_tools.py             ← @tool-decorated functions
        ├── evaluator.py                 ← BettingSetupEvaluator
        └── snapshot.py                  ← CopilotSnapshot hydration

packages/models/src/sharpedge_models/
    ├── monte_carlo.py                   ← NEW: MonteCarloSimulator
    ├── alpha.py                         ← NEW: AlphaComposer + BettingAlpha
    └── walk_forward.py                  ← NEW: WalkForwardBacktester

packages/analytics/src/sharpedge_analytics/
    ├── regime.py                        ← NEW: BettingRegimeDetector
    └── key_numbers.py                   ← NEW: KeyNumberZoneDetector

apps/api/                                ← NEW app (extends webhook_server patterns)
    └── src/sharpedge_api/
        ├── main.py
        └── routes/
            ├── value_plays.py
            ├── game_analysis.py
            ├── copilot.py               ← SSE streaming endpoint
            ├── portfolio.py
            ├── bankroll.py
            └── prediction_markets.py
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Putting I/O Inside Quant Modules
**What goes wrong:** `MonteCarloSimulator`, `AlphaComposer`, `BettingRegimeDetector` reach into Supabase or Redis directly.
**Why bad:** Breaks testability. Quant modules need unit tests with no external deps. State graph nodes own I/O; quant modules are pure functions.
**Instead:** Nodes fetch all data, pass plain Python dicts/dataclasses to quant modules.

### Anti-Pattern 2: Shared Mutable State Between Concurrent Graph Runs
**What goes wrong:** Two concurrent `BettingAnalysisWorkflow` invocations share a global object (e.g., Redis connection pool used unsafely, or a module-level cache dict mutated during a run).
**Why bad:** Race conditions. LangGraph compiles a reusable graph object — the `state` dict is per-invocation, but any module-level mutable state is shared.
**Instead:** Make quant modules stateless. Connection pools are fine (they are thread/async-safe). Module-level mutable dicts are not.

### Anti-Pattern 3: Calling `analyze_game` Inside the Background Job Hot Path for Every Game
**What goes wrong:** Each scheduled scan invokes the full 9-node LangGraph workflow (including two LLM calls) for every candidate game.
**Why bad:** At 100+ simultaneous games, LLM costs become punishing. The evaluator LLM call alone at $0.003/request × 100 games × 12 scans/hour = $3.60/hour.
**Instead:** Background job runs the deterministic nodes (fetch_context, detect_regime, run_models, calculate_ev, compose_alpha) and only invokes `validate_setup` + `generate_report` for games that clear the alpha threshold.

### Anti-Pattern 4: Storing the Full CopilotSnapshot in LangGraph State
**What goes wrong:** Embedding the entire portfolio history (hundreds of bet records) into the `BettingAnalysisState` TypedDict.
**Why bad:** LangGraph serializes state at checkpoints; large state inflates checkpoint size and slows graph execution.
**Instead:** Snapshot hydration lives in `copilot.py` as a Python object. The graph state holds only a `user_id` + lightweight summary. Tools fetch full data on demand.

### Anti-Pattern 5: Streaming Full Tool Results as Tokens
**What goes wrong:** When a copilot tool returns a large structured result (e.g., odds for 30 books), it gets streamed character by character as if it were prose.
**Why bad:** Client cannot parse structured data from a token stream.
**Instead:** Tool results are emitted as structured SSE events (`tool_call_result` event type with JSON payload), separate from the token stream.

---

## Scalability Considerations

| Concern | Current scale (Discord bot) | At 1K daily active users | At 10K daily active users |
|---------|----------------------------|--------------------------|---------------------------|
| Graph invocations | ~50/day | ~500/hour | Needs queue |
| LLM costs (validate + report nodes) | Negligible | ~$5-15/day | Consider caching report for identical game_id + alpha |
| Monte Carlo per request | Instant (2000 paths in <50ms pure numpy) | No concern | No concern |
| Regime detector | Cheap (deterministic, Redis-cached) | No concern | No concern |
| Supabase queries per graph run | ~4-6 queries | Redis caching absorbs most | Add read replicas |
| Copilot sessions | Not yet built | Session state in Redis (TTL 1hr) | Horizontal FastAPI replicas + Redis for session affinity |

---

## Build Order Implications

The dependency graph below determines which phases can start in parallel and which are blocked.

```
1. Quant modules (no dependencies on new code)
   packages/models/monte_carlo.py          ← can start immediately
   packages/models/alpha.py                ← can start immediately
   packages/analytics/regime.py            ← can start immediately
   packages/analytics/key_numbers.py       ← can start immediately

2. Agent nodes (depend on quant modules)
   packages/agents/nodes/detect_regime.py  ← blocked on regime.py
   packages/agents/nodes/compose_alpha.py  ← blocked on alpha.py
   packages/agents/nodes/size_position.py  ← blocked on monte_carlo.py
   packages/agents/nodes/calculate_ev.py   ← blocked on key_numbers.py
   packages/agents/nodes/fetch_context.py  ← no new deps, can start immediately
   packages/agents/nodes/validate_setup.py ← no new deps
   packages/agents/nodes/generate_report.py← no new deps

3. StateGraph wire-up (depends on all nodes)
   packages/agents/workflow.py             ← blocked on all nodes complete

4. BettingCopilot (depends on workflow + all tools)
   packages/agents/copilot.py              ← blocked on workflow.py

5. FastAPI layer (depends on workflow + copilot)
   apps/api/                               ← blocked on copilot.py + workflow.py

6. Front-ends (depend on FastAPI)
   Next.js web                             ← blocked on API routes stable
   Expo mobile                             ← blocked on API routes stable

7. WalkForwardBacktester (independent of hot path)
   packages/models/walk_forward.py         ← can build in parallel with step 1
```

The critical path is: **quant modules → agent nodes → StateGraph → Copilot → FastAPI → front-ends**.

Walk-forward backtester and ensemble model upgrade are off the critical path and can proceed in parallel.

---

## Sources

- LangGraph Python documentation (training data, August 2025 — MEDIUM confidence; verify current node/edge API signatures)
- UPGRADE_ROADMAP.md — primary source for FinnAI → SharpEdge pattern mapping (HIGH confidence, project document)
- `.planning/codebase/ARCHITECTURE.md` — existing system boundaries (HIGH confidence, project document)
- `.planning/PROJECT.md` — requirements and constraints (HIGH confidence, project document)
- LangGraph `StateGraph`, `TypedDict` state, conditional edges, `ToolNode`, `.astream_events()` — patterns verified consistent with LangGraph 0.2.x (MEDIUM confidence; check for breaking changes in any release post Aug 2025)
