# Other AlphaBreak Guides

This directory contains supplementary guides that provide **detailed implementation instructions** for specific deployment scenarios and advanced features. These guides contain information **not fully covered** in the main documentation (ARCHITECTURE.md, DEPLOYMENT.md, SETUP_GUIDE.md).

---

## 📚 Guides in This Directory

### Kubernetes & Container Deployment

1. **[EC2_KUBERNETES_GUIDE.md](EC2_KUBERNETES_GUIDE.md)**
   - Installing k0s or k3s on EC2
   - Lightweight Kubernetes for single-node clusters
   - Step-by-step setup with code examples
   - **Use Case**: Setting up Kubernetes on existing EC2 instance

2. **[KUBERNETES_MIGRATION_PLAN.md](KUBERNETES_MIGRATION_PLAN.md)**
   - Complete K8s migration roadmap
   - Dockerfiles for all services (Flask API, Frontend, PostgreSQL)
   - Kubernetes manifests (Deployments, Services, Ingress)
   - Airflow on Kubernetes setup
   - **Use Case**: Full containerization and K8s migration (Q3 2026 roadmap)

3. **[K8S_POSTGRESQL_MIGRATION_GUIDE.md](K8S_POSTGRESQL_MIGRATION_GUIDE.md)**
   - Migrating native PostgreSQL to K8s StatefulSet
   - Backup and restore procedures
   - Persistent volume configuration
   - **Use Case**: Moving database into Kubernetes cluster

4. **[LOCAL_KUBERNETES_SETUP_WINDOWS.md](LOCAL_KUBERNETES_SETUP_WINDOWS.md)**
   - Docker Desktop + Kubernetes on Windows 10/11
   - No VM required (uses WSL2)
   - Step-by-step with screenshots
   - **Use Case**: Windows developers running full stack locally

### Local Development & Testing

5. **[VM_DEPLOYMENT_GUIDE.md](VM_DEPLOYMENT_GUIDE.md)**
   - VirtualBox/VMware setup for local testing
   - Ubuntu 22.04 VM with K8s (minikube)
   - Full stack deployment in VM
   - **Use Case**: Isolated testing environment on any host OS

### Implementation Guides

6. **[FLASK_API_IMPLEMENTATION_GUIDE.txt](FLASK_API_IMPLEMENTATION_GUIDE.txt)**
   - Detailed Flask API architecture
   - Code examples for robust API design
   - Authentication, caching, error handling
   - Model loading and serving
   - **Use Case**: Reference for improving/extending Flask API

7. **[MODEL_TRAINING_GUIDE.md](MODEL_TRAINING_GUIDE.md)**
   - Training XGBoost and Keras models
   - Feature engineering pipeline
   - Backtesting procedures
   - Model evaluation and validation
   - **Use Case**: Retraining ML models or adding new models

8. **[SYSTEM_INTEGRATION_GUIDE.txt](SYSTEM_INTEGRATION_GUIDE.txt)**
   - How all modules work together
   - Meta-learning → Trend prediction → Options analysis flow
   - Module descriptions and use cases
   - **Use Case**: Understanding system architecture at code level

---

## 📂 When to Use These Guides

### Use Main Documentation For:
- **Getting started**: [SETUP_GUIDE.md](../setup/SETUP_GUIDE.md)
- **Understanding architecture**: [ARCHITECTURE.md](../ARCHITECTURE.md)
- **Production deployment**: [DEPLOYMENT.md](../DEPLOYMENT.md)
- **API reference**: [API_DOCUMENTATION.md](../api/API_DOCUMENTATION.md)

### Use These Guides For:
- **Kubernetes migration** (Q3 2026 roadmap item)
- **Windows local development** with Docker Desktop
- **VM-based testing** environment
- **Detailed Flask API implementation** examples
- **ML model training** procedures
- **PostgreSQL containerization**

---

## 🗂️ Guide Categories

| Category | Guides | Purpose |
|----------|--------|---------|
| **K8s Deployment** | EC2_KUBERNETES_GUIDE, KUBERNETES_MIGRATION_PLAN, K8S_POSTGRESQL_MIGRATION_GUIDE | Containerization and K8s setup |
| **Local Development** | LOCAL_KUBERNETES_SETUP_WINDOWS, VM_DEPLOYMENT_GUIDE | Developer workstations |
| **Implementation** | FLASK_API_IMPLEMENTATION_GUIDE, SYSTEM_INTEGRATION_GUIDE | Code-level details |
| **ML Training** | MODEL_TRAINING_GUIDE | Model development |

---

## 🔗 Related Documentation

- **Main Setup Guide**: [docs/setup/SETUP_GUIDE.md](../setup/SETUP_GUIDE.md)
- **Architecture Overview**: [docs/ARCHITECTURE.md](../ARCHITECTURE.md)
- **Deployment Guide**: [docs/DEPLOYMENT.md](../DEPLOYMENT.md)
- **Roadmap** (K8s migration timeline): [docs/ROADMAP.md](../ROADMAP.md)

---

## 📝 Notes

- These guides were created during early development phases
- Some may reference older architecture (pre-v2.0)
- Verify current system state before following older guides
- When in doubt, consult main documentation first

---

**Last Updated**: February 2, 2026
**Directory Created**: February 2, 2026
**Maintained By**: Development Team
