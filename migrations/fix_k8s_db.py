"""Fix K8s database: add holding_type, clear journal, buy TSLY, add snapshot."""
import psycopg2

conn = psycopg2.connect(
    host='postgres-timeseries-service', port=5432,
    dbname='trading_data', user='trading', password='trading_password'
)
conn.autocommit = False
cur = conn.cursor()

# 1. Add holding_type column to trade_journal
cur.execute("ALTER TABLE trade_journal ADD COLUMN IF NOT EXISTS holding_type VARCHAR(20) DEFAULT 'swing'")
cur.execute("CREATE INDEX IF NOT EXISTS idx_journal_holding_type ON trade_journal(holding_type)")
print("Added holding_type column")

# 2. Clear old journal entries
cur.execute("DELETE FROM trade_journal")
print(f"Cleared {cur.rowcount} old journal entries")

# 3. Buy TSLY
tsly_price = 17.50
lt_target = 50000.0
shares = int(lt_target / tsly_price)
total_cost = shares * tsly_price

cur.execute("""
    INSERT INTO portfolio_holdings
        (ticker, holding_type, asset_type, quantity, avg_cost_basis, current_price,
         market_value, unrealized_pnl, unrealized_pnl_pct, entry_date, entry_signal,
         entry_rationale)
    VALUES ('TSLY', 'long_term', 'stock', %s, %s, %s, %s, 0, 0, NOW(),
            'tsly_default_yield', 'Consolidated LT allocation into TSLY yield (proof of concept)')
""", (shares, tsly_price, tsly_price, total_cost))
print(f"Created TSLY holding: {shares} shares @ ${tsly_price}")

cur.execute("""
    INSERT INTO portfolio_transactions
        (transaction_id, ticker, action, holding_type, asset_type, quantity, price, total_value,
         signal_source, signal_details, executed_at)
    VALUES (gen_random_uuid(), 'TSLY', 'buy', 'long_term', 'stock', %s, %s, %s,
            'tsly_default_yield',
            '{"reason": "Consolidated LT allocation into TSLY yield position (proof of concept)"}',
            NOW())
""", (shares, tsly_price, total_cost))

# 4. Update cash
cur.execute("UPDATE portfolio_account SET cash_balance = cash_balance - %s, updated_at = NOW() WHERE id = 1", (total_cost,))
cur.execute("SELECT cash_balance FROM portfolio_account WHERE id = 1")
cash = float(cur.fetchone()[0])
print(f"Cash balance: ${cash:.2f}")

# 5. Journal entry for TSLY
cur.execute("""
    INSERT INTO trade_journal (user_id, ticker, trade_date, direction, entry_price, quantity,
        holding_type, signal_source, entry_notes)
    VALUES (2, 'TSLY', CURRENT_DATE, 'long', %s, %s, 'tsly_yield', 'tsly_default_yield',
            'TSLY yield position - consolidated LT allocation (proof of concept)')
""", (tsly_price, shares))
print("Created TSLY journal entry")

# 6. Performance snapshot
holdings_val = total_cost
total = cash + holdings_val
starting = 100000.0
cur.execute("""
    INSERT INTO portfolio_performance
        (snapshot_date, total_value, cash_balance, holdings_value, long_term_value, swing_value,
         daily_pnl, daily_pnl_pct, total_pnl, total_pnl_pct, win_rate,
         open_positions, long_term_positions, swing_positions)
    VALUES (%s, %s, %s, %s, %s, 0, 0, 0, %s, %s, 0, 1, 1, 0)
    ON CONFLICT (snapshot_date) DO UPDATE SET
        total_value = EXCLUDED.total_value,
        cash_balance = EXCLUDED.cash_balance,
        holdings_value = EXCLUDED.holdings_value,
        long_term_value = EXCLUDED.long_term_value,
        open_positions = EXCLUDED.open_positions,
        long_term_positions = EXCLUDED.long_term_positions
""", ('2026-04-03', total, cash, holdings_val, holdings_val, total - starting, (total - starting) / starting))
print(f"Snapshot: total=${total:.2f}, P&L=${total - starting:.2f}")

conn.commit()
print("DONE - all changes committed")
conn.close()
