-- ============================================================================
-- Forex Data Schema
-- ============================================================================
-- Tables for storing forex historical data, correlation patterns, and trend breaks.
-- Supports the Forex Correlation Model for AlphaBreak.

-- ──────────────────────────────────────────────────────────────────────────────
-- Core Forex Data Tables
-- ──────────────────────────────────────────────────────────────────────────────

-- Main forex daily data table (all pairs)
CREATE TABLE IF NOT EXISTS forex_daily_data (
    id SERIAL PRIMARY KEY,
    pair VARCHAR(10) NOT NULL,           -- e.g., 'EUR/USD', 'USD/JPY'
    date DATE NOT NULL,
    open DECIMAL(18, 8),
    high DECIMAL(18, 8),
    low DECIMAL(18, 8),
    close DECIMAL(18, 8) NOT NULL,
    volume BIGINT DEFAULT 0,
    source VARCHAR(20) DEFAULT 'FRED',   -- 'FRED', 'Yahoo', 'combined'

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(pair, date)
);

-- Forex pairs metadata
CREATE TABLE IF NOT EXISTS forex_pairs (
    id SERIAL PRIMARY KEY,
    pair VARCHAR(10) NOT NULL UNIQUE,    -- e.g., 'EUR/USD'
    base_currency VARCHAR(3) NOT NULL,   -- e.g., 'EUR'
    quote_currency VARCHAR(3) NOT NULL,  -- e.g., 'USD'

    -- Data availability
    data_start_date DATE,
    data_end_date DATE,
    total_records INTEGER DEFAULT 0,

    -- Model status
    model_trained BOOLEAN DEFAULT FALSE,
    model_trained_at TIMESTAMPTZ,
    model_version VARCHAR(20),

    -- Statistics
    avg_daily_range DECIMAL(10, 6),      -- Average daily movement %
    volatility_30d DECIMAL(10, 6),       -- 30-day volatility

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ──────────────────────────────────────────────────────────────────────────────
-- Trend Break Analysis for Forex
-- ──────────────────────────────────────────────────────────────────────────────

-- Notable movements / trend breaks for each currency pair
CREATE TABLE IF NOT EXISTS forex_trend_breaks (
    id SERIAL PRIMARY KEY,
    pair VARCHAR(10) NOT NULL,
    break_date DATE NOT NULL,

    -- Break characteristics
    break_direction VARCHAR(10) NOT NULL,    -- 'bullish', 'bearish'
    break_probability DECIMAL(5, 4),         -- 0.8000 to 1.0000
    confidence DECIMAL(5, 4),

    -- Price context
    price_at_break DECIMAL(18, 8) NOT NULL,
    price_before_5d DECIMAL(18, 8),          -- Price 5 days before
    price_after_5d DECIMAL(18, 8),           -- Price 5 days after (filled later)
    movement_pct DECIMAL(8, 4),              -- % move that triggered break

    -- Indicator values at break
    rsi_value DECIMAL(6, 2),
    cci_value DECIMAL(10, 2),
    macd_histogram DECIMAL(12, 8),
    stochastic_k DECIMAL(6, 2),
    stochastic_d DECIMAL(6, 2),
    adx_value DECIMAL(6, 2),

    -- Bollinger Band position
    bb_position VARCHAR(20),                 -- 'above_upper', 'below_lower', 'within'

    -- Outcome tracking (filled after the fact)
    outcome_5d_pct DECIMAL(8, 4),            -- Actual 5-day return
    outcome_10d_pct DECIMAL(8, 4),           -- Actual 10-day return
    outcome_20d_pct DECIMAL(8, 4),           -- Actual 20-day return
    was_correct BOOLEAN,                      -- Did price move in predicted direction?

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(pair, break_date)
);

-- ──────────────────────────────────────────────────────────────────────────────
-- Correlation Patterns
-- ──────────────────────────────────────────────────────────────────────────────

-- Correlation matrix between pairs (computed periodically)
CREATE TABLE IF NOT EXISTS forex_correlations (
    id SERIAL PRIMARY KEY,
    pair_a VARCHAR(10) NOT NULL,
    pair_b VARCHAR(10) NOT NULL,

    -- Correlation metrics
    correlation_30d DECIMAL(6, 4),           -- 30-day rolling correlation
    correlation_90d DECIMAL(6, 4),           -- 90-day rolling correlation
    correlation_1y DECIMAL(6, 4),            -- 1-year rolling correlation
    correlation_all DECIMAL(6, 4),           -- All-time correlation

    -- Pattern strength classification
    pattern_strength VARCHAR(10),            -- 'strong', 'mid', 'weak'

    -- Lead/lag relationship
    lead_lag_days INTEGER,                   -- Positive = A leads B, Negative = B leads A
    lead_lag_correlation DECIMAL(6, 4),      -- Correlation at optimal lag

    -- Calculation metadata
    calculation_date DATE NOT NULL,
    data_points INTEGER,                     -- Number of data points used

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(pair_a, pair_b, calculation_date)
);

-- Pattern strength thresholds (configurable)
CREATE TABLE IF NOT EXISTS forex_correlation_thresholds (
    id SERIAL PRIMARY KEY,
    calculation_date DATE NOT NULL,

    -- Threshold values (calculated from data distribution)
    strong_min DECIMAL(6, 4),                -- Minimum for 'strong' pattern
    mid_min DECIMAL(6, 4),                   -- Minimum for 'mid' pattern
    weak_max DECIMAL(6, 4),                  -- Maximum for 'weak' pattern

    -- Statistics
    max_correlation DECIMAL(6, 4),
    min_correlation DECIMAL(6, 4),
    avg_correlation DECIMAL(6, 4),

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(calculation_date)
);

-- ──────────────────────────────────────────────────────────────────────────────
-- Forex-Equity Correlations (for cross-asset analysis)
-- ──────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS forex_equity_correlations (
    id SERIAL PRIMARY KEY,
    forex_pair VARCHAR(10) NOT NULL,
    equity_symbol VARCHAR(10) NOT NULL,      -- Stock ticker or sector ETF
    equity_type VARCHAR(20) NOT NULL,        -- 'stock', 'sector_etf', 'index'

    -- Correlation metrics
    correlation_30d DECIMAL(6, 4),
    correlation_90d DECIMAL(6, 4),
    correlation_1y DECIMAL(6, 4),

    -- Lead/lag analysis
    lead_lag_days INTEGER,
    lead_lag_correlation DECIMAL(6, 4),

    -- Pattern classification
    pattern_strength VARCHAR(10),            -- 'strong', 'mid', 'weak'
    relationship_type VARCHAR(20),           -- 'positive', 'negative', 'neutral'

    calculation_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(forex_pair, equity_symbol, calculation_date)
);

-- ──────────────────────────────────────────────────────────────────────────────
-- Model Training Results
-- ──────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS forex_models (
    id SERIAL PRIMARY KEY,
    pair VARCHAR(10) NOT NULL,
    model_type VARCHAR(30) NOT NULL,         -- 'correlation', 'trend_break', 'combined'
    model_version VARCHAR(20) NOT NULL,

    -- Training info
    trained_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    training_start_date DATE,
    training_end_date DATE,
    training_samples INTEGER,

    -- Model performance
    accuracy DECIMAL(5, 4),
    precision_score DECIMAL(5, 4),
    recall DECIMAL(5, 4),
    f1_score DECIMAL(5, 4),

    -- Pattern counts from training
    strong_patterns INTEGER DEFAULT 0,
    mid_patterns INTEGER DEFAULT 0,
    weak_patterns INTEGER DEFAULT 0,

    -- Model artifact
    model_path VARCHAR(255),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ──────────────────────────────────────────────────────────────────────────────
-- Indexes for Performance
-- ──────────────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_forex_daily_pair ON forex_daily_data (pair);
CREATE INDEX IF NOT EXISTS idx_forex_daily_date ON forex_daily_data (date DESC);
CREATE INDEX IF NOT EXISTS idx_forex_daily_pair_date ON forex_daily_data (pair, date DESC);

CREATE INDEX IF NOT EXISTS idx_forex_breaks_pair ON forex_trend_breaks (pair);
CREATE INDEX IF NOT EXISTS idx_forex_breaks_date ON forex_trend_breaks (break_date DESC);
CREATE INDEX IF NOT EXISTS idx_forex_breaks_direction ON forex_trend_breaks (pair, break_direction);

CREATE INDEX IF NOT EXISTS idx_forex_corr_pairs ON forex_correlations (pair_a, pair_b);
CREATE INDEX IF NOT EXISTS idx_forex_corr_date ON forex_correlations (calculation_date DESC);
CREATE INDEX IF NOT EXISTS idx_forex_corr_strength ON forex_correlations (pattern_strength);

CREATE INDEX IF NOT EXISTS idx_forex_equity_forex ON forex_equity_correlations (forex_pair);
CREATE INDEX IF NOT EXISTS idx_forex_equity_symbol ON forex_equity_correlations (equity_symbol);

-- ──────────────────────────────────────────────────────────────────────────────
-- Grants
-- ──────────────────────────────────────────────────────────────────────────────

GRANT ALL PRIVILEGES ON forex_daily_data TO trading;
GRANT ALL PRIVILEGES ON forex_pairs TO trading;
GRANT ALL PRIVILEGES ON forex_trend_breaks TO trading;
GRANT ALL PRIVILEGES ON forex_correlations TO trading;
GRANT ALL PRIVILEGES ON forex_correlation_thresholds TO trading;
GRANT ALL PRIVILEGES ON forex_equity_correlations TO trading;
GRANT ALL PRIVILEGES ON forex_models TO trading;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO trading;
