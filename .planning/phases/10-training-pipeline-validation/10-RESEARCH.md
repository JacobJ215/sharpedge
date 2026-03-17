# Phase 10: Training Pipeline Validation - Research

**Researched:** 2026-03-15
**Domain:** Python ML pipeline — Supabase storage migration, RandomForest training, Kalshi/Polymarket API backfill
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Storage layer — Supabase, not parquet**
- Resolved market backfill writes to a new `resolved_pm_markets` Supabase table, not local parquet files
- Upsert by `market_id` — download is idempotent and resumable by design (restart = re-upsert only new records)
- `process_pm_historical.py` queries from Supabase instead of reading parquet
- Rationale: parquet was inherited from the sports ML pipeline pattern; Supabase is consistent with the rest of the data layer and makes the ablation/backtest in Phase 13 directly queryable via SQL

**Backfill scope**
- Pull all-time resolved markets (no date filter, no page cap)
- Run until cursor is exhausted — this is a one-time training backfill
- Polymarket: filter by `volume > 100 USDC` — excludes noise markets that would degrade calibration
- Kalshi: no volume filter — Kalshi markets tend to be more liquid by design

**Category coverage**
- Train whatever categories have >= 200 resolved markets — do NOT hard-require all 5
- GATE-01 (Phase 13) checks artifacts exist for trained categories only, not a hard all-5 requirement
- Categories below the 200-market minimum are skipped with a WARNING in the training report
- Untrained categories fall back to fee-adjusted probability in `scan_pm_edges()` — existing graceful fallback

**Quality badge threshold**
- Minimum `medium` badge required for an artifact to be written to `data/models/pm/`
- `low` badge result → training report entry with `WARNING` status, no `.joblib` artifact written
- `medium` / `high` / `excellent` → artifact written and marked production-ready in report
- Consistent with the sports model pipeline promotion gate

**API credentials**
- Preflight check at script start: verify `KALSHI_API_KEY` + `KALSHI_PRIVATE_KEY_PEM` are set and make one authenticated test call before starting pagination
- If credentials missing or auth fails → hard exit with a clear, actionable error message (not silent offline fallback)
- Offline/fixture mode is test-only — operational training runs always require live credentials
- Polymarket download requires no auth (Gamma API is public) — no preflight needed there

### Claude's Discretion

None noted in CONTEXT.md — all implementation decisions were locked.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TRAIN-01 | Operator can run `download_pm_historical.py` against live Kalshi + Polymarket APIs to backfill resolved markets | Storage layer migration from parquet write to Supabase upsert; preflight credential check pattern; cursor-based Kalshi pagination; Polymarket volume filter |
| TRAIN-02 | Operator can run `process_pm_historical.py` to produce per-category feature DataFrames from the backfill | Change data source from parquet read to Supabase SELECT; existing `_build_feature_row` + `_rows_to_df` logic remains; per-category output as in-memory DataFrames passed to training |
| TRAIN-03 | Operator can run `train_pm_models.py` to produce per-category `.joblib` RandomForest artifacts | `train_category()` already implemented and functional; reads from DataFrames, no storage layer change needed; `data/models/pm/` already established as `PM_MODEL_DIR` |
| TRAIN-04 | Training pipeline emits a JSON report with quality badge, calibration score, and category market counts | `training_report.json` written by `train_pm_models.py::main()` exists; needs calibration score field added to each entry alongside existing badge and market_count |
</phase_requirements>

---

## Summary

Phase 10 is a storage layer migration and live execution phase. All three scripts (`download_pm_historical.py`, `process_pm_historical.py`, `train_pm_models.py`) were created in Phase 9 as working implementations. The scripts currently use parquet files as the intermediate storage layer. This phase migrates the storage layer to Supabase for the download and process scripts, then executes all three against live APIs to produce real `.joblib` artifacts.

The primary implementation work is: (1) adding a `resolved_pm_markets` Supabase table via a new migration file, (2) replacing the parquet write in `download_pm_historical.py` with a Supabase upsert, (3) replacing the parquet read in `process_pm_historical.py` with a Supabase SELECT, and (4) adding a preflight credential check to `download_pm_historical.py` for Kalshi. The `train_pm_models.py` script needs only a minor addition: a calibration score field in the training report JSON output.

The existing dual-mode (in-memory without env vars, Supabase with env vars) pattern from `SettlementLedger` in `packages/venue_adapters/src/sharpedge_venue_adapters/ledger.py` is the exact blueprint for how `resolved_pm_markets` storage should work — offline mode (no `SUPABASE_URL`) keeps using the existing parquet fixture path for tests, while production mode writes to Supabase.

**Primary recommendation:** Four targeted edits to existing scripts/migrations — no new ML logic, no new packages. The main risk is the Supabase upsert column schema for `resolved_pm_markets` needing to accommodate both Kalshi fields (ticker, event_ticker, yes_bid, yes_ask, result) and Polymarket fields (condition_id, question, volume, liquidity, resolved_yes).

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `supabase-py` | >=2.0 | Supabase upsert and SELECT | Already used via `packages/database/src/sharpedge_db/client.py` |
| `joblib` | >=1.3 | Model serialization | Already used in `train_pm_models.py` and `pm_resolution_predictor.py` |
| `scikit-learn` | >=1.3 | RandomForestClassifier, CalibrationStore | Already used; `sklearn.ensemble.RandomForestClassifier` |
| `pandas` | >=2.0 | DataFrame construction from Supabase rows | Already the project standard |
| `httpx` | >=0.27 | Kalshi authenticated HTTP | Already used in `kalshi_client.py` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `asyncio` | stdlib | Concurrent Kalshi + Polymarket backfill | Already used in `download_pm_historical.py::_run()` |
| `cryptography` | >=42 | RSA-PSS-SHA256 signing for Kalshi auth | Already used in `kalshi_client.py::_rsa_pss_sign()` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Supabase upsert | Write parquet to object storage | Supabase is already the project data layer; SQL queryable for Phase 13 ablation |
| Single unified table for both platforms | Separate tables per platform | Unified table with nullable platform-specific columns is simpler; one migration |

**Installation:** No new packages required — all dependencies already present in workspace.

---

## Architecture Patterns

### Recommended Project Structure

No new directories needed. Changes are confined to:
```
scripts/
├── download_pm_historical.py    # modify: add preflight, swap parquet write → Supabase upsert
├── process_pm_historical.py     # modify: swap parquet read → Supabase SELECT
└── train_pm_models.py           # modify: add calibration_score field to report entries

packages/database/src/sharpedge_db/migrations/
└── 006_resolved_pm_markets.sql  # NEW: resolved_pm_markets table DDL
```

### Pattern 1: Supabase Dual-Mode (In-Memory / Live)

**What:** Storage class checks for `SUPABASE_URL` at init time. Without it, data stays in-memory (or uses existing parquet fixtures for tests). With it, writes go to Supabase.

**When to use:** Any storage component that needs to work in offline/test mode AND production Supabase mode. Phase 6 `SettlementLedger` is the reference implementation.

**Example (from `ledger.py`, the established pattern):**
```python
# Source: packages/venue_adapters/src/sharpedge_venue_adapters/ledger.py

def __init__(self) -> None:
    self._entries: list = []
    self._supabase = None

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if url and key:
        try:
            from supabase import create_client
            self._supabase = create_client(url, key)
        except ImportError:
            pass  # in-memory mode
```

The `resolved_pm_markets` storage should follow the identical pattern: a `ResolvedPMMarketsStore` class or inline equivalent in `download_pm_historical.py`.

### Pattern 2: Supabase Upsert-on-Conflict

**What:** Insert rows, conflict on the unique market_id key updates non-key columns. Idempotent re-runs do not duplicate data.

**When to use:** Any backfill where the operator might re-run the script (e.g., after a network interruption).

**Example (established pattern from migration 003):**
```sql
-- Source: packages/database/src/sharpedge_db/migrations/003_prediction_markets.sql
-- UNIQUE(platform, market_id, outcome_id) on pm_market_outcomes
-- Supabase Python upsert:
client.table("resolved_pm_markets").upsert(row, on_conflict="market_id").execute()
```

### Pattern 3: Kalshi Preflight Credential Check

**What:** Before starting pagination, make one authenticated GET call. If it fails (401/403 or network error), exit with a clear error message citing the missing env vars.

**When to use:** Any script that requires live Kalshi credentials for a long-running operation.

**Example:**
```python
# Pattern consistent with CONTEXT.md decision: hard exit, not silent fallback
def _kalshi_preflight(api_key: str, private_key_pem: str) -> None:
    """Raises SystemExit with actionable message if Kalshi auth fails."""
    config = KalshiConfig(api_key=api_key, private_key_pem=private_key_pem)
    client = KalshiClient(config=config)
    try:
        # Make one test call — get_markets with limit=1 is the least expensive
        asyncio.run(client.get_markets(status="settled", limit=1))
    except Exception as exc:
        sys.exit(
            f"ERROR: Kalshi preflight failed — {exc}\n"
            f"Set KALSHI_API_KEY and KALSHI_PRIVATE_KEY_PEM in your environment."
        )
```

### Pattern 4: Polymarket Volume Filter

**What:** After fetching the full batch from Polymarket, filter `volume > 100 USDC` before inserting into Supabase or building the DataFrame.

**When to use:** Polymarket backfill only — per locked decision (Kalshi has no volume filter).

**Example:**
```python
# Apply after batch collection, before row construction
all_markets = [m for m in all_markets if getattr(m, "volume", 0) > 100]
```

### Pattern 5: Training Report with Calibration Score

**What:** The training report JSON currently includes `badge`, `market_count`, and `skipped`. TRAIN-04 requires a `calibration_score` field. The calibration score is derived from the OOF Brier score computed during walk-forward.

**When to use:** `train_pm_models.py::train_category()` — add `calibration_score` to the `_write_entry()` dict.

**Example:**
```python
# In train_category(), after walk-forward:
calibration_score = float(np.mean([
    brier_score_loss(oof_actuals[i:i+chunk], oof_probs[i:i+chunk])
    for i, chunk in ...
])) if oof_probs else None

_write_entry({
    "category": category,
    "skipped": False,
    "badge": badge,
    "market_count": len(df),
    "calibration_score": calibration_score,  # NEW
    "model_path": str(model_path),
})
```

A simpler approach: use the overall `brier_score_loss(oof_actuals, oof_probs)` directly — this is already computed (OOF probs and actuals are available). No additional computation needed.

### Anti-Patterns to Avoid

- **Silent offline fallback in production:** The old `_is_kalshi_offline()` function silently falls back to fixture data when `KALSHI_API_KEY` is absent. For live training runs, this must be replaced with a hard exit. The `--offline` flag must remain for test-only use.
- **Re-reading parquet after migration:** `process_pm_historical.py::main()` currently checks for `kalshi_resolved.parquet` existence. After migration, it must query Supabase. Do not keep both paths active simultaneously.
- **Unified `market_id` collision between platforms:** Kalshi uses `ticker` as the market identifier; Polymarket uses `condition_id`. The `resolved_pm_markets` table must include a `source` column (`kalshi`/`polymarket`) as part of the unique constraint to prevent collisions.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Supabase client construction | Custom HTTP client | `packages/database/src/sharpedge_db/client.py::get_supabase_client()` | Singleton pattern already handles env var validation |
| RSA-PSS signing | Custom crypto | `sharpedge_feeds.kalshi_client._rsa_pss_sign()` | Already implemented and tested |
| Cursor-based Kalshi pagination | Custom pagination | Existing `backfill_kalshi_resolved()` loop — just fix the cursor advance logic | Current code breaks when `len(batch) == 100` but there are exactly 100 remaining records (off-by-one); use explicit `cursor` field from response if available |
| Quality badge computation | Custom threshold logic | `sharpedge_models.walk_forward.quality_badge_from_windows()` | Already accounts for window count, OOS win rate, ROI thresholds |
| Platt calibration | Custom sigmoid fit | `sharpedge_models.calibration_store.CalibrationStore.update()` | Already handles all edge cases including single-class folds |
| Category feature assembly | Custom feature extraction | `sharpedge_models.pm_feature_assembler.PMFeatureAssembler.assemble()` | Handles all 5 categories, fallback defaults, never raises |

**Key insight:** Every reusable component for this phase already exists. The work is plumbing (swap storage layers, add preflight, add one report field) — not new ML logic.

---

## Common Pitfalls

### Pitfall 1: Kalshi Cursor Pagination Off-by-One

**What goes wrong:** Current `download_pm_historical.py` advances cursor using `batch[-1].ticker`. If exactly 100 markets remain on the last page, `len(batch) < 100` is False, so the loop tries to fetch page N+1 which returns empty — then breaks. This is correct behavior. However, if the Kalshi API returns a next-cursor field in the response, using the ticker as cursor may be incorrect.

**Why it happens:** The Phase 9 implementation used ticker as a proxy cursor. The actual Kalshi API may return a `cursor` field in the response envelope.

**How to avoid:** Check `KalshiClient.get_markets()` return signature. If the API response includes a pagination cursor field, use that instead of the last ticker. If not present, the ticker approach is acceptable.

**Warning signs:** Fetching far fewer markets than expected; duplicate markets in consecutive pages.

### Pitfall 2: `resolved_pm_markets` Schema Mismatch Between Sources

**What goes wrong:** Kalshi rows have `ticker`, `event_ticker`, `yes_bid`, `yes_ask`, `result` (string: "yes"/"no"). Polymarket rows have `condition_id`, `question`, `volume`, `liquidity`, `resolved_yes` (int: 0/1). A single table must accommodate both.

**Why it happens:** The two sources have different schemas. If columns are not normalized before insert, the Supabase upsert will fail or produce NULL-heavy rows.

**How to avoid:** Define the `resolved_pm_markets` table with a shared canonical schema. Map source-specific fields to canonical equivalents at insert time:
- `market_id` = ticker (Kalshi) or condition_id (Polymarket)
- `title` = title (Kalshi) or question (Polymarket)
- `market_prob` = (yes_bid + yes_ask) / 2 (Kalshi) or last price from outcomes (Polymarket)
- `resolved_yes` = 1 if result=="yes" (Kalshi) or resolved_yes field (Polymarket)
- `source` = "kalshi" or "polymarket"
- `volume` = volume from both (numeric)

**Warning signs:** KeyError on INSERT; NULL calibration features in processed DataFrames.

### Pitfall 3: process_pm_historical.py Still Reading Parquet After Migration

**What goes wrong:** The script currently checks for `kalshi_resolved.parquet` existence and reads it. After migration, no parquet is written by the download script. If the check is not updated, the process script will silently produce empty DataFrames.

**Why it happens:** The migration changes what the download script writes but the process script's data source is unchanged until explicitly updated.

**How to avoid:** Update `process_pm_historical.py::main()` to query `resolved_pm_markets` table via Supabase. The existing `_build_feature_row()` and `_process_raw()` functions can be adapted: instead of iterating `pd.read_parquet(raw_path).iterrows()`, iterate rows fetched from Supabase.

**Warning signs:** No processed parquet files in `data/processed/prediction_markets/`; training script reports no data for any category.

### Pitfall 4: Calibration Score Missing from Low-Data Categories

**What goes wrong:** If `oof_probs` is empty (e.g., single-class folds prevented OOF computation), computing `brier_score_loss(oof_actuals, oof_probs)` will raise a ValueError.

**Why it happens:** `train_pm_models.py::_run_walk_forward()` already handles this: it skips windows where `len(set(y_tr.tolist())) < 2`. If all windows are skipped, `oof_probs` is `[]`.

**How to avoid:** Guard the calibration score computation: `calibration_score = brier_score_loss(oof_actuals, oof_probs) if oof_probs and oof_actuals else None`. Write `None` (serializes as JSON `null`) into the report entry.

**Warning signs:** `ValueError: Found input variables with inconsistent numbers of samples` from sklearn.

### Pitfall 5: Offline Mode Breaking Existing Tests

**What goes wrong:** Tests in `tests/unit/scripts/test_download_pm_historical.py` rely on offline mode (fixture parquet). If offline mode is removed or broken by the preflight change, 8 existing tests will fail.

**Why it happens:** The preflight hard-exit must only trigger in production mode (when `KALSHI_API_KEY` is present). The offline fallback (`_is_kalshi_offline()`) must remain intact for tests.

**How to avoid:** Preflight runs ONLY when `offline=False` AND credentials are present. The `--offline` flag continues to bypass all API calls. The auto-detection (no `KALSHI_API_KEY` → offline) behavior stays. The change is: when `KALSHI_API_KEY` is present but auth fails, hard exit rather than silently continuing.

**Warning signs:** All 8 existing `test_backfill_kalshi_*` tests fail; `SystemExit` raised during test runs.

---

## Code Examples

Verified patterns from existing codebase:

### Supabase Upsert Pattern (from ledger.py)
```python
# Source: packages/venue_adapters/src/sharpedge_venue_adapters/ledger.py
result = self._supabase.table("ledger_entries").insert(row).execute()

# For upsert-on-conflict (resolved_pm_markets):
result = client.table("resolved_pm_markets").upsert(
    row, on_conflict="market_id,source"
).execute()
```

### Supabase SELECT Pattern (for process_pm_historical.py)
```python
# Standard supabase-py query pattern
client = get_supabase_client()
response = client.table("resolved_pm_markets").select("*").execute()
rows = response.data  # list of dicts
df = pd.DataFrame(rows)
```

### Kalshi Cursor Pagination (from download_pm_historical.py)
```python
# Source: scripts/download_pm_historical.py — existing pattern
cursor: str | None = None
while True:
    batch = await client.get_markets(status="settled", limit=100, cursor=cursor)
    if not batch:
        break
    all_markets.extend(batch)
    if len(batch) < 100:
        break
    cursor = batch[-1].ticker
```

### Training Report Structure (from train_pm_models.py)
```python
# Source: scripts/train_pm_models.py — existing _write_entry() dict
# Current:
{"category": category, "skipped": False, "badge": badge, "market_count": len(df), "model_path": str(model_path)}

# Required for TRAIN-04 (add calibration_score):
{
    "category": category,
    "skipped": False,
    "badge": badge,
    "market_count": len(df),
    "calibration_score": float(brier_score_loss(oof_actuals, oof_probs)) if oof_probs else None,
    "model_path": str(model_path),
}
```

### resolved_pm_markets DDL (new migration)
```sql
-- packages/database/src/sharpedge_db/migrations/006_resolved_pm_markets.sql
CREATE TABLE IF NOT EXISTS resolved_pm_markets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    market_id TEXT NOT NULL,
    source TEXT NOT NULL,             -- 'kalshi' or 'polymarket'
    title TEXT,
    category TEXT,
    market_prob DECIMAL,
    bid_ask_spread DECIMAL,
    last_price DECIMAL,
    volume DECIMAL,
    open_interest DECIMAL,
    days_to_close INTEGER,
    resolved_yes INTEGER NOT NULL,    -- 1 or 0
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(market_id, source)
);

CREATE INDEX IF NOT EXISTS idx_resolved_pm_category ON resolved_pm_markets(category);
CREATE INDEX IF NOT EXISTS idx_resolved_pm_source ON resolved_pm_markets(source);

ALTER TABLE resolved_pm_markets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access to resolved_pm_markets"
ON resolved_pm_markets FOR ALL TO service_role USING (true);
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Write resolved markets to parquet | Upsert to Supabase `resolved_pm_markets` | Phase 10 | Enables SQL queries in Phase 13 ablation; removes local file dependency |
| Download script silently falls back to fixtures | Hard exit with actionable message when credentials present but auth fails | Phase 10 | Prevents silent training on fixture data in production |
| Training report omits calibration score | Report includes `calibration_score` (Brier score) per category | Phase 10 | TRAIN-04 compliance; Phase 13 can gate on calibration quality |

**Deprecated/outdated:**
- `data/raw/prediction_markets/kalshi_resolved.parquet`: After migration, this file is no longer the authoritative data source for processing. The fixture at `data/raw/prediction_markets/fixtures/kalshi_sample.json` remains for test-only offline mode.
- `data/raw/prediction_markets/polymarket_resolved.parquet`: Same — superseded by Supabase for production; fixture DataFrame in `_build_polymarket_fixture()` retained for tests.

---

## Open Questions

1. **Kalshi API cursor field availability**
   - What we know: `KalshiClient.get_markets()` returns `list[KalshiMarket]` — a list of dataclass objects. The raw HTTP response envelope may include a `cursor` field not surfaced in the dataclass.
   - What's unclear: Whether the Kalshi API returns a proper pagination cursor in the response, or whether the ticker-based cursor approach is officially supported.
   - Recommendation: Check `kalshi_client.py::get_markets()` implementation for how the cursor is forwarded. If the current implementation passes the cursor to the API and gets back the next page correctly, the existing approach works. If the Kalshi API requires a cursor from the response envelope, `KalshiClient.get_markets()` needs to expose it.

2. **Polymarket Gamma API volume filter field name**
   - What we know: `PolymarketMarket` has a `.volume` field. The volume filter is `volume > 100 USDC`.
   - What's unclear: Whether `.volume` is in USDC or shares/contracts. If it is shares, the threshold may need adjustment.
   - Recommendation: Check `polymarket_client.py` to verify the unit. If the unit is confirmed USDC, 100 is appropriate. Document the unit assumption in the filter code.

3. **CalibrationStore calibration score field name**
   - What we know: `CalibrationStore.update()` writes a calibration artifact. The training report needs a scalar `calibration_score`.
   - What's unclear: Whether `CalibrationStore` exposes a summary score or only the fitted calibrator object.
   - Recommendation: Use `brier_score_loss(oof_actuals, oof_probs)` directly from the walk-forward OOF arrays — this is already computed in `train_pm_models.py::train_category()`. No need to read back from `CalibrationStore`.

---

## Validation Architecture

> nyquist_validation is enabled (config.json: `"nyquist_validation": true`)

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24 + pytest-mock 3.14 |
| Config file | `pyproject.toml` (pytest section) |
| Quick run command | `python -m pytest tests/unit/scripts/ -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TRAIN-01 | `download_pm_historical.py` writes to Supabase `resolved_pm_markets` (live mode) | unit (mock Supabase) | `pytest tests/unit/scripts/test_download_pm_historical.py -x -q` | Partially — existing tests cover parquet write; new tests needed for Supabase upsert |
| TRAIN-01 | Preflight exits with error when credentials present but Kalshi auth fails | unit | Same file | ❌ Wave 0 |
| TRAIN-01 | Polymarket volume filter excludes markets with volume <= 100 | unit | Same file | ❌ Wave 0 |
| TRAIN-02 | `process_pm_historical.py` reads from Supabase `resolved_pm_markets` | unit (mock Supabase) | `pytest tests/unit/scripts/test_process_pm_historical.py -x -q` | Partially — existing tests cover parquet read path |
| TRAIN-03 | `train_pm_models.py` writes per-category `.joblib` to `data/models/pm/` | unit | `pytest tests/unit/scripts/test_train_pm_models.py -x -q` | ✅ (xfail stubs — become GREEN after implementation) |
| TRAIN-04 | Training report JSON contains `quality_badge`, `calibration_score`, `market_count` per category | unit | Same file | Partially — badge and market_count tested; calibration_score missing |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/unit/scripts/ -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/scripts/test_download_pm_historical.py` — add test: Supabase upsert called when `SUPABASE_URL` is set (mock `supabase.create_client`); covers TRAIN-01 storage migration
- [ ] `tests/unit/scripts/test_download_pm_historical.py` — add test: preflight exits with `SystemExit` when `KALSHI_API_KEY` present but `get_markets` raises; covers TRAIN-01 credential check
- [ ] `tests/unit/scripts/test_download_pm_historical.py` — add test: Polymarket markets with `volume <= 100` are excluded from upsert; covers TRAIN-01 volume filter
- [ ] `tests/unit/scripts/test_process_pm_historical.py` — add test: main() queries Supabase when `SUPABASE_URL` set (mock client); covers TRAIN-02 storage migration
- [ ] `tests/unit/scripts/test_train_pm_models.py` — update xfail stubs to GREEN once `train_category()` is verified functional; add test: report entry contains `calibration_score` key when OOF data available; covers TRAIN-04
- [ ] `packages/database/src/sharpedge_db/migrations/006_resolved_pm_markets.sql` — create DDL; required before any Supabase upsert can work

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `scripts/download_pm_historical.py` — current parquet write pattern, offline mode logic, cursor pagination
- Direct code inspection of `scripts/process_pm_historical.py` — current parquet read path, `_process_raw()`, `_build_feature_row()`
- Direct code inspection of `scripts/train_pm_models.py` — `train_category()`, `_run_walk_forward()`, report structure
- Direct code inspection of `packages/venue_adapters/src/sharpedge_venue_adapters/ledger.py` — dual-mode Supabase/in-memory pattern
- Direct code inspection of `packages/models/src/sharpedge_models/pm_feature_assembler.py` — `PM_CATEGORIES`, feature vector contracts
- Direct code inspection of `packages/models/src/sharpedge_models/pm_resolution_predictor.py` — `PM_MODEL_DIR`, artifact loading
- Direct code inspection of `packages/database/src/sharpedge_db/client.py` — Supabase singleton pattern
- Direct code inspection of `packages/database/src/sharpedge_db/migrations/003_prediction_markets.sql` — existing PM migration precedent
- Direct code inspection of `tests/unit/scripts/test_download_pm_historical.py` — existing test coverage
- Direct code inspection of `tests/unit/scripts/test_train_pm_models.py` — xfail stubs from Phase 9
- `.planning/phases/10-training-pipeline-validation/10-CONTEXT.md` — all locked decisions

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` — TRAIN-01 through TRAIN-04 definitions
- `.planning/ROADMAP.md` — Phase 10 success criteria, phase dependencies

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already in use in the project; no new packages
- Architecture: HIGH — dual-mode pattern is directly observed in `SettlementLedger`; Supabase DDL follows established migration conventions
- Pitfalls: HIGH — derived from direct code inspection of the existing scripts and their known gaps (offline mode preservation, schema mismatch, cursor pagination)

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable domain — Supabase API and scikit-learn patterns are stable; Kalshi API auth scheme may change but is unlikely within 30 days)
