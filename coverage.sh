#!/bin/bash
set -euo pipefail

# generates comprehensive coverage report from unit and integration tests

echo "==> Cleaning previous coverage data..."
rm -f .coverage .coverage.* coverage.xml
rm -rf coverage_report/

echo "==> Running unit tests with coverage..."
COVERAGE_FILE=.coverage.pytest pytest test/blackvuesync_test.py --cov=. --cov-report= -v

echo ""
echo "==> Running integration tests with coverage..."
behave -D collect_coverage=true

echo ""
echo "==> Combining coverage data..."
coverage combine --keep

echo ""
echo "==> Generating HTML report..."
coverage html

# detects OS and uses appropriate command
os_name=$(uname -s)
if [[ "$os_name" == "Darwin" ]]; then
    open coverage_report/index.html
elif [[ "$os_name" == "Linux" ]]; then
    xdg-open coverage_report/index.html
else
    echo >&2 "Unknown OS. Please open coverage_report/index.html manually."
fi

echo ""
echo "Done! HTML report available at: coverage_report/index.html"
