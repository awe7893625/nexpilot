#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== NexPilot Review Gate ==="

bash scripts/doctor.sh

required_files=(
  README.md
  SECURITY.md
  docs/TESTER_QUICKSTART.md
  docs/BETA_TESTER_TERMS.md
  docs/CLOUD_RELAY_SECURITY_SPEC.md
  docs/NEXPILOT_PRIVATE_BETA_REPORT.md
  docs/NEXPILOT_INTRANET_CONNECTION_REPORT.md
  docs/REVIEW_GATE.md
  docs/TERMINAL_GRADE_BETA.md
  docs/WINDOWS_BETA.md
)

for path in "${required_files[@]}"; do
  if [[ ! -f "$path" ]]; then
    echo "Missing required review file: $path" >&2
    exit 1
  fi
done

if rg -n "public internet|公網|Tailscale|token|same Wi-Fi|同 Wi-Fi" README.md SECURITY.md docs >/dev/null; then
  :
else
  echo "Required safety wording not found in docs." >&2
  exit 1
fi

if rg -n "Do not copy|redistribute|non-transferable|non-transferable|不能轉傳|不可轉傳" README.md SECURITY.md LICENSE docs >/dev/null; then
  :
else
  echo "Required redistribution warning not found in docs." >&2
  exit 1
fi

if rg -n "not yet full Termius|not yet a complete Termius|not yet full Termius feature parity" README.md docs >/dev/null; then
  :
else
  echo "Termius parity limitation is not documented." >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Working tree is not clean." >&2
  git status -sb
  exit 1
fi

echo "NexPilot review gate: PASS"
