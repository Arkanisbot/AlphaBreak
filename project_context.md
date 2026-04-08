# Securities Prediction Model - Project Context

## Project Overview
A comprehensive trading analysis platform with:
- Real-time market data analysis
- Options pricing with fair value calculations
- Forex currency correlation analysis
- Portfolio management with automated trading signals
- Market sentiment analysis
- Technical indicators

## Recent Updates (April 2026)

### April 3, 2026 - Infrastructure & AWS CLI

#### 1. AWS CLI Setup
- **Configured AWS CLI** on local Windows dev machine
- VSCode required restart due to cached PowerShell not recognizing aws path
- `aws sts get-caller-identity` verified successfully

#### 2. EBS Volume Expansion
- **Expanded EBS from 50GB → 100GB** using AWS CLI (`aws ec2 modify-volume`)
- Volume: `vol-06270ebf514fb8671` (gp2)
- Grew partition with `growpart` and resized ext4 filesystem with `resize2fs`
- Zero downtime — done live on running instance
- Result: 97GB available, 39% used, 59GB free
- Resolves recurring disk pressure during Docker builds

---

## Updates (February 2026)

### February 9, 2026 - Portfolio DAG & API Bug Fixes

#### 1. Portfolio DAG - Database Connection Fix
- **Fixed Kubernetes hostname fallback**: DAG and Flask app both defaulted to `postgres-timeseries-service` (a Kubernetes DNS name) instead of `127.0.0.1` when env vars were unset
  - Modified (EC2): `/home/ubuntu/dags/portfolio_update_dag.py` - `DB_CONFIG` defaults
  - Modified (EC2): `/home/ubuntu/flask_app/app/utils/database.py` - pool defaults
  - Modified (EC2): `/home/ubuntu/flask_app/app/services/portfolio_service.py` - `get_db_config()` defaults
  - All DB defaults now use `127.0.0.1` and correct password

#### 2. Portfolio DAG - SQL Schema Fixes
- **Fixed `fetch_trend_break_signals`**: Query referenced nonexistent `trend_break_reports` table
  - Rewritten to query `trend_breaks` table with correct columns (`break_type`, `direction_after`, `price_at_break`, `magnitude`)
  - Bullish signal: `direction_after = 'increasing'`; Bearish: `'decreasing'`
  - Time window widened from 24 hours to 30 days
  - Modified: `kubernetes/airflow/dags/portfolio_update_dag.py`

- **Fixed `fetch_13f_signals`**: Query used nonexistent columns (`signal`, `total_value_usd`, `funds_buying`, etc.)
  - Rewritten with correct column mappings: `institutional_sentiment` > 1.0 = STRONG_BUY, > 0.5 = BUY
  - Uses latest `report_quarter` instead of time-based filter
  - Column mapping: `total_market_value`, `funds_initiated + funds_increased`, `net_shares_change`
  - Modified: `kubernetes/airflow/dags/portfolio_update_dag.py`

#### 3. Portfolio DAG - Python Path Fixes
- **Fixed import paths**: DAG used Docker paths (`/app/src`) instead of EC2 paths (`/home/ubuntu/src`)
  - Changed `sys.path.insert(0, '/app')` to `/home/ubuntu`
  - Changed all `sys.path.insert(0, '/app/src')` to `/home/ubuntu/src`
  - Modified: `kubernetes/airflow/dags/portfolio_update_dag.py`

#### 4. Portfolio DAG - Missing Dependencies
- **Installed `yfinance`** in Airflow venv (`/home/ubuntu/airflow/airflow_venv/`)
- **Fixed `log_summary` task**: Format string crash on `None` values from snapshot

#### 5. Flask API - Portfolio Service Fix
- **Fixed password default**: `portfolio_service.py` had wrong DB password default (`trading123`)
  - Changed to `trading_password`
- **Restarted gunicorn** via `start_gunicorn.sh` (sets correct env vars)

#### Result
- DAG successfully runs all 10 tasks end-to-end
- Portfolio now holds 6 swing positions (AMP, BLK, CAT, CMI, DPZ, FICO)
- API at `https://alphabreak.vip/api/portfolio/summary` returns live data

### February 2, 2026 - Deployment and Fixes

#### 1. Options Analysis Enhancements
- **Fixed API Authentication Error**: Removed `@require_api_key` decorator from frontend endpoints to allow seamless API access
  - Modified: `flask_app/app/routes/frontend_compat.py`
  - Endpoints now accessible without API keys for development

- **Extended Options Window**: Updated options analysis to show all options expiring within 90 days (previously only nearest expiry)
  - Modified: `src/options_pricing.py`
  - Added: `get_options_within_days()` function
  - Each option now displays specific expiry date and days until expiration

- **Fixed Fair Value Calculations**: Added parameter validation with sensible defaults
  - Volatility: defaults to 30% if invalid
  - Time to expiry: minimum 1 day
  - Risk-free rate: defaults to 4.5%

#### 2. Forex Chart Fixes
- **Fixed DXY Inline Charts**: Corrected data parsing for forex currency pair charts
  - Modified: `frontend/forex.js` (lines 623-643)
  - Charts now properly calculate DXY index from chart_data array
  - Added dual Y-axis visualization for currency pairs with DXY backdrop

#### 3. Watchlist Features
- **Ticker Validation**: Added real-time validation before adding securities to watchlist
  - Modified: `frontend/watchlist.js`
  - API check ensures ticker exists before adding

- **Snackbar Notifications**: Implemented global notification system
  - Added to: `frontend/app.js`, `frontend/watchlist.js`
  - Styled in: `frontend/styles.css`
  - Success, error, info, and warning message types

- **"+ Watch" Button**: Added quick-add functionality to options analysis page
  - Modified: `frontend/index.html`, `frontend/app.js`
  - Adds analyzed ticker directly to intra-day trading watchlist

#### 4. UI Improvements
- **Market Sentiment Visibility**: Hidden market sentiment widget on portfolio page for cleaner UI
  - Modified: `frontend/app.js` tab switching logic

#### 5. Airflow Deployment
- **Automated Portfolio Updates**: Deployed Apache Airflow for scheduled portfolio management
  - Installed: Apache Airflow 2.8.1 with PostgreSQL backend
  - Location: `/home/ubuntu/airflow/`
  - Services: `airflow-scheduler.service`, `airflow-webserver.service`
  - DAG: `portfolio_update` runs at 9 AM EST on weekdays (Mon-Fri)
  - Web UI: http://3.140.78.15:8080 (admin/admin123)

- **Portfolio DAG Features**:
  - Fetches trend break signals (80%+ probability threshold)
  - Analyzes 13F institutional sentiment
  - Processes buy/sell signals
  - Manages long-term positions (75% allocation)
  - Executes swing trades (25% allocation)
  - Handles covered calls and stop-losses
  - Creates daily portfolio snapshots

## Deployment Architecture

### EC2 Instance (3.140.78.15)
- **Domain**: https://alphabreak.vip (SSL via Let's Encrypt)
- **Orchestration**: k0s Kubernetes single-node (all services containerized)
- **Frontend**: Nginx on port 443 (serves static files)
- **API**: Flask/Gunicorn (containerized, proxied via Nginx at `/api/`)
- **Airflow**: KubernetesExecutor, 12 DAGs
- **Database**: PostgreSQL 15 + TimescaleDB (containerized, 106 tables)
- **Cache**: Redis (containerized)
- **Storage**: 100GB EBS (gp2) — expanded from 50GB on April 3, 2026
- **SSH**: Port 22 (username: `ubuntu`)

### Services Running
1. **Flask API** (`start_gunicorn.sh`)
   - Location: `/home/ubuntu/flask_app/`
   - Virtual env: `/home/ubuntu/flask_app/venv/`

2. **Airflow Scheduler**
   - Systemd service: `airflow-scheduler.service`
   - Scans DAGs every 30 seconds
   - LocalExecutor for task execution

3. **Airflow Webserver**
   - Systemd service: `airflow-webserver.service`
   - 4 gunicorn workers
   - Basic auth + session auth

### Database Configuration
- **Host**: 127.0.0.1:5432
- **Database**: trading_data
- **User**: trading
- **Tables**:
  - Portfolio management (portfolio_signals, portfolio_holdings, portfolio_trades, etc.)
  - Trend break reports
  - 13F institutional data
  - Forex data
  - Securities metadata

## File Structure

```
Securities_prediction_model/
├── flask_app/              # Backend API
│   ├── app/
│   │   ├── routes/
│   │   │   ├── frontend_compat.py  # Frontend API endpoints
│   │   │   ├── options.py          # Options analysis
│   │   │   └── portfolio.py        # Portfolio management
│   │   └── utils/
│   ├── venv/               # Python virtual environment
│   └── .env                # Environment configuration
├── frontend/               # Static web application
│   ├── index.html
│   ├── app.js              # Main application logic
│   ├── forex.js            # Forex analysis
│   ├── watchlist.js        # Watchlist management
│   ├── styles.css
│   └── ...
├── src/                    # Core analysis modules
│   ├── options_pricing.py  # Options analysis (Black-Scholes, Binomial)
│   ├── portfolio_manager.py # Portfolio management logic
│   └── ...
├── kubernetes/airflow/dags/ # Airflow DAGs
│   └── portfolio_update_dag.py
└── docs/
    └── other/security/
        └── trading-db-key.pem  # EC2 SSH key
```

## SSH Access

### Connection
```bash
ssh -i "Securities_prediction_model/docs/other/security/trading-db-key.pem" ubuntu@3.140.78.15
```

**Note**: Port 22 may be blocked on some home/corporate networks. Use mobile hotspot if connection times out.

## Known Issues & Notes

1. **SSH Port Blocking**: Some ISPs (Comcast, Cox) block outbound port 22 for residential customers
   - Workaround: Use mobile hotspot or VPN

2. **API Key Authentication**: Currently disabled for frontend endpoints to simplify development
   - Consider re-enabling for production with proper key management

3. **Database Connection**: Flask app configured to use localhost PostgreSQL
   - Airflow uses same database for metadata storage

4. **Deployment Method**: Files currently deployed via SCP
   - Consider implementing CI/CD pipeline for automated deployments

## Development Workflow

### Testing Changes Locally
1. Make code changes in local repository
2. Test locally if possible
3. Deploy to EC2 via SCP (when SSH is available)
4. Restart affected services

### Restarting Services
```bash
# Restart Flask API
pkill -f 'gunicorn.*5000'
cd /home/ubuntu/flask_app && nohup bash start_gunicorn.sh > /home/ubuntu/gunicorn.log 2>&1 &

# Restart Airflow services
sudo systemctl restart airflow-scheduler
sudo systemctl restart airflow-webserver
```

### Checking Logs
```bash
# Flask API logs
tail -f /home/ubuntu/gunicorn.log

# Airflow scheduler logs
sudo journalctl -u airflow-scheduler -f

# Airflow webserver logs
sudo journalctl -u airflow-webserver -f
```

## Next Steps

- [ ] Set up CI/CD pipeline for automated deployments
- [ ] Enable API key authentication for production
- [ ] Add monitoring and alerting (Prometheus/Grafana)
- [x] Configure SSL certificates for HTTPS (done - Let's Encrypt via Certbot)
- [ ] Set up database backups
- [ ] Implement portfolio email notifications
- [ ] Add more technical indicators
- [ ] Expand forex pair coverage
- [ ] Populate `trend_break_predictions` table (currently empty - predictions model not running)
- [ ] Set up systemd service for gunicorn (currently started manually via start_gunicorn.sh)

## Contacts & Resources

- **Repository**: [data-acq-functional-SophistryDude](https://github.com/SophistryDude/data-acq-functional-SophistryDude)
- **EC2 Instance**: 3.140.78.15 (us-east-2)
- **Airflow UI**: http://3.140.78.15:8080
- **Application**: https://alphabreak.vip

---

Last Updated: April 3, 2026
