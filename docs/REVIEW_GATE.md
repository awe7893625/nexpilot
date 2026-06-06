# NexPilot Private Beta Review Gate

This gate must pass before any GitHub push, tester invite, tarball handoff, or
visibility change.

## Verdict Levels

- `PASS`: safe for the next private-beta step.
- `REVISION_REQUIRED`: do not share yet; fix listed issues and rerun.
- `BLOCKED`: cannot proceed without owner input or missing credentials.

## Required Review Lanes

### 1. Source Isolation

Required:

- Work from this clean repo only.
- Do not publish M4ControlCenter, `.m4_data`, NexDesk hub data, Kai artifacts,
  logs, DBs, backups, or private device IDs.
- `git status -sb` must be clean before publish.

### 2. Secret Hygiene

Required command:

```bash
python3 scripts/secret-scan.py .
```

Required result: PASS.

### 3. Functional Gate

Required command:

```bash
bash scripts/doctor.sh
```

Required result:

- compile PASS
- secret scan PASS
- pytest PASS

### 4. Runtime Smoke

Required before first external tester:

```bash
nexpilot --host 127.0.0.1 --port 8765 --token test-token
python3 scripts/smoke-terminal.py --url 'ws://127.0.0.1:8765/ws/terminal?token=test-token'
```

Required result: terminal marker round-trip PASS.

Reconnect smoke:

```bash
python3 scripts/smoke-reconnect.py --url 'ws://127.0.0.1:8765/ws/terminal?token=test-token'
```

Required result: reconnect marker PASS.

### 5. Network Safety

Required:

- Same Wi-Fi/LAN or tester-owned Tailscale only.
- No public IP exposure.
- No router port forwarding.
- No Rain internal tailnet access for testers.

### 6. Documentation

Required files:

- `README.md`
- `SECURITY.md`
- `docs/TESTER_QUICKSTART.md`
- `docs/BETA_TESTER_TERMS.md`
- `docs/CLOUD_RELAY_SECURITY_SPEC.md`
- `docs/NEXPILOT_PRIVATE_BETA_REPORT.md`
- `docs/NEXPILOT_INTRANET_CONNECTION_REPORT.md`
- `docs/TERMINAL_GRADE_BETA.md`
- `docs/WINDOWS_BETA.md`

Required content:

- token URL warning
- no public internet warning
- same Wi-Fi / own Tailscale instructions
- non-transferable / no redistribution warning
- public cloud relay disabled unless a separate security gate passes
- Termius parity limitation
- current limitations

### 7. Terminal-Grade Beta Gate

Required:

- session reconnect enabled
- recent output replay enabled
- heartbeat/stale connection handling enabled
- input/output batching enabled
- paste chunking enabled
- copy/paste/clear controls present
- Windows import path does not break on non-POSIX platforms

### 8. Copy-Risk Control

Required:

- GitHub private repo only.
- Per-tester tarballs must be built with
  `bash scripts/make-tester-package.sh TESTER_ID`.
- Tester packages must include `BETA_ACCESS_NOTICE.txt`.
- Tester packages must include SHA-256 checksums.

Important boundary: source access cannot technically stop copying after a
tester receives it. This private beta reduces risk with private invites,
non-transferable terms, per-tester packages, and review evidence. Stronger copy
resistance requires a later binary-only build plus a license server.

### 9. GitHub Publish

Required:

- Repo must be private.
- Default target: `awe7893625/nexpilot-private-beta`.
- `scripts/publish-github.sh` must be used after `gh auth login`.
- GitHub Actions CI must pass after push.

## Current Review Status

Current local status: `REVISION_REQUIRED` for external sharing only because
GitHub CLI auth is invalid and no GitHub remote has been pushed.

Package readiness status: `PASS` for local package and internal review.

Known blocker:

```text
gh auth status -> token invalid for awe7893625
```

Next step:

```bash
gh auth login -h github.com
bash scripts/review-gate.sh
bash scripts/publish-github.sh
```
