#!/usr/bin/env bash
# runs one test module and checks its source module against the
# configured line and branch coverage floor. paths are relative to the project root.
#
# usage: scripts/coverage-direct.sh blackvuesync.py test/blackvuesync_test.py
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "usage: $0 <source-path> <test-path>" >&2
    exit 2
fi

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

# uses the project venv when there is one, so the gate runs without activating it
if [[ -f venv/bin/activate ]]; then
    # shellcheck source=/dev/null
    source venv/bin/activate
fi

# keeps the measurement out of the project's own coverage data
data_dir=$(mktemp -d)
trap 'rm -rf "$data_dir"' EXIT
export COVERAGE_FILE="$data_dir/.coverage"

pytest --cov --cov-report= "$2"
coverage report --include="$1" --show-missing
