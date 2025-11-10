#!/bin/bash
#
# Performance Benchmark Test Runner
# ==================================
# Executes comprehensive performance benchmarks for Remindr backend
# and validates against PRD performance targets.
#
# Usage:
#   bash scripts/run-performance-tests.sh [options]
#
# Options:
#   --all          Run all performance tests (default)
#   --quick        Run quick smoke tests only
#   --verbose      Show detailed output
#   --report       Generate HTML coverage report
#   --ci           CI mode (stricter assertions, no verbose output)
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_DIR="backend"
TEST_FILE="tests/test_performance.py"
VENV_PATH="$BACKEND_DIR/.venv"

# Parse arguments
MODE="all"
VERBOSE=""
REPORT=false
CI_MODE=false

for arg in "$@"; do
  case $arg in
    --all)
      MODE="all"
      ;;
    --quick)
      MODE="quick"
      ;;
    --verbose)
      VERBOSE="-v -s"
      ;;
    --report)
      REPORT=true
      ;;
    --ci)
      CI_MODE=true
      VERBOSE=""
      ;;
    *)
      echo -e "${RED}Unknown option: $arg${NC}"
      exit 1
      ;;
  esac
done

# Banner
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Remindr Performance Benchmark Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if backend directory exists
if [ ! -d "$BACKEND_DIR" ]; then
  echo -e "${RED}Error: Backend directory not found${NC}"
  exit 1
fi

cd "$BACKEND_DIR"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
  echo -e "${YELLOW}Warning: Virtual environment not found at $VENV_PATH${NC}"
  echo -e "${YELLOW}Attempting to use system Python...${NC}"
  PYTHON_CMD="python3"
else
  # Activate virtual environment
  echo -e "${GREEN}Activating virtual environment...${NC}"
  source "$VENV_PATH/bin/activate"
  PYTHON_CMD="python"
fi

# Verify pytest is installed
if ! $PYTHON_CMD -m pytest --version > /dev/null 2>&1; then
  echo -e "${RED}Error: pytest is not installed${NC}"
  echo -e "${YELLOW}Install dependencies: pip install -r requirements.txt${NC}"
  exit 1
fi

# Verify required dependencies
echo -e "${GREEN}Checking dependencies...${NC}"
MISSING_DEPS=()

for package in "sentence_transformers" "google.cloud.speech" "psutil"; do
  if ! $PYTHON_CMD -c "import $package" > /dev/null 2>&1; then
    MISSING_DEPS+=("$package")
  fi
done

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
  echo -e "${YELLOW}Warning: Some dependencies are missing: ${MISSING_DEPS[*]}${NC}"
  echo -e "${YELLOW}Some tests may be skipped or mocked${NC}"
fi

# Display test configuration
echo -e "${GREEN}Test Mode: ${MODE}${NC}"
echo -e "${GREEN}CI Mode: ${CI_MODE}${NC}"
echo ""

# Run tests based on mode
if [ "$MODE" = "quick" ]; then
  echo -e "${BLUE}Running quick performance smoke tests...${NC}"
  TESTS=(
    "test_nlp_inference_performance"
    "test_text_capture_end_to_end_performance"
    "test_performance_summary"
  )
  
  for test in "${TESTS[@]}"; do
    echo -e "${YELLOW}Running: $test${NC}"
    $PYTHON_CMD -m pytest "$TEST_FILE::$test" -m performance $VERBOSE || true
  done
  
elif [ "$MODE" = "all" ]; then
  echo -e "${BLUE}Running all performance benchmarks...${NC}"
  echo ""
  
  # Run all performance tests with markers
  if [ "$CI_MODE" = true ]; then
    $PYTHON_CMD -m pytest "$TEST_FILE" -m performance --tb=short
  else
    $PYTHON_CMD -m pytest "$TEST_FILE" -m performance $VERBOSE --tb=short
  fi
fi

# Generate report if requested
if [ "$REPORT" = true ]; then
  echo ""
  echo -e "${GREEN}Generating HTML coverage report...${NC}"
  $PYTHON_CMD -m pytest "$TEST_FILE" -m performance --cov=app --cov-report=html
  echo -e "${GREEN}Report generated: backend/htmlcov/index.html${NC}"
fi

# Summary
EXIT_CODE=$?
echo ""
echo -e "${BLUE}========================================${NC}"
if [ $EXIT_CODE -eq 0 ]; then
  echo -e "${GREEN}✅ All performance benchmarks passed!${NC}"
else
  echo -e "${RED}❌ Some performance benchmarks failed${NC}"
fi
echo -e "${BLUE}========================================${NC}"
echo ""

# Performance targets summary
echo -e "${BLUE}PRD Performance Targets:${NC}"
echo -e "  • Task capture time: ${YELLOW}< 3 seconds${NC}"
echo -e "  • Google sync latency: ${YELLOW}< 10 seconds${NC}"
echo -e "  • AI classification accuracy: ${YELLOW}≥ 90%${NC}"
echo -e "  • NLP inference time: ${YELLOW}< 500ms${NC}"
echo ""

# Next steps
if [ $EXIT_CODE -ne 0 ] && [ "$CI_MODE" = false ]; then
  echo -e "${YELLOW}Next steps:${NC}"
  echo -e "  1. Review failed benchmarks above"
  echo -e "  2. Check docs/performance_benchmarks.md for optimization tips"
  echo -e "  3. Profile slow operations with: python -m cProfile -s cumtime"
  echo ""
fi

exit $EXIT_CODE
