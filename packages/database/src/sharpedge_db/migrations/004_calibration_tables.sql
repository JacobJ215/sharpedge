-- Migration 004: Calibration and Backtesting Tables
-- Stores model predictions and outcomes for statistical calibration

-- ============================================
-- MODEL PREDICTIONS TABLE
-- ============================================
-- Stores every prediction made by the model for later calibration
CREATE TABLE IF NOT EXISTS model_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_id TEXT UNIQUE NOT NULL,  -- External reference ID
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Prediction details
    market_type TEXT NOT NULL,  -- 'spread', 'total', 'moneyline'
    sport TEXT NOT NULL,
    game_id TEXT,
    game_description TEXT,

    -- Model output
    predicted_probability DECIMAL(5,4) NOT NULL,  -- 0.0000 to 1.0000
    predicted_edge DECIMAL(6,4),  -- Edge in probability points
    model_line DECIMAL(6,2),  -- Model's projected line
    market_line DECIMAL(6,2),  -- Market line at prediction time
    odds INTEGER NOT NULL,  -- American odds

    -- Outcome (filled in later)
    outcome BOOLEAN,  -- NULL = pending, true = won, false = lost
    resolved_at TIMESTAMPTZ,
    closing_line DECIMAL(6,2),  -- For CLV calculation
    closing_odds INTEGER,

    -- Metadata
    model_version TEXT,
    confidence_level TEXT,  -- PREMIUM, HIGH, MEDIUM, LOW, SPECULATIVE

    CONSTRAINT valid_probability CHECK (predicted_probability >= 0 AND predicted_probability <= 1)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_predictions_market_type ON model_predictions(market_type);
CREATE INDEX IF NOT EXISTS idx_predictions_sport ON model_predictions(sport);
CREATE INDEX IF NOT EXISTS idx_predictions_created ON model_predictions(created_at);
CREATE INDEX IF NOT EXISTS idx_predictions_outcome ON model_predictions(outcome) WHERE outcome IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_predictions_pending ON model_predictions(created_at) WHERE outcome IS NULL;


-- ============================================
-- CALIBRATION REPORTS TABLE
-- ============================================
-- Stores computed calibration metrics for each model/market combination
CREATE TABLE IF NOT EXISTS calibration_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Scope
    market_type TEXT NOT NULL,
    sport TEXT,  -- NULL = all sports combined
    model_version TEXT,

    -- Sample info
    total_predictions INTEGER NOT NULL,
    total_resolved INTEGER NOT NULL,

    -- Calibration metrics
    brier_score DECIMAL(8,6),  -- 0 = perfect, lower is better
    calibration_error DECIMAL(8,6),  -- Mean absolute calibration error
    discrimination DECIMAL(6,4),  -- AUC-ROC equivalent

    -- Status
    status TEXT NOT NULL,  -- 'uncalibrated', 'preliminary', 'calibrated', 'well_calibrated'

    -- Calibration bins (stored as JSONB)
    -- Each bin: {prob_min, prob_max, predicted_avg, actual_rate, sample_size, ci_lower, ci_upper}
    bins JSONB NOT NULL DEFAULT '[]'::jsonb,

    CONSTRAINT valid_status CHECK (status IN ('uncalibrated', 'preliminary', 'calibrated', 'well_calibrated'))
);

-- Unique constraint on scope
CREATE UNIQUE INDEX IF NOT EXISTS idx_calibration_scope
ON calibration_reports(market_type, COALESCE(sport, ''), COALESCE(model_version, ''));


-- ============================================
-- CALIBRATION HISTORY TABLE
-- ============================================
-- Tracks calibration over time to detect model drift
CREATE TABLE IF NOT EXISTS calibration_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    market_type TEXT NOT NULL,
    sport TEXT,

    -- Snapshot of key metrics
    brier_score DECIMAL(8,6),
    calibration_error DECIMAL(8,6),
    total_resolved INTEGER,
    status TEXT
);

CREATE INDEX IF NOT EXISTS idx_calibration_history_time ON calibration_history(recorded_at);


-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to get calibration status based on sample size
CREATE OR REPLACE FUNCTION get_calibration_status(resolved_count INTEGER)
RETURNS TEXT AS $$
BEGIN
    IF resolved_count < 30 THEN
        RETURN 'uncalibrated';
    ELSIF resolved_count < 100 THEN
        RETURN 'preliminary';
    ELSIF resolved_count < 1000 THEN
        RETURN 'calibrated';
    ELSE
        RETURN 'well_calibrated';
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;


-- Function to calculate Wilson score confidence interval
CREATE OR REPLACE FUNCTION wilson_score_interval(
    successes INTEGER,
    total INTEGER,
    confidence DECIMAL DEFAULT 0.95
)
RETURNS TABLE(ci_lower DECIMAL, ci_upper DECIMAL) AS $$
DECLARE
    z DECIMAL;
    p_hat DECIMAL;
    denominator DECIMAL;
    center DECIMAL;
    margin DECIMAL;
BEGIN
    IF total = 0 THEN
        RETURN QUERY SELECT 0::DECIMAL, 1::DECIMAL;
        RETURN;
    END IF;

    -- Z-score for 95% CI
    z := 1.96;
    p_hat := successes::DECIMAL / total;

    denominator := 1 + z * z / total;
    center := (p_hat + z * z / (2 * total)) / denominator;
    margin := z * SQRT((p_hat * (1 - p_hat) + z * z / (4 * total)) / total) / denominator;

    RETURN QUERY SELECT
        GREATEST(0, center - margin)::DECIMAL,
        LEAST(1, center + margin)::DECIMAL;
END;
$$ LANGUAGE plpgsql IMMUTABLE;


-- ============================================
-- ROW LEVEL SECURITY
-- ============================================
ALTER TABLE model_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE calibration_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE calibration_history ENABLE ROW LEVEL SECURITY;

-- Service role has full access
CREATE POLICY "Service role full access to predictions"
ON model_predictions FOR ALL TO service_role USING (true);

CREATE POLICY "Service role full access to calibration_reports"
ON calibration_reports FOR ALL TO service_role USING (true);

CREATE POLICY "Service role full access to calibration_history"
ON calibration_history FOR ALL TO service_role USING (true);


-- ============================================
-- COMMENTS
-- ============================================
COMMENT ON TABLE model_predictions IS 'Stores model predictions for backtesting and calibration';
COMMENT ON TABLE calibration_reports IS 'Computed calibration metrics for each model/market';
COMMENT ON TABLE calibration_history IS 'Historical calibration snapshots for drift detection';
COMMENT ON COLUMN model_predictions.predicted_probability IS 'Model probability estimate (0-1)';
COMMENT ON COLUMN model_predictions.outcome IS 'NULL=pending, true=won, false=lost';
COMMENT ON COLUMN calibration_reports.brier_score IS 'Brier score: 0=perfect, lower=better';
COMMENT ON COLUMN calibration_reports.bins IS 'JSONB array of calibration bins with CI';
