# SharpEdge Review Phase 1

## Purpose

Define the operating model for using SharpEdge as a **paper-trading alpha lab** until strategies are proven worthy of live review.

This phase is for:
- monitoring
- reviewing
- documenting
- improvement planning
- promotion-readiness assessment

This phase is **not** for:
- autonomous live trading
- autonomous promotion
- silent codebase changes
- uncontrolled strategy expansion

---

## Operating mode

**Paper only**

All SharpEdge strategies and swarm workflows should be treated as:
- experimental capital engines
- paper-monitored systems
- promotion candidates only after evidence

---

## Core objective

Continuously answer:

**Which SharpEdge strategies are stable enough to deserve trust, and which are not?**

---

## Review scope

Applies to:
- prediction market strategies
- sports betting strategies
- arb / dislocation workflows
- swarm-run paper strategies
- strategy families already present in SharpEdge

---

## Phase 1 agent roles

### 1. Paper Monitoring Agent
**Purpose**
Monitor current paper runs and summarize health/performance.

**Responsibilities**
- collect run summaries
- track strategy-by-strategy status
- detect anomalies
- surface failures and suspicious behavior

**Outputs**
- monitoring summary
- strategy status table
- anomalies / alerts

---

### 2. Strategy Review Agent
**Purpose**
Evaluate whether paper strategies show real signal quality or misleading noise.

**Responsibilities**
- review individual strategy-family outcomes
- assess consistency and edge quality
- compare healthy vs unstable strategies
- identify weak sample-size situations

**Outputs**
- strategy review memo
- classification:
  - healthy
  - promising
  - unstable
  - broken

---

### 3. Risk Review Agent
**Purpose**
Review paper risk behavior and identify promotion blockers.

**Responsibilities**
- inspect drawdown
- inspect exposure concentration
- inspect streak behavior
- inspect circuit breaker events
- inspect category/venue concentration

**Outputs**
- risk memo
- blocker list
- promotion constraints

---

### 4. Improvement Memo Agent
**Purpose**
Document what should improve before live consideration.

**Responsibilities**
- identify weak points
- recommend fixes or investigation areas
- separate urgent fixes from later ideas
- avoid code changes unless explicitly requested elsewhere

**Outputs**
- prioritized improvement memo
- do now / do later / ignore list

---

### 5. Promotion Review Agent
**Purpose**
Prepare final review before any live-promotion discussion.

**Responsibilities**
- gather monitoring evidence
- gather risk evidence
- gather strategy-review evidence
- produce readiness recommendation

**Outputs**
- promotion-readiness packet
- recommendation:
  - not ready
  - needs more paper time
  - ready for human review

---

## Status labels

Use these simple labels for strategies or strategy families:

- `paper_running`
- `paper_promising`
- `paper_blocked`
- `paper_unstable`
- `promotion_candidate`
- `not_ready`

Optional:
- `paused`
- `under_review`

---

## Monitoring workflow

### Stage 1 — Run
Run the SharpEdge swarm and paper strategies as currently designed.

### Stage 2 — Monitor
Collect:
- paper PnL
- win rate
- drawdown
- exposure
- category/venue concentration
- failed jobs
- API/data issues
- suspicious execution behavior

### Stage 3 — Review
For each strategy/family:
- is edge positive?
- is performance stable?
- is sample size meaningful?
- are losses explainable?
- are there operational issues?

### Stage 4 — Improve or document
If weak:
- document improvement path
- do not silently promote
- do not assume paper noise is edge

### Stage 5 — Promotion review
Only after enough evidence:
- compile review packet
- request human decision

---

## Required review packet

Before any promotion discussion, prepare a packet with:

### 1. Performance summary
- total paper PnL
- win rate
- strategy-family contribution
- venue/category breakdown
- risk-adjusted notes if available

### 2. Risk summary
- max drawdown
- exposure concentration
- streak behavior
- breaker/circuit events
- risk concerns

### 3. Operations summary
- uptime / run stability
- data/API issues
- failed jobs
- execution inconsistencies
- notable incidents

### 4. Improvement summary
- top weaknesses
- required fixes
- optional enhancements
- unresolved uncertainties

### 5. Recommendation
One of:
- `not_ready`
- `needs_more_paper_time`
- `ready_for_human_review`

---

## Promotion rules

No live promotion unless all are true:
- sufficient paper sample size
- acceptable drawdown behavior
- acceptable operational stability
- no unresolved critical issues
- risk review completed
- promotion packet completed
- explicit human approval

---

## Weekly review cadence

Recommended minimum cadence:

### Regular / daily-ish
- monitoring summary
- anomaly summary
- top/bottom strategy snapshot

### Weekly
- strategy-family review
- risk review
- improvement memo
- updated status labels

### Before any promotion
- full review packet
- explicit recommendation
- human approval gate

---

## Phase 1 operating rule

SharpEdge in this phase is a **paper alpha lab**, not a live autonomous trader.

The burden of proof is:
- stability
- evidence
- discipline
- inspectability

Not excitement.
