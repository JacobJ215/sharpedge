# Quant Factory End-to-End Workflow and Prompt Stress Suite

## Purpose
This document explains the current end-to-end quant pipeline as implemented in code today, from first user prompt through strategy creation, backtesting, stress testing, and alerts-first deployment behavior. It also provides a large prompt suite to test coverage, routing, model families, and failure boundaries.

## Current Readiness Snapshot (as of 2026-03-09 code state)
- The platform is operational end-to-end for rule-native and supported model-native flows.
- Build modes are explicit: `rule_native`, `model_native`, `unsupported_now`.
- Clarification and unsupported responses are explicit and structured.
- Multi-candidate generation and selection are enabled.
- Backtesting includes OOS, walk-forward, regime-aware Monte Carlo (HMM latent), cost sensitivity, quality gate, and deployability gate.
- Alerts-first subscription/poll/ack flow is wired for both rule-native and supported model-native strategies.
- Remaining depth gaps still exist in research-to-strategy breadth, broader UX polish, and broader live E2E verification depth.

## Public API Surface
- `POST /api/quant/strategies/create`
- `POST /api/quant/strategies/:id/backtest`
- `GET /api/quant/strategies/:id/runs/:runId`
- `POST /api/quant/strategies/:id/subscribe`
- `POST /api/quant/alerts/poll`
- `POST /api/quant/alerts/ack`

## End-to-End Pipeline (Create Request)
1. Request intake and symbol resolution
- Prompt is received and symbols are resolved from prompt text.
- Request is normalized into a full `QuantStrategyRequest` (asset class, symbols, timeframe, constraints, validation defaults, backtest window).

2. Candidate planning
- One prompt is expanded into multiple deterministic candidate plans.
- Plans vary across:
- `template_refine`
- `strategy_synthesis`
- `template_blend`
- Futures paths can include bounded overlay variants (for example macro/event suppression overlays).

3. Per-candidate workflow graph execution
- Each candidate runs the same workflow graph:
- `intent_normalize`
- `research_context`
- `hypothesis_stage`
- `router`
- `template_match`
- `strategy_design`
- `refactor`
- `code_compile`
- `static_validate`
- `backtest_plan`
- `execute_backtests`
- `robustness`
- `summarize`
- `persist`

4. Router and capability classification
- Router emits:
- `capabilityClass` (`objective_prompt`, `rule_prompt`, `model_prompt`, `research_to_strategy`, `unsupported_now`)
- `buildMode` (`rule_native`, `model_native`, `unsupported_now`)
- `fidelity` (`rule_native`, `model_native`, `unsupported`)
- `supportStatus` (`supported` or `unsupported_now`)
- `generationPath`
- clarification signals and items when needed

5. Strategy construction path
- Rule-native path:
- Template refine, synthesis, or blend into DSL.
- Compile to deterministic module artifact.
- Run static DSL validation.
- Model-native path:
- Build model spec from registry.
- Check executable adapter support.
- Persist model spec + artifact references.
- No silent fallback to rule-native for unsupported model prompts.

6. Backtesting and stress testing
- If executable and `runBacktests=true`, backtest suite runs:
- in-sample and out-of-sample split (70/30 with floor logic)
- walk-forward slices
- regime-aware Monte Carlo via latent HMM model
- cost sensitivity
- overfit diagnostics
- regime breakdown
- benchmark comparison
- stress test summary
- quality gate
- deployability gate

7. Candidate selection
- Service ranks candidates by:
- has backtest report
- deployable gate pass
- quality gate pass
- supported status
- clarification requirement
- OOS Sharpe
- OOS return
- router confidence
- Selected candidate is returned plus full candidate set metadata.

8. Persistence and run tracking
- Strategy version and run rows are persisted.
- Backtest report and hashes are persisted.
- For model-native: model artifact references are persisted.

9. Final response contract
- Response can be:
- executable success
- `clarification_required` style response (`needsClarification=true`)
- `unsupported_now`
- execution error (`success=false` with error payload from route/service path)
- Response includes rich metadata: build mode, family, artifact fields, router fields, quality/stress fields, and candidate set fields.

## Rerun, Run Detail, and Alerts Lifecycle
1. Rerun
- `POST /api/quant/strategies/:id/backtest` reruns backtest for stored strategy version.
- Rule-native rerun uses stored DSL.
- Model-native rerun uses stored model spec and adapter support checks.
- Model-native rerun currently normalizes timeframe to `1D` in service path.

2. Run detail
- `GET /api/quant/strategies/:id/runs/:runId` returns run and attached report metadata.

3. Subscribe
- `POST /api/quant/strategies/:id/subscribe` creates alerts subscription if strategy version is deploy-path eligible.

4. Poll
- `POST /api/quant/alerts/poll` evaluates latest signal transitions for active subscriptions.
- Rule-native uses DSL signal evaluator.
- Model-native uses model-native latest signal evaluator.

5. Ack
- `POST /api/quant/alerts/ack` marks delivered transition to prevent duplicate sends.

## Build Modes and Families
### Rule-native
- Template-based deterministic DSL generation and bounded synthesis.
- Includes general indicator templates and bounded futures/ICT families.

### Model-native (currently executable)
- Native adapter families:
- `linear_regression`
- `hmm_policy`
- `garch`
- `carry_trend`
- `laplacian_diffusion`
- Artifact-backed families:
- `ridge`
- `tcn`
- `gru`
- `lstm`
- `gnn`
- `tgx`

### Notes on carry/diffusion families
- These are now true model-native families in adapter execution path.
- They require cross-asset bars for peer symbol features.
- They are deterministic bounded implementations, not unconstrained research runtimes.

## Backtest and Stress Contract Versions
- Deployability threshold version: `2026-03-07`
- Deployability decision version: `2026-03-08`
- Regime model version: `2026-03-09-hmm-latent-v1`
- Stress contract version: `2026-03-09-stress-contract-v2`

## Gate Semantics (What "Good" Means Here)
- A strategy is considered deploy-ready only if both:
- quantitative thresholds pass (Sharpe, trades, drawdown, stability, positive OOS return)
- quality gate checks pass (section completeness, complexity cap, parameter stability, turnover sanity, data dependency validation)
- This does not guarantee future performance; it enforces minimum robustness standards for alerts-first readiness.

## How to Use This System Operationally
1. Start with prompt and target market/symbol/timeframe.
2. Submit create request and inspect:
- `supportStatus`
- `buildMode`
- `needsClarification`
- `candidateCount` and `candidates[]`
3. If clarification requested, answer directly and rerun create.
4. If unsupported, use nearest supported path/template hints and rerun.
5. For executable outputs, compare candidate OOS and gate quality; avoid selecting by return-only.
6. Rerun with tighter constraints and realistic costs.
7. Subscribe only when gate and quality are both clean.
8. Monitor transitions through poll/ack flow.

## Prompt Stress Suite
Use these prompts as-is or with symbol/timeframe variants. They are grouped to test routing and execution behavior.

### A) Rule-native baseline prompts
1. Build an SMA crossover swing strategy for AAPL with 1D bars and 1% risk per trade.
2. Build a momentum breakout strategy for NVDA using volume confirmation and ATR exits.
3. Build an RSI mean reversion strategy for SPY with long-only entries below RSI 30.
4. Build a z-score value reversion strategy for MSFT with trend filter.
5. Build a time-series momentum strategy for QQQ with a 63-bar momentum filter.
6. Build a volatility expansion breakout strategy for TSLA with strict drawdown cap.
7. Build a mean-reversion strategy on ETH/USD using RSI and VWAP context.
8. Build a daily long/short strategy for BTC/USD using EMA trend and volatility filter.
9. Build a conservative trend-following strategy for AMZN with max 15% position size.
10. Build a both-sides strategy for META with commission 2 bps and slippage 8 bps.
11. Build a long-only strategy for AAPL that limits max hold to 20 bars.
12. Build a risk-balanced equity strategy for NFLX with minimum 40 trades.

### B) Template blend and synthesis prompts
1. Blend momentum breakout and RSI mean reversion for AAPL.
2. Blend volatility expansion breakout and SMA crossover for SPY.
3. Combine trend-following with mean-reversion fallback on NVDA.
4. Build a custom synthesis strategy for TSLA with regime filter and event suppression.
5. Build from scratch a bounded strategy for QQQ using volatility targeting and dynamic position sizing.
6. Create a hybrid strategy for BTC/USD that blends momentum and value reversion motifs.
7. Synthesize a strategy for ETH/USD with trend confirmation and volatility-adaptive exits.
8. Blend two templates for MSFT and keep complexity under 12 total rules.
9. Build a custom pairs-aware synthesis strategy for AAPL vs QQQ.
10. Build a strategy synthesis for SPY that avoids entries during macro risk windows.
11. Blend kill-zone timing with volatility breakout logic for ES futures.
12. Build a synthesis candidate for NQ futures that prioritizes session discipline.

### C) Model-native prompts (family coverage)
1. Build a linear regression model for AAPL next-bar return with a neutral dead band.
2. Build a ridge regression model for AAPL using 64 by 12 feature window and volatility-aware sizing.
3. Build a TCN model for AAPL with 64x12 feature window, next-bar probability output, and dead-band execution.
4. Take a 64x12 feature window and run it through a causal temporal convolutional network, turn that embedding into next-bar probability, then apply a moving average dead-band filter.
5. Build a GRU model for AAPL next-bar probability with long/short/flat thresholding.
6. Build an LSTM model for AAPL with probability edge sizing and 0.45 to 0.55 neutral band.
7. Build a GNN model for AAPL, MSFT, NVDA cross-asset graph scoring.
8. Build a TGX temporal graph strategy for AAPL, QQQ, SPY.
9. Build an HMM conditioned policy for AAPL that gates entries by latent regime probabilities.
10. Build a GARCH volatility model for AAPL and use inverse-volatility exposure scaling.
11. Build a carry trend model for AAPL using SPY and QQQ as peer carry proxies.
12. Build a laplacian diffusion model for AAPL with SPY, QQQ, IWM neighborhood.
13. Build a linear regression model for BTC/USD with return, volatility, and volume z-score features.
14. Build a ridge model for ETH/USD and apply probability dead-band before execution.
15. Build a TCN for BTC/USD with next-bar direction probability and capped exposure.
16. Build a GRU for MSFT with walk-forward calibration and dead-band thresholds.
17. Build an LSTM for NVDA with explicit prediction target next-bar probability.
18. Build a GNN for energy symbols XOM, CVX, CL proxy to generate cross-sectional signal.
19. Build TGX for tech basket AAPL, MSFT, NVDA, AMD with temporal graph score.
20. Build a carry trend family model for CL using ES and DXY proxy peers.
21. Build laplacian diffusion for ES using NQ and VIX proxy graph features.
22. Build HMM policy for SPY with downstream trend policy and state-conditioned risk scaling.
23. Build GARCH for BTC/USD and use volatility gating to suppress entries.
24. Build linear regression for QQQ with explicit 5-bar horizon target.
25. Build ridge for SPY with feature schema ret_1, ret_5, atr_14, volume_ratio.

### D) Research-to-strategy prompts
1. Use macro event research and news sentiment to build an executable NQ futures strategy.
2. Convert this thesis into a tradable strategy: post-CPI volatility expansion with intraday trend continuation.
3. Build a strategy from recent earnings sentiment for AAPL and MSFT with risk suppression around event windows.
4. Translate internet research on momentum crashes into a bounded defensive strategy for QQQ.
5. Turn a macro thesis on declining real yields into a strategy for gold proxies.
6. Use event-risk context and sentiment to build a strategy for CL futures.
7. Build a research-driven strategy for BTC/USD around ETF flow sentiment.
8. Convert a mean-reversion thesis from recent market commentary into a bounded SPY strategy.
9. Use research and macro calendar signals to build a kill-zone futures strategy for ES.
10. Build a strategy from a thesis: volatility regime shifts are rising, avoid chop and trade expansion breaks.
11. Build from research: risk-on rotation in semis, generate a strategy for NVDA and AMD.
12. Use thesis-driven research-to-strategy for NQ and add nearest executable path if needed.

### E) Objective/clarification prompts (should ask questions first)
1. Build me something that beats the S&P 500.
2. Make the best strategy possible for the next decade.
3. Outperform everything with low drawdown.
4. Find alpha anywhere and deploy it.
5. Build a benchmark-crushing strategy with no constraints.
6. Create the highest Sharpe strategy you can.
7. Maximize returns but keep risk low.
8. Build a fully automated strategy that always wins.
9. Build an institutional-grade strategy for all markets.
10. Create one strategy that works for every symbol and timeframe.
11. Build a strategy with maximum profit and minimal losses.
12. Design the optimal portfolio strategy with no further input.

### F) Stress and robustness prompts
1. Build AAPL strategy with slippage 20 bps and commission 5 bps and rerun backtests.
2. Build NVDA strategy with max drawdown 12% and minimum 80 trades.
3. Build BTC/USD strategy with both-side trading and max hold 10 bars.
4. Build SPY strategy and require Monte Carlo, walk-forward, and cost sensitivity.
5. Build QQQ strategy with conservative profile and strict stability requirements.
6. Build NQ futures strategy with event-risk suppression tags and intraday timeframe.
7. Build CL futures strategy with low turnover and strict session exits.
8. Build ETH/USD strategy with max position size 10% and high cost assumptions.
9. Build a strategy for AAPL and rerun with a narrower backtest window.
10. Build model-native HMM policy for SPY then rerun with tighter drawdown threshold.
11. Build GARCH for AAPL then rerun with higher minTrades and lower maxDrawdown.
12. Build carry trend for AAPL using SPY/QQQ and test with higher slippage.
13. Build laplacian diffusion for AAPL and test sensitivity to cost multipliers.
14. Build a rule-native blend and verify quality gate passes before subscribe.
15. Build a strategy and require out-of-sample positive return and stability > baseline.

### G) Unsupported-boundary prompts (should return `unsupported_now`)
1. Build an options market-making gamma scalping strategy on SPY.
2. Build an order-book microstructure HFT strategy for NQ.
3. Build a latency arbitrage strategy across exchanges.
4. Build a delta-hedged volatility surface strategy for SPX options.
5. Build a reinforcement learning execution agent for futures order flow.
6. Build a transformer model for tick-level prediction and execution.
7. Build a cross-exchange market making bot for BTC perpetuals.
8. Build an options dispersion strategy using full implied vol surface.
9. Build a high-frequency queue-position alpha model.
10. Build a smart order router execution algo with millisecond scheduling.
11. Build a stat-arb market-neutral options book with dynamic delta hedging.
12. Build a microstructure strategy from full depth L3 order book events.

### H) Edge-case parsing/routing prompts
1. TCN 64x12 next bar prob dead band for AAPL.
2. causal temporal convolutional network 64 by 12 on NVDA, next bar probability, threshold around 0.5.
3. hmm policy plus trend policy for SPY no proxying.
4. garch vol gate for BTCUSD with inverse-vol sizing.
5. blend ORB and VWAP mean reversion for NQ and ES.
6. use internet research and macro and sentiment and build from thesis for CL.
7. beat spy.
8. hybrid carry diffusion graph-ish setup for AAPL vs QQQ vs SPY.
9. build only if model-native real, no fallback.
10. if unsupported show nearest path and ask clarifying questions.
11. create two candidate variants for TSLA and pick best OOS sharpe.
12. objective prompt: outperform QQQ with controlled turnover, ask what else you need.

### I) High-performance iteration prompts
1. Generate 3 candidates for AAPL trend-following and rank by OOS Sharpe then stability.
2. Generate 3 candidates for SPY mean-reversion and rank by deployability gate first.
3. Create two model-native candidates (ridge and linear regression) for MSFT and compare OOS + drawdown.
4. Build a TCN candidate and a rule-native blend candidate for NVDA and compare quality gate outcomes.
5. Build carry_trend and laplacian_diffusion candidates for AAPL with SPY/QQQ peers and compare.
6. Build an HMM policy and GARCH candidate for SPY and compare stress failure modes.
7. Build a volatility expansion rule-native strategy and tighten constraints until gate passes.
8. Build NQ futures candidates emphasizing session discipline and evaluate walk-forward stability.
9. Build CL futures candidates with inventory suppression overlay and compare cost sensitivity.
10. Build BTC/USD candidates for trend and mean-reversion motifs and pick robust winner.
11. Build three candidates with identical symbols but different timeframes and compare turnover sanity.
12. Build strategy, rerun with stricter slippage, rerun with stricter drawdown, keep only consistent candidate.

## Practical Testing Checklist for Each Prompt
1. Confirm `capabilityClass`, `buildMode`, `supportStatus`.
2. Confirm `needsClarification` behavior is honest.
3. Confirm candidate set is returned and selected candidate is sensible.
4. For executable candidates, compare:
- OOS Sharpe
- OOS return
- max drawdown
- trade count
- walk-forward stability
- Monte Carlo downside
- benchmark excess return
- quality gate pass/fail reasons
- deployability gate pass/fail reasons
5. Confirm no silent downgrade from model-native requests.
6. Confirm unsupported prompts return nearest supported path guidance.
7. Subscribe only if gate + quality are both clean and failure modes are acceptable.

## Bottom Line
The system is now a real capability-routed quant factory with explicit rule-native/model-native separation, executable adapters across key model families, and a materially stronger validation stack. Use the prompt suite above to pressure routing honesty, execution fidelity, and robustness before trusting any strategy in alerts-first operation.
