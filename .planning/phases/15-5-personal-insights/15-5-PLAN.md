# Phase 15.5 — Personal insights & bet logging (competitor-parity hooks)

**Milestone:** v3.0 Launch & Distribution  
**Inserted after:** Phase 15 (arb scanner), **before** Phase 17 (web deployment) — does not replace auth Phase 16.  
**Goal:** Close the loop on **personal P&amp;L** and **bet logging** using existing schema (`bets`, `users`, `value_plays`, `injuries`) without new design systems or heavy mobile nav.

## Plans

| # | Plan | Status |
|---|------|--------|
| 01 | `POST /api/v1/bets` + portfolio/history correctness | Complete |
| 02 | Portfolio API/UI breakdowns (book, bet type, odds bucket) + optional unit display | Complete |
| 03 | Game analysis: injuries strip from `injuries` table | Complete |

## Success criteria (phase)

1. Authenticated mobile/web client can **log a bet** tied to a `value_play` id; rows land on `bets` with correct internal `user_id`.
2. **Portfolio** reflects **pending** active bets and **CLV** fields when present.
3. No new top-level mobile tab; web reuses existing dashboard layout.

## References

- Schema: `packages/database/src/sharpedge_db/migrations/001_initial_schema.sql`, `002_analytics_tables.sql`, `008_auth_bridge.sql`
- Prior notes: `.planning/codebase/ARCHITECTURE.md` (API surfaces)
