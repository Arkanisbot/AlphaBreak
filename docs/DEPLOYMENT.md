# Production Deployment Guide

**Version**: 2.0
**Last Updated**: February 2, 2026
**Target Environment**: AWS EC2 (us-east-2)

---

## Table of Contents

1. [Overview](#overview)
2. [Infrastructure Provisioning](#infrastructure-provisioning)
3. [Initial Server Setup](#initial-server-setup)
4. [Application Deployment](#application-deployment)
5. [Service Configuration](#service-configuration)
6. [Database Management](#database-management)
7. [SSL & Security Configuration](#ssl--security-configuration)
8. [Monitoring & Logging](#monitoring--logging)
9. [Backup & Disaster Recovery](#backup--disaster-recovery)
10. [Update Procedures](#update-procedures)
11. [Rollback Procedures](#rollback-procedures)
12. [Troubleshooting](#troubleshooting)

---

## Overview

This guide covers production deployment to AWS EC2. For local development or Kubernetes/Docker deployment, see [SETUP_GUIDE.md](setup%20guide/SETUP_GUIDE.md).

### Current Production Environment

- **Instance**: EC2 t3.medium (us-east-2)
- **Public IP**: 3.140.78.15
- **OS**: Ubuntu 22.04 LTS
- **Services**: Flask API, Nginx, PostgreSQL 15, Airflow 2.8.1
- **Branches**:
  - `main` - Production deployment
  - `localhost-dev` - Local development

### Service Endpoints

| Service | Port | URL | Access |
|---------|------|-----|--------|
| Frontend | 8000 | http://3.140.78.15:8000 | Public |
| Flask API | 5000 | http://3.140.78.15:5000 | Localhost only |
| Airflow UI | 8080 | http://3.140.78.15:8080 | Public (basic auth) |
| PostgreSQL | 5432 | localhost:5432 | Localhost only |
| SSH | 22 | 3.140.78.15:22 | Key-based auth |

---

## Infrastructure Provisioning

### 1. AWS EC2 Instance Setup

#### Launch Instance

1. **Navigate to EC2 Console** (us-east-2)
2. **Launch Instance**:
   - **Name**: securities-prediction-model-prod
   - **AMI**: Ubuntu Server 22.04 LTS (64-bit x86)
   - **Instance Type**: t3.medium (2 vCPU, 4 GB RAM)
   - **Key Pair**: Create or select existing (download .pem file)
   - **Storage**: 30 GB gp3 SSD
   - **Network**: Default VPC

#### Security Group Configuration

**Name**: securities-prediction-sg

| Type | Protocol | Port | Source | Description |
|------|----------|------|--------|-------------|
| SSH | TCP | 22 | My IP / 0.0.0.0/0 | SSH access |
| HTTP | TCP | 8000 | 0.0.0.0/0 | Frontend |
| Custom TCP | TCP | 8080 | 0.0.0.0/0 | Airflow UI |
| Custom TCP | TCP | 5000 | 127.0.0.1/32 | Flask API (localhost only) |
| PostgreSQL | TCP | 5432 | 127.0.0.1/32 | Database (localhost only) |

**Security Notes**:
- Port 5000 (API) and 5432 (PostgreSQL) should NEVER be exposed to public internet
- Port 22 may be blocked by some ISPs - document this in troubleshooting

#### Elastic IP (Optional but Recommended)

1. **Allocate Elastic IP** from EC2 console
2. **Associate** with instance
3. **Update DNS** records (if using custom domain)

### 2. Initial Costs Estimate

| Resource | Monthly Cost |
|----------|--------------|
| t3.medium instance | ~$30/month |
| 30 GB gp3 storage | ~$3/month |
| Elastic IP (optional) | $0 (if associated) |
| Data transfer (100 GB) | ~$9/month |
| **Total** | **~$42/month** |

---

## Initial Server Setup

### 1. Connect to Instance

```bash
# Download key from AWS console
chmod 400 trading-db-key.pem

# Connect
ssh -i trading-db-key.pem ubuntu@3.140.78.15
```

**Troubleshooting**: If connection times out, your ISP may block port 22. Use mobile hotspot or AWS Systems Manager Session Manager.

### 2. System Update & Essential Packages

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y \
    git \
    python3.10 \
    python3.10-venv \
    python3-pip \
    postgresql-15 \
    postgresql-contrib \
    nginx \
    htop \
    tmux \
    curl \
    vim

# Install TimescaleDB
sudo sh -c "echo 'deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -cs) main' > /etc/apt/sources.list.d/timescaledb.list"
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -
sudo apt update
sudo apt install -y timescaledb-2-postgresql-15
sudo timescaledb-tune --quiet --yes
```

### 3. Create Directory Structure

```bash
# Create application directories
mkdir -p ~/flask_app
mkdir -p ~/frontend
mkdir -p ~/dags
mkdir -p ~/airflow
mkdir -p ~/logs

# Set permissions
chmod 755 ~/flask_app ~/frontend ~/dags ~/airflow
```

### 4. Configure Firewall (UFW)

```bash
# Enable firewall
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8000/tcp  # Frontend
sudo ufw allow 8080/tcp  # Airflow UI
sudo ufw enable

# Verify
sudo ufw status
```

---

## Application Deployment

### 1. Clone Repository

```bash
cd ~
git clone https://github.com/SophistryDude/data-acq-functional-SophistryDude.git repo
cd repo
git checkout main  # Use main branch for production
```

### 2. Deploy Frontend

```bash
# Copy frontend files
cp -r AlphaBreak/frontend/* ~/frontend/

# Configure Nginx
sudo tee /etc/nginx/sites-available/frontend <<EOF
server {
    listen 8000;
    server_name 3.140.78.15;

    root /home/ubuntu/frontend;
    index index.html;

    location / {
        try_files \$uri \$uri/ =404;
    }

    # API proxy (if needed in future)
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/frontend /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 3. Deploy Flask API

```bash
# Copy Flask app
cp -r AlphaBreak/flask_app/* ~/flask_app/

# Create virtual environment
cd ~/flask_app
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
cat > .env <<EOF
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=False

# Database Configuration
TIMESERIES_DB_HOST=127.0.0.1
TIMESERIES_DB_PORT=5432
TIMESERIES_DB_NAME=trading_data
TIMESERIES_DB_USER=trading
TIMESERIES_DB_PASSWORD=YOUR_SECURE_PASSWORD_HERE

# JWT Configuration
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ACCESS_TOKEN_EXPIRES=900         # 15 minutes
JWT_REFRESH_TOKEN_EXPIRES=604800     # 7 days

# Data Sources
OPTIONS_DATA_SOURCE=yfinance
STOCK_DATA_SOURCE=yfinance
FOREX_DATA_SOURCE=yfinance

# Logging
LOG_LEVEL=INFO
LOG_FILE=/home/ubuntu/logs/flask_app.log
EOF

# Create startup script
cat > start_flask.sh <<'EOF'
#!/bin/bash
cd /home/ubuntu/flask_app
source venv/bin/activate
nohup gunicorn -w 3 -b 127.0.0.1:5000 wsgi:app > /home/ubuntu/gunicorn.log 2>&1 &
echo "Flask API started on port 5000 (PID: $!)"
EOF

chmod +x start_flask.sh

# Start Flask API
./start_flask.sh
```

### 4. Verify Deployment

```bash
# Check Flask API
curl http://127.0.0.1:5000/api/health

# Check frontend (from local machine)
curl http://3.140.78.15:8000

# Check Nginx
sudo systemctl status nginx

# Check processes
ps aux | grep gunicorn
```

---

## Service Configuration

### 1. Airflow Setup

#### Install Airflow

```bash
# Create Airflow directory
mkdir -p ~/airflow
cd ~/airflow

# Create virtual environment
python3 -m venv airflow_venv
source airflow_venv/bin/activate

# Install Airflow with PostgreSQL support
export AIRFLOW_HOME=~/airflow
export AIRFLOW_VERSION=2.8.1
export PYTHON_VERSION=3.10
export CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip install "apache-airflow[postgres]==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
```

#### Configure Airflow

```bash
# Initialize Airflow database
airflow db init

# Create admin user
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin123

# Edit airflow.cfg
nano ~/airflow/airflow.cfg
```

**Key Configuration Changes**:

```ini
[core]
dags_folder = /home/ubuntu/dags
executor = LocalExecutor
load_examples = False
default_timezone = America/New_York

[database]
sql_alchemy_conn = postgresql+psycopg2://trading:PASSWORD@localhost:5432/trading_data

[webserver]
web_server_host = 0.0.0.0
web_server_port = 8080
secret_key = YOUR_SECRET_KEY_HERE
auth_backend = airflow.api.auth.backend.basic_auth

[scheduler]
dag_dir_list_interval = 30
```

#### Create Systemd Services

**Airflow Scheduler**:

```bash
sudo tee /etc/systemd/system/airflow-scheduler.service <<EOF
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
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

**Airflow Webserver**:

```bash
sudo tee /etc/systemd/system/airflow-webserver.service <<EOF
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
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

**Enable and Start Services**:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable airflow-scheduler
sudo systemctl enable airflow-webserver

# Start services
sudo systemctl start airflow-scheduler
sudo systemctl start airflow-webserver

# Check status
sudo systemctl status airflow-scheduler
sudo systemctl status airflow-webserver

# View logs
sudo journalctl -u airflow-scheduler -f
sudo journalctl -u airflow-webserver -f
```

### 2. Deploy Airflow DAGs

```bash
# Copy DAGs from repository
cp ~/repo/AlphaBreak/dags/* ~/dags/

# Verify DAG syntax
cd ~/airflow
source airflow_venv/bin/activate
export AIRFLOW_HOME=~/airflow
airflow dags list

# Unpause portfolio DAG
airflow dags unpause portfolio_update

# Trigger test run (optional)
airflow dags test portfolio_update 2026-02-02
```

---

## Database Management

### 1. PostgreSQL Initial Setup

```bash
# Switch to postgres user
sudo -u postgres psql

-- Create database and user
CREATE DATABASE trading_data;
CREATE USER trading WITH ENCRYPTED PASSWORD 'YOUR_SECURE_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE trading_data TO trading;
\q

# Enable TimescaleDB extension
sudo -u postgres psql -d trading_data -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
```

### 2. Apply Database Schema

```bash
# Copy schema files
cp ~/repo/AlphaBreak/kubernetes/*.sql ~/

# Apply schemas
psql -U trading -d trading_data -h 127.0.0.1 -f ~/schema_v2_intraday.sql
psql -U trading -d trading_data -h 127.0.0.1 -f ~/schema_auth.sql
psql -U trading -d trading_data -h 127.0.0.1 -f ~/schema_forex.sql

# Verify
psql -U trading -d trading_data -h 127.0.0.1 -c "\dt"
```

### 3. Configure PostgreSQL

```bash
# Edit postgresql.conf
sudo nano /etc/postgresql/15/main/postgresql.conf
```

**Key Settings**:

```ini
shared_buffers = 1GB                    # 25% of RAM
effective_cache_size = 3GB              # 75% of RAM
maintenance_work_mem = 256MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1                  # SSD
effective_io_concurrency = 200          # SSD
work_mem = 10MB
min_wal_size = 1GB
max_wal_size = 4GB
max_connections = 100

# TimescaleDB settings
shared_preload_libraries = 'timescaledb'
```

```bash
# Restart PostgreSQL
sudo systemctl restart postgresql
```

### 4. Database Access from Local Machine

**Via SSH Tunnel**:

```bash
# From local machine
ssh -i trading-db-key.pem -L 5432:127.0.0.1:5432 ubuntu@3.140.78.15

# Connect with psql (in another terminal)
psql -h localhost -U trading -d trading_data
```

**Using pgAdmin or DBeaver**:
- Host: localhost (with SSH tunnel active)
- Port: 5432
- Database: trading_data
- User: trading
- Password: [from .env file]

---

## SSL & Security Configuration

### 1. Let's Encrypt SSL (Planned)

**Note**: Currently using HTTP only. SSL setup planned for Q2 2026.

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate (requires domain name)
sudo certbot --nginx -d yourdomain.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

### 2. Nginx SSL Configuration (Future)

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # ... rest of config
}
```

### 3. Security Hardening

```bash
# Disable password authentication for SSH
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
# Set: PermitRootLogin no
sudo systemctl restart sshd

# Configure fail2ban
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Enable automatic security updates
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

---

## Monitoring & Logging

### 1. Application Logs

| Service | Log Location | Command |
|---------|--------------|---------|
| Flask API | `/home/ubuntu/gunicorn.log` | `tail -f ~/gunicorn.log` |
| Airflow Scheduler | systemd journal | `sudo journalctl -u airflow-scheduler -f` |
| Airflow Webserver | systemd journal | `sudo journalctl -u airflow-webserver -f` |
| Nginx Access | `/var/log/nginx/access.log` | `sudo tail -f /var/log/nginx/access.log` |
| Nginx Error | `/var/log/nginx/error.log` | `sudo tail -f /var/log/nginx/error.log` |
| PostgreSQL | `/var/log/postgresql/` | `sudo tail -f /var/log/postgresql/*.log` |

### 2. System Monitoring

```bash
# Install monitoring tools
sudo apt install -y htop iotop nethogs

# Check system resources
htop           # CPU, RAM, processes
df -h          # Disk usage
free -h        # Memory usage
sudo iotop     # Disk I/O
sudo nethogs   # Network usage per process
```

### 3. Database Monitoring

```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

-- Long-running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '5 minutes';

-- Database size
SELECT pg_size_pretty(pg_database_size('trading_data'));

-- Table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
```

### 4. Prometheus + Grafana (Planned)

**Note**: Monitoring stack planned for Q3 2026.

```yaml
# docker-compose.yml (future)
version: '3'
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

---

## Backup & Disaster Recovery

### 1. Database Backups

#### Automated Backup Script

```bash
# Create backup script
cat > ~/backup_db.sh <<'EOF'
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="trading_data_$DATE.dump"

mkdir -p $BACKUP_DIR

# Backup database
pg_dump -U trading -h 127.0.0.1 -d trading_data -F c -f $BACKUP_DIR/$FILENAME

# Compress
gzip $BACKUP_DIR/$FILENAME

# Keep only last 7 days
find $BACKUP_DIR -name "*.dump.gz" -mtime +7 -delete

echo "Backup completed: $FILENAME.gz"
EOF

chmod +x ~/backup_db.sh

# Create cron job (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /home/ubuntu/backup_db.sh") | crontab -
```

#### Manual Backup

```bash
# Full database backup
pg_dump -U trading -h 127.0.0.1 -d trading_data -F c -f backup_$(date +%Y%m%d).dump

# Backup specific tables
pg_dump -U trading -h 127.0.0.1 -d trading_data -t portfolio_holdings -F c -f portfolio_backup.dump

# Copy to local machine
scp -i trading-db-key.pem ubuntu@3.140.78.15:~/backup_*.dump .
```

#### Restore from Backup

```bash
# Restore full database
pg_restore -U trading -h 127.0.0.1 -d trading_data -c backup_20260202.dump

# Restore specific table
pg_restore -U trading -h 127.0.0.1 -d trading_data -t portfolio_holdings portfolio_backup.dump
```

### 2. Code Backups

```bash
# All code is in Git - no manual backups needed
# Ensure all changes are committed and pushed

cd ~/repo/AlphaBreak
git status
git add .
git commit -m "Production changes"
git push origin main
```

### 3. Configuration Backups

```bash
# Backup all configuration files
tar -czf ~/config_backup_$(date +%Y%m%d).tar.gz \
    ~/flask_app/.env \
    ~/airflow/airflow.cfg \
    /etc/nginx/sites-available/frontend \
    /etc/systemd/system/airflow-*.service

# Copy to local machine
scp -i trading-db-key.pem ubuntu@3.140.78.15:~/config_backup_*.tar.gz .
```

### 4. Disaster Recovery Plan

**RTO (Recovery Time Objective)**: 2 hours
**RPO (Recovery Point Objective)**: 24 hours (daily backups)

**Recovery Steps**:

1. **Provision New EC2 Instance** (15 min)
   - Use same AMI and instance type
   - Apply same security group

2. **Restore System Packages** (30 min)
   - Follow [Initial Server Setup](#initial-server-setup)

3. **Restore Database** (30 min)
   - Restore from latest backup
   - Verify data integrity

4. **Restore Application Code** (15 min)
   - Clone from Git
   - Deploy to new instance

5. **Restore Configurations** (15 min)
   - Extract config backup
   - Update IP addresses if changed

6. **Verify Services** (15 min)
   - Test all endpoints
   - Verify Airflow DAGs
   - Check database connectivity

---

## Update Procedures

### 1. Frontend Updates

**Risk Level**: Low (no downtime)

```bash
# From local machine
scp -i docs/security/trading-db-key.pem -r frontend/* ubuntu@3.140.78.15:~/frontend/

# Verify (from local machine)
curl http://3.140.78.15:8000
```

**No service restart required** - Nginx serves static files directly.

### 2. Flask API Updates

**Risk Level**: Medium (5-10 second downtime)

```bash
# From local machine
scp -i docs/security/trading-db-key.pem -r flask_app/* ubuntu@3.140.78.15:~/flask_app/

# Restart API (from EC2)
ssh -i docs/security/trading-db-key.pem ubuntu@3.140.78.15 << 'EOF'
pkill gunicorn
cd /home/ubuntu/flask_app
source venv/bin/activate
./start_flask.sh
EOF

# Verify
curl http://127.0.0.1:5000/api/health
```

### 3. Dependency Updates

**Risk Level**: Medium (test thoroughly)

```bash
# Connect to EC2
ssh -i docs/security/trading-db-key.pem ubuntu@3.140.78.15

# Update Flask dependencies
cd ~/flask_app
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Restart API
pkill gunicorn
./start_flask.sh

# Update Airflow dependencies (if needed)
cd ~/airflow
source airflow_venv/bin/activate
pip install --upgrade [package-name]
sudo systemctl restart airflow-scheduler
```

### 4. Airflow DAG Updates

**Risk Level**: Low (no downtime)

```bash
# From local machine
scp -i docs/security/trading-db-key.pem dags/* ubuntu@3.140.78.15:~/dags/

# DAGs are automatically reloaded (30 second scan interval)
# No restart required
```

### 5. Database Schema Updates

**Risk Level**: High (backup first!)

```bash
# 1. Backup database
ssh -i docs/security/trading-db-key.pem ubuntu@3.140.78.15 "pg_dump -U trading -h 127.0.0.1 -d trading_data -F c -f ~/backup_pre_migration.dump"

# 2. Copy schema changes
scp -i docs/security/trading-db-key.pem migrations/schema_v3.sql ubuntu@3.140.78.15:~/

# 3. Apply changes
ssh -i docs/security/trading-db-key.pem ubuntu@3.140.78.15 "psql -U trading -h 127.0.0.1 -d trading_data -f ~/schema_v3.sql"

# 4. Verify
ssh -i docs/security/trading-db-key.pem ubuntu@3.140.78.15 "psql -U trading -h 127.0.0.1 -d trading_data -c '\dt'"
```

### 6. Full System Update

**Risk Level**: High (schedule downtime)

```bash
# 1. Notify users (post banner on frontend)
# 2. Stop Airflow to prevent job runs
ssh -i docs/security/trading-db-key.pem ubuntu@3.140.78.15 << 'EOF'
sudo systemctl stop airflow-scheduler
sudo systemctl stop airflow-webserver
EOF

# 3. Backup database
ssh -i docs/security/trading-db-key.pem ubuntu@3.140.78.15 "~/backup_db.sh"

# 4. Update system packages
ssh -i docs/security/trading-db-key.pem ubuntu@3.140.78.15 << 'EOF'
sudo apt update && sudo apt upgrade -y
EOF

# 5. Deploy code changes (follow steps 1-4 above)

# 6. Restart services
ssh -i docs/security/trading-db-key.pem ubuntu@3.140.78.15 << 'EOF'
pkill gunicorn
cd /home/ubuntu/flask_app && ./start_flask.sh
sudo systemctl start airflow-scheduler
sudo systemctl start airflow-webserver
EOF

# 7. Verify all services
ssh -i docs/security/trading-db-key.pem ubuntu@3.140.78.15 << 'EOF'
systemctl status airflow-scheduler
systemctl status airflow-webserver
ps aux | grep gunicorn
curl http://127.0.0.1:5000/api/health
EOF
```

---

## Rollback Procedures

### 1. Code Rollback

```bash
# Connect to EC2
ssh -i docs/security/trading-db-key.pem ubuntu@3.140.78.15

# Rollback to previous commit
cd ~/repo/AlphaBreak
git log  # Find commit hash
git checkout <previous-commit-hash>

# Redeploy
cp -r frontend/* ~/frontend/
cp -r flask_app/* ~/flask_app/

# Restart API
pkill gunicorn
cd ~/flask_app && ./start_flask.sh
```

### 2. Database Rollback

```bash
# Connect to EC2
ssh -i docs/security/trading-db-key.pem ubuntu@3.140.78.15

# Stop application to prevent writes
pkill gunicorn
sudo systemctl stop airflow-scheduler

# Restore from backup
pg_restore -U trading -h 127.0.0.1 -d trading_data -c ~/backup_pre_migration.dump

# Restart services
cd ~/flask_app && ./start_flask.sh
sudo systemctl start airflow-scheduler
```

### 3. Full System Rollback

**Last Resort**: Restore from EC2 snapshot

1. Go to EC2 Console → Snapshots
2. Find latest snapshot before deployment
3. Create new volume from snapshot
4. Stop instance, detach old volume, attach new volume
5. Start instance
6. Verify all services

---

## Troubleshooting

### 1. SSH Connection Issues

**Problem**: `ssh: connect to host 3.140.78.15 port 22: Connection timed out`

**Solutions**:
1. Check if ISP blocks port 22 (common for Comcast, Cox, Spectrum)
   - **Workaround**: Use mobile hotspot
2. Verify EC2 security group allows your IP on port 22
3. Check instance is running: AWS Console → EC2 → Instances
4. Use AWS Systems Manager Session Manager (no SSH required):
   ```bash
   aws ssm start-session --target <instance-id>
   ```

### 2. Flask API Not Responding

**Problem**: `curl: (7) Failed to connect to 127.0.0.1 port 5000`

**Solutions**:
```bash
# Check if Gunicorn is running
ps aux | grep gunicorn

# If not running, check logs
tail -50 ~/gunicorn.log

# Common issues:
# - Database connection error (check .env file)
# - Port already in use (kill process: pkill gunicorn)
# - Virtual environment not activated

# Restart API
cd ~/flask_app
source venv/bin/activate
pkill gunicorn
./start_flask.sh
```

### 3. Airflow Services Not Starting

**Problem**: `sudo systemctl status airflow-scheduler` shows "failed"

**Solutions**:
```bash
# Check logs
sudo journalctl -u airflow-scheduler -n 100 --no-pager

# Common issues:
# - Database connection error (check airflow.cfg)
# - Python path issues (check Environment in service file)
# - Port 8080 already in use

# Verify Airflow config
cd ~/airflow
source airflow_venv/bin/activate
export AIRFLOW_HOME=~/airflow
airflow config list

# Restart services
sudo systemctl daemon-reload
sudo systemctl restart airflow-scheduler
sudo systemctl restart airflow-webserver
```

### 4. Database Connection Errors

**Problem**: `FATAL: password authentication failed for user "trading"`

**Solutions**:
```bash
# Verify database is running
sudo systemctl status postgresql

# Check PostgreSQL logs
sudo tail -50 /var/log/postgresql/postgresql-15-main.log

# Test connection
psql -U trading -h 127.0.0.1 -d trading_data

# Reset password if needed
sudo -u postgres psql
ALTER USER trading WITH ENCRYPTED PASSWORD 'new_password';
\q

# Update .env file with new password
nano ~/flask_app/.env
```

### 5. Port 8080 Conflict (Airflow)

**Problem**: `OSError: [Errno 98] Address already in use`

**Solutions**:
```bash
# Find process using port 8080
sudo lsof -i:8080

# Common culprit: kube-rout or another webserver
# Kill process:
sudo kill -9 <PID>

# Or change Airflow webserver port
nano ~/airflow/airflow.cfg
# Change: web_server_port = 8081

sudo systemctl restart airflow-webserver
```

### 6. Frontend Not Loading

**Problem**: Browser shows "Site can't be reached" or 404

**Solutions**:
```bash
# Check Nginx status
sudo systemctl status nginx

# Check Nginx config
sudo nginx -t

# View Nginx logs
sudo tail -50 /var/log/nginx/error.log

# Verify files exist
ls -la ~/frontend/

# Restart Nginx
sudo systemctl restart nginx
```

### 7. High Memory Usage

**Problem**: System running out of RAM (OOM killer)

**Solutions**:
```bash
# Check memory usage
free -h
htop

# Identify memory hogs
ps aux --sort=-%mem | head -10

# Solutions:
# 1. Reduce Gunicorn workers (edit start_flask.sh: -w 2)
# 2. Reduce Airflow webserver workers (edit service file: --workers 2)
# 3. Optimize PostgreSQL (reduce shared_buffers)
# 4. Upgrade to t3.large (8 GB RAM)

# Emergency: Add swap space
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 8. Disk Space Full

**Problem**: `No space left on device`

**Solutions**:
```bash
# Check disk usage
df -h
du -h ~ | sort -hr | head -20

# Clean up:
# 1. Old logs
sudo find /var/log -type f -name "*.log" -mtime +30 -delete

# 2. Airflow logs
find ~/airflow/logs -type f -mtime +30 -delete

# 3. Old database backups
find ~/backups -name "*.dump.gz" -mtime +30 -delete

# 4. Package cache
sudo apt clean
sudo apt autoremove

# 5. Docker (if installed)
docker system prune -a

# If still full, increase EBS volume size in AWS Console
```

---

## Related Documentation

- **[SETUP_GUIDE.md](setup/SETUP_GUIDE.md)** - Local development, K8s, Docker setup
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and design decisions
- **[DATA_ARCHITECTURE.md](DATA_ARCHITECTURE.md)** - Database schema and query patterns
- **[CHANGELOG.md](../CHANGELOG.md)** - Version history and changes
- **[ROADMAP.md](ROADMAP.md)** - Future features and improvements

---

**Last Updated**: February 2, 2026
**Maintained By**: DevOps Team
**Review Cycle**: After each production deployment
**Emergency Contact**: [Your contact information]
