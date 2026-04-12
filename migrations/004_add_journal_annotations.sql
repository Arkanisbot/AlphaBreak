-- Migration 004: Add annotations JSONB column to trade_journal
-- Stores auto-generated market condition annotations at the time of trade entry.

ALTER TABLE trade_journal ADD COLUMN IF NOT EXISTS annotations JSONB;

COMMENT ON COLUMN trade_journal.annotations IS 'Auto-generated market signals/indicators snapshot at time of journal entry creation';
