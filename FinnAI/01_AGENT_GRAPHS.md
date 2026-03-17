# Quant Agentic System: Exact Agent Graphs

## Scope
This document defines graph topology for:
- Quant Strategy Factory (user-facing, current + target).
- Internal Prop System (admin-only, target).

There is a single strategy build mode (`standard`). OOS, walk-forward, and Monte Carlo are default requirements.

## 1) Quant Strategy Factory: Current Build Graph (Exact Node IDs)
Source: `apps/orchestrator/src/quantFactory/workflow.ts`.

```mermaid
flowchart TD
  START["__start__"] --> N1["intent_normalize"]
  N1 --> N2["research_context"]
  N2 --> N3["template_match"]
  N3 --> N4["strategy_design"]
  N4 --> N5["code_compile"]
  N5 --> N6["static_validate"]
  N6 --> N7["backtest_plan"]
  N7 --> N8["execute_backtests"]
  N8 --> N9["summarize"]
  N9 --> N10["persist"]
  N10 --> END["__end__"]
```

### Node responsibilities
- `intent_normalize`: normalize prompt/request into `QuantStrategyRequest`.
- `research_context`: event risk + news + macro + research specialist synthesis.
- `template_match`: choose best template family using prompt + context.
- `strategy_design`: strategy specialist + codegen specialist produce concrete DSL.
- `code_compile`: DSL -> deterministic Python artifact + hashes.
- `static_validate`: lint and policy checks.
- `backtest_plan`: persist strategy/version, create run row, fetch bars.
- `execute_backtests`: IS/OOS + WF + MC + sensitivity + gate.
- `summarize`: backtest analyst summary.
- `persist`: persist report, finalize run, update strategy status.

## 2) Quant Strategy Conversation Graph (Current `/query` + Chart Chat + Discord)
Source: `apps/orchestrator/src/index.ts`, `apps/web/src/app/charting/page.tsx`, `apps/orchestrator/src/discord-server/src/bot/discordBot.ts`.

```mermaid
flowchart TD
  U1["User NL prompt"] --> Q1["is quant command?"]
  Q1 -->|yes| C1["execute !quant* command path"]
  Q1 -->|no| Q2["is quant intent?"]
  Q2 -->|no| FALL["normal ChatOps path"]
  Q2 -->|yes| S1["resolve symbol (LLM-first)"]
  S1 --> P1["persist stage=confirm_build"]
  P1 --> R1["send proposal"]
  R1 --> U2["user reply"]
  U2 --> D1["yes/no/revise"]
  D1 -->|revise| S2["re-resolve symbol + update pending plan"]
  D1 -->|no| X1["clear conversation state"]
  D1 -->|yes| B1["POST /api/quant/strategies/create"]
  B1 --> P2["persist stage=confirm_subscribe"]
  P2 --> U3["ask subscribe yes/no"]
  U3 --> D2["yes/no"]
  D2 -->|yes| B2["POST /api/quant/strategies/:id/subscribe"]
  D2 -->|no| X2["clear conversation state"]
  B2 --> X3["clear conversation state"]
```

Notes:
- Conversation state has DB persistence with in-memory cache fallback and 15-minute TTL.
- Pre-confirmation symbol resolution uses backend LLM-first resolver with heuristic/regex fallback.

## 3) Quant Alerts Graph (Current)
Source: `apps/orchestrator/src/quantFactory/service.ts`, Discord bot scheduler.

```mermaid
flowchart TD
  T0["Scheduler tick"] --> A1["POST /api/quant/alerts/poll"]
  A1 --> A2["load active subscriptions"]
  A2 --> A3["fetch bars + evaluate latest signal"]
  A3 --> A4["upsert signal_state"]
  A4 --> A5["dedupe/cooldown + transition check"]
  A5 -->|transition| A6["send Discord alert"]
  A6 --> A7["POST /api/quant/alerts/ack"]
  A5 -->|none| A8["no-op"]
```

## 4) Internal Prop System: Target Build/Deploy Graph (Admin-only)
This is the recommended deterministic graph for the separate prop pipeline.

```mermaid
flowchart TD
  S0["intent_normalize"] --> S1["account_policy_resolve"]
  S1 --> S2["market_research_context"]
  S2 --> S3["candidate_strategy_generation"]
  S3 --> S4["dsl_compile"]
  S4 --> S5["static_validate_and_sandbox_check"]
  S5 --> S6["validation_suite_run"]
  S6 --> S7["prop_rule_compliance_check"]
  S7 --> S8["score_and_rank"]
  S8 --> S9["human_approval_gate"]
  S9 -->|approved| S10["paper_shadow_run"]
  S9 -->|rejected| S11["revision_loop"]
  S10 --> S12["execution_plan_build"]
  S12 --> S13["account_execution"]
  S13 --> S14["live_monitoring_and_risk_kill_switch"]
  S14 --> S15["drift_detection_and_retrain_queue"]
  S15 --> END["post_trade_review_and_registry_update"]
```

## 5) Internal Prop System: Continuous Monitoring Graph (Target)

```mermaid
flowchart TD
  M0["position/PNL stream"] --> M1["risk_limit_check"]
  M1 -->|breach| M2["flatten_or_block_new_entries"]
  M1 -->|ok| M3["strategy_health_check"]
  M3 --> M4["drift_detection"]
  M4 -->|drift| M5["retrain_candidate_build"]
  M4 -->|stable| M6["continue"]
  M5 --> M7["revalidation_suite"]
  M7 -->|pass| M8["promote_model_version"]
  M7 -->|fail| M9["archive_and_alert"]
```

## 6) Agent roster by graph
- Quant Strategy Factory agents:
  - `ResearchAgent`
  - `StrategyDesignerAgent`
  - `CodegenAgent`
  - `BacktestAnalystAgent`
- Prop System agents (target):
  - `PropPolicyAgent`
  - `ResearchAgent`
  - `CandidateGeneratorAgent`
  - `ValidationAnalystAgent`
  - `ExecutionPlannerAgent`
  - `RiskSentinelAgent`
  - `DriftAndRetrainAgent`

All numeric market outputs must come from tools/engines, not free-form model text.
