# Copilot checkpoint retention (LangGraph + Postgres)

Short reference for operators: **checkpoint** row growth, **retention** / TTL-style cleanup, and Supabase **RLS** (optional).

## Tables (`langgraph-checkpoint-postgres`)

`AsyncPostgresSaver.setup()` creates (see upstream `langgraph.checkpoint.postgres.base.MIGRATIONS`):

| Table | Role |
|-------|------|
| `checkpoint_migrations` | Schema version |
| `checkpoints` | Thread checkpoint JSON (`thread_id`, `checkpoint_id`, …) |
| `checkpoint_blobs` | Binary channel blobs per thread |
| `checkpoint_writes` | Pending writes per checkpoint step |

Indexes exist on `thread_id` for the main tables.

## Retention / TTL

There is **no built-in TTL** in the saver; growth is bounded by **policy + maintenance**:

1. **Product policy** — align with Phase 2 commercial memory expectations (see `.planning/COPILOT-COMMERCIAL-ROADMAP.md` Phase 2).
2. **Optional scheduled job** — e.g. weekly `DELETE` rows older than N days for **stale** `thread_id` keys you define as abandoned (requires a rule: last activity timestamp in `metadata` if you add it, or delete by `thread_id` prefix patterns for test data only).
3. **`VACUUM ANALYZE`** on the checkpoint tables after large deletes to reclaim space.

Example **illustrative** cleanup (adjust predicates; run in a maintenance window; test on a copy first):

```sql
-- Example only: delete checkpoints for one thread (application-defined id).
-- DELETE FROM checkpoint_writes WHERE thread_id = '...';
-- DELETE FROM checkpoint_blobs WHERE thread_id = '...';
-- DELETE FROM checkpoints WHERE thread_id = '...';
-- VACUUM ANALYZE checkpoints;
```

Do **not** store secrets in this repo; use Supabase SQL editor or CI with injected credentials.

## RLS (Supabase)

Row Level Security on these tables is **operator choice** in the Supabase UI. The webhook server uses a **service** role today for the checkpointer; if you enable RLS, ensure the checkpointer role retains required CRUD or use a dedicated DB role.

## Related

- Commercial roadmap: `.planning/COPILOT-COMMERCIAL-ROADMAP.md` (Phase 2 memory, Phase 7 hardening).
