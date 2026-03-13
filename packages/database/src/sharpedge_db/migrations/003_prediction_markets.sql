-- Migration 003: Prediction Market Tables
-- Supports Kalshi, Polymarket, and cross-platform arbitrage

-- ============================================
-- PREDICTION MARKET CANONICAL EVENTS
-- Maps equivalent events across platforms
-- ============================================
CREATE TABLE IF NOT EXISTS pm_canonical_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,  -- 'crypto', 'politics', 'economics', 'sports', 'other'
    description TEXT NOT NULL,
    resolution_date TIMESTAMPTZ,
    resolution_source TEXT,
    resolution_criteria TEXT,
    equivalence_confidence DECIMAL DEFAULT 1.0,
    resolution_risk TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pm_events_type ON pm_canonical_events(event_type);
CREATE INDEX idx_pm_events_resolution ON pm_canonical_events(resolution_date);

-- ============================================
-- PREDICTION MARKET OUTCOMES
-- Individual market outcomes from each platform
-- ============================================
CREATE TABLE IF NOT EXISTS pm_market_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_event_id TEXT REFERENCES pm_canonical_events(canonical_id),
    platform TEXT NOT NULL,  -- 'kalshi', 'polymarket', 'polymarket_us', 'predictit'
    market_id TEXT NOT NULL,
    outcome_id TEXT NOT NULL,
    question TEXT NOT NULL,
    outcome_label TEXT NOT NULL,  -- 'Yes', 'No', or custom
    price DECIMAL NOT NULL,  -- 0-1 probability
    volume_24h DECIMAL DEFAULT 0,
    liquidity DECIMAL DEFAULT 0,
    resolution_source TEXT,
    resolution_criteria TEXT,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(platform, market_id, outcome_id)
);

CREATE INDEX idx_pm_outcomes_canonical ON pm_market_outcomes(canonical_event_id);
CREATE INDEX idx_pm_outcomes_platform ON pm_market_outcomes(platform);
CREATE INDEX idx_pm_outcomes_price ON pm_market_outcomes(price);

-- ============================================
-- PREDICTION MARKET ARBITRAGE OPPORTUNITIES
-- Cross-platform arb detections
-- ============================================
CREATE TABLE IF NOT EXISTS pm_arbitrage_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_event_id TEXT NOT NULL,
    event_description TEXT,
    event_type TEXT,

    -- Side A: Buy YES
    buy_yes_platform TEXT NOT NULL,
    buy_yes_price DECIMAL NOT NULL,

    -- Side B: Buy NO
    buy_no_platform TEXT NOT NULL,
    buy_no_price DECIMAL NOT NULL,

    -- Profit metrics
    gross_gap_pct DECIMAL NOT NULL,
    gross_profit_pct DECIMAL NOT NULL,
    net_profit_pct DECIMAL NOT NULL,

    -- Sizing
    stake_yes DECIMAL,
    stake_no DECIMAL,
    guaranteed_return DECIMAL,

    -- Risk assessment
    resolution_risk DECIMAL DEFAULT 0,
    equivalence_confidence DECIMAL DEFAULT 1.0,

    -- Timing
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    estimated_window_seconds INTEGER DEFAULT 30,
    expired_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,

    UNIQUE(canonical_event_id, buy_yes_platform, buy_no_platform)
);

CREATE INDEX idx_pm_arb_active ON pm_arbitrage_opportunities(is_active, net_profit_pct DESC);
CREATE INDEX idx_pm_arb_detected ON pm_arbitrage_opportunities(detected_at DESC);

-- ============================================
-- PREDICTION MARKET PRICE HISTORY
-- Track price movements for analysis
-- ============================================
CREATE TABLE IF NOT EXISTS pm_price_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,
    market_id TEXT NOT NULL,
    price DECIMAL NOT NULL,
    volume DECIMAL,
    captured_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pm_price_history ON pm_price_history(platform, market_id, captured_at DESC);

-- Partition by time for efficient queries (optional)
-- CREATE TABLE pm_price_history_2025 PARTITION OF pm_price_history
--     FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

-- ============================================
-- PLATFORM FEE CONFIGURATION
-- Store platform fee structures for calculations
-- ============================================
CREATE TABLE IF NOT EXISTS pm_platform_fees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL UNIQUE,
    taker_fee_pct DECIMAL NOT NULL DEFAULT 0,
    maker_fee_pct DECIMAL NOT NULL DEFAULT 0,
    settlement_fee_per_contract DECIMAL NOT NULL DEFAULT 0,
    withdrawal_fee DECIMAL NOT NULL DEFAULT 0,
    fee_formula TEXT,  -- Description of formula if complex
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default fee structures
INSERT INTO pm_platform_fees (platform, taker_fee_pct, maker_fee_pct, settlement_fee_per_contract, withdrawal_fee, fee_formula)
VALUES
    ('kalshi', 0.01, 0.0, 0.01, 2.0, '0.07 × contracts × price × (1-price)'),
    ('polymarket', 0.0, 0.0, 0.0, 0.50, 'No trading fees on standard markets'),
    ('polymarket_us', 0.001, 0.0, 0.0, 0.50, '0.10% taker fee'),
    ('predictit', 0.05, 0.05, 0.10, 0.0, '5% on trades, 10% on profits')
ON CONFLICT (platform) DO UPDATE SET
    taker_fee_pct = EXCLUDED.taker_fee_pct,
    maker_fee_pct = EXCLUDED.maker_fee_pct,
    settlement_fee_per_contract = EXCLUDED.settlement_fee_per_contract,
    withdrawal_fee = EXCLUDED.withdrawal_fee,
    fee_formula = EXCLUDED.fee_formula,
    updated_at = NOW();

-- ============================================
-- USER PREDICTION MARKET PREFERENCES
-- Track user's PM platform accounts and settings
-- ============================================
CREATE TABLE IF NOT EXISTS user_pm_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- Platform accounts (for alert routing)
    has_kalshi_account BOOLEAN DEFAULT FALSE,
    has_polymarket_account BOOLEAN DEFAULT FALSE,
    has_predictit_account BOOLEAN DEFAULT FALSE,

    -- Alert preferences
    min_profit_pct DECIMAL DEFAULT 1.0,
    max_resolution_risk DECIMAL DEFAULT 0.1,
    alert_on_pm_arbs BOOLEAN DEFAULT TRUE,

    -- Bankroll for sizing
    pm_bankroll DECIMAL DEFAULT 0,
    max_bet_pct DECIMAL DEFAULT 0.05,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id)
);

-- ============================================
-- FUNCTIONS
-- ============================================

-- Function to expire old PM arbs
CREATE OR REPLACE FUNCTION expire_old_pm_arbs()
RETURNS INTEGER AS $$
DECLARE
    expired_count INTEGER;
BEGIN
    UPDATE pm_arbitrage_opportunities
    SET is_active = FALSE, expired_at = NOW()
    WHERE is_active = TRUE
    AND detected_at < NOW() - INTERVAL '30 minutes';

    GET DIAGNOSTICS expired_count = ROW_COUNT;
    RETURN expired_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get best current PM arbs
CREATE OR REPLACE FUNCTION get_best_pm_arbs(min_profit DECIMAL DEFAULT 0.5, max_results INTEGER DEFAULT 10)
RETURNS TABLE (
    canonical_event_id TEXT,
    event_description TEXT,
    buy_yes_platform TEXT,
    buy_yes_price DECIMAL,
    buy_no_platform TEXT,
    buy_no_price DECIMAL,
    net_profit_pct DECIMAL,
    resolution_risk DECIMAL,
    detected_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.canonical_event_id,
        a.event_description,
        a.buy_yes_platform,
        a.buy_yes_price,
        a.buy_no_platform,
        a.buy_no_price,
        a.net_profit_pct,
        a.resolution_risk,
        a.detected_at
    FROM pm_arbitrage_opportunities a
    WHERE a.is_active = TRUE
    AND a.net_profit_pct >= min_profit
    ORDER BY a.net_profit_pct DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;
