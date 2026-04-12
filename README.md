# AlphaBreak

**Live:** [https://alphabreak.vip](https://alphabreak.vip)

AI-driven stock and options analysis platform. Bridges charting/TA and fundamental analysis in one tool — something no competitor does. Built for retail and professional traders who want Bloomberg-grade depth at a fraction of the cost.

---

## What This Is

A full-stack trading analysis platform with:
- **AI-powered trend break detection** (78% accuracy, 854K backtested trades, 98.5% win rate)
- **Regime-aware scoring** (BULL/BEAR/RANGE/HIGH_VOL classification with confidence %)
- **Auto-detected trendlines** with historical analog matching (no competitor offers this)
- **TradingView-quality charts** (Lightweight Charts, WebGL, 50K+ candles at 60fps)
- **13F institutional holdings** (20 hedge funds tracked, 85K+ holdings, 20K aggregates)
- **Options pricing** (Black-Scholes + Binomial Tree with fair value detection)
- **Trade journal with AI scoring** (entry/exit/timing grades)
- **8-indicator market sentiment** across 4 timeframes

## Architecture

```
Frontend:  Vanilla JS (no framework) + TradingView Lightweight Charts + Chart.js
Backend:   Flask API (Python) + Gunicorn
Database:  PostgreSQL 15 + TimescaleDB (106 tables, ~8GB)
Cache:     Redis
Scheduler: Apache Airflow (12 DAGs, KubernetesExecutor)
Infra:     k0s Kubernetes on AWS EC2 (t3.medium)
Domain:    alphabreak.vip (SSL via Let's Encrypt)
```

## Getting Caught Up

### Key Documentation
| Doc | What It Covers |
|-----|---------------|
| [docs/ROADMAP.md](docs/ROADMAP.md) | Full feature roadmap by tier (Free/Pro/Elite/API), what's built vs planned |
| [docs/COMPETITIVE_ANALYSIS.md](docs/COMPETITIVE_ANALYSIS.md) | Feature matrix vs 10 competitors + glossary |
| [docs/PRICING_TIERS.md](docs/PRICING_TIERS.md) | Free / Pro $99 / Elite $299 / API $499-999 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture + data flow |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production deployment procedures |
| [docs/csv/](docs/csv/) | Excel competitive analysis files (bifurcation, vs-all-competitors) |

### Codebase Structure
```
frontend/               # Static HTML/JS/CSS served by nginx
  index.html            # Single-page app (all tabs)
  app.js                # Core: sidebar, tabs, auth init, widget collapse, landing/contact logic
  onboarding.js         # 3-stage onboarding: tooltip tour, checklist banner, empty states
  analyze.js            # Security Analysis page (default for authenticated users)
  charts.js             # AlphaCharts module (Lightweight Charts wrapper + AI popovers)
  chart-indicators.js   # Indicator sub-panes (RSI, MACD, Stochastic, VWAP)
  chart-drawings.js     # Drawing tools (trendline, hline, Fibonacci, rectangle)
  educational.js        # AI briefs, tooltips, guide panels for Reports/Earnings/Options
  dashboard.js          # Sentiment, sectors, VIX, commodities
  reports.js            # Trend Break Reports
  earnings.js           # Quarterly Earnings
  longterm.js           # Long Term Trading + 13F holdings
  portfolio.js          # Portfolio tracker
  forex.js              # Forex correlations
  journal.js            # Trade journal
  auth.js               # JWT authentication
  notifications.js      # In-app notifications
  account.js            # User profile + settings
  indicators.js         # Indicator guide
  styles.css            # All CSS (~7K lines, dark theme)

flask_app/              # Flask API
  app/__init__.py       # App factory, blueprint registration
  app/routes/           # API endpoints
    analyze.py          # /api/analyze/* (security analysis, chart, trendlines, patterns, compare)
    reports.py          # /api/reports/* (trend break reports)
    earnings.py         # /api/earnings/* (earnings calendar)
    options.py          # /api/options/* (options pricing)
    portfolio.py        # /api/portfolio/* (paper trading)
    journal.py          # /api/journal/* (trade journal)
    longterm.py         # /api/longterm/* (13F holdings)
    forex.py            # /api/forex/* (currency correlations)
    watchlist.py        # /api/watchlist/* (batch ticker data)
    auth.py             # /api/auth/* (JWT auth)
    user.py             # /api/user/* (watchlist management)
    notifications.py    # /api/notifications/*
    health.py           # /api/health, /api/ready, /api/live
  app/services/         # Business logic
    analyze_service.py  # Single-ticker deep-dive data aggregation
    trendline_service.py # Auto-detected trendlines + regime classification
    pattern_service.py  # Candlestick pattern recognition + seasonality
    watchlist_service.py # Indicator calculations, chart data
    longterm_service.py # 13F aggregate queries
    dashboard_service.py # Sentiment calculations
    report_service.py   # Trend break detection
    journal_service.py  # AI trade scoring
  app/utils/
    database.py         # PostgreSQL connection pool + helpers
    auth.py             # JWT decorators, API key validation

src/                    # Data pipelines + ML models
  sec_13f_fetcher.py    # SEC EDGAR 13F filing fetcher
  detect_trend_breaks.py # Trend break detection engine
  meta_learning_model.py # Meta-learning indicator selection
  options_pricing.py    # Black-Scholes + Binomial Tree
  forex_correlation_model.py # Forex analysis
  data_fetcher.py       # yfinance data fetching

kubernetes/             # K8s deployment manifests
  api-deployment.yaml   # Flask API pods (3 replicas, HPA)
  api-service.yaml      # NodePort 30427
  airflow/              # Airflow scheduler, webserver, DAGs
  scripts/              # Phased deployment scripts
```

### Key API Endpoints
```
GET  /api/analyze/AAPL              # Full analysis (header, stats, indicators, signals, analyst, earnings, institutional)
GET  /api/analyze/AAPL/chart        # OHLCV + volume + SMA + Bollinger overlays
GET  /api/analyze/AAPL/trendlines   # Auto-detected trendlines + regime + analog scores
GET  /api/analyze/AAPL/patterns     # Candlestick patterns + seasonality
GET  /api/analyze/AAPL/compare      # Normalized % comparison vs SPY, VIX, sector ETF
GET  /api/analyze/search?q=APP      # Ticker autocomplete
GET  /api/reports/latest?frequency=daily  # Trend break reports
GET  /api/earnings/calendar         # Earnings calendar
GET  /api/longterm/holdings         # 13F institutional holdings
GET  /api/options/chain/AAPL        # Options chain
GET  /api/forex/correlations        # Currency pair correlations
GET  /api/portfolio/summary         # Portfolio tracker
```

### Deployment
```bash
PEM="docs/other/security/trading-db-key.pem"

# Frontend (zero downtime — nginx serves from repo clone):
git push
ssh -i "$PEM" ubuntu@3.140.78.15 "cd ~/Securities_prediction_model && git pull"

# Backend (rebuild Docker + restart pods):
git push
ssh -i "$PEM" ubuntu@3.140.78.15 "cd ~/Securities_prediction_model && git pull && sudo docker build -f flask_app/Dockerfile -t trading-api:latest . && sudo docker save trading-api:latest | sudo k0s ctr images import - && sudo docker system prune -af && sudo k0s kubectl delete pods -n trading-system -l app=trading-api --force"
```

## What's Built (Free Tier)

| Feature | Status |
|---------|--------|
| Security Analysis (single-ticker deep dive) | Complete |
| TradingView Lightweight Charts (candlestick + volume) | Complete |
| Auto-detected trendlines with clickable AI popovers | Complete (Pro-gated) |
| Drawing tools (trendline, Fibonacci, hline, rectangle) | Complete |
| Indicator sub-panes (RSI, MACD, Stochastic, VWAP) | Complete |
| Market regime classification (BULL/BEAR/RANGE/HIGH_VOL) | Complete |
| Historical analog matching | Complete |
| Candlestick pattern recognition (8 patterns) | Complete (Pro-gated) |
| Seasonality heatmap (5yr monthly) | Complete (Pro-gated) |
| Symbol comparison overlay (SPY, VIX, sector ETF) | Complete |
| AI Analysis Brief (plain-English synthesis) | Complete |
| AI Dashboard (regime, signals, sectors, screener) | Complete |
| Quant Letter Grades (A+ through F, 6 factors) | Complete |
| Short interest + squeeze risk score | Complete |
| Dividend analysis + safety grade | Complete |
| Market Maker expected move (ATM straddle) | Complete |
| Educational tooltips + guide panels | Complete |
| Trend break reports (3 frequencies) | Complete |
| Options analysis (fair value, Greeks, MM move) | Complete |
| 13F institutional holdings (20 funds) | Complete |
| Portfolio tracker (paper trading) | Complete |
| Trade journal with AI scoring | Complete |
| Forex correlations (21 pairs) | Complete |
| Market sentiment (8 indicators) | Complete |
| Earnings calendar + CBOE activity | Complete |
| All widgets collapsible | Complete |
| Pricing page (4-tier funnel) | Complete |
| Landing page (marketing, social proof, CTAs) | Complete |
| Contact page (form, FAQ, info) | Complete |
| Onboarding flow (tooltip tour + checklist + empty states) | Complete |
| Premium gating with 1 free trial per feature | Complete |

## What's Next (Pro Tier — Not Yet Built)

See [docs/ROADMAP.md](docs/ROADMAP.md) for the full list. Highlights:
- Peer comparison tables
- Insider trading signals (SEC Form 4)
- News NLP sentiment (FinBERT)
- Unusual options activity
- Multi-chart layout with synced crosshairs
- More indicators (Ichimoku, OBV, ATR, Parabolic SAR)
- Regime-aware indicator weighting
- Natural-language scripting for alerts and screeners
- Real-time data via Polygon.io
- Stripe billing integration

## Tech Decisions

**Why vanilla JS instead of React?** The frontend was built incrementally over 6 months. Each tab is a self-contained module. At current complexity (~7K CSS, ~15 JS files), a framework migration would cost weeks with no user-facing benefit. If we add significantly more interactivity (drawing tools, multi-chart), we'd consider React for those components specifically.

**Why Lightweight Charts instead of TradingView's paid library?** The paid TradingView charting library costs $15K/year. Lightweight Charts is free, open-source (Apache 2.0), 45KB, WebGL-accelerated, and looks nearly identical. Our AI overlays (trendlines, regime, patterns) are the differentiator, not the chart library.

**Why Flask instead of FastAPI?** Started with Flask for simplicity. The API is stateless and behind Gunicorn with 3 workers. Performance is adequate (<1s for most endpoints with caching). Migration to FastAPI would help with async data fetching but isn't a bottleneck yet.

---

**Maintained by:** Nick (solo dev)
**Contact:** contact@alphabreak.vip
