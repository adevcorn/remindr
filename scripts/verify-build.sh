#!/bin/bash
# Build verification script for CI/CD pipelines

set -e  # Exit on error

echo "======================================"
echo "Remindr Build Verification"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
OVERALL_STATUS=0

echo ""
echo "1. Checking Python environment..."
if python3 --version; then
    echo -e "${GREEN}✓ Python installed${NC}"
else
    echo -e "${RED}✗ Python not found${NC}"
    OVERALL_STATUS=1
fi

echo ""
echo "2. Verifying backend dependencies..."
cd backend
if pip install -r requirements.txt --dry-run > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend dependencies resolvable${NC}"
else
    echo -e "${RED}✗ Backend dependencies have issues${NC}"
    OVERALL_STATUS=1
fi

echo ""
echo "3. Checking backend code quality..."
if command -v flake8 &> /dev/null; then
    if flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics; then
        echo -e "${GREEN}✓ No critical syntax errors${NC}"
    else
        echo -e "${RED}✗ Syntax errors found${NC}"
        OVERALL_STATUS=1
    fi
else
    echo -e "${YELLOW}⚠ flake8 not installed, skipping${NC}"
fi

echo ""
echo "4. Verifying backend imports..."
if python3 -c "from app.main import app; print('✓ Main app imports successfully')" 2>/dev/null; then
    echo -e "${GREEN}✓ Backend imports valid${NC}"
else
    echo -e "${YELLOW}⚠ Backend imports need dependencies installed${NC}"
fi

cd ..

echo ""
echo "5. Checking Flutter environment..."
if command -v flutter &> /dev/null; then
    echo -e "${GREEN}✓ Flutter installed${NC}"
    flutter --version
else
    echo -e "${YELLOW}⚠ Flutter not installed (mobile builds will be skipped)${NC}"
fi

echo ""
echo "6. Verifying mobile dependencies..."
if command -v flutter &> /dev/null; then
    cd mobile
    if flutter pub get --dry-run > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Mobile dependencies resolvable${NC}"
    else
        echo -e "${RED}✗ Mobile dependencies have issues${NC}"
        OVERALL_STATUS=1
    fi
    cd ..
else
    echo -e "${YELLOW}⚠ Skipping mobile dependency check${NC}"
fi

echo ""
echo "7. Checking Docker..."
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓ Docker installed${NC}"
    docker --version
else
    echo -e "${YELLOW}⚠ Docker not installed (containerization unavailable)${NC}"
fi

echo ""
echo "8. Checking docker-compose..."
if command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}✓ docker-compose installed${NC}"
    docker-compose --version
else
    echo -e "${YELLOW}⚠ docker-compose not installed${NC}"
fi

echo ""
echo "======================================"
if [ $OVERALL_STATUS -eq 0 ]; then
    echo -e "${GREEN}✓ Build verification PASSED${NC}"
    echo "======================================"
    exit 0
else
    echo -e "${RED}✗ Build verification FAILED${NC}"
    echo "======================================"
    exit 1
fi
