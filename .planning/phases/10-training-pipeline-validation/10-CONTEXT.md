# Phase 10: Training Pipeline Validation — Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Run the three existing PM training scripts against live Kalshi and Polymarket APIs, store resolved market data in Supabase, and produce validated per-category `.joblib` RandomForest artifacts. All three scripts exist from Phase 9 — this phase migrates their storage layer from parquet to Supabase and executes them against live data. No new ML logic is written here.

</domain>

<decisions>
## Implementation Decisions

### Storage layer — Supabase, not parquet

- Resolved market backfill writes to a new `resolved_pm_markets` Supabase table, not local parquet files
- Upsert by `market_id` — download is idempotent and resumable by design (restart = re-upsert only new records)
- `process_pm_historical.py` queries from Supabase instead of reading parquet
- Rationale: parquet was inherited from the sports ML pipeline pattern; Supabase is consistent with the rest of the data layer and makes the ablation/backtest in Phase 13 directly queryable via SQL

### Backfill scope

- Pull **all-time** resolved markets (no date filter, no page cap)
- Run until cursor is exhausted — this is a one-time training backfill
- **Polymarket**: filter by `volume > 100 USDC` — excludes noise markets that would degrade calibration
- **Kalshi**: no volume filter — Kalshi markets tend to be more liquid by design

### Category coverage

- Train whatever categories have ≥ 200 resolved markets — do **not** hard-require all 5
- GATE-01 (Phase 13) checks artifacts exist for **trained categories only**, not a hard all-5 requirement
- Categories below the 200-market minimum are skipped with a WARNING in the training report
- Untrained categories fall back to fee-adjusted probability in `scan_pm_edges()` — existing graceful fallback

### Quality badge threshold

- Minimum **`medium`** badge required for an artifact to be written to `data/models/pm/`
- `low` badge result → training report entry with `WARNING` status, no `.joblib` artifact written
- `medium` / `high` / `excellent` → artifact written and marked production-ready in report
- Consistent with the sports model pipeline promotion gate

### API credentials

- Preflight check at script start: verify `KALSHI_API_KEY` + `KALSHI_PRIVATE_KEY_PEM` are set and make one authenticated test call before starting pagination
- If credentials missing or auth fails → **hard exit** with a clear, actionable error message (not silent offline fallback)
- Offline/fixture mode is **test-only** — operational training runs always require live credentials
- Polymarket download requires no auth (Gamma API is public) — no preflight needed there

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- `scripts/download_pm_historical.py` — exists, currently writes to parquet. Needs: storage layer swapped to Supabase upsert, offline mode preserved for tests, preflight added.
- `scripts/process_pm_historical.py` — exists, currently reads parquet. Needs: query from Supabase instead.
- `scripts/train_pm_models.py` — exists, reads from processed DataFrames. Minimal change needed if process_pm_historical.py outputs are compatible.
- `packages/data_feeds/src/sharpedge_feeds/kalshi_client.py` — `get_markets(status="settled")` already supports resolved market fetch with cursor pagination.
- `packages/data_feeds/src/sharpedge_feeds/polymarket_client.py` — `get_markets(active=False, closed=True)` returns resolved markets. No auth required.
- `packages/models/src/sharpedge_models/pm_feature_assembler.py` — `PM_CATEGORIES` constant defines the 5 categories.
- `packages/models/src/sharpedge_models/walk_forward.py` — `quality_badge_from_windows()` already implements the badge logic.
- `packages/models/src/sharpedge_models/calibration_store.py` — `CalibrationStore.update()` for Platt calibration per category.

### Established Patterns

- `data/models/` — existing sports `.joblib` artifacts live here; PM artifacts go in `data/models/pm/` (already defined as `PM_MODEL_DIR` in `pm_resolution_predictor.py`)
- `SettlementLedger` dual-mode pattern (Phase 6) — in-memory without env vars, Supabase with env vars. The `resolved_pm_markets` table should follow the same dual-mode pattern.
- Supabase upsert-on-conflict pattern used in existing Phase 6 stores — use the same approach

### Integration Points

- `packages/database/` — Supabase migration for `resolved_pm_markets` table goes here
- `pm_resolution_predictor.py` — reads from `data/models/pm/` at inference time; no change needed there
- `scan_pm_edges()` in `pm_edge_scanner.py` — `model_probs.get(market_id)` fallback is already correct; no change

</code_context>

<specifics>
## Specific Ideas

- Storage decision: "confused as to why we are going with parquet files over SQL with our Supabase DB" — Supabase is the right home for this data
- Offline mode is test-only; the operator's `.env` always has credentials for production training runs
- Upsert-by-market_id means the operator can re-run the download script any time without duplication or corruption

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-training-pipeline-validation*
*Context gathered: 2026-03-15*
