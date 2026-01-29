# Securities Prediction Model - Setup Guide

This guide walks you through setting up the project on a fresh machine. No AI assistance required.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Clone the Repository](#clone-the-repository)
3. [Environment Configuration](#environment-configuration)
4. [Install Dependencies](#install-dependencies)
5. [Database Setup](#database-setup)
6. [Running the Flask API](#running-the-flask-api)
7. [Running the Frontend](#running-the-frontend)
8. [Data Population Scripts](#data-population-scripts)
9. [Model Training (Optional)](#model-training-optional)
10. [Docker Deployment](#docker-deployment)
11. [Kubernetes Deployment](#kubernetes-deployment)
12. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.10+ | Backend, data scripts |
| PostgreSQL | 15+ | Database (if running locally) |
| Git | Any | Version control |

### Optional Software

| Software | Version | Purpose |
|----------|---------|---------|
| Docker | 20+ | Containerized deployment |
| Docker Compose | 2.0+ | Multi-container orchestration |
| kubectl | 1.28+ | Kubernetes deployment |
| Redis | 7+ | Rate limiting, caching |

---

## Clone the Repository

```bash
git clone https://github.com/SophistryDude/Securities_prediction_model.git
cd Securities_prediction_model
```

---

## Environment Configuration

### Option A: Connect to Existing EC2 Database (Recommended)

The project has a running TimescaleDB instance on AWS EC2 with all data pre-loaded.

1. Copy the AWS environment file:
   ```bash
   cp .env.aws .env
   ```

2. The database credentials are already configured for `3.140.78.15:5432`

3. Copy Flask-specific settings:
   ```bash
   cp flask_app/.env.example flask_app/.env
   ```

4. Edit `flask_app/.env` and update the database settings to match:
   ```
   TIMESERIES_DB_HOST=3.140.78.15
   TIMESERIES_DB_PORT=5432
   TIMESERIES_DB_NAME=trading_data
   TIMESERIES_DB_USER=trading
   TIMESERIES_DB_PASSWORD=<password from .env.aws>
   TIMESERIES_DB_SSLMODE=require
   ```

### Option B: Set Up Local Database

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your local PostgreSQL credentials

3. Copy Flask settings:
   ```bash
   cp flask_app/.env.example flask_app/.env
   ```

4. Edit `flask_app/.env` with matching database credentials

---

## Install Dependencies

### Python Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate
```

### Install Root Dependencies (for src/ scripts)

```bash
pip install -r requirements.txt
```

### Install Flask API Dependencies

```bash
cd flask_app
pip install -r requirements.txt
cd ..
```

### Install All Dependencies at Once

```bash
pip install -r requirements.txt -r flask_app/requirements.txt
```

---

## Database Setup

### Option A: Using EC2 Database

No setup required - database is already running and populated.

Test connection:
```bash
python -c "
import psycopg2
conn = psycopg2.connect(
    host='3.140.78.15',
    port=5432,
    dbname='trading_data',
    user='trading',
    password='<password from .env.aws>',
    sslmode='require'
)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM stock_prices;')
print(f'Stock prices: {cur.fetchone()[0]:,} rows')
conn.close()
"
```

### Option B: Local PostgreSQL + TimescaleDB

1. Install PostgreSQL 15 and TimescaleDB extension

2. Create database and user:
   ```sql
   CREATE USER trading WITH PASSWORD 'your-password';
   CREATE DATABASE trading_data OWNER trading;
   \c trading_data
   CREATE EXTENSION IF NOT EXISTS timescaledb;
   ```

3. Run schema initialization:
   ```bash
   psql -U trading -d trading_data -f kubernetes/01-init-timescaledb.sql
   psql -U trading -d trading_data -f kubernetes/schema_v2_intraday.sql
   psql -U trading -d trading_data -f kubernetes/schema_trend_breaks.sql
   psql -U trading -d trading_data -f kubernetes/schema_reports.sql
   psql -U trading -d trading_data -f kubernetes/schema_earnings.sql
   ```

4. Populate initial data:
   ```bash
   python src/populate_database.py --tickers AAPL MSFT GOOGL
   python src/populate_market_indices.py
   ```

---

## Running the Flask API

### Development Mode

```bash
cd flask_app
python run_dev.py
```

Server runs on `http://localhost:5001`

### Production Mode (with Gunicorn)

```bash
cd flask_app
gunicorn -c gunicorn_config.py wsgi:app
```

Server runs on `http://0.0.0.0:5000`

### Verify API is Running

```bash
curl http://localhost:5001/api/health
```

Expected response:
```json
{"status": "healthy", "models_loaded": false}
```

---

## Running the Frontend

The frontend is static HTML/CSS/JavaScript with no build step.

### Option 1: Python HTTP Server

```bash
cd frontend
python -m http.server 8000
```

Access at `http://localhost:8000`

### Option 2: VS Code Live Server

1. Install the "Live Server" extension in VS Code
2. Right-click `frontend/index.html`
3. Select "Open with Live Server"

### Configure API URL

Edit `frontend/app.js` and update the `CONFIG` object:

```javascript
const CONFIG = {
    API_BASE_URL: 'http://localhost:5001',  // Update if API runs elsewhere
    API_KEY: '',  // Add if API_KEY_REQUIRED=true
};
```

---

## Data Population Scripts

All scripts are in the `src/` directory and require database connection.

### Stock Price Data

```bash
# Specific tickers
python src/populate_database.py --tickers AAPL MSFT GOOGL AMZN

# S&P 500 (full dataset)
python src/populate_database.py --sp500
```

### Market Indices

```bash
python src/populate_market_indices.py
```

### Dark Pool Data (FINRA)

```bash
python src/finra_darkpool_fetcher.py
```

### Institutional Holdings (SEC 13F)

```bash
python src/sec_13f_fetcher.py
```

### Options Data (CBOE)

```bash
python src/cboe_options_fetcher.py
```

---

## Model Training (Optional)

The Flask API works without trained models (with reduced functionality).

To train models, you need historical data in the database.

### Train Trend Break Model

```bash
python src/detect_trend_breaks.py --train
```

### Train Meta-Learning Model

```bash
python src/meta_learning_model.py --train
```

Models are saved to the `models/` directory:
- `indicator_reliability_model.h5` - Keras neural network
- `trend_break_model.json` - XGBoost classifier
- `model_metadata.pkl` - Model metadata

---

## Docker Deployment

### Build and Run with Docker Compose

```bash
cd flask_app

# Build the image
docker-compose build

# Start services (API + Redis)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services:
- API: `http://localhost:5000`
- Redis: `localhost:6379`

### Environment Variables for Docker

Create `flask_app/.env` with production settings before running:

```bash
FLASK_ENV=production
SECRET_KEY=<generate-secure-key>
TIMESERIES_DB_HOST=3.140.78.15
TIMESERIES_DB_PORT=5432
TIMESERIES_DB_NAME=trading_data
TIMESERIES_DB_USER=trading
TIMESERIES_DB_PASSWORD=<password>
TIMESERIES_DB_SSLMODE=require
```

---

## Kubernetes Deployment

### Prerequisites

- Docker Desktop with Kubernetes enabled, OR
- minikube, OR
- A cloud Kubernetes cluster (GKE, EKS, AKS)

### Local Deployment (Windows/Docker Desktop)

```powershell
.\deploy-local.ps1
```

This creates:
- Namespace: `trading-system`
- ConfigMap and Secrets
- Redis deployment
- Flask API deployment
- Services and ingress

### Manual Deployment

```bash
# Create namespace
kubectl apply -f kubernetes/namespace.yaml

# Apply configs and secrets
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secrets.yaml

# Deploy services
kubectl apply -f kubernetes/redis-deployment.yaml
kubectl apply -f kubernetes/api-deployment.yaml
kubectl apply -f kubernetes/api-service.yaml
```

### Access the API

```bash
# Port forward to access locally
kubectl port-forward svc/trading-api -n trading-system 5000:5000

# Access at http://localhost:5000
```

---

## Troubleshooting

### Database Connection Errors

**Error:** `connection refused` or `could not connect to server`

1. Verify database host is reachable:
   ```bash
   ping 3.140.78.15
   ```

2. Check port is open:
   ```bash
   nc -zv 3.140.78.15 5432
   ```

3. Verify credentials in `.env` file match the database

### SSL Connection Errors

**Error:** `SSL connection is required`

Set `sslmode=require` in your environment:
```
TIMESERIES_DB_SSLMODE=require
```

### Module Not Found Errors

Ensure you've installed all dependencies:
```bash
pip install -r requirements.txt -r flask_app/requirements.txt
```

### Models Not Loading

The API works without models. To check model status:
```bash
curl http://localhost:5001/api/health
```

If `models_loaded: false`, either:
- Train models using the training scripts
- Copy pre-trained models to `models/` directory

### Frontend Not Connecting to API

1. Verify API is running (`curl http://localhost:5001/api/health`)
2. Check `frontend/app.js` has correct `API_BASE_URL`
3. Check browser console for CORS errors
4. Ensure Flask CORS is configured (`CORS_ORIGINS=*` in `.env`)

### Port Already in Use

```bash
# Find process using port 5000
netstat -ano | findstr :5000  # Windows
lsof -i :5000                  # macOS/Linux

# Kill the process or use a different port
```

---

## Quick Reference

| Component | Default Port | Command |
|-----------|-------------|---------|
| Flask API (dev) | 5001 | `cd flask_app && python run_dev.py` |
| Flask API (prod) | 5000 | `cd flask_app && gunicorn -c gunicorn_config.py wsgi:app` |
| Frontend | 8000 | `cd frontend && python -m http.server 8000` |
| Redis | 6379 | `docker run -d -p 6379:6379 redis:7-alpine` |
| Docker Compose | 5000, 6379 | `cd flask_app && docker-compose up -d` |

---

## External Services

| Service | Required | Free Tier | Sign Up |
|---------|----------|-----------|---------|
| PostgreSQL/TimescaleDB | Yes | EC2 provided | - |
| Polygon.io | No | 5 calls/min | https://polygon.io |
| FINRA API | No | Unlimited | Default creds work |
| SEC EDGAR | No | Unlimited | No signup |
| Yahoo Finance | No | Unlimited | No signup |

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/SophistryDude/Securities_prediction_model/issues
