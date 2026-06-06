#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

bash scripts/doctor.sh

if [[ -f scripts/review-gate.sh ]]; then
  # Avoid recursion: review-gate calls doctor but not prepublish.
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
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Working tree is not clean." >&2
  git status -sb
  exit 1
fi

echo "NexPilot prepublish gate: PASS"
