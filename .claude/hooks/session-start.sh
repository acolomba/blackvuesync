#!/bin/bash
set -euo pipefail

# creates the venv when missing, as in a fresh remote container. scripts/init.sh
# does the rest of the setup.
if [[ ! -d venv ]]; then
  python3 -m venv venv
  venv/bin/pip install -q -e ".[dev]"
fi

# activates the venv for the session
echo "source \"$CLAUDE_PROJECT_DIR/venv/bin/activate\"" >> "$CLAUDE_ENV_FILE"
