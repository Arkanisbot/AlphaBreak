"""
Backdate TSLY buy to Jan 30 and import swing trades into journal.
"""
import psycopg2
import json

conn = psycopg2.connect(
    host='postgres-timeseries-service', port=5432,
    dbname='trading_data', user='trading', password='trading_password'
)
conn.autocommit = False
cur = conn.cursor()

# ── 1. Backdate TSLY holding to Jan 30 at $32.49 ──
jan30_price = 32.49
cur.execute("""
    UPDATE portfolio_holdings
    SET avg_cost_basis = %s,
        entry_date = '2026-01-30 14:00:00+00',
        entry_rationale = 'TSLY yield position from portfolio inception (proof of concept)'
    WHERE ticker = 'TSLY' AND holding_type = 'long_term'
""", (jan30_price,))
print("Updated TSLY cost basis to", jan30_price)

# Update the TSLY buy transaction to Jan 30
cur.execute("""
    UPDATE portfolio_transactions
    SET price = %s, executed_at = '2026-01-30 14:00:00+00',
        total_value = quantity * %s
    WHERE id = (
        SELECT id FROM portfolio_transactions
        WHERE ticker = 'TSLY' AND action = 'buy' AND signal_source = 'tsly_default_yield'
        ORDER BY executed_at DESC LIMIT 1
    )
""", (jan30_price, jan30_price))

# Get the TSLY quantity for value calculations
cur.execute("SELECT quantity FROM portfolio_holdings WHERE ticker = 'TSLY'")
tsly_shares = float(cur.fetchone()[0])
print("TSLY shares:", int(tsly_shares))

# Update TSLY current price to latest (~29.01) and recalc market value
current_price = 29.01
market_val = tsly_shares * current_price
cost_val = tsly_shares * jan30_price
unrealized = market_val - cost_val
unrealized_pct = unrealized / cost_val if cost_val > 0 else 0

cur.execute("""
    UPDATE portfolio_holdings
    SET current_price = %s, market_value = %s,
        unrealized_pnl = %s, unrealized_pnl_pct = %s
    WHERE ticker = 'TSLY' AND holding_type = 'long_term'
""", (current_price, market_val, unrealized, unrealized_pct))
print("TSLY value: cost={:.2f} current={:.2f} P&L={:.2f}".format(cost_val, market_val, unrealized))

# Fix cash balance: we originally deducted at $17.50, need to deduct at $32.49 instead
# Difference = shares * (32.49 - 17.50)
price_diff = jan30_price - 17.50
cash_adjustment = tsly_shares * price_diff
cur.execute("UPDATE portfolio_account SET cash_balance = cash_balance - %s WHERE id = 1", (cash_adjustment,))
cur.execute("SELECT cash_balance FROM portfolio_account WHERE id = 1")
cash = float(cur.fetchone()[0])
print("Adjusted cash: {:.2f} (deducted {:.2f} more for price diff)".format(cash, cash_adjustment))

# Update TSLY journal entry
cur.execute("""
    UPDATE trade_journal
    SET entry_price = %s, trade_date = '2026-01-30',
        entry_notes = 'TSLY yield position from portfolio inception - proof of concept LT allocation'
    WHERE ticker = 'TSLY' AND holding_type = 'tsly_yield'
""", (jan30_price,))
print("Updated TSLY journal entry to Jan 30")

# ── 2. Import swing trades into journal ──
# Get all swing sell/close transactions
cur.execute("""
    SELECT t.transaction_id, t.ticker, t.action, t.holding_type, t.asset_type,
           t.quantity, t.price, t.total_value, t.realized_pnl, t.realized_pnl_pct,
           t.signal_source, t.signal_details, t.executed_at, t.option_type
    FROM portfolio_transactions t
    WHERE t.action IN ('sell', 'sell_to_close')
      AND t.realized_pnl IS NOT NULL
      AND t.holding_type = 'swing'
      AND t.transaction_id NOT IN (
          SELECT transaction_id FROM trade_journal WHERE transaction_id IS NOT NULL
      )
    ORDER BY t.executed_at DESC
""")
sells = cur.fetchall()
print("Found {} swing sells to import".format(len(sells)))

# Get buy transactions for entry price lookup
cur.execute("""
    SELECT ticker, action, asset_type, price, signal_source, signal_details, executed_at
    FROM portfolio_transactions
    WHERE action IN ('buy', 'buy_to_open')
    ORDER BY executed_at DESC
""")
buys = cur.fetchall()

# Build lookup
buy_lookup = {}
for b in buys:
    ticker = b[0]
    if ticker not in buy_lookup:
        buy_lookup[ticker] = []
    buy_lookup[ticker].append({
        'price': float(b[3]) if b[3] else None,
        'signal_source': b[4],
        'executed_at': b[6],
    })

imported = 0
for r in sells:
    ticker = r[1]
    exit_price = float(r[6]) if r[6] else None
    sell_date = r[12]
    direction = 'long' if r[2] == 'sell' else 'long'

    # Find matching buy
    entry_price = None
    buy_signal = None
    for buy in buy_lookup.get(ticker, []):
        if buy['executed_at'] and sell_date and buy['executed_at'] < sell_date:
            entry_price = buy['price']
            buy_signal = buy['signal_source']
            break

    if entry_price is None and exit_price and r[9]:
        pnl_pct = float(r[9])
        if pnl_pct != 0 and abs(1 + pnl_pct) > 0.01:
            entry_price = exit_price / (1 + pnl_pct)

    note = "Entry: {} @ ${:.2f}".format(buy_signal or 'manual', entry_price) if entry_price else "Auto-imported {} {}".format(r[2], ticker)

    cur.execute("""
        INSERT INTO trade_journal
            (user_id, transaction_id, ticker, trade_date, direction, entry_price, exit_price,
             quantity, realized_pnl, realized_pnl_pct, holding_type, signal_source, entry_notes)
        VALUES (2, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'swing', %s, %s)
    """, (
        str(r[0]), ticker, sell_date.date() if sell_date else '2026-04-03',
        direction, entry_price, exit_price,
        float(r[5]) if r[5] else None,
        float(r[8]) if r[8] else None,
        float(r[9]) if r[9] else None,
        r[10], note
    ))
    imported += 1

print("Imported {} swing trades into journal".format(imported))

# Also import LT sells (non-TSLY) as long_term type
cur.execute("""
    SELECT t.transaction_id, t.ticker, t.action, t.holding_type, t.asset_type,
           t.quantity, t.price, t.total_value, t.realized_pnl, t.realized_pnl_pct,
           t.signal_source, t.signal_details, t.executed_at
    FROM portfolio_transactions t
    WHERE t.action = 'sell'
      AND t.realized_pnl IS NOT NULL
      AND t.holding_type = 'long_term'
      AND t.ticker != 'TSLY'
      AND t.transaction_id NOT IN (
          SELECT transaction_id FROM trade_journal WHERE transaction_id IS NOT NULL
      )
    ORDER BY t.executed_at DESC
""")
lt_sells = cur.fetchall()

for r in lt_sells:
    ticker = r[1]
    exit_price = float(r[6]) if r[6] else None
    sell_date = r[12]

    entry_price = None
    buy_signal = None
    for buy in buy_lookup.get(ticker, []):
        if buy['executed_at'] and sell_date and buy['executed_at'] < sell_date:
            entry_price = buy['price']
            buy_signal = buy['signal_source']
            break

    if entry_price is None and exit_price and r[9]:
        pnl_pct = float(r[9])
        if pnl_pct != 0 and abs(1 + pnl_pct) > 0.01:
            entry_price = exit_price / (1 + pnl_pct)

    note = "LT exit: {} @ ${:.2f}".format(r[10] or 'manual', exit_price) if exit_price else "Auto-imported"

    cur.execute("""
        INSERT INTO trade_journal
            (user_id, transaction_id, ticker, trade_date, direction, entry_price, exit_price,
             quantity, realized_pnl, realized_pnl_pct, holding_type, signal_source, entry_notes)
        VALUES (2, %s, %s, %s, 'long', %s, %s, %s, %s, %s, 'long_term', %s, %s)
    """, (
        str(r[0]), ticker, sell_date.date() if sell_date else '2026-04-03',
        entry_price, exit_price,
        float(r[5]) if r[5] else None,
        float(r[8]) if r[8] else None,
        float(r[9]) if r[9] else None,
        r[10], note
    ))
    imported += 1

print("Total journal entries imported: {}".format(imported))

# Show final state
cur.execute("SELECT COUNT(*), SUM(realized_pnl) FROM trade_journal WHERE holding_type = 'swing'")
row = cur.fetchone()
print("Swing trades: {} entries, total P&L: {:.2f}".format(row[0], float(row[1] or 0)))

cur.execute("SELECT COUNT(*), SUM(realized_pnl) FROM trade_journal WHERE holding_type = 'long_term'")
row = cur.fetchone()
print("LT trades: {} entries, total P&L: {:.2f}".format(row[0], float(row[1] or 0)))

cur.execute("SELECT COUNT(*) FROM trade_journal WHERE holding_type = 'tsly_yield'")
print("TSLY entries:", cur.fetchone()[0])

conn.commit()
print("DONE")
conn.close()
