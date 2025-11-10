# CI/CD and Deployment Guide

## Overview

This document describes the CI/CD infrastructure for the Remindr application, including pipelines, deployment configurations, and required secrets/environment variables.

## Architecture

```
┌─────────────────┐
│  GitHub Actions │
│   CI/CD Pipeline│
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    │         │          │          │
┌───▼───┐ ┌──▼────┐ ┌───▼────┐ ┌───▼────────┐
│Backend│ │Mobile │ │Security│ │Integration │
│  CI   │ │  CI   │ │ Checks │ │   Tests    │
└───┬───┘ └───┬───┘ └───┬────┘ └───┬────────┘
    │         │          │          │
    └─────────┴──────────┴──────────┘
                 │
         ┌───────▼────────┐
         │  Docker Build  │
         │  & Registry    │
         └───────┬────────┘
                 │
         ┌───────▼────────┐
         │   Kubernetes   │
         │   Deployment   │
         └────────────────┘
```

## CI/CD Pipelines

### 1. Backend CI (.github/workflows/backend-ci.yml)

**Triggers:**
- Push to `main` or feature branches
- Pull requests to `main`
- Changes to `backend/**` files

**Jobs:**

#### Lint and Test (Python 3.11, 3.12)
- Code formatting (Black)
- Import sorting (isort)
- Linting (flake8, pylint)
- Type checking (mypy)
- Unit tests (pytest with coverage)
- Security scanning (bandit, safety)

#### Build Verification
- Verify FastAPI application starts
- Test health endpoints
- Validate API accessibility

**Services:**
- PostgreSQL 15 (test database)
- Redis 7 (test cache/queue)

### 2. Mobile CI (.github/workflows/mobile-ci.yml)

**Triggers:**
- Push to `main` or feature branches
- Pull requests to `main`
- Changes to `mobile/**` files

**Jobs:**

#### Analyze and Test
- Flutter code analysis
- Dart formatting check
- Unit tests with coverage

#### Build Android
- Debug APK build (Android ARM64)
- Release App Bundle (unsigned)
- Upload APK artifacts (7-day retention)

#### Build iOS
- Debug build (no codesign)
- Verify build artifacts

### 3. Integration Tests (.github/workflows/integration.yml)

**Triggers:**
- Push to `main`
- Pull requests to `main`
- Manual workflow dispatch

**Tests:**
- Backend API health checks
- Core endpoint validation
- Database connection verification
- Backend-Mobile API contract validation

## Deployment Configurations

### Docker Compose (Local/Development)

**File:** `docker-compose.yml`

**Services:**
- `postgres` - PostgreSQL 15 database
- `redis` - Redis 7 cache/queue
- `backend` - FastAPI application (port 8000)
- `celery-worker` - Async task processing
- `celery-beat` - Scheduled task execution

**Usage:**
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

### Kubernetes (Production)

**Configuration Files:**
- `k8s/backend-deployment.yml` - Backend API deployment
- `k8s/celery-deployment.yml` - Celery worker & beat
- `k8s/config.yml` - ConfigMaps and Secrets

**Features:**
- **Horizontal Pod Autoscaling:** 3-10 replicas based on CPU/memory
- **Rolling Updates:** Zero-downtime deployments
- **Health Checks:** Liveness and readiness probes
- **Resource Limits:** CPU and memory constraints
- **Secrets Management:** Encrypted credentials

**Deployment:**
```bash
# Apply configurations
kubectl apply -f k8s/config.yml
kubectl apply -f k8s/backend-deployment.yml
kubectl apply -f k8s/celery-deployment.yml

# Verify deployment
kubectl get pods -l app=remindr
kubectl get svc remindr-backend

# View logs
kubectl logs -l app=remindr,component=backend --tail=100 -f

# Scale manually
kubectl scale deployment remindr-backend --replicas=5
```

## Environment Variables and Secrets

### Backend Environment Variables

#### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/remindr` |
| `REDIS_URL` | Redis connection string | `redis://host:6379/0` |
| `SECRET_KEY` | Application secret key | `random-secure-string` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON | `/path/to/service-account.json` |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | `my-project-123456` |
| `GOOGLE_CLIENT_ID` | OAuth 2.0 client ID | `*.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 client secret | `GOCSPX-***` |

#### Optional (with defaults)

| Variable | Description | Default |
|----------|-------------|---------|
| `AI_CONFIDENCE_THRESHOLD` | Minimum AI confidence for auto-filing | `0.85` |
| `SYNC_RETRY_MAX_ATTEMPTS` | Max sync retry attempts | `5` |
| `SYNC_RETRY_BACKOFF_BASE` | Exponential backoff base | `2` |
| `API_V1_PREFIX` | API path prefix | `/api/v1` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000` |

### GitHub Secrets Configuration

Add these secrets to your GitHub repository:

```bash
# GitHub Settings -> Secrets and variables -> Actions -> New repository secret

# Backend Secrets
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
SECRET_KEY=...
GOOGLE_APPLICATION_CREDENTIALS=<base64-encoded-json>
GOOGLE_CLOUD_PROJECT=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Container Registry (if using GCR)
GCP_PROJECT_ID=...
GCP_SA_KEY=<base64-encoded-service-account-json>
```

### Kubernetes Secrets

```bash
# Create database secret
kubectl create secret generic remindr-secrets \
  --from-literal=database-url='postgresql://...' \
  --from-literal=redis-url='redis://...' \
  --from-literal=secret-key='...' \
  --from-literal=google-client-id='...' \
  --from-literal=google-client-secret='...'

# Create Google service account secret
kubectl create secret generic google-service-account \
  --from-file=service-account.json=path/to/service-account.json

# Verify secrets
kubectl get secrets
kubectl describe secret remindr-secrets
```

## Security Considerations

### Secret Management

1. **Never commit secrets to version control**
   - Use `.env` files (added to `.gitignore`)
   - Use environment variables in CI/CD
   - Use Kubernetes secrets or cloud secret managers

2. **Rotate credentials regularly**
   - Database passwords every 90 days
   - API keys every 180 days
   - OAuth credentials on security events

3. **Use least privilege principle**
   - Google service account minimal scopes
   - Database user restricted permissions
   - Kubernetes RBAC policies

### CI/CD Security

- **Dependency scanning:** Safety checks in backend CI
- **Security linting:** Bandit for Python vulnerabilities
- **Image scanning:** Docker image vulnerability scans (recommended)
- **Secret scanning:** GitHub secret scanning enabled

## Monitoring and Observability

### Health Checks

- **Backend:** `GET /health` returns `{"status": "healthy"}`
- **Database:** PostgreSQL `pg_isready` check
- **Redis:** `redis-cli ping` check

### Logs

**Docker Compose:**
```bash
docker-compose logs -f [service-name]
```

**Kubernetes:**
```bash
kubectl logs -l app=remindr,component=backend --tail=100 -f
kubectl logs -l app=remindr,component=celery-worker --tail=100 -f
```

### Metrics (Recommended)

- **Application:** Prometheus + Grafana
- **Infrastructure:** Cloud provider monitoring (GCP Monitoring, etc.)
- **Uptime:** External health check monitoring

## Build Verification

### Local Build Test

```bash
# Backend
cd backend
pip install -r requirements.txt
python -m pytest
python -m uvicorn app.main:app --reload

# Mobile
cd mobile
flutter pub get
flutter analyze
flutter test
flutter build apk --debug
```

### Docker Build Test

```bash
# Build backend image
docker build -t remindr-backend:test ./backend

# Test image
docker run -d --name test-backend \
  -e DATABASE_URL=sqlite:///./test.db \
  -e REDIS_URL=redis://localhost:6379 \
  -e SECRET_KEY=test \
  -p 8000:8000 \
  remindr-backend:test

# Verify
curl http://localhost:8000/health

# Cleanup
docker stop test-backend && docker rm test-backend
```

## Troubleshooting

### Common Issues

**Issue:** Backend CI fails with "Import could not be resolved"
- **Solution:** Ensure all dependencies in `requirements.txt` are installed

**Issue:** Mobile build fails on iOS
- **Solution:** iOS builds require macOS runner, debug build is no-codesign

**Issue:** Docker build fails with "Cannot connect to database"
- **Solution:** Ensure `DATABASE_URL` is set correctly and database is accessible

**Issue:** Kubernetes pods crash with "Secret not found"
- **Solution:** Create required secrets before deploying: `kubectl create secret...`

### Debug Commands

```bash
# Check GitHub Actions logs
gh run list --workflow=backend-ci.yml
gh run view <run-id> --log

# Check Docker logs
docker-compose logs -f backend
docker inspect <container-id>

# Check Kubernetes status
kubectl describe pod <pod-name>
kubectl logs <pod-name> --previous
kubectl get events --sort-by='.lastTimestamp'
```

## Next Steps

1. **Review and customize** environment variables for your deployment
2. **Set up GitHub secrets** for automated CI/CD
3. **Configure Google Cloud** services (Speech, Vision, Tasks, Calendar APIs)
4. **Set up Kubernetes cluster** (GKE, EKS, or self-managed)
5. **Deploy to staging** environment first
6. **Run integration tests** against staging
7. **Deploy to production** with monitoring enabled

## Support

For issues or questions:
- Review workflow logs in GitHub Actions
- Check application logs in Docker/Kubernetes
- Consult the PRD (`docs/prd.md`) and SPEC (`docs/spec.txt`) for requirements
- Contact DevOps Engineer agent for infrastructure issues
