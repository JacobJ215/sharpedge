-- ============================================================
-- SharpEdge — Complete Database Schema
-- Run this once in the Supabase SQL Editor (Dashboard → SQL Editor)
-- Safe to re-run: all statements use IF NOT EXISTS / OR REPLACE
-- ============================================================


-- ============================================================
-- PART 1: INITIAL SCHEMA (users, bets, usage, alerts, projections, odds_history)
-- ============================================================

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

CREATE TABLE IF NOT EXISTS bets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    sport VARCHAR(50) NOT NULL,
    league VARCHAR(100),
    game VARCHAR(255) NOT NULL,
    bet_type VARCHAR(50) NOT NULL,
    selection VARCHAR(255) NOT NULL,

    odds INTEGER NOT NULL,
    units DECIMAL(4, 2) NOT NULL,
    stake DECIMAL(10, 2) NOT NULL,
    potential_win DECIMAL(10, 2) NOT NULL,

    opening_line DECIMAL(6, 2),
    line_at_bet DECIMAL(6, 2),
    closing_line DECIMAL(6, 2),
    clv_points DECIMAL(4, 2),

    result VARCHAR(20) DEFAULT 'PENDING',
    profit DECIMAL(10, 2),

    sportsbook VARCHAR(100),
    notes TEXT,
    game_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    settled_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    feature VARCHAR(100) NOT NULL,
    used_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL,
    game_id VARCHAR(255),
    content TEXT,
    delivered_at TIMESTAMPTZ DEFAULT NOW()
);

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

CREATE TABLE IF NOT EXISTS odds_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id VARCHAR(255) NOT NULL,
    sportsbook VARCHAR(100) NOT NULL,
    bet_type VARCHAR(50) NOT NULL,
    line DECIMAL(6, 2),
    odds INTEGER,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
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

-- Auto-update updated_at trigger function
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

-- RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE bets ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE projections ENABLE ROW LEVEL SECURITY;
ALTER TABLE odds_history ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'users' AND policyname = 'Service role full access on users') THEN
    CREATE POLICY "Service role full access on users" ON users FOR ALL USING (auth.role() = 'service_role');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'bets' AND policyname = 'Service role full access on bets') THEN
    CREATE POLICY "Service role full access on bets" ON bets FOR ALL USING (auth.role() = 'service_role');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'usage' AND policyname = 'Service role full access on usage') THEN
    CREATE POLICY "Service role full access on usage" ON usage FOR ALL USING (auth.role() = 'service_role');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'alerts' AND policyname = 'Service role full access on alerts') THEN
    CREATE POLICY "Service role full access on alerts" ON alerts FOR ALL USING (auth.role() = 'service_role');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'projections' AND policyname = 'Service role full access on projections') THEN
    CREATE POLICY "Service role full access on projections" ON projections FOR ALL USING (auth.role() = 'service_role');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'odds_history' AND policyname = 'Service role full access on odds_history') THEN
    CREATE POLICY "Service role full access on odds_history" ON odds_history FOR ALL USING (auth.role() = 'service_role');
  END IF;
END $$;


-- ============================================================
-- PART 2: ANALYTICS TABLES
-- (opening_lines, consensus_lines, line_movements, public_betting,
--  game_weather, value_plays, arbitrage_opportunities,
--  middle_opportunities, team_schedules, injuries,
--  user_alert_preferences, alert_delivery_log)
-- ============================================================

CREATE TABLE IF NOT EXISTS opening_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    sport TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    sportsbook TEXT NOT NULL,
    bet_type TEXT NOT NULL,
    line DECIMAL,
    odds_a INTEGER,
    odds_b INTEGER,
    game_start_time TIMESTAMPTZ,
    captured_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(game_id, sportsbook, bet_type)
);

CREATE INDEX IF NOT EXISTS idx_opening_lines_game ON opening_lines(game_id);
CREATE INDEX IF NOT EXISTS idx_opening_lines_sport_time ON opening_lines(sport, game_start_time);


CREATE TABLE IF NOT EXISTS consensus_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    sport TEXT NOT NULL,
    spread_consensus DECIMAL,
    spread_weighted_consensus DECIMAL,
    spread_min DECIMAL,
    spread_max DECIMAL,
    spread_books_count INTEGER,
    total_consensus DECIMAL,
    total_weighted_consensus DECIMAL,
    total_min DECIMAL,
    total_max DECIMAL,
    total_books_count INTEGER,
    spread_fair_home_prob DECIMAL,
    spread_fair_away_prob DECIMAL,
    total_fair_over_prob DECIMAL,
    total_fair_under_prob DECIMAL,
    ml_fair_home_prob DECIMAL,
    ml_fair_away_prob DECIMAL,
    market_agreement DECIMAL,
    calculated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_consensus_game ON consensus_lines(game_id);
CREATE INDEX IF NOT EXISTS idx_consensus_recent ON consensus_lines(calculated_at DESC);


CREATE TABLE IF NOT EXISTS line_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    sport TEXT NOT NULL,
    bet_type TEXT NOT NULL,
    sportsbook TEXT,
    old_line DECIMAL,
    new_line DECIMAL,
    old_odds INTEGER,
    new_odds INTEGER,
    direction TEXT,
    magnitude DECIMAL,
    movement_type TEXT,
    confidence DECIMAL,
    interpretation TEXT,
    is_significant BOOLEAN DEFAULT FALSE,
    public_side TEXT,
    detected_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_movements_game ON line_movements(game_id, detected_at);
CREATE INDEX IF NOT EXISTS idx_movements_type ON line_movements(movement_type) WHERE is_significant = TRUE;
CREATE INDEX IF NOT EXISTS idx_movements_recent ON line_movements(detected_at DESC);


CREATE TABLE IF NOT EXISTS public_betting (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    sport TEXT NOT NULL,
    home_team TEXT,
    away_team TEXT,
    spread_ticket_home DECIMAL,
    spread_ticket_away DECIMAL,
    spread_money_home DECIMAL,
    spread_money_away DECIMAL,
    total_ticket_over DECIMAL,
    total_ticket_under DECIMAL,
    total_money_over DECIMAL,
    total_money_under DECIMAL,
    ml_ticket_home DECIMAL,
    ml_ticket_away DECIMAL,
    ml_money_home DECIMAL,
    ml_money_away DECIMAL,
    spread_sharp_side TEXT,
    spread_divergence DECIMAL,
    total_sharp_side TEXT,
    total_divergence DECIMAL,
    source TEXT NOT NULL,
    captured_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_public_betting_game ON public_betting(game_id);
CREATE INDEX IF NOT EXISTS idx_public_betting_recent ON public_betting(captured_at DESC);


CREATE TABLE IF NOT EXISTS game_weather (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL UNIQUE,
    sport TEXT NOT NULL,
    venue TEXT,
    is_dome BOOLEAN DEFAULT FALSE,
    is_retractable BOOLEAN DEFAULT FALSE,
    temperature DECIMAL,
    wind_speed DECIMAL,
    wind_direction TEXT,
    precipitation_chance DECIMAL,
    precipitation_type TEXT,
    humidity DECIMAL,
    conditions TEXT,
    total_adjustment DECIMAL,
    spread_adjustment DECIMAL,
    impact_level TEXT,
    source TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_weather_game ON game_weather(game_id);


CREATE TABLE IF NOT EXISTS value_plays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    game TEXT NOT NULL,
    sport TEXT NOT NULL,
    bet_type TEXT NOT NULL,
    side TEXT NOT NULL,
    sportsbook TEXT NOT NULL,
    market_odds INTEGER NOT NULL,
    model_probability DECIMAL NOT NULL,
    implied_probability DECIMAL NOT NULL,
    fair_odds INTEGER,
    edge_percentage DECIMAL NOT NULL,
    ev_percentage DECIMAL NOT NULL,
    confidence TEXT NOT NULL,
    game_start_time TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    result TEXT,
    actual_clv DECIMAL,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_value_plays_active ON value_plays(created_at DESC) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_value_plays_game ON value_plays(game_id);
CREATE INDEX IF NOT EXISTS idx_value_plays_confidence ON value_plays(confidence, ev_percentage DESC) WHERE is_active = TRUE;


CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    game TEXT NOT NULL,
    sport TEXT NOT NULL,
    bet_type TEXT NOT NULL,
    book_a TEXT NOT NULL,
    side_a TEXT NOT NULL,
    odds_a INTEGER NOT NULL,
    stake_a_percentage DECIMAL NOT NULL,
    book_b TEXT NOT NULL,
    side_b TEXT NOT NULL,
    odds_b INTEGER NOT NULL,
    stake_b_percentage DECIMAL NOT NULL,
    profit_percentage DECIMAL NOT NULL,
    total_implied DECIMAL NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    expired_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_arb_active ON arbitrage_opportunities(detected_at DESC) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_arb_profit ON arbitrage_opportunities(profit_percentage DESC) WHERE is_active = TRUE;


CREATE TABLE IF NOT EXISTS middle_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    game TEXT NOT NULL,
    sport TEXT NOT NULL,
    bet_type TEXT NOT NULL,
    book_a TEXT NOT NULL,
    line_a DECIMAL NOT NULL,
    odds_a INTEGER NOT NULL,
    book_b TEXT NOT NULL,
    line_b DECIMAL NOT NULL,
    odds_b INTEGER NOT NULL,
    middle_low DECIMAL NOT NULL,
    middle_high DECIMAL NOT NULL,
    middle_width DECIMAL NOT NULL,
    hit_probability DECIMAL NOT NULL,
    expected_value DECIMAL,
    ev_percentage DECIMAL,
    is_active BOOLEAN DEFAULT TRUE,
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    expired_at TIMESTAMPTZ,
    final_margin DECIMAL,
    result TEXT
);

CREATE INDEX IF NOT EXISTS idx_middle_active ON middle_opportunities(detected_at DESC) WHERE is_active = TRUE;


CREATE TABLE IF NOT EXISTS team_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    team TEXT NOT NULL,
    sport TEXT NOT NULL,
    is_home BOOLEAN NOT NULL,
    rest_days INTEGER,
    games_last_7_days INTEGER,
    games_last_14_days INTEGER,
    is_back_to_back BOOLEAN DEFAULT FALSE,
    is_3_in_4 BOOLEAN DEFAULT FALSE,
    is_4_in_5 BOOLEAN DEFAULT FALSE,
    travel_miles INTEGER,
    timezone_change INTEGER,
    previous_location TEXT,
    previous_opponent TEXT,
    previous_result TEXT,
    previous_margin INTEGER,
    next_opponent TEXT,
    schedule_edge DECIMAL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(game_id, team)
);

CREATE INDEX IF NOT EXISTS idx_schedules_game ON team_schedules(game_id);
CREATE INDEX IF NOT EXISTS idx_schedules_team ON team_schedules(team, sport);


CREATE TABLE IF NOT EXISTS injuries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team TEXT NOT NULL,
    sport TEXT NOT NULL,
    player_name TEXT NOT NULL,
    position TEXT,
    status TEXT NOT NULL,
    injury_type TEXT,
    injury_details TEXT,
    impact_rating DECIMAL,
    spread_impact DECIMAL,
    is_key_player BOOLEAN DEFAULT FALSE,
    injury_date DATE,
    expected_return DATE,
    source TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(team, sport, player_name)
);

CREATE INDEX IF NOT EXISTS idx_injuries_team ON injuries(team, sport);
CREATE INDEX IF NOT EXISTS idx_injuries_active ON injuries(status) WHERE status IN ('Out', 'Doubtful', 'Questionable');


-- Extra columns on projections
ALTER TABLE projections
ADD COLUMN IF NOT EXISTS spread_home_prob DECIMAL,
ADD COLUMN IF NOT EXISTS spread_away_prob DECIMAL,
ADD COLUMN IF NOT EXISTS over_prob DECIMAL,
ADD COLUMN IF NOT EXISTS under_prob DECIMAL,
ADD COLUMN IF NOT EXISTS home_win_prob DECIMAL,
ADD COLUMN IF NOT EXISTS away_win_prob DECIMAL,
ADD COLUMN IF NOT EXISTS weather_adjusted BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS schedule_adjusted BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS injuries_adjusted BOOLEAN DEFAULT FALSE;


CREATE TABLE IF NOT EXISTS user_alert_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    value_alerts_enabled BOOLEAN DEFAULT TRUE,
    min_ev_threshold DECIMAL DEFAULT 2.0,
    min_edge_threshold DECIMAL DEFAULT 2.0,
    value_confidence_filter TEXT DEFAULT 'MEDIUM',
    movement_alerts_enabled BOOLEAN DEFAULT TRUE,
    min_movement_threshold DECIMAL DEFAULT 0.5,
    steam_alerts_only BOOLEAN DEFAULT FALSE,
    arb_alerts_enabled BOOLEAN DEFAULT FALSE,
    min_arb_profit DECIMAL DEFAULT 1.0,
    sports_filter TEXT[],
    dm_enabled BOOLEAN DEFAULT TRUE,
    channel_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);


CREATE TABLE IF NOT EXISTS alert_delivery_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    alert_type TEXT NOT NULL,
    source_id UUID,
    source_table TEXT,
    channel_id TEXT,
    message_id TEXT,
    delivered_at TIMESTAMPTZ DEFAULT NOW(),
    clicked BOOLEAN DEFAULT FALSE,
    bet_placed BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_alert_log_user ON alert_delivery_log(user_id, delivered_at DESC);

-- Triggers for updated_at
CREATE OR REPLACE TRIGGER update_game_weather_updated_at
    BEFORE UPDATE ON game_weather
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_team_schedules_updated_at
    BEFORE UPDATE ON team_schedules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_injuries_updated_at
    BEFORE UPDATE ON injuries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_user_alert_preferences_updated_at
    BEFORE UPDATE ON user_alert_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS
ALTER TABLE opening_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE consensus_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE line_movements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public_betting ENABLE ROW LEVEL SECURITY;
ALTER TABLE game_weather ENABLE ROW LEVEL SECURITY;
ALTER TABLE value_plays ENABLE ROW LEVEL SECURITY;
ALTER TABLE arbitrage_opportunities ENABLE ROW LEVEL SECURITY;
ALTER TABLE middle_opportunities ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE injuries ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_alert_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_delivery_log ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'opening_lines' AND policyname = 'Service role full access') THEN
    CREATE POLICY "Service role full access" ON opening_lines FOR ALL USING (auth.role() = 'service_role');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'consensus_lines' AND policyname = 'Service role full access') THEN
    CREATE POLICY "Service role full access" ON consensus_lines FOR ALL USING (auth.role() = 'service_role');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'line_movements' AND policyname = 'Service role full access') THEN
    CREATE POLICY "Service role full access" ON line_movements FOR ALL USING (auth.role() = 'service_role');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'public_betting' AND policyname = 'Service role full access') THEN
    CREATE POLICY "Service role full access" ON public_betting FOR ALL USING (auth.role() = 'service_role');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'game_weather' AND policyname = 'Service role full access') THEN
    CREATE POLICY "Service role full access" ON game_weather FOR ALL USING (auth.role() = 'service_role');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'value_plays' AND policyname = 'Service role full access') THEN
    CREATE POLICY "Service role full access" ON value_plays FOR ALL USING (auth.role() = 'service_role');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'arbitrage_opportunities' AND policyname = 'Service role full access') THEN
    CREATE POLICY "Service role full access" ON arbitrage_opportunities FOR ALL USING (auth.role() = 'service_role');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'middle_opportunities' AND policyname = 'Service role full access') THEN
    CREATE POLICY "Service role full access" ON middle_opportunities FOR ALL USING (auth.role() = 'service_role');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'team_schedules' AND policyname = 'Service role full access') THEN
    CREATE POLICY "Service role full access" ON team_schedules FOR ALL USING (auth.role() = 'service_role');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'injuries' AND policyname = 'Service role full access') THEN
    CREATE POLICY "Service role full access" ON injuries FOR ALL USING (auth.role() = 'service_role');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'user_alert_preferences' AND policyname = 'Service role full access') THEN
    CREATE POLICY "Service role full access" ON user_alert_preferences FOR ALL USING (auth.role() = 'service_role');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'alert_delivery_log' AND policyname = 'Service role full access') THEN
    CREATE POLICY "Service role full access" ON alert_delivery_log FOR ALL USING (auth.role() = 'service_role');
  END IF;
END $$;

-- Views
CREATE OR REPLACE VIEW active_value_plays AS
SELECT
    v.*,
    c.spread_consensus,
    c.total_consensus,
    c.market_agreement
FROM value_plays v
LEFT JOIN consensus_lines c ON v.game_id = c.game_id
WHERE v.is_active = TRUE
    AND (v.expires_at IS NULL OR v.expires_at > NOW())
ORDER BY v.ev_percentage DESC;

CREATE OR REPLACE VIEW sharp_money_indicators AS
SELECT
    p.game_id,
    p.sport,
    p.home_team,
    p.away_team,
    p.spread_ticket_home,
    p.spread_money_home,
    p.spread_divergence,
    p.spread_sharp_side,
    CASE
        WHEN p.spread_divergence >= 15 THEN 'STRONG'
        WHEN p.spread_divergence >= 10 THEN 'MODERATE'
        WHEN p.spread_divergence >= 5 THEN 'SLIGHT'
        ELSE 'NONE'
    END as sharp_signal_strength,
    p.captured_at
FROM public_betting p
WHERE p.captured_at = (
    SELECT MAX(captured_at) FROM public_betting WHERE game_id = p.game_id
);

CREATE OR REPLACE VIEW recent_significant_movements AS
SELECT
    m.*,
    o.line as opening_line,
    m.new_line - o.line as total_movement_from_open
FROM line_movements m
LEFT JOIN opening_lines o ON m.game_id = o.game_id
    AND m.sportsbook = o.sportsbook
    AND m.bet_type = o.bet_type
WHERE m.is_significant = TRUE
    AND m.detected_at > NOW() - INTERVAL '24 hours'
ORDER BY m.detected_at DESC;


-- ============================================================
-- PART 3: PREDICTION MARKET TABLES
-- (pm_canonical_events, pm_market_outcomes, pm_arbitrage_opportunities,
--  pm_price_history, pm_platform_fees, user_pm_preferences)
-- ============================================================

CREATE TABLE IF NOT EXISTS pm_canonical_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    description TEXT NOT NULL,
    resolution_date TIMESTAMPTZ,
    resolution_source TEXT,
    resolution_criteria TEXT,
    equivalence_confidence DECIMAL DEFAULT 1.0,
    resolution_risk TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pm_events_type ON pm_canonical_events(event_type);
CREATE INDEX IF NOT EXISTS idx_pm_events_resolution ON pm_canonical_events(resolution_date);


CREATE TABLE IF NOT EXISTS pm_market_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_event_id TEXT REFERENCES pm_canonical_events(canonical_id),
    platform TEXT NOT NULL,
    market_id TEXT NOT NULL,
    outcome_id TEXT NOT NULL,
    question TEXT NOT NULL,
    outcome_label TEXT NOT NULL,
    price DECIMAL NOT NULL,
    volume_24h DECIMAL DEFAULT 0,
    liquidity DECIMAL DEFAULT 0,
    resolution_source TEXT,
    resolution_criteria TEXT,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(platform, market_id, outcome_id)
);

CREATE INDEX IF NOT EXISTS idx_pm_outcomes_canonical ON pm_market_outcomes(canonical_event_id);
CREATE INDEX IF NOT EXISTS idx_pm_outcomes_platform ON pm_market_outcomes(platform);
CREATE INDEX IF NOT EXISTS idx_pm_outcomes_price ON pm_market_outcomes(price);


CREATE TABLE IF NOT EXISTS pm_arbitrage_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_event_id TEXT NOT NULL,
    event_description TEXT,
    event_type TEXT,
    buy_yes_platform TEXT NOT NULL,
    buy_yes_price DECIMAL NOT NULL,
    buy_no_platform TEXT NOT NULL,
    buy_no_price DECIMAL NOT NULL,
    gross_gap_pct DECIMAL NOT NULL,
    gross_profit_pct DECIMAL NOT NULL,
    net_profit_pct DECIMAL NOT NULL,
    stake_yes DECIMAL,
    stake_no DECIMAL,
    guaranteed_return DECIMAL,
    resolution_risk DECIMAL DEFAULT 0,
    equivalence_confidence DECIMAL DEFAULT 1.0,
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    estimated_window_seconds INTEGER DEFAULT 30,
    expired_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(canonical_event_id, buy_yes_platform, buy_no_platform)
);

CREATE INDEX IF NOT EXISTS idx_pm_arb_active ON pm_arbitrage_opportunities(is_active, net_profit_pct DESC);
CREATE INDEX IF NOT EXISTS idx_pm_arb_detected ON pm_arbitrage_opportunities(detected_at DESC);


CREATE TABLE IF NOT EXISTS pm_price_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,
    market_id TEXT NOT NULL,
    price DECIMAL NOT NULL,
    volume DECIMAL,
    captured_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pm_price_history ON pm_price_history(platform, market_id, captured_at DESC);


CREATE TABLE IF NOT EXISTS pm_platform_fees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL UNIQUE,
    taker_fee_pct DECIMAL NOT NULL DEFAULT 0,
    maker_fee_pct DECIMAL NOT NULL DEFAULT 0,
    settlement_fee_per_contract DECIMAL NOT NULL DEFAULT 0,
    withdrawal_fee DECIMAL NOT NULL DEFAULT 0,
    fee_formula TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO pm_platform_fees (platform, taker_fee_pct, maker_fee_pct, settlement_fee_per_contract, withdrawal_fee, fee_formula)
VALUES
    ('kalshi',        0.01,  0.0,  0.01, 2.0,  '0.07 × contracts × price × (1-price)'),
    ('polymarket',    0.0,   0.0,  0.0,  0.50, 'No trading fees on standard markets'),
    ('polymarket_us', 0.001, 0.0,  0.0,  0.50, '0.10% taker fee'),
    ('predictit',     0.05,  0.05, 0.10, 0.0,  '5% on trades, 10% on profits')
ON CONFLICT (platform) DO UPDATE SET
    taker_fee_pct              = EXCLUDED.taker_fee_pct,
    maker_fee_pct              = EXCLUDED.maker_fee_pct,
    settlement_fee_per_contract = EXCLUDED.settlement_fee_per_contract,
    withdrawal_fee             = EXCLUDED.withdrawal_fee,
    fee_formula                = EXCLUDED.fee_formula,
    updated_at                 = NOW();


CREATE TABLE IF NOT EXISTS user_pm_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    has_kalshi_account BOOLEAN DEFAULT FALSE,
    has_polymarket_account BOOLEAN DEFAULT FALSE,
    has_predictit_account BOOLEAN DEFAULT FALSE,
    min_profit_pct DECIMAL DEFAULT 1.0,
    max_resolution_risk DECIMAL DEFAULT 0.1,
    alert_on_pm_arbs BOOLEAN DEFAULT TRUE,
    pm_bankroll DECIMAL DEFAULT 0,
    max_bet_pct DECIMAL DEFAULT 0.05,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

CREATE OR REPLACE FUNCTION expire_old_pm_arbs()
RETURNS INTEGER AS $$
DECLARE expired_count INTEGER;
BEGIN
    UPDATE pm_arbitrage_opportunities
    SET is_active = FALSE, expired_at = NOW()
    WHERE is_active = TRUE AND detected_at < NOW() - INTERVAL '30 minutes';
    GET DIAGNOSTICS expired_count = ROW_COUNT;
    RETURN expired_count;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_best_pm_arbs(min_profit DECIMAL DEFAULT 0.5, max_results INTEGER DEFAULT 10)
RETURNS TABLE (
    canonical_event_id TEXT, event_description TEXT,
    buy_yes_platform TEXT, buy_yes_price DECIMAL,
    buy_no_platform TEXT,  buy_no_price DECIMAL,
    net_profit_pct DECIMAL, resolution_risk DECIMAL,
    detected_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT a.canonical_event_id, a.event_description,
           a.buy_yes_platform, a.buy_yes_price,
           a.buy_no_platform, a.buy_no_price,
           a.net_profit_pct, a.resolution_risk, a.detected_at
    FROM pm_arbitrage_opportunities a
    WHERE a.is_active = TRUE AND a.net_profit_pct >= min_profit
    ORDER BY a.net_profit_pct DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- PART 4: CALIBRATION & BACKTESTING TABLES
-- (model_predictions, calibration_reports, calibration_history)
-- ============================================================

CREATE TABLE IF NOT EXISTS model_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_id TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    market_type TEXT NOT NULL,
    sport TEXT NOT NULL,
    game_id TEXT,
    game_description TEXT,
    predicted_probability DECIMAL(5,4) NOT NULL,
    predicted_edge DECIMAL(6,4),
    model_line DECIMAL(6,2),
    market_line DECIMAL(6,2),
    odds INTEGER NOT NULL,
    outcome BOOLEAN,
    resolved_at TIMESTAMPTZ,
    closing_line DECIMAL(6,2),
    closing_odds INTEGER,
    model_version TEXT,
    confidence_level TEXT,
    CONSTRAINT valid_probability CHECK (predicted_probability >= 0 AND predicted_probability <= 1)
);

CREATE INDEX IF NOT EXISTS idx_predictions_market_type ON model_predictions(market_type);
CREATE INDEX IF NOT EXISTS idx_predictions_sport ON model_predictions(sport);
CREATE INDEX IF NOT EXISTS idx_predictions_created ON model_predictions(created_at);
CREATE INDEX IF NOT EXISTS idx_predictions_outcome ON model_predictions(outcome) WHERE outcome IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_predictions_pending ON model_predictions(created_at) WHERE outcome IS NULL;


CREATE TABLE IF NOT EXISTS calibration_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    market_type TEXT NOT NULL,
    sport TEXT,
    model_version TEXT,
    total_predictions INTEGER NOT NULL,
    total_resolved INTEGER NOT NULL,
    brier_score DECIMAL(8,6),
    calibration_error DECIMAL(8,6),
    discrimination DECIMAL(6,4),
    status TEXT NOT NULL,
    bins JSONB NOT NULL DEFAULT '[]'::jsonb,
    CONSTRAINT valid_status CHECK (status IN ('uncalibrated', 'preliminary', 'calibrated', 'well_calibrated'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_calibration_scope
ON calibration_reports(market_type, COALESCE(sport, ''), COALESCE(model_version, ''));


CREATE TABLE IF NOT EXISTS calibration_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    market_type TEXT NOT NULL,
    sport TEXT,
    brier_score DECIMAL(8,6),
    calibration_error DECIMAL(8,6),
    total_resolved INTEGER,
    status TEXT
);

CREATE INDEX IF NOT EXISTS idx_calibration_history_time ON calibration_history(recorded_at);

CREATE OR REPLACE FUNCTION get_calibration_status(resolved_count INTEGER)
RETURNS TEXT AS $$
BEGIN
    IF resolved_count < 30 THEN RETURN 'uncalibrated';
    ELSIF resolved_count < 100 THEN RETURN 'preliminary';
    ELSIF resolved_count < 1000 THEN RETURN 'calibrated';
    ELSE RETURN 'well_calibrated';
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION wilson_score_interval(
    successes INTEGER, total INTEGER, confidence DECIMAL DEFAULT 0.95
)
RETURNS TABLE(ci_lower DECIMAL, ci_upper DECIMAL) AS $$
DECLARE
    z DECIMAL; p_hat DECIMAL; denominator DECIMAL; center DECIMAL; margin DECIMAL;
BEGIN
    IF total = 0 THEN RETURN QUERY SELECT 0::DECIMAL, 1::DECIMAL; RETURN; END IF;
    z := 1.96;
    p_hat := successes::DECIMAL / total;
    denominator := 1 + z * z / total;
    center := (p_hat + z * z / (2 * total)) / denominator;
    margin := z * SQRT((p_hat * (1 - p_hat) + z * z / (4 * total)) / total) / denominator;
    RETURN QUERY SELECT GREATEST(0, center - margin)::DECIMAL, LEAST(1, center + margin)::DECIMAL;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

ALTER TABLE model_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE calibration_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE calibration_history ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'model_predictions' AND policyname = 'Service role full access to predictions') THEN
    CREATE POLICY "Service role full access to predictions" ON model_predictions FOR ALL TO service_role USING (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'calibration_reports' AND policyname = 'Service role full access to calibration_reports') THEN
    CREATE POLICY "Service role full access to calibration_reports" ON calibration_reports FOR ALL TO service_role USING (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'calibration_history' AND policyname = 'Service role full access to calibration_history') THEN
    CREATE POLICY "Service role full access to calibration_history" ON calibration_history FOR ALL TO service_role USING (true);
  END IF;
END $$;


-- ============================================================
-- PART 5: CLV ENHANCEMENTS
-- (extra columns on bets, closing_lines table, CLV functions/view)
-- ============================================================

ALTER TABLE bets
ADD COLUMN IF NOT EXISTS opening_odds INTEGER,
ADD COLUMN IF NOT EXISTS closing_odds INTEGER,
ADD COLUMN IF NOT EXISTS clv_percentage DECIMAL(6, 3),
ADD COLUMN IF NOT EXISTS beat_closing_line BOOLEAN,
ADD COLUMN IF NOT EXISTS fair_prob_at_bet DECIMAL(6, 4),
ADD COLUMN IF NOT EXISTS fair_prob_at_close DECIMAL(6, 4);

ALTER TABLE odds_history
ADD COLUMN IF NOT EXISTS side TEXT,
ADD COLUMN IF NOT EXISTS game_start_time TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_odds_history_close
ON odds_history(game_id, sportsbook, bet_type, recorded_at DESC);


CREATE TABLE IF NOT EXISTS closing_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    sport TEXT NOT NULL,
    bet_type TEXT NOT NULL,
    sportsbook TEXT NOT NULL,
    line DECIMAL,
    odds_side1 INTEGER,
    odds_side2 INTEGER,
    fair_prob_side1 DECIMAL(6, 4),
    fair_prob_side2 DECIMAL(6, 4),
    vig_percentage DECIMAL(4, 2),
    game_start_time TIMESTAMPTZ,
    captured_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(game_id, sportsbook, bet_type)
);

CREATE INDEX IF NOT EXISTS idx_closing_lines_game ON closing_lines(game_id);
CREATE INDEX IF NOT EXISTS idx_closing_lines_time ON closing_lines(game_start_time);

CREATE OR REPLACE VIEW user_clv_summary AS
SELECT
    user_id, sport, bet_type,
    COUNT(*) as total_bets,
    COUNT(*) FILTER (WHERE clv_percentage IS NOT NULL) as bets_with_clv,
    AVG(clv_percentage) FILTER (WHERE clv_percentage IS NOT NULL) as avg_clv,
    COUNT(*) FILTER (WHERE beat_closing_line = TRUE) as positive_clv_count,
    COUNT(*) FILTER (WHERE beat_closing_line = FALSE) as negative_clv_count,
    ROUND(
        COUNT(*) FILTER (WHERE beat_closing_line = TRUE)::DECIMAL /
        NULLIF(COUNT(*) FILTER (WHERE clv_percentage IS NOT NULL), 0) * 100,
        1
    ) as positive_clv_rate
FROM bets
WHERE result != 'PENDING'
GROUP BY user_id, sport, bet_type;

CREATE OR REPLACE FUNCTION calculate_clv(p_bet_odds INTEGER, p_closing_odds INTEGER)
RETURNS DECIMAL AS $$
DECLARE
    v_bet_implied DECIMAL; v_close_implied DECIMAL;
BEGIN
    IF p_bet_odds > 0 THEN v_bet_implied := 100.0 / (p_bet_odds + 100);
    ELSE v_bet_implied := ABS(p_bet_odds)::DECIMAL / (ABS(p_bet_odds) + 100); END IF;

    IF p_closing_odds > 0 THEN v_close_implied := 100.0 / (p_closing_odds + 100);
    ELSE v_close_implied := ABS(p_closing_odds)::DECIMAL / (ABS(p_closing_odds) + 100); END IF;

    RETURN ROUND((v_close_implied - v_bet_implied) * 100, 3);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

ALTER TABLE closing_lines ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'closing_lines' AND policyname = 'Service role full access to closing_lines') THEN
    CREATE POLICY "Service role full access to closing_lines" ON closing_lines FOR ALL TO service_role USING (true);
  END IF;
END $$;


-- ============================================================
-- PART 6: SOCIAL MEDIA AUTOMATION
-- (social_posts, alert_queue, win_announcements)
-- ============================================================

CREATE TABLE IF NOT EXISTS social_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type TEXT NOT NULL,       -- 'value_play', 'win_announcement', 'alert'
    source_id UUID,                  -- FK to value_plays.id or bets.id
    platform TEXT NOT NULL,         -- 'discord', 'twitter', 'instagram'
    channel_or_handle TEXT,         -- Discord channel_id, Twitter handle, IG account
    external_post_id TEXT,          -- tweet_id, Discord message_id, IG media_id
    content_text TEXT,
    image_url TEXT,
    posted_at TIMESTAMPTZ DEFAULT NOW(),
    engagement_likes INT DEFAULT 0,
    engagement_comments INT DEFAULT 0,
    engagement_reposts INT DEFAULT 0,
    last_engagement_sync TIMESTAMPTZ,
    reply_to_post_id TEXT,          -- for linking win posts back to alert posts
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    value_play_id UUID NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending','posted','failed','skipped'
    attempts INT DEFAULT 0,
    last_attempted_at TIMESTAMPTZ,
    skip_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS win_announcements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bet_id UUID NOT NULL,
    social_post_id UUID REFERENCES social_posts(id),
    sport TEXT,
    game TEXT,
    selection TEXT,
    odds INT,
    stake DECIMAL(10,2),
    profit DECIMAL(10,2),
    roi_at_post DECIMAL(8,4),
    running_wins INT DEFAULT 0,
    running_losses INT DEFAULT 0,
    running_units DECIMAL(10,2),
    announced_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_social_posts_source ON social_posts(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_social_posts_platform ON social_posts(platform, posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_alert_queue_status ON alert_queue(status, created_at);
CREATE INDEX IF NOT EXISTS idx_alert_queue_play ON alert_queue(value_play_id);

ALTER TABLE social_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE win_announcements ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'social_posts' AND policyname = 'Service role full access to social_posts') THEN
    CREATE POLICY "Service role full access to social_posts" ON social_posts FOR ALL TO service_role USING (true);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'alert_queue' AND policyname = 'Service role full access to alert_queue') THEN
    CREATE POLICY "Service role full access to alert_queue" ON alert_queue FOR ALL TO service_role USING (true);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'win_announcements' AND policyname = 'Service role full access to win_announcements') THEN
    CREATE POLICY "Service role full access to win_announcements" ON win_announcements FOR ALL TO service_role USING (true);
  END IF;
END $$;


-- ============================================================
-- PART 7: SETTLEMENT LEDGER (Phase 6)
-- Append-only financial event ledger — no UPDATE or DELETE
-- Run this migration after Part 6 (RLS setup must be complete)
-- ============================================================

CREATE TABLE IF NOT EXISTS ledger_entries (
    entry_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_type      TEXT NOT NULL CHECK (event_type IN (
                        'FILL', 'FEE', 'REBATE', 'SETTLEMENT',
                        'ADJUSTMENT', 'POSITION_OPENED', 'POSITION_CLOSED'
                    )),
    venue_id        TEXT NOT NULL,
    market_id       TEXT NOT NULL,
    position_lot_id TEXT NOT NULL,
    amount_usdc     DOUBLE PRECISION NOT NULL,
    fee_component   DOUBLE PRECISION NOT NULL DEFAULT 0,
    rebate_component DOUBLE PRECISION NOT NULL DEFAULT 0,
    price_at_event  DOUBLE PRECISION NOT NULL,
    occurred_at     TIMESTAMPTZ NOT NULL,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes           TEXT NOT NULL DEFAULT ''
);

-- Append-only RLS policy: INSERT only, no UPDATE or DELETE
ALTER TABLE ledger_entries ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'ledger_entries' AND policyname = 'ledger_insert_only') THEN
    CREATE POLICY "ledger_insert_only" ON ledger_entries
        FOR INSERT
        WITH CHECK (true);
  END IF;
END $$;

-- No SELECT/UPDATE/DELETE policies by default — service role bypasses RLS
-- Application reads via service_role key only (server-side)

-- Index for position replay queries
CREATE INDEX IF NOT EXISTS idx_ledger_position_lot
    ON ledger_entries (position_lot_id, occurred_at ASC);

CREATE INDEX IF NOT EXISTS idx_ledger_venue_market
    ON ledger_entries (venue_id, market_id, occurred_at ASC);


-- ============================================================
-- PART 8: MARKET STATE SNAPSHOT STORE (Phase 6, Plan 08)
-- Append-only table for MarketStatePacket persistence (deterministic replay support)
-- Run after ledger_entries migration (both in same schema.sql file)
-- ============================================================

CREATE TABLE IF NOT EXISTS market_snapshots (
    snapshot_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    venue_id        TEXT NOT NULL,
    market_id       TEXT NOT NULL,
    snapshot_at     TIMESTAMPTZ NOT NULL,
    orderbook_json  JSONB NOT NULL DEFAULT '{}',
    quotes_json     JSONB NOT NULL DEFAULT '[]',
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Append-only: no UPDATE or DELETE
ALTER TABLE market_snapshots ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'market_snapshots' AND policyname = 'snapshots_insert_only') THEN
    CREATE POLICY "snapshots_insert_only" ON market_snapshots
        FOR INSERT
        WITH CHECK (true);
  END IF;
END $$;

-- Primary replay index: filter by market, order by time
CREATE INDEX IF NOT EXISTS idx_snapshot_venue_market_time
    ON market_snapshots (venue_id, market_id, snapshot_at ASC);

-- Secondary index for time-range queries
CREATE INDEX IF NOT EXISTS idx_snapshot_at
    ON market_snapshots (snapshot_at ASC);


-- ============================================================
-- DONE — 25 tables, 3 views, 6 functions created
-- Tables: users, bets, usage, alerts, projections, odds_history,
--         opening_lines, consensus_lines, line_movements, public_betting,
--         game_weather, value_plays, arbitrage_opportunities,
--         middle_opportunities, team_schedules, injuries,
--         user_alert_preferences, alert_delivery_log,
--         pm_canonical_events, pm_market_outcomes,
--         pm_arbitrage_opportunities, pm_price_history,
--         pm_platform_fees, user_pm_preferences,
--         model_predictions, calibration_reports, calibration_history,
--         closing_lines,
--         social_posts, alert_queue, win_announcements,
--         ledger_entries, market_snapshots
-- ============================================================
