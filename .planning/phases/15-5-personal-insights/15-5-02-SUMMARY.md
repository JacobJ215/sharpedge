# 15.5 Plan 02 — Summary

**Completed:** 2026-03-21

## API (`GET /api/v1/users/{id}/portfolio`)

- **`unit_size`**: dollars per unit from `get_unit_size_for_user` (0 if unset).
- **`by_sport`**: settled bets — `sport`, `total_bets`, `wins`, `losses`, `win_rate`, `roi` (reuses `get_breakdown_by_sport`).
- **`by_bet_type`**: same shape via `get_breakdown_by_bet_type`.
- **`by_book`**: new `get_breakdown_by_sportsbook` — `sportsbook` (or `"(none)"`).
- **`by_juice`**: new `get_breakdown_by_juice_bucket` + `american_odds_juice_bucket()` buckets: `<= -150`, `-149 to -110`, `-109 to +100`, `+101 to +200`, `>= +201`.

`load_portfolio_breakdowns()` is patchable in tests alongside `get_unit_size_for_user`.

## Web

- `apps/web/src/lib/api.ts` — `Portfolio` extended with breakdown types.
- `apps/web/src/components/portfolio/breakdown-tables.tsx` — compact tables under “Performance splits”.
- `apps/web/src/app/(dashboard)/portfolio/page.tsx` — renders breakdown block after `StatsCards`.

## Verify

- `uv run pytest apps/webhook_server/tests/unit/api/test_portfolio.py -q`
- `uv run ruff check` on touched Python paths
- `npx vitest run src/test/bankroll.test.tsx` (targeted; full web suite has unrelated auth failures)
