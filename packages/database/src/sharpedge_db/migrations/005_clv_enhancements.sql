-- Migration 005: CLV (Closing Line Value) Enhancements
-- Adds columns needed for proper CLV calculation and tracking

-- ============================================
-- ENHANCE BETS TABLE FOR CLV
-- ============================================

-- Add closing odds columns for proper CLV calculation
-- CLV needs both the line AND the odds at close
ALTER TABLE bets
ADD COLUMN IF NOT EXISTS opening_odds INTEGER,
ADD COLUMN IF NOT EXISTS closing_odds INTEGER,
ADD COLUMN IF NOT EXISTS clv_percentage DECIMAL(6, 3),
ADD COLUMN IF NOT EXISTS beat_closing_line BOOLEAN;

-- Add no-vig fair probability at bet time
ALTER TABLE bets
ADD COLUMN IF NOT EXISTS fair_prob_at_bet DECIMAL(6, 4),
ADD COLUMN IF NOT EXISTS fair_prob_at_close DECIMAL(6, 4);

COMMENT ON COLUMN bets.opening_odds IS 'American odds when market opened';
COMMENT ON COLUMN bets.closing_odds IS 'American odds at market close (game start)';
COMMENT ON COLUMN bets.clv_percentage IS 'CLV as percentage: (fair_close - implied_bet) * 100';
COMMENT ON COLUMN bets.beat_closing_line IS 'True if bet odds were better than closing odds';
COMMENT ON COLUMN bets.fair_prob_at_bet IS 'No-vig fair probability when bet was placed';
COMMENT ON COLUMN bets.fair_prob_at_close IS 'No-vig fair probability at market close';


-- ============================================
-- CLOSING LINES TABLE
-- Stores closing odds for all games
-- ============================================

CREATE TABLE IF NOT EXISTS closing_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id TEXT NOT NULL,
    sport TEXT NOT NULL,
    bet_type TEXT NOT NULL,  -- 'spread', 'total', 'moneyline'
    sportsbook TEXT NOT NULL,

    -- Closing values
    line DECIMAL,
    odds_side1 INTEGER,  -- Home spread odds, Over odds, Home ML
    odds_side2 INTEGER,  -- Away spread odds, Under odds, Away ML

    -- No-vig fair values
    fair_prob_side1 DECIMAL(6, 4),
    fair_prob_side2 DECIMAL(6, 4),
    vig_percentage DECIMAL(4, 2),

    -- Metadata
    game_start_time TIMESTAMPTZ,
    captured_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(game_id, sportsbook, bet_type)
);

CREATE INDEX IF NOT EXISTS idx_closing_lines_game ON closing_lines(game_id);
CREATE INDEX IF NOT EXISTS idx_closing_lines_time ON closing_lines(game_start_time);


-- ============================================
-- CLV AGGREGATE VIEW
-- Summary statistics for CLV tracking
-- ============================================

CREATE OR REPLACE VIEW user_clv_summary AS
SELECT
    user_id,
    sport,
    bet_type,
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


-- ============================================
-- FUNCTION: Calculate CLV for a bet
-- ============================================

CREATE OR REPLACE FUNCTION calculate_clv(
    p_bet_odds INTEGER,
    p_closing_odds INTEGER
)
RETURNS DECIMAL AS $$
DECLARE
    v_bet_implied DECIMAL;
    v_close_implied DECIMAL;
    v_clv DECIMAL;
BEGIN
    -- Convert American odds to implied probability
    IF p_bet_odds > 0 THEN
        v_bet_implied := 100.0 / (p_bet_odds + 100);
    ELSE
        v_bet_implied := ABS(p_bet_odds)::DECIMAL / (ABS(p_bet_odds) + 100);
    END IF;

    IF p_closing_odds > 0 THEN
        v_close_implied := 100.0 / (p_closing_odds + 100);
    ELSE
        v_close_implied := ABS(p_closing_odds)::DECIMAL / (ABS(p_closing_odds) + 100);
    END IF;

    -- CLV = (closing_implied - bet_implied) * 100
    -- Positive = you got a better price than closing
    v_clv := (v_close_implied - v_bet_implied) * 100;

    RETURN ROUND(v_clv, 3);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION calculate_clv IS 'Calculate CLV in percentage points. Positive = bet was better than close.';


-- ============================================
-- FUNCTION: Update bet CLV when closing line is captured
-- ============================================

CREATE OR REPLACE FUNCTION update_bet_clv()
RETURNS TRIGGER AS $$
BEGIN
    -- Update all pending bets for this game
    UPDATE bets b
    SET
        closing_line = NEW.line,
        closing_odds = CASE
            WHEN b.selection LIKE '%' || 'Over' || '%' OR b.bet_type = 'over' THEN NEW.odds_side1
            WHEN b.selection LIKE '%' || 'Under' || '%' OR b.bet_type = 'under' THEN NEW.odds_side2
            -- For spreads, need to match team
            ELSE NEW.odds_side1
        END,
        fair_prob_at_close = CASE
            WHEN b.selection LIKE '%' || 'Over' || '%' OR b.bet_type = 'over' THEN NEW.fair_prob_side1
            WHEN b.selection LIKE '%' || 'Under' || '%' OR b.bet_type = 'under' THEN NEW.fair_prob_side2
            ELSE NEW.fair_prob_side1
        END
    WHERE b.result = 'PENDING'
        AND b.game LIKE '%' || (
            SELECT COALESCE(
                (SELECT home_team FROM opening_lines WHERE game_id = NEW.game_id LIMIT 1),
                NEW.game_id
            )
        ) || '%';

    -- Calculate CLV for updated bets
    UPDATE bets
    SET
        clv_percentage = calculate_clv(odds, closing_odds),
        beat_closing_line = (calculate_clv(odds, closing_odds) > 0)
    WHERE closing_odds IS NOT NULL
        AND clv_percentage IS NULL;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ============================================
-- ODDS HISTORY ENHANCEMENTS
-- ============================================

-- Add composite market column for easier querying
ALTER TABLE odds_history
ADD COLUMN IF NOT EXISTS side TEXT,  -- 'home', 'away', 'over', 'under', 'draw'
ADD COLUMN IF NOT EXISTS game_start_time TIMESTAMPTZ;

-- Create index for closing line queries
CREATE INDEX IF NOT EXISTS idx_odds_history_close
ON odds_history(game_id, sportsbook, bet_type, recorded_at DESC);


-- ============================================
-- ROW LEVEL SECURITY
-- ============================================

ALTER TABLE closing_lines ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access to closing_lines"
ON closing_lines FOR ALL TO service_role USING (true);


-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON TABLE closing_lines IS 'Stores final closing odds for all games, captured at game start';
COMMENT ON VIEW user_clv_summary IS 'Aggregated CLV statistics per user, sport, and bet type';
