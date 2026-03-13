# Domain Pitfalls

**Domain:** LangGraph agent orchestration + quantitative sports betting engine
**Project:** SharpEdge v2
**Researched:** 2026-03-13
**Confidence:** MEDIUM — LangGraph pitfalls drawn from known 0.1–0.2 API behavior and community patterns; quant pitfalls drawn from established numerical computing literature; sports betting pitfalls from known domain constraints. WebSearch unavailable; all claims based on training knowledge through August 2025. Flag for verification where noted.

---

## Critical Pitfalls

Mistakes that cause rewrites, silent incorrect output, or production failures.

---

### Pitfall 1: LangGraph State Mutation Overwrites Parallel Node Output

**What goes wrong:** When two nodes run in parallel (e.g., `fetch_context` and `detect_regime` running concurrently via `add_edge` branching), both nodes write to the same `BettingAnalysisState` TypedDict key. LangGraph's default reducer is `last_write_wins`. If both nodes write to `game_context`, one result is silently dropped. No error is raised.

**Why it happens:** LangGraph requires explicit `Annotated` reducers for any state key that multiple nodes write to. Without them, the merge strategy is undefined and order-dependent (nondeterministic in async execution).

**Consequences:**
- `game_context` populated by one node gets overwritten by another writing a partial update
- Regime detection runs on stale data because its input was silently clobbered
- Alpha score is computed from inconsistent inputs — wrong outputs with no visible error

**Prevention:**
```python
from typing import Annotated
import operator

class BettingAnalysisState(TypedDict):
    # Nodes that append findings use operator.add
    quality_warnings: Annotated[list[str], operator.add]
    # Nodes that do a full replacement use a custom last-write reducer
    game_context: GameContext          # Only one node writes this — safe
    regime_state: RegimeState          # Only one node writes this — safe
    model_predictions: ModelPreds      # Only one node writes this — safe
```
Audit every state key: identify which nodes write it, use `Annotated[T, reducer]` for any key touched by more than one node. Test parallel paths explicitly.

**Detection:** Write a test that runs the graph with two parallel nodes both writing the same key; assert both values survive. Absence of assertion failure = problem.

**Phase:** Phase 2 (Agent Architecture) — must be correct before any parallel specialist nodes are added.

---

### Pitfall 2: Backtesting Lookahead Bias via Feature Leakage

**What goes wrong:** The walk-forward backtester uses features that were not available at the time the bet was placed. Common leakages in this project:
- **Final injury report** used to retrain model, but at bet time only the morning injury report existed
- **Closing line** used as a feature, but the bet was placed at open
- **Public betting %** from post-close aggregators applied to pre-game windows
- `datetime.utcnow()` comparisons using naive datetimes mix timezone-aware and naive objects, causing incorrect window boundaries

**Why it happens:** Historical data fetched from Supabase is stored with resolution timestamps. If those timestamps are imprecise or missing, the feature builder cannot safely reconstruct what was known at bet time. The existing `backtesting.py` has 4 unimplemented stub methods (`save_result`, `load_results`) — the persistence layer was never validated, so window boundaries were never tested.

**Consequences:** Backtester reports positive out-of-sample ROI that does not exist in live trading. Walk-forward quality badge reads `excellent` for a leaky strategy. Users receive `PREMIUM` alerts based on a phantom edge.

**Prevention:**
- Every feature must carry a `valid_at: datetime` timestamp
- The `WalkForwardBacktester.validate()` method must filter features using `feature.valid_at <= window_start`
- Implement the 4 stub methods before building any window logic
- Fix `datetime.utcnow()` to `datetime.now(timezone.utc)` across `packages/models/` before writing any window comparison logic
- Add a `LeakageAudit` test that asserts no feature `valid_at` falls after the window boundary

**Detection:** Run backtest on a known-loser strategy; if it shows positive ROI, leakage is present.

**Phase:** Phase 1 (Quant Engine) — fix stubs and datetime issue before implementing walk-forward windows.

---

### Pitfall 3: Monte Carlo Fixed Seed Produces Misleading Reproducibility

**What goes wrong:** `seed=42` in `simulate_bankroll()` makes results fully reproducible — which is correct for testing — but creates two production problems:
1. If `seed` is hardcoded in the production call path, every user gets the same 2000 paths regardless of their `win_prob` or `unit_size_pct`. The variance looks right but the path distribution is not independently sampled per call.
2. Using `numpy.random.seed(42)` (global seed) makes the entire process non-thread-safe. When the FastAPI `/bankroll/simulate` endpoint handles concurrent requests, global seed state is shared. Results from concurrent calls contaminate each other.

**Why it happens:** The FinnAI `monteCarloSimulator.ts` used a deterministic seed for the Box-Muller transform for testability. The Python port must use `numpy.random.Generator` (not the legacy global RNG) with per-call RNG instances.

**Consequences:** Concurrent API users see silently wrong variance estimates. Two users simulating different bet sizes at the same time may receive results swapped between sessions.

**Prevention:**
```python
# WRONG — global state, not thread-safe
np.random.seed(42)
results = np.random.normal(...)

# CORRECT — per-call RNG instance
rng = np.random.default_rng(seed=seed if seed is not None else None)
results = rng.normal(...)
```
The `seed` parameter should default to `None` in production (non-reproducible) and only be set explicitly in tests. Document this distinction in the method signature.

**Detection:** Write a test that calls `simulate_bankroll()` twice with different `win_prob` values but the same seed in two threads; assert distributions differ.

**Phase:** Phase 1 (Quant Engine) — implement correctly from the start; retrofitting thread safety is error-prone.

---

### Pitfall 4: HMM Regime Detector Has Insufficient Training Data for 7 States

**What goes wrong:** A 7-state HMM requires a minimum of roughly 10× the number of states in observations per state to converge reliably — approximately 700+ labeled regime observations minimum, more realistically 2000+. Sports betting lines data has structural sparsity:
- NFL season: ~270 games/year × 16 weeks = limited samples per regime state
- Some regimes (`STEAM_MOVE`, `THIN_MARKET`) occur infrequently
- The existing historical odds pipeline in Supabase has no regime labels — the detector must be trained unsupervised or labels must be generated

If the HMM is trained on insufficient data, it will converge to a degenerate solution: one or two dominant states with near-zero probability mass on rare states like `STEAM_MOVE`. The `regime_scale` multiplier will be wrong for those states.

**Why it happens:** The design calls for "analogous to FinnAI's 7-state HMM" but FinnAI operates on equity markets with continuous tick data (millions of observations). Sports betting has hundreds or thousands of observations with weekly seasonality.

**Consequences:** Regime classification is confidently wrong. Alpha scores for rare regimes are miscalibrated. `SHARP_VS_PUBLIC` events (highest alpha at 1.4×) may be misclassified as `SETTLED`, suppressing the best alerts.

**Prevention:**
- Start with 3–4 states for the initial implementation, not 7; add states only after the classifier is validated
- Use multi-season historical data (minimum 3 seasons per sport) before fitting the HMM
- Consider a rule-based fallback regime classifier as a baseline while gathering training data: `ticket% > 70%` → `PUBLIC_HEAVY`, line moves > 1 point in < 15 min → `STEAM_MOVE`
- Validate regime transitions against known historical steam moves (traceable from line movement data)
- Use `hmmlearn` (scikit-learn compatible) for the HMM; validate with BIC/AIC model selection for number of states

**Detection:** After training, check the stationary distribution of the HMM. If any state has < 2% probability mass, it is underfitted.

**Phase:** Phase 1 (Quant Engine) — architecture decision (3 vs 7 states) must be made before implementing regime_scale multipliers.

---

### Pitfall 5: LangGraph Graph Cycles and Conditional Edges Cause Silent Infinite Loops

**What goes wrong:** The 9-node workflow has a `validate_setup` node that can issue `WARN` or `REJECT`. If the graph uses a conditional edge to re-route `WARN` back to earlier nodes for enrichment (a natural design), the graph can loop indefinitely. LangGraph does not enforce a maximum cycle count by default. In production, a `WARN` from the evaluator that keeps re-triggering `fetch_context` or `run_models` will consume unlimited LLM API calls.

**Why it happens:** Conditional edges in StateGraph are functions over state — they return a node name. Without an explicit loop counter tracked in state, there is no termination condition.

**Consequences:** Runaway LLM cost. Discord alert delayed indefinitely. FastAPI endpoint hangs until timeout. Concurrent users all stall behind the looping graph.

**Prevention:**
```python
class BettingAnalysisState(TypedDict):
    ...
    retry_count: int  # Increment in validate_setup; route to END if > MAX_RETRIES

def route_after_validation(state: BettingAnalysisState) -> str:
    if state["eval_result"].verdict == "PASS":
        return "compose_alpha"
    if state["retry_count"] >= 2:
        return "generate_report"  # Emit with WARN badge, don't loop
    return "fetch_context"  # Re-enrich once only
```
Add `recursion_limit` to `graph.compile()` as a safety net: `graph.compile(recursion_limit=10)`.

**Detection:** Instrument every node with a counter; alert if any graph execution exceeds 15 node invocations.

**Phase:** Phase 2 (Agent Architecture) — must be designed into the graph structure from the start.

---

### Pitfall 6: BettingCopilot Context Window Overflow on Long Sessions

**What goes wrong:** The `BettingCopilot` maintains `snapshot` state across follow-up questions. Each turn appends: the user message, tool call results (odds snapshots, portfolio stats, Monte Carlo JSON), and the assistant response. After 5–10 turns with tool calls returning large payloads (e.g., 30-book odds comparison JSON, full backtest report), the combined context exceeds GPT-4o's 128k token limit. The API raises a context length error. The copilot crashes mid-session.

**Why it happens:** The FinnAI `copilot.ts` pattern uses a snapshot object that is serialized and re-injected each turn. JSON serialization of structured betting data is verbose. A single `get_active_bets` tool response can return thousands of tokens if the user has many tracked bets.

**Consequences:** Copilot sessions fail after extended use (when they're most valuable). Error surfaces to the user as a crash, not a graceful "I can't recall earlier context."

**Prevention:**
- Implement a sliding window: keep the last N turns of full context + a compressed summary of earlier turns
- Truncate tool call responses before injection: extract only the top 5 results, not all 30 books
- Track running token count per session using `tiktoken`; when approaching 100k tokens, summarize the session state into a compressed snapshot and replace the full history
- Store the snapshot in Redis (keyed by Discord user ID + session ID) with a 30-minute TTL; reload on reconnect
- For the `/copilot` FastAPI endpoint, enforce a `max_session_turns` parameter

**Detection:** Log token count per copilot API call; alert when any call exceeds 80k tokens.

**Phase:** Phase 2 (Agent Architecture) — session management architecture must be designed before copilot is wired to the API.

---

## Moderate Pitfalls

---

### Pitfall 7: The Odds API Rate Limit Triggers on Parallel Graph Nodes

**What goes wrong:** The LangGraph workflow has nodes that fetch different data sources. If `fetch_context` and `detect_regime` both call The Odds API (e.g., context node fetches current lines, regime node fetches line movement history), they hit the API in parallel. The Odds API has a monthly quota (500 requests on free tier, varying on paid). Parallel execution within a single graph run can double or triple API usage per analysis. Under concurrent Discord command load (multiple users running `/analyze` simultaneously), the quota is exhausted rapidly.

**Prevention:**
- The existing Redis caching layer in `packages/odds_client/` must be used for all in-graph API calls — not just the background job scanner
- Deduplicate: fetch all required Odds API data in a single `fetch_context` node at graph entry, store in state, and have all downstream nodes read from state (not from the API)
- Add request counting to the Redis cache layer; alert when monthly quota is > 80% consumed
- Use snapshot-at-entry pattern: one API call per graph execution, not one per node

**Detection:** Log Odds API call counts per graph execution. More than 1 call per execution = architectural leak.

**Phase:** Phase 2 (Agent Architecture) — enforced before the graph is wired to live data.

---

### Pitfall 8: Walk-Forward Windows Produce False Stability When Windows Overlap

**What goes wrong:** Walk-forward validation splits historical bets into rolling windows. If training windows overlap (e.g., window 1: bets 1–100, window 2: bets 50–150), the same bets appear in multiple training sets. The model "learns" those bets twice. Reported cross-window consistency is inflated. The `out_of_sample_win_rate` appears stable because the model has effectively seen the test data.

**Why it happens:** Rolling window implementations default to overlapping to maximize data usage. When the existing backtest stubs are implemented, the window slicing logic is the highest-risk spot.

**Prevention:**
- Use non-overlapping windows for initial validation: window 1 = season 1 train / season 2 test, window 2 = seasons 1+2 train / season 3 test
- Explicitly assert in tests: `assert len(set(window_n.train_ids) & set(window_n.test_ids)) == 0`
- The quality badge should be downgraded one level if fewer than 3 non-overlapping windows are available

**Detection:** For each window pair, assert zero overlap between their test sets.

**Phase:** Phase 1 (Quant Engine) — window design must be settled before `BacktestReport.quality_badge` logic is written.

---

### Pitfall 9: Alpha Score Dominance by a Single Component Masks Weak Signals

**What goes wrong:** The composite alpha formula `edge_score × survival_prob × regime_scale × confidence_mult` uses multiplication. If `regime_scale = 1.4` (SHARP_VS_PUBLIC) and `confidence_mult = 1.3` (well-calibrated model), a mediocre `edge_score` of 0.1 produces `alpha = 0.1 × 1.0 × 1.4 × 1.3 = 0.182`. This ranks higher than a strong `edge_score = 0.25` in a `SETTLED` regime: `0.25 × 1.0 × 1.0 × 1.0 = 0.25`. The multipliers can overrank low-edge bets in favorable regimes, promoting `SPECULATIVE` setups as `PREMIUM`.

**Prevention:**
- Apply a minimum `edge_score` floor before multipliers are applied: if `edge_score < 0.05`, force alpha to `SPECULATIVE` regardless of multipliers
- Add a component breakdown to every `BettingAlpha` object so the explanation always shows what drove the score
- In the `LLM Setup Evaluator`, pass the raw component values — not just the composite alpha — so it can catch regime-boosted weak edges

**Detection:** Unit tests asserting that a bet with `P(edge > 0) < 0.55` never receives a `HIGH` or `PREMIUM` badge.

**Phase:** Phase 1 (Quant Engine) — must be built into the alpha formula definition, not patched in later.

---

### Pitfall 10: Prediction Market Scanner Over-Fires on Illiquid Markets

**What goes wrong:** The `PredictionMarketEdgeScanner` uses `|edge| > 0.03` as its threshold. On Kalshi/Polymarket markets with low open interest, the bid-ask spread alone can be 5–10 cents. The CLOB mid price on a thin market does not represent the true probability — it represents the last trade or the best one-sided quote. The scanner will fire on spread-induced "edges" that immediately close on entry.

**Prevention:**
- Add a minimum liquidity filter: `market.open_interest > MIN_OI_THRESHOLD` and `market.bid_ask_spread < 0.03` before edge calculation
- Use the bid price (for YES buys) not the mid price: `edge = model_prob - market.best_ask` for long entries
- Weight the alpha score by a liquidity factor: `liquidity_mult = min(1.0, market.open_interest / TARGET_OI)`
- The PM regime classifier's `THIN_MARKET` state should suppress alpha to near-zero, providing a second guard

**Detection:** Backtest PM alerts on historical data; filter for cases where the post-alert mid price moved > 2 cents against the recommended direction within 5 minutes.

**Phase:** Phase 3 (Prediction Market Intelligence) — must be in the scanner before any PM alerts are sent.

---

### Pitfall 11: LangGraph Async Node Exceptions Swallowed by Graph Executor

**What goes wrong:** If an async node in the StateGraph raises an unhandled exception (e.g., httpx timeout in `fetch_game_context`, Supabase connection error in `size_position`), LangGraph's default behavior is to propagate the exception to the graph caller. But if the caller does not explicitly await and handle it — or if the Discord command handler wraps only synchronous errors — the exception is swallowed. The graph returns `None` or an incomplete state. The Discord user receives no response and no error embed.

**Why it happens:** The existing codebase uses "log and continue" at job boundaries but the new LangGraph integration is at the command handler level. The command handler will need explicit `try/except` around the graph invocation that is not currently present.

**Prevention:**
- Wrap every `graph.ainvoke()` call in a `try/except` with explicit error embed dispatch to Discord
- Add a final `generate_report` node that handles both success and failure paths — always produces a response
- Use LangGraph's `add_fallback` edge pattern: any node failure routes to an `error_handler` node that formats a graceful degradation message
- The existing `CONCERNS.md` flags "silent failure" in the analytics package — this pattern must not be replicated in the agent layer

**Detection:** Integration test that injects a mock exception in `fetch_game_context`; assert the Discord command still returns a user-visible response.

**Phase:** Phase 2 (Agent Architecture) — error routing must be designed into the graph structure.

---

### Pitfall 12: Calibration Engine Trained on Out-of-Sample Predictions Retroactively

**What goes wrong:** The `ContinuousCalibrationEngine` uses Platt scaling to recalibrate model probabilities. If the calibration is applied retroactively — fitting Platt parameters on the full historical dataset and then re-scoring historical bets — the calibration is itself a form of lookahead bias. All historical confidence multipliers will be inflated. The `WELL_CALIBRATED` badge will be awarded to models that are not well-calibrated prospectively.

**Prevention:**
- Calibration parameters must be fit on a held-out calibration set that predates the test period
- Use a rolling calibration: re-fit Platt parameters every N games using only bets from > 30 days ago
- The `confidence_mult` used in live alpha scoring must use the calibration parameters from the previous rolling window, not the current one

**Detection:** Compare model probability distribution on hold-out bets before and after calibration; if calibration improves by more than 5 Brier score points on its own training data, retroactive fitting is likely.

**Phase:** Phase 5 (Data & Model Pipeline) — calibration architecture decision must be made before implementing `ContinuousCalibrationEngine`.

---

## Minor Pitfalls

---

### Pitfall 13: FastAPI Streaming Endpoint for Copilot Blocks Under Uvicorn Single Worker

**What goes wrong:** The `/api/v1/copilot/chat` endpoint streams LLM tokens using `StreamingResponse`. If deployed with a single Uvicorn worker (the default for development), a streaming copilot session holds a worker for the entire duration of the LLM response (5–20 seconds). Concurrent users are queued behind it. This is not a problem in development but will appear in production immediately.

**Prevention:** Deploy with `gunicorn -k uvicorn.workers.UvicornWorker` with worker count = `(2 × CPU cores) + 1`. Add this to the deployment documentation.

**Phase:** Phase 4 (Front-End / API) — deployment config must specify worker count before web/mobile go live.

---

### Pitfall 14: Expo Push Notifications Fail for iOS Without Entitlements

**What goes wrong:** Expo's push notification system requires APNs entitlements in the iOS provisioning profile. In development (Expo Go), notifications work without this. In production builds (EAS Build), the entitlement must be explicitly configured. High-alpha alerts delivered via push are the primary mobile value proposition — if this is not configured before TestFlight, it will appear to work and then silently fail in production.

**Prevention:** Configure `expo-notifications` in `app.json` with `ios.entitlements` set during Phase 4 setup, not at the end of Phase 5. Test on a real device via EAS Build before considering push notifications validated.

**Phase:** Phase 4 (Mobile App) — configure early, test on device, not just simulator.

---

### Pitfall 15: Supabase Row-Level Security Not Enabled Exposes All Users' Portfolio Data

**What goes wrong:** The architecture notes state "row-level security not currently used." The new FastAPI REST layer exposes `/api/v1/users/:id/portfolio` with user-scoped data. If RLS is not enabled, a user who obtains a valid JWT token can query any other user's portfolio by changing the `:id` parameter. The existing Supabase client uses the service role key for all queries — this bypasses RLS entirely.

**Prevention:**
- Enable RLS on `bets`, `users`, and `value_plays` tables before the API layer is built
- Use Supabase user JWTs (not the service role key) for user-scoped API queries
- The service role key should only be used in trusted server-side contexts (background jobs, admin operations)

**Detection:** Test: log in as user A, attempt to fetch user B's portfolio via the API; assert 403.

**Phase:** Phase 4 (API Layer) — RLS must be enabled before any user-scoped API endpoints are deployed.

---

### Pitfall 16: `visualizations.py` (896 lines) and `tools.py` (576 lines) Block Module Imports When Split

**What goes wrong:** These two oversized modules need to be split per the < 500-line constraint. However, they are imported by the existing Discord bot commands. A naive split that changes the import path will break all existing bot commands in production. There are currently zero tests to catch this regression.

**Prevention:**
- When splitting, maintain backward-compatible re-exports in the original module's `__init__.py` during the transition
- Write smoke tests for existing Discord commands before performing the split
- Split one module at a time, not both simultaneously

**Phase:** Phase 1 (Quant Engine) — these files are in `packages/analytics/` and `apps/bot/tools.py`; they will be touched during the agent upgrade. Split them before adding new code.

---

## Phase-Specific Warnings

| Phase | Topic | Likely Pitfall | Mitigation |
|-------|-------|----------------|------------|
| Phase 1 | Monte Carlo implementation | Global numpy RNG seed breaks concurrent use | Use `np.random.default_rng()` per call |
| Phase 1 | Walk-forward backtester | Lookahead bias via unvalidated feature timestamps | Add `valid_at` to every feature; fix datetime stubs first |
| Phase 1 | HMM regime detector | Under-trained on 7 states with limited betting data | Start with 3–4 states; validate before expanding |
| Phase 1 | Alpha formula | Multiplicative boost masks weak edge scores | Add minimum edge floor before multipliers |
| Phase 2 | LangGraph StateGraph | Parallel node state collisions with default reducer | Audit all keys; use `Annotated` reducers |
| Phase 2 | LangGraph conditional edges | Infinite loop on WARN re-route | Add `retry_count` to state; set `recursion_limit` |
| Phase 2 | BettingCopilot | Context window overflow after 5–10 turns | Sliding window + token counting with `tiktoken` |
| Phase 2 | Graph async exceptions | Exceptions swallowed, no Discord response | Wrap `graph.ainvoke()` in try/except; add error node |
| Phase 3 | PM edge scanner | Fires on illiquid markets (spread = fake edge) | Liquidity filter + bid price not mid price |
| Phase 4 | FastAPI streaming | Single-worker blocks under concurrent load | Deploy with multi-worker gunicorn from day one |
| Phase 4 | API user data endpoints | Missing RLS exposes all users' portfolios | Enable RLS before user-scoped routes go live |
| Phase 4 | Expo push notifications | APNs entitlements missing in production build | Configure EAS + test on device before Phase 5 |
| Phase 5 | Calibration engine | Retroactive Platt fitting inflates confidence badges | Rolling calibration; fit on lagged data only |

---

## Sources

**Confidence notes:**
- LangGraph state mutation and recursion limit behavior: HIGH confidence — consistent with LangGraph 0.1/0.2 documented TypedDict reducer requirements and graph compile options
- Monte Carlo numpy thread-safety: HIGH confidence — well-documented numpy global RNG vs Generator behavior
- HMM data requirements: MEDIUM confidence — derived from standard HMM sample complexity literature; specific observation counts are heuristic
- Backtesting lookahead bias patterns: HIGH confidence — canonical ML finance problem, well-documented
- Context window overflow: HIGH confidence — GPT-4o 128k limit is documented; token accumulation in conversation patterns is well-understood
- Expo APNs entitlements: MEDIUM confidence — known Expo Go vs EAS Build divergence; verify against current Expo SDK docs
- Supabase RLS with service role key: HIGH confidence — Supabase documentation explicitly states service role bypasses RLS

Flag for external verification: HMM minimum observation count heuristics, Kalshi/Polymarket current liquidity thresholds, LangGraph latest recursion_limit API (may have changed post-August 2025).
