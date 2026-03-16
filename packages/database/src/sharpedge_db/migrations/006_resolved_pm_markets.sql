-- Migration 006: Resolved Prediction Market Markets
-- Canonical table for resolved Kalshi and Polymarket markets used in PM resolution model training

-- ============================================
-- RESOLVED PM MARKETS TABLE
-- One row per resolved market across all platforms.
-- source column ('kalshi' or 'polymarket') scopes market_id to prevent
-- cross-platform collisions; UNIQUE(market_id, source) is the upsert key.
-- ============================================
CREATE TABLE IF NOT EXISTS resolved_pm_markets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    market_id TEXT NOT NULL,
    source TEXT NOT NULL,              -- 'kalshi' or 'polymarket'
    title TEXT,
    category TEXT,
    market_prob DECIMAL,               -- implied probability at close (0-1)
    bid_ask_spread DECIMAL,            -- yes_ask - yes_bid for Kalshi; null for Polymarket
    last_price DECIMAL,                -- last traded price (0-1)
    volume DECIMAL,
    open_interest DECIMAL,
    days_to_close INTEGER,             -- days between listing and resolution
    resolved_yes INTEGER NOT NULL,     -- 1 = resolved YES, 0 = resolved NO
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(market_id, source)
);

CREATE INDEX IF NOT EXISTS idx_resolved_pm_category ON resolved_pm_markets (category);
CREATE INDEX IF NOT EXISTS idx_resolved_pm_source ON resolved_pm_markets (source);

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================
ALTER TABLE resolved_pm_markets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access to resolved_pm_markets"
ON resolved_pm_markets FOR ALL TO service_role USING (true);
