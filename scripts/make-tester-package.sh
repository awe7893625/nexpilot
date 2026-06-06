#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ $# -ne 1 ]]; then
  echo "Usage: bash scripts/make-tester-package.sh TESTER_ID" >&2
  echo "Example: bash scripts/make-tester-package.sh alice-20260606" >&2
  exit 2
fi

tester_id="$1"
if [[ ! "$tester_id" =~ ^[A-Za-z0-9._-]{3,64}$ ]]; then
  echo "TESTER_ID must be 3-64 chars: letters, numbers, dot, underscore, hyphen." >&2
  exit 2
fi

bash scripts/review-gate.sh

version="$(PYTHONPATH="$ROOT/src" python3 -c 'from nexpilot_public import __version__; print(__version__)')"
short_sha="$(git rev-parse --short HEAD)"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
package_dir="nexpilot-private-beta-${version}-${tester_id}-${short_sha}"
tmp_root="$(mktemp -d)"
out_dir="$ROOT/dist/testers"
out_file="$out_dir/${package_dir}.tar.gz"

cleanup() {
  rm -rf "$tmp_root"
}
trap cleanup EXIT

mkdir -p "$out_dir"
git archive --format=tar --prefix="${package_dir}/" HEAD | tar -x -C "$tmp_root"

notice_path="$tmp_root/$package_dir/BETA_ACCESS_NOTICE.txt"
{
  echo "NexPilot private beta package"
  echo "Tester ID: $tester_id"
  echo "Commit: $short_sha"
  echo "Generated UTC: $stamp"
  echo ""
  echo "This package is non-transferable."
  echo "Do not copy, redistribute, mirror, sell, sublicense, publish, upload, or share it."
  echo "Do not share token URLs. A token URL grants shell access while the agent is running."
  echo "Use same Wi-Fi/LAN or tester-owned Tailscale only. Do not expose this to the public internet."
  echo ""
  echo "See docs/BETA_TESTER_TERMS.md and LICENSE."
} > "$notice_path"

tar -czf "$out_file" -C "$tmp_root" "$package_dir"
shasum -a 256 "$out_file" > "${out_file}.sha256"

echo "Tester package: $out_file"
echo "Checksum:       ${out_file}.sha256"
