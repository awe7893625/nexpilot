#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OWNER="${GITHUB_OWNER:-awe7893625}"
REPO="${GITHUB_REPO:-nexpilot}"
FULL_NAME="$OWNER/$REPO"

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI 'gh' is required." >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "GitHub CLI is not authenticated." >&2
  echo "Run: gh auth login -h github.com" >&2
  exit 1
fi

bash scripts/prepublish.sh

if gh repo view "$FULL_NAME" >/dev/null 2>&1; then
  echo "Using existing public repo: $FULL_NAME"
  if ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "https://github.com/$FULL_NAME.git"
  fi
  git push -u origin main
else
  echo "Creating public GitHub repo: $FULL_NAME"
  gh repo create "$FULL_NAME" \
    --public \
    --description "local-first phone terminal cockpit" \
    --source "$ROOT" \
    --remote origin \
    --push
fi

echo
echo "Published public repo:"
echo "https://github.com/$FULL_NAME"
