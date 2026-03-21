# Codebase Concerns

**Analysis Date:** 2026-03-21

## Tech Debt

**Supabase client dual export (web):**
- Issue: `createClient()` is the preferred factory, but a legacy `supabase` singleton remains for gradual migration.
- Files: `apps/web/src/lib/supabase.ts`
- Impact: Two code paths instantiate browser clients; risk of inconsistent usage and harder refactors until `supabase` is removed.
- Fix approach: Grep for `import { supabase }` (currently: `apps/web/src/app/page.tsx`, `apps/web/src/app/(dashboard)/layout.tsx`, `apps/web/src/app/(dashboard)/portfolio/page.tsx`, `apps/web/src/app/account/page.tsx`, `apps/web/src/app/auth/login/page.tsx`, `apps/web/src/app/auth/signup/page.tsx`, `apps/web/src/app/auth/set-password/page.tsx`, `apps/web/src/components/copilot/chat-stream.tsx`, `apps/web/src/components/swarm/post-mortem-panel.tsx`, `apps/web/src/components/swarm/risk-panel.tsx`) and switch each to `createClient()`; then delete the legacy export and the TODO comment.

**Kalshi venue adapter — silent degradation:**
- Issue: `list_markets`, `get_orderbook`, and related paths catch broad `Exception` and return empty structures without surfacing errors.
- Files: `packages/venue_adapters/src/sharpedge_venue_adapters/adapters/kalshi.py`
- Impact: Callers cannot distinguish “no markets” from auth failure, network error, or API change — debugging and monitoring blind spots.
- Fix approach: Log at warning/error with context, optionally re-raise for execution paths, or return a typed result (success vs error) instead of empty lists/books.

**Settlement outcome not mapped:**
- Issue: `get_settlement_state` always passes `outcome=None` with a TODO; settled markets do not expose yes/no outcome through the adapter.
- Files: `packages/venue_adapters/src/sharpedge_venue_adapters/adapters/kalshi.py` (see `get_settlement_state`, `_to_canonical` which already reads `m.result`)
- Impact: Downstream settlement / P&L logic that needs outcome strings may be wrong or incomplete in live mode.
- Fix approach: Map `market.result` (`"yes"` / `"no"`) into `SettlementState.outcome` when `KalshiClient` is available; align with phase notes in `.planning/phases/06-.../06-VERIFICATION.md`.

**Regime model — HMM deferred:**
- Issue: Rule-based regime only; explicit TODO for HMM upgrade gated on data volume audit.
- Files: `packages/analytics/src/sharpedge_analytics/regime.py`
- Impact: Regime signals may be less adaptive than planned until the upgrade path is executed.
- Fix approach: Run the Supabase observation-count audit referenced in the comment, then implement HMM behind a feature flag if thresholds are met.

**Polymarket live execution:**
- Issue: CLOB live path raises `NotImplementedError` when `ENABLE_POLY_EXECUTION=true`.
- Files: `packages/data_feeds/src/sharpedge_feeds/polymarket_clob_orders.py`
- Impact: Any automation that flips the env var expecting real orders will crash at runtime.
- Fix approach: Treat as explicit phase work (tracked as POLY-EXEC-01 in file docstring); keep flag false in all deployed configs until implemented.

**Public betting data — synthetic fallback:**
- Issue: Action Network integration is a placeholder; production flow falls back to `_generate_estimated_data`.
- Files: `packages/data_feeds/src/sharpedge_feeds/public_betting_client.py`
- Impact: Features consuming “public %" may show heuristic estimates, not measured ticket splits — dangerous if presented as factual without labeling.
- Fix approach: Gate UI/analytics on data source metadata, or require real feeds before surfacing in user-facing copy.

**Historical Kalshi snapshots:**
- Issue: `get_historical_snapshots` raises `NotImplementedError` until candlestick API is confirmed.
- Files: `packages/venue_adapters/src/sharpedge_venue_adapters/adapters/kalshi.py`
- Impact: Replay/backtest paths that call this method will fail until implemented or routed around.

## Known Bugs

**None verified in this pass** — several behaviors are intentional stubs or graceful empty responses; treat “empty list” API responses from `apps/webhook_server/src/sharpedge_webhooks/routes/v1/prediction_markets.py` as degraded mode, not necessarily bugs.

## Security Considerations

**Service role and server-side secrets:**
- Risk: Backend jobs use `SUPABASE_SERVICE_KEY` (e.g. FCM token fan-out) with full database bypass of RLS — any leak is catastrophic.
- Files: `apps/bot/src/sharpedge_bot/jobs/value_scanner_job.py`, `packages/venue_adapters/src/sharpedge_venue_adapters/snapshot_store.py`
- Current mitigation: Keys expected from environment only; `.gitignore` excludes `.env` and credential patterns; workspace rules forbid committing secrets.
- Recommendations: Never expose service role to Next.js client bundles; keep using `NEXT_PUBLIC_*` only for anon URL/key on the web app (`apps/web/src/lib/supabase.ts`, `apps/web/src/middleware.ts`). Rotate keys if plist or env files were ever copied into chat or CI logs.

**Untracked Firebase / Google config on disk:**
- Risk: Git status shows untracked `apps/mobile/ios/Runner/GoogleService-Info.plist` and `apps/mobile/macos/Runner/GoogleService-Info.plist` — these often contain project identifiers and should not be committed casually.
- Files: paths above (existence only; contents not audited here)
- Current mitigation: Untracked — verify `.gitignore` or repo policy before first commit of mobile app assets.
- Recommendations: Use team secrets/EAS credentials; document in mobile README whether plists are local-only.

## Performance Bottlenecks

**Synchronous env-based client creation:**
- Problem: Legacy `supabase` export in `apps/web/src/lib/supabase.ts` creates a client at module load for every importer.
- Files: `apps/web/src/lib/supabase.ts`
- Improvement path: Per-request or per-tree `createClient()` patterns from `@supabase/ssr` reduce risk of stale singleton assumptions (align with middleware usage in `apps/web/src/middleware.ts`).

**Large in-repo or workspace data artifacts:**
- Problem: Untracked `data/processed/**/*.parquet` and `.csv` (per git status) can bloat clones and confuse CI if later added without Git LFS or DVC.
- Files: under `data/processed/` (e.g. sport training sets, `prediction_markets/*.parquet`)
- Cause: ML pipelines write large binaries; `.gitignore` already ignores `data/models/` but not necessarily all processed tables.
- Improvement path: Prefer DVC, LFS, or artifact storage; keep processed data out of default git commits.

## Fragile Areas

**Webhook PM routes — swallow-all error handling:**
- Files: `apps/webhook_server/src/sharpedge_webhooks/routes/v1/prediction_markets.py`
- Why fragile: Lazy imports and broad `except` return `[]`, masking import errors, missing jobs, or runtime failures; operators see “no data” instead of 500 with a reason.
- Safe modification: Add structured logging inside each `except`, metrics, or a degraded header/body field before returning empty lists.
- Test coverage: Confirm webhook integration tests exist for these endpoints; if not, add contract tests.

**Trading swarm sentiment placeholder:**
- Files: `packages/trading_swarm/src/sharpedge_trading/agents/research_agent.py` (`_raw_to_score` uses fixed `sentiment=0.5` until LLM step)
- Why fragile: If prediction agent or LLM path is skipped or fails open, scores stay neutral — may underweight narrative risk.
- Safe modification: Integration tests that assert end-to-end score mutation when LLM returns non-neutral sentiment.

## Scaling Limits

**FCM broadcast model:**
- Current capacity: `value_scanner_job` loads all `fcm_token` rows in one select (`user_device_tokens`) and iterates sends.
- Limit: Large user tables will slow the job and approach provider rate limits.
- Scaling path: Batch sends, pagination, queue workers, and per-user targeting instead of global fan-out.

## Dependencies at Risk

**Next.js 14.2.x (web):**
- Risk: Framework drift vs current Next/Vercel recommendations; security and RSC patterns evolve quickly.
- Impact: `apps/web/package.json` pins `next@14.2.5` — planned upgrades need regression pass on auth middleware (`apps/web/src/middleware.ts`) and SWR data hooks.

## Missing Critical Features

**CI pipeline in repo:**
- Problem: No `.github/workflows` detected in workspace — no automated test/lint gate on push.
- Blocks: Consistent quality enforcement across the uv workspace and `apps/web`.
- Priority: High for teams larger than one; add jobs for `pytest` (workspace) and `apps/web` `npm test` / `npm run build`.

**ESLint config for web:**
- Problem: No `eslint.config.*` or `.eslintrc*` under `apps/web` — TypeScript errors rely on compiler and Vitest only.
- Blocks: Uniform style and some classes of static bugs.
- Priority: Medium.

## Test Coverage Gaps

**Python packages vs web:**
- Web: Vitest tests under `apps/web/src/test/*.test.tsx` (e.g. `apps/web/src/test/dashboard.test.tsx`, `apps/web/src/test/copilot.test.tsx`).
- Python: Distributed under `packages/*/tests/` and `tests/unit/` — coverage uneven across new features (e.g. webhook v1 routes, Kalshi adapter error paths).
- Risk: Silent-empty behaviors in `kalshi.py` and `prediction_markets.py` lack negative tests.
- Priority: Medium for adapter and API routes; High before live trading execution phases.

---

*Concerns audit: 2026-03-21*
