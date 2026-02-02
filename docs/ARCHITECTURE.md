# System Architecture

**Version**: 2.0
**Last Updated**: February 2, 2026
**Status**: Production

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [High-Level Architecture](#high-level-architecture)
4. [Component Architecture](#component-architecture)
5. [Data Architecture](#data-architecture)
6. [Technology Stack](#technology-stack)
7. [Deployment Architecture](#deployment-architecture)
8. [Security Architecture](#security-architecture)
9. [Scalability & Performance](#scalability--performance)
10. [Related Documentation](#related-documentation)

---

## System Overview

The Securities Prediction Model is a comprehensive AI-powered trading analysis platform that identifies high-probability short-term trading opportunities using technical indicators, machine learning, and options pricing analysis.

### Primary Goals

1. **Trend Break Detection**: Identify when securities are likely to break out of current trends
2. **Options Analysis**: Calculate fair value for options and identify mispriced opportunities
3. **Portfolio Automation**: Execute automated trading strategies based on quantitative signals
4. **Forex Analysis**: Track currency correlations to inform equity positioning
5. **Market Sentiment**: Aggregate technical indicators for real-time market overview

### User Types

- **Retail Traders**: Web dashboard for market analysis and trade ideas
- **Portfolio Managers**: Automated portfolio management with Airflow scheduling
- **Data Scientists**: ML feature engineering and model development
- **DevOps**: System administration and deployment

---

## Architecture Principles

### Design Philosophy

1. **Modularity**: Clear separation between data fetching, analysis, API, and presentation layers
2. **Simplicity**: Vanilla JavaScript frontend, Flask API backend - no complex frameworks
3. **Data-Driven**: PostgreSQL/TimescaleDB as source of truth for all analysis
4. **Automation**: Airflow for scheduled jobs, no manual intervention required
5. **Extensibility**: Easy to add new indicators, models, or data sources

### Key Decisions

| Decision | Rationale |
|----------|-----------|
| Vanilla JS (no React/Vue) | Reduce complexity, faster load times, easier debugging |
| Flask over Django | Lightweight, flexible, better for API-first design |
| TimescaleDB over MongoDB | Time-series optimization, SQL familiarity, ACID compliance |
| LocalExecutor (not Celery) | Simpler deployment, sufficient for current workload |
| Gunicorn over uWSGI | Better Python 3.10+ support, simpler configuration |

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER INTERACTIONS                              │
│                                                                          │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐            │
│   │   Browser    │    │  Airflow UI  │    │  DB Client   │            │
│   │ (Port 8000)  │    │ (Port 8080)  │    │ (Port 5432)  │            │
│   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘            │
└──────────┼─────────────────── ┼────────────────────┼───────────────────┘
           │                    │                    │
           │                    │                    │
┌──────────▼────────────────────▼────────────────────▼───────────────────┐
│                          EC2 INSTANCE (3.140.78.15)                     │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                    PRESENTATION LAYER                           │    │
│  │                                                                 │    │
│  │  ┌──────────────┐         ┌───────────────────────┐           │    │
│  │  │    Nginx     │         │  Frontend (Static)    │           │    │
│  │  │  Port 8000   │────────▶│  - index.html         │           │    │
│  │  │              │         │  - app.js, forex.js   │           │    │
│  │  └──────────────┘         │  - Chart.js           │           │    │
│  │                           └───────────────────────┘           │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                     │                                   │
│                                     │ HTTP API Calls                    │
│                                     ▼                                   │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                      APPLICATION LAYER                          │    │
│  │                                                                 │    │
│  │  ┌──────────────────────────────────────────────────────────┐  │    │
│  │  │         Flask API (Gunicorn - 3 workers)                │  │    │
│  │  │                     Port 5000                            │  │    │
│  │  │                                                          │  │    │
│  │  │  Routes:                                                 │  │    │
│  │  │  • /api/predict/*     - Trend breaks & options          │  │    │
│  │  │  • /api/sentiment     - Market sentiment                │  │    │
│  │  │  • /api/forex/*       - Currency analysis               │  │    │
│  │  │  • /api/portfolio/*   - Portfolio management            │  │    │
│  │  │  • /api/watchlist/*   - User watchlists                 │  │    │
│  │  │  • /api/auth/*        - JWT authentication              │  │    │
│  │  └──────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────┬────────────────────────────────────   │
│                                │                                        │
│                                │                                        │
│  ┌─────────────────────────────▼──────────────────────────────────┐    │
│  │                      BUSINESS LOGIC LAYER                       │    │
│  │                                                                 │    │
│  │  ┌───────────────────┐  ┌────────────────────┐                │    │
│  │  │  Core Modules     │  │  Airflow Scheduler │                │    │
│  │  │  (src/)           │  │  LocalExecutor     │                │    │
│  │  │                   │  │                    │                │    │
│  │  │  • data_fetcher   │  │  DAGs:             │                │    │
│  │  │  • technical_     │  │  • portfolio_      │                │    │
│  │  │    indicators     │  │    update          │                │    │
│  │  │  • options_       │  │    (9 AM EST)      │                │    │
│  │  │    pricing        │  │                    │                │    │
│  │  │  • portfolio_     │  └────────────────────┘                │    │
│  │  │    manager        │                                         │    │
│  │  │  • forex_         │                                         │    │
│  │  │    correlation    │                                         │    │
│  │  │  • sec_13f_       │                                         │    │
│  │  │    fetcher        │                                         │    │
│  │  └───────────────────┘                                         │    │
│  └─────────────────────────────┬────────────────────────────────────   │
│                                │                                        │
│                                │                                        │
│  ┌─────────────────────────────▼──────────────────────────────────┐    │
│  │                        DATA LAYER                               │    │
│  │                                                                 │    │
│  │  ┌────────────────────────────────────────────────────────┐    │    │
│  │  │   PostgreSQL 15 + TimescaleDB (Port 5432)             │    │    │
│  │  │                                                        │    │    │
│  │  │   Hypertables:                                         │    │    │
│  │  │   • stock_prices_intraday (1-day chunks)              │    │    │
│  │  │   • stock_prices_daily (1-year chunks)                │    │    │
│  │  │   • market_breadth_intraday                           │    │    │
│  │  │                                                        │    │    │
│  │  │   Standard Tables:                                     │    │    │
│  │  │   • portfolio_* (signals, holdings, trades, etc.)     │    │    │
│  │  │   • forex_* (pairs, correlations, trend_breaks)       │    │    │
│  │  │   • f13_* (institutional holdings)                    │    │    │
│  │  │   • users, user_watchlists, refresh_tokens            │    │    │
│  │  │   • ticker_metadata, corporate_actions                │    │    │
│  │  └────────────────────────────────────────────────────────┘    │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                                 │ API Calls
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL DATA SOURCES                             │
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │   Yahoo     │  │    FRED     │  │ SEC EDGAR   │  │  Polygon.io  │  │
│  │  Finance    │  │   (Forex)   │  │  (13F)      │  │   (Future)   │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. Frontend (Presentation Layer)

**Location**: `frontend/`
**Technology**: Vanilla JavaScript, Chart.js, HTML5/CSS3
**Port**: 8000 (Nginx)

#### Components

| File | Purpose | Key Features |
|------|---------|--------------|
| `index.html` | Main HTML structure | Single-page app, 4 tabs, modals |
| `app.js` | Core application logic | API client, tab management, auth state |
| `dashboard.js` | Market sentiment dashboard | Real-time indicators (CCI, RSI, ADX, etc.) |
| `reports.js` | Trend break reports | Probability scores, signal filtering |
| `watchlist.js` | User watchlist management | Server sync, ticker validation |
| `forex.js` | Forex correlation analysis | Dual Y-axis charts, DXY backdrop |
| `earnings.js` | Earnings calendar | Upcoming events, historical surprises |
| `auth.js` | Authentication state | JWT token management, login/logout |
| `styles.css` | Dark theme styling | Responsive design, modern UI |

#### Data Flow

```
User Action → API Request → Backend → Database → Response → Chart.js Rendering
```

#### Key Design Decisions

- **No Build Step**: Direct script loading for faster development
- **localStorage**: Client-side caching for watchlist (syncs to server on login)
- **Modular JavaScript**: Each tab has its own JS file
- **Chart.js**: Lightweight charting library with good mobile support

---

### 2. Backend API (Application Layer)

**Location**: `flask_app/`
**Technology**: Flask 3.x, Gunicorn (3 workers)
**Port**: 5000

#### Route Structure

```
flask_app/app/routes/
├── frontend_compat.py   # Legacy endpoints for ML predictions
├── dashboard.py         # Market sentiment, commodities, crypto
├── reports.py           # Trend break analysis
├── watchlist.py         # Watchlist CRUD
├── earnings.py          # Earnings calendar
├── forex.py             # Forex data & correlations
├── portfolio.py         # Portfolio management
├── options.py           # Options fair value analysis
├── auth.py              # JWT authentication
└── user.py              # User-specific data
```

#### Service Architecture

```python
# Layered architecture example
@app.route('/api/forex/correlations')
@require_auth  # Authentication middleware
def get_forex_correlations():
    # 1. Parse request
    params = request.args

    # 2. Call service layer
    from app.services.forex_service import ForexService
    correlations = ForexService.get_correlations(params)

    # 3. Return JSON response
    return jsonify(correlations)
```

#### Key Features

- **JWT Authentication**: Access tokens (15 min) + refresh tokens (7 days)
- **Error Handling**: Centralized error handlers for 400/401/404/500
- **CORS**: Configured for local development and production
- **Logging**: Python logging to files + journalctl
- **Connection Pooling**: SQLAlchemy connection pool (pool_size=10)

---

### 3. Core Analysis Modules (Business Logic Layer)

**Location**: `src/`
**Technology**: Python 3.10, pandas, numpy, scikit-learn

#### Module Breakdown

| Module | Purpose | Key Functions |
|--------|---------|--------------|
| `data_fetcher.py` | Fetch market data | `fetch_stock_data()`, `fetch_historical()` |
| `technical_indicators.py` | Calculate 47 indicators | `calculate_all_features()`, `calculate_rsi()` |
| `trend_analysis.py` | Detect trend breaks | `detect_trend_break()`, `calculate_probability()` |
| `meta_learning_model.py` | Indicator reliability | `predict_indicator_reliability()` |
| `options_pricing.py` | Options fair value | `black_scholes()`, `binomial_tree()` |
| `forex_data_fetcher.py` | Forex data retrieval | `fetch_forex_data()`, `fetch_dxy()` |
| `forex_correlation_model.py` | Currency correlations | `calculate_correlations()` |
| `sec_13f_fetcher.py` | Institutional holdings | `fetch_13f_filings()`, `calculate_sentiment()` |
| `portfolio_manager.py` | Portfolio automation | `process_signals()`, `execute_trades()` |

#### Feature Engineering Pipeline

```python
# Example: 47 standard features + 12 forex-specific features
def calculate_all_features(ticker, df):
    """
    Calculate all technical indicators for ML model

    Args:
        ticker: Stock symbol
        df: OHLCV dataframe

    Returns:
        dict: 59 features
    """
    features = {}

    # Price-based features (8)
    features['price_change_pct'] = (df['close'] - df['open']) / df['open']
    features['daily_range'] = (df['high'] - df['low']) / df['open']
    # ...

    # Volume features (6)
    features['volume_change'] = df['volume'].pct_change()
    features['obv'] = calculate_obv(df)
    # ...

    # Momentum indicators (12)
    features['rsi'] = calculate_rsi(df['close'], 14)
    features['macd'], features['macd_signal'] = calculate_macd(df)
    # ...

    # Volatility indicators (8)
    features['atr'] = calculate_atr(df, 14)
    features['bbands_width'] = calculate_bbands(df)
    # ...

    # Market context (13)
    features['spy_correlation'] = calculate_correlation(ticker, 'SPY')
    features['vix_level'] = fetch_vix()
    # ...

    # Forex features (12) - if relevant
    if is_forex_sensitive(ticker):
        features.update(calculate_forex_features(ticker))

    return features
```

---

### 4. Scheduler (Automation Layer)

**Location**: `/home/ubuntu/airflow/`
**Technology**: Apache Airflow 2.8.1
**Port**: 8080 (Web UI)

#### Airflow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Airflow Components                           │
│                                                                  │
│  ┌──────────────────┐         ┌──────────────────┐             │
│  │   Webserver      │         │    Scheduler     │             │
│  │   (4 workers)    │         │  (Scans DAGs     │             │
│  │   Port 8080      │         │   every 30s)     │             │
│  │                  │         │                  │             │
│  │  Gunicorn        │         │  LocalExecutor   │             │
│  │  Basic Auth      │         │                  │             │
│  └──────────────────┘         └──────────────────┘             │
│           │                            │                        │
│           └────────────────┬───────────┘                        │
│                            │                                    │
│                            ▼                                    │
│                   ┌─────────────────┐                          │
│                   │   PostgreSQL    │                          │
│                   │   (Metadata)    │                          │
│                   │   trading_data  │                          │
│                   └─────────────────┘                          │
│                                                                 │
│  DAGs folder: /home/ubuntu/dags/                               │
│  Logs folder: /home/ubuntu/airflow/logs/                       │
└─────────────────────────────────────────────────────────────────┘
```

#### Portfolio Update DAG

**Schedule**: `0 14 * * 1-5` (9 AM EST, Mon-Fri)
**Execution**: ~2-5 minutes per run

```python
# Simplified DAG structure
portfolio_update_dag = DAG(
    'portfolio_update',
    schedule_interval='0 14 * * 1-5',
    catchup=False
)

# Task dependencies
fetch_signals >> fetch_prices >> create_signals >> process_signals >> [
    manage_long_term,
    stop_losses
] >> daily_snapshot
```

**Tasks**:

1. **fetch_signals**: Query `trend_breaks` table for 80%+ probability signals
2. **fetch_prices**: Get current prices via yfinance
3. **create_signals**: Insert into `portfolio_signals` with institutional sentiment
4. **process_signals**: Execute buy orders (25% swing / 75% long-term allocation)
5. **manage_long_term**: Check for exit conditions, covered calls, sector rotation
6. **stop_losses**: Monitor and execute stop-loss orders
7. **daily_snapshot**: Create end-of-day portfolio snapshot

---

## Data Architecture

**See [DATA_ARCHITECTURE.md](DATA_ARCHITECTURE.md) for complete database schema.**

### Database Choice: TimescaleDB

**Why TimescaleDB over alternatives?**

| Feature | TimescaleDB | MongoDB | InfluxDB |
|---------|-------------|---------|----------|
| SQL Support | ✅ Full PostgreSQL | ❌ NoSQL only | ⚠️ Limited (Flux) |
| Time-series optimization | ✅ Hypertables | ⚠️ TTL indexes | ✅ Native |
| ACID compliance | ✅ Full | ⚠️ Eventual | ❌ Limited |
| Continuous aggregates | ✅ Yes | ❌ Manual | ✅ Yes |
| ML integration | ✅ pgvector, MADlib | ⚠️ External | ⚠️ External |
| Hosting cost | ⚠️ Medium | ✅ Low (Atlas) | ⚠️ Medium |

**Decision**: TimescaleDB wins for SQL familiarity, ACID guarantees, and ML integration.

### Schema Overview

```sql
-- Core time-series tables (hypertables)
CREATE TABLE stock_prices_intraday (
    ticker VARCHAR(10),
    timestamp TIMESTAMPTZ NOT NULL,
    interval_type VARCHAR(10),  -- '1min', '5min', '10min', '1hour'
    open DECIMAL(12,4),
    high DECIMAL(12,4),
    low DECIMAL(12,4),
    close DECIMAL(12,4),
    volume BIGINT,
    vwap DECIMAL(12,4),
    trade_count INTEGER,
    PRIMARY KEY (ticker, timestamp, interval_type)
);

SELECT create_hypertable('stock_prices_intraday', 'timestamp',
    chunk_time_interval => INTERVAL '1 day');

-- Continuous aggregates for 10-min and hourly rollups
CREATE MATERIALIZED VIEW cagg_prices_10min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('10 minutes', timestamp) AS bucket,
    ticker,
    first(open, timestamp) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, timestamp) AS close,
    sum(volume) AS volume,
    avg(vwap) AS vwap
FROM stock_prices_intraday
WHERE interval_type = '1min'
GROUP BY bucket, ticker;

-- Portfolio tables (standard PostgreSQL)
CREATE TABLE portfolio_signals (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10),
    signal_date DATE,
    signal_type VARCHAR(20),  -- 'LONG_TERM' or 'SWING'
    probability DECIMAL(5,2),
    institutional_sentiment VARCHAR(20),
    action_taken VARCHAR(20),  -- 'PENDING', 'EXECUTED', 'SKIPPED'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE portfolio_holdings (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10),
    shares DECIMAL(12,4),
    avg_cost DECIMAL(12,4),
    current_price DECIMAL(12,4),
    market_value DECIMAL(12,2),
    unrealized_pnl DECIMAL(12,2),
    position_type VARCHAR(20),  -- 'LONG_TERM' or 'SWING'
    entry_date DATE,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- Forex tables
CREATE TABLE forex_daily_data (
    id SERIAL PRIMARY KEY,
    pair VARCHAR(10),
    date DATE,
    open DECIMAL(12,6),
    high DECIMAL(12,6),
    low DECIMAL(12,6),
    close DECIMAL(12,6),
    volume BIGINT,
    data_source VARCHAR(20),
    UNIQUE(pair, date)
);

CREATE TABLE forex_correlations (
    id SERIAL PRIMARY KEY,
    pair1 VARCHAR(10),
    pair2 VARCHAR(10),
    correlation_30d DECIMAL(5,4),
    correlation_90d DECIMAL(5,4),
    correlation_180d DECIMAL(5,4),
    calculated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Storage Estimates

**S&P 500 + DJIA (~530 tickers)**:

| Data Type | Retention | Records | Compressed Size |
|-----------|-----------|---------|-----------------|
| 1-min bars | 30 days | 619M | 200 MB |
| 10-min aggregates | 5 years | 26M | 800 MB |
| Hourly aggregates | 10 years | 9.3M | 300 MB |
| Daily bars | 64 years | 8.5M | 340 MB |
| **Total** | - | **~660M** | **~1.7 GB** |

**With compression & retention policies**: ~2 GB total database size.

---

## Technology Stack

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| Vanilla JavaScript | ES6+ | No build step, fast development |
| Chart.js | 4.4.0 | Responsive charts, dual Y-axis support |
| HTML5/CSS3 | Latest | Semantic markup, flexbox/grid layout |
| localStorage | Native | Client-side caching |

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.10 | Type hints, performance improvements |
| Flask | 3.x | Lightweight REST API framework |
| Gunicorn | 21.x | Production WSGI server (3 workers) |
| SQLAlchemy | 2.x | ORM with connection pooling |
| pandas | 2.x | Time-series data manipulation |
| numpy | 1.26.x | Numerical computations |
| scikit-learn | 1.4.x | ML models (XGBoost, LightGBM) |
| yfinance | 0.2.x | Market data fetching |
| pandas_ta | 0.3.x | Technical indicators |
| PyJWT | 2.8.x | JWT authentication |
| bcrypt | 4.1.x | Password hashing |

### Database

| Technology | Version | Purpose |
|------------|---------|---------|
| PostgreSQL | 15.x | Relational database |
| TimescaleDB | 2.13.x | Time-series extension |
| psycopg2 | 2.9.x | PostgreSQL adapter |

### Scheduler

| Technology | Version | Purpose |
|------------|---------|---------|
| Apache Airflow | 2.8.1 | Workflow orchestration |
| LocalExecutor | Built-in | Task execution (no Celery needed) |

### Infrastructure

| Technology | Version | Purpose |
|------------|---------|---------|
| AWS EC2 | t3.medium | Ubuntu 22.04, 2 vCPU, 4 GB RAM |
| Nginx | 1.18.x | Reverse proxy, static file serving |
| systemd | Built-in | Service management (Airflow) |

---

## Deployment Architecture

### EC2 Instance Configuration

**Instance ID**: i-0abc123... (us-east-2)
**Public IP**: 3.140.78.15
**Instance Type**: t3.medium (2 vCPU, 4 GB RAM)
**OS**: Ubuntu 22.04 LTS
**Storage**: 30 GB gp3 SSD

### Port Allocation

| Port | Service | Protocol | Access |
|------|---------|----------|--------|
| 22 | SSH | TCP | Public (key-based) |
| 5000 | Flask API | HTTP | Localhost only |
| 5432 | PostgreSQL | TCP | Localhost only |
| 8000 | Frontend (Nginx) | HTTP | Public |
| 8080 | Airflow UI | HTTP | Public (basic auth) |

### Service Management

```bash
# Flask API (manual process)
/home/ubuntu/flask_app/start_flask.sh

# Airflow services (systemd)
sudo systemctl status airflow-scheduler
sudo systemctl status airflow-webserver

# PostgreSQL (systemd)
sudo systemctl status postgresql

# Nginx (systemd)
sudo systemctl status nginx
```

### Systemd Service Files

**Airflow Scheduler**: `/etc/systemd/system/airflow-scheduler.service`
```ini
[Unit]
Description=Airflow Scheduler
After=network.target postgresql.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
Environment="PATH=/home/ubuntu/airflow/airflow_venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="AIRFLOW_HOME=/home/ubuntu/airflow"
ExecStart=/home/ubuntu/airflow/airflow_venv/bin/airflow scheduler
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Airflow Webserver**: `/etc/systemd/system/airflow-webserver.service`
```ini
[Unit]
Description=Airflow Webserver
After=network.target postgresql.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
Environment="PATH=/home/ubuntu/airflow/airflow_venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="AIRFLOW_HOME=/home/ubuntu/airflow"
ExecStart=/home/ubuntu/airflow/airflow_venv/bin/airflow webserver --port 8080 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Deployment Process

**See [DEPLOYMENT.md](DEPLOYMENT.md) for step-by-step deployment guide.**

```bash
# 1. Connect to EC2
ssh -i "docs/security/trading-db-key.pem" ubuntu@3.140.78.15

# 2. Update code
cd /home/ubuntu/flask_app
git pull origin main

# 3. Install dependencies (if requirements.txt changed)
source venv/bin/activate
pip install -r requirements.txt

# 4. Restart services
pkill gunicorn
./start_flask.sh

# 5. Restart Airflow (if DAGs or config changed)
sudo systemctl restart airflow-scheduler
```

---

## Security Architecture

### Authentication & Authorization

#### JWT Token Flow

```
┌────────────┐                                    ┌────────────┐
│   Client   │                                    │   Server   │
└─────┬──────┘                                    └──────┬─────┘
      │                                                  │
      │ POST /api/auth/login                             │
      │ { username, password }                           │
      ├─────────────────────────────────────────────────▶│
      │                                                  │
      │                              1. Validate creds  │
      │                              2. Hash + compare  │
      │                              3. Generate tokens │
      │                                                  │
      │ { access_token (15min), refresh_token (7d) }    │
      │◀─────────────────────────────────────────────────┤
      │                                                  │
      │ Store tokens in localStorage                     │
      │                                                  │
      │ GET /api/user/watchlist                          │
      │ Authorization: Bearer <access_token>             │
      ├─────────────────────────────────────────────────▶│
      │                                                  │
      │                              1. Validate token   │
      │                              2. Check expiry     │
      │                              3. Get user_id      │
      │                                                  │
      │ { watchlist: [...] }                             │
      │◀─────────────────────────────────────────────────┤
      │                                                  │
      │ (15 min later - access token expired)            │
      │ POST /api/auth/refresh                           │
      │ { refresh_token }                                │
      ├─────────────────────────────────────────────────▶│
      │                                                  │
      │                              1. Validate refresh │
      │                              2. Check not revoked│
      │                              3. Generate new     │
      │                                 access token     │
      │                                                  │
      │ { access_token (15min) }                         │
      │◀─────────────────────────────────────────────────┤
      │                                                  │
```

#### Password Security

- **Hashing**: bcrypt with 12 rounds (2^12 = 4096 iterations)
- **Salt**: Automatically generated per-password by bcrypt
- **Storage**: Only hashed passwords in database, no plaintext

```python
# Password hashing example
from werkzeug.security import generate_password_hash, check_password_hash

# On registration
hashed = generate_password_hash(password, method='bcrypt')  # 12 rounds default

# On login
if check_password_hash(stored_hash, submitted_password):
    # Valid password
```

### API Security

#### Rate Limiting

**Current**: None implemented
**Planned**: Flask-Limiter with Redis backend

```python
# Example (not yet implemented)
from flask_limiter import Limiter

limiter = Limiter(
    app,
    key_func=lambda: request.headers.get('Authorization'),
    default_limits=["100 per hour", "10 per minute"]
)

@app.route('/api/predict/trend-break')
@limiter.limit("10 per minute")
def predict_trend_break():
    # ...
```

#### CORS Configuration

```python
# flask_app/app/__init__.py
from flask_cors import CORS

CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:8000", "http://3.140.78.15:8000"],
        "methods": ["GET", "POST", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type"],
        "supports_credentials": True
    }
})
```

### Database Security

- **Connection**: Localhost only (not exposed to public internet)
- **Authentication**: Password-based (stored in .env file)
- **Encryption**: None currently (data not PII-sensitive)
- **Backups**: Manual via `pg_dump` (automated backups planned)

```bash
# Manual backup
pg_dump -U trading -d trading_data -F c -f backup_$(date +%Y%m%d).dump
```

### SSH Security

- **Authentication**: Key-based only (password auth disabled)
- **Key Location**: `docs/security/trading-db-key.pem` (600 permissions)
- **Firewall**: AWS Security Group restricts SSH to specific IPs

### Known Security Gaps

| Gap | Risk | Mitigation Plan |
|-----|------|-----------------|
| No HTTPS | ⚠️ Medium | Let's Encrypt SSL cert (planned) |
| No API rate limiting | ⚠️ Medium | Flask-Limiter + Redis (Q2 2026) |
| No database encryption | ⚠️ Low | Not PII-sensitive data |
| Hardcoded secrets in .env | ⚠️ Medium | AWS Secrets Manager (planned) |
| No monitoring/alerting | ⚠️ Medium | Prometheus + Grafana (planned) |

---

## Scalability & Performance

### Current Performance Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| API Response Time | 200-500ms | <200ms | ⚠️ Acceptable |
| Frontend Load Time | <2s | <1s | ✅ Good |
| Database Query Time | 50-100ms | <50ms | ⚠️ Acceptable |
| Airflow DAG Runtime | 2-5 min | <2 min | ⚠️ Acceptable |
| Uptime | 99.5% | 99.9% | ⚠️ Good |

### Bottlenecks

1. **yfinance API**: 1-2s per ticker for real-time data
   - **Mitigation**: Batch requests, cache results for 1-5 minutes

2. **Single Gunicorn process**: Only 3 workers
   - **Mitigation**: Increase to 5 workers (2 * num_cores + 1)

3. **No CDN**: Static assets served from EC2
   - **Mitigation**: CloudFront CDN (planned)

4. **No caching layer**: Every request hits database or external API
   - **Mitigation**: Redis caching layer (planned)

### Horizontal Scaling Strategy

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FUTURE ARCHITECTURE                          │
│                          (K8s + Redis)                               │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     Load Balancer (ALB)                       │   │
│  └────────────────────────────┬─────────────────────────────────┘   │
│                               │                                      │
│                ┌──────────────┼──────────────┐                      │
│                │              │              │                       │
│         ┌──────▼──────┐ ┌────▼─────┐ ┌─────▼──────┐                │
│         │   Pod 1     │ │  Pod 2   │ │   Pod 3    │                │
│         │  Flask API  │ │ Flask API│ │  Flask API │                │
│         └──────┬──────┘ └────┬─────┘ └─────┬──────┘                │
│                │              │             │                        │
│                └──────────────┼─────────────┘                        │
│                               │                                      │
│                        ┌──────▼───────┐                              │
│                        │     Redis    │                              │
│                        │   (Cache)    │                              │
│                        └──────┬───────┘                              │
│                               │                                      │
│                        ┌──────▼───────┐                              │
│                        │   PostgreSQL │                              │
│                        │ (TimescaleDB)│                              │
│                        └──────────────┘                              │
└─────────────────────────────────────────────────────────────────────┘
```

**Scaling Plan**:

1. **Phase 1** (Current): Single EC2 instance, manual deployment
2. **Phase 2** (Q2 2026): Docker containers, Nginx load balancer, Redis cache
3. **Phase 3** (Q3 2026): Kubernetes cluster (EKS), horizontal pod autoscaling
4. **Phase 4** (Q4 2026): Multi-region deployment, CloudFront CDN

### Database Optimization

#### TimescaleDB Features

1. **Compression**: Compress chunks older than 7 days
```sql
ALTER TABLE stock_prices_intraday SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'ticker'
);

SELECT add_compression_policy('stock_prices_intraday', INTERVAL '7 days');
```

2. **Retention Policies**: Auto-delete old data
```sql
-- Delete 1-min bars older than 30 days
SELECT add_retention_policy('stock_prices_intraday', INTERVAL '30 days',
    if_not_exists => true);
```

3. **Continuous Aggregates**: Pre-computed rollups
```sql
-- Refresh 10-min aggregates every 10 minutes
SELECT add_continuous_aggregate_policy('cagg_prices_10min',
    start_offset => INTERVAL '1 day',
    end_offset => INTERVAL '10 minutes',
    schedule_interval => INTERVAL '10 minutes');
```

#### Query Optimization

```sql
-- Example: Optimized trend break query with indexes
CREATE INDEX idx_trend_breaks_ticker_date
    ON trend_breaks (ticker, signal_date DESC);

CREATE INDEX idx_trend_breaks_probability
    ON trend_breaks (probability)
    WHERE probability >= 80;

-- Query plan uses index scan instead of sequential scan
EXPLAIN ANALYZE
SELECT * FROM trend_breaks
WHERE ticker = 'AAPL'
  AND signal_date >= CURRENT_DATE - INTERVAL '30 days'
  AND probability >= 80
ORDER BY signal_date DESC;
```

---

## Related Documentation

- **[DATA_ARCHITECTURE.md](DATA_ARCHITECTURE.md)** - Complete database schema, query patterns, storage estimates
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Step-by-step deployment instructions for EC2, K8s, Docker
- **[SETUP_GUIDE.md](setup/SETUP_GUIDE.md)** - Local development setup, environment configuration
- **[COMPLETED_FEATURES.md](COMPLETED_FEATURES.md)** - Production-ready features and deployment status
- **[COMPREHENSIVE_FEATURE_DOCUMENTATION.md](COMPREHENSIVE_FEATURE_DOCUMENTATION.md)** - ML feature engineering specifications
- **[API_DOCUMENTATION.md](api/API_DOCUMENTATION.md)** - API endpoints, request/response formats
- **[CHANGELOG.md](../CHANGELOG.md)** - Version history and release notes
- **[ROADMAP.md](ROADMAP.md)** - Future development plans and priorities

---

**Last Updated**: February 2, 2026
**Maintained By**: Development Team
**Review Cycle**: Quarterly
