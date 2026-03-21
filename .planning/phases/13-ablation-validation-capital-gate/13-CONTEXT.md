# Phase 13: Ablation Validation & Capital Gate - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Validate that trained PM models beat a fee-adjusted market-price fallback (ablation), and enforce four pre-conditions before `ENABLE_KALSHI_EXECUTION=true` is honored (capital gate). Scope: new `CapitalGate` class in `venue_adapters`, ablation script, approval script, and GATE-04 circuit breaker wiring. Dashboard pages are Phase 14.

</domain>

<decisions>
## Implementation Decisions

### Gate enforcement architecture
- **D-01:** Hybrid `CapitalGate` class in `packages/venue_adapters` — `check()` returns a status report (usable from standalone script or CI), `assert_ready()` raises if any condition fails (called from `ShadowExecutionEngine.from_env()`)
- **D-02:** `assert_ready()` collects ALL failing conditions before raising — operator sees the full picture in one error, not whack-a-mole

### Paper-trading period (GATE-02)
- **D-03:** State backed by Supabase — query `shadow_ledger` table rows to compute paper-trading metrics
- **D-04:** Minimum 7 days of paper trading required
- **D-05:** Two metrics both required: positive-signal rate ≥ 55% AND mean predicted edge ≥ 1.5%
- **D-06:** Uses existing `ShadowLedgerEntry.predicted_edge` field — no new columns needed

### Ablation report (ABLATE-01, ABLATE-02)
- **D-07:** Fallback baseline = "always bet YES at current market price, fee-adjusted" — most meaningful comparison against market consensus
- **D-08:** Output: console table (human-readable) + `data/ablation_report.json` (machine-readable, gate reads this)
- **D-09:** Pass threshold: overall edge delta ≥ +1.5% AND every category edge delta ≥ 0.0% (no category allowed to be net-negative)
- **D-10:** Report shows per-category edge delta + overall delta, with PASS/FAIL per category and overall

### Manual review UX (GATE-03)
- **D-11:** `scripts/approve_live.py` — standalone script, shows full gate status table before prompting, blocks if GATE-01 or GATE-02 not met
- **D-12:** Operator types their name at the prompt; script writes `data/live_approval.json` with: `approved_at` (ISO UTC), `approved_by` (operator name), `gate_snapshot` (all 4 condition states at approval time)
- **D-13:** `CapitalGate` reads `data/live_approval.json` to verify GATE-03 — file must exist and be valid JSON

### Circuit breaker (GATE-04)
### Claude's Discretion
- GATE-04 wires into the existing `CircuitBreakerState` pattern from `packages/trading_swarm/src/sharpedge_trading/agents/risk_agent.py` — when daily realized loss exceeds the configured threshold, write a circuit-breaker log entry AND remove/invalidate `data/live_approval.json` so live mode cannot restart without re-approval
- Drawdown threshold: configurable via `CIRCUIT_BREAKER_DAILY_LOSS_PCT` env var (default matches existing `TradingConfig.daily_loss_limit`)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Execution engine (gate integration point)
- `packages/venue_adapters/src/sharpedge_venue_adapters/execution_engine.py` — `ShadowExecutionEngine.from_env()` is where `assert_ready()` gets called; `ShadowLedger` is the paper-trading data source

### Circuit breaker pattern
- `packages/trading_swarm/src/sharpedge_trading/agents/risk_agent.py` — `CircuitBreakerState` + `check_circuit_breakers()` — GATE-04 extends this pattern, don't duplicate

### Model artifacts
- `data/models/pm/` — all 5 `.joblib` artifacts (crypto, economic, entertainment, political, weather) — GATE-01 checks these exist

### Settlement ledger schema
- `packages/venue_adapters/src/sharpedge_venue_adapters/ledger.py` — `ShadowLedger` + `ShadowLedgerEntry.predicted_edge` — GATE-02 queries these

### Requirements
- `.planning/REQUIREMENTS.md` §"Live Capital Gate" — GATE-01 through GATE-04 acceptance criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CircuitBreakerState` (`risk_agent.py`): daily_loss tracking + paused_until logic — GATE-04 reuses/extends this
- `ShadowLedger` + `ShadowLedgerEntry.predicted_edge` — paper-trading metrics source for GATE-02
- `ShadowExecutionEngine.from_env()` — injection point for `assert_ready()` call
- `data/models/pm/*.joblib` — all 5 categories present (crypto, economic, entertainment, political, weather)

### Established Patterns
- Gate enforcement lives in `packages/venue_adapters` — same package as execution engine
- Env var convention: `ENABLE_KALSHI_EXECUTION`, `SHADOW_MAX_MARKET_EXPOSURE`, `KALSHI_API_KEY` — new gate vars follow same pattern
- Approval token as JSON file in `data/` — simple, portable, version-controllable if needed

### Integration Points
- `from_env()` is the single startup entry point for live mode — one `assert_ready()` call blocks all bad state
- `scripts/` directory for operator-facing CLI scripts — `approve_live.py` and ablation script go here
- `data/` directory for output files — `ablation_report.json`, `live_approval.json`

</code_context>

<specifics>
## Specific Ideas

- `approve_live.py` should show the same table format as `check()` — operator sees identical output whether they call `check()` manually or run the approval script
- Ablation script runs on historical resolved PM data (already in Supabase `resolved_pm_markets`) — no live API calls needed
- Circuit breaker invalidation: delete or rename `live_approval.json` to `live_approval.json.disabled` (not delete — preserves audit trail)

</specifics>

<deferred>
## Deferred Ideas

- Dashboard visualization of gate status — Phase 14
- Automatic re-approval via CI after drawdown recovery — out of scope for v2.0
- Per-category ablation thresholds configurable separately — current design uses one threshold for all categories

</deferred>

---

*Phase: 13-ablation-validation-capital-gate*
*Context gathered: 2026-03-20*
