-- Migration 007: Trading Swarm Tables
-- Supports the autonomous multi-agent trading daemon (packages/trading_swarm)

-- ============================================
-- PAPER TRADES
-- Every simulated (paper) and live trade executed by the daemon.
-- ============================================
CREATE TABLE IF NOT EXISTS paper_trades (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    market_id          TEXT NOT NULL,
    direction          TEXT NOT NULL CHECK (direction IN ('yes', 'no')),
    size               NUMERIC NOT NULL,                -- dollars
    entry_price        NUMERIC NOT NULL,                -- 0-1
    exit_price         NUMERIC,                         -- 0-1, null until settled
    pnl                NUMERIC,                         -- null until settled
    confidence_score   NUMERIC,                         -- at time of trade
    category           TEXT CHECK (category IN ('political','economic','crypto','entertainment','weather')),
    trading_mode       TEXT NOT NULL CHECK (trading_mode IN ('paper','live')),
    idempotency_key    TEXT UNIQUE,                     -- prevents duplicate fills
    opened_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at        TIMESTAMPTZ,
    actual_outcome     BOOLEAN                          -- null until settled
);

CREATE INDEX IF NOT EXISTS idx_paper_trades_market   ON paper_trades (market_id);
CREATE INDEX IF NOT EXISTS idx_paper_trades_mode     ON paper_trades (trading_mode);
CREATE INDEX IF NOT EXISTS idx_paper_trades_opened   ON paper_trades (opened_at DESC);
CREATE INDEX IF NOT EXISTS idx_paper_trades_resolved ON paper_trades (resolved_at DESC);

ALTER TABLE paper_trades ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access to paper_trades"
    ON paper_trades FOR ALL TO service_role USING (true);


-- ============================================
-- LIVE TRADES
-- Real orders placed via KalshiExecutor (TRADING_MODE=live).
-- Separate table from paper_trades for audit safety.
-- ============================================
CREATE TABLE IF NOT EXISTS live_trades (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    market_id          TEXT NOT NULL,
    direction          TEXT NOT NULL CHECK (direction IN ('yes', 'no')),
    size               NUMERIC NOT NULL,
    entry_price        NUMERIC NOT NULL,
    exit_price         NUMERIC,
    pnl                NUMERIC,
    confidence_score   NUMERIC,
    category           TEXT,
    trading_mode       TEXT NOT NULL DEFAULT 'live',
    idempotency_key    TEXT UNIQUE,
    kalshi_order_id    TEXT,                            -- order ID from Kalshi REST API
    opened_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at        TIMESTAMPTZ,
    actual_outcome     BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_live_trades_market ON live_trades (market_id);
CREATE INDEX IF NOT EXISTS idx_live_trades_opened ON live_trades (opened_at DESC);

ALTER TABLE live_trades ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access to live_trades"
    ON live_trades FOR ALL TO service_role USING (true);


-- ============================================
-- OPEN POSITIONS
-- Tracks positions currently held, pending settlement.
-- Monitor agent polls this table every 60 seconds.
-- ============================================
CREATE TABLE IF NOT EXISTS open_positions (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    market_id                TEXT NOT NULL,
    size                     NUMERIC NOT NULL,
    entry_price              NUMERIC NOT NULL,
    expected_resolution_time TIMESTAMPTZ,
    trading_mode             TEXT NOT NULL CHECK (trading_mode IN ('paper','live')),
    status                   TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','settling','settled')),
    opened_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at              TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_open_positions_status ON open_positions (status);
CREATE INDEX IF NOT EXISTS idx_open_positions_mode   ON open_positions (trading_mode, status);

ALTER TABLE open_positions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access to open_positions"
    ON open_positions FOR ALL TO service_role USING (true);


-- ============================================
-- TRADE POST MORTEMS
-- Loss attribution written by Post-Mortem Agent after each losing trade.
-- ============================================
CREATE TABLE IF NOT EXISTS trade_post_mortems (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_id            UUID,                           -- references paper_trades.id or live_trades.id
    model_error_score   NUMERIC NOT NULL DEFAULT 0 CHECK (model_error_score BETWEEN 0 AND 1),
    signal_error_score  NUMERIC NOT NULL DEFAULT 0 CHECK (signal_error_score BETWEEN 0 AND 1),
    sizing_error_score  NUMERIC NOT NULL DEFAULT 0 CHECK (sizing_error_score BETWEEN 0 AND 1),
    variance_score      NUMERIC NOT NULL DEFAULT 0 CHECK (variance_score BETWEEN 0 AND 1),
    llm_narrative       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_post_mortems_trade   ON trade_post_mortems (trade_id);
CREATE INDEX IF NOT EXISTS idx_post_mortems_created ON trade_post_mortems (created_at DESC);

ALTER TABLE trade_post_mortems ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access to trade_post_mortems"
    ON trade_post_mortems FOR ALL TO service_role USING (true);


-- ============================================
-- TRADING CONFIG
-- Runtime-adjustable parameters for the daemon.
-- Post-mortem agent writes bounded updates here.
-- ============================================
CREATE TABLE IF NOT EXISTS trading_config (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT DEFAULT 'human'     -- 'post_mortem_agent' | 'human'
);

ALTER TABLE trading_config ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access to trading_config"
    ON trading_config FOR ALL TO service_role USING (true);

-- Insert defaults (idempotent)
INSERT INTO trading_config (key, value, updated_by) VALUES
    ('confidence_threshold',   '0.03', 'human'),
    ('kelly_fraction',         '0.25', 'human'),
    ('max_category_exposure',  '0.20', 'human'),
    ('max_total_exposure',     '0.40', 'human'),
    ('daily_loss_limit',       '0.10', 'human'),
    ('min_liquidity',          '500',  'human'),
    ('min_edge',               '0.03', 'human')
ON CONFLICT (key) DO NOTHING;


-- ============================================
-- CIRCUIT BREAKER STATE
-- Tracks active circuit breakers (daily loss, consecutive losses, etc.)
-- Risk Agent reads this before each trade.
-- ============================================
CREATE TABLE IF NOT EXISTS circuit_breaker_state (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    breaker_type          TEXT NOT NULL CHECK (breaker_type IN (
                              'daily_loss', 'consecutive_losses', 'exposure', 'api_error'
                          )),
    triggered_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resume_at             TIMESTAMPTZ,
    consecutive_loss_count INT NOT NULL DEFAULT 0,
    daily_loss_amount     NUMERIC NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_circuit_breaker_type ON circuit_breaker_state (breaker_type, triggered_at DESC);

ALTER TABLE circuit_breaker_state ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access to circuit_breaker_state"
    ON circuit_breaker_state FOR ALL TO service_role USING (true);


-- ============================================
-- TRADE RESEARCH LOG
-- Research artifact snapshot for each trade (optional, for post-mortem debugging).
-- Post-mortem agent reads calibrated_prob + llm_adjustment from here.
-- ============================================
CREATE TABLE IF NOT EXISTS trade_research_log (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_id         UUID,                              -- references paper_trades.id
    market_id        TEXT,
    signal_breakdown JSONB,                             -- per-source sentiment scores
    rf_probability   NUMERIC,                           -- base Phase 9 model output (0-1)
    llm_adjustment   NUMERIC,                           -- delta applied by LLM calibrator
    final_edge       NUMERIC,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_research_log_trade ON trade_research_log (trade_id);

ALTER TABLE trade_research_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access to trade_research_log"
    ON trade_research_log FOR ALL TO service_role USING (true);
