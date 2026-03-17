---
phase: 10-training-pipeline-validation
verified: 2026-03-15T00:00:00Z
status: human_needed
score: 6/8 must-haves verified
human_verification:
  - test: "Run python scripts/download_pm_historical.py with live KALSHI_API_KEY + KALSHI_PRIVATE_KEY_PEM + SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY set. Confirm exit code 0 and log shows row count upserted to resolved_pm_markets."
    expected: "Script completes without error; Supabase receives resolved market rows from both Kalshi and Polymarket."
    why_human: "Requires live API credentials. Cursor exhaustion takes minutes. Cannot mock end-to-end backfill in automated tests."
  - test: "Run python scripts/train_pm_models.py after the backfill has populated resolved_pm_markets. Inspect data/models/pm/ directory."
    expected: "One or more .joblib files exist in data/models/pm/ for categories with >= 200 resolved markets (exact set depends on live data volume)."
    why_human: "Artifact existence depends on real training data being present in Supabase. No .joblib files exist in data/models/pm/ yet — directory does not exist."
  - test: "After train_pm_models.py completes, open data/models/pm/training_report.json."
    expected: "JSON contains one entry per trained category. Each entry has keys: category, badge, market_count, calibration_score (float or null), model_path. No entry has skipped=true for categories with >= 200 markets."
    why_human: "Report content depends on live training run with real data. File does not exist yet."
---

# Phase 10: Training Pipeline Validation — Verification Report

**Phase Goal:** Per-category `.joblib` RandomForest artifacts exist, are calibrated, and the training report confirms quality — so Phase 11 has real models to gate against.
**Verified:** 2026-03-15
**Status:** human_needed — all automated checks pass; 3 items require live credentials to verify
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | resolved_pm_markets DDL exists with UNIQUE(market_id, source) and RLS | VERIFIED | `packages/database/src/sharpedge_db/migrations/006_resolved_pm_markets.sql` line 26: `UNIQUE(market_id, source)`; line 35: `ENABLE ROW LEVEL SECURITY` |
| 2 | download_pm_historical.py has Supabase upsert path and Kalshi preflight sys.exit | VERIFIED | Lines 52-56: `_get_supabase_client()`; line 149: `sys.exit`; lines 184, 267: `upsert(row, on_conflict="market_id,source")` |
| 3 | Polymarket backfill excludes markets with volume <= 100 | VERIFIED | Line 234-235: `all_markets = [m for m in all_markets if getattr(m, "volume", 0) > 100]` |
| 4 | process_pm_historical.py reads from resolved_pm_markets Supabase SELECT in main() | VERIFIED | Line 99: `client.table("resolved_pm_markets").select("*").execute()`; line 164: `if os.environ.get("SUPABASE_URL")` guards Supabase path in main() |
| 5 | train_pm_models.py writes calibration_score to report entries | VERIFIED | Lines 122-127: `brier_score_loss` computation with length guard; line 129: `_write_entry({..., "calibration_score": calibration_score, ...})`; line 106: `quality_below_minimum` entry includes `calibration_score: None` |
| 6 | All 24 scripts unit tests pass with no xfail markers remaining | VERIFIED | `24 passed, 1 warning in 5.24s` — confirmed live test run; no `@pytest.mark.xfail` found in any of the 3 test files |
| 7 | `.joblib` artifacts exist in data/models/pm/ per trained category | NEEDS HUMAN | `data/models/pm/` directory does not exist. VALIDATION.md classifies this as manual-only — requires live backfill + training run with credentials. |
| 8 | training_report.json exists with badge, calibration_score, and market_count per category | NEEDS HUMAN | File does not exist. Depends on live training run. VALIDATION.md classifies this as manual-only. |

**Score:** 6/8 truths verified (2 require human verification with live credentials)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/database/src/sharpedge_db/migrations/006_resolved_pm_markets.sql` | DDL with UNIQUE(market_id, source) + RLS | VERIFIED | 39 lines; CREATE TABLE, UNIQUE constraint, 2 indexes, RLS policy — all present |
| `scripts/download_pm_historical.py` | Supabase upsert + preflight + volume filter | VERIFIED | Contains `_get_supabase_client`, `sys.exit` preflight, Polymarket volume filter, upsert calls |
| `scripts/process_pm_historical.py` | Supabase SELECT in main() | VERIFIED | `_get_resolved_pm_from_supabase()` and `_process_supabase_df()` present; main() branches on `SUPABASE_URL` |
| `scripts/train_pm_models.py` | calibration_score in report entries | VERIFIED | `brier_score_loss` imported; calibration_score computed and written in both success and quality_below_minimum entries |
| `tests/unit/scripts/test_download_pm_historical.py` | >= 260 lines; 3 Wave 0 tests present | VERIFIED | 332 lines; `test_backfill_kalshi_upserts_to_supabase_when_url_set`, `test_kalshi_preflight_exits_on_auth_failure`, `test_polymarket_volume_filter_excludes_low_volume` all present |
| `tests/unit/scripts/test_process_pm_historical.py` | >= 120 lines; Supabase test + xfail removed | VERIFIED | 137 lines; `test_main_queries_supabase_when_url_set` present; no `@pytest.mark.xfail` markers |
| `tests/unit/scripts/test_train_pm_models.py` | >= 110 lines; calibration_score test + xfail removed | VERIFIED | 140 lines; `test_train_category_report_includes_calibration_score` present; no `@pytest.mark.xfail` markers |
| `scripts/__init__.py` | Makes scripts/ importable as Python package | VERIFIED | File exists; unblocks all `from scripts.X import Y` in test suite |
| `data/models/pm/*.joblib` | Per-category RandomForest artifacts | NEEDS HUMAN | Directory does not exist. Requires live backfill + training run. |
| `data/models/pm/training_report.json` | JSON with badge + calibration_score + market_count | NEEDS HUMAN | File does not exist. Requires live training run. |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/unit/scripts/test_download_pm_historical.py` | `scripts/download_pm_historical.py` | `from scripts.download_pm_historical import backfill_kalshi_resolved` | WIRED | Import confirmed at 14 test sites in the file |
| `scripts/download_pm_historical.py` | `resolved_pm_markets` Supabase table | `upsert(row, on_conflict="market_id,source")` | WIRED | Lines 184 and 267 call upsert on the table; guarded by `_get_supabase_client()` check |
| `scripts/process_pm_historical.py` | `resolved_pm_markets` Supabase table | `client.table("resolved_pm_markets").select("*").execute()` | WIRED | Line 99; called from `_get_resolved_pm_from_supabase()` which is invoked in `main()` |
| `scripts/train_pm_models.py` | `data/models/pm/{category}.joblib` | `joblib.dump(final_clf, model_path)` | WIRED (code path exists) | Line 113: `joblib.dump(final_clf, model_path)`; artifacts not yet written because live data has not been processed |
| `scripts/train_pm_models.py` | `data/models/pm/training_report.json` | `_write_entry()` with calibration_score | WIRED (code path exists) | Lines 106, 129: both `_write_entry()` calls include `calibration_score` key; file not yet written for same reason |
| `packages/database/src/sharpedge_db/migrations/006_resolved_pm_markets.sql` | Supabase `resolved_pm_markets` table | migration runner | NEEDS HUMAN | SQL file correct; human must apply migration to Supabase instance before live run works |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TRAIN-01 | 10-01, 10-02 | Operator can run `download_pm_historical.py` against live Kalshi + Polymarket APIs without error | NEEDS HUMAN | Code path fully implemented and tested offline; live end-to-end requires credentials |
| TRAIN-02 | 10-01, 10-02 | Operator can run `process_pm_historical.py` and receive per-category feature DataFrames | NEEDS HUMAN | Supabase SELECT path implemented; offline parquet path tested; live path untested without credentials |
| TRAIN-03 | 10-01, 10-03 | Operator can run `train_pm_models.py` and receive `.joblib` files per category | NEEDS HUMAN | `joblib.dump` wired at line 113; no `.joblib` files exist yet — requires live data |
| TRAIN-04 | 10-01, 10-03 | Training report JSON contains quality badge, calibration score, market count per category | PARTIAL | `calibration_score` key confirmed in code at lines 106, 129; report JSON does not exist yet |

All 4 requirements from REQUIREMENTS.md are accounted for. No orphaned requirements.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

The two `return []` calls in `scripts/process_pm_historical.py` (lines 95, 103) are appropriate guard returns in `_get_resolved_pm_from_supabase()` — not stubs. First guards against missing credentials; second handles Supabase connection errors gracefully.

---

## Commit Verification

All 5 task commits confirmed in git history:
- `b72e025` — feat(10-01): create resolved_pm_markets migration DDL
- `cdcb9db` — test(10-01): add Wave 0 test coverage for TRAIN-01 through TRAIN-04
- `a0945ee` — feat(10-02): migrate download_pm_historical.py
- `990535d` — feat(10-02): migrate process_pm_historical.py
- `f2b2a7f` — feat(10-03): add calibration_score to train_pm_models report entries

---

## Human Verification Required

### 1. Live Backfill — End-to-End Download

**Test:** With `KALSHI_API_KEY`, `KALSHI_PRIVATE_KEY_PEM`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` in environment, apply migration 006 to Supabase, then run `python scripts/download_pm_historical.py`.
**Expected:** Exit code 0; log output shows rows upserted to `resolved_pm_markets` from both Kalshi (all resolved markets) and Polymarket (volume > 100 only).
**Why human:** Requires live credentials. Cursor exhaustion is a multi-minute network operation. Cannot mock in automated tests.

### 2. Per-Category .joblib Artifacts

**Test:** After live backfill, run `python scripts/process_pm_historical.py` then `python scripts/train_pm_models.py`. Inspect `data/models/pm/` directory.
**Expected:** One `.joblib` file per category that has >= 200 resolved markets and achieves at least `medium` quality badge. Directory may be empty for categories below threshold — that is acceptable per CONTEXT.md.
**Why human:** Artifact existence depends on real data volume in Supabase. No `.joblib` files exist at time of verification. The training code path is fully wired (`joblib.dump` at line 113 of `train_pm_models.py`) — just needs live data.

### 3. Training Report JSON Schema

**Test:** Open `data/models/pm/training_report.json` after training completes.
**Expected:** Valid JSON array/object with one entry per trained category. Each entry contains `badge` (string), `calibration_score` (float or null), `market_count` (int), `model_path` (string), `skipped` (false). Categories below threshold have `skipped: true` with no `model_path`.
**Why human:** File does not exist until live training run completes.

---

## Gaps Summary

No automated-verifiable gaps found. All code is substantive (no stubs or placeholder returns), all key links are wired, and all test artifacts pass at the expected line counts.

The 2 unverified truths (`.joblib` artifacts and `training_report.json`) are not implementation gaps — the code is complete and the write paths are wired. These are operational gaps: the live backfill has not been executed against real Kalshi/Polymarket APIs. The VALIDATION.md and CONTEXT.md for Phase 10 explicitly classify these as manual-only verifications requiring live credentials.

Phase 11 can proceed once one of the following is satisfied:
- A human operator runs the pipeline end-to-end with live credentials and confirms `.joblib` files exist in `data/models/pm/`, OR
- Phase 11 is designed to tolerate a missing `data/models/pm/` directory (per CONTEXT.md note: "Categories below the 200-market minimum are skipped... Untrained categories fall back to fee-adjusted probability in `scan_pm_edges()`").

---

_Verified: 2026-03-15_
_Verifier: Claude (gsd-verifier)_
