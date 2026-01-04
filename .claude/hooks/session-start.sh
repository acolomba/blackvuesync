#!/bin/bash
set -euo pipefail

# create venv if it doesn't exist
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

# activate the venv for the script and session
source venv/bin/activate

# install package in editable mode with dev dependencies
pip install -q -e ".[dev]"

# install pre-commit hooks (without --install-hooks to avoid network issues)
pre-commit install
pre-commit install --hook-type commit-msg

# activate the venv for the session
echo 'source "$CLAUDE_PROJECT_DIR/venv/bin/activate"' >> "$CLAUDE_ENV_FILE"
