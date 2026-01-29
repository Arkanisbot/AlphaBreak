# Installing Kubernetes on EC2

This guide covers installing a lightweight Kubernetes distribution on an AWS EC2 instance. We'll use **k0s** (recommended) or **k3s** — both are production-ready and run well on small instances.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Option A: k0s (Recommended)](#option-a-k0s-recommended)
3. [Option B: k3s](#option-b-k3s)
4. [Post-Installation](#post-installation)
5. [Deploy Your Application](#deploy-your-application)
6. [Remote Access with kubectl](#remote-access-with-kubectl)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### EC2 Instance Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 1 vCPU | 2+ vCPUs |
| RAM | 2 GB | 4+ GB |
| Disk | 20 GB | 50+ GB |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### Security Group Rules

Ensure your EC2 security group allows:

| Port | Protocol | Source | Purpose |
|------|----------|--------|---------|
| 22 | TCP | Your IP | SSH |
| 6443 | TCP | Your IP | Kubernetes API |
| 80 | TCP | 0.0.0.0/0 | HTTP (optional) |
| 443 | TCP | 0.0.0.0/0 | HTTPS (optional) |
| 30000-32767 | TCP | Your IP | NodePort services |

Add rules via AWS Console or CLI:
```bash
# Add Kubernetes API port
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxx \
    --protocol tcp \
    --port 6443 \
    --cidr YOUR_IP/32
```

### SSH into Your Instance

```bash
ssh -i ~/.ssh/trading-db-key.pem ubuntu@YOUR_EC2_IP
```

---

## Option A: k0s (Recommended)

k0s is a zero-friction Kubernetes distribution. Single binary, no dependencies, perfect for single-node clusters.

### Step 1: Install k0s

```bash
# Download and install k0s
curl -sSLf https://get.k0s.sh | sudo sh

# Verify installation
k0s version
```

### Step 2: Create Configuration (Optional)

```bash
# Generate default config
sudo k0s config create > k0s.yaml

# Edit if needed (e.g., to change cluster name)
nano k0s.yaml
```

### Step 3: Install as Controller + Worker (Single Node)

```bash
# Install k0s as a systemd service (controller + worker)
sudo k0s install controller --single

# Start k0s
sudo k0s start

# Check status
sudo k0s status
```

### Step 4: Wait for Cluster to be Ready

```bash
# Watch until all components are running (takes 1-2 minutes)
sudo k0s kubectl get nodes

# Expected output:
# NAME              STATUS   ROLES           AGE   VERSION
# ip-172-31-x-x     Ready    control-plane   1m    v1.29.x+k0s
```

### Step 5: Configure kubectl

```bash
# Create kubeconfig for your user
sudo k0s kubeconfig admin > ~/.kube/config
chmod 600 ~/.kube/config

# Test
kubectl get nodes
kubectl get pods -A
```

### k0s Commands Reference

```bash
sudo k0s start          # Start the cluster
sudo k0s stop           # Stop the cluster
sudo k0s status         # Check status
sudo k0s reset          # Completely reset (removes all data)
sudo k0s kubectl ...    # Run kubectl commands
```

---

## Option B: k3s

k3s is another lightweight Kubernetes distribution by Rancher. Slightly more features than k0s, but uses more resources.

### Step 1: Install k3s

```bash
# Install k3s (single node, with kubectl)
curl -sfL https://get.k3s.io | sh -

# Wait for node to be ready
sudo k3s kubectl get nodes
```

### Step 2: Configure kubectl

```bash
# Copy kubeconfig to user directory
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config
chmod 600 ~/.kube/config

# Update server address if accessing remotely
sed -i 's/127.0.0.1/YOUR_EC2_PUBLIC_IP/' ~/.kube/config

# Test
kubectl get nodes
```

### Step 3: Verify Installation

```bash
# Check all pods are running
kubectl get pods -A

# Expected: coredns, traefik, metrics-server, etc.
```

### k3s Commands Reference

```bash
sudo systemctl start k3s      # Start
sudo systemctl stop k3s       # Stop
sudo systemctl status k3s     # Status
sudo /usr/local/bin/k3s-uninstall.sh  # Uninstall
```

---

## Post-Installation

### Install Helm (Package Manager)

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Verify
helm version
```

### Create a Namespace for Your App

```bash
kubectl create namespace trading-system
kubectl config set-context --current --namespace=trading-system
```

### Install NGINX Ingress Controller (Optional)

For k0s:
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.5/deploy/static/provider/cloud/deploy.yaml
```

For k3s (Traefik is pre-installed, or replace with NGINX):
```bash
# Disable Traefik if you prefer NGINX
sudo systemctl stop k3s
sudo k3s server --disable traefik &
```

---

## Deploy Your Application

### Option 1: Apply Kubernetes Manifests

From your local machine, copy the manifests:

```bash
# From local machine
scp -i ~/.ssh/trading-db-key.pem -r kubernetes/ ubuntu@YOUR_EC2_IP:~/
```

On EC2:
```bash
cd ~/kubernetes

# Apply in order
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f redis-deployment.yaml
kubectl apply -f api-deployment.yaml
kubectl apply -f api-service.yaml
```

### Option 2: Deploy with Docker Image

First, build and push your image to a registry:

```bash
# On local machine - build and push to Docker Hub
cd flask_app
docker build -t yourusername/trading-api:latest .
docker push yourusername/trading-api:latest
```

Then update `kubernetes/api-deployment.yaml`:
```yaml
spec:
  containers:
  - name: trading-api
    image: yourusername/trading-api:latest  # Update this
```

### Option 3: Use Local Image (No Registry)

For k3s, you can import local images:
```bash
# Build image on EC2
docker build -t trading-api:latest ./flask_app

# Import to k3s
sudo k3s ctr images import trading-api.tar
```

---

## Remote Access with kubectl

### Step 1: Get the Kubeconfig from EC2

On EC2:
```bash
# For k0s
sudo k0s kubeconfig admin > ~/kubeconfig.yaml

# For k3s
sudo cat /etc/rancher/k3s/k3s.yaml > ~/kubeconfig.yaml
```

### Step 2: Download to Local Machine

```bash
scp -i ~/.ssh/trading-db-key.pem ubuntu@YOUR_EC2_IP:~/kubeconfig.yaml ~/.kube/ec2-config
```

### Step 3: Update Server Address

Edit `~/.kube/ec2-config` and change:
```yaml
server: https://127.0.0.1:6443
```
To:
```yaml
server: https://YOUR_EC2_PUBLIC_IP:6443
```

### Step 4: Use the Config

```bash
# Option A: Set as default
export KUBECONFIG=~/.kube/ec2-config

# Option B: Use per-command
kubectl --kubeconfig ~/.kube/ec2-config get nodes

# Option C: Merge configs
KUBECONFIG=~/.kube/config:~/.kube/ec2-config kubectl config view --flatten > ~/.kube/merged
mv ~/.kube/merged ~/.kube/config
```

### Step 5: Test Connection

```bash
kubectl get nodes
kubectl get pods -A
```

---

## Monitoring & Maintenance

### View Logs

```bash
# k0s logs
sudo journalctl -u k0scontroller -f

# k3s logs
sudo journalctl -u k3s -f

# Pod logs
kubectl logs -f deployment/trading-api -n trading-system
```

### Check Resource Usage

```bash
# Node resources
kubectl top nodes

# Pod resources
kubectl top pods -n trading-system
```

### Update k0s

```bash
sudo k0s stop
curl -sSLf https://get.k0s.sh | sudo sh
sudo k0s start
```

### Backup etcd (k0s)

```bash
sudo k0s backup --save-path /tmp/k0s-backup.tar.gz
```

---

## Troubleshooting

### Cluster Won't Start

```bash
# Check system resources
free -h
df -h

# Check logs
sudo journalctl -u k0scontroller --no-pager -n 100
# or
sudo journalctl -u k3s --no-pager -n 100
```

### Pods Stuck in Pending

```bash
# Check events
kubectl describe pod POD_NAME -n trading-system

# Common causes:
# - Insufficient resources → add resource limits to deployment
# - Image pull failed → check image name and registry access
```

### Can't Connect Remotely

1. Check security group allows port 6443
2. Check kubeconfig has correct public IP
3. Test connectivity:
   ```bash
   nc -zv YOUR_EC2_IP 6443
   ```

### Reset Everything

```bash
# k0s
sudo k0s stop
sudo k0s reset
sudo rm -rf /var/lib/k0s

# k3s
sudo /usr/local/bin/k3s-uninstall.sh
```

### Memory Issues

For instances with <4GB RAM, add swap:
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## Quick Reference

### k0s Single-Node Setup (Copy-Paste)

```bash
# Run these commands in sequence
curl -sSLf https://get.k0s.sh | sudo sh
sudo k0s install controller --single
sudo k0s start
sleep 60  # Wait for startup
sudo k0s kubeconfig admin > ~/.kube/config
chmod 600 ~/.kube/config
kubectl get nodes
```

### k3s Single-Node Setup (Copy-Paste)

```bash
# Run these commands in sequence
curl -sfL https://get.k3s.io | sh -
sleep 30  # Wait for startup
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config
kubectl get nodes
```

---

## Resource Comparison

| Feature | k0s | k3s |
|---------|-----|-----|
| Memory (idle) | ~300 MB | ~500 MB |
| Binary size | ~170 MB | ~60 MB |
| Built-in ingress | No | Traefik |
| Built-in load balancer | No | ServiceLB |
| CNI | Kube-router | Flannel |
| Container runtime | containerd | containerd |
| Best for | Minimal footprint | Batteries included |

---

## Next Steps

1. **Deploy your app**: Apply the manifests from `kubernetes/`
2. **Set up CI/CD**: Use GitHub Actions to auto-deploy on push
3. **Add monitoring**: Install Prometheus + Grafana with Helm
4. **Set up backups**: Schedule etcd backups with cron
5. **Add TLS**: Use cert-manager for automatic Let's Encrypt certificates

---

## Related Documentation

- [k0s Documentation](https://docs.k0sproject.io/)
- [k3s Documentation](https://docs.k3s.io/)
- [Project Setup Guide](./SETUP_GUIDE.md)
- [Kubernetes Deployment Guide](../kubernetes/KUBERNETES_DEPLOYMENT_GUIDE.txt)
