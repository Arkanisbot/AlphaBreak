#!/bin/bash
# ============================================================================
# AlphaBreak Backend Deploy (EC2)
# ============================================================================
# Rebuilds BOTH trading-api and airflow-trading images on every deploy and
# imports both into k0s containerd. This prevents the failure mode where a
# `docker system prune -af` after importing one image silently GCs the other
# from k0s (Apr 15 2026 incident — Airflow lost its image for ~4 days).
#
# Run from the repo root on the EC2 box:
#   cd ~/AlphaBreak && bash scripts/deploy-backend.sh
#
# Or from a dev machine:
#   ssh -i "$PEM" ubuntu@3.140.78.15 'cd ~/AlphaBreak && bash scripts/deploy-backend.sh'
#
# Flags:
#   --no-pull       skip `git pull` (use current working tree)
#   --api-only      rebuild + restart trading-api only
#   --airflow-only  rebuild + restart airflow pods only
# ============================================================================

set -euo pipefail

NO_PULL=false
API_ONLY=false
AIRFLOW_ONLY=false
for arg in "$@"; do
    case "$arg" in
        --no-pull) NO_PULL=true ;;
        --api-only) API_ONLY=true ;;
        --airflow-only) AIRFLOW_ONLY=true ;;
        *) echo "Unknown flag: $arg" >&2; exit 1 ;;
    esac
done

NAMESPACE="trading-system"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

say() { echo -e "\n\033[1;36m==> $*\033[0m"; }

if [ "$NO_PULL" = false ]; then
    say "Pulling latest from origin/main"
    git pull --ff-only
fi

BUILD_API=true
BUILD_AIRFLOW=true
if [ "$API_ONLY" = true ]; then BUILD_AIRFLOW=false; fi
if [ "$AIRFLOW_ONLY" = true ]; then BUILD_API=false; fi

if [ "$BUILD_API" = true ]; then
    say "Building trading-api:latest"
    sudo docker build -f flask_app/Dockerfile -t trading-api:latest .
fi

if [ "$BUILD_AIRFLOW" = true ]; then
    say "Building airflow-trading:latest"
    sudo docker build -f Dockerfile.airflow -t airflow-trading:latest .
fi

# Import BOTH images into k0s containerd in a single tarball so partial
# failure can't leave only one image landed.
say "Importing images into k0s containerd"
TAR="/tmp/k8s-images-$$.tar"
trap 'sudo rm -f "$TAR"' EXIT

IMAGES=()
[ "$BUILD_API" = true ] && IMAGES+=("trading-api:latest")
[ "$BUILD_AIRFLOW" = true ] && IMAGES+=("airflow-trading:latest")

sudo docker save "${IMAGES[@]}" -o "$TAR"
sudo k0s ctr images import "$TAR"

# Safe prune: only dangling Docker layers, NEVER -a. k0s has its own copy in
# containerd; Docker's image cache is just a staging area at this point.
say "Pruning dangling Docker layers (safe)"
sudo docker image prune -f >/dev/null

say "Verifying images in k0s containerd"
sudo k0s ctr images ls | grep -E "trading-api:latest|airflow-trading:latest" || {
    echo "ERROR: expected images not found in k0s containerd" >&2
    exit 1
}

# Restart the relevant pods. `kubectl delete` lets the Deployment recreate
# them with the freshly-imported image.
if [ "$BUILD_API" = true ]; then
    say "Restarting trading-api pods"
    sudo k0s kubectl delete pods -n "$NAMESPACE" -l app=trading-api --force --grace-period=0 || true
fi

if [ "$BUILD_AIRFLOW" = true ]; then
    say "Restarting airflow-scheduler and airflow-webserver pods"
    sudo k0s kubectl delete pods -n "$NAMESPACE" -l "app=airflow,component=scheduler" --force --grace-period=0 || true
    sudo k0s kubectl delete pods -n "$NAMESPACE" -l "app=airflow,component=webserver" --force --grace-period=0 || true
fi

say "Deploy complete. Pod status:"
sudo k0s kubectl get pods -n "$NAMESPACE" -o wide | grep -E "NAME|trading-api|airflow" || true

cat <<EOF

Next checks (give pods ~2 min to warm up):
  curl -sS https://alphabreak.vip/api/health
  sudo k0s kubectl logs -n $NAMESPACE -l app=trading-api --tail=30
  sudo k0s kubectl logs -n $NAMESPACE -l "app=airflow,component=scheduler" --tail=30
EOF
