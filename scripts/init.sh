#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

PATH="$PATH:$HOME/.local/bin:$(npm prefix --global)/bin"
export PATH

# git
export GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never

# venv
if [[ ! -d venv ]]; then
    python3 -m venv venv
fi

venv/bin/pip install -q -e ".[dev]"

# pre-commit
if [[ -z $(git config --get core.hooksPath || true) ]]; then
    venv/bin/pre-commit install
fi

# skills
npx --yes skills@latest add blader/humanizer -a universal claude-code -y
npx --yes skills@latest add AminBlg/SimpleEnglish -a universal claude-code -y
