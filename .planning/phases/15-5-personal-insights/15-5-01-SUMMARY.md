# 15.5 Plan 01 — Summary

**Completed:** 2026-03-21

## Delivered

- **`POST /api/v1/bets`** (`apps/webhook_server/.../routes/v1/bets.py`): Auth JWT → internal `users.id` via `get_internal_user_id_by_supabase_auth`; loads `get_value_play`; validates `event` matches play; derives `units` from `get_unit_size_for_user` (fallback `$50` unit); `create_bet` with `notes=value_play_id=…`. **201 Created**; body matches Flutter `logBet`.
- **`get_unit_size_for_user`** in `packages/database/.../queries/users.py`.
- **`get_user_bets_history`**: includes **pending** bets, `created_at` desc, adds `sportsbook`, `clv_points`, `clv` alias.
- **Portfolio**: `_is_pending_result` for `PENDING` / `pending`; active bets and CLV use new fields.
- **Mobile `/api/bankroll`**: pending count uses case-insensitive `PENDING`.
- **Tests**: `test_bets_log.py`; portfolio mock updated to `PENDING`.
- **Ruff**: `bets.py` datetime imports modernized to `UTC` (auto-fix).

## Verify

`uv run pytest apps/webhook_server/tests/unit/api/ -q` → 35 passed (as of run).
