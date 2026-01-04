#!/bin/bash
set -euo pipefail

# install system packages needed for pre-commit hooks
if ! command -v shellcheck &> /dev/null; then
  apt-get update -qq && apt-get install -y -qq shellcheck >/dev/null 2>&1
fi

# create venv if it doesn't exist
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

# activate the venv for the script and session
# shellcheck source=/dev/null
source venv/bin/activate

# install package in editable mode with dev dependencies
pip install -q -e ".[dev]"

# install pre-commit hooks (without --install-hooks to avoid network issues)
pre-commit install
pre-commit install --hook-type commit-msg

# activate the venv for the session
# shellcheck disable=SC2016
echo 'source "$CLAUDE_PROJECT_DIR/venv/bin/activate"' >> "$CLAUDE_ENV_FILE"
