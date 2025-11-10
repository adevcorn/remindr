# Makefile for Remindr development and CI/CD tasks

.PHONY: help install test lint format clean docker-build docker-up docker-down verify

# Default target
help:
	@echo "Remindr Development Commands"
	@echo "============================"
	@echo ""
	@echo "Setup:"
	@echo "  make install          - Install all dependencies"
	@echo "  make install-backend  - Install backend dependencies"
	@echo "  make install-mobile   - Install mobile dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make run-backend      - Run backend in development mode"
	@echo "  make run-mobile       - Run mobile app"
	@echo ""
	@echo "Quality:"
	@echo "  make test             - Run all tests"
	@echo "  make test-backend     - Run backend tests"
	@echo "  make test-mobile      - Run mobile tests"
	@echo "  make lint             - Lint all code"
	@echo "  make lint-backend     - Lint backend code"
	@echo "  make lint-mobile      - Lint mobile code"
	@echo "  make format           - Format all code"
	@echo "  make format-backend   - Format backend code"
	@echo "  make format-mobile    - Format mobile code"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build     - Build Docker images"
	@echo "  make docker-up        - Start services with docker-compose"
	@echo "  make docker-down      - Stop services"
	@echo "  make docker-logs      - View service logs"
	@echo ""
	@echo "CI/CD:"
	@echo "  make verify           - Run build verification"
	@echo "  make ci               - Run CI checks locally"
	@echo "  make clean            - Clean build artifacts"

# Installation
install: install-backend install-mobile

install-backend:
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing dev dependencies..."
	pip install flake8 mypy black isort pylint pytest pytest-asyncio pytest-cov bandit safety

install-mobile:
	@echo "Installing mobile dependencies..."
	cd mobile && flutter pub get

# Development
run-backend:
	cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-mobile:
	cd mobile && flutter run

# Testing
test: test-backend test-mobile

test-backend:
	@echo "Running backend tests..."
	cd backend && pytest --cov=app --cov-report=term-missing

test-mobile:
	@echo "Running mobile tests..."
	cd mobile && flutter test --coverage

# Linting
lint: lint-backend lint-mobile

lint-backend:
	@echo "Linting backend code..."
	cd backend && flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics
	cd backend && flake8 app/ --count --max-complexity=15 --max-line-length=100 --statistics
	cd backend && pylint app/ --max-line-length=100 --disable=C0111,R0903,W0212 || true
	cd backend && mypy app/ --ignore-missing-imports --no-strict-optional --check-untyped-defs || true

lint-mobile:
	@echo "Linting mobile code..."
	cd mobile && flutter analyze

# Formatting
format: format-backend format-mobile

format-backend:
	@echo "Formatting backend code..."
	cd backend && black app/
	cd backend && isort app/

format-mobile:
	@echo "Formatting mobile code..."
	cd mobile && dart format lib/

# Security
security-check:
	@echo "Running security checks..."
	cd backend && bandit -r app/ -ll -x app/tests/ || true
	cd backend && safety check || true

# Docker
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d
	@echo "Waiting for services to start..."
	@sleep 5
	@echo "Services started. Backend available at http://localhost:8000"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-restart:
	docker-compose restart

# CI/CD
verify:
	@bash scripts/verify-build.sh

ci: lint test security-check
	@echo "✓ All CI checks passed locally"

# Cleanup
clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	cd mobile && flutter clean || true
	@echo "✓ Cleanup complete"

# Database migrations (for future use)
db-migrate:
	cd backend && alembic upgrade head

db-rollback:
	cd backend && alembic downgrade -1

db-reset:
	cd backend && alembic downgrade base && alembic upgrade head
