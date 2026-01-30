# Kubernetes Migration Plan

Migration guide for containerizing the Securities Prediction Model with Docker/Kubernetes and adding Airflow for scheduled jobs.

**Created:** January 30, 2026

---

## Current Architecture

```
EC2 Instance (3.140.78.15)
├── nginx (port 80/443) ─── serves frontend, proxies /api
├── gunicorn/Flask (port 5000) ─── REST API
├── PostgreSQL/TimescaleDB (port 5432) ─── database
├── k0s (port 6443) ─── Kubernetes (currently unused)
└── Python scripts (src/) ─── run manually for data fetching
```

**Current state:**
- All services run directly on EC2 host (not containerized)
- Data fetching scripts run manually or via cron
- k0s Kubernetes cluster exists but is unused
- No orchestration for scheduled jobs

---

## Target Architecture

```
EC2 Instance
├── nginx (host) ─── reverse proxy to K8s ingress
└── k0s Kubernetes Cluster
    ├── Namespace: alphabreak
    │   ├── Deployment: flask-api (2 replicas)
    │   ├── Deployment: frontend (nginx container)
    │   ├── StatefulSet: timescaledb (1 replica, persistent volume)
    │   ├── Deployment: airflow-webserver
    │   ├── Deployment: airflow-scheduler
    │   ├── Deployment: airflow-worker
    │   └── ConfigMaps, Secrets, Services, Ingress
    └── Namespace: airflow-system (optional)
```

---

## Phase 1: Dockerfiles

### 1.1 Flask API Dockerfile

```dockerfile
# flask_app/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application code
COPY app/ ./app/
COPY wsgi.py .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "wsgi:app"]
```

### 1.2 Frontend Dockerfile

```dockerfile
# frontend/Dockerfile
FROM nginx:alpine

# Copy frontend files
COPY . /usr/share/nginx/html/

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**frontend/nginx.conf:**
```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
```

### 1.3 Data Scripts Dockerfile

```dockerfile
# src/Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Default command (overridden by Airflow)
CMD ["python", "--version"]
```

### 1.4 Airflow Dockerfile

```dockerfile
# airflow/Dockerfile
FROM apache/airflow:2.8.1-python3.11

USER root
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Install additional Python packages needed by DAGs
COPY requirements-airflow.txt .
RUN pip install --no-cache-dir -r requirements-airflow.txt

# Copy DAGs
COPY dags/ /opt/airflow/dags/
```

---

## Phase 2: Kubernetes Manifests

### 2.1 Namespace and Secrets

```yaml
# kubernetes/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: alphabreak
---
# kubernetes/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
  namespace: alphabreak
type: Opaque
stringData:
  TIMESERIES_DB_HOST: "timescaledb-service"
  TIMESERIES_DB_PORT: "5432"
  TIMESERIES_DB_NAME: "trading_data"
  TIMESERIES_DB_USER: "trading"
  TIMESERIES_DB_PASSWORD: "trading_password"
  POLYGON_API_KEY: "<your-polygon-key>"
```

### 2.2 TimescaleDB StatefulSet

```yaml
# kubernetes/timescaledb.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: timescaledb-pvc
  namespace: alphabreak
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi
  storageClassName: local-path
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: timescaledb
  namespace: alphabreak
spec:
  serviceName: timescaledb
  replicas: 1
  selector:
    matchLabels:
      app: timescaledb
  template:
    metadata:
      labels:
        app: timescaledb
    spec:
      containers:
        - name: timescaledb
          image: timescale/timescaledb:latest-pg15
          ports:
            - containerPort: 5432
          env:
            - name: POSTGRES_DB
              value: "trading_data"
            - name: POSTGRES_USER
              value: "trading"
            - name: POSTGRES_PASSWORD
              value: "trading_password"
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
          resources:
            requests:
              memory: "1Gi"
              cpu: "500m"
            limits:
              memory: "2Gi"
              cpu: "1000m"
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: timescaledb-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: timescaledb-service
  namespace: alphabreak
spec:
  selector:
    app: timescaledb
  ports:
    - port: 5432
      targetPort: 5432
  clusterIP: None
```

### 2.3 Flask API Deployment

```yaml
# kubernetes/flask-api.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flask-api
  namespace: alphabreak
spec:
  replicas: 2
  selector:
    matchLabels:
      app: flask-api
  template:
    metadata:
      labels:
        app: flask-api
    spec:
      containers:
        - name: flask-api
          image: alphabreak/flask-api:latest
          ports:
            - containerPort: 5000
          envFrom:
            - secretRef:
                name: db-credentials
          env:
            - name: FLASK_ENV
              value: "production"
            - name: REDIS_URL
              value: "memory://"
            - name: RATELIMIT_STORAGE_URL
              value: "memory://"
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          readinessProbe:
            httpGet:
              path: /api/health
              port: 5000
            initialDelaySeconds: 10
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /api/health
              port: 5000
            initialDelaySeconds: 30
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: flask-api-service
  namespace: alphabreak
spec:
  selector:
    app: flask-api
  ports:
    - port: 5000
      targetPort: 5000
```

### 2.4 Frontend Deployment

```yaml
# kubernetes/frontend.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: alphabreak
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
        - name: frontend
          image: alphabreak/frontend:latest
          ports:
            - containerPort: 80
          resources:
            requests:
              memory: "64Mi"
              cpu: "50m"
            limits:
              memory: "128Mi"
              cpu: "100m"
---
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: alphabreak
spec:
  selector:
    app: frontend
  ports:
    - port: 80
      targetPort: 80
```

### 2.5 Ingress

```yaml
# kubernetes/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: alphabreak-ingress
  namespace: alphabreak
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
spec:
  ingressClassName: nginx
  rules:
    - host: alphabreak.vip
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: flask-api-service
                port:
                  number: 5000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend-service
                port:
                  number: 80
```

---

## Phase 3: Airflow Setup

### 3.1 Airflow Values (Helm)

```yaml
# airflow/values.yaml
executor: KubernetesExecutor

webserver:
  replicas: 1
  resources:
    requests:
      memory: "512Mi"
      cpu: "250m"

scheduler:
  replicas: 1
  resources:
    requests:
      memory: "512Mi"
      cpu: "250m"

postgresql:
  enabled: true
  persistence:
    size: 5Gi

redis:
  enabled: false  # Not needed for KubernetesExecutor

dags:
  persistence:
    enabled: true
    size: 1Gi

env:
  - name: AIRFLOW__CORE__LOAD_EXAMPLES
    value: "False"
```

### 3.2 Sample DAG - Daily Data Fetch

```python
# airflow/dags/daily_data_fetch.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

default_args = {
    'owner': 'alphabreak',
    'depends_on_past': False,
    'email_on_failure': True,
    'email': ['nick@alphabreak.vip'],
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'daily_data_pipeline',
    default_args=default_args,
    description='Daily data fetching and analysis',
    schedule_interval='0 6 * * 1-5',  # 6 AM EST, weekdays
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['data', 'daily'],
) as dag:

    fetch_stock_data = KubernetesPodOperator(
        task_id='fetch_stock_data',
        name='fetch-stock-data',
        namespace='alphabreak',
        image='alphabreak/data-scripts:latest',
        cmds=['python', 'polygon_data_fetcher.py'],
        env_from=[{'secretRef': {'name': 'db-credentials'}}],
        is_delete_operator_pod=True,
        get_logs=True,
    )

    fetch_forex_data = KubernetesPodOperator(
        task_id='fetch_forex_data',
        name='fetch-forex-data',
        namespace='alphabreak',
        image='alphabreak/data-scripts:latest',
        cmds=['python', 'forex_data_fetcher.py'],
        env_from=[{'secretRef': {'name': 'db-credentials'}}],
        is_delete_operator_pod=True,
        get_logs=True,
    )

    run_correlation_model = KubernetesPodOperator(
        task_id='run_correlation_model',
        name='run-correlation-model',
        namespace='alphabreak',
        image='alphabreak/data-scripts:latest',
        cmds=['python', 'forex_correlation_model.py'],
        env_from=[{'secretRef': {'name': 'db-credentials'}}],
        is_delete_operator_pod=True,
        get_logs=True,
    )

    detect_trend_breaks = KubernetesPodOperator(
        task_id='detect_trend_breaks',
        name='detect-trend-breaks',
        namespace='alphabreak',
        image='alphabreak/data-scripts:latest',
        cmds=['python', 'detect_trend_breaks.py'],
        env_from=[{'secretRef': {'name': 'db-credentials'}}],
        is_delete_operator_pod=True,
        get_logs=True,
    )

    # Task dependencies
    [fetch_stock_data, fetch_forex_data] >> run_correlation_model >> detect_trend_breaks
```

### 3.3 Weekly 13F Fetch DAG

```python
# airflow/dags/weekly_13f_fetch.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

default_args = {
    'owner': 'alphabreak',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=10),
}

with DAG(
    'weekly_13f_pipeline',
    default_args=default_args,
    description='Weekly 13F filing fetch',
    schedule_interval='0 8 * * 6',  # Saturday 8 AM
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['13f', 'weekly'],
) as dag:

    fetch_13f = KubernetesPodOperator(
        task_id='fetch_13f_filings',
        name='fetch-13f-filings',
        namespace='alphabreak',
        image='alphabreak/data-scripts:latest',
        cmds=['python', 'sec_13f_fetcher.py'],
        env_from=[{'secretRef': {'name': 'db-credentials'}}],
        is_delete_operator_pod=True,
        get_logs=True,
    )
```

---

## Phase 4: Migration Steps

### Step 1: Build and Push Docker Images

```bash
# On EC2 or local machine with Docker

# Build Flask API
cd flask_app
docker build -t alphabreak/flask-api:v1 .
docker tag alphabreak/flask-api:v1 alphabreak/flask-api:latest

# Build Frontend
cd ../frontend
docker build -t alphabreak/frontend:v1 .
docker tag alphabreak/frontend:v1 alphabreak/frontend:latest

# Build Data Scripts
cd ../src
docker build -t alphabreak/data-scripts:v1 .
docker tag alphabreak/data-scripts:v1 alphabreak/data-scripts:latest

# Push to registry (or use local k0s import)
# For k0s local:
k0s ctr images import flask-api.tar
```

### Step 2: Database Migration

```bash
# 1. Create database backup
pg_dump -h localhost -U trading trading_data > backup.sql

# 2. Deploy TimescaleDB to K8s
kubectl apply -f kubernetes/timescaledb.yaml

# 3. Wait for pod to be ready
kubectl wait --for=condition=ready pod -l app=timescaledb -n alphabreak --timeout=120s

# 4. Restore database
kubectl exec -i timescaledb-0 -n alphabreak -- psql -U trading trading_data < backup.sql
```

### Step 3: Deploy Application

```bash
# Apply all manifests
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/secrets.yaml
kubectl apply -f kubernetes/timescaledb.yaml
kubectl apply -f kubernetes/flask-api.yaml
kubectl apply -f kubernetes/frontend.yaml
kubectl apply -f kubernetes/ingress.yaml

# Verify deployments
kubectl get pods -n alphabreak
kubectl get svc -n alphabreak
```

### Step 4: Install Airflow

```bash
# Add Airflow Helm repo
helm repo add apache-airflow https://airflow.apache.org
helm repo update

# Install Airflow
helm install airflow apache-airflow/airflow \
  -n alphabreak \
  -f airflow/values.yaml \
  --set webserver.defaultUser.password=<password>

# Copy DAGs
kubectl cp airflow/dags/ alphabreak/airflow-scheduler-0:/opt/airflow/dags/
```

### Step 5: Update nginx on Host

```nginx
# /etc/nginx/sites-available/alphabreak.vip
upstream k8s_ingress {
    server 127.0.0.1:30080;  # NodePort for ingress
}

server {
    listen 443 ssl;
    server_name alphabreak.vip www.alphabreak.vip;

    ssl_certificate /etc/letsencrypt/live/alphabreak.vip/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/alphabreak.vip/privkey.pem;

    location / {
        proxy_pass http://k8s_ingress;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Step 6: Cutover

```bash
# 1. Stop old services
sudo systemctl stop gunicorn  # or pkill gunicorn
sudo pkill -f "python.*http.server"

# 2. Verify K8s services are healthy
kubectl get pods -n alphabreak
curl http://localhost:30080/api/health

# 3. Reload nginx
sudo nginx -t && sudo systemctl reload nginx

# 4. Test production
curl https://alphabreak.vip/api/health
```

---

## Timeline Estimate

| Phase | Task | Duration |
|-------|------|----------|
| **Prep** | Write Dockerfiles, test locally | 4-6 hours |
| **Prep** | Write K8s manifests | 2-3 hours |
| **Prep** | Write Airflow DAGs | 2-3 hours |
| **Prep** | Test in staging (optional) | 4-8 hours |
| **Migration** | Build Docker images | 30 min |
| **Migration** | Deploy TimescaleDB + restore data | 1-2 hours |
| **Migration** | Deploy Flask API + Frontend | 30 min |
| **Migration** | Install Airflow | 1 hour |
| **Migration** | Update nginx, cutover | 30 min |
| **Validation** | Test all endpoints | 1 hour |
| **Buffer** | Troubleshooting | 2-4 hours |

**Total estimated time: 18-30 hours of work**

This can be spread across:
- **Prep work (no downtime):** 1-2 days
- **Migration day:** 4-6 hours

---

## Downtime Estimate

### Option A: Big Bang Migration
- **Downtime: 2-4 hours**
- Stop old services, deploy new, cutover
- Higher risk, but simpler

### Option B: Blue-Green Migration (Recommended)
- **Downtime: 5-15 minutes**
- Run old and new in parallel
- Switch nginx upstream when K8s is ready
- Rollback easy if issues

### Option C: Zero Downtime (Advanced)
- **Downtime: 0 minutes**
- Requires:
  - Database replication or shared storage
  - Health checks and gradual traffic shift
  - More complex setup

**Recommended approach: Option B (Blue-Green)**

```bash
# During migration, nginx can load-balance:
upstream backend {
    server 127.0.0.1:5000 weight=1;     # Old gunicorn
    server 127.0.0.1:30080 weight=0;    # New K8s (disabled)
}

# When ready, flip weights:
upstream backend {
    server 127.0.0.1:5000 weight=0;     # Old (disabled)
    server 127.0.0.1:30080 weight=1;    # New K8s (active)
}
```

---

## Rollback Plan

If migration fails:

```bash
# 1. Revert nginx to old config
sudo cp /etc/nginx/sites-available/alphabreak.vip.backup /etc/nginx/sites-available/alphabreak.vip
sudo nginx -t && sudo systemctl reload nginx

# 2. Restart old services
cd /home/ubuntu/flask_app && ./start_gunicorn.sh &
cd /home/ubuntu/frontend && python3 -m http.server 8000 &

# 3. Scale down K8s (optional)
kubectl scale deployment --all --replicas=0 -n alphabreak
```

---

## Post-Migration Benefits

1. **Scalability**: Easily scale API replicas with `kubectl scale`
2. **Automated Jobs**: Airflow handles all data fetching on schedule
3. **Self-healing**: K8s restarts failed containers automatically
4. **Rolling Updates**: Zero-downtime deployments for code changes
5. **Resource Limits**: Prevent any service from consuming all memory/CPU
6. **Monitoring Ready**: Easy to add Prometheus/Grafana

---

## Prerequisites Checklist

- [ ] Docker installed on EC2 (or build machine)
- [ ] k0s cluster healthy (`kubectl get nodes`)
- [ ] Helm installed (`helm version`)
- [ ] nginx ingress controller in K8s
- [ ] Persistent storage class configured
- [ ] Database backup taken
- [ ] DNS propagated (alphabreak.vip)

---

## Questions to Decide Before Starting

1. **Image Registry**: Use Docker Hub, ECR, or k0s local import?
2. **Database**: Migrate to K8s or keep PostgreSQL on host?
3. **Airflow**: Full Helm install or minimal custom deployment?
4. **Monitoring**: Add Prometheus/Grafana now or later?
5. **CI/CD**: Set up GitHub Actions for automated builds?
