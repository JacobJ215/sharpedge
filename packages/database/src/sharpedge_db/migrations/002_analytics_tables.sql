-- SharpEdge Analytics Tables Migration
-- Run this after 001_initial_schema.sql

-- ============================================
-- OPENING LINES TRACKING
-- Captures the first odds for each game when market opens
-- ============================================

CREATE TABLE IF NOT EXISTS opening_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    sport TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    sportsbook TEXT NOT NULL,
    bet_type TEXT NOT NULL,  -- 'spread', 'total', 'moneyline'

    -- Line values
    line DECIMAL,            -- Spread or total number
    odds_a INTEGER,          -- Odds for side A (home spread, over, home ML)
    odds_b INTEGER,          -- Odds for side B (away spread, under, away ML)

    -- Metadata
    game_start_time TIMESTAMPTZ,
    captured_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure one opening line per game/book/bet_type
    UNIQUE(game_id, sportsbook, bet_type)
);

CREATE INDEX idx_opening_lines_game ON opening_lines(game_id);
CREATE INDEX idx_opening_lines_sport_time ON opening_lines(sport, game_start_time);


-- ============================================
-- CONSENSUS LINES
-- Market consensus calculated from all sportsbooks
-- ============================================

CREATE TABLE IF NOT EXISTS consensus_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    sport TEXT NOT NULL,

    -- Spread consensus
    spread_consensus DECIMAL,
    spread_weighted_consensus DECIMAL,  -- Weighted by book sharpness
    spread_min DECIMAL,
    spread_max DECIMAL,
    spread_books_count INTEGER,

    -- Total consensus
    total_consensus DECIMAL,
    total_weighted_consensus DECIMAL,
    total_min DECIMAL,
    total_max DECIMAL,
    total_books_count INTEGER,

    -- No-vig fair odds
    spread_fair_home_prob DECIMAL,
    spread_fair_away_prob DECIMAL,
    total_fair_over_prob DECIMAL,
    total_fair_under_prob DECIMAL,
    ml_fair_home_prob DECIMAL,
    ml_fair_away_prob DECIMAL,

    -- Market agreement score (0-100)
    market_agreement DECIMAL,

    calculated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_consensus_game ON consensus_lines(game_id);
CREATE INDEX idx_consensus_recent ON consensus_lines(calculated_at DESC);


-- ============================================
-- LINE MOVEMENTS
-- Track all line changes with classification
-- ============================================

CREATE TABLE IF NOT EXISTS line_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    sport TEXT NOT NULL,
    bet_type TEXT NOT NULL,  -- 'spread', 'total', 'moneyline'
    sportsbook TEXT,         -- NULL for consensus movement

    -- Movement details
    old_line DECIMAL,
    new_line DECIMAL,
    old_odds INTEGER,
    new_odds INTEGER,

    -- Classification
    direction TEXT,          -- 'toward_favorite', 'toward_underdog', 'over', 'under'
    magnitude DECIMAL,
    movement_type TEXT,      -- 'steam', 'rlm', 'gradual', 'buyback', 'correction'
    confidence DECIMAL,      -- 0-1 confidence in classification
    interpretation TEXT,

    -- Context
    is_significant BOOLEAN DEFAULT FALSE,
    public_side TEXT,        -- Which side public was on when movement happened

    detected_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_movements_game ON line_movements(game_id, detected_at);
CREATE INDEX idx_movements_type ON line_movements(movement_type) WHERE is_significant = TRUE;
CREATE INDEX idx_movements_recent ON line_movements(detected_at DESC);


-- ============================================
-- PUBLIC BETTING DATA
-- Ticket and money percentages
-- ============================================

CREATE TABLE IF NOT EXISTS public_betting (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    sport TEXT NOT NULL,
    home_team TEXT,
    away_team TEXT,

    -- Spread betting percentages
    spread_ticket_home DECIMAL,
    spread_ticket_away DECIMAL,
    spread_money_home DECIMAL,
    spread_money_away DECIMAL,

    -- Total betting percentages
    total_ticket_over DECIMAL,
    total_ticket_under DECIMAL,
    total_money_over DECIMAL,
    total_money_under DECIMAL,

    -- Moneyline betting percentages
    ml_ticket_home DECIMAL,
    ml_ticket_away DECIMAL,
    ml_money_home DECIMAL,
    ml_money_away DECIMAL,

    -- Sharp money indicators
    spread_sharp_side TEXT,
    spread_divergence DECIMAL,
    total_sharp_side TEXT,
    total_divergence DECIMAL,

    source TEXT NOT NULL,    -- 'action_network', 'covers', 'manual', etc.
    captured_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_public_betting_game ON public_betting(game_id);
CREATE INDEX idx_public_betting_recent ON public_betting(captured_at DESC);


-- ============================================
-- GAME WEATHER
-- Weather data for outdoor games
-- ============================================

CREATE TABLE IF NOT EXISTS game_weather (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL UNIQUE,
    sport TEXT NOT NULL,

    -- Venue info
    venue TEXT,
    is_dome BOOLEAN DEFAULT FALSE,
    is_retractable BOOLEAN DEFAULT FALSE,

    -- Weather conditions
    temperature DECIMAL,      -- Fahrenheit
    wind_speed DECIMAL,       -- MPH
    wind_direction TEXT,
    precipitation_chance DECIMAL,  -- 0-100
    precipitation_type TEXT,  -- 'rain', 'snow', 'sleet', NULL
    humidity DECIMAL,         -- 0-100
    conditions TEXT,          -- 'Clear', 'Cloudy', 'Rain', etc.

    -- Calculated impact
    total_adjustment DECIMAL,
    spread_adjustment DECIMAL,
    impact_level TEXT,        -- 'none', 'minor', 'moderate', 'severe'

    source TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_weather_game ON game_weather(game_id);


-- ============================================
-- VALUE PLAYS
-- Detected +EV betting opportunities
-- ============================================

CREATE TABLE IF NOT EXISTS value_plays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    game TEXT NOT NULL,       -- "Chiefs vs Raiders"
    sport TEXT NOT NULL,
    bet_type TEXT NOT NULL,   -- 'spread', 'total', 'moneyline'
    side TEXT NOT NULL,       -- "Chiefs -3", "Over 45.5", "Raiders ML"
    sportsbook TEXT NOT NULL,

    -- Value metrics
    market_odds INTEGER NOT NULL,
    model_probability DECIMAL NOT NULL,
    implied_probability DECIMAL NOT NULL,
    fair_odds INTEGER,
    edge_percentage DECIMAL NOT NULL,
    ev_percentage DECIMAL NOT NULL,
    confidence TEXT NOT NULL,  -- 'HIGH', 'MEDIUM', 'LOW'

    -- Lifecycle
    game_start_time TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,

    -- Outcome tracking
    result TEXT,              -- 'win', 'loss', 'push', NULL if pending
    actual_clv DECIMAL,       -- Closing line value if tracked

    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_value_plays_active ON value_plays(created_at DESC) WHERE is_active = TRUE;
CREATE INDEX idx_value_plays_game ON value_plays(game_id);
CREATE INDEX idx_value_plays_confidence ON value_plays(confidence, ev_percentage DESC) WHERE is_active = TRUE;


-- ============================================
-- ARBITRAGE OPPORTUNITIES
-- Guaranteed profit opportunities across books
-- ============================================

CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    game TEXT NOT NULL,
    sport TEXT NOT NULL,
    bet_type TEXT NOT NULL,

    -- Side A
    book_a TEXT NOT NULL,
    side_a TEXT NOT NULL,
    odds_a INTEGER NOT NULL,
    stake_a_percentage DECIMAL NOT NULL,

    -- Side B
    book_b TEXT NOT NULL,
    side_b TEXT NOT NULL,
    odds_b INTEGER NOT NULL,
    stake_b_percentage DECIMAL NOT NULL,

    -- Profit
    profit_percentage DECIMAL NOT NULL,
    total_implied DECIMAL NOT NULL,

    -- Lifecycle
    is_active BOOLEAN DEFAULT TRUE,
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    expired_at TIMESTAMPTZ
);

CREATE INDEX idx_arb_active ON arbitrage_opportunities(detected_at DESC) WHERE is_active = TRUE;
CREATE INDEX idx_arb_profit ON arbitrage_opportunities(profit_percentage DESC) WHERE is_active = TRUE;


-- ============================================
-- MIDDLE OPPORTUNITIES
-- Win-both-sides opportunities
-- ============================================

CREATE TABLE IF NOT EXISTS middle_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    game TEXT NOT NULL,
    sport TEXT NOT NULL,
    bet_type TEXT NOT NULL,

    -- Side details
    book_a TEXT NOT NULL,
    line_a DECIMAL NOT NULL,
    odds_a INTEGER NOT NULL,

    book_b TEXT NOT NULL,
    line_b DECIMAL NOT NULL,
    odds_b INTEGER NOT NULL,

    -- Middle range
    middle_low DECIMAL NOT NULL,
    middle_high DECIMAL NOT NULL,
    middle_width DECIMAL NOT NULL,
    hit_probability DECIMAL NOT NULL,

    -- Expected value
    expected_value DECIMAL,
    ev_percentage DECIMAL,

    -- Lifecycle
    is_active BOOLEAN DEFAULT TRUE,
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    expired_at TIMESTAMPTZ,

    -- Outcome
    final_margin DECIMAL,     -- Actual margin of victory
    result TEXT               -- 'hit', 'miss_a', 'miss_b'
);

CREATE INDEX idx_middle_active ON middle_opportunities(detected_at DESC) WHERE is_active = TRUE;


-- ============================================
-- SCHEDULE DATA
-- Rest and travel information
-- ============================================

CREATE TABLE IF NOT EXISTS team_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    team TEXT NOT NULL,
    sport TEXT NOT NULL,
    is_home BOOLEAN NOT NULL,

    -- Rest info
    rest_days INTEGER,
    games_last_7_days INTEGER,
    games_last_14_days INTEGER,
    is_back_to_back BOOLEAN DEFAULT FALSE,
    is_3_in_4 BOOLEAN DEFAULT FALSE,
    is_4_in_5 BOOLEAN DEFAULT FALSE,

    -- Travel info
    travel_miles INTEGER,
    timezone_change INTEGER,
    previous_location TEXT,

    -- Context
    previous_opponent TEXT,
    previous_result TEXT,     -- 'W', 'L'
    previous_margin INTEGER,
    next_opponent TEXT,

    -- Calculated edge
    schedule_edge DECIMAL,    -- Point adjustment

    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(game_id, team)
);

CREATE INDEX idx_schedules_game ON team_schedules(game_id);
CREATE INDEX idx_schedules_team ON team_schedules(team, sport);


-- ============================================
-- INJURIES
-- Player injury tracking
-- ============================================

CREATE TABLE IF NOT EXISTS injuries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team TEXT NOT NULL,
    sport TEXT NOT NULL,
    player_name TEXT NOT NULL,
    position TEXT,

    -- Status
    status TEXT NOT NULL,     -- 'Out', 'Doubtful', 'Questionable', 'Probable', 'IR'
    injury_type TEXT,         -- 'Knee', 'Ankle', 'Concussion', etc.
    injury_details TEXT,

    -- Impact assessment
    impact_rating DECIMAL,    -- 0-10 scale
    spread_impact DECIMAL,    -- Estimated point impact
    is_key_player BOOLEAN DEFAULT FALSE,

    -- Dates
    injury_date DATE,
    expected_return DATE,

    source TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(team, sport, player_name)
);

CREATE INDEX idx_injuries_team ON injuries(team, sport);
CREATE INDEX idx_injuries_active ON injuries(status) WHERE status IN ('Out', 'Doubtful', 'Questionable');


-- ============================================
-- MODEL PROJECTIONS (Enhanced)
-- Store model outputs with confidence intervals
-- ============================================

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


-- ============================================
-- USER ALERTS PREFERENCES
-- Per-user alert configuration
-- ============================================

CREATE TABLE IF NOT EXISTS user_alert_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Value alerts
    value_alerts_enabled BOOLEAN DEFAULT TRUE,
    min_ev_threshold DECIMAL DEFAULT 2.0,
    min_edge_threshold DECIMAL DEFAULT 2.0,
    value_confidence_filter TEXT DEFAULT 'MEDIUM',  -- 'HIGH', 'MEDIUM', 'LOW'

    -- Movement alerts
    movement_alerts_enabled BOOLEAN DEFAULT TRUE,
    min_movement_threshold DECIMAL DEFAULT 0.5,
    steam_alerts_only BOOLEAN DEFAULT FALSE,

    -- Arbitrage alerts
    arb_alerts_enabled BOOLEAN DEFAULT FALSE,
    min_arb_profit DECIMAL DEFAULT 1.0,

    -- Sport filters (NULL = all sports)
    sports_filter TEXT[],

    -- Delivery preferences
    dm_enabled BOOLEAN DEFAULT TRUE,
    channel_enabled BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id)
);


-- ============================================
-- ALERT DELIVERY LOG
-- Track which alerts were sent to whom
-- ============================================

CREATE TABLE IF NOT EXISTS alert_delivery_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    alert_type TEXT NOT NULL,  -- 'value', 'movement', 'arb', 'middle'

    -- Reference to source
    source_id UUID,            -- ID from value_plays, line_movements, etc.
    source_table TEXT,

    -- Delivery info
    channel_id TEXT,
    message_id TEXT,
    delivered_at TIMESTAMPTZ DEFAULT NOW(),

    -- User action
    clicked BOOLEAN DEFAULT FALSE,
    bet_placed BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_alert_log_user ON alert_delivery_log(user_id, delivered_at DESC);


-- ============================================
-- TRIGGERS
-- ============================================

-- Update timestamp triggers for new tables
CREATE TRIGGER update_game_weather_updated_at
    BEFORE UPDATE ON game_weather
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_team_schedules_updated_at
    BEFORE UPDATE ON team_schedules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_injuries_updated_at
    BEFORE UPDATE ON injuries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_alert_preferences_updated_at
    BEFORE UPDATE ON user_alert_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================
-- ROW LEVEL SECURITY
-- ============================================

-- Enable RLS on new tables
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

-- Service role policies (full access for backend)
CREATE POLICY "Service role full access" ON opening_lines FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access" ON consensus_lines FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access" ON line_movements FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access" ON public_betting FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access" ON game_weather FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access" ON value_plays FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access" ON arbitrage_opportunities FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access" ON middle_opportunities FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access" ON team_schedules FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access" ON injuries FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access" ON user_alert_preferences FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access" ON alert_delivery_log FOR ALL USING (auth.role() = 'service_role');


-- ============================================
-- HELPFUL VIEWS
-- ============================================

-- Active value plays view
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

-- Sharp money indicator view
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
    SELECT MAX(captured_at)
    FROM public_betting
    WHERE game_id = p.game_id
);

-- Recent line movements view
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
