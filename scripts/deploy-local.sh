#!/bin/bash
# Quick deployment script for local development

set -e

echo "======================================"
echo "Remindr Local Deployment"
echo "======================================"

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from example..."
    if [ -f .env.production.example ]; then
        cp .env.production.example .env
        echo "✓ Created .env from .env.production.example"
        echo "⚠️  Please edit .env and add your actual credentials"
        exit 1
    elif [ -f backend/.env.example ]; then
        cp backend/.env.example .env
        echo "✓ Created .env from backend/.env.example"
        echo "⚠️  Please edit .env and add your actual credentials"
        exit 1
    else
        echo "✗ No .env example file found"
        exit 1
    fi
fi

# Check for docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "✗ docker-compose not found. Please install Docker and docker-compose."
    exit 1
fi

# Check if services are already running
if docker-compose ps | grep -q "Up"; then
    echo "⚠️  Services are already running. Stopping them first..."
    docker-compose down
fi

echo ""
echo "Starting services..."
docker-compose up -d

echo ""
echo "Waiting for services to be healthy..."
sleep 10

# Check service health
echo ""
echo "Checking service status..."
docker-compose ps

echo ""
echo "Testing backend health endpoint..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ Backend is healthy and responding"
else
    echo "✗ Backend health check failed"
    echo "Check logs with: docker-compose logs backend"
    exit 1
fi

echo ""
echo "======================================"
echo "✓ Deployment successful!"
echo "======================================"
echo ""
echo "Services:"
echo "  - Backend API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"
echo ""
echo "Useful commands:"
echo "  - View logs: docker-compose logs -f [service]"
echo "  - Stop services: docker-compose down"
echo "  - Restart: docker-compose restart [service]"
echo "  - Shell access: docker-compose exec backend bash"
echo ""
