"""Get TSLY price history and dividends since portfolio inception."""
import yfinance as yf
from datetime import date

tsly = yf.Ticker('TSLY')
hist = tsly.history(start='2026-01-30', end='2026-04-04')
print("Date range:", hist.index[0].date(), "to", hist.index[-1].date())
print("Start price (Jan 30): {:.2f}".format(hist.iloc[0]['Close']))
print("Current price: {:.2f}".format(hist.iloc[-1]['Close']))

# Feb 9 price
feb9 = hist.loc[hist.index.date >= date(2026, 2, 9)].iloc[0]
print("Feb 9 price: {:.2f}".format(feb9['Close']))

# Price change
start_p = float(hist.iloc[0]['Close'])
end_p = float(hist.iloc[-1]['Close'])
pct = (end_p - start_p) / start_p * 100
print("Price change: {:.2f} -> {:.2f} ({:+.1f}%)".format(start_p, end_p, pct))

# Dividends
divs = tsly.dividends
if len(divs) > 0:
    recent = divs[divs.index >= '2026-01-30']
    print("Dividends since Jan 30: {} payments".format(len(recent)))
    total_div = 0
    for dt, amount in recent.items():
        print("  {}: {:.4f}".format(dt.date(), amount))
        total_div += amount
    print("Total dividends per share: {:.4f}".format(total_div))

# How many shares with 50K at Jan 30 price
shares = int(50000 / start_p)
total_cost = shares * start_p
print("\nWith 50K at Jan 30 price:")
print("  Shares: {}".format(shares))
print("  Cost basis: {:.2f}".format(total_cost))
print("  Current value: {:.2f}".format(shares * end_p))
print("  Price gain: {:.2f}".format(shares * (end_p - start_p)))
print("  Dividend income: {:.2f}".format(shares * total_div))
print("  Total return: {:.2f}".format(shares * (end_p - start_p) + shares * total_div))
