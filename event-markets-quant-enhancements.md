# Event Markets Quant Enhancement Proposal

## Purpose

This document proposes a concrete enhancement program for an existing separate application that will expand into:

- Kalshi
- Polymarket
- sportsbook and odds-based markets

This is not a FinnAI implementation plan.

It assumes:

- the target application already exists
- the target application's architecture is different from FinnAI
- FinnAI code will not be reused directly
- only FinnAI's quantitative practices, model-governance discipline, and system-design ideas will be transferred conceptually

## Strategic Position

The product should be treated as a probability, market-microstructure, and risk-allocation system, not as a port of stock or futures strategies.

The first objective is not "automate betting." The first objective is:

1. build a reliable market-state and pricing layer
2. measure edge after costs, fees, and execution constraints
3. calibrate probabilities and validate them out of sample
4. add risk allocation and execution only after the research loop is trustworthy

## FinnQuant Practices To Transfer Conceptually

The target application should inherit these disciplines from FinnQuant in concept, not by module reuse:

- EV-first decisioning rather than heuristic confidence-only scoring
- explicit cost modeling for fees, spread, slippage, and liquidity
- out-of-sample, walk-forward, and ablation-driven research
- calibration of probabilities before capital allocation
- deterministic replay for research, incident review, and settlement verification
- thin transport layers with heavy modeling isolated behind stable contracts
- explicit risk budgets, exposure limits, and promotion gates before production rollout

## Product Scope

The enhancement program should support three venue families with one internal quant language:

- Kalshi: binary event contracts with exchange-style order books and venue APIs
- Polymarket: event markets with public market discovery, CLOB data, and venue-specific auth and settlement mechanics
- Sportsbooks: odds markets across books, with line-shopping and fair-probability estimation as the initial priority

The unifying abstraction should be:

- a market
- a set of mutually exclusive outcomes
- a quoted price or odds representation
- fees and venue rules
- time-to-resolution
- settlement state
- liquidity and execution state

## What Not To Do

- Do not import FinnAI domain modules into the target application.
- Do not force the target app to adopt FinnAI's folder structure.
- Do not begin with execution automation for every venue.
- Do not model these markets as if they were OHLCV-only bar series.
- Do not skip calibration, replay, or settlement accounting because the product "looks quantitative enough."

## Proposed Bounded Contexts

### 1. Market Catalog And Lifecycle

Responsibilities:

- ingest venue market metadata
- normalize event, market, and outcome identities
- track open, suspended, resumed, resolved, and cancelled states
- define canonical time fields such as `listed_at`, `closes_at`, `resolves_at`, and `settles_at`

Core entities:

- `Event`
- `Market`
- `Outcome`
- `MarketLifecycleState`
- `VenueContractRef`

### 2. Venue Connectivity

Responsibilities:

- connect to venue REST and streaming APIs
- translate venue payloads into canonical snapshots
- expose venue capabilities, rate limits, fees, and auth requirements
- separate read-only data access from execution-capable access

Core entities:

- `VenueAdapter`
- `VenueCapability`
- `VenueAuthContext`
- `VenueFeeSchedule`
- `VenueRateLimitPolicy`

### 3. Market Data And Quote Normalization

Responsibilities:

- normalize order books, trades, spreads, midpoints, and odds formats
- normalize American, decimal, implied-probability, and share-price views
- maintain historical snapshots for replay and research
- produce canonical market-state packets

Core entities:

- `CanonicalQuote`
- `CanonicalOrderBook`
- `CanonicalTrade`
- `CanonicalOddsSnapshot`
- `MarketStatePacket`

### 4. Probability And Pricing

Responsibilities:

- derive fair probabilities from venue quotes and external models
- remove vig or hold where applicable
- normalize binary and multi-outcome books
- produce edge estimates after fees and execution assumptions

Core entities:

- `FairProbability`
- `VenueImpliedProbability`
- `NoVigBook`
- `PricingDecision`
- `EdgeEstimate`

### 5. Research And Feature Engineering

Responsibilities:

- build datasets by venue, market family, and event type
- maintain time-correct train, validation, and test splits
- run walk-forward, ablation, and sensitivity workflows
- generate reusable research artifacts and model reports

Core entities:

- `DatasetVersion`
- `FeatureView`
- `ResearchRun`
- `WalkForwardSlice`
- `PromotionReport`

### 6. Risk, Exposure, And Portfolio Construction

Responsibilities:

- manage bankroll or inventory budgets
- aggregate exposure across correlated outcomes and venues
- cap risk by venue, event, sport, and market regime
- explain why exposure is allowed, reduced, or blocked

Core entities:

- `ExposureBook`
- `RiskLimit`
- `CorrelationBucket`
- `AllocationDecision`
- `VenueInventory`

### 7. Execution And Order Strategy

Responsibilities:

- place, amend, cancel, and simulate orders where allowed
- estimate fills under queue, depth, spread, and latency assumptions
- support both passive quoting and aggressive taker logic
- keep execution policy separate from fair-pricing logic

Core entities:

- `OrderIntent`
- `ExecutionPlan`
- `FillEstimate`
- `OrderLifecycle`
- `PassiveQuotePolicy`

### 8. Settlement And Ledger

Responsibilities:

- record fills, realized PnL, fees, rebates, and settlement outcomes
- support deterministic replay from order and market events
- reconcile venue statements against internal accounting
- support idempotent resolution and payout workflows

Core entities:

- `LedgerEntry`
- `PositionLot`
- `SettlementEvent`
- `PayoutRecord`
- `ReconciliationReport`

### 9. API, Operator Tools, And Product Surfaces

Responsibilities:

- expose research summaries, market monitors, and decision reports
- provide human-review workflows before promotions or execution changes
- separate operator actions from public or customer-facing APIs

Core entities:

- `ResearchDashboard`
- `PromotionDecision`
- `ReviewQueue`
- `Alert`
- `OperatorAction`

## Venue Adapter Strategy

The implementation should define one canonical adapter contract and then implement venue-specific modules behind it.

### Canonical Adapter Contract

Each venue adapter should expose at least:

- `listMarkets()`
- `getMarketDetails()`
- `getOrderBook()`
- `getTrades()`
- `getHistoricalSnapshots()`
- `getFeesAndLimits()`
- `getSettlementState()`
- `placeOrder()` and `cancelOrder()` only where execution is approved

Each adapter should also declare capabilities such as:

- `read_only`
- `streaming_quotes`
- `streaming_orderbook`
- `execution_supported`
- `wallet_or_key_auth`
- `maker_rewards`
- `settlement_feed`

### Kalshi Adapter

Initial responsibilities:

- market catalog ingestion
- event and contract normalization
- order book and trade snapshot history
- fee-aware EV calculation
- settlement-state ingestion

Research priority:

- binary contract fair-probability estimation
- queue-aware fill modeling
- event-time and news-jump sensitivity

### Polymarket Adapter

Initial responsibilities:

- market discovery and outcome mapping
- CLOB market data ingestion
- midpoint, spread, and depth normalization
- wallet or CLOB auth abstraction
- settlement and reward metadata ingestion

Research priority:

- reward-aware passive quoting
- cross-venue dislocation versus Kalshi or sportsbook consensus
- liquidity and spread dynamics around event windows

### Sportsbook Adapter Family

Initial responsibilities:

- read-only odds ingestion first
- line shopping across books
- no-vig price normalization
- odds history and closing-line archive
- market availability and suspension tracking

Research priority:

- stale-line detection
- closing-line-value benchmarking
- market-family calibration by league, market type, and time-to-start

Execution note:

- sportsbook execution should be treated as a later-stage capability because operational, legal, and account constraints are materially different from exchange-style venues

## Core Quant Models

### 1. Fair Probability Engine

Purpose:

- map venue quotes to fair probabilities after hold, fees, and known frictions

Methods:

- binary normalization
- multi-outcome no-vig normalization
- constrained probability reconciliation across related markets
- consensus blending across venues

### 2. Calibration Stack

Purpose:

- ensure predicted probabilities are decision-usable, not just rank-ordered

Methods:

- Platt scaling
- isotonic calibration
- beta calibration where sample behavior warrants it
- calibration by venue, sport, market family, and time-to-resolution

### 3. Market Microstructure Model

Purpose:

- convert visible prices into fill-aware and queue-aware actionable edge

Methods:

- spread and depth modeling
- fill-hazard estimation
- latency sensitivity
- passive-versus-aggressive execution comparison

### 4. Cross-Venue Dislocation Model

Purpose:

- identify when one venue materially differs from fair value or peer consensus

Methods:

- venue spread decomposition
- stale quote detection
- consensus deviation scoring
- paired or basket exposure checks across related outcomes

### 5. Event-State And Time-To-Resolution Model

Purpose:

- model how signal quality changes as events approach lock, settlement, or major information releases

Methods:

- hazard-style event-time features
- regime segmentation by market phase
- pre-event versus in-event versus post-event state classification

### 6. Allocation And Exposure Model

Purpose:

- translate edge into controlled sizing

Methods:

- fractional Kelly or capped Kelly variants
- drawdown-aware throttles
- venue concentration caps
- correlated-outcome netting

### 7. Settlement Replay And Attribution

Purpose:

- replay exactly how quoted edge became realized PnL or loss

Methods:

- event-sourced replay
- pre-trade versus post-trade attribution
- fee and rebate decomposition
- calibration drift and execution drift decomposition

## Model-Governance Requirements

No model should move into production-facing decisioning without:

- time-correct train, validation, and test splits
- walk-forward evidence
- ablation results for major feature families
- calibration reports
- cost and fee sensitivity analysis
- venue-specific drift monitoring
- deterministic replay of representative scenarios

Recommended promotion gates:

- calibration error threshold
- minimum post-cost edge threshold
- maximum drawdown or exposure violation threshold
- minimum live-paper stability period before capitalized deployment

## Recommended System Shape

Because the target application already exists and has its own architecture, this proposal is intentionally shape-agnostic.

Use these mapping rules instead of copying FinnAI structure:

- bounded contexts become modules or services in the target app's native architecture
- heavy modeling can live in Python or another modeling runtime behind stable contracts
- read models and operator dashboards should follow the target app's existing UI and API conventions
- venue adapters should land behind ports or interfaces already used by the target app where possible

The minimum architectural requirement is not a specific framework. It is the separation of:

- market normalization
- pricing
- execution
- settlement
- research and model governance

## Research Roadmap

### Phase 0. Discovery And Domain Contracts

Deliverables:

- canonical market, outcome, quote, and settlement schemas
- venue capability matrix
- legal and operational constraints memo by venue family
- initial metric definitions for edge, calibration, fill quality, and realized attribution

Exit criteria:

- the team agrees on canonical domain objects and data contracts

### Phase 1. Read-Only Venue Data Foundation

Deliverables:

- Kalshi market and order book ingestion
- Polymarket market and CLOB ingestion
- sportsbook odds and history ingestion
- historical archive with replayable snapshots

Exit criteria:

- the platform can reconstruct market state for selected test windows across all three venue families

### Phase 2. Fair Pricing And Calibration

Deliverables:

- no-vig and fee-aware pricing library
- venue-implied probability normalization
- first calibration reports by venue and market family
- baseline fair-value dashboard

Exit criteria:

- the team can compare raw venue pricing versus calibrated fair pricing in a repeatable way

### Phase 3. Simulation And Microstructure

Deliverables:

- fill simulator for exchange-style venues
- line-movement and stale-quote simulation for sportsbooks
- post-cost edge evaluation
- scenario replay around major event windows

Exit criteria:

- strategy ideas can be evaluated after realistic execution assumptions

### Phase 4. Exposure And Allocation

Deliverables:

- bankroll and inventory model
- correlation buckets across related outcomes
- venue and event-level concentration limits
- operator-readable exposure explanations

Exit criteria:

- the system can explain why capital is allocated or blocked

### Phase 5. Controlled Productionization

Deliverables:

- alerting and operator review workflows
- paper-trading or shadow-decision mode
- venue-specific execution for approved surfaces
- settlement and reconciliation reporting

Exit criteria:

- the system can run safely in shadow mode with deterministic replay and post-trade review

## Venue-Specific Research Priorities

### Kalshi

- binary market calibration by category and time-to-close
- spread and depth dynamics near information shocks
- passive quote viability after fees
- fill-probability estimation from order book state

### Polymarket

- midpoint quality and reward-aware quoting
- fragmentation and cross-market consistency
- liquidity dynamics during event clustering
- settlement and reward attribution quality

### Sportsbooks

- no-vig consensus construction
- closing-line-value benchmarking
- stale-line detection
- market family calibration by league, sport, and bet type

## Handoff Instructions For The Next Agent

The next agent working in the target application should produce, in order:

1. a canonical domain model for markets, outcomes, quotes, fees, and settlement
2. an adapter interface and capability matrix for Kalshi, Polymarket, and sportsbooks
3. a research data model and replay format
4. a pricing-and-calibration specification
5. an exposure and settlement specification
6. a phased implementation plan aligned to the target app's existing architecture

The next agent should not begin by building UI or execution automation. It should begin by locking the domain contracts and the research loop.