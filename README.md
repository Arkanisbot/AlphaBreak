# AlphaBreak

A comprehensive AI-powered trading prediction system that identifies high-probability short-term trading opportunities using technical indicators, machine learning, and options pricing analysis.

## Overview

This application analyzes securities to predict trend breaks and identify mispriced options, enabling informed swing trading decisions. The system uses a multi-stage approach:

1. **Meta-Learning Stage** - Determines which technical indicators are most reliable under current market conditions
2. **Prediction Stage** - Uses XGBoost/LightGBM to predict when trend breaks will occur
3. **Options Analysis Stage** - Identifies mispriced options aligned with predicted trends

## Architecture

```
src/
├── data_fetcher.py           # Stock data retrieval (yfinance)
├── technical_indicators.py   # 25+ indicators using pandas_ta
├── trend_analysis.py         # Trend break detection & accuracy analysis
├── meta_learning_model.py    # Indicator reliability prediction (multi-timeframe)
├── models.py                 # XGBoost, LightGBM, LSTM, Dense NN
├── options_pricing.py        # Black-Scholes & Binomial Tree pricing
├── populate_market_indices.py # Market indices & ETF data population
├── sec_13f_fetcher.py        # SEC EDGAR 13F institutional holdings tracker
└── scheduled_runner.py       # Automated daily analysis
```

## Key Features

### Technical Indicators
- RSI, MACD, ADX, Stochastic Oscillator
- Bollinger Bands, SuperTrend
- Volume indicators (OBV, VPT, CMF, MFI, VWAP)
- Moving averages and trend lines

### Machine Learning Models

| Prediction Goal | Recommended Model | Why |
|----------------|-------------------|-----|
| Price direction (up/down) | XGBoost or LightGBM | Handles tabular data, feature importance |
| Trend break probability | XGBoost or LightGBM | Classification, good with indicators |
| Future price value | LSTM/GRU | Time series regression |
| Indicator reliability | Dense NN (Keras) | Multi-output regression |

### Market Indices & ETFs
- S&P 500 (^GSPC), Dow Jones (^DJI), VIX (^VIX)
- E-mini S&P 500 Futures (ES=F)
- Inverse ETFs: SH, PSQ, DOG (sentiment indicators)
- Volatility ETF: VXX
- Calculated features: S&P trend, VIX regime, futures premium, inverse ETF flows

### 13F Institutional Holdings Analysis
- Tracks 20 major hedge funds (Berkshire, Bridgewater, Renaissance, Citadel, DE Shaw, etc.)
- Fetches quarterly 13F filings from SEC EDGAR
- Calculates quarter-over-quarter position changes
- Aggregate institutional sentiment per stock
- Signals: STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL based on fund activity
- CUSIP-to-ticker mapping via SEC company data

### Options Pricing
- **Binomial Tree** (American options) - Recommended for US stocks
- **Black-Scholes** (European options) - For indices, some ETFs
- Dynamic risk-free rate from Treasury yields
- Greeks calculation (Delta, Gamma, Theta, Vega, Rho)
- Trend-aligned option filtering for swing trading

### Forex Correlation Model
Analyzes correlations between currency pairs to identify patterns that may inform equity positioning.

**Data Sources:**
- **FRED (Federal Reserve)** - Historical exchange rates back to 1971 (54 years for major pairs)
- **Yahoo Finance** - Recent OHLCV data for supplementation

**Currency Pairs Tracked:**
| Pair | Data Start | History |
|------|------------|---------|
| USD/JPY, GBP/USD, USD/CAD, USD/CHF, AUD/USD | 1971 | ~54 years |
| USD/CNY | 1981 | ~44 years |
| EUR/USD | 1999 | ~26 years (Euro introduction) |
| USD/MXN, USD/BRL, USD/INR, USD/KRW, etc. | Various | 20-30 years |

**Correlation Analysis:**
- Computes correlations between all currency pairs (30d, 90d, 1yr, all-time)
- Classifies patterns as **Strong**, **Mid**, or **Weak** using relative thresholds
- Identifies lead/lag relationships (which pair moves first)

**Trend Break Detection:**
- Applies the same trend-break model used for equities to forex pairs
- Detects notable movements using RSI, CCI, MACD, Stochastic, and Bollinger Bands
- Tracks movement outcomes (5d, 10d, 20d returns)

**Files:**
- `src/forex_data_fetcher.py` - Fetches data from FRED and Yahoo Finance
- `src/forex_correlation_model.py` - Correlation model and trend break analysis
- `flask_app/app/routes/forex.py` - REST API endpoints
- `kubernetes/schema_forex.sql` - Database schema

## Installation

```bash
pip install -r requirements.txt
```

Required packages:
- pandas, numpy, scipy
- pandas_ta (technical indicators)
- yfinance (market data)
- xgboost, lightgbm (gradient boosting)
- tensorflow/keras (neural networks)
- scikit-learn (utilities)

## Quick Start

```python
from src import (
    get_stock_data,
    calculate_rsi, calculate_macd,
    trend_break, feature_engineering,
    train_xgboost_model,
    analyze_option_pricing
)

# 1. Fetch data and calculate indicators
data = get_stock_data('AAPL', '2023-01-01', '2024-01-01')

# 2. Detect trend breaks
breaks = trend_break(data, 'Close', 'direction')

# 3. Train prediction model
model, metrics = train_xgboost_model(X_train, y_train, X_test, y_test)

# 4. Analyze options (American pricing by default)
results = analyze_option_pricing(
    'AAPL', '2023-01-01', '2024-01-15',
    pricing_model='american',
    trend_direction='bullish'
)
underpriced = results[results['recommendation'] == 'UNDERPRICED']
```

## Project Structure

```
Securities_prediction_model/
├── src/                    # Production modules
├── docs/
│   └── code_snippets/     # Reference implementations & development history
├── flask_app/             # Web API (in development)
├── frontend/              # UI (in development)
├── kubernetes/            # Deployment configs (PostgreSQL/TimescaleDB)
└── requirements.txt
```

### Database Schema (PostgreSQL/TimescaleDB)

| Table | Description |
|-------|-------------|
| `stock_data` | Daily/intraday OHLCV for individual stocks |
| `market_indices` | Daily data for S&P 500, DJI, VIX, futures, inverse ETFs |
| `market_indices_intraday` | 5min/1hr data for market ETFs |
| `hedge_fund_managers` | 20 tracked institutional investors |
| `f13_filings` | Quarterly 13F filing metadata |
| `f13_holdings` | Individual holdings per filing with Q/Q changes |
| `f13_stock_aggregates` | Per-stock aggregate institutional sentiment |
| `cusip_ticker_map` | CUSIP to ticker symbol mappings |
| `forex_daily_data` | Historical forex OHLCV from FRED + Yahoo Finance |
| `forex_pairs` | Currency pair metadata and model status |
| `forex_correlations` | Pair-to-pair correlation matrix with pattern strength |
| `forex_trend_breaks` | Notable forex movements with technical indicators |

## Usage Notes

### American vs European Options
Most US stock options are **American** (exercise anytime). Use `binomial_tree_american()` for accurate pricing. Black-Scholes underprices American options, especially:
- Puts when stock price drops significantly
- Calls on dividend-paying stocks

### Model Selection
- **XGBoost/LightGBM**: Best for indicator-based tabular data
- **LSTM**: Best for pure time-series with temporal dependencies
- **Dense NN**: Good for meta-learning (predicting indicator accuracy)

### Dynamic Risk-Free Rate
The system automatically fetches current Treasury yields:
- <3 months to expiry: 13-week T-bill (^IRX)
- 3-6 months: 5-year Treasury (^FVX)
- >6 months: 10-year Treasury (^TNX)

## Roadmap

- [x] Database integration for historical data storage (PostgreSQL/TimescaleDB)
- [x] Multi-timeframe models (5min, 1hr, daily)
- [x] 13F report analysis (SEC hedge fund holdings)
- [x] Market indices & ETF tracking
- [ ] Airflow service for scheduled analysis
- [ ] Push notifications for high-probability trades
- [ ] Visualizations dashboard

## Future Work

- **User Authentication** — Login system with per-user settings, saved watchlists, and personalized dashboards
- ~~**Forex Correlation Model**~~ ✅ Implemented - Currency pair correlation analysis with 54 years of historical data
- **Trading Platform Integration** — Direct connectivity to Schwab and/or Robinhood APIs for order execution and portfolio sync
- **Pullback/Continuation Model** — Predict candlestick count after a trend break, model whether price action represents a pullback (continuation) or full reversal

### Theoretical Portfolio Tracker

A paper trading portfolio to validate the prediction model's effectiveness before committing real capital.

**Concept:**
- Start with **$100,000 USD** in a simulated money market account
- Execute trades based on model signals (trend breaks, options analysis, 13F sentiment)
- Track theoretical P&L over time to measure model accuracy

**Portfolio Document Structure:**
```
docs/theoretical_portfolio/
├── portfolio.json          # Current holdings, cash balance, transaction history
├── performance.json        # Daily/weekly/monthly returns, Sharpe ratio, max drawdown
├── trades.csv              # All executed trades with entry/exit prices, rationale
└── README.md               # Portfolio rules, position sizing, risk management
```

**Automation Options:**

| Method | Description | Complexity |
|--------|-------------|------------|
| **Cron + Python Script** | Daily script checks signals, updates `portfolio.json`, calculates P&L | Low |
| **Flask API Endpoint** | `/api/portfolio/execute` processes pending signals and updates holdings | Medium |
| **Airflow DAG** | Scheduled workflow: fetch signals → validate → execute → report | Medium |
| **GitHub Actions** | Scheduled workflow runs daily, commits portfolio updates to repo | Low |
| **Database + Triggers** | Store portfolio in PostgreSQL, use triggers/functions for automatic updates | Medium |
| **Webhook Integration** | Trend break detection triggers webhook → portfolio service executes trade | High |

**Suggested Implementation (Phase 1):**

1. Create `src/portfolio_manager.py` with functions:
   - `get_portfolio()` — Load current holdings from JSON/DB
   - `execute_signal(ticker, action, quantity, price)` — Record theoretical trade
   - `calculate_pnl()` — Compute unrealized/realized P&L
   - `generate_report()` — Daily performance summary

2. Add scheduled job (cron or Airflow):
   - Run after market close (4:30 PM ET)
   - Fetch today's trend break signals
   - Apply position sizing rules (e.g., max 5% per position)
   - Execute theoretical trades
   - Update portfolio JSON
   - Optionally commit to Git or send email report

3. Dashboard integration:
   - New "Portfolio" tab showing holdings, P&L, trade history
   - Charts: equity curve, sector allocation, win/loss ratio

**Position Sizing Rules:**
- Max 5% of portfolio per individual stock position
- Max 2% per options contract (due to higher risk)
- Maintain 20% cash reserve minimum
- Stop-loss at 7% below entry for stocks, 50% for options

## License

MIT
