#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -d venv ]]; then
    python3 -m venv venv
    venv/bin/pip install -q -e ".[dev]"
fi
