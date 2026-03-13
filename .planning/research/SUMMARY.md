# Research Summary

**Project:** SharpEdge v2 — Institutional-Grade Sports Betting Intelligence Platform
**Synthesized:** 2026-03-13
**Source files:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md

---

## Executive Summary

SharpEdge v2 upgrades an existing functional Python monorepo (Discord bot + FastAPI + Supabase + Redis) into an institutional-grade betting intelligence platform. The research is unambiguous about the approach: replace the flat 3-agent OpenAI Agents SDK setup with a LangGraph StateGraph that models the full 9-node analysis pipeline as a directed acyclic workflow with conditional edges, parallel fan-out, and persistent checkpointing. Every other technology in the stack already exists in the codebase; the upgrade is additive, not a rewrite. The critical path runs from quant engine modules (MonteCarloSimulator, AlphaComposer, BettingRegimeDetector) through agent graph nodes, to the FastAPI REST layer, and finally to web and mobile front-ends.

The competitive differentiation is concrete: no retail betting tool combines composite alpha scoring, Monte Carlo ruin simulation, regime-aware sizing, an LLM quality gate, a conversational copilot, and prediction market edge detection in one platform. The combination is the moat. The hardest features to replicate are BettingCopilot (requires stable StateGraph) and the regime detector (requires multi-season training data). The features most demanded by serious bettors — CLV tracking, calibrated probabilities, walk-forward backtesting — are also achievable within the existing data foundation.

The top risks are not algorithmic but architectural: lookahead bias in the walk-forward backtester (feature timestamps are unvalidated), LangGraph parallel state collisions (reducers not yet defined), context window overflow in copilot sessions, and the HMM regime detector being trained on insufficient data if it targets 7 states immediately. Each of these has a clear prevention strategy documented in PITFALLS.md and must be addressed in Phase 1 and Phase 2 before downstream work is valid.

---

## Key Findings

### From STACK.md

| Technology | Rationale |
|-----------|-----------|
| LangGraph 0.2.x | Only Python framework that models the 9-node conditional workflow with parallel fan-out and persistent checkpointing; replaces flat OpenAI Agents SDK |
| hmmlearn 0.3.x | Stable, sklearn-compatible HMM library; pomegranate dropped due to PyTorch dependency and 2024 API instability |
| numpy 2.0 default_rng | Vectorized Monte Carlo (10k paths in one call); per-call Generator required for thread safety |
| sklearn CalibratedClassifierCV | Platt scaling on existing GBM models; `cv='prefit'` prevents calibration data leakage |
| Next.js 14.2.x | App Router is production-stable; Next.js 15 breaking changes in caching and params types make it premature |
| Expo SDK 51 | Managed workflow eliminates native build overhead; EAS Build handles CI/CD; shared TypeScript types with web via monorepo workspace |
| Tanstack Query 5.x | Shared data-fetching hooks across Next.js and Expo via `packages/hooks/` workspace package |
| langgraph-checkpoint-postgres | Persistent conversation memory across Discord sessions using existing Supabase connection |

**Critical version flags:** All versions marked [VERIFY] in STACK.md must be confirmed against PyPI/npm before pinning. Knowledge cutoff is August 2025; Expo SDK, LangGraph minor version, and langgraph-checkpoint-postgres package name all require validation.

**What NOT to use:** aioredis (deprecated), OpenAI Agents SDK for graph routing, pomegranate, matplotlib for web/mobile output, np.random.seed() (global state), AsyncStorage for mobile auth tokens, Next.js Pages Router for new pages.

---

### From FEATURES.md

**Must-have (table stakes):**
- EV calculator, no-vig fair odds, multi-book comparison — already built
- Line movement history/classification — already built
- Arbitrage detection — already built
- Kelly Criterion sizing — already built
- CLV tracking — NOT YET BUILT; high credibility risk with serious bettors, simple to add
- Bet tracking with ROI/win rate — schema exists, portfolio API route needed
- Odds alerts/notifications — Discord exists, mobile push needed

**Should-have (differentiators — the moat):**
- Composite Alpha Score (EV × regime × survival × confidence) — no retail tool does multi-factor composition
- Monte Carlo bankroll ruin simulation — uniquely communicable risk metric; no retail equivalent
- 7-state betting market regime detection (HMM) — regime-aware sizing unavailable in any retail tool
- Walk-forward backtesting with quality badges — honest out-of-sample validation
- LLM Setup Evaluator (PASS/WARN/REJECT gate) — reduces false-positive alerts
- BettingCopilot with portfolio awareness — highest retention; closest to a quant analyst in a pocket
- Prediction market edge detection (Kalshi/Polymarket) — novel at retail level
- Cross-market correlation engine — prevents double-exposure across correlated bets
- Model calibration quality badges — builds trust, differentiates from black-box tip services

**Defer to v2+ (anti-features):**
Automated bet placement, social/community features, picks marketplace, browser extension, sportsbook account health scoring, general sports news feed, public consensus aggregation, paper trading, AI-generated game narratives.

**MVP upgrade priority order:** Alpha Score → Regime Detector → Monte Carlo → LLM Evaluator → LangGraph StateGraph skeleton → BettingCopilot. CLV tracking should not be deferred — add it before Copilot.

---

### From ARCHITECTURE.md

**Major components and responsibilities:**

| Component | Package | Responsibility |
|-----------|---------|----------------|
| BettingAnalysisWorkflow | packages/agents/ | 9-node LangGraph StateGraph; routes bet analysis through specialist nodes |
| BettingCopilot | packages/agents/ | Stateful conversational agent; tool-call loop against CopilotSnapshot |
| BettingSetupEvaluator | packages/agents/ | GPT-4o-mini gate; validates candidate alerts before report node |
| MonteCarloSimulator | packages/models/ | 2000-path bankroll simulation; returns ruin probability + percentile outcomes |
| BettingRegimeDetector | packages/analytics/ | 7-state market regime classifier using line movement, ticket%, handle% |
| AlphaComposer | packages/models/ | Composite alpha = edge_prob × ev_score × regime_scale × survival_prob × confidence_mult |
| WalkForwardBacktester | packages/models/ | Off-critical-path; background job; produces quality badges |
| FastAPI layer | apps/api/ | REST + SSE endpoints; proxies to agent and quant layers |

**Key patterns:**
- Quant modules are pure functions with no I/O dependencies — nodes are thin wrappers that pass plain Python data in and state updates out. This keeps quant modules unit-testable in isolation.
- BettingAnalysisState is a single TypedDict threaded through all 9 nodes. No side-effecting global state.
- Two LLM call tiers: GPT-4o-mini for route_intent and validate_setup (routing/gating); GPT-4o for generate_report only (quality matters here).
- Background job runs deterministic nodes only; LLM nodes invoked only for games clearing alpha threshold. This limits LLM cost scaling.
- Copilot uses SSE streaming via FastAPI StreamingResponse; client receives structured `tool_call_result` events separate from token stream.
- CopilotSnapshot is a Python object in copilot.py, not in LangGraph state. Only user_id and lightweight summary live in graph state.

**Critical path:** quant modules → agent nodes → StateGraph wire-up → BettingCopilot → FastAPI → front-ends. Walk-forward backtester and ensemble model upgrade are off critical path and can proceed in parallel.

---

### From PITFALLS.md

**Top 5 pitfalls with prevention strategies:**

**1. LangGraph parallel state collisions (CRITICAL)**
Two nodes writing the same state key without an `Annotated` reducer silently overwrites one result. Default reducer is last-write-wins; no error raised. Prevention: audit every state key, use `Annotated[T, operator.add]` for multi-writer keys. Phase 2.

**2. Backtesting lookahead bias via feature leakage (CRITICAL)**
Features without `valid_at` timestamps allow future data to contaminate historical windows. Existing `backtesting.py` has 4 unimplemented stub methods; `datetime.utcnow()` (timezone-naive) used throughout. Prevention: add `valid_at` to all features, fix stubs and datetime before writing walk-forward window logic, add `LeakageAudit` test. Phase 1.

**3. Monte Carlo global RNG — concurrent session contamination (CRITICAL)**
`np.random.seed(42)` is not thread-safe. Concurrent FastAPI requests share global RNG state. Prevention: use `np.random.default_rng(seed=None)` per call in production, seed only in tests. Phase 1.

**4. HMM regime detector under-trained on 7 states (CRITICAL)**
Sports betting data is sparse relative to equity tick data. A 7-state HMM requires 2000+ labeled observations; NFL has ~270 games/year. Prevention: start with 3–4 states; add a rule-based fallback classifier while gathering multi-season training data; expand states only after validation. Phase 1.

**5. LangGraph conditional edge infinite loops (CRITICAL)**
WARN re-route without a loop counter runs unlimited LLM calls. Prevention: add `retry_count: int` to BettingAnalysisState; set `recursion_limit=10` on graph.compile(). Phase 2.

**Additional high-priority pitfalls:**
- Copilot context window overflow after 5–10 turns with large tool payloads — sliding window + tiktoken tracking required (Phase 2)
- PM scanner fires on illiquid markets (bid-ask spread creates fake edges) — liquidity filter + bid price, not mid price (Phase 3)
- Supabase RLS not enabled exposes all user portfolio data — enable before any user-scoped API route goes live (Phase 4)
- Retroactive Platt scaling calibration inflates confidence badges — rolling calibration, fit on lagged data only (Phase 5)
- visualizations.py (896 lines) and tools.py (576 lines) block imports when split — maintain backward-compatible re-exports during split (Phase 1)

---

## Implications for Roadmap

The feature dependency graph from FEATURES.md and the build order from ARCHITECTURE.md converge on the same phase structure. The phase boundaries below are not arbitrary — each represents a natural dependency boundary where downstream work cannot begin until upstream deliverables are stable.

### Suggested Phase Structure (5 Phases)

**Phase 1 — Quant Engine Foundation**
Build all pure-Python quantitative modules with no LangGraph dependency. These are the computational primitives everything else depends on.

- MonteCarloSimulator (numpy default_rng, per-call RNG, thread-safe)
- AlphaComposer with minimum edge floor
- BettingRegimeDetector (3–4 states initially, rule-based fallback)
- KeyNumberZoneDetector
- WalkForwardBacktester stubs fixed + valid_at timestamps
- CLV tracking computation (simple, high credibility payoff)
- Fix: datetime.utcnow() → datetime.now(timezone.utc) across packages/models/
- Fix: split visualizations.py (896 lines) and tools.py (576 lines) with backward-compatible re-exports

Rationale: No agent or front-end work is valid until quant correctness is established. Lookahead bias, thread-safety, and HMM state-count decisions must be made here before downstream code encodes wrong assumptions.

Pitfalls to avoid: Pitfalls 1–4, 8–9, 12, 16.

Research flag: NEEDS DEEPER RESEARCH — HMM training data availability (how many seasons of betting data exist in Supabase), and optimal initial state count validation strategy.

---

**Phase 2 — Agent Architecture (LangGraph StateGraph + Copilot)**
Wire quant modules into the 9-node StateGraph. Build BettingCopilot. Build BettingSetupEvaluator.

- BettingAnalysisState TypedDict with Annotated reducers
- All 9 graph nodes as thin wrappers around quant modules
- StateGraph compilation with recursion_limit=10 and error handler node
- BettingCopilot with CopilotSnapshot, sliding window session management, tiktoken tracking
- BettingSetupEvaluator (GPT-4o-mini gate)
- LangGraph checkpoint-postgres for Discord session persistence
- Background job updated to run deterministic nodes only; LLM nodes only for alpha-clearing games

Rationale: StateGraph is the integration point for all quant work. Copilot is the highest-retention feature and the architectural test of whether the graph routes correctly. Both must be stable before any front-end is built.

Pitfalls to avoid: Pitfalls 5, 6, 7, 11 (state collisions, infinite loops, context overflow, async exception handling, rate limit deduplication).

Research flag: STANDARD PATTERNS — LangGraph StateGraph is well-documented; verify exact `.astream_events()` event type names and `recursion_limit` parameter against current LangGraph docs before implementing.

---

**Phase 3 — Prediction Market Intelligence**
Add Kalshi/Polymarket edge scoring and PM regime classification on top of the stable Phase 2 graph.

- PredictionMarketEdgeScanner with liquidity filter and bid-price edge calculation
- PM regime classification (Discovery / Consensus / News Catalyst / Pre-Resolution)
- Cross-market correlation engine (prevent double-exposure across correlated bets)
- Extend BettingCopilot tools: get_prediction_market_edge

Rationale: PM features are novel differentiators but depend on the full alpha pipeline being stable (Phase 1+2). The liquidity filter (Pitfall 10) must be in place before PM alerts are dispatched.

Pitfalls to avoid: Pitfall 10 (illiquid market scanner over-firing).

Research flag: NEEDS DEEPER RESEARCH — current Kalshi/Polymarket API liquidity data fields and rate limits should be verified; competitive PM edge tools may have emerged since August 2025 training cutoff.

---

**Phase 4 — API Layer + Front-Ends (Web and Mobile)**
Build FastAPI REST + SSE layer, Next.js web dashboard, Expo mobile app, and enable Supabase RLS.

- FastAPI REST + SSE endpoints (value_plays, game_analysis, copilot chat, portfolio, bankroll, PM)
- Enable Supabase RLS on bets/users/value_plays before any user-scoped endpoint goes live
- Multi-worker gunicorn deployment configured from day one
- Next.js 14.2 web dashboard: alpha scores, Monte Carlo charts (Recharts), regime timeline, portfolio/CLV
- Expo SDK 51 mobile app: value plays feed, copilot chat, push notifications for alpha alerts
- Push notification APNs entitlements configured and tested on real device (not simulator) before Phase 5
- Shared packages/api-client/, packages/hooks/, packages/types/ workspace packages

Rationale: All front-end work is blocked on stable API routes. Both web and mobile can build in parallel once API routes are stable. RLS must precede any user-scoped route deployment.

Pitfalls to avoid: Pitfalls 13 (single-worker SSE blocking), 14 (iOS APNs entitlements), 15 (RLS not enabled).

Research flag: STANDARD PATTERNS — Next.js 14 App Router and Expo Router are well-documented; verify current shadcn/ui and next-auth v4 compatibility with Next.js 14.2 before starting web phase.

---

**Phase 5 — Data Pipeline + Model Upgrade**
Implement continuous model improvement and walk-forward validation quality badges. Expand HMM to 7 states once training data is validated.

- Rolling Platt scaling calibration on lagged data only (not retroactive)
- 5-model ensemble upgrade (team form, matchup, injury, sentiment, weather) — only if benchmark justifies
- WalkForwardBacktester full implementation with non-overlapping windows and quality badges
- HMM expansion from 3–4 states to 7 states if multi-season data supports it
- LightGBM upgrade for gradient boosting if >10% benchmark gain demonstrated
- Confidence multiplier sourced from rolling calibration window (not live calibration set)

Rationale: Model improvements are valuable but not blocking. Walking forward the backtester requires stable historical data pipeline (already in Supabase). Calibration and ensemble upgrades are operational improvements to an already-working prediction system.

Pitfalls to avoid: Pitfall 12 (retroactive Platt calibration), Pitfall 8 (overlapping walk-forward windows).

Research flag: STANDARD PATTERNS for sklearn calibration; NEEDS DEEPER RESEARCH for multi-sport HMM state validation and LightGBM benchmark methodology.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Core choices (LangGraph, hmmlearn, numpy, sklearn) are HIGH confidence. Frontend version pinning (Next.js 14.2, Expo SDK 51) is MEDIUM — ecosystem may have advanced since Aug 2025 training cutoff. All [VERIFY] tags must be resolved before pinning versions. |
| Features | HIGH | Feature categorization is derived from PROJECT.md and UPGRADE_ROADMAP.md (primary sources). Competitive positioning is MEDIUM — based on training data through Aug 2025, not live product verification. |
| Architecture | MEDIUM-HIGH | StateGraph node design and data flow are HIGH confidence (matches LangGraph 0.2.x patterns). Exact API signatures (.astream_events() event types, recursion_limit parameter) are MEDIUM — verify against current LangGraph docs before implementing. |
| Pitfalls | HIGH for most | Lookahead bias, numpy thread-safety, context overflow, Supabase RLS, and LangGraph state mutations are HIGH confidence (well-documented canonical problems). HMM minimum sample requirements and Expo APNs behavior are MEDIUM. |
| Overall | MEDIUM-HIGH | Research is internally consistent across all four files. The main uncertainty is version staleness (WebSearch unavailable; knowledge cutoff August 2025). Version verification is a low-effort, high-value action before Phase 1 starts. |

---

## Gaps to Address

1. **Version verification:** All [VERIFY] tags in STACK.md must be resolved against PyPI/npm before Phase 1 begins. Especially: LangGraph 0.2.x minor version, langgraph-checkpoint-postgres exact package name, Expo SDK current version.

2. **HMM training data audit:** Count how many seasons of betting data exist in Supabase per sport before committing to 3-state vs 7-state regime detector. The decision affects the alpha formula's regime_scale multiplier design.

3. **Competitive landscape re-verification:** FEATURES.md competitive analysis is based on August 2025 training data. OddsJam, Pikkit, and Action Network may have shipped features that reduce SharpEdge's differentiation since then. Verify before roadmap is finalized.

4. **Existing codebase audit:** PITFALLS.md flags datetime.utcnow() usage, unimplemented backtesting stubs, and the 896-line visualizations.py. A quick codebase scan should map the full scope of these issues before Phase 1 estimates are set.

5. **LangGraph current docs:** Verify `.astream_events()` event type names, `recursion_limit` parameter location, and `ToolNode` API against current LangGraph documentation before agent architecture work begins.

6. **Kalshi/Polymarket API liquidity fields:** PM edge scanner design depends on access to bid-ask spread and open interest data. Verify these fields are available in both APIs before Phase 3 is scoped.

---

## Aggregated Sources

| Source | Confidence | Scope |
|--------|------------|-------|
| PROJECT.md (project document) | HIGH | Existing feature inventory, constraints, architecture |
| UPGRADE_ROADMAP.md (project document) | HIGH | Feature specifications, upgrade phases |
| .planning/codebase/ARCHITECTURE.md (project document) | HIGH | Existing system boundaries and package structure |
| LangGraph Python documentation (training knowledge, Aug 2025) | MEDIUM | StateGraph, node patterns, conditional edges, checkpointing |
| numpy / scipy / sklearn documentation (training knowledge) | HIGH | Monte Carlo, calibration, HMM patterns |
| hmmlearn documentation (training knowledge) | HIGH | GaussianHMM API, sklearn compatibility |
| Competitive tool landscape (OddsJam, Action Network, Pikkit, etc.) | MEDIUM | Feature comparison — not live-verified |
| Next.js 14 / Expo SDK 51 documentation (training knowledge) | MEDIUM | Version pinning decisions — verify against current releases |

**Note:** WebSearch and WebFetch were unavailable during all research sessions. All external claims are from training knowledge through August 2025. Version verification against PyPI, npm, and official documentation is the single highest-leverage action before development begins.
