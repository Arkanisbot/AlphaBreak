# Getting Started

This guide explains how to set up your development environment and deploy changes to the EC2 production server.

---

## Prerequisites

- Git installed
- Python 3.10+
- SSH key for EC2 access (`docs/security/trading-db-key.pem`)

---

## 1. Clone the Repository

```bash
git clone https://github.com/SophistryDude/Securities_prediction_model.git
cd Securities_prediction_model
```

---

## 2. Branch Structure

| Branch | Purpose | Frontend API URL |
|--------|---------|------------------|
| `main` | Production (EC2) | `http://3.140.78.15:5000` |
| `localhost-dev` | Local development | `http://localhost:5001` |

---

## 3. EC2 Server Details

| Resource | URL/Address |
|----------|-------------|
| **Frontend** | http://3.140.78.15:8000 |
| **API** | http://3.140.78.15:5000 |
| **SSH** | `ubuntu@3.140.78.15` |
| **Database** | PostgreSQL on localhost:5432 (from EC2) |

---

## 4. Connect to EC2

```bash
ssh -i docs/security/trading-db-key.pem ubuntu@3.140.78.15
```

### Useful EC2 Commands

```bash
# Check service status
sudo systemctl status trading-api trading-frontend postgresql

# View API logs
sudo journalctl -u trading-api -f

# Restart services
sudo systemctl restart trading-api
sudo systemctl restart trading-frontend
```

---

## 5. Deploy Code Changes to EC2

### Option A: Quick Deploy (Frontend Only)

After making changes to `frontend/`:

```bash
# From your local machine
scp -i docs/security/trading-db-key.pem -r frontend/* ubuntu@3.140.78.15:~/frontend/
```

### Option B: Full Deploy (Frontend + Flask API)

```bash
# Copy frontend
scp -i docs/security/trading-db-key.pem -r frontend/* ubuntu@3.140.78.15:~/frontend/

# Copy Flask app
scp -i docs/security/trading-db-key.pem -r flask_app/* ubuntu@3.140.78.15:~/flask_app/

# SSH in and restart the API
ssh -i docs/security/trading-db-key.pem ubuntu@3.140.78.15 "sudo systemctl restart trading-api"
```

### Option C: Deploy Script

Create a `deploy.sh` in your project root:

```bash
#!/bin/bash
KEY="docs/security/trading-db-key.pem"
HOST="ubuntu@3.140.78.15"

echo "Deploying frontend..."
scp -i $KEY -r frontend/* $HOST:~/frontend/

echo "Deploying Flask API..."
scp -i $KEY -r flask_app/* $HOST:~/flask_app/

echo "Restarting services..."
ssh -i $KEY $HOST "sudo systemctl restart trading-api"

echo "Done! Check http://3.140.78.15:8000"
```

Run with: `bash deploy.sh`

---

## 6. Local Development

To work locally instead of against EC2:

```bash
# Switch to local dev branch
git checkout localhost-dev

# Install dependencies
pip install -r requirements.txt
pip install -r flask_app/requirements.txt

# Start the Flask API (terminal 1)
cd flask_app
python run_dev.py  # Runs on localhost:5001

# Start the frontend (terminal 2)
cd frontend
python -m http.server 8000  # Runs on localhost:8000

# Open http://localhost:8000
```

---

## 7. Database Access

The PostgreSQL database runs on EC2 with TimescaleDB.

### Connect from EC2

```bash
ssh -i docs/security/trading-db-key.pem ubuntu@3.140.78.15
sudo -u postgres psql -d trading_data
```

### Connect Remotely (via SSH tunnel)

```bash
# Terminal 1: Create tunnel
ssh -i docs/security/trading-db-key.pem -L 5433:localhost:5432 ubuntu@3.140.78.15 -N

# Terminal 2: Connect
psql -h localhost -p 5433 -U trading -d trading_data
# Password is in .env.aws
```

### Database Stats

- ~4 million stock price records
- 461 tickers (S&P 500 + extras)
- Data from 1980 to present

---

## 8. Project Structure

```
Securities_prediction_model/
├── frontend/           # Static HTML/JS frontend
│   ├── index.html
│   ├── app.js          # Main app (CONFIG.API_BASE_URL here)
│   └── styles.css
├── flask_app/          # Flask API backend
│   ├── app/
│   │   ├── routes/     # API endpoints
│   │   └── utils/      # Database, models
│   ├── run_dev.py      # Development server
│   └── wsgi.py         # Production entry point
├── src/                # Data scripts (not deployed)
├── docs/               # Documentation
│   └── security/       # SSH keys (gitignored)
└── kubernetes/         # K8s manifests (future use)
```

---

## 9. Common Tasks

### Update Frontend Code

1. Edit files in `frontend/`
2. Deploy: `scp -i docs/security/trading-db-key.pem -r frontend/* ubuntu@3.140.78.15:~/frontend/`
3. Refresh browser (no restart needed)

### Update API Code

1. Edit files in `flask_app/`
2. Deploy: `scp -i docs/security/trading-db-key.pem -r flask_app/* ubuntu@3.140.78.15:~/flask_app/`
3. Restart: `ssh -i docs/security/trading-db-key.pem ubuntu@3.140.78.15 "sudo systemctl restart trading-api"`

### Add New Python Dependencies

1. Add to `flask_app/requirements.txt`
2. SSH into EC2:
   ```bash
   ssh -i docs/security/trading-db-key.pem ubuntu@3.140.78.15
   cd ~/flask_app
   source venv/bin/activate
   pip install -r requirements.txt
   sudo systemctl restart trading-api
   ```

### Check if Services are Running

```bash
curl http://3.140.78.15:5000/api/health
curl http://3.140.78.15:8000
```

---

## 10. Troubleshooting

### API Not Responding

```bash
ssh -i docs/security/trading-db-key.pem ubuntu@3.140.78.15
sudo systemctl status trading-api
sudo journalctl -u trading-api -n 50
```

### Database Connection Issues

```bash
ssh -i docs/security/trading-db-key.pem ubuntu@3.140.78.15
sudo systemctl status postgresql
sudo -u postgres psql -c "SELECT 1"
```

### Permission Denied on SSH

```bash
chmod 400 docs/security/trading-db-key.pem
```

---

## Quick Reference

| Task | Command |
|------|---------|
| SSH to EC2 | `ssh -i docs/security/trading-db-key.pem ubuntu@3.140.78.15` |
| Deploy frontend | `scp -i docs/security/trading-db-key.pem -r frontend/* ubuntu@3.140.78.15:~/frontend/` |
| Restart API | `ssh ... "sudo systemctl restart trading-api"` |
| View API logs | `ssh ... "sudo journalctl -u trading-api -f"` |
| Check health | `curl http://3.140.78.15:5000/api/health` |
