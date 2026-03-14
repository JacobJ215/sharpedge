# Phase 3: Prediction Market Intelligence - Research

**Researched:** 2026-03-13
**Domain:** Prediction market edge scanning, rule-based regime classification, portfolio correlation detection
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Edge delivery channel:**
- PM edges post to the same Discord channel as sports value plays, with a clear PM label/prefix to distinguish them
- PM scanning runs in the same job as value_scanner_job.py — no separate pm_scanner_job.py
- All alerts (PM and sports) ranked by unified composite alpha score — highest alpha posts first regardless of type
- PM edges go through the same 9-node LangGraph validate_setup gate (PASS/WARN/REJECT) before posting — no separate quality check

**Liquidity threshold:**
- Primary filter: minimum 24h volume in $ using the existing `UnifiedOutcome.volume_24h` field
- Per-platform thresholds: Kalshi and Polymarket have different typical volumes — configure separately
- Default minimum: $500 for both platforms as starting point (tunable per-platform)
- Markets below the liquidity floor are silently skipped — filtered count goes to debug log only, not Discord

**PM regime behavior:**
- Regime adjusts edge threshold dynamically — Pre-Resolution gets stricter (e.g. 5%), Discovery gets looser (e.g. 2%), 3% as the neutral baseline
- Classification: rule-based classifier using 4 signals (same pattern as Phase 1 sports regime — deterministic, no ML)
  - Time-to-resolution: Markets closing in <24h → Pre-Resolution
  - Price stability: Low recent variance → Consensus; high variance → Sharp Disagreement or News Catalyst
  - Volume trend: Sudden spike → News Catalyst; steady accumulation → Consensus
  - Market age: Markets <48h old → Discovery
- Regime applied post-scan only — all markets above liquidity floor are scanned; regime adjusts threshold and alpha score after detection (no pre-scan filtering)

**Correlation detection scope:**
- Active positions sourced from user's logged bets in Supabase (existing bet tracker)
- Correlation determined by team/entity matching — two positions are correlated if they share the same team, player, or event entity (string/entity match on market description)
- When an alert would push correlation >0.6: post a Discord warning embed before the correlated alert — user sees the risk before the play
- Correlated alerts post with warning, not blocked — no queue/acknowledge flow

### Claude's Discretion
- Exact threshold multipliers per regime state (e.g. Pre-Resolution 5% vs Discovery 2%)
- Entity extraction approach for team/player matching
- Exact embed format for PM alerts vs sports alerts

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PM-01 | System scans all active Kalshi markets, computes model probability vs market probability, and surfaces edges >3% with alpha score | KalshiClient.get_markets() already works; `mid_price` gives market prob; edge = model_prob - mid_price; alpha via existing compose_alpha() |
| PM-02 | System scans Polymarket markets with same edge detection as Kalshi | PolymarketClient.get_markets() already works; yes_price gives market prob; same edge/alpha pipeline as Kalshi |
| PM-03 | System classifies prediction market regime (Discovery, Consensus, News Catalyst, Pre-Resolution, Sharp Disagreement) and adjusts edge threshold accordingly | Mirror regime.py pattern — 5-state rule-based classifier using 4 signals; threshold multiplier table per state |
| PM-04 | System detects correlated positions across sportsbook bets and prediction markets and warns user when portfolio correlation coefficient exceeds 0.6 | Read active bets from Supabase `bets` table; entity match on market description; compute correlation coefficient; Discord warning embed before correlated alert |
</phase_requirements>

---

## Summary

Phase 3 extends the existing value scanning pipeline to prediction markets. The core data infrastructure is already in place: `KalshiClient` and `PolymarketClient` can fetch live markets, `UnifiedOutcome.volume_24h` provides the liquidity field, `compose_alpha()` and `enrich_with_alpha()` provide alpha scoring, and `value_scanner_job.py` is the correct extension point. The architectural decisions are locked: no new jobs, no new bot channels, same alpha-ranking pipeline.

The two new modules to build are `pm_regime.py` (a 5-state rule-based PM regime classifier mirroring `regime.py`) and `pm_edge_scanner.py` (the PM scanning function that mirrors the sports value scanner but operates on PM market data). A third concern is correlation detection: the `bets` table already stores active sportsbook bets; Phase 3 needs to read those bets, extract entity tokens from market descriptions, compare against PM market entities, and compute a simple correlation coefficient before dispatching an alert.

The existing `prediction_market_scanner.py` job does arbitrage detection (cross-platform arb). Phase 3 is a different problem: single-platform edge detection (model prob vs market prob). These are complementary, not duplicate concerns. The existing arbitrage scanner should not be confused with the new edge scanner.

**Primary recommendation:** Create `pm_edge_scanner.py` in `packages/analytics/src/sharpedge_analytics/`, create `pm_regime.py` in the same package, then extend `value_scanner_job.py` to call the new PM scanner after the sports scan. Split `prediction_markets.py` (614 lines, over 500-line limit) as a prerequisite.

---

## Standard Stack

### Core (all already in the project — no new installations)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | >=0.27 | Async HTTP for Kalshi/Polymarket API calls | Already used in both API clients |
| supabase-py | in workspace | Read active bets for correlation detection | Already used project-wide |
| langchain-core | in workspace | validate_setup gate route for PM edges | Already used in LangGraph graph |
| pytest | >=8.0 | Unit tests (pyproject.toml dev dep) | Established test framework |
| pytest-asyncio | >=0.24 | Async test support | Already in dev deps |
| pytest-mock | >=3.14 | Mock API calls in tests | Already in dev deps |

### No new packages required
All required capabilities exist. Do not add dependencies for Phase 3.

---

## Architecture Patterns

### Recommended Project Structure

New files to create:

```
packages/analytics/src/sharpedge_analytics/
├── pm_edge_scanner.py       # PM-01, PM-02: single-platform edge detection
├── pm_regime.py             # PM-03: 5-state PM regime classifier
└── prediction_markets/      # Split from prediction_markets.py (614 lines)
    ├── __init__.py          # Re-export everything — backward compat
    ├── fees.py              # Platform fee structures
    ├── types.py             # MarketOutcome, CanonicalEvent, etc.
    └── arbitrage.py         # Arb detection functions

apps/bot/src/sharpedge_bot/jobs/
└── value_scanner_job.py     # Extend (do not replace) — add PM scan section

packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/
└── tools.py                 # Replace stub get_prediction_market_edge with real impl

tests/unit/analytics/
├── test_pm_edge_scanner.py  # PM-01, PM-02 unit tests
└── test_pm_regime.py        # PM-03 unit tests

tests/unit/
└── test_correlation.py      # PM-04 unit tests
```

### Pattern 1: PM Edge Scanner (mirrors value scanner)

**What:** Functional module that accepts a list of PM markets (with model probabilities), applies liquidity filter, computes edge as `model_prob - market_prob`, enriches with alpha, and returns ranked `PMEdge` list.

**When to use:** Called from `value_scanner_job.py` after the sports scan loop.

```python
# packages/analytics/src/sharpedge_analytics/pm_edge_scanner.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class PMEdge:
    platform: str           # "kalshi" | "polymarket"
    market_id: str
    market_title: str
    market_prob: float      # mid_price or yes_price (0-1)
    model_prob: float       # our estimate (0-1)
    edge_pct: float         # (model_prob - market_prob) * 100
    volume_24h: float       # USD
    close_time: datetime | None
    alpha_score: float | None
    alpha_badge: str | None  # "PREMIUM" | "HIGH" | "MEDIUM" | "SPECULATIVE"
    regime: str | None
    regime_threshold: float  # adjusted threshold for this regime

def scan_pm_edges(
    markets: list,           # KalshiMarket or PolymarketMarket objects
    model_probs: dict[str, float],  # market_id -> model probability
    platform: str,
    volume_floor: float = 500.0,
    base_threshold_pct: float = 3.0,
) -> list[PMEdge]:
    """Scan markets for model-vs-market edges above threshold."""
    ...
```

### Pattern 2: PM Regime Classifier (mirrors regime.py)

**What:** Rule-based 5-state classifier. 4 signals, priority-ordered rules, deterministic output. Returns `PMRegimeClassification` with `regime`, `confidence`, `edge_threshold_pct`.

**Five states (locked in CONTEXT.md):**
- `DISCOVERY` — market age <48h → looser threshold (2%)
- `CONSENSUS` — low price variance + steady volume → neutral threshold (3%)
- `NEWS_CATALYST` — sudden volume spike → neutral threshold (3%), flag for manual review
- `PRE_RESOLUTION` — close_time <24h → stricter threshold (5%)
- `SHARP_DISAGREEMENT` — high price variance, no volume spike → neutral threshold (3%)

**Rule priority order (Claude's discretion — recommended):**
1. PRE_RESOLUTION: `hours_to_close < 24`
2. DISCOVERY: `hours_since_created < 48`
3. NEWS_CATALYST: `volume_spike_ratio > 3.0` (24h vol / 7d avg vol)
4. CONSENSUS: `price_variance_7d < 0.02` AND `volume_trend == "steady"`
5. SHARP_DISAGREEMENT: default fallback

```python
# packages/analytics/src/sharpedge_analytics/pm_regime.py
from dataclasses import dataclass
from enum import Enum

class PMRegimeState(str, Enum):
    DISCOVERY = "DISCOVERY"
    CONSENSUS = "CONSENSUS"
    NEWS_CATALYST = "NEWS_CATALYST"
    PRE_RESOLUTION = "PRE_RESOLUTION"
    SHARP_DISAGREEMENT = "SHARP_DISAGREEMENT"

PM_REGIME_THRESHOLDS: dict[PMRegimeState, float] = {
    PMRegimeState.DISCOVERY: 2.0,
    PMRegimeState.CONSENSUS: 3.0,
    PMRegimeState.NEWS_CATALYST: 3.0,
    PMRegimeState.PRE_RESOLUTION: 5.0,
    PMRegimeState.SHARP_DISAGREEMENT: 3.0,
}

PM_REGIME_SCALE: dict[PMRegimeState, float] = {
    PMRegimeState.DISCOVERY: 1.2,       # More opportunity in young markets
    PMRegimeState.CONSENSUS: 1.0,
    PMRegimeState.NEWS_CATALYST: 0.9,   # Higher uncertainty
    PMRegimeState.PRE_RESOLUTION: 0.8,  # Stricter filter, lower scale
    PMRegimeState.SHARP_DISAGREEMENT: 1.1,
}

@dataclass(frozen=True)
class PMRegimeClassification:
    regime: PMRegimeState
    confidence: float
    edge_threshold_pct: float  # Regime-adjusted threshold
    scale: float               # For alpha composition

def classify_pm_regime(
    hours_to_close: float,
    hours_since_created: float,
    price_variance_7d: float,
    volume_spike_ratio: float,
) -> PMRegimeClassification:
    """Classify PM regime using priority-ordered rules."""
    ...
```

### Pattern 3: Correlation Detection (PM-04)

**What:** Before dispatching a PM edge alert, check whether any active sportsbook bet shares the same entity (team, player, event) as the PM market. If correlation coefficient exceeds 0.6, post a warning embed first.

**Entity extraction approach (Claude's discretion — recommended):** Token-based matching. Normalize market description and bet `selection` field to lowercase tokens, strip punctuation and common words ("will", "the", "be", "in", "at"). Shared token ratio is the correlation coefficient. This is intentionally simple and fast — no NLP library needed.

```
correlation = |shared_tokens| / max(|tokens_a|, |tokens_b|)
```

If `correlation > 0.6` for any combination of (active_bet, pm_edge), dispatch a correlation warning embed before the PM edge embed.

```python
# packages/analytics/src/sharpedge_analytics/pm_correlation.py
def compute_entity_correlation(
    text_a: str,   # PM market title
    text_b: str,   # Sportsbook bet selection
    stopwords: frozenset[str] | None = None,
) -> float:
    """Token-overlap correlation between two market descriptions."""
    ...

def detect_correlated_positions(
    pm_edge_title: str,
    active_bets: list[dict],  # from Supabase bets table: [{selection, game, sport}]
    threshold: float = 0.6,
) -> list[dict]:
    """Return active bets that are correlated with a PM edge above threshold."""
    ...
```

### Pattern 4: Extending value_scanner_job.py

The job must call the PM scanner AFTER the sports scan loop and merge PM edges into the unified alert queue.

```python
# In value_scanner_job.py, after sports loop:

# PM scan (Kalshi)
kalshi_edges = await scan_kalshi_edges(kalshi_client, model_probs, volume_floor=500.0)
# PM scan (Polymarket)
poly_edges = await scan_polymarket_edges(poly_client, model_probs, volume_floor=500.0)

# Merge with sports plays, enrich, rank by alpha
all_plays = all_value_plays + kalshi_edges + poly_edges
enriched = enrich_with_alpha(all_plays)
ranked = rank_by_alpha(enriched)
```

PM edges must be compatible with `enrich_with_alpha()`. The `PMEdge` dataclass must have the same fields that `enrich_with_alpha()` reads from `ValuePlay` — specifically `edge_percentage`, `confidence`, `game_id`/`market_id`. Either add duck-typing to `enrich_with_alpha()` or define a protocol/union type.

### Pattern 5: Discord Embed for PM Edges

PM alerts use the same embed builder as sports alerts but with `[PM]` prefix on title and platform identifier in footer.

```
Title: [PM] Will the Fed cut rates by June 2026? — Kalshi
Fields: Model Prob | Market Prob | Edge | Alpha Badge | Regime
Footer: Kalshi · Discovery regime · Vol $12,400 24h
```

Correlation warning embed (posted BEFORE the PM alert):
```
Title: ⚠ Correlation Warning
Description: This PM play (NBA title odds) correlates with your active bet
             (Lakers -4.5, FanDuel) — correlation 0.72. Review before placing.
Color: orange (0xFFA500)
```

### Anti-Patterns to Avoid

- **Creating a pm_scanner_job.py:** Locked decision — extend value_scanner_job.py only.
- **Pre-scan regime filtering:** Regime is applied post-scan. Never skip markets based on regime before scanning.
- **Blocking correlated alerts:** Correlation warning posts BEFORE the alert; the alert still posts.
- **ML-based entity matching:** Token overlap is sufficient. No spaCy, no NLTK.
- **Calling validate_setup directly:** PM edges route through the same LangGraph graph node — do not bypass it.
- **Storing model probabilities as hardcoded values:** model_probs dict must be computed at scan time, not cached from a prior run.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Alpha scoring | Custom PM alpha formula | `compose_alpha()` from `alpha.py` | Exact same formula used for sports; unified ranking requires shared scorer |
| Alpha enrichment | Custom loop | `enrich_with_alpha()` from `sharpedge_analytics` | Already handles None-safe sort, badge assignment |
| Alpha ranking | Custom sort | `rank_by_alpha()` from `sharpedge_agent_pipeline.alerts.alpha_ranker` | None-safe sort already tested |
| Kalshi API calls | Raw httpx calls | `KalshiClient.get_markets()` | Already handles RSA auth, pagination, field parsing |
| Polymarket API calls | Raw httpx calls | `PolymarketClient.get_markets()` | Already handles gamma/CLOB split, volume_24h field |
| Discord embeds | Custom embed builder | Extend existing `analysis_embeds.py` pattern | Discord color constants, badge formatting already established |
| Fee calculation | Custom fee math | `PLATFORM_FEES[Platform.KALSHI]` in `prediction_markets.py` | Fee formula already correct: `0.07 * contracts * price * (1 - price)` |

**Key insight:** The PM alpha and PM regime modules must produce output that is directly sortable with sports value play alpha scores. Build for unified ranking from the start — the PMEdge dataclass and the ValuePlay dataclass must share enough interface that `rank_by_alpha()` can handle both.

---

## Common Pitfalls

### Pitfall 1: prediction_markets.py at 614 Lines
**What goes wrong:** Any attempt to add new functions to `prediction_markets.py` immediately pushes it further over the 500-line limit (already 114 lines over). CI/linting may enforce this limit.
**Why it happens:** Existing file accumulated fee structures, dataclasses, arb logic, and correlation network.
**How to avoid:** Split `prediction_markets.py` into a sub-package (`prediction_markets/`) as the first task of Wave 0. Use backward-compat re-exports in `__init__.py`. Do not add PM edge code to the monolith.
**Warning signs:** If a plan task says "add to prediction_markets.py" without first splitting it, flag that task.

### Pitfall 2: enrich_with_alpha() Incompatibility
**What goes wrong:** `enrich_with_alpha()` reads `edge_percentage`, `confidence`, and other fields from `ValuePlay` dataclass using `getattr()` with defaults. A `PMEdge` without these fields will silently get SPECULATIVE badges on every PM edge.
**Why it happens:** `enrich_with_alpha()` uses duck typing but PMEdge is a new type with different field names.
**How to avoid:** Either (a) make PMEdge a subclass of ValuePlay with appropriate fields, or (b) add explicit PMEdge handling branch to `enrich_with_alpha()`. Option (b) preferred — minimal change.
**Warning signs:** All PM edges getting SPECULATIVE badge regardless of edge size.

### Pitfall 3: Model Probability Source is Undefined
**What goes wrong:** PM-01 and PM-02 require "model probability" to compare against market price. The project has sports model projections (from `projections` Supabase table) but no PM model.
**Why it happens:** Prediction markets don't have historical stats the same way sports games do.
**How to avoid:** For Phase 3, use a simplified model probability: the market's fair probability implied by removing the platform fee (Kalshi: probability-weighted fee formula already in PLATFORM_FEES). "Model probability" = `price / (1 - effective_fee_rate)` when no external model exists. This is equivalent to asking: "what is the fair price after fees?" An edge exists when the user's external view (derived from news/fundamentals) differs from the fee-adjusted market price. Document this assumption clearly in the module docstring.
**Warning signs:** If PM-01 tasks reference an external prediction model that doesn't exist, flag it.

### Pitfall 4: Kalshi Auth Header Expiry
**What goes wrong:** `KalshiClient._build_headers()` generates a timestamp at construction time. For long-running jobs, the auth header becomes stale.
**Why it happens:** `_build_headers()` is called once in `__init__`, but Kalshi requires a fresh timestamp per request.
**How to avoid:** Each API call in the extended job must create a fresh KalshiClient (or refresh headers before each call). The existing `get_kalshi_client()` helper creates a new instance — use it per scan cycle, not once globally.
**Warning signs:** 401 errors after first scan run; intermittent auth failures.

### Pitfall 5: Correlation Computation Running on Every Alert
**What goes wrong:** If correlation check queries Supabase on every PM edge in every scan cycle, this becomes N*M queries (N edges × M active bets).
**Why it happens:** Naive implementation calls Supabase inside the alert loop.
**How to avoid:** Fetch all active bets once at the start of the scan, cache as a list, pass to `detect_correlated_positions()` for each PM edge. O(N*M) in memory but O(1) DB queries.
**Warning signs:** Slow scan cycles; Supabase rate limit warnings in logs.

### Pitfall 6: PM Regime Requires Market History Fields Not Available
**What goes wrong:** PM regime classification needs `price_variance_7d` and `volume_spike_ratio`, but `KalshiMarket` only has `volume_24h`, `last_price`, and `close_time`. No 7-day history.
**Why it happens:** Both API clients only fetch current snapshot, not historical data.
**How to avoid:** For Phase 3, use available proxies:
- `price_variance_7d`: use `spread` (bid-ask spread) as a proxy for price uncertainty. Tight spread = low variance (Consensus). Wide spread = high variance.
- `volume_spike_ratio`: unavailable — classify NEWS_CATALYST only when `volume_24h > 5 * avg_volume_floor` (configurable heuristic).
- `hours_since_created`: unavailable from market data — Discovery classification requires an approximation. Use the fact that Kalshi markets with `volume < 1000` AND `open_interest < 100` are likely young. For Polymarket, no `created_at` in the client — default Discovery to "not classifiable from snapshot" and fall through to next rule.
**Warning signs:** Every market classified as CONSENSUS because variance data is missing.

---

## Code Examples

### Kalshi API Field Mapping for PM Edge

```python
# From KalshiMarket dataclass (kalshi_client.py):
market.mid_price          # = (yes_bid + yes_ask) / 2 — use as market_prob
market.volume_24h         # = int (contracts traded 24h) — use for liquidity filter
market.close_time         # datetime | None — for PRE_RESOLUTION classification
market.spread             # = yes_ask - yes_bid — proxy for price variance

# Edge calculation:
edge_pct = (model_prob - market.mid_price) * 100
# Surface if edge_pct > regime_threshold_pct
```

### Polymarket API Field Mapping for PM Edge

```python
# From PolymarketMarket dataclass (polymarket_client.py):
market.yes_price          # float 0-1 — use as market_prob
market.volume_24h         # float USD — use for liquidity filter directly
market.end_date           # datetime | None — for PRE_RESOLUTION
market.liquidity          # float — additional liquidity signal

# Edge calculation:
edge_pct = (model_prob - market.yes_price) * 100
# Surface if edge_pct > regime_threshold_pct
```

### Composing Alpha for a PM Edge

```python
# pm_edge_scanner.py — after edge is detected
from sharpedge_models.alpha import compose_alpha
from sharpedge_analytics.pm_regime import classify_pm_regime, PM_REGIME_SCALE

regime_result = classify_pm_regime(
    hours_to_close=hours_to_close,
    hours_since_created=48.0,  # approximation if unavailable
    price_variance_7d=market.spread,  # proxy
    volume_spike_ratio=1.0,  # default if history unavailable
)

alpha_result = compose_alpha(
    edge_score=edge_pct / 100,          # normalize to 0-1
    regime_scale=PM_REGIME_SCALE[regime_result.regime],
    survival_prob=0.95,                 # PM positions are fixed size — no ruin risk
    confidence_mult=1.0,                # Phase 5 calibration not yet available
)
```

### Correlation Warning Dispatch (in value_scanner_job.py extension)

```python
# For each PM edge, check correlation before queueing alert
correlations = detect_correlated_positions(
    pm_edge_title=edge.market_title,
    active_bets=active_bets,  # fetched once before loop
    threshold=0.6,
)
if correlations:
    _pending_value_alerts.append({
        "type": "correlation_warning",
        "pm_market": edge.market_title,
        "correlated_bets": correlations,
    })
# Then queue the PM edge alert regardless
_pending_value_alerts.append({
    "type": "pm_edge",
    ...
})
```

---

## File Size Constraint Compliance

The 500-line limit applies to all files. Current violations that affect Phase 3:

| File | Lines | Action Required |
|------|-------|----------------|
| `prediction_markets.py` | 614 | Split into sub-package before adding any PM code — Wave 0 task |
| `value_scanner_job.py` | ~262 (safe) | Extend cautiously; adding PM section should stay under 400 lines |
| `copilot/tools.py` | ~383 (safe) | Replace stub with real implementation; still under limit |

New files to create must each stay under 500 lines:
- `pm_edge_scanner.py` — target 150-200 lines
- `pm_regime.py` — target 80-120 lines (mirrors regime.py at 100 lines)
- `pm_correlation.py` — target 80-100 lines

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate PM scanner job | Extend value_scanner_job.py | Phase 3 design decision | Simpler scheduling; unified alert queue |
| Cross-platform arb detection | Single-platform edge detection | Phase 3 (new) | Model prob vs market prob is different from arb |
| Stub get_prediction_market_edge | Real implementation | Phase 3 | Copilot tool becomes functional |

**Already exists but is the wrong problem:**
- `prediction_market_scanner.py`: Does arbitrage between Kalshi and Polymarket (buy YES on one, NO on other). Phase 3 is about model probability vs a single platform's market price. These are distinct — do not confuse or merge them.

---

## Open Questions

1. **Model probability source for PM markets**
   - What we know: Sports models use the `projections` table. No PM-specific model exists.
   - What's unclear: Should model_prob come from an external source (Metaculus consensus, Manifold aggregator), or be computed from the fee-adjusted price?
   - Recommendation: Use fee-adjusted price as the baseline "model probability" for Phase 3. This surfaces markets where the market is mispriced relative to its own fee structure. Document this assumption. A real model can be plugged in Phase 5.

2. **Kalshi volume units (contracts vs USD)**
   - What we know: `KalshiMarket.volume_24h` is declared as `int` in the dataclass. The field is labeled in contracts (not USD). The $500 liquidity floor uses USD.
   - What's unclear: The Kalshi API documentation and the existing parsing code (`data.get("volume_24h", 0)`) do not apply a price conversion. At $0.50/contract average, 1000 contracts = $500.
   - Recommendation: Verify the unit via Kalshi API docs (https://docs.kalshi.com). For Phase 3, treat `volume_24h * avg_price` as the USD proxy. The planner should make this a Wave 0 verification step.

3. **Supabase bets table schema for correlation (PM-04)**
   - What we know: `bets.py` shows `selection`, `game`, `sport`, `sportsbook` fields. `create_bet()` inserts these.
   - What's unclear: Are all currently active sportsbook bets in Supabase? The `bets` table query pattern shows `result` filter for PENDING. If the field is not consistently populated, correlation check would miss bets.
   - Recommendation: Use `result = PENDING` filter to get active bets. Add a fallback to also include bets with `result IS NULL` for safety.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0 + pytest-asyncio 0.24 + pytest-mock 3.14 |
| Config file | pyproject.toml (no separate pytest.ini) |
| Quick run command | `python -m pytest tests/unit/analytics/ -x -q` |
| Full suite command | `python -m pytest tests/unit/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PM-01 | scan_pm_edges() returns edges >threshold for Kalshi markets with sufficient volume | unit | `python -m pytest tests/unit/analytics/test_pm_edge_scanner.py -x -q` | Wave 0 |
| PM-01 | Markets below volume_floor are silently skipped | unit | `python -m pytest tests/unit/analytics/test_pm_edge_scanner.py::test_volume_floor -x` | Wave 0 |
| PM-02 | scan_pm_edges() returns edges for Polymarket markets with same threshold logic | unit | `python -m pytest tests/unit/analytics/test_pm_edge_scanner.py::test_polymarket -x` | Wave 0 |
| PM-03 | classify_pm_regime() returns PRE_RESOLUTION when hours_to_close <24 | unit | `python -m pytest tests/unit/analytics/test_pm_regime.py::test_pre_resolution -x` | Wave 0 |
| PM-03 | classify_pm_regime() returns DISCOVERY when hours_since_created <48 | unit | `python -m pytest tests/unit/analytics/test_pm_regime.py::test_discovery -x` | Wave 0 |
| PM-03 | Edge threshold adjusts per regime (DISCOVERY=2%, PRE_RESOLUTION=5%) | unit | `python -m pytest tests/unit/analytics/test_pm_regime.py::test_thresholds -x` | Wave 0 |
| PM-04 | detect_correlated_positions() returns matching bets when token overlap >0.6 | unit | `python -m pytest tests/unit/analytics/test_pm_correlation.py -x -q` | Wave 0 |
| PM-04 | Correlation warning queued before PM edge alert in scanner job | integration | `python -m pytest tests/unit/analytics/test_pm_edge_scanner.py::test_correlation_warning_order -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/unit/analytics/ -x -q`
- **Per wave merge:** `python -m pytest tests/unit/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/analytics/test_pm_edge_scanner.py` — covers PM-01, PM-02
- [ ] `tests/unit/analytics/test_pm_regime.py` — covers PM-03
- [ ] `tests/unit/analytics/test_pm_correlation.py` — covers PM-04
- [ ] `tests/unit/analytics/__init__.py` — already exists (no gap)
- [ ] No new framework install required — pytest already configured

---

## Sources

### Primary (HIGH confidence)
- Direct code read: `packages/data_feeds/src/sharpedge_feeds/kalshi_client.py` — KalshiMarket fields, auth pattern, get_markets() signature
- Direct code read: `packages/data_feeds/src/sharpedge_feeds/polymarket_client.py` — PolymarketMarket fields, volume_24h field name, get_markets() pagination
- Direct code read: `packages/analytics/src/sharpedge_analytics/prediction_markets.py` — fee formulas, arb detection, 614-line count
- Direct code read: `packages/analytics/src/sharpedge_analytics/regime.py` — 4-state rule-based classifier pattern to mirror
- Direct code read: `packages/models/src/sharpedge_models/alpha.py` — compose_alpha() signature, EDGE_SCORE_FLOOR, badge thresholds
- Direct code read: `apps/bot/src/sharpedge_bot/jobs/value_scanner_job.py` — extension point, enrich_with_alpha() call site, alpha ranking
- Direct code read: `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py` — get_prediction_market_edge stub location, COPILOT_TOOLS list
- Direct code read: `packages/database/src/sharpedge_db/queries/bets.py` — Supabase bets schema, create_bet() fields

### Secondary (MEDIUM confidence)
- CONTEXT.md locked decisions — user decisions verbatim, no need for external verification
- pyproject.toml — confirmed pytest, pytest-asyncio, pytest-mock versions
- Existing test files in `tests/unit/` — confirmed test directory structure and file naming conventions

### Tertiary (LOW confidence)
- Kalshi API volume unit (contracts vs USD): not verified against official docs — flagged as open question requiring verification before implementation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all existing code read directly; no new dependencies
- Architecture: HIGH — locked decisions from CONTEXT.md; pattern from regime.py is concrete
- Pitfalls: HIGH — file size issue verified by line count; auth issue identified from code; model probability gap is a genuine design question
- Volume unit (Kalshi): LOW — requires API doc verification

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (Kalshi and Polymarket APIs are stable; 30-day horizon safe)
