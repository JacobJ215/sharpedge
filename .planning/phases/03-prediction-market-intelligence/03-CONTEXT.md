# Phase 3: Prediction Market Intelligence - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Surface edges in Kalshi and Polymarket prediction markets, classify PM regime state, and warn when portfolio correlation across sportsbook + PM positions exceeds the threshold. All built on top of the stable Phase 2 LangGraph graph. Creating/placing bets and UI presentation are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Edge delivery channel
- PM edges post to the **same Discord channel** as sports value plays, with a clear PM label/prefix to distinguish them
- PM scanning runs in the **same job as value_scanner_job.py** — no separate pm_scanner_job.py
- All alerts (PM and sports) ranked by **unified composite alpha score** — highest alpha posts first regardless of type
- PM edges go through the **same 9-node LangGraph validate_setup gate** (PASS/WARN/REJECT) before posting — no separate quality check

### Liquidity threshold
- Primary filter: **minimum 24h volume in $** using the existing `UnifiedOutcome.volume_24h` field
- **Per-platform thresholds**: Kalshi and Polymarket have different typical volumes — configure separately
- Default minimum: **$500** for both platforms as starting point (tunable per-platform)
- Markets below the liquidity floor are **silently skipped** — filtered count goes to debug log only, not Discord

### PM regime behavior
- Regime **adjusts edge threshold dynamically** — Pre-Resolution gets stricter (e.g. 5%), Discovery gets looser (e.g. 2%), 3% as the neutral baseline
- Classification: **rule-based classifier** using 4 signals (same pattern as Phase 1 sports regime — deterministic, no ML)
  - **Time-to-resolution**: Markets closing in <24h → Pre-Resolution
  - **Price stability**: Low recent variance → Consensus; high variance → Sharp Disagreement or News Catalyst
  - **Volume trend**: Sudden spike → News Catalyst; steady accumulation → Consensus
  - **Market age**: Markets <48h old → Discovery
- Regime applied **post-scan only** — all markets above liquidity floor are scanned; regime adjusts threshold and alpha score after detection (no pre-scan filtering)

### Correlation detection scope
- Active positions sourced from **user's logged bets in Supabase** (existing bet tracker)
- Correlation determined by **team/entity matching** — two positions are correlated if they share the same team, player, or event entity (string/entity match on market description)
- When an alert would push correlation >0.6: **post a Discord warning embed before the correlated alert** — user sees the risk before the play
- Correlated alerts **post with warning, not blocked** — no queue/acknowledge flow

### Claude's Discretion
- Exact threshold multipliers per regime state (e.g. Pre-Resolution 5% vs Discovery 2%)
- Entity extraction approach for team/player matching
- Exact embed format for PM alerts vs sports alerts

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `prediction_markets.py` (614 lines, over limit): PM arbitrage detection with Kalshi/Polymarket fee structures — needs splitting before extending
- `unified_markets.py` (565 lines, over limit): Cross-platform analytics with `UnifiedOutcome` dataclass that already has `volume_24h`, `probability`, `platform_fee_pct` fields — reuse as core PM edge type
- `kalshi_client.py` (273 lines): Kalshi API client with `KalshiMarket` dataclass, RSA auth, demo/prod env support
- `polymarket_client.py` (375 lines): Polymarket API client
- `value_scanner_job.py`: Existing scheduled scanner job to extend for PM edges
- `alpha.py`: `compose_alpha()` and `enrich_with_alpha()` from Phase 1 — reuse for PM alpha scoring
- `regime.py`: Rule-based 4-state sports classifier — mirror pattern for PM regime classifier
- `copilot/tools.py`: `get_prediction_market_edge` tool already wired — ensure PM scanner data feeds this

### Established Patterns
- Rule-based classifier with confidence score (from `regime.py`) — use for PM regime
- `enrich_with_alpha()` + `rank_by_alpha()` pipeline (from Phase 2) — extend to PM plays
- Functional module-level APIs (not class-based) — consistent with Phase 1/2 patterns
- Discord embed format from existing value play alerts — PM alerts use same format with label prefix

### Integration Points
- `value_scanner_job.py` — extend to call PM scanner after sports scan
- LangGraph `validate_setup` node — PM edges route through same node
- Supabase bet tracker tables — read active bets for correlation check
- Discord bot embed dispatch — same channel, PM-labeled embeds

</code_context>

<specifics>
## Specific Ideas

- PM edges need a clear visual distinction in Discord — label prefix or emoji (e.g. `[PM]` or a prediction market icon) so users don't confuse them with sports plays
- The liquidity floor ($500 default) should be easy to tune per-platform via config — Kalshi sports markets are typically more liquid than political markets

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-prediction-market-intelligence*
*Context gathered: 2026-03-14*
