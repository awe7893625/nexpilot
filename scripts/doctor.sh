#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 -m compileall src tests
python3 scripts/secret-scan.py .
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH="$ROOT/src" python3 -m pytest
