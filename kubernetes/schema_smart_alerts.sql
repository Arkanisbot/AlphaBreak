-- Smart Alerts + Password Reset
-- Rule-based price/indicator alerts and self-service password reset tokens.

CREATE TABLE IF NOT EXISTS user_alert_rules (
    id                SERIAL PRIMARY KEY,
    user_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name              VARCHAR(120) NOT NULL,
    ticker            VARCHAR(12) NOT NULL,
    conditions        JSONB NOT NULL,
    cooldown_seconds  INTEGER NOT NULL DEFAULT 86400,
    email_enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    in_app_enabled    BOOLEAN NOT NULL DEFAULT TRUE,
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    last_triggered_at TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_rules_user_active
    ON user_alert_rules (user_id, is_active);

CREATE INDEX IF NOT EXISTS idx_alert_rules_ticker_active
    ON user_alert_rules (ticker) WHERE is_active;

CREATE TABLE IF NOT EXISTS alert_rule_firings (
    id              SERIAL PRIMARY KEY,
    rule_id         INTEGER NOT NULL REFERENCES user_alert_rules(id) ON DELETE CASCADE,
    fired_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    matched_values  JSONB NOT NULL,
    notification_id INTEGER REFERENCES notifications(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_alert_firings_rule_time
    ON alert_rule_firings (rule_id, fired_at DESC);

-- Password reset tokens (one-shot, hashed, 1-hour TTL)
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  CHAR(64) NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address  VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_password_reset_user
    ON password_reset_tokens (user_id, created_at DESC);
