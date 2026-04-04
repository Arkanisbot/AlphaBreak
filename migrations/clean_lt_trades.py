"""
Remove all LT stock trades (buys + sells) from history.
Keep only: TSLY position + swing trades + dividends.
Recalculate cash from scratch.
"""
import psycopg2

conn = psycopg2.connect(
    host='postgres-timeseries-service', port=5432,
    dbname='trading_data', user='trading', password='trading_password'
)
conn.autocommit = False
cur = conn.cursor()

# 1. Remove LT journal entries (not TSLY)
cur.execute("DELETE FROM trade_journal WHERE holding_type = 'long_term'")
print("Removed {} LT journal entries".format(cur.rowcount))

# 2. Remove LT transactions (not TSLY)
cur.execute("""
    DELETE FROM portfolio_transactions
    WHERE holding_type = 'long_term'
      AND ticker != 'TSLY'
""")
print("Removed {} LT transactions".format(cur.rowcount))

# 3. Verify what remains
cur.execute("""
    SELECT ticker, action, holding_type, COUNT(*)
    FROM portfolio_transactions
    GROUP BY ticker, action, holding_type
    ORDER BY ticker, action
""")
print("\nRemaining transactions:")
for r in cur.fetchall():
    print("  {} {} ({}): {}".format(r[0], r[1], r[2], r[3]))

# 4. Recalculate cash from scratch
# Cash = starting_balance + all transaction cash flows
cur.execute("""
    SELECT COALESCE(SUM(
        CASE WHEN action IN ('buy', 'buy_to_open') THEN -total_value
             WHEN action IN ('sell', 'sell_to_close') THEN total_value
             WHEN action = 'dividend' THEN total_value
             ELSE 0 END
    ), 0)
    FROM portfolio_transactions
""")
all_cash_flows = float(cur.fetchone()[0])
starting = 100000.0
correct_cash = starting + all_cash_flows

cur.execute("UPDATE portfolio_account SET cash_balance = %s, updated_at = NOW() WHERE id = 1",
            (correct_cash,))
print("\nCash flows: {:.2f}".format(all_cash_flows))
print("Cash balance: {:.2f}".format(correct_cash))

# 5. Get holdings value
cur.execute("SELECT SUM(market_value) FROM portfolio_holdings")
holdings = float(cur.fetchone()[0] or 0)
total = correct_cash + holdings
pnl = total - starting

print("\n--- Portfolio Summary ---")
print("Cash: ${:.2f}".format(correct_cash))
print("TSLY: ${:.2f}".format(holdings))
print("Total: ${:.2f}".format(total))
print("P&L: ${:.2f} ({:+.1f}%)".format(pnl, pnl / starting * 100))

# 6. Update performance snapshot
cur.execute("""
    UPDATE portfolio_performance
    SET total_value = %s, cash_balance = %s, holdings_value = %s,
        long_term_value = %s, swing_value = 0,
        total_pnl = %s, total_pnl_pct = %s,
        open_positions = 1, long_term_positions = 1, swing_positions = 0
    WHERE snapshot_date = '2026-04-03'
""", (total, correct_cash, holdings, holdings, pnl, pnl / starting))

# 7. Show final journal
cur.execute("SELECT id, ticker, holding_type, trade_date, realized_pnl FROM trade_journal ORDER BY trade_date DESC")
print("\nJournal entries:")
for r in cur.fetchall():
    print("  {} {} ({}) {} P&L={}".format(r[0], r[1], r[2], r[3], r[4]))

conn.commit()
print("\nDONE")
conn.close()
