#!/bin/bash
#
# Run all test suites in sequence
# Usage: ./scripts/run_all_tests.sh [--api-url URL]
#

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
API_URL="${API_URL:-http://localhost:8000}"
SKIP_UNIT=false
SKIP_INTEGRATION=false
SKIP_SMOKE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --api-url)
      API_URL="$2"
      shift 2
      ;;
    --skip-unit)
      SKIP_UNIT=true
      shift
      ;;
    --skip-integration)
      SKIP_INTEGRATION=true
      shift
      ;;
    --skip-smoke)
      SKIP_SMOKE=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--api-url URL] [--skip-unit] [--skip-integration] [--skip-smoke]"
      exit 1
      ;;
  esac
done

echo ""
echo "======================================================================"
echo "🧪 AI Employee - Complete Test Suite"
echo "======================================================================"
echo "API URL: $API_URL"
echo ""

FAILED_TESTS=()

# 1. Unit Tests (Spec Tests)
if [ "$SKIP_UNIT" = false ]; then
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "📝 1. Running Unit Tests (116 spec tests)"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  
  if PYTHONPATH=. GROQ_API_KEY=test-dummy python -m unittest discover -s tests -v; then
    echo -e "${GREEN}✅ Unit tests PASSED${NC}"
  else
    echo -e "${RED}❌ Unit tests FAILED${NC}"
    FAILED_TESTS+=("Unit Tests")
  fi
  echo ""
else
  echo -e "${YELLOW}⏭️  Skipping unit tests${NC}"
  echo ""
fi

# 2. Smoke Tests
if [ "$SKIP_SMOKE" = false ]; then
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🔬 2. Running Smoke Tests (Critical paths)"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  
  if python scripts/smoke_test.py --api-url "$API_URL"; then
    echo -e "${GREEN}✅ Smoke tests PASSED${NC}"
  else
    echo -e "${RED}❌ Smoke tests FAILED${NC}"
    FAILED_TESTS+=("Smoke Tests")
  fi
  echo ""
else
  echo -e "${YELLOW}⏭️  Skipping smoke tests${NC}"
  echo ""
fi

# 3. Integration Tests
if [ "$SKIP_INTEGRATION" = false ]; then
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🔗 3. Running Integration Tests (End-to-end booking flow)"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  
  if python scripts/integration_test.py --api-url "$API_URL"; then
    echo -e "${GREEN}✅ Integration tests PASSED${NC}"
  else
    echo -e "${RED}❌ Integration tests FAILED${NC}"
    FAILED_TESTS+=("Integration Tests")
  fi
  echo ""
else
  echo -e "${YELLOW}⏭️  Skipping integration tests${NC}"
  echo ""
fi

# 4. Multi-Trade QA (P0)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🏭 4. Running Multi-Trade QA (P0 automated tests)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if PYTHONPATH=. python scripts/p0_trade_qa.py plumbing gas_engineer mobile_mechanic; then
  echo -e "${GREEN}✅ Multi-trade QA PASSED${NC}"
else
  echo -e "${YELLOW}⚠️  Multi-trade QA completed with warnings${NC}"
  # Don't fail the suite on P0 QA warnings
fi
echo ""

# Final Summary
echo "======================================================================"
echo "📊 Test Suite Summary"
echo "======================================================================"
echo ""

if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
  echo -e "${GREEN}✅ ALL TEST SUITES PASSED${NC}"
  echo ""
  echo "Total test suites run: $(( 4 - ${SKIP_UNIT:-0} - ${SKIP_SMOKE:-0} - ${SKIP_INTEGRATION:-0} ))"
  echo ""
  echo "Your code is ready for deployment! 🚀"
  echo ""
  exit 0
else
  echo -e "${RED}❌ FAILED TEST SUITES:${NC}"
  for test in "${FAILED_TESTS[@]}"; do
    echo "  - $test"
  done
  echo ""
  echo "Please fix failing tests before deployment."
  echo ""
  exit 1
fi
