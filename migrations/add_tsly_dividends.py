"""Add TSLY dividend income to portfolio - 9 weekly payments since Jan 30."""
import psycopg2

conn = psycopg2.connect(
    host='postgres-timeseries-service', port=5432,
    dbname='trading_data', user='trading', password='trading_password'
)
conn.autocommit = False
cur = conn.cursor()

# Get TSLY share count
cur.execute("SELECT quantity FROM portfolio_holdings WHERE ticker = 'TSLY' AND holding_type = 'long_term'")
shares = float(cur.fetchone()[0])
print("TSLY shares:", int(shares))

# Dividend history from yfinance
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

total_div = 0
for div_date, per_share in dividends:
    amount = shares * per_share
    total_div += amount

    import json
    details = json.dumps({"per_share": per_share, "shares": int(shares), "payment_date": div_date})
    cur.execute("""
        INSERT INTO portfolio_transactions
            (transaction_id, ticker, action, holding_type, asset_type, quantity, price, total_value,
             signal_source, signal_details, executed_at)
        VALUES (gen_random_uuid(), 'TSLY', 'dividend', 'long_term', 'stock', %s, %s, %s,
                'tsly_dividend', %s::jsonb, %s)
    """, (shares, per_share, amount, details, div_date))
    print("  {} : {:.4f}/share x {} = {:.2f}".format(div_date, per_share, int(shares), amount))

print("Total dividend income: {:.2f}".format(total_div))

# Add to cash balance
cur.execute("UPDATE portfolio_account SET cash_balance = cash_balance + %s, updated_at = NOW() WHERE id = 1", (total_div,))
cur.execute("SELECT cash_balance FROM portfolio_account WHERE id = 1")
cash = float(cur.fetchone()[0])

cur.execute("SELECT market_value FROM portfolio_holdings WHERE ticker = 'TSLY'")
holdings = float(cur.fetchone()[0])

print("New cash: {:.2f}".format(cash))
print("Portfolio total: {:.2f}".format(cash + holdings))
print("P&L from 100K: {:.2f}".format(cash + holdings - 100000))

# Update today's performance snapshot
total = cash + holdings
cur.execute("""
    UPDATE portfolio_performance
    SET total_value = %s, cash_balance = %s, total_pnl = %s, total_pnl_pct = %s
    WHERE snapshot_date = '2026-04-03'
""", (total, cash, total - 100000, (total - 100000) / 100000))

conn.commit()
print("DONE")
conn.close()
