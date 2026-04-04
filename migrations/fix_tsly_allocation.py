"""
Fix TSLY to correct 50% allocation ($50K at inception).
Rules: 50% LT ($50K TSLY) / 30% swing ($30K) / 20% cash float ($20K)
"""
import psycopg2
import json

conn = psycopg2.connect(
    host='postgres-timeseries-service', port=5432,
    dbname='trading_data', user='trading', password='trading_password'
)
conn.autocommit = False
cur = conn.cursor()

# Portfolio rules
starting_balance = 100000.0
lt_pct = 0.50  # $50K
jan30_price = 32.49
current_price = 29.01

# Correct TSLY position: $50K / $32.49 = 1538 shares
correct_shares = int((starting_balance * lt_pct) / jan30_price)
correct_cost = correct_shares * jan30_price
print("Correct TSLY: {} shares @ {:.2f} = {:.2f}".format(correct_shares, jan30_price, correct_cost))

# Current wrong state
cur.execute("SELECT quantity FROM portfolio_holdings WHERE ticker = 'TSLY'")
old_shares = float(cur.fetchone()[0])
print("Current TSLY: {} shares (wrong)".format(int(old_shares)))

# 1. Fix TSLY holding to correct shares
new_market_val = correct_shares * current_price
unrealized = new_market_val - correct_cost
unrealized_pct = unrealized / correct_cost

cur.execute("""
    UPDATE portfolio_holdings
    SET quantity = %s, avg_cost_basis = %s, current_price = %s,
        market_value = %s, unrealized_pnl = %s, unrealized_pnl_pct = %s
    WHERE ticker = 'TSLY' AND holding_type = 'long_term'
""", (correct_shares, jan30_price, current_price, new_market_val, unrealized, unrealized_pct))
print("TSLY holding: {} shares, value={:.2f}, P&L={:.2f}".format(
    correct_shares, new_market_val, unrealized))

# 2. Fix the buy transaction
cur.execute("""
    UPDATE portfolio_transactions
    SET quantity = %s, total_value = %s
    WHERE id = (
        SELECT id FROM portfolio_transactions
        WHERE ticker = 'TSLY' AND action = 'buy' AND signal_source = 'tsly_default_yield'
        ORDER BY executed_at ASC LIMIT 1
    )
""", (correct_shares, correct_cost))

# 3. Fix dividend transactions and recalculate total dividends
dividends = [
    ('2026-02-05', 0.3300),
    ('2026-02-12', 0.3310),
    ('2026-02-19', 0.3210),
    ('2026-02-26', 0.3150),
    ('2026-03-05', 0.2960),
    ('2026-03-12', 0.2850),
    ('2026-03-19', 0.2740),
    ('2026-03-26', 0.2630),
    ('2026-04-02', 0.2590),
]

# Delete old dividend transactions and re-insert with correct shares
cur.execute("DELETE FROM portfolio_transactions WHERE ticker = 'TSLY' AND action = 'dividend'")
print("Cleared old dividend records")

total_div = 0
for div_date, per_share in dividends:
    amount = correct_shares * per_share
    total_div += amount
    details = json.dumps({"per_share": per_share, "shares": correct_shares, "payment_date": div_date})
    cur.execute("""
        INSERT INTO portfolio_transactions
            (transaction_id, ticker, action, holding_type, asset_type, quantity, price, total_value,
             signal_source, signal_details, executed_at)
        VALUES (gen_random_uuid(), 'TSLY', 'dividend', 'long_term', 'stock', %s, %s, %s,
                'tsly_dividend', %s::jsonb, %s)
    """, (correct_shares, per_share, amount, details, div_date))

print("Total dividends: {:.2f} ({} shares x {:.4f}/share total)".format(
    total_div, correct_shares, sum(d[1] for d in dividends)))

# 4. Fix journal entry
cur.execute("""
    UPDATE trade_journal
    SET quantity = %s, entry_price = %s
    WHERE ticker = 'TSLY' AND holding_type = 'tsly_yield'
""", (correct_shares, jan30_price))

# 5. Recalculate cash balance from scratch
# Start: $100K
# Buy TSLY: -$50K (correct_cost)
# Swing trades: need to calculate net from transactions
cur.execute("""
    SELECT COALESCE(SUM(
        CASE WHEN action IN ('buy', 'buy_to_open') THEN -total_value
             WHEN action IN ('sell', 'sell_to_close') THEN total_value
             WHEN action = 'dividend' THEN total_value
             ELSE 0 END
    ), 0)
    FROM portfolio_transactions
    WHERE ticker != 'TSLY'
""")
swing_net = float(cur.fetchone()[0])
print("Swing trades net cash flow: {:.2f}".format(swing_net))

# Cash = starting - TSLY cost + swing net + dividends
# But swing trades already reflect in the transaction history
# Let's compute: starting_balance + all transaction cash flows
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
correct_cash = starting_balance + all_cash_flows
print("All cash flows: {:.2f}".format(all_cash_flows))
print("Correct cash: {:.2f}".format(correct_cash))

cur.execute("UPDATE portfolio_account SET cash_balance = %s, updated_at = NOW() WHERE id = 1",
            (correct_cash,))

# 6. Summary
total_portfolio = correct_cash + new_market_val
total_pnl = total_portfolio - starting_balance
print("\n--- Portfolio Summary ---")
print("Cash: {:.2f} ({:.0f}%)".format(correct_cash, correct_cash/total_portfolio*100))
print("TSLY: {:.2f} ({:.0f}%)".format(new_market_val, new_market_val/total_portfolio*100))
print("Total: {:.2f}".format(total_portfolio))
print("P&L: {:.2f} ({:+.1f}%)".format(total_pnl, total_pnl/starting_balance*100))
print("  TSLY price change: {:.2f}".format(unrealized))
print("  TSLY dividends: {:.2f}".format(total_div))
print("  Swing P&L: {:.2f}".format(swing_net))

# 7. Update performance snapshot
cur.execute("""
    UPDATE portfolio_performance
    SET total_value = %s, cash_balance = %s, holdings_value = %s,
        long_term_value = %s, swing_value = 0,
        total_pnl = %s, total_pnl_pct = %s,
        open_positions = 1, long_term_positions = 1, swing_positions = 0
    WHERE snapshot_date = '2026-04-03'
""", (total_portfolio, correct_cash, new_market_val, new_market_val,
      total_pnl, total_pnl / starting_balance))

conn.commit()
print("\nDONE")
conn.close()
