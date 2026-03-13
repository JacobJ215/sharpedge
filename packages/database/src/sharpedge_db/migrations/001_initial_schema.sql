-- SharpEdge Initial Schema
-- Run this against your Supabase project's SQL editor

-- ============================================================
-- TABLES
-- ============================================================

-- Users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    discord_id VARCHAR(255) UNIQUE NOT NULL,
    discord_username VARCHAR(255),
    tier VARCHAR(50) DEFAULT 'free',
    subscription_id VARCHAR(255),
    bankroll DECIMAL(12, 2) DEFAULT 0,
    unit_size DECIMAL(10, 2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bets
CREATE TABLE IF NOT EXISTS bets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- Bet Details
    sport VARCHAR(50) NOT NULL,
    league VARCHAR(100),
    game VARCHAR(255) NOT NULL,
    bet_type VARCHAR(50) NOT NULL,
    selection VARCHAR(255) NOT NULL,

    -- Odds & Stakes
    odds INTEGER NOT NULL,
    units DECIMAL(4, 2) NOT NULL,
    stake DECIMAL(10, 2) NOT NULL,
    potential_win DECIMAL(10, 2) NOT NULL,

    -- Line Tracking
    opening_line DECIMAL(6, 2),
    line_at_bet DECIMAL(6, 2),
    closing_line DECIMAL(6, 2),
    clv_points DECIMAL(4, 2),

    -- Result
    result VARCHAR(20) DEFAULT 'PENDING',
    profit DECIMAL(10, 2),

    -- Metadata
    sportsbook VARCHAR(100),
    notes TEXT,
    game_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    settled_at TIMESTAMPTZ
);

-- Usage Tracking (rate limiting)
CREATE TABLE IF NOT EXISTS usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    feature VARCHAR(100) NOT NULL,
    used_at TIMESTAMPTZ DEFAULT NOW()
);

-- Alerts Delivered
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL,
    game_id VARCHAR(255),
    content TEXT,
    delivered_at TIMESTAMPTZ DEFAULT NOW()
);

-- Model Projections (cache)
CREATE TABLE IF NOT EXISTS projections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id VARCHAR(255) UNIQUE NOT NULL,
    sport VARCHAR(50) NOT NULL,
    home_team VARCHAR(100),
    away_team VARCHAR(100),
    projected_spread DECIMAL(5, 2),
    projected_total DECIMAL(5, 2),
    spread_confidence DECIMAL(3, 2),
    total_confidence DECIMAL(3, 2),
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    game_time TIMESTAMPTZ
);

-- Odds History
CREATE TABLE IF NOT EXISTS odds_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id VARCHAR(255) NOT NULL,
    sportsbook VARCHAR(100) NOT NULL,
    bet_type VARCHAR(50) NOT NULL,
    line DECIMAL(6, 2),
    odds INTEGER,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_bets_user_id ON bets(user_id);
CREATE INDEX IF NOT EXISTS idx_bets_sport ON bets(sport);
CREATE INDEX IF NOT EXISTS idx_bets_result ON bets(result);
CREATE INDEX IF NOT EXISTS idx_bets_created_at ON bets(created_at);
CREATE INDEX IF NOT EXISTS idx_bets_user_sport ON bets(user_id, sport);
CREATE INDEX IF NOT EXISTS idx_bets_user_result ON bets(user_id, result);

CREATE INDEX IF NOT EXISTS idx_usage_user_feature ON usage(user_id, feature, used_at);

CREATE INDEX IF NOT EXISTS idx_alerts_user_type ON alerts(user_id, alert_type, delivered_at);

CREATE INDEX IF NOT EXISTS idx_odds_game_id ON odds_history(game_id);
CREATE INDEX IF NOT EXISTS idx_odds_recorded_at ON odds_history(recorded_at);
CREATE INDEX IF NOT EXISTS idx_odds_game_book ON odds_history(game_id, sportsbook, recorded_at);

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Auto-update updated_at on users table
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

-- Enable RLS on all tables (service key bypasses RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE bets ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE projections ENABLE ROW LEVEL SECURITY;
ALTER TABLE odds_history ENABLE ROW LEVEL SECURITY;

-- Service role can do everything (our bot uses service key)
CREATE POLICY "Service role full access on users"
    ON users FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on bets"
    ON bets FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on usage"
    ON usage FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on alerts"
    ON alerts FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on projections"
    ON projections FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on odds_history"
    ON odds_history FOR ALL
    USING (auth.role() = 'service_role');
