-- ============================================================
-- SharpEdge — Supabase Row-Level Security Migration
-- ============================================================
-- Run with service_role privileges via Supabase SQL editor or:
--   psql $DATABASE_URL < scripts/schema_rls.sql
--
-- MIGRATION PENDING if applied without DB access:
--   run this script via Supabase SQL editor or psql before
--   deploying portfolio/device-token routes.
-- ============================================================


-- ----------------------------------------------------------
-- 1. Enable RLS on all user-scoped tables
-- ----------------------------------------------------------

ALTER TABLE bets ENABLE ROW LEVEL SECURITY;

ALTER TABLE user_bankroll ENABLE ROW LEVEL SECURITY;

ALTER TABLE value_plays ENABLE ROW LEVEL SECURITY;


-- ----------------------------------------------------------
-- 2. RLS policies for bets (user owns their own bets)
-- ----------------------------------------------------------

-- Drop existing policies if re-running migration
DROP POLICY IF EXISTS "user_own_bets" ON bets;
DROP POLICY IF EXISTS "service_role_all_bets" ON bets;

CREATE POLICY "user_own_bets"
    ON bets
    FOR ALL
    USING (auth.uid() = user_id);

CREATE POLICY "service_role_all_bets"
    ON bets
    FOR ALL
    TO service_role
    USING (true);


-- ----------------------------------------------------------
-- 3. RLS policies for user_bankroll (user owns their bankroll)
-- ----------------------------------------------------------

DROP POLICY IF EXISTS "user_own_bankroll" ON user_bankroll;
DROP POLICY IF EXISTS "service_role_all_bankroll" ON user_bankroll;

CREATE POLICY "user_own_bankroll"
    ON user_bankroll
    FOR ALL
    USING (auth.uid() = user_id);

CREATE POLICY "service_role_all_bankroll"
    ON user_bankroll
    FOR ALL
    TO service_role
    USING (true);


-- ----------------------------------------------------------
-- 4. RLS policies for value_plays (shared game data — service_role only write)
-- ----------------------------------------------------------

DROP POLICY IF EXISTS "public_read_value_plays" ON value_plays;
DROP POLICY IF EXISTS "service_role_write_value_plays" ON value_plays;

-- Authenticated users may read value_plays (shared market data)
CREATE POLICY "public_read_value_plays"
    ON value_plays
    FOR SELECT
    TO authenticated
    USING (true);

-- Only service_role may insert/update/delete
CREATE POLICY "service_role_write_value_plays"
    ON value_plays
    FOR ALL
    TO service_role
    USING (true);


-- ----------------------------------------------------------
-- 5. user_device_tokens table (FCM push notification tokens)
-- ----------------------------------------------------------

CREATE TABLE IF NOT EXISTS user_device_tokens (
    id          UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    fcm_token   TEXT        NOT NULL,
    platform    TEXT        NOT NULL CHECK (platform IN ('ios', 'android')),
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE (user_id, fcm_token)
);

ALTER TABLE user_device_tokens ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "user_own_device_tokens" ON user_device_tokens;
DROP POLICY IF EXISTS "service_role_all_device_tokens" ON user_device_tokens;

CREATE POLICY "user_own_device_tokens"
    ON user_device_tokens
    FOR ALL
    USING (auth.uid() = user_id);

CREATE POLICY "service_role_all_device_tokens"
    ON user_device_tokens
    FOR ALL
    TO service_role
    USING (true);


-- ----------------------------------------------------------
-- 6. Verification query (run after migration to confirm RLS)
-- ----------------------------------------------------------
-- SELECT relname, relrowsecurity
-- FROM pg_class
-- WHERE relname IN ('bets', 'user_bankroll', 'user_device_tokens');
-- Expected: relrowsecurity = true for all three rows.
