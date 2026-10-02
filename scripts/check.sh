#!/usr/bin/env bash
# runs the merge gate: the test pairing gate, the unit tests with line and
# branch coverage at the configured floor, and the behave scenarios. pre-commit runs the linters.
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

# uses the project venv when there is one, so the gate runs without activating it
if [[ -f venv/bin/activate ]]; then
    # shellcheck source=/dev/null
    source venv/bin/activate
fi

python3 scripts/check_corresponding_tests.py
pytest --cov --cov-report=term-missing --cov-report=xml:coverage.xml
behave
behave -D legacy_api=true
