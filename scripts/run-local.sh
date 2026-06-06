#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  echo "Missing .venv. Run: bash scripts/install.sh" >&2
  exit 1
fi

source .venv/bin/activate
nexpilot --host 127.0.0.1
