#!/bin/bash
set -euo pipefail

# only run in Claude Code on the web
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# create venv if it doesn't exist
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

# install package in editable mode with dev dependencies
venv/bin/pip install -q -e ".[dev]"

# install pre-commit hooks (without --install-hooks to avoid network issues)
venv/bin/pre-commit install
venv/bin/pre-commit install --hook-type commit-msg

# add venv/bin to PATH for the session
echo 'export PATH="$CLAUDE_PROJECT_DIR/venv/bin:$PATH"' >> "$CLAUDE_ENV_FILE"
